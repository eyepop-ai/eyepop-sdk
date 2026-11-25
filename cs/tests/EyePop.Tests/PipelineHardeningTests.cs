using System.Text.Json.Nodes;
using EyePop.Core;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

/// <summary>Races between a socket, its replacement and the Pipeline's own background work.</summary>
public class PipelineHardeningTests
{
    private static readonly Source Url = new(new Media.Url("https://example.com/a.jpg"));
    private static readonly Source LiveUrl = new(new Media.Url("rtsp://example.com/cam"), new SourceOptions(Live: true));

    private static string Type(JsonNode node) => node["type"]!.GetValue<string>();

    private class TrackedStream(int length) : MemoryStream(new byte[length])
    {
        public volatile bool Closed;

        protected override void Dispose(bool disposing)
        {
            Closed = true;
            base.Dispose(disposing);
        }
    }

    private static Source Chunked(Func<Stream> open) => new(new Media.Upload("video/mp4", UploadContent.FromStream(open)));

    // Uploads across sockets

    [Fact]
    public async Task A_read_that_outlives_its_socket_does_not_cost_the_new_socket_a_second_open_of_the_stream()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        using var gate = new ManualResetEventSlim();
        var opens = 0;
        // The first stream is short, so its late read ends the upload: that is the read that must not evict the new socket's reader.
        var job = pipeline.SetSource(Chunked(() =>
        {
            if (Interlocked.Increment(ref opens) == 1)
            {
                gate.Wait();
                return new MemoryStream(new byte[100]);
            }
            return new MemoryStream(new byte[100_000]);
        }));
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await first.SentOfType("setSource");
        first.Say(new { type = "send", id = job.Id, credit = 70_000 });
        await Eventually.True(() => opens == 1);

        first.Close(1001, "going away");
        Assert.True(await next);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        await Rig.Answer(second, "setPop");
        await second.SentOfType("setSource");
        second.Say(new { type = "send", id = job.Id, credit = 70_000 });
        await Eventually.True(() => second.Sent.OfType<BinaryFrame>().Count() == 2);
        gate.Set();
        second.Say(new { type = "credit", id = job.Id, bytes = 40_000 });
        await second.SentOfType("uploaded");

        Assert.Equal(2, opens);
        Assert.Equal(new[] { 65_536, 4_464, 30_000 }, second.Sent.OfType<BinaryFrame>().Select(f => f.Bytes.Length - 1).ToArray());
        Assert.Empty(first.Sent.OfType<BinaryFrame>());
    }

    [Fact]
    public async Task A_reconnect_sends_an_upload_again_from_its_first_byte_by_opening_the_stream_again()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var opens = 0;
        var job = pipeline.SetSource(Chunked(() =>
        {
            Interlocked.Increment(ref opens);
            return new MemoryStream(Enumerable.Range(0, 1000).Select(i => (byte)i).ToArray());
        }));
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await first.SentOfType("setSource");
        first.Say(new { type = "send", id = job.Id, credit = 400 });
        await Eventually.True(() => first.Sent.OfType<BinaryFrame>().Any());

        first.Close(1001, "going away");
        Assert.True(await next);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        await Rig.Answer(second, "setPop");
        await second.SentOfType("setSource");
        second.Say(new { type = "send", id = job.Id, credit = 2000 });
        await second.SentOfType("uploaded");

        Assert.Equal(2, opens);
        var resent = second.Sent.OfType<BinaryFrame>().Single().Bytes.Span[1..].ToArray();
        Assert.Equal(1000, resent.Length);
        Assert.Equal(0, resent[0]);
    }

    [Fact]
    public async Task A_stream_failing_after_its_socket_was_replaced_does_not_stop_the_source_on_the_new_socket()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        using var gate = new ManualResetEventSlim();
        var opens = 0;
        var job = pipeline.SetSource(Chunked(() =>
        {
            if (Interlocked.Increment(ref opens) == 1)
            {
                gate.Wait();
                throw new IOException("old read failed late");
            }
            return new MemoryStream(new byte[10]);
        }));
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await first.SentOfType("setSource");
        first.Say(new { type = "send", id = job.Id, credit = 100 });
        await Eventually.True(() => opens == 1);
        first.Close(1001, "going away");
        Assert.True(await next);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        await Rig.Answer(second, "setPop");
        await second.SentOfType("setSource");

        gate.Set();
        await Eventually.Settle();

        Assert.DoesNotContain(second.SentJson, j => Type(j) == "stopSource");
        Assert.Equal(PipelineState.Open, pipeline.Status().State);
    }

    [Theory]
    [InlineData("http")]
    [InlineData("cancelled")]
    [InlineData("io")]
    public async Task A_stream_that_fails_to_open_stops_its_source_and_ends_the_Job_with_that_failure(string kind)
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        Exception failure = kind switch
        {
            "http" => new HttpRequestException("download failed"),
            "cancelled" => new TaskCanceledException("the caller's own timeout"),
            _ => new IOException("disk gone"),
        };
        var content = UploadContent.FromStream(() => throw failure, 10);

        var job = pipeline.SetSource(new Source(new Media.Upload("image/jpeg", content)));
        await socket.SentOfType("stopSource");
        socket.Say(new { type = "end", id = job.Id, reason = "stopped" });

        var error = await Assert.ThrowsAnyAsync<Exception>(async () => { await foreach (var _ in job.Messages()) { } });
        Assert.Same(failure, error);
    }

    [Fact]
    public async Task The_stream_of_a_source_is_closed_when_its_Job_ends()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var stream = new TrackedStream(10_000);
        var job = pipeline.SetSource(Chunked(() => stream));
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await socket.SentOfType("setSource");
        socket.Say(new { type = "send", id = job.Id, credit = 100 });
        await Eventually.True(() => socket.Sent.OfType<BinaryFrame>().Any());

        job.Cancel();
        await socket.SentOfType("stopSource");
        socket.Say(new { type = "end", id = job.Id, reason = "stopped" });

        await Eventually.True(() => stream.Closed);
    }

    [Fact]
    public async Task The_stream_of_a_source_is_closed_when_its_socket_is_replaced()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var stream = new TrackedStream(10_000);
        var job = pipeline.SetSource(Chunked(() => stream));
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        await socket.SentOfType("setSource");
        socket.Say(new { type = "send", id = job.Id, credit = 100 });
        await Eventually.True(() => socket.Sent.OfType<BinaryFrame>().Any());

        socket.Close(1001, "going away");
        await next;

        await Eventually.True(() => stream.Closed);
    }

    [Fact]
    public async Task The_stream_of_a_source_is_closed_when_the_Pipeline_closes()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var stream = new TrackedStream(10_000);
        var job = pipeline.SetSource(Chunked(() => stream));
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        await socket.SentOfType("setSource");
        socket.Say(new { type = "send", id = job.Id, credit = 100 });
        await Eventually.True(() => socket.Sent.OfType<BinaryFrame>().Any());

        await pipeline.CloseAsync();

        Assert.True(stream.Closed);
    }

    // A replaced socket

    [Fact]
    public async Task A_message_a_replaced_socket_still_delivers_is_dropped()
    {
        var rig = new Rig();
        rig.Sockets.NextIgnoresToken = true;
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await first.SentOfType("setSource");
        first.FailSends = true;
        pipeline.PingAsync().ContinueWith(_ => { }).Ignore();
        Assert.True(await next);
        Assert.IsType<Reconnecting>(messages.Current);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        await Rig.Answer(second, "setPop");
        Assert.IsType<Reconnected>((await Take(messages)));

        first.Say(Rig.Prediction(job.Id, 99));
        second.Say(Rig.Prediction(job.Id, 1));

        var prediction = Assert.IsType<PredictionMessage>(await Take(messages));
        Assert.Equal(1, prediction.Prediction.Timestamp);
    }

    [Fact]
    public async Task A_failure_a_replaced_socket_reports_late_does_not_end_the_new_one()
    {
        var rig = new Rig();
        rig.Sockets.NextIgnoresToken = true;
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await first.SentOfType("setSource");
        first.FailSends = true;
        pipeline.PingAsync().ContinueWith(_ => { }).Ignore();
        Assert.True(await next);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        await Rig.Answer(second, "setPop");
        Assert.IsType<Reconnected>(await Take(messages));

        first.Close(1008, "unexpected_bytes");
        second.Say(Rig.Prediction(job.Id, 1));

        Assert.IsType<PredictionMessage>(await Take(messages));
        Assert.Equal(PipelineState.Open, pipeline.Status().State);
    }

    private static async Task<JobMessage> Take(IAsyncEnumerator<JobMessage> messages)
    {
        Assert.True(await messages.MoveNextAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(5)));
        return messages.Current;
    }

    // Supervising the shell's own work

    [Fact]
    public async Task An_upgrade_that_never_answers_times_out_and_is_retried_with_backoff()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        rig.Sockets.HangNext();
        first.Close(1001, "going away");
        Assert.True(await next);
        await rig.AdvanceUntilConnect();

        await rig.Elapse(TimeSpan.FromSeconds(31));

        var retry = Assert.IsType<Reconnecting>(await Take(messages));
        Assert.Equal(ErrorKind.ConnectionFailed, retry.Cause.Kind);
        Assert.Equal(2, retry.Attempt);
    }

    [Fact]
    public async Task A_transport_that_throws_something_unexpected_is_retried_not_lost()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        rig.Sockets.BreakNext();
        first.Close(1001, "going away");
        Assert.True(await next);
        await rig.AdvanceUntilConnect();

        var retry = Assert.IsType<Reconnecting>(await Take(messages));

        Assert.Equal(ErrorKind.ConnectionFailed, retry.Cause.Kind);
    }

    [Fact]
    public async Task A_socket_whose_receive_throws_something_unexpected_is_replaced()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await Eventually.True(() => first.SentJson.Any(j => Type(j) == "setSource"));

        // The receive that is pending returns this message; the next one throws.
        first.ThrowOnReceive = new InvalidOperationException("a bug in the transport");
        first.Say(Rig.Prediction(job.Id, 1));

        Assert.True(await next);
        Assert.IsType<PredictionMessage>(messages.Current);
        Assert.IsType<Reconnecting>(await Take(messages));
    }

    // Closing

    [Fact]
    public async Task Close_cannot_hang_on_a_socket_that_never_finishes_sending()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        socket.BlockSends = true;

        var closing = pipeline.CloseAsync();
        await Eventually.Settle();
        Assert.False(closing.IsCompleted);
        await rig.Elapse(TimeSpan.FromSeconds(6));

        await closing.WaitAsync(TimeSpan.FromSeconds(5));
        Assert.True(socket.Disposed);
    }

    [Fact]
    public async Task Close_flushes_quit_before_it_closes_the_socket()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();

        await pipeline.CloseAsync();

        Assert.Equal("quit", Type(socket.SentJson.Last()));
        Assert.True(socket.Disposed);
    }

    [Fact]
    public async Task A_socket_that_opens_after_Close_is_closed_before_Close_returns()
    {
        var rig = new Rig();
        var release = new TaskCompletionSource();
        rig.Sockets.Hold = release.Task;
        using var cancel = new CancellationTokenSource();
        var connecting = Pipeline.ConnectAsync(Rig.LocalConfig, Rig.EmptyPop, rig.Deps(), cancel.Token);
        await Eventually.True(() => rig.Sockets.Attempts == 1);

        cancel.Cancel();
        release.SetResult();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => connecting);

        Assert.True(rig.Sockets.Opened.Single().Disposed);
    }

    [Fact]
    public async Task Close_during_a_resend_delay_does_not_wait_for_it()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        var setSource = await socket.SentOfType("setSource");
        socket.Say(new { type = "end", id = Rig.Id(setSource), reason = "eos" });
        await Eventually.True(() => rig.Time.HasTimerWithin(TimeSpan.FromSeconds(2)));

        await pipeline.CloseAsync().WaitAsync(TimeSpan.FromSeconds(5));

        Assert.False(await next);
    }

    // Jobs nobody reads

    [Fact]
    public async Task A_disposed_Job_does_not_stall_the_Jobs_that_are_read()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var abandoned = pipeline.SetSource(Url);
        var read = pipeline.SetSource(Url);
        var messages = read.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();

        await abandoned.DisposeAsync();
        for (var i = 0; i < 300; i++) socket.Say(Rig.Prediction(abandoned.Id, i));
        socket.Say(Rig.Prediction(read.Id, 7));

        Assert.True(await next.WaitAsync(TimeSpan.FromSeconds(5)));
        Assert.Equal(0, abandoned.Buffered);
    }

    [Fact]
    public async Task A_Job_whose_reader_stopped_does_not_stall_the_Jobs_that_are_read_and_buffers_nothing_more()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var left = pipeline.SetSource(Url);
        var read = pipeline.SetSource(Url);
        var leftMessages = left.Messages().GetAsyncEnumerator();
        var leftNext = leftMessages.MoveNextAsync().AsTask();
        socket.Say(Rig.Prediction(left.Id, 0));
        Assert.True(await leftNext);
        await leftMessages.DisposeAsync();
        var messages = read.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();

        for (var i = 0; i < 300; i++) socket.Say(Rig.Prediction(left.Id, i));
        socket.Say(Rig.Prediction(read.Id, 7));

        Assert.True(await next.WaitAsync(TimeSpan.FromSeconds(5)));
        Assert.Equal(0, left.Buffered);
    }

    [Fact]
    public async Task A_Job_that_ends_its_enumeration_no_longer_makes_the_reader_run()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Url);
        var other = pipeline.SetSource(Url);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        socket.Say(Rig.Prediction(job.Id, 0));
        Assert.True(await next);
        await messages.DisposeAsync();
        var before = socket.Received;
        // The receive that was already pending takes one more message; after that the reader waits.
        socket.Say(Rig.Prediction(other.Id, 1));
        await Eventually.True(() => socket.Received == before + 1);
        socket.Say(Rig.Prediction(other.Id, 2));
        await Eventually.Settle();

        Assert.Equal(before + 1, socket.Received);
    }

    [Fact]
    public async Task A_Job_that_filled_its_buffer_and_is_then_disposed_lets_the_reader_run_again()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var stalled = pipeline.SetSource(Url);
        var read = pipeline.SetSource(Url);
        var messages = read.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        var before = socket.Received;
        for (var i = 0; i < 300; i++) socket.Say(Rig.Prediction(stalled.Id, i));
        await Eventually.True(() => socket.Received - before == 256);
        socket.Say(Rig.Prediction(read.Id, 7));
        await Eventually.Settle();
        Assert.False(next.IsCompleted);

        await stalled.DisposeAsync();

        Assert.True(await next.WaitAsync(TimeSpan.FromSeconds(5)));
    }

    // Work that must not run under the Pipeline's lock, and what Close cancels

    [Fact]
    public async Task The_callers_stream_is_opened_outside_the_Pipelines_lock()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        bool? free = null;
        var content = UploadContent.FromStream(() =>
        {
            // Status takes the lock: from another thread it answers only if this thread does not hold it.
            free = Task.Run(() => pipeline.Status()).Wait(TimeSpan.FromSeconds(2));
            return new MemoryStream(new byte[10]);
        }, 10);

        pipeline.SetSource(new Source(new Media.Upload("image/jpeg", content)));
        await Eventually.True(() => free is not null);

        Assert.True(free);
    }

    private sealed class HangingStream : Stream
    {
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken ct = default)
        {
            await Task.Delay(Timeout.Infinite, ct);
            return 0;
        }

        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override void Flush() { }
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }

    [Fact]
    public async Task Close_cancels_a_read_of_the_callers_stream_that_is_waiting()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Chunked(() => new HangingStream()));
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        await socket.SentOfType("setSource");
        socket.Say(new { type = "send", id = job.Id, credit = 100 });
        await Eventually.Settle();

        await pipeline.CloseAsync().WaitAsync(TimeSpan.FromSeconds(5));
    }

    private sealed class BrokenStream : TrackedStream
    {
        public BrokenStream() : base(10) { }

        public override int Read(byte[] buffer, int offset, int count) => throw new IOException("read failed");
        public override int Read(Span<byte> buffer) => throw new IOException("read failed");
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken ct = default) => throw new IOException("read failed");
        public override Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken ct) => throw new IOException("read failed");
    }

    [Fact]
    public async Task A_stream_that_fails_while_it_is_read_is_closed_at_once()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var stream = new BrokenStream();
        var job = pipeline.SetSource(Chunked(() => stream));
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        await socket.SentOfType("setSource");

        socket.Say(new { type = "send", id = job.Id, credit = 100 });
        await socket.SentOfType("stopSource");

        Assert.True(stream.Closed);
    }

    [Fact]
    public async Task Status_carries_the_Pipeline_id()
    {
        var rig = new Rig();
        var (pipeline, _) = await rig.Open();

        Assert.Equal(pipeline.Id, pipeline.Status().Id);
    }
}

internal static class TaskExtensions
{
    public static void Ignore(this Task task) => _ = task;
}
