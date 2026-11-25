using System.Text.Json.Nodes;
using System.Threading.Channels;
using EyePop.Core;
using EyePop.Protocol;

namespace EyePop;

public enum PipelineState { Connecting, Open, BackingOff, Idle, Closed }

public enum GraphFormat { Dot, Png, Pdf }

/// <summary>
/// What <see cref="Pipeline.Status"/> reports. Reconnects counts every attempt that followed a failure, failed attempts included.
/// The malformed frames are the ones the SDK skipped.
/// </summary>
public sealed record PipelineStatus(string Id, PipelineState State, int Reconnects, EyePopException? LastError, int Malformed, string? LastMalformed);

/// <summary>
/// One pop and its sources, over one socket at a time. It outlives its socket: when one fails for a reason a
/// retry can fix, it opens another and replays its state. The decisions are all in the pure core
/// (<see cref="Machine.Step"/>); this class feeds it inputs under one lock and applies its outputs in order.
/// </summary>
public sealed class Pipeline : IAsyncDisposable
{
    private static readonly TimeSpan TokenMargin = TimeSpan.FromSeconds(60);

    private readonly object _lock = new();
    private readonly Config _config;
    private readonly Dependencies _deps;
    private readonly CancellationTokenSource _lifetime = new();
    private CancellationTokenSource _timers;
    private readonly HashSet<Task> _tasks = new();
    private readonly Dictionary<string, TaskCompletionSource<JsonNode>> _commands = new();
    private readonly Dictionary<string, Job> _jobs = new();
    private readonly Dictionary<int, UploadReader> _uploads = new();

    private State _state;
    private Link? _link;
    private Token? _token;
    private CancellationTokenSource? _connectCts;
    private int _connectId;
    private bool _backingOff;
    private int _pulling;
    private TaskCompletionSource _wake = NewWake();
    private bool _closing;
    private bool _disposed;

    private int _reconnects;
    private int _malformed;
    private string? _lastMalformed;
    private EyePopException? _lastError;

    private Pipeline(Config config, Dependencies deps)
    {
        _config = config;
        _deps = deps;
        _state = State.Initial(deps.Settings);
        _timers = CancellationTokenSource.CreateLinkedTokenSource(_lifetime.Token);
        Id = Guid.NewGuid().ToString();
    }

    /// <summary>Made by the SDK when the Pipeline opens. It stays the same across reconnects.</summary>
    public string Id { get; }

    /// <summary>
    /// Opens the socket, sets the pop and returns when the server has applied it. Failures a retry can fix
    /// are retried until <paramref name="ct"/> is cancelled. A failure that cannot be fixed, or a cancelled
    /// call, closes the Pipeline before it is thrown.
    /// </summary>
    public static Task<Pipeline> ConnectAsync(Config config, Pop pop, CancellationToken ct = default) =>
        ConnectAsync(config, pop, Dependencies.For(config), ct);

    internal static async Task<Pipeline> ConnectAsync(Config config, Pop pop, Dependencies deps, CancellationToken ct = default)
    {
        var pipeline = new Pipeline(config, deps);
        try
        {
            await pipeline.SetPopAsync(pop, ct).ConfigureAwait(false);
            return pipeline;
        }
        catch
        {
            await pipeline.CloseAsync().ConfigureAwait(false);
            throw;
        }
    }

    // Commands from the caller

    /// <summary>Returns the Job at once, without waiting for the server. Every outcome of the source goes through the Job.</summary>
    public Job SetSource(Source source)
    {
        var job = new Job(this);
        lock (_lock)
        {
            Apply(new Input.SetSource(source), id =>
            {
                job.Id = id;
                _jobs[id] = job;
            });
        }
        return job;
    }

    /// <summary>Completes when the server answers. If it fails, the Pipeline keeps the last pop that applied.</summary>
    public async Task SetPopAsync(Pop pop, CancellationToken ct = default) =>
        await CommandAsync(new Input.SetPop(pop), ct).ConfigureAwait(false);

    /// <summary>The server's answer, as raw JSON.</summary>
    public Task<JsonNode> GetGraphAsync(GraphFormat format, bool? verbose = null, CancellationToken ct = default) =>
        CommandAsync(new Input.GetGraph(ToCore(format), verbose), ct);

    public async Task PingAsync(CancellationToken ct = default) =>
        await CommandAsync(new Input.Ping(), ct).ConfigureAwait(false);

    public PipelineStatus Status()
    {
        lock (_lock)
        {
            var state = _state.Phase switch
            {
                Phase.Open => PipelineState.Open,
                Phase.Closed => PipelineState.Closed,
                Phase.Connecting => _backingOff ? PipelineState.BackingOff : PipelineState.Connecting,
                _ => PipelineState.Idle,
            };
            return new PipelineStatus(Id, state, _reconnects, _lastError, _malformed, _lastMalformed);
        }
    }

    /// <summary>Sends quit, ends every Job normally and stops reconnecting. Only this ends a Pipeline.</summary>
    public async Task CloseAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (!_closing)
            {
                _closing = true;
                Apply(new Input.Quit());
                _lifetime.Cancel();
            }
        }
        // Looped, because a task that was starting when the snapshot was taken is waited for by the next one.
        while (true)
        {
            Task[] tasks;
            lock (_lock)
            {
                tasks = _tasks.ToArray();
            }
            if (tasks.Length == 0)
            {
                break;
            }
            await Task.WhenAll(tasks).WaitAsync(ct).ConfigureAwait(false);
        }
        lock (_lock)
        {
            if (!_disposed)
            {
                _disposed = true;
                _timers.Dispose();
                _lifetime.Dispose();
            }
        }
    }

    public ValueTask DisposeAsync() => new(CloseAsync());

    /// <summary>How many background tasks run now. The soak test checks it stays flat across reconnects.</summary>
    internal int BackgroundTasks
    {
        get
        {
            lock (_lock)
            {
                return _tasks.Count;
            }
        }
    }

    private static GetGraphFormat ToCore(GraphFormat format) => format switch
    {
        GraphFormat.Dot => GetGraphFormat.Dot,
        GraphFormat.Png => GetGraphFormat.Png,
        GraphFormat.Pdf => GetGraphFormat.Pdf,
        _ => throw new ArgumentOutOfRangeException(nameof(format)),
    };

    private Task<JsonNode> CommandAsync(Input command, CancellationToken ct)
    {
        var answer = new TaskCompletionSource<JsonNode>(TaskCreationOptions.RunContinuationsAsynchronously);
        lock (_lock)
        {
            Apply(command, id => _commands[id] = answer);
        }
        return answer.Task.WaitAsync(ct);
    }

    // What Job calls

    internal void Stop(Job job)
    {
        lock (_lock)
        {
            Apply(new Input.StopSource(job.Id));
        }
    }

    internal void Pull(bool pulling)
    {
        lock (_lock)
        {
            _pulling += pulling ? 1 : -1;
            Signal();
        }
    }

    internal void Wake()
    {
        lock (_lock)
        {
            Signal();
        }
    }

    // The loop: one input in, outputs applied in order. Always under _lock.

    private void Apply(Input input, Action<string>? issued = null)
    {
        var (state, outputs) = Machine.Step(_state, input, new Moment(_deps.Time.GetUtcNow(), _deps.Random()));
        _state = state;
        if (input is Input.Failed && outputs.Any(o => o is Output.Connect))
        {
            _reconnects++;
        }
        foreach (var output in outputs)
        {
            Handle(output, issued);
        }
        Signal();
    }

    private void Handle(Output output, Action<string>? issued)
    {
        switch (output)
        {
            case Output.Issued i:
                issued?.Invoke(i.Id);
                break;
            case Output.Send send:
                _link!.Outbox.Writer.TryWrite(send.Frame);
                break;
            case Output.Deliver deliver:
                if (_jobs.TryGetValue(deliver.JobId, out var target))
                {
                    if (deliver.Message is Reconnecting reconnecting)
                    {
                        _lastError = reconnecting.Cause;
                    }
                    target.Enqueue(deliver.Message);
                }
                break;
            case Output.CloseJob close:
                if (_jobs.Remove(close.JobId, out var closed))
                {
                    _lastError = close.Error ?? _lastError;
                    closed.Complete(close.Error);
                }
                DisposeUploads(close.JobId);
                break;
            case Output.Completed completed:
                if (_commands.Remove(completed.CommandId, out var answer))
                {
                    answer.TrySetResult(completed.Result);
                }
                break;
            case Output.CommandFailed failed:
                _lastError = failed.Error;
                if (_commands.Remove(failed.CommandId, out var refused))
                {
                    refused.TrySetException(failed.Error);
                }
                break;
            case Output.Connect connect:
                RenewTimers();
                StartConnect(connect);
                break;
            case Output.CloseSocket:
                RetireLink(graceful: false);
                break;
            case Output.GoIdle:
                RenewTimers();
                CancelConnect();
                RetireLink(graceful: true);
                break;
            case Output.ScheduleResend resend:
                var timers = _timers.Token;
                Spawn(() => ResendLater(resend, timers));
                break;
            case Output.ReadUpload read:
                Spawn(() => ReadUpload(read));
                break;
            case Output.Status status:
                _lastError = status.Error;
                break;
        }
    }

    // The reader runs only while a Job is pulled or a command awaits its answer, and never while a Job
    // holds a full buffer.
    private bool Wanted() =>
        (_commands.Count > 0 || _pulling > 0) && !_jobs.Values.Any(job => !job.Abandoned && job.Buffered >= Job.BufferLimit);

    private static TaskCompletionSource NewWake() => new(TaskCreationOptions.RunContinuationsAsynchronously);

    private void Signal()
    {
        var woken = _wake;
        _wake = NewWake();
        woken.TrySetResult();
    }

    private async Task AwaitDemand(CancellationToken ct)
    {
        while (true)
        {
            Task changed;
            lock (_lock)
            {
                if (Wanted())
                {
                    return;
                }
                changed = _wake.Task;
            }
            await changed.WaitAsync(ct).ConfigureAwait(false);
        }
    }

    // Connecting

    private void StartConnect(Output.Connect connect)
    {
        _connectCts?.Cancel();
        var id = ++_connectId;
        var cts = CancellationTokenSource.CreateLinkedTokenSource(_lifetime.Token);
        _connectCts = cts;
        _backingOff = connect.Delay > TimeSpan.Zero;
        Spawn(() => RunConnect(id, connect, cts));
    }

    private void CancelConnect()
    {
        _connectCts?.Cancel();
        _connectId++;
        _backingOff = false;
    }

    private async Task RunConnect(int id, Output.Connect connect, CancellationTokenSource cts)
    {
        var ct = cts.Token;
        try
        {
            if (connect.Delay > TimeSpan.Zero)
            {
                await Task.Delay(connect.Delay, _deps.Time, ct).ConfigureAwait(false);
                lock (_lock)
                {
                    _backingOff = _backingOff && _connectId != id;
                }
            }
            var jwt = await CurrentJwt(id, connect.ForceExchange, ct).ConfigureAwait(false);
            if (jwt.Failed)
            {
                return;
            }
            var socket = await OpenSocket(id, jwt.Value, ct).ConfigureAwait(false);
            if (socket is not null && !Attach(id, socket))
            {
                // Awaited here, so CloseAsync returns only after a socket that arrived too late is closed.
                await socket.DisposeAsync().ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
        }
        catch (Exception) when (!ct.IsCancellationRequested)
        {
            // Something the transport should not throw: the attempt failed, and a retry may work.
            Fail(id, new Failure.Upgrade(null));
        }
        finally
        {
            // Forget it before disposing, so a later cancel never meets a disposed source.
            lock (_lock)
            {
                if (_connectCts == cts)
                {
                    _connectCts = null;
                }
            }
            cts.Dispose();
        }
    }

    // Null: the attempt failed and was reported.
    private async Task<ISocket?> OpenSocket(int id, string? jwt, CancellationToken ct)
    {
        using var timeout = new CancellationTokenSource(_deps.UpgradeTimeout, _deps.Time);
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(ct, timeout.Token);
        try
        {
            return await _deps.Sockets.ConnectAsync(_config.PipelineUrl, jwt, linked.Token).ConfigureAwait(false);
        }
        catch (UpgradeException e)
        {
            Fail(id, new Failure.Upgrade(e.Status, e.RetryAfter));
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            Fail(id, new Failure.Upgrade(null));
        }
        return null;
    }

    private async Task<(string? Value, bool Failed)> CurrentJwt(int id, bool force, CancellationToken ct)
    {
        if (_deps.Exchange is not { } exchange)
        {
            return (null, false);
        }
        Token? token;
        lock (_lock)
        {
            token = _token;
        }
        if (force || token is null || token.ExpiresAt - _deps.Time.GetUtcNow() < TokenMargin)
        {
            try
            {
                token = await exchange.ExchangeAsync(ct).ConfigureAwait(false);
            }
            catch (ExchangeException e)
            {
                Fail(id, new Failure.Exchange(e.Status, e.RetryAfter));
                return (null, true);
            }
            lock (_lock)
            {
                _token = token;
            }
        }
        return (token.Jwt, false);
    }

    // A failure of an attempt that a newer attempt, close() or idle has already replaced is ignored.
    private void Fail(int connectId, Failure failure)
    {
        lock (_lock)
        {
            if (_connectId == connectId)
            {
                Apply(new Input.Failed(failure));
            }
        }
    }

    // False: the attempt was replaced or the Pipeline closed, and the caller closes the socket.
    private bool Attach(int connectId, ISocket socket)
    {
        lock (_lock)
        {
            if (_connectId != connectId)
            {
                return false;
            }
            _backingOff = false;
            var link = new Link(socket);
            _link = link;
            Apply(new Input.Opened());
            Spawn(() => ReadLoop(link));
            Spawn(() => WriteLoop(link));
            return true;
        }
    }

    // The socket

    private void RetireLink(bool graceful)
    {
        DisposeUploads();
        if (_link is not { } link)
        {
            return;
        }
        _link = null;
        // A graceful retire lets quit go out before the socket closes, but only for so long: a server that
        // stopped reading would otherwise hold Close forever. A socket already reported dead has nothing to flush.
        graceful &= !link.Dead;
        link.Dead = true;
        link.CancelRead();
        link.Outbox.Writer.TryComplete();
        if (graceful)
        {
            link.StartDrain(_deps.Time, _deps.DrainLimit);
        }
        else
        {
            link.CancelWrite();
        }
    }

    // The first failure of a socket counts; the old socket's later ones do not.
    private void Report(Link link, Failure failure)
    {
        lock (_lock)
        {
            if (link.Dead || _link != link)
            {
                return;
            }
            link.Dead = true;
            Apply(new Input.Failed(failure));
        }
    }

    private async Task ReadLoop(Link link)
    {
        var ct = link.ReadCts.Token;
        try
        {
            while (true)
            {
                await AwaitDemand(ct).ConfigureAwait(false);
                var inbound = await ReceiveWithinWindow(link, ct).ConfigureAwait(false);
                switch (inbound)
                {
                    case null:
                        Report(link, Failure.Silent);
                        return;
                    case Inbound.Closed closed:
                        Report(link, new Failure.SocketClosed(closed.Code, closed.Reason));
                        return;
                    case Inbound.Message message:
                        Receive(link, message.Frame);
                        break;
                }
            }
        }
        catch (OperationCanceledException)
        {
        }
        finally
        {
            link.Release();
        }
    }

    // Null: the liveness window passed with no message. Time spent waiting for demand does not count.
    // The socket honours the token, so a cancelled read ends by itself; the wait below is for silence only.
    // The client socket answers the server's pings inside the transport and never shows them, so a quiet
    // healthy socket cannot be told from a dead one by waiting. Halfway through the window the shell asks
    // with a ping of its own: any message, the pong included, proves the socket alive.
    private async Task<Inbound?> ReceiveWithinWindow(Link link, CancellationToken ct)
    {
        var half = _deps.Liveness / 2;
        using var received = CancellationTokenSource.CreateLinkedTokenSource(ct);
        var receiving = link.Socket.ReceiveAsync(received.Token);
        foreach (var probe in new[] { true, false })
        {
            try
            {
                return await receiving.WaitAsync(half, _deps.Time).ConfigureAwait(false);
            }
            catch (TimeoutException)
            {
                if (probe)
                {
                    lock (_lock)
                    {
                        link.Outbox.Writer.TryWrite(FrameCodec.Encode(new Ping("liveness")));
                    }
                }
            }
        }
        // A message that arrived as the window closed is still a message.
        received.Cancel();
        try
        {
            return await receiving.ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            return null;
        }
    }

    private void Receive(Link link, Frame frame)
    {
        var decoded = FrameCodec.Decode(frame);
        lock (_lock)
        {
            if (link.Dead || _link != link)
            {
                return;
            }
            switch (decoded)
            {
                case Decoded.Ok ok:
                    Apply(new Input.Received(ok.Message));
                    break;
                case Malformed malformed:
                    _malformed++;
                    _lastMalformed = malformed.Reason;
                    break;
            }
        }
    }

    private async Task WriteLoop(Link link)
    {
        try
        {
            await foreach (var frame in link.Outbox.Reader.ReadAllAsync(link.WriteCts.Token).ConfigureAwait(false))
            {
                await link.Socket.SendAsync(frame, link.WriteCts.Token).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (IOException)
        {
            Report(link, new Failure.SocketClosed(null, null));
        }
        finally
        {
            await link.Socket.DisposeAsync().ConfigureAwait(false);
            link.Release();
        }
    }

    // Timers and uploads

    // Connecting and going idle both end whatever resend was waiting: the sources are sent again, or not at all, by the core.
    private void RenewTimers()
    {
        _timers.Cancel();
        _timers.Dispose();
        _timers = CancellationTokenSource.CreateLinkedTokenSource(_lifetime.Token);
    }

    private async Task ResendLater(Output.ScheduleResend resend, CancellationToken ct)
    {
        try
        {
            await Task.Delay(resend.Delay, _deps.Time, ct).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            return;
        }
        lock (_lock)
        {
            Apply(new Input.ResendDue(resend.Id));
        }
    }

    private async Task ReadUpload(Output.ReadUpload read)
    {
        if (ReaderFor(read) is not { } reader)
        {
            return;
        }
        try
        {
            var (data, last) = await reader.ReadAsync(read.Count, read.Whole, _lifetime.Token).ConfigureAwait(false);
            lock (_lock)
            {
                if (last || read.Whole)
                {
                    Forget(read.Token, reader);
                }
                // The answer to a read for a socket that has been replaced is not for the new one.
                if (read.Epoch == _state.Epoch)
                {
                    Apply(new Input.UploadRead(read.Epoch, read.Id, read.Token, read.Member, data, last || read.Whole));
                }
            }
        }
        catch (OperationCanceledException) when (_lifetime.IsCancellationRequested)
        {
        }
        catch (Exception e) when (!_lifetime.IsCancellationRequested)
        {
            // The caller's stream threw: whatever it threw, including its own cancellation and timeouts.
            UploadFailed(read, e);
        }
    }

    // Null: the read is for a socket that is gone, and nothing is opened for it.
    private UploadReader? ReaderFor(Output.ReadUpload read)
    {
        lock (_lock)
        {
            if (read.Epoch != _state.Epoch || _state.Phase != Phase.Open)
            {
                return null;
            }
            if (!_uploads.TryGetValue(read.Token, out var reader))
            {
                reader = new UploadReader(read.Id, read.Content);
                _uploads[read.Token] = reader;
            }
            return reader;
        }
    }

    // Only the reader that was stored under the token may remove it.
    private void Forget(int token, UploadReader reader)
    {
        if (_uploads.TryGetValue(token, out var stored) && ReferenceEquals(stored, reader))
        {
            _uploads.Remove(token);
        }
        reader.Dispose();
    }

    // The caller's stream failed. The server holds a half-sent upload, so the source is stopped, and its Job
    // ends with the caller's own exception. A read that fails because its socket closed is not a failure.
    private void UploadFailed(Output.ReadUpload read, Exception failure)
    {
        lock (_lock)
        {
            if (read.Epoch != _state.Epoch || _state.Phase != Phase.Open)
            {
                return;
            }
            if (_jobs.TryGetValue(read.Id, out var job))
            {
                job.FailWith(failure);
            }
            Apply(new Input.StopSource(read.Id));
            DisposeUploads(read.Id);
        }
    }

    private void DisposeUploads(string? jobId = null)
    {
        foreach (var (token, reader) in _uploads.Where(u => jobId is null || u.Value.JobId == jobId).ToList())
        {
            Forget(token, reader);
        }
    }

    // Starts background work that CloseAsync waits for. Always under _lock, but the work never runs inside it.
    private void Spawn(Func<Task> work)
    {
        var start = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Task? task = null;
        task = Task.Run(async () =>
        {
            await start.Task.ConfigureAwait(false);
            try
            {
                await work().ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception) when (!_lifetime.IsCancellationRequested)
            {
                // A bug in a transport or a stream must not leave the Pipeline waiting on work that died.
                lock (_lock)
                {
                    Apply(new Input.Failed(new Failure.Upgrade(null)));
                }
            }
            finally
            {
                lock (_lock)
                {
                    _tasks.Remove(task!);
                }
            }
        });
        _tasks.Add(task);
        start.SetResult();
    }

    private sealed class Link(ISocket socket)
    {
        private int _live = 2;
        private bool _released;
        private ITimer? _drain;

        public ISocket Socket { get; } = socket;
        public Channel<Frame> Outbox { get; } = Channel.CreateUnbounded<Frame>(new UnboundedChannelOptions { SingleReader = true });
        public CancellationTokenSource ReadCts { get; } = new();
        public CancellationTokenSource WriteCts { get; } = new();

        /// <summary>Failed or retired. Under the Pipeline's lock.</summary>
        public bool Dead { get; set; }

        public void CancelRead() => Guarded(ReadCts.Cancel);

        public void CancelWrite() => Guarded(WriteCts.Cancel);

        public void StartDrain(TimeProvider time, TimeSpan limit) =>
            Guarded(() => _drain = time.CreateTimer(_ => CancelWrite(), null, limit, Timeout.InfiniteTimeSpan));

        // The reader and the writer each release the link when they end; the last one disposes what it owns.
        public void Release()
        {
            if (Interlocked.Decrement(ref _live) == 0)
            {
                Guarded(() =>
                {
                    _released = true;
                    _drain?.Dispose();
                    ReadCts.Dispose();
                    WriteCts.Dispose();
                });
            }
        }

        // A late cancel or timer can meet a link that has ended and been disposed.
        private void Guarded(Action action)
        {
            lock (this)
            {
                if (!_released)
                {
                    action();
                }
            }
        }
    }
}
