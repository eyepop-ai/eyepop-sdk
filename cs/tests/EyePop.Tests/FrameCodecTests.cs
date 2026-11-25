using System.Buffers.Binary;
using System.Text;
using System.Text.Json.Nodes;
using EyePop.Core;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class FrameCodecTests
{
    private static readonly string Valid = Path.Combine(AppContext.BaseDirectory, "protocol-examples", "valid");

    public static IEnumerable<object[]> Files(string prefix) =>
        Directory.GetFiles(Valid, prefix + "*.json").Select(f => new object[] { Path.GetFileName(f) });

    public static IEnumerable<object[]> CommandFiles() => Files("command-");
    public static IEnumerable<object[]> MessageFiles() => Files("message-");

    private static string Text(string file) => File.ReadAllText(Path.Combine(Valid, file));

    [Theory]
    [MemberData(nameof(CommandFiles))]
    public void Every_example_command_encodes_to_a_text_frame_with_the_same_json(string file)
    {
        var command = Command.FromJson(JsonNode.Parse(Text(file)));

        var frame = Assert.IsType<TextFrame>(FrameCodec.Encode(command));

        Assert.True(JsonNode.DeepEquals(JsonNode.Parse(Text(file)), JsonNode.Parse(frame.Text)));
    }

    [Fact]
    public void A_chunk_frame_is_the_kind_byte_then_the_media()
    {
        var frame = Assert.IsType<BinaryFrame>(FrameCodec.Chunk(new byte[] { 7, 8, 9 }));

        Assert.Equal(new byte[] { 0x01, 7, 8, 9 }, frame.Bytes.ToArray());
    }

    [Fact]
    public void A_combined_frame_is_the_kind_byte_a_big_endian_header_length_the_header_and_the_media()
    {
        var header = new SetSource("s1", Upload: new SetSourceUpload("image/png"));

        var bytes = Assert.IsType<BinaryFrame>(FrameCodec.Combined(header, new byte[] { 1, 2 })).Bytes.ToArray();

        var json = Encoding.UTF8.GetBytes(header.ToJson().ToJsonString());
        Assert.Equal(0x02, bytes[0]);
        Assert.Equal(json.Length, BinaryPrimitives.ReadInt32BigEndian(bytes.AsSpan(1, 4)));
        Assert.Equal(json, bytes[5..(5 + json.Length)]);
        Assert.Equal(new byte[] { 1, 2 }, bytes[(5 + json.Length)..]);
    }

    [Theory]
    [MemberData(nameof(MessageFiles))]
    public void Every_example_message_decodes_to_a_known_message(string file)
    {
        var decoded = FrameCodec.Decode(new TextFrame(Text(file)));

        var ok = Assert.IsType<Decoded.Ok>(decoded);
        Assert.IsNotType<UnknownMessage>(ok.Message);
    }

    [Theory]
    [MemberData(nameof(MessageFiles))]
    public void Every_example_message_encodes_back_to_the_json_it_was_decoded_from(string file)
    {
        var message = Assert.IsType<Decoded.Ok>(FrameCodec.Decode(new TextFrame(Text(file)))).Message;

        Assert.True(JsonNode.DeepEquals(JsonNode.Parse(Text(file)), message.ToJson()));
    }

    [Fact]
    public void A_message_type_the_sdk_does_not_know_decodes_as_unknown()
    {
        var decoded = FrameCodec.Decode(new TextFrame("""{"type":"from-the-future","id":"s1"}"""));

        Assert.IsType<UnknownMessage>(Assert.IsType<Decoded.Ok>(decoded).Message);
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("")]
    [InlineData("[1,2]")]
    [InlineData("42")]
    [InlineData("""{"id":"s1"}""")]
    [InlineData("""{"type":7}""")]
    [InlineData("""{"type":"end","id":"s1"}""")]
    [InlineData("""{"type":"send","id":"s1","credit":"many"}""")]
    [InlineData("""{"type":"error","id":"s1"}""")]
    public void A_frame_that_is_not_a_message_or_a_known_type_missing_fields_is_malformed(string text) =>
        Assert.IsType<Malformed>(FrameCodec.Decode(new TextFrame(text)));

    [Fact]
    public void A_binary_frame_from_the_server_is_malformed() =>
        Assert.IsType<Malformed>(FrameCodec.Decode(new BinaryFrame(new byte[] { 1, 2, 3 })));

    [Fact]
    public void Nesting_beyond_what_the_parser_allows_is_malformed_not_a_crash()
    {
        var deep = new string('[', 100_000) + new string(']', 100_000);

        Assert.IsType<Malformed>(FrameCodec.Decode(new TextFrame(deep)));
    }

    [Fact]
    public void Decode_never_throws_on_mutated_truncated_or_oversized_frames()
    {
        var random = new Random(20241125);
        var samples = Directory.GetFiles(Valid, "message-*.json").Select(File.ReadAllText).ToList();
        var frames = new List<Frame> { new TextFrame(new string('x', 4_000_000)), new BinaryFrame(Array.Empty<byte>()) };
        foreach (var sample in samples)
        {
            for (var cut = 0; cut < sample.Length; cut += 3)
            {
                frames.Add(new TextFrame(sample[..cut]));
            }
            for (var i = 0; i < 200; i++)
            {
                var chars = sample.ToCharArray();
                chars[random.Next(chars.Length)] = (char)random.Next(0, 0x250);
                frames.Add(new TextFrame(new string(chars)));
            }
        }

        foreach (var frame in frames)
        {
            var decoded = Record.Exception(() => FrameCodec.Decode(frame));
            Assert.Null(decoded);
        }
    }
}
