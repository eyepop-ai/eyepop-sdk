using EyePop;
using Xunit;

public class ClientTests
{
    [Fact]
    public void Version_is_the_stamped_version_without_build_metadata()
    {
        // The Taskfile exports EXPECTED_VERSION when it builds with -p:Version; otherwise the 0.0.0 placeholder.
        var expected = Environment.GetEnvironmentVariable("EXPECTED_VERSION");
        if (string.IsNullOrEmpty(expected)) expected = "0.0.0";

        Assert.Equal(expected, Client.Version());
    }
}
