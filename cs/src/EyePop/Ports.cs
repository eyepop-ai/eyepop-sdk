using System.Text;
using EyePop.Core;

namespace EyePop;

// The seams of the shell. Each has a second implementation in the tests, so the Pipeline runs with no
// network, no real clock and no real randomness.

/// <summary>The short-lived credential the exchange returns. Its printed form never holds the JWT.</summary>
internal sealed record Token(string Jwt, DateTimeOffset ExpiresAt)
{
    private bool PrintMembers(StringBuilder builder)
    {
        builder.Append($"Jwt = ***, ExpiresAt = {ExpiresAt:O}");
        return true;
    }
}

internal interface IExchange
{
    /// <exception cref="ExchangeException">The exchange failed. Cancellation is the only other exception.</exception>
    Task<Token> ExchangeAsync(CancellationToken ct);
}

/// <summary>A null status means the exchange could not connect, was reset or timed out.</summary>
internal sealed class ExchangeException(int? status, TimeSpan? retryAfter) : Exception("the token exchange failed")
{
    public int? Status { get; } = status;
    public TimeSpan? RetryAfter { get; } = retryAfter;
}

/// <summary>A null status means the upgrade could not connect, was reset or timed out.</summary>
internal sealed class UpgradeException(int? status, TimeSpan? retryAfter) : Exception("the socket upgrade failed")
{
    public int? Status { get; } = status;
    public TimeSpan? RetryAfter { get; } = retryAfter;
}

internal abstract record Inbound
{
    private Inbound() { }

    public sealed record Message(Frame Frame) : Inbound;

    /// <summary>A null code means the socket dropped with no close frame.</summary>
    public sealed record Closed(int? Code, string? Reason) : Inbound;
}

internal interface ISocket : IAsyncDisposable
{
    /// <exception cref="IOException">The frame could not be sent. Cancellation is the only other exception.</exception>
    Task SendAsync(Frame frame, CancellationToken ct);

    /// <summary>Never throws but for cancellation: a dropped socket is <see cref="Inbound.Closed"/> with no code.</summary>
    Task<Inbound> ReceiveAsync(CancellationToken ct);
}

internal interface ISocketFactory
{
    /// <exception cref="UpgradeException">The socket did not open. Cancellation is the only other exception.</exception>
    Task<ISocket> ConnectAsync(Uri pipelineUrl, string? jwt, CancellationToken ct);
}

/// <summary>Everything the Pipeline gets from outside itself.</summary>
internal sealed record Dependencies(
    IExchange? Exchange,
    ISocketFactory Sockets,
    TimeProvider Time,
    Func<double> Random,
    Settings Settings,
    TimeSpan Liveness)
{
    public static Dependencies For(Config config) => new(
        config.Auth is Auth.Exchange exchange ? new HttpExchange(exchange, config.AccountUuid, TimeProvider.System) : null,
        new ClientWebSocketFactory(),
        TimeProvider.System,
        System.Random.Shared.NextDouble,
        new Settings(),
        TimeSpan.FromSeconds(60));
}
