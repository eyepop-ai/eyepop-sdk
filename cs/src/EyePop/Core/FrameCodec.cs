using System.Buffers.Binary;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using EyePop.Protocol;

namespace EyePop.Core;

internal abstract record Frame;

internal sealed record TextFrame(string Text) : Frame;

internal sealed record BinaryFrame(ReadOnlyMemory<byte> Bytes) : Frame;

internal abstract record Decoded
{
    public sealed record Ok(IMessage Message) : Decoded;
}

/// <summary>A frame that is not JSON, or a known message type with a missing or wrong field.</summary>
internal sealed record Malformed(string Reason) : Decoded;

internal static class FrameCodec
{
    private const byte ChunkKind = 0x01;
    private const byte CombinedKind = 0x02;

    // The deepest nesting the conformance examples use. A frame nested deeper than this is refused by
    // the parser, which would otherwise be a way to exhaust the stack.
    private const int MaxDepth = 5_001;

    // The types MessageWire decodes. A known type that fails to decode is Malformed; any other type is Unknown.
    private static readonly HashSet<string> KnownTypes =
        new() { "result", "send", "credit", "start", "prediction", "dropped", "usage", "end", "done", "pong", "error" };

    public static Frame Encode(Command command) => new TextFrame(command.ToJson().ToJsonString());

    public static Frame Chunk(ReadOnlyMemory<byte> media) => Binary(ChunkKind, ReadOnlySpan<byte>.Empty, media);

    public static Frame Combined(SetSource header, ReadOnlyMemory<byte> media)
    {
        var json = Encoding.UTF8.GetBytes(header.ToJson().ToJsonString());
        var length = new byte[4];
        BinaryPrimitives.WriteInt32BigEndian(length, json.Length);
        return Binary(CombinedKind, length.Concat(json).ToArray(), media);
    }

    private static Frame Binary(byte kind, ReadOnlySpan<byte> head, ReadOnlyMemory<byte> media)
    {
        var bytes = new byte[1 + head.Length + media.Length];
        bytes[0] = kind;
        head.CopyTo(bytes.AsSpan(1));
        media.CopyTo(bytes.AsMemory(1 + head.Length));
        return new BinaryFrame(bytes);
    }

    /// <summary>Never throws.</summary>
    public static Decoded Decode(Frame frame)
    {
        if (frame is not TextFrame text)
        {
            return new Malformed("the server sent a binary frame");
        }
        JsonNode? node;
        try
        {
            node = JsonNode.Parse(text.Text, documentOptions: new JsonDocumentOptions { MaxDepth = MaxDepth });
        }
        catch (JsonException)
        {
            return new Malformed("not JSON");
        }
        if (node is not JsonObject obj || obj["type"] is not JsonValue type || !type.TryGetValue<string>(out var tag))
        {
            return new Malformed("not an object with a string type");
        }
        var message = MessageWire.Decode(obj);
        return message is UnknownMessage && KnownTypes.Contains(tag)
            ? new Malformed($"a {tag} message is missing a field or holds a wrong one")
            : new Decoded.Ok(message);
    }
}
