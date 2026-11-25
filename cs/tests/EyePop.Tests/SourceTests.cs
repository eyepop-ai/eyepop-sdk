using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class SourceTests
{
    private static ErrorKind KindOf(Action refused) => Assert.Throws<EyePopException>(refused).Kind;

    [Fact]
    public void An_upload_of_bytes_knows_its_length() =>
        Assert.Equal(3, new Media.Upload("image/png", UploadContent.FromBytes(new byte[3])).Content.Length);

    [Fact]
    public void An_upload_opened_from_a_stream_may_not_know_its_length() =>
        Assert.Null(new Media.Upload("image/png", UploadContent.FromStream(() => new MemoryStream())).Content.Length);

    [Fact]
    public void A_negative_length_is_refused() =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => UploadContent.FromStream(() => new MemoryStream(), -1)));

    [Fact]
    public void An_upload_without_a_content_type_is_refused() =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => new Media.Upload("", UploadContent.FromBytes(new byte[1]))));

    [Fact]
    public void A_group_without_members_is_refused() =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => new Media.Group(Array.Empty<Media.Member>())));

    [Fact]
    public void A_group_keeps_its_members_in_order()
    {
        var members = new Media.Member[] { new Media.Url("https://a"), new Media.Upload("image/png", UploadContent.FromBytes(new byte[1])) };

        Assert.Equal(members, new Media.Group(members).Members);
    }

    [Fact]
    public void A_source_is_not_live_unless_it_says_so()
    {
        Assert.False(new Source(new Media.Url("https://a")).Options.Live);
        Assert.True(new Source(new Media.Url("rtsp://a"), new SourceOptions(Live: true)).Options.Live);
    }
}
