using System.Reflection;
using System.Reflection.Emit;
using Xunit;

namespace EyePop.Tests;

public class PurityTests
{
    // The shell, which does IO, lives outside these namespaces and outside these names.
    private static readonly string[] CoreNamespaces = { "EyePop.Core", "EyePop.Protocol" };

    private static readonly string[] CoreNames =
    {
        "Config", "ConfigArgs", "Auth", "EyePopEnvironment", "Source", "SourceOptions", "Media", "UploadContent",
        "EyePopException", "ErrorKind", "ErrorKindWire", "Reconnecting", "Reconnected", "Urls",
    };

    private static bool InCore(Type type)
    {
        var top = type;
        while (top.DeclaringType is not null) top = top.DeclaringType;
        return CoreNamespaces.Contains(top.Namespace) || (top.Namespace == "EyePop" && CoreNames.Contains(top.Name));
    }

    private static bool Forbidden(MethodBase callee)
    {
        var type = callee.DeclaringType!;
        var ns = type.Namespace ?? "";
        return ns.StartsWith("System.Net") || ns.StartsWith("System.IO") || ns.StartsWith("System.Threading")
            || ns.StartsWith("System.Diagnostics") || ns.StartsWith("System.Security.Cryptography")
            || type == typeof(TimeProvider) || type == typeof(Environment.SpecialFolder)
            || type == typeof(Environment) || type == typeof(Random) || type == typeof(Console)
            || (type == typeof(DateTime) || type == typeof(DateTimeOffset)) && callee.Name is "get_Now" or "get_UtcNow" or "get_Today"
            || type == typeof(Guid) && callee.Name == "NewGuid";
    }

    private static IEnumerable<MethodBase> Callees(MethodBase method)
    {
        var il = method.GetMethodBody()?.GetILAsByteArray();
        if (il is null) yield break;
        var typeArgs = method.DeclaringType!.IsGenericType ? method.DeclaringType.GetGenericArguments() : null;
        var methodArgs = method.IsGenericMethod ? method.GetGenericArguments() : null;
        for (var i = 0; i < il.Length - 4; i++)
        {
            if (il[i] is not (0x28 or 0x6F or 0x73)) continue; // call, callvirt, newobj
            MethodBase? callee = null;
            try { callee = method.Module.ResolveMethod(BitConverter.ToInt32(il, i + 1), typeArgs, methodArgs); }
            catch (Exception) { /* the byte was an operand of another instruction */ }
            if (callee is not null) yield return callee;
        }
    }

    [Fact]
    public void No_core_type_does_IO_reads_the_process_environment_or_reads_a_clock_or_random_source()
    {
        const BindingFlags All = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly;
        var offenders = typeof(Client).Assembly.GetTypes()
            .Where(InCore)
            .SelectMany(t => t.GetMethods(All).Cast<MethodBase>().Concat(t.GetConstructors(All)))
            .SelectMany(m => Callees(m).Where(Forbidden).Select(c => $"{m.DeclaringType!.Name}.{m.Name} calls {c.DeclaringType!.Name}.{c.Name}"))
            .Distinct()
            .ToList();

        Assert.Empty(offenders);
    }

    [Fact]
    public void The_scan_does_find_a_forbidden_call()
    {
        var callees = Callees(typeof(PurityTests).GetMethod(nameof(Reads_the_clock), BindingFlags.NonPublic | BindingFlags.Static)!);

        Assert.Contains(callees, Forbidden);
    }

    private static DateTimeOffset Reads_the_clock() => DateTimeOffset.UtcNow;
}
