using System.Text.Json.Nodes;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class ProtocolExamplesTests
{
    private static readonly string Examples = Path.Combine(AppContext.BaseDirectory, "protocol-examples");

    public static IEnumerable<object[]> ValidExamples() =>
        Directory.GetFiles(Examples, "*.json").OrderBy(p => p).Select(p => new object[] { Path.GetFileName(p) });

    [Fact]
    public void The_valid_examples_are_found()
    {
        Assert.True(ValidExamples().Count() > 30);
    }

    [Theory]
    [MemberData(nameof(ValidExamples))]
    public void A_valid_example_decodes_to_a_known_variant_and_encodes_back_unchanged(string name)
    {
        var data = JsonNode.Parse(File.ReadAllText(Path.Combine(Examples, name)))!;

        JsonNode encoded;
        if (name.StartsWith("command-"))
        {
            var command = Command.Decode(data);
            Assert.IsNotType<UnknownCommand>(command);
            encoded = command.ToJson();
        }
        else
        {
            var message = Message.Decode(data);
            Assert.IsNotType<UnknownMessage>(message);
            encoded = message.ToJson();
        }

        Assert.True(JsonNode.DeepEquals(encoded, data), $"{name}: {encoded.ToJsonString()} != {data.ToJsonString()}");
    }
}
