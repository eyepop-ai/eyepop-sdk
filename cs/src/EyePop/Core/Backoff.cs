namespace EyePop.Core;

/// <summary>The supervision settings. Each default is the one the docs state.</summary>
internal sealed record Settings(
    TimeSpan? Initial = null,
    TimeSpan? Cap = null,
    TimeSpan? HealthyAfter = null,
    TimeSpan? GiveUpAfter = null)
{
    public TimeSpan InitialDelay => Initial ?? TimeSpan.FromSeconds(1);
    public TimeSpan CapDelay => Cap ?? TimeSpan.FromSeconds(60);
    public TimeSpan HealthyDuration => HealthyAfter ?? TimeSpan.FromSeconds(30);
    public TimeSpan GiveUpDuration => GiveUpAfter ?? TimeSpan.FromMinutes(15);
}

internal static class Backoff
{
    /// <summary>Exponential with full jitter. <paramref name="random"/> is in [0, 1) and arrives as an argument so this stays pure.</summary>
    public static TimeSpan Delay(int attempt, double random, Settings? settings = null)
    {
        settings ??= new Settings();
        // 2^30 seconds is far past any cap; limiting the exponent keeps the multiplication finite.
        var ceiling = TimeSpan.FromTicks((long)Math.Min(
            settings.CapDelay.Ticks,
            settings.InitialDelay.Ticks * Math.Pow(2, Math.Clamp(attempt, 0, 30))));
        return ceiling * Math.Clamp(random, 0.0, 1.0);
    }
}
