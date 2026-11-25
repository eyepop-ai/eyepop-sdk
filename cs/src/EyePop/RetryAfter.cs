using System.Globalization;

namespace EyePop;

internal static class RetryAfter
{
    /// <summary>
    /// A Retry-After value is seconds or an HTTP date. Anything else is no hint: the caller still backs off.
    /// The core caps the result, so a hostile value cannot stall a Pipeline.
    /// </summary>
    public static TimeSpan? Parse(string? value, DateTimeOffset now)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }
        if (long.TryParse(value.Trim(), NumberStyles.None, CultureInfo.InvariantCulture, out var seconds))
        {
            return TimeSpan.FromSeconds(Math.Min(seconds, TimeSpan.MaxValue.TotalSeconds / 2));
        }
        return DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out var date)
            ? (date > now ? date - now : TimeSpan.Zero)
            : null;
    }
}
