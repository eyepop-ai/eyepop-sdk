using EyePop.Protocol;

namespace EyePop;

/// <summary>
/// What an upload sends. A stream that can be read only once is not accepted: a reconnect sends the upload
/// again, so it is bytes or a function that opens a new stream each time.
/// </summary>
public abstract record UploadContent
{
    public abstract long? Length { get; }

    private UploadContent() { }

    public static UploadContent FromBytes(ReadOnlyMemory<byte> bytes) => new BytesContent(bytes);

    public static UploadContent FromStream(Func<Stream> open, long? length = null) =>
        length is < 0
            ? throw new EyePopException(ErrorKind.InvalidConfig, "an upload length cannot be negative")
            : new StreamContent(open, length);

    internal sealed record BytesContent(ReadOnlyMemory<byte> Bytes) : UploadContent
    {
        public override long? Length => Bytes.Length;
    }

    internal sealed record StreamContent(Func<Stream> Open, long? Known) : UploadContent
    {
        public override long? Length => Known;
    }
}

/// <summary>What the pipeline processes. There is no mode: the pipeline applies its default.</summary>
public abstract record Media
{
    private Media() { }

    /// <summary>A group member: a <see cref="Url"/> or an <see cref="Upload"/>, in the order the ability sees them.</summary>
    public abstract record Member : Media
    {
        private protected Member() { }
    }

    public sealed record Url(string Address) : Member;

    public sealed record Asset(string AssetUuid) : Media;

    public sealed record Upload : Member
    {
        public string ContentType { get; }
        public UploadContent Content { get; }

        public Upload(string contentType, UploadContent content)
        {
            ContentType = string.IsNullOrWhiteSpace(contentType)
                ? throw new EyePopException(ErrorKind.InvalidConfig, "an upload needs a content type")
                : contentType;
            Content = content;
        }
    }

    public sealed record Group : Media
    {
        public IReadOnlyList<Member> Members { get; }

        public Group(IReadOnlyList<Member> members)
        {
            Members = members.Count == 0
                ? throw new EyePopException(ErrorKind.InvalidConfig, "a group needs members")
                : members.ToArray();
        }
    }
}

public sealed record SourceOptions(
    IReadOnlyList<ComponentParams>? Params = null,
    Roi? Roi = null,
    Camera? Camera = null,
    string? Fps = null,
    bool Live = false);

public sealed record Source
{
    public Media Media { get; }
    public SourceOptions Options { get; }

    public Source(Media media, SourceOptions? options = null)
    {
        Media = media;
        Options = options ?? new SourceOptions();
    }
}
