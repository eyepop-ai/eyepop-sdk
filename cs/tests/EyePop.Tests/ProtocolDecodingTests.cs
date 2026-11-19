using System.Numerics;
using System.Text.Json;
using System.Text.Json.Nodes;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class ProtocolDecodingTests
{
    private static readonly string Examples = Path.Combine(AppContext.BaseDirectory, "protocol-examples");

    private static JsonArray LoadCases() => JsonNode.Parse(File.ReadAllText(Path.Combine(Examples, "decoding.json")))!.AsArray();

    private static string NameOf(JsonNode c) => (c["file"] ?? c["name"])!.GetValue<string>();

    public static IEnumerable<object[]> Cases() => LoadCases().Select(c => new object[] { NameOf(c!) });

    [Fact]
    public void The_decoding_cases_are_found()
    {
        Assert.True(LoadCases().Count > 60);
    }

    [Theory]
    [MemberData(nameof(Cases))]
    public void A_decoding_case_has_its_stated_outcome(string name)
    {
        var c = LoadCases().Single(x => NameOf(x!) == name)!;

        string? problem;
        try
        {
            problem = Problem(c);
        }
        catch (Exception error)
        {
            problem = error.ToString();
        }

        if (c["diverges"]?["csharp"] is { } reason)
        {
            Assert.True(problem is not null, $"passes but is marked as a known C# divergence ({reason}); remove the marker");
        }
        else
        {
            Assert.True(problem is null, problem);
        }
    }

    private static string? Problem(JsonNode c)
    {
        var text = c["file"] is { } file
            ? File.ReadAllText(Path.Combine(Examples, file.GetValue<string>()))
            : c["text"]!.GetValue<string>();
        var options = new JsonDocumentOptions { MaxDepth = int.MaxValue };
        var data = JsonNode.Parse(text, documentOptions: options);
        var (unknown, encoded) = c["union"]!.GetValue<string>() == "command"
            ? Result(Command.Decode(data))
            : Result(Message.Decode(data));
        var variant = unknown ? "Unknown" : encoded["type"]!.GetValue<string>();
        if (variant != c["variant"]!.GetValue<string>())
        {
            return $"decoded to {variant}, want {c["variant"]}";
        }
        using var input = JsonDocument.Parse(text, options);
        if (Same(encoded, input.RootElement) != c["unchanged"]!.GetValue<bool>())
        {
            return $"encoded {encoded.ToJsonString()}, want unchanged = {c["unchanged"]}";
        }
        if (c["keeps"] is { } keeps && !encoded.ToJsonString().Contains(keeps.GetValue<string>()))
        {
            return $"encoded {encoded.ToJsonString()}, want it to contain {keeps}";
        }
        return null;
    }

    private static (bool, JsonNode) Result(Command command) => (command is UnknownCommand, command.ToJson());

    private static (bool, JsonNode) Result(Message message) => (message is UnknownMessage, message.ToJson());

    private static bool Same(JsonNode? a, JsonElement b) => (a, b.ValueKind) switch
    {
        (JsonObject x, JsonValueKind.Object) => LastWins(b) is var y
            && x.Count == y.Count
            && x.All(p => y.TryGetValue(p.Key, out var v) && Same(p.Value, v)),
        (JsonArray x, JsonValueKind.Array) => x.Count == b.GetArrayLength() && x.Zip(b.EnumerateArray()).All(p => Same(p.First, p.Second)),
        (JsonValue x, JsonValueKind.Number) when x.GetValueKind() == JsonValueKind.Number =>
            Canonical(x.ToJsonString()) == Canonical(b.GetRawText()),
        _ => b.ValueKind is not (JsonValueKind.Object or JsonValueKind.Array) && JsonNode.DeepEquals(a, JsonValue.Create(b)),
    };

    private static Dictionary<string, JsonElement> LastWins(JsonElement obj) =>
        obj.EnumerateObject().GroupBy(p => p.Name).ToDictionary(g => g.Key, g => g.Last().Value);

    private static string Canonical(string number)
    {
        var parts = number.Split('e', 'E');
        var exponent = parts.Length > 1 ? BigInteger.Parse(parts[1]) : BigInteger.Zero;
        var sign = parts[0].StartsWith('-') ? "-" : "";
        var decimals = parts[0].TrimStart('-').Split('.');
        var fraction = decimals.Length > 1 ? decimals[1] : "";
        var digits = (decimals[0] + fraction).TrimStart('0');
        if (digits.Length == 0)
        {
            return "0";
        }
        var significant = digits.TrimEnd('0');
        exponent += digits.Length - significant.Length - fraction.Length;
        return $"{sign}{significant}e{exponent}";
    }

    [Fact]
    public void A_field_set_to_null_is_removed_from_the_retained_json()
    {
        var source = (SetSource)Command.Decode(JsonNode.Parse("""{"type":"setSource","id":"s1","url":"u"}"""));

        var changed = source with { Url = null, AssetUuid = "a" };

        Assert.True(JsonNode.DeepEquals(changed.ToJson(), JsonNode.Parse("""{"type":"setSource","id":"s1","assetUuid":"a"}""")));
    }

    [Fact]
    public void Decoded_json_is_a_snapshot_of_the_input()
    {
        var input = JsonNode.Parse("""{"type":"result","id":"r1","extra":{"status":"original"}}""")!;
        var message = Message.Decode(input);

        input["extra"]!["status"] = "changed";

        Assert.Equal("original", message.ToJson()["extra"]!["status"]!.GetValue<string>());
    }

    [Fact]
    public void An_integer_held_as_a_clr_int_is_accepted()
    {
        var input = new JsonObject { ["type"] = "credit", ["id"] = "c1", ["bytes"] = JsonValue.Create(1) };

        Assert.IsType<Credit>(Message.Decode(input));
    }
}
