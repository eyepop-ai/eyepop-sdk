using Xunit;

namespace EyePop.Tests;

public class PublicSurfaceTests
{
    private static IEnumerable<Type> Exported() => typeof(Client).Assembly.GetExportedTypes().Where(type => type.Namespace?.StartsWith("EyePop") == true);

    // The pure core, the state machine and the frame codec are internal: a caller names only the values below.
    [Fact]
    public void The_public_types_in_the_EyePop_namespace_are_the_values_and_nothing_of_the_core()
    {
        var exported = Exported()
            .Where(type => type.Namespace == "EyePop")
            .Select(type => type.FullName![("EyePop.".Length)..])
            .Order(StringComparer.Ordinal);

        Assert.Equal(
            new[]
            {
                "Auth", "Auth+AnonymousAuth", "Auth+Exchange", "Client", "Config", "ConfigArgs", "ErrorKind",
                "EyePopEnvironment", "EyePopException", "Media", "Media+Asset", "Media+Group", "Media+Member",
                "Media+Upload", "Media+Url", "Reconnected", "Reconnecting", "Source", "SourceOptions", "UploadContent",
            },
            exported);
    }

    [Fact]
    public void No_public_type_is_in_the_core_namespace() =>
        Assert.DoesNotContain(Exported(), type => type.Namespace == "EyePop.Core");
}
