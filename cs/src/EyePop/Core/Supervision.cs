using EyePop.Protocol;

namespace EyePop.Core;

/// <summary>What the shell observed go wrong. The shell reports it; <see cref="Supervision.Classify"/> decides what to do.</summary>
internal abstract record Failure
{
    /// <summary>The shell watches the liveness window; no message for that long is this failure.</summary>
    public static readonly Failure Silent = new SilentFailure();

    private Failure() { }

    /// <summary>A null status means the exchange could not connect, was reset or timed out.</summary>
    public sealed record Exchange(int? Status, TimeSpan? RetryAfter = null) : Failure;

    /// <summary>A null status means the upgrade could not connect, was reset or timed out.</summary>
    public sealed record Upgrade(int? Status, TimeSpan? RetryAfter = null) : Failure;

    /// <summary>A null code means the socket dropped with no close frame.</summary>
    public sealed record SocketClosed(int? Code, string? Reason) : Failure;

    public sealed record SilentFailure : Failure;
}

internal abstract record Verdict
{
    private Verdict() { }

    public sealed record Retry(EyePopException Cause, TimeSpan? Floor = null, bool Immediate = false, bool ForceExchange = false, bool UpgradeRetry = false) : Verdict;

    /// <summary>A retry would fail the same way: the Jobs end with the error and the Pipeline goes idle.</summary>
    public sealed record Terminal(EyePopException Cause) : Verdict;

    public sealed record Idle : Verdict;

    /// <summary>The server stopped the pipeline while a setPop was pending: that pop did not apply.</summary>
    public sealed record PopStopped(EyePopException Cause) : Verdict;
}

/// <summary>The failure table of docs/sdk-interface.md ("Supervision") as a function. The pipeline API does not mark errors retryable yet, so this is the only source of the decision.</summary>
internal static class Supervision
{
    public static Verdict Classify(Failure failure, bool popPending, bool upgradeRetried, bool hasWork) => failure switch
    {
        Failure.Exchange { Status: null } => new Verdict.Retry(new(ErrorKind.ConnectionFailed, "the token exchange could not connect")),
        Failure.Exchange { Status: var status, RetryAfter: var after } when Retryable(status!.Value) =>
            new Verdict.Retry(new(ErrorKind.ExchangeFailed, "the token exchange failed", status: status), after),
        Failure.Exchange { Status: var status } =>
            new Verdict.Terminal(new(ErrorKind.ExchangeFailed, "the token exchange was refused", status: status)),

        Failure.Upgrade { Status: null } => new Verdict.Retry(new(ErrorKind.ConnectionFailed, "the socket could not connect")),
        Failure.Upgrade { Status: 401 or 403 } refused => upgradeRetried
            ? new Verdict.Terminal(new(ErrorKind.UpgradeRefused, "the socket upgrade was refused", status: refused.Status))
            : new Verdict.Retry(new(ErrorKind.UpgradeRefused, "the socket upgrade was refused", status: refused.Status), Immediate: true, ForceExchange: true, UpgradeRetry: true),
        Failure.Upgrade { Status: var status, RetryAfter: var after } when Retryable(status!.Value) =>
            new Verdict.Retry(new(ErrorKind.UpgradeRefused, "the pipeline cannot take a socket now", status: status), after),
        Failure.Upgrade { Status: var status } =>
            new Verdict.Terminal(new(ErrorKind.UpgradeRefused, "the socket upgrade was refused", status: status)),

        Failure.SocketClosed { Code: 1011, Reason: "pipeline_stopped" } closed when popPending => new Verdict.PopStopped(Closed(closed)),
        Failure.SocketClosed { Code: 1008, Reason: "credential_expired" } closed =>
            new Verdict.Retry(Closed(closed), Immediate: true, ForceExchange: true),
        // The SDK broke the upload protocol, so sending the upload again would break it again.
        Failure.SocketClosed { Code: 1008, Reason: "unexpected_bytes" or "credit_exceeded" } closed => new Verdict.Terminal(Closed(closed)),
        Failure.SocketClosed { Code: 1000, Reason: "idle" } when !hasWork => new Verdict.Idle(),
        Failure.SocketClosed { Code: null } => new Verdict.Retry(new(ErrorKind.ConnectionFailed, "the socket dropped")),
        Failure.SocketClosed closed => new Verdict.Retry(Closed(closed)),

        _ => new Verdict.Retry(new(ErrorKind.ConnectionFailed, "the socket went silent")),
    };

    private static bool Retryable(int status) => status == 429 || status >= 500;

    private static EyePopException Closed(Failure.SocketClosed closed) =>
        new(ErrorKind.Closed, "the socket closed", closeCode: closed.Code, error: closed.Reason);
}
