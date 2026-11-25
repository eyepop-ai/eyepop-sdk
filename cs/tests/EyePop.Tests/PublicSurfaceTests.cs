using Xunit;

namespace EyePop.Tests;

public class PublicSurfaceTests
{
    // The pure core, the state machine and the frame codec are internal: a caller names only the values below.
    [Fact]
    public void The_public_types_in_the_EyePop_namespace_are_the_values_and_nothing_of_the_core()
    {
        var exported = typeof(Client).Assembly.GetExportedTypes()
            .Where(type => type.Namespace == "EyePop" && type.DeclaringType is null)
            .Select(type => type.Name)
            .Order(StringComparer.Ordinal);

        Assert.Equal(
            new[]
            {
                "Auth", "Client", "Config", "ConfigArgs", "ErrorKind", "EyePopEnvironment", "EyePopException", "Media",
                "Reconnected", "Reconnecting", "Source", "SourceOptions", "UploadContent",
            },
            exported);
    }
}
