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
    public int Received => Volatile.Read(ref _received);
    public bool Disposed => Volatile.Read(ref _disposed) == 1;

    public IReadOnlyList<Frame> Sent { get { lock (_sent) return _sent.ToArray(); } }

    public IEnumerable<JsonNode> SentJson =>
        Sent.OfType<TextFrame>().Select(f => JsonNode.Parse(f.Text)!);

    public void Say(string json) => _inbound.Writer.TryWrite(new Inbound.Message(new TextFrame(json)));

    public void Say(object message) => Say(System.Text.Json.JsonSerializer.Serialize(message));

    public void SayRaw(Frame frame) => _inbound.Writer.TryWrite(new Inbound.Message(frame));

    public void Close(int? code, string? reason) => _inbound.Writer.TryWrite(new Inbound.Closed(code, reason));

    public Task SendAsync(Frame frame, CancellationToken ct)
    {
        if (Disposed) throw new IOException("the socket is closed");
        lock (_sent) _sent.Add(frame);
        return Task.CompletedTask;
    }

    public async Task<Inbound> ReceiveAsync(CancellationToken ct)
    {
        var inbound = await _inbound.Reader.ReadAsync(ct);
        Interlocked.Increment(ref _received);
        return inbound;
    }

    public ValueTask DisposeAsync()
    {
        Interlocked.Exchange(ref _disposed, 1);
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

    /// <summary>When set, a connect waits for it and ignores cancellation, as a real socket that was nearly open might.</summary>
    public Task? Hold { get; set; }

    public void FailNext(int? status, TimeSpan? retryAfter = null) => _failures.Enqueue(new UpgradeException(status, retryAfter));

    public async Task<ISocket> ConnectAsync(Uri pipelineUrl, string? jwt, CancellationToken ct)
    {
        Interlocked.Increment(ref Attempts);
        if (Hold is { } hold) await hold;
        if (_failures.TryDequeue(out var failure)) throw failure;
        var socket = new FakeSocket { Jwt = jwt };
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

    public Dependencies Deps(bool exchange = false, Settings? settings = null) =>
        new(exchange ? Exchange : null, Sockets, Time, () => 0.5, settings ?? new Settings(), TimeSpan.FromSeconds(60));

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
