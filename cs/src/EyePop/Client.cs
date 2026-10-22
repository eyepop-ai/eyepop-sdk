using System.Reflection;

namespace EyePop;

public static class Client
{
    // The SDK appends "+<commit sha>" to the informational version; the release version is what precedes it.
    public static string Version() =>
        typeof(Client).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!
            .InformationalVersion.Split('+')[0];
}
