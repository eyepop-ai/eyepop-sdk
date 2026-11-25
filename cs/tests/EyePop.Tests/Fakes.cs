using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Channels;
using EyePop.Core;
using EyePop.Protocol;

namespace EyePop.Tests;

/// <summary>A clock the test moves. Timers and Task.Delay fire only when time is advanced.</summary>
internal sealed class FakeTime : TimeProvider
{
    private readonly object _sync = new();
    private readonly List<FakeTimer> _timers = new();
    private DateTimeOffset _now = new(2026, 1, 1, 0, 0, 0, TimeSpan.Zero);

    public override DateTimeOffset GetUtcNow() { lock (_sync) return _now; }

    public override ITimer CreateTimer(TimerCallback callback, object? state, TimeSpan dueTime, TimeSpan period)
    {
        var timer = new FakeTimer(this, callback, state);
        timer.Change(dueTime, period);
        return timer;
    }

    /// <summary>Whether a timer is waiting that <see cref="Advance"/> by this much would fire. Tests wait for it instead of sleeping.</summary>
    public bool HasTimerWithin(TimeSpan by)
    {
        lock (_sync) return _timers.Any(t => t.Due <= _now + by);
    }

    /// <summary>Moves the clock in steps so a timer set by a fired timer still fires in order.</summary>
    public void Advance(TimeSpan by)
    {
        var target = GetUtcNow() + by;
        while (true)
        {
            FakeTimer? due;
            lock (_sync)
            {
                due = _timers.Where(t => t.Due <= target).OrderBy(t => t.Due).FirstOrDefault();
                if (due is null) { _now = target; return; }
                _now = due.Due > _now ? due.Due : _now;
                _timers.Remove(due);
            }
            due.Fire();
        }
    }

    private sealed class FakeTimer(FakeTime owner, TimerCallback callback, object? state) : ITimer
    {
        public DateTimeOffset Due { get; private set; }

        public bool Change(TimeSpan dueTime, TimeSpan period)
        {
            lock (owner._sync)
            {
                owner._timers.Remove(this);
                if (dueTime == Timeout.InfiniteTimeSpan) return true;
                Due = owner._now + dueTime;
                owner._timers.Add(this);
            }
            return true;
        }

        public void Fire() => callback(state);

        public void Dispose() { lock (owner._sync) owner._timers.Remove(this); }

        public ValueTask DisposeAsync() { Dispose(); return default; }
    }
}

/// <summary>The server's end of a socket, driven by the test.</summary>
internal sealed class FakeSocket : ISocket
{
    private readonly Channel<Inbound> _inbound = Channel.CreateUnbounded<Inbound>();
    private readonly List<Frame> _sent = new();
    private int _received;
    private int _disposed;

    public string? Jwt { get; init; }

    /// <summary>A socket whose receive does not honour cancellation, like one a real transport is still reading from.</summary>
    public bool IgnoreToken { get; init; }

    public volatile bool FailSends;
    public volatile bool BlockSends;
    public volatile Exception? ThrowOnReceive;
    public int Received => Volatile.Read(ref _received);
    public bool Disposed => Volatile.Read(ref _disposed) == 1;

    public IReadOnlyList<Frame> Sent { get { lock (_sent) return _sent.ToArray(); } }

    public IEnumerable<JsonNode> SentJson =>
        Sent.OfType<TextFrame>().Select(f => JsonNode.Parse(f.Text)!);

    public void Say(string json) => _inbound.Writer.TryWrite(new Inbound.Message(new TextFrame(json)));

    public void Say(object message) => Say(System.Text.Json.JsonSerializer.Serialize(message));

    public void SayRaw(Frame frame) => _inbound.Writer.TryWrite(new Inbound.Message(frame));

    public void Close(int? code, string? reason) => _inbound.Writer.TryWrite(new Inbound.Closed(code, reason));

    public async Task SendAsync(Frame frame, CancellationToken ct)
    {
        if (Disposed || FailSends) throw new IOException("the socket is closed");
        if (BlockSends) await Task.Delay(Timeout.Infinite, ct);
        lock (_sent) _sent.Add(frame);
    }

    public async Task<Inbound> ReceiveAsync(CancellationToken ct)
    {
        if (ThrowOnReceive is { } failure) throw failure;
        var inbound = await _inbound.Reader.ReadAsync(IgnoreToken ? CancellationToken.None : ct);
        Interlocked.Increment(ref _received);
        return inbound;
    }

    public ValueTask DisposeAsync()
    {
        Interlocked.Exchange(ref _disposed, 1);
        // A receive that ignores its token ends when the socket goes, as a transport's would.
        if (!IgnoreToken) _inbound.Writer.TryComplete();
        return default;
    }

    public async Task<JsonNode> SentOfType(string type, int index = 0)
    {
        await Eventually.True(() => SentJson.Count(j => j["type"]?.GetValue<string>() == type) > index);
        return SentJson.Where(j => j["type"]?.GetValue<string>() == type).ElementAt(index);
    }
}

internal sealed class FakeSockets : ISocketFactory
{
    private readonly Queue<UpgradeException> _failures = new();
    public List<FakeSocket> Opened { get; } = new();
    public int Attempts;
    private readonly Queue<Func<Task<ISocket>>> _scripted = new();
    public bool NextIgnoresToken { get; set; }

    /// <summary>The next connect never answers, but honours cancellation.</summary>
    public void HangNext() => _scripted.Enqueue(null!);

    /// <summary>The next connect throws something the factory contract does not allow.</summary>
    public void BreakNext() => _scripted.Enqueue(() => throw new InvalidOperationException("a bug in the transport"));

    /// <summary>When set, a connect waits for it and ignores cancellation, as a real socket that was nearly open might.</summary>
    public Task? Hold { get; set; }

    public void FailNext(int? status, TimeSpan? retryAfter = null) => _failures.Enqueue(new UpgradeException(status, retryAfter));

    public async Task<ISocket> ConnectAsync(Uri pipelineUrl, string? jwt, CancellationToken ct)
    {
        Interlocked.Increment(ref Attempts);
        if (Hold is { } hold) await hold;
        if (_scripted.TryDequeue(out var script))
        {
            if (script is null) await Task.Delay(Timeout.Infinite, ct);
            else return await script();
        }
        if (_failures.TryDequeue(out var failure)) throw failure;
        var socket = new FakeSocket { Jwt = jwt, IgnoreToken = NextIgnoresToken };
        NextIgnoresToken = false;
        lock (Opened) Opened.Add(socket);
        return socket;
    }

    public async Task<FakeSocket> Socket(int index)
    {
        await Eventually.True(() => { lock (Opened) return Opened.Count > index; });
        lock (Opened) return Opened[index];
    }
}

internal sealed class FakeExchange(FakeTime time) : IExchange
{
    private readonly Queue<ExchangeException> _failures = new();
    public int Calls;
    public TimeSpan Lifetime { get; set; } = TimeSpan.FromHours(1);

    public void FailNext(int? status, TimeSpan? retryAfter = null) => _failures.Enqueue(new ExchangeException(status, retryAfter));

    public Task<Token> ExchangeAsync(CancellationToken ct)
    {
        var call = Interlocked.Increment(ref Calls);
        if (_failures.TryDequeue(out var failure)) throw failure;
        return Task.FromResult(new Token($"jwt-{call}", time.GetUtcNow() + Lifetime));
    }
}

internal static class Eventually
{
    public static async Task True(Func<bool> condition)
    {
        var until = DateTime.UtcNow.AddSeconds(5);
        while (!condition())
        {
            if (DateTime.UtcNow > until) throw new TimeoutException("the condition did not become true");
            await Task.Delay(5);
        }
    }

    public static async Task<List<JsonNode>> Sent(FakeSocket socket, int count)
    {
        await True(() => socket.SentJson.Count() >= count);
        return socket.SentJson.ToList();
    }

    /// <summary>For asserting that something does not happen: lets every runnable task run first.</summary>
    public static async Task Settle()
    {
        for (var i = 0; i < 20; i++) await Task.Delay(5);
    }
}

/// <summary>A Pipeline over fakes, with the server answering nothing until the test says so.</summary>
internal sealed class Rig
{
    public FakeTime Time { get; } = new();
    public FakeSockets Sockets { get; } = new();
    public FakeExchange Exchange { get; }
    public Pipeline Pipeline { get; private set; } = null!;
    public static readonly string ApiKey = "sk-test-key-value";

    public Rig() => Exchange = new FakeExchange(Time);

    /// <summary>Moves time once a timer is waiting that this step would fire, so no test guesses how long a task takes to start.</summary>
    public async Task Elapse(TimeSpan by)
    {
        await Eventually.True(() => Time.HasTimerWithin(by));
        Time.Advance(by);
    }

    /// <summary>
    /// Moves time in small steps until the Pipeline has made another connect attempt. The backoff timer is
    /// started by a background task, so a single jump could land before it exists.
    /// </summary>
    public async Task AdvanceUntilConnect()
    {
        var before = Sockets.Attempts;
        var until = DateTime.UtcNow.AddSeconds(5);
        while (Sockets.Attempts == before)
        {
            if (DateTime.UtcNow > until) throw new TimeoutException("the Pipeline made no connect attempt");
            Time.Advance(TimeSpan.FromMilliseconds(500));
            await Task.Delay(2);
        }
    }

    public Dependencies Deps(bool exchange = false, Settings? settings = null) =>
        new(exchange ? Exchange : null, Sockets, Time, () => 0.5, settings ?? new Settings(), TimeSpan.FromSeconds(60), TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(5));

    public static Config LocalConfig => Config.Create(new Uri("http://127.0.0.1:9002"), Auth.Anonymous);

    public static Pop EmptyPop => new(Array.Empty<PopComponent>());

    /// <summary>Connects and answers the first setPop, so the Pipeline is open with the empty pop applied.</summary>
    public async Task<(Pipeline, FakeSocket)> Open(bool exchange = false, Settings? settings = null)
    {
        var connecting = Pipeline.ConnectAsync(LocalConfig, EmptyPop, Deps(exchange, settings));
        var socket = await Sockets.Socket(0);
        await Answer(socket, "setPop");
        Pipeline = await connecting;
        return (Pipeline, socket);
    }

    public static async Task Answer(FakeSocket socket, string type, int index = 0)
    {
        var command = await socket.SentOfType(type, index);
        socket.Say(new { type = "result", id = command["id"]!.GetValue<string>() });
    }

    public static string Id(JsonNode command) => command["id"]!.GetValue<string>();

    public static object Prediction(string id, int n) => new { type = "prediction", id, prediction = new { timestamp = n } };
}
