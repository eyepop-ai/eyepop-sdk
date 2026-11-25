using EyePop.Core;
using Xunit;

namespace EyePop.Tests;

public class BackoffTests
{
    [Theory]
    [InlineData(0, 1.0, 1)]
    [InlineData(1, 1.0, 2)]
    [InlineData(3, 1.0, 8)]
    [InlineData(5, 1.0, 32)]
    [InlineData(6, 1.0, 60)]
    [InlineData(1000, 1.0, 60)]
    public void The_ceiling_doubles_from_one_second_and_stops_at_sixty(int attempt, double random, double seconds) =>
        Assert.Equal(TimeSpan.FromSeconds(seconds), Backoff.Delay(attempt, random));

    [Theory]
    [InlineData(0.0, 0)]
    [InlineData(0.5, 2)]
    public void Full_jitter_scales_the_ceiling_by_the_random_value(double random, double seconds) =>
        Assert.Equal(TimeSpan.FromSeconds(seconds), Backoff.Delay(2, random));

    [Fact]
    public void A_random_value_outside_zero_to_one_is_clamped()
    {
        Assert.Equal(TimeSpan.Zero, Backoff.Delay(2, -3));
        Assert.Equal(TimeSpan.FromSeconds(4), Backoff.Delay(2, 7));
    }

    [Fact]
    public void The_initial_delay_and_cap_are_settings()
    {
        var settings = new Settings(Initial: TimeSpan.FromSeconds(2), Cap: TimeSpan.FromSeconds(10));

        Assert.Equal(TimeSpan.FromSeconds(10), Backoff.Delay(3, 1.0, settings));
    }
}
