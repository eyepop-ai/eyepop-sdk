using System.Runtime.CompilerServices;
using System.Threading.Channels;
using EyePop.Protocol;

namespace EyePop;

/// <summary>
/// The handle of one Source: a demux of the Pipeline's socket by source id. It has one reader, and the
/// Pipeline reads the socket only while a Job is read, so a slow reader slows the server down.
/// </summary>
public sealed class Job : IAsyncDisposable
{
    internal const int BufferLimit = 256;

    private readonly Pipeline _owner;
    // Unbounded, but the Pipeline stops reading the socket while this holds BufferLimit messages: only the
    // Pipeline's own reconnecting and reconnected messages can go past it, and they are few.
    private readonly Channel<JobMessage> _queue = Channel.CreateUnbounded<JobMessage>(new UnboundedChannelOptions { SingleReader = true });
    private int _buffered;
    private int _taken;
    private int _abandoned;
    private Exception? _failure;

    internal Job(Pipeline owner) => _owner = owner;

    /// <summary>Chosen by the SDK, numbered per Pipeline, unique for the Pipeline's life.</summary>
    public string Id { get; internal set; } = "";

    internal int Buffered => Volatile.Read(ref _buffered);

    /// <summary>Nobody will read this Job again: it buffers nothing more and holds nobody else up.</summary>
    internal bool Abandoned => Volatile.Read(ref _abandoned) == 1;

    /// <summary>That source's start, prediction, dropped, usage and end, and the Pipeline's reconnecting and reconnected.</summary>
    /// <exception cref="InvalidOperationException">Messages or Predictions was already called: a Job has one reader.</exception>
    public IAsyncEnumerable<JobMessage> Messages()
    {
        TakeReader();
        return Read(default);
    }

    /// <summary>
    /// Every prediction of the source, selected ones included. Fails after the last prediction when the Job
    /// ends with an error or with end reason error.
    /// </summary>
    /// <exception cref="InvalidOperationException">Messages or Predictions was already called: a Job has one reader.</exception>
    public IAsyncEnumerable<Prediction> Predictions()
    {
        TakeReader();
        return ReadPredictions(default);
    }

    /// <summary>Sends stopSource. The Job ends with end reason stopped.</summary>
    public void Cancel() => _owner.Stop(this);

    public ValueTask DisposeAsync()
    {
        Cancel();
        Abandon();
        return default;
    }

    // A Job a caller walked away from would fill to the limit and stall the reader for every other Job.
    // Its end is still processed, so the source stops and its upload stream closes.
    private void Abandon()
    {
        Volatile.Write(ref _abandoned, 1);
        _owner.Wake();
    }

    // A second reader would see only part of the buffer, so it is refused at the call, not at the first read.
    private void TakeReader()
    {
        if (Interlocked.Exchange(ref _taken, 1) == 1)
        {
            throw new InvalidOperationException("a Job has one reader: messages() or predictions() was already called");
        }
    }

    private async IAsyncEnumerable<JobMessage> Read([EnumeratorCancellation] CancellationToken ct)
    {
        _owner.Pull(true);
        try
        {
            while (await _queue.Reader.WaitToReadAsync(ct).ConfigureAwait(false))
            {
                while (_queue.Reader.TryRead(out var message))
                {
                    if (Interlocked.Decrement(ref _buffered) == BufferLimit - 1)
                    {
                        _owner.Wake();
                    }
                    yield return message;
                }
            }
        }
        finally
        {
            _owner.Pull(false);
            Abandon();
        }
    }

    private async IAsyncEnumerable<Prediction> ReadPredictions([EnumeratorCancellation] CancellationToken ct)
    {
        await foreach (var message in Read(ct).WithCancellation(ct).ConfigureAwait(false))
        {
            if (message is PredictionMessage prediction)
            {
                yield return prediction.Prediction;
            }
            else if (message is End { Reason: EndReason.Error } end)
            {
                throw new EyePopException(ErrorKind.CommandRejected, end.Message ?? "the source ended with an error", error: "end_error");
            }
        }
    }

    // The three below run under the Pipeline's lock.

    internal void Enqueue(JobMessage message)
    {
        if (Abandoned)
        {
            return;
        }
        Interlocked.Increment(ref _buffered);
        _queue.Writer.TryWrite(message);
    }

    /// <summary>The caller's own stream failed: the Job ends with that exception once its source stops.</summary>
    internal void FailWith(Exception failure) => _failure ??= failure;

    internal void Complete(Exception? error) => _queue.Writer.TryComplete(_failure ?? error);
}
