using System.Text.Json.Nodes;
using EyePop.Core;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class PipelineTests
{
    private static readonly Source Url = new(new Media.Url("https://example.com/a.jpg"));
    private static readonly Source LiveUrl = new(new Media.Url("rtsp://example.com/cam"), new SourceOptions(Live: true));

    private static async Task<List<JobMessage>> Take(IAsyncEnumerator<JobMessage> messages, int count)
    {
        var taken = new List<JobMessage>();
        while (taken.Count < count && await messages.MoveNextAsync().AsTask().WaitAsync(TimeSpan.FromSeconds(5)))
        {
            taken.Add(messages.Current);
        }
        return taken;
    }

    private static string Type(JsonNode node) => node["type"]!.GetValue<string>();

    // Connect

    [Fact]
    public async Task Connect_sets_the_pop_and_returns_when_the_server_answers()
    {
        var rig = new Rig();
        var connecting = Pipeline.ConnectAsync(Rig.LocalConfig, Rig.EmptyPop, rig.Deps());
        var socket = await rig.Sockets.Socket(0);

        Assert.False(connecting.IsCompleted);
        await Rig.Answer(socket, "setPop");

        await using var pipeline = await connecting;
        Assert.Equal(PipelineState.Open, pipeline.Status().State);
        Assert.False(string.IsNullOrEmpty(pipeline.Id));
    }

    [Fact]
    public async Task Connect_exchanges_the_key_and_gives_the_token_to_the_socket()
    {
        var rig = new Rig();
        var connecting = Pipeline.ConnectAsync(Rig.LocalConfig, Rig.EmptyPop, rig.Deps(exchange: true));

        var socket = await rig.Sockets.Socket(0);
        await Rig.Answer(socket, "setPop");
        await using var pipeline = await connecting;

        Assert.Equal("jwt-1", socket.Jwt);
        Assert.Equal(1, rig.Exchange.Calls);
    }

    [Fact]
    public async Task Connect_fails_and_leaves_no_socket_when_the_server_refuses_the_pop()
    {
        var rig = new Rig();
        var connecting = Pipeline.ConnectAsync(Rig.LocalConfig, Rig.EmptyPop, rig.Deps());
        var socket = await rig.Sockets.Socket(0);
        var setPop = await socket.SentOfType("setPop");

        socket.Say(new { type = "error", id = Rig.Id(setPop), error = "bad_pop", message = "no" });

        var error = await Assert.ThrowsAsync<EyePopException>(() => connecting);
        Assert.Equal(ErrorKind.CommandRejected, error.Kind);
        Assert.Equal("bad_pop", error.Error);
        await Eventually.True(() => socket.Disposed);
    }

    [Fact]
    public async Task Connect_fails_with_exchange_failed_when_the_key_is_refused()
    {
        var rig = new Rig();
        rig.Exchange.FailNext(401);

        var error = await Assert.ThrowsAsync<EyePopException>(() =>
            Pipeline.ConnectAsync(Rig.LocalConfig, Rig.EmptyPop, rig.Deps(exchange: true)));

        Assert.Equal(ErrorKind.ExchangeFailed, error.Kind);
        Assert.Equal(401, error.Status);
        Assert.Empty(rig.Sockets.Opened);
    }

    [Fact]
    public async Task Connect_stops_and_cleans_up_when_cancelled_while_the_server_is_silent()
    {
        var rig = new Rig();
        using var cancel = new CancellationTokenSource();
        var connecting = Pipeline.ConnectAsync(Rig.LocalConfig, Rig.EmptyPop, rig.Deps(), cancel.Token);
        var socket = await rig.Sockets.Socket(0);
        await socket.SentOfType("setPop");

        cancel.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => connecting);
        await Eventually.True(() => socket.Disposed);
    }

    // Jobs

    [Fact]
    public async Task SetSource_returns_a_Job_at_once_and_the_Job_delivers_its_messages_in_order_until_end()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();

        var job = pipeline.SetSource(Url);
        var setSource = await socket.SentOfType("setSource");
        Assert.Equal(job.Id, Rig.Id(setSource));
        socket.Say(new { type = "start", id = job.Id });
        socket.Say(Rig.Prediction(job.Id, 1));
        socket.Say(new { type = "end", id = job.Id, reason = "eos" });

        var all = new List<JobMessage>();
        await foreach (var message in job.Messages()) all.Add(message);

        Assert.Equal(new[] { typeof(Start), typeof(PredictionMessage), typeof(End) }, all.Select(m => m.GetType()));
    }

    [Fact]
    public async Task Jobs_read_only_their_own_messages()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var first = pipeline.SetSource(Url);
        var second = pipeline.SetSource(Url);

        socket.Say(Rig.Prediction(second.Id, 2));
        socket.Say(new { type = "end", id = second.Id, reason = "eos" });
        socket.Say(Rig.Prediction(first.Id, 1));
        socket.Say(new { type = "end", id = first.Id, reason = "eos" });

        var firstPredictions = new List<Prediction>();
        await foreach (var p in first.Predictions()) firstPredictions.Add(p);
        Assert.Equal(1, Assert.Single(firstPredictions).Timestamp);
    }

    [Fact]
    public async Task Predictions_skips_every_message_but_predictions()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Url);
        socket.Say(new { type = "start", id = job.Id });
        socket.Say(Rig.Prediction(job.Id, 7));
        socket.Say(new { type = "usage", id = job.Id, milli_compute_units = 5 });
        socket.Say(new { type = "end", id = job.Id, reason = "eos" });

        var seen = new List<long?>();
        await foreach (var p in job.Predictions()) seen.Add(p.Timestamp);

        Assert.Equal(new long?[] { 7 }, seen);
    }

    [Fact]
    public async Task Predictions_fails_after_the_last_prediction_when_the_source_ends_with_reason_error()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Url);
        socket.Say(Rig.Prediction(job.Id, 7));
        socket.Say(new { type = "end", id = job.Id, reason = "error", message = "decode failed" });

        var seen = new List<long?>();
        var failure = await Assert.ThrowsAsync<EyePopException>(async () =>
        {
            await foreach (var p in job.Predictions()) seen.Add(p.Timestamp);
        });

        Assert.Equal(new long?[] { 7 }, seen);
        Assert.Equal(ErrorKind.CommandRejected, failure.Kind);
    }

    [Fact]
    public async Task A_second_reader_of_a_Job_is_a_misuse_not_an_Error()
    {
        var rig = new Rig();
        var (pipeline, _) = await rig.Open();
        var job = pipeline.SetSource(Url);
        _ = job.Messages();

        Assert.Throws<InvalidOperationException>(() => job.Messages());
        Assert.Throws<InvalidOperationException>(() => job.Predictions());
    }

    [Fact]
    public async Task A_refused_source_fails_its_Job_with_command_rejected_and_leaves_the_socket_open()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Url);
        socket.Say(new { type = "error", id = job.Id, error = "queue_full", message = "full" });

        var error = await Assert.ThrowsAsync<EyePopException>(async () => { await foreach (var _ in job.Messages()) { } });

        Assert.Equal(ErrorKind.CommandRejected, error.Kind);
        Assert.Equal("queue_full", error.Error);
        Assert.Equal(PipelineState.Open, pipeline.Status().State);
    }

    [Fact]
    public async Task Cancel_sends_stopSource_and_the_Job_ends_with_reason_stopped()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Url);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();

        job.Cancel();
        var stop = await socket.SentOfType("stopSource");
        socket.Say(new { type = "end", id = job.Id, reason = "stopped" });

        Assert.Equal(job.Id, Rig.Id(stop));
        Assert.True(await next);
        var end = Assert.IsType<End>(messages.Current);
        Assert.Equal(EndReason.Stopped, end.Reason);
        Assert.False(await messages.MoveNextAsync());
    }

    [Fact]
    public async Task Commands_complete_on_their_own_answer()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();

        var ping = pipeline.PingAsync();
        var graph = pipeline.GetGraphAsync(GraphFormat.Dot);
        var pingFrame = await socket.SentOfType("ping");
        var graphFrame = await socket.SentOfType("getGraph");
        Assert.False(ping.IsCompleted);
        socket.Say(new { type = "result", id = Rig.Id(graphFrame), graph = "digraph {}" });
        socket.Say(new { type = "pong", id = Rig.Id(pingFrame) });

        await ping;
        Assert.Equal("digraph {}", (await graph)["graph"]!.GetValue<string>());
        Assert.Equal("dot", graphFrame["format"]!.GetValue<string>());
    }

    // Backpressure

    [Fact]
    public async Task The_reader_does_not_read_while_nothing_is_pulled_and_no_command_waits()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Url);
        var before = socket.Received;
        for (var i = 0; i < 3; i++) socket.Say(Rig.Prediction(job.Id, i));

        await Eventually.Settle();

        Assert.Equal(before, socket.Received);
        var messages = job.Messages().GetAsyncEnumerator();
        Assert.Equal(3, (await Take(messages, 3)).Count);
        await messages.DisposeAsync();
    }

    [Fact]
    public async Task A_Job_nobody_reads_stalls_the_reader_at_256_buffered_messages_and_resumes_when_read_with_nothing_dropped()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var pulled = pipeline.SetSource(Url);
        var stalled = pipeline.SetSource(Url);
        var pulledMessages = pulled.Messages().GetAsyncEnumerator();
        var pulling = pulledMessages.MoveNextAsync().AsTask();
        var before = socket.Received;
        for (var i = 0; i < 300; i++) socket.Say(Rig.Prediction(stalled.Id, i));

        await Eventually.True(() => socket.Received - before == 256);
        await Eventually.Settle();
        Assert.Equal(256, socket.Received - before);

        var timestamps = new List<long?>();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await foreach (var p in stalled.Predictions().WithCancellation(timeout.Token))
        {
            timestamps.Add(p.Timestamp);
            if (timestamps.Count == 300) break;
        }
        Assert.Equal(Enumerable.Range(0, 300).Select(i => (long?)i), timestamps);
        Assert.Equal(300, socket.Received - before);
        socket.Say(Rig.Prediction(pulled.Id, 1));
        Assert.True(await pulling);
    }

    // Supervision

    [Fact]
    public async Task A_reconnect_replays_the_pop_then_every_unended_source_with_its_id_and_the_Job_sees_reconnecting_and_reconnected()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(Url);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        var firstSetSource = await first.SentOfType("setSource");

        first.Close(1001, "going away");
        Assert.True(await next);
        var reconnecting = Assert.IsType<Reconnecting>(messages.Current);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        var replayedPop = await second.SentOfType("setPop");
        var replayedSource = await second.SentOfType("setSource");
        await Rig.Answer(second, "setPop");

        Assert.Equal(ErrorKind.Closed, reconnecting.Cause.Kind);
        Assert.Equal(1001, reconnecting.Cause.CloseCode);
        Assert.Equal(Rig.Id(firstSetSource), Rig.Id(replayedSource));
        Assert.Equal(new[] { "setPop", "setSource" }, second.SentJson.Select(Type).ToArray());
        Assert.NotEqual(Rig.Id(replayedPop), Rig.Id(replayedSource));
        Assert.IsType<Reconnected>((await Take(messages, 1)).Single());
        Assert.True(first.Disposed);
        Assert.Equal(1, pipeline.Status().Reconnects);
    }

    [Fact]
    public async Task A_message_from_the_old_socket_is_not_delivered_after_the_reconnect_began()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(Url);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        first.Close(1001, "going away");
        first.Say(Rig.Prediction(job.Id, 99));

        Assert.True(await next);
        Assert.IsType<Reconnecting>(messages.Current);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        await Rig.Answer(second, "setPop");
        var rest = await Take(messages, 1);

        Assert.IsType<Reconnected>(rest.Single());
    }

    [Fact]
    public async Task Close_1008_credential_expired_exchanges_the_key_again_and_reconnects_at_once()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open(exchange: true);
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();

        first.Close(1008, "credential_expired");

        var second = await rig.Sockets.Socket(1);
        Assert.Equal("jwt-2", second.Jwt);
        Assert.Equal(2, rig.Exchange.Calls);
        Assert.True(await next);
    }

    [Fact]
    public async Task A_token_with_less_than_60_seconds_left_is_exchanged_again_before_a_reconnect()
    {
        var rig = new Rig { };
        rig.Exchange.Lifetime = TimeSpan.FromSeconds(100);
        var (pipeline, first) = await rig.Open(exchange: true);
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await rig.Elapse(TimeSpan.FromSeconds(50));

        first.Close(1001, "going away");
        Assert.True(await next);
        await rig.AdvanceUntilConnect();

        var second = await rig.Sockets.Socket(1);
        Assert.Equal("jwt-2", second.Jwt);
    }

    [Fact]
    public async Task A_token_with_time_left_is_kept_across_a_reconnect()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open(exchange: true);
        var job = pipeline.SetSource(LiveUrl);
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();

        first.Close(1001, "going away");
        await next;
        await rig.AdvanceUntilConnect();

        var second = await rig.Sockets.Socket(1);
        Assert.Equal("jwt-1", second.Jwt);
        Assert.Equal(1, rig.Exchange.Calls);
    }

    [Fact]
    public async Task An_upgrade_503_waits_at_least_Retry_After_before_the_next_attempt()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        rig.Sockets.FailNext(503, TimeSpan.FromSeconds(30));
        first.Close(1001, "going away");
        await next;
        await rig.AdvanceUntilConnect();
        await Eventually.True(() => rig.Sockets.Attempts == 2);

        await Eventually.True(() => rig.Time.HasTimerWithin(TimeSpan.FromSeconds(31)));
        rig.Time.Advance(TimeSpan.FromSeconds(29));
        await Eventually.Settle();

        Assert.Equal(2, rig.Sockets.Attempts);
        rig.Time.Advance(TimeSpan.FromSeconds(31));
        var second = await rig.Sockets.Socket(1);
        Assert.NotNull(second);
        Assert.Equal(3, rig.Sockets.Attempts);
    }

    [Fact]
    public async Task An_exchange_refused_with_403_ends_every_Job_with_exchange_failed_and_the_Pipeline_goes_idle()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open(exchange: true);
        var job = pipeline.SetSource(Url);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        rig.Exchange.FailNext(403);
        first.Close(1008, "credential_expired");

        Assert.True(await next);
        Assert.IsType<Reconnecting>(messages.Current);
        var error = await Assert.ThrowsAsync<EyePopException>(async () => await messages.MoveNextAsync());

        Assert.Equal(ErrorKind.ExchangeFailed, error.Kind);
        Assert.Equal(403, error.Status);
        Assert.Equal(PipelineState.Idle, pipeline.Status().State);
        Assert.Equal(ErrorKind.ExchangeFailed, pipeline.Status().LastError!.Kind);
    }

    [Fact]
    public async Task A_socket_silent_for_60_seconds_is_probed_with_a_ping_then_closed_and_reconnected()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        await rig.Elapse(TimeSpan.FromSeconds(31));
        var probe = await first.SentOfType("ping");
        await rig.Elapse(TimeSpan.FromSeconds(31));

        Assert.True(await next);
        await rig.AdvanceUntilConnect();
        var second = await rig.Sockets.Socket(1);
        Assert.NotNull(second);
        Assert.Equal("liveness", Rig.Id(probe));
        Assert.True(first.Disposed);
    }

    [Fact]
    public async Task Any_message_after_the_probe_keeps_the_socket()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();
        await rig.Elapse(TimeSpan.FromSeconds(31));
        await first.SentOfType("ping");

        first.Say(new { type = "pong", id = "liveness" });
        first.Say(Rig.Prediction(job.Id, 1));
        await rig.Elapse(TimeSpan.FromSeconds(31));
        await Eventually.Settle();

        Assert.True(await next);
        Assert.Single(rig.Sockets.Opened);
    }

    [Fact]
    public async Task A_close_the_SDK_cannot_retry_ends_every_Job_in_flight_with_closed_and_its_code()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var a = pipeline.SetSource(Url);
        var b = pipeline.SetSource(Url);
        var aMessages = a.Messages().GetAsyncEnumerator();
        var next = aMessages.MoveNextAsync().AsTask();

        socket.Close(1008, "unexpected_bytes");

        var error = await Assert.ThrowsAsync<EyePopException>(() => next);
        Assert.Equal(ErrorKind.Closed, error.Kind);
        Assert.Equal(1008, error.CloseCode);
        var other = await Assert.ThrowsAsync<EyePopException>(async () => { await foreach (var _ in b.Messages()) { } });
        Assert.Equal(1008, other.CloseCode);
        Assert.Equal(PipelineState.Idle, pipeline.Status().State);
    }

    [Fact]
    public async Task An_idle_Pipeline_has_no_socket_and_the_next_command_opens_one_and_sets_the_pop_again()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(Url);
        var messages = job.Messages().GetAsyncEnumerator();
        var started = messages.MoveNextAsync().AsTask();
        first.Say(new { type = "end", id = job.Id, reason = "eos" });
        first.Close(1000, "idle");
        Assert.True(await started);
        await Eventually.True(() => pipeline.Status().State == PipelineState.Idle);
        await messages.DisposeAsync();

        var second = pipeline.SetSource(Url);

        var socket = await rig.Sockets.Socket(1);
        Assert.Equal(new[] { "setPop", "setSource" }, (await Eventually.Sent(socket, 2)).Select(Type).ToArray());
        Assert.Equal(second.Id, Rig.Id(socket.SentJson.Last()));
        Assert.True(first.Disposed);
    }

    [Fact]
    public async Task A_malformed_frame_is_skipped_and_counted_and_the_socket_stays_open()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(Url);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();

        socket.Say("not json");
        socket.Say(Rig.Prediction(job.Id, 5));

        Assert.True(await next);
        Assert.Equal(1, pipeline.Status().Malformed);
        Assert.NotNull(pipeline.Status().LastMalformed);
        Assert.Equal(PipelineState.Open, pipeline.Status().State);
    }

    [Fact]
    public async Task An_error_with_no_id_goes_to_status_and_no_Job()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var ping = pipeline.PingAsync();
        socket.Say(new { type = "error", error = "internal", message = "oops" });
        await Rig.Answer(socket, "ping");
        var pong = await socket.SentOfType("ping");
        socket.Say(new { type = "pong", id = Rig.Id(pong) });
        await ping;

        Assert.Equal("internal", pipeline.Status().LastError!.Error);
    }

    // Closing

    [Fact]
    public async Task Close_sends_quit_ends_every_Job_normally_closes_the_socket_and_refuses_later_commands()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var messages = job.Messages().GetAsyncEnumerator();
        var next = messages.MoveNextAsync().AsTask();

        await pipeline.CloseAsync();

        Assert.False(await next);
        Assert.Contains(socket.SentJson, j => Type(j) == "quit");
        Assert.True(socket.Disposed);
        Assert.Equal(PipelineState.Closed, pipeline.Status().State);
        var error = await Assert.ThrowsAsync<EyePopException>(() => pipeline.PingAsync());
        Assert.Equal(ErrorKind.Closed, error.Kind);
        var late = await Assert.ThrowsAsync<EyePopException>(async () => { await foreach (var _ in pipeline.SetSource(Url).Messages()) { } });
        Assert.Equal(ErrorKind.Closed, late.Kind);
    }

    [Fact]
    public async Task Close_during_a_backoff_cancels_the_waiting_connect()
    {
        var rig = new Rig();
        var (pipeline, first) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        first.Close(1001, "going away");
        await next;
        await Eventually.True(() => pipeline.Status().State == PipelineState.BackingOff);

        await pipeline.CloseAsync();
        rig.Time.Advance(TimeSpan.FromMinutes(2));
        await Eventually.Settle();

        Assert.Single(rig.Sockets.Opened);
    }

    [Fact]
    public async Task A_socket_that_opens_after_Close_is_closed_again()
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

        var late = await rig.Sockets.Socket(0);
        await Eventually.True(() => late.Disposed);
        Assert.Empty(late.Sent);
    }

    // Uploads

    [Fact]
    public async Task An_upload_stream_of_known_length_within_8_MiB_goes_as_one_combined_frame()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var content = UploadContent.FromStream(() => new MemoryStream(new byte[] { 1, 2, 3, 4 }), 4);

        pipeline.SetSource(new Source(new Media.Upload("image/jpeg", content)));

        await Eventually.True(() => socket.Sent.OfType<BinaryFrame>().Any());
        var frame = socket.Sent.OfType<BinaryFrame>().Single();
        Assert.Equal(0x02, frame.Bytes.Span[0]);
        Assert.Equal(new byte[] { 1, 2, 3, 4 }, frame.Bytes.Span[^4..].ToArray());
    }

    [Fact]
    public async Task A_chunked_upload_sends_at_most_64_KiB_per_frame_under_credit_then_uploaded()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var content = UploadContent.FromStream(() => new MemoryStream(new byte[100_000]));
        var job = pipeline.SetSource(new Source(new Media.Upload("video/mp4", content)));
        _ = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();
        var header = await socket.SentOfType("setSource");
        Assert.Equal(job.Id, Rig.Id(header));
        Assert.Empty(socket.Sent.OfType<BinaryFrame>());

        socket.Say(new { type = "send", id = job.Id, credit = 70_000 });
        await Eventually.True(() => socket.Sent.OfType<BinaryFrame>().Count() == 2);
        socket.Say(new { type = "credit", id = job.Id, bytes = 40_000 });

        var uploaded = await socket.SentOfType("uploaded");
        var sizes = socket.Sent.OfType<BinaryFrame>().Select(f => f.Bytes.Length - 1).ToArray();
        Assert.Equal(job.Id, Rig.Id(uploaded));
        Assert.Equal(new[] { 65_536, 4_464, 30_000 }, sizes);
        Assert.All(socket.Sent.OfType<BinaryFrame>(), f => Assert.Equal(0x01, f.Bytes.Span[0]));
        Assert.Equal("uploaded", Type(socket.SentJson.Last()));
    }

    [Fact]
    public async Task An_upload_whose_stream_cannot_be_read_stops_its_source_and_fails_its_Job_with_that_error()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var content = UploadContent.FromStream(() => throw new IOException("disk gone"), 10);

        var job = pipeline.SetSource(new Source(new Media.Upload("image/jpeg", content)));
        var stop = await socket.SentOfType("stopSource");
        socket.Say(new { type = "end", id = job.Id, reason = "stopped" });

        var error = await Assert.ThrowsAsync<IOException>(async () => { await foreach (var _ in job.Messages()) { } });
        Assert.Equal("disk gone", error.Message);
        Assert.Equal(job.Id, Rig.Id(stop));
    }

    // Soak

    [Fact]
    public async Task Many_reconnects_leave_one_open_socket_and_a_flat_number_of_background_tasks()
    {
        var rig = new Rig();
        var (pipeline, socket) = await rig.Open();
        var job = pipeline.SetSource(LiveUrl);
        var next = job.Messages().GetAsyncEnumerator().MoveNextAsync().AsTask();

        for (var i = 1; i <= 25; i++)
        {
            socket.Close(1001, "going away");
            await rig.AdvanceUntilConnect();
            socket = await rig.Sockets.Socket(i);
            await Rig.Answer(socket, "setPop");
        }

        await Eventually.Settle();
        Assert.Equal(26, rig.Sockets.Opened.Count);
        Assert.Equal(25, rig.Sockets.Opened.Count(s => s.Disposed));
        Assert.InRange(pipeline.BackgroundTasks, 0, 4);
        Assert.Equal(25, pipeline.Status().Reconnects);
        Assert.True(await next);
    }
}
