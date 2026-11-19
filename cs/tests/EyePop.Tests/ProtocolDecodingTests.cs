using System.Text.Json.Nodes;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class ProtocolDecodingTests
{
    public static IEnumerable<object[]> Cases() =>
        JsonNode.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "protocol-decoding.json")))!
            .AsArray()
            .Select(c => new object[] { c!["name"]!.GetValue<string>() });

    [Theory]
    [MemberData(nameof(Cases))]
    public void A_decoding_case_is_known_or_unknown_and_keeps_exact_numbers(string name)
    {
        var c = JsonNode.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "protocol-decoding.json")))!
            .AsArray()
            .Single(x => x!["name"]!.GetValue<string>() == name)!;
        var data = JsonNode.Parse(c["text"]!.GetValue<string>());

        var (known, encoded) = c["union"]!.GetValue<string>() == "command"
            ? Result(Command.Decode(data), Command.Decode(data) is not UnknownCommand)
            : Result(Message.Decode(data), Message.Decode(data) is not UnknownMessage);

        Assert.Equal(c["known"]!.GetValue<bool>(), known);
        if (c["keeps"] is { } keeps)
        {
            Assert.Contains(keeps.GetValue<string>(), encoded.ToJsonString());
        }
    }

    private static (bool, JsonNode) Result(Command command, bool known) => (known, command.ToJson());

    private static (bool, JsonNode) Result(Message message, bool known) => (known, message.ToJson());

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
