namespace EyePop;

public enum ErrorKind
{
    InvalidConfig,
    ExchangeFailed,
    ConnectionFailed,
    UpgradeRefused,
    CommandRejected,
    Closed,
}

/// <summary>
/// The SDK's own failure. It is raised only when a retry would fail the same way. It never holds the API key or a token.
/// </summary>
public sealed class EyePopException : Exception
{
    public ErrorKind Kind { get; }
    public int? Status { get; }
    public int? CloseCode { get; }
    public string? Error { get; }

    public EyePopException(ErrorKind kind, string message, int? status = null, int? closeCode = null, string? error = null, Exception? inner = null)
        : base(message, inner)
    {
        Kind = kind;
        Status = status;
        CloseCode = closeCode;
        Error = error;
    }
}

internal static class ErrorKindWire
{
    public static string ToWire(this ErrorKind kind) => kind switch
    {
        ErrorKind.InvalidConfig => "invalid_config",
        ErrorKind.ExchangeFailed => "exchange_failed",
        ErrorKind.ConnectionFailed => "connection_failed",
        ErrorKind.UpgradeRefused => "upgrade_refused",
        ErrorKind.CommandRejected => "command_rejected",
        ErrorKind.Closed => "closed",
        _ => throw new ArgumentOutOfRangeException(nameof(kind)),
    };
}
