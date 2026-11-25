using Xunit;

namespace EyePop.Demo.Tests;

public class FailureTests
{
    [Theory]
    [InlineData(ErrorKind.ExchangeFailed, "API key")]
    [InlineData(ErrorKind.ConnectionFailed, "network")]
    [InlineData(ErrorKind.UpgradeRefused, "EYEPOP_ENV")]
    [InlineData(ErrorKind.Closed, "closed")]
    [InlineData(ErrorKind.CommandRejected, "detail")]
    [InlineData(ErrorKind.InvalidConfig, "detail")]
    public void Every_error_kind_has_a_one_line_message(ErrorKind kind, string mention)
    {
        var message = Failure.Describe(new EyePopException(kind, "detail"), 60, true);

        Assert.Contains(mention, message);
        Assert.DoesNotContain('\n', message);
    }

    [Fact]
    public void A_timeout_after_predictions_only_suggests_a_longer_timeout() =>
        Assert.Equal("timed out after 7 seconds; raise it with --timeout", Failure.Describe(new OperationCanceledException(), 7, true));

    [Fact]
    public void A_timeout_with_no_prediction_suggests_the_network() =>
        Assert.Equal(
            "timed out after 7 seconds; check your network, or raise it with --timeout",
            Failure.Describe(new OperationCanceledException(), 7, false));

    [Fact]
    public void Bad_pop_json_and_bad_pops_say_so()
    {
        Assert.Equal("the pop is not valid JSON", Failure.Describe(new System.Text.Json.JsonException(), 60, true));
        Assert.StartsWith("the pop is not a valid pop", Failure.Describe(new FormatException("x"), 60, true));
    }

    [Fact]
    public void A_demo_failure_keeps_its_own_message() =>
        Assert.Equal("file not found: a.jpg", Failure.Describe(new DemoFailure("file not found: a.jpg"), 60, true));
}
