using Xunit;

namespace EyePop.Demo.Tests;

public class FailureTests
{
    [Theory]
    [InlineData(ErrorKind.ExchangeFailed, "API key")]
    [InlineData(ErrorKind.ConnectionFailed, "network")]
    [InlineData(ErrorKind.UpgradeRefused, "EYEPOP_ENV")]
    [InlineData(ErrorKind.Closed, "closed")]
    public void Every_error_kind_has_a_one_line_message(ErrorKind kind, string mention)
    {
        var message = Failure.Describe(new EyePopException(kind, "detail"), 60);

        Assert.Contains(mention, message);
        Assert.DoesNotContain('\n', message);
    }

    [Fact]
    public void A_cancelled_run_is_a_timeout() =>
        Assert.Equal("timed out after 7 seconds; raise it with --timeout", Failure.Describe(new OperationCanceledException(), 7));

    [Fact]
    public void A_demo_failure_keeps_its_own_message() =>
        Assert.Equal("file not found: a.jpg", Failure.Describe(new DemoFailure("file not found: a.jpg"), 60));
}
