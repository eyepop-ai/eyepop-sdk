using System.Numerics;
using System.Text;
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

        var problem = Problem(c);

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
        var (unknown, decoded) = c["union"]!.GetValue<string>() == "command"
            ? Result(Command.Decode(data))
            : Result(Message.Decode(data));
        var encoded = JsonNode.Parse(decoded.ToJsonString(), documentOptions: options)!;
        var variant = unknown ? "Unknown" : encoded["type"]!.GetValue<string>();
        if (variant != c["variant"]!.GetValue<string>())
        {
            return $"decoded to {variant}, want {c["variant"]}";
        }
        using var input = JsonDocument.Parse(text, options);
        if (Unchanged(encoded, input.RootElement, text) != c["unchanged"]!.GetValue<bool>())
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

    private static (bool, JsonNode) Result(object message) => (message is UnknownMessage, Message.ToJson(message));

    private static bool Unchanged(JsonNode encoded, JsonElement input, string text)
    {
        try
        {
            return Same(encoded, input);
        }
        catch (InvalidOperationException) when (HoldsALoneSurrogate(text))
        {
            return false;
        }
    }

    private static bool HoldsALoneSurrogate(string text)
    {
        var reader = new Utf8JsonReader(Encoding.UTF8.GetBytes(text), new JsonReaderOptions { MaxDepth = int.MaxValue });
        while (reader.Read())
        {
            if (reader.TokenType is not (JsonTokenType.String or JsonTokenType.PropertyName)) continue;
            try
            {
                reader.GetString();
            }
            catch (InvalidOperationException)
            {
                return true;
            }
        }
        return false;
    }

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

        Assert.Equal("original", Message.ToJson(message)["extra"]!["status"]!.GetValue<string>());
    }

    [Fact]
    public void A_nan_double_keeps_every_field()
    {
        var known = Message.Decode(new JsonObject { ["type"] = "credit", ["id"] = "c1", ["bytes"] = 1, ["extra"] = JsonValue.Create(double.NaN) });
        var unknown = Message.Decode(new JsonObject { ["type"] = "credit", ["id"] = "c1", ["bytes"] = JsonValue.Create(double.NaN) });

        Assert.True(double.IsNaN(((Credit)known).Raw!["extra"]!.GetValue<double>()));
        Assert.Equal(3, ((UnknownMessage)unknown).Raw.Count);
    }

    [Fact]
    public void A_lone_surrogate_key_decodes_to_unknown_keeping_every_field()
    {
        var message = Message.Decode(new JsonObject { ["type"] = "credit", ["id"] = "c1", ["bytes"] = 1, ["\ud800"] = 1 });

        Assert.Equal(4, Assert.IsType<UnknownMessage>(message).Raw.Count);
    }

    [Theory]
    [InlineData("""{"type":"credit","id":"c1","bytes":1,"\ud800":1}""", """{"type":"credit","id":"c1","bytes":1,"\uFFFD":1}""")]
    [InlineData("""{"\ud800":1,"type":"credit","id":"c1","bytes":1,"bytes":2}""", """{"\uFFFD":1,"type":"credit","id":"c1","bytes":2}""")]
    [InlineData("""{"type":"credit","id":"\ud800","bytes":1,"bytes":2}""", """{"type":"credit","id":"\uFFFD","bytes":2}""")]
    public void A_lone_surrogate_in_parsed_text_decodes_to_a_readable_unknown(string text, string written)
    {
        var message = Assert.IsType<UnknownMessage>(Message.Decode(JsonNode.Parse(text)));

        Assert.Equal(("credit", written), (message.Raw["type"]!.GetValue<string>(), message.ToJson().ToJsonString()));
    }

    [Theory]
    [InlineData("""{"type":"credit","id":"\ufffd","bytes":1,"bytes":2}""")]
    [InlineData("""{"\ud800":1,"type":"credit","id":"c1","bytes":1}""")]
    public void Without_the_element_accessor_a_parsed_object_it_cannot_read_decodes_to_an_empty_unknown(string text)
    {
        Wire.ReadsUnreadObjects = false;
        try
        {
            var message = Assert.IsType<UnknownMessage>(Message.Decode(JsonNode.Parse(text)));

            Assert.Empty(message.Raw);
        }
        finally
        {
            Wire.ReadsUnreadObjects = true;
        }
    }

    [Fact]
    public void A_lone_surrogate_value_held_in_memory_decodes_to_unknown_keeping_every_field()
    {
        var message = Message.Decode(new JsonObject { ["type"] = "credit", ["id"] = "c1", ["bytes"] = 1, ["note"] = "\ud800" });

        Assert.Equal(4, Assert.IsType<UnknownMessage>(message).Raw.Count);
    }

    [Fact]
    public void A_replacement_character_is_ordinary_text()
    {
        Assert.IsType<Credit>(Message.Decode(JsonNode.Parse("""{"type":"credit","id":"\ufffd","bytes":1,"\ufffd":"\ufffd"}""")));
    }

    [Fact]
    public void A_string_length_counts_code_points()
    {
        Assert.Equal((1, 2), (WireRules.Length("\U0001F600"), WireRules.Length("e\u0301")));
    }

    [Fact]
    public void An_integer_held_as_a_clr_int_is_accepted()
    {
        var input = new JsonObject { ["type"] = "credit", ["id"] = "c1", ["bytes"] = JsonValue.Create(1) };

        Assert.IsType<Credit>(Message.Decode(input));
    }
}
