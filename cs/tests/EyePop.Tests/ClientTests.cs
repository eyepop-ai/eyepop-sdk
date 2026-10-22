using EyePop;
using Xunit;

public class ClientTests
{
    [Fact]
    public void Version_is_a_plain_version_without_build_metadata()
    {
        var version = Client.Version();

        Assert.Matches(@"^\d+\.\d+\.\d+", version);
        Assert.DoesNotContain("+", version);
    }
}
