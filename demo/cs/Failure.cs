using System.Text.Json;

namespace EyePop.Demo;

/// <summary>A scenario failed for a reason the user can act on. The message is the FAIL line's reason.</summary>
public sealed class DemoFailure(string message) : Exception(message);

public static class Failure
{
    /// <summary>One short sentence for the FAIL line; never a stack trace.</summary>
    public static string Describe(Exception error, int timeoutSeconds, bool gotPredictions) => error switch
    {
        DemoFailure => error.Message,
        // Without the network the SDK retries until the deadline, so "unreachable" shows up as a timeout.
        OperationCanceledException => gotPredictions
            ? $"timed out after {timeoutSeconds} seconds; raise it with --timeout"
            : $"timed out after {timeoutSeconds} seconds; check your network, or raise it with --timeout",
        EyePopException e => Describe(e),
        JsonException => "the pop is not valid JSON",
        FormatException => $"the pop is not a valid pop: {error.Message}",
        _ => error.Message,
    };

    public static string Describe(EyePopException error) => error.Kind switch
    {
        ErrorKind.ExchangeFailed => "EyePop rejected the API key; check EYEPOP_API_KEY and EYEPOP_ENV",
        ErrorKind.ConnectionFailed => "cannot reach EyePop; check your network connection",
        ErrorKind.UpgradeRefused => "EyePop refused the connection; check EYEPOP_ENV, EYEPOP_URL and EYEPOP_AUTH_URL",
        ErrorKind.CommandRejected => $"EyePop rejected the request: {error.Message}",
        ErrorKind.Closed => "the connection closed before the job finished",
        _ => $"invalid configuration: {error.Message}",
    };
}
