using System.Collections.Immutable;
using System.Text.Json.Nodes;
using EyePop.Protocol;

namespace EyePop.Core;

internal enum Phase { Idle, Connecting, Open, Closed }

/// <summary>Stopping: the caller cancelled it. It is never sent again, so its Job ends when the server answers or at the next reconnect.</summary>
internal sealed record OpenSource(string Id, Source Source, bool AwaitingResend = false, bool Stopping = false);

/// <summary>A command whose answer has not come. A reconnect sends it again.</summary>
internal sealed record PendingCommand(string Id, Command Command, bool SentByReconnect);

/// <summary>
/// One upload being sent in chunks, or, with a Header, one combined upload waiting for its bytes. The content
/// stays in the Source: the core never reads a stream.
/// </summary>
internal sealed record UploadTask(string Id, int Token, int? Member, UploadContent Content, long Credit = 0, bool Requested = false, SetSource? Header = null, long Sent = 0);

internal sealed record State
{
    public Settings Settings { get; init; } = new();
    public Phase Phase { get; init; } = Phase.Idle;

    /// <summary>The last pop that applied.</summary>
    public Pop? Pop { get; init; }

    /// <summary>Set when the pop a reconnect sent failed: the Pipeline waits for a setPop that works.</summary>
    public EyePopException? PopError { get; init; }

    public ImmutableList<OpenSource> Sources { get; init; } = ImmutableList<OpenSource>.Empty;
    public ImmutableList<PendingCommand> Pending { get; init; } = ImmutableList<PendingCommand>.Empty;
    public ImmutableList<UploadTask> Uploads { get; init; } = ImmutableList<UploadTask>.Empty;

    /// <summary>Ids of commands and Jobs share one counter, so no id repeats for the Pipeline's life.</summary>
    public int NextId { get; init; } = 1;

    /// <summary>Counts sockets, so an upload read that was in flight when a socket closed is told apart from one for the new socket.</summary>
    public int Epoch { get; init; }

    public int Attempt { get; init; }

    /// <summary>
    /// When the current series of failures began, for the give-up limit. A socket that opens does not end the
    /// series: only 30 healthy seconds do.
    /// </summary>
    public DateTimeOffset? ReconnectingSince { get; init; }

    public DateTimeOffset? HealthySince { get; init; }
    public bool AfterFailure { get; init; }
    public bool UpgradeRetried { get; init; }

    public static State Initial(Settings? settings = null) => new() { Settings = settings ?? new Settings() };
}

internal abstract record Input
{
    private Input() { }

    public sealed record SetPop(Pop Pop) : Input;
    public sealed record SetSource(Source Source) : Input;
    public sealed record StopSource(string Id) : Input;
    public sealed record GetGraph(GetGraphFormat Format, bool? Verbose = null) : Input;
    public sealed record Ping : Input;
    public sealed record Quit : Input;

    public sealed record Received(IMessage Message) : Input;
    public sealed record Failed(Failure Failure) : Input;

    /// <summary>The socket is open.</summary>
    public sealed record Opened : Input;

    /// <summary>A backoff the core asked for with <see cref="Output.ScheduleResend"/> has run out.</summary>
    public sealed record ResendDue(string Id) : Input;

    /// <summary>The answer to <see cref="Output.ReadUpload"/>: the bytes read, and whether the content ended.</summary>
    public sealed record UploadRead(int Epoch, string Id, int Token, int? Member, ReadOnlyMemory<byte> Data, bool Last) : Input;
}

internal abstract record Output
{
    private Output() { }

    public sealed record Send(Frame Frame) : Output;

    /// <summary>
    /// Read up to Count bytes of an upload's content (all of it when Whole) and answer with <see cref="Input.UploadRead"/>,
    /// echoing Epoch (which socket) and Token (which upload: a source sent again gets a new one).
    /// </summary>
    public sealed record ReadUpload(int Epoch, string Id, int Token, int? Member, UploadContent Content, long Count, bool Whole) : Output;

    public sealed record Deliver(string JobId, JobMessage Message) : Output;

    /// <summary>The Job has nothing more to deliver. An error means it failed, no error means it ended normally.</summary>
    public sealed record CloseJob(string JobId, EyePopException? Error) : Output;

    /// <summary>The id the state gave to the command or Job the input made.</summary>
    public sealed record Issued(string Id) : Output;

    public sealed record Completed(string CommandId, JsonNode Result) : Output;
    public sealed record CommandFailed(string CommandId, EyePopException Error) : Output;

    /// <summary>Open a socket after the delay, exchanging the key first if ForceExchange or the token is short-lived.</summary>
    public sealed record Connect(TimeSpan Delay, bool ForceExchange) : Output;

    /// <summary>
    /// Close the socket if one is open, cancel a connect or resend timer that is waiting, and stay without a socket until the
    /// next command. After a <c>quit</c> frame the shell must flush it before closing.
    /// </summary>
    public sealed record GoIdle : Output;

    /// <summary>Close the socket if one is open. The Pipeline keeps going: a Connect follows or the input says why not.</summary>
    public sealed record CloseSocket : Output;

    public sealed record ScheduleResend(string Id, TimeSpan Delay) : Output;

    /// <summary>An error from the server that belongs to no command.</summary>
    public sealed record Status(EyePopException Error) : Output;
}

/// <summary>What the pure core is given besides the input: time and a random value in [0, 1).</summary>
internal sealed record Moment(DateTimeOffset Now, double Random);
