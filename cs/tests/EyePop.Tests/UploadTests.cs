using EyePop.Core;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class UploadTests
{
    private const int EightMiB = 8 * 1024 * 1024;

    private static int Kind(Output.Send send) => ((BinaryFrame)send.Frame).Bytes.Span[0];

    [Fact]
    public void Bytes_of_8_MiB_or_less_go_as_one_combined_frame()
    {
        var session = Session.Opened();

        session.SetSource(Session.UploadOf(Session.Bytes(EightMiB)));

        var send = Assert.Single(session.Of<Output.Send>());
        Assert.Equal(0x02, Kind(send));
        Assert.Empty(session.Of<Output.ReadUpload>());
    }

    [Fact]
    public void Bytes_of_one_more_than_8_MiB_are_chunked_so_the_header_goes_as_text_and_nothing_is_read_before_credit()
    {
        var session = Session.Opened();

        var id = session.SetSource(Session.UploadOf(Session.Bytes(EightMiB + 1)));

        var header = Assert.Single(session.Sent());
        Assert.Equal(id, header["id"]!.GetValue<string>());
        Assert.Equal("image/jpeg", header["upload"]!["contentType"]!.GetValue<string>());
        Assert.Empty(session.Of<Output.ReadUpload>());
    }

    [Fact]
    public void A_stream_of_known_length_within_8_MiB_is_read_whole_then_sent_combined()
    {
        var session = Session.Opened();
        var content = UploadContent.FromStream(() => new MemoryStream(), 10);

        var id = session.SetSource(Session.UploadOf(content));
        var read = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Empty(session.Sent());
        Assert.Equal(10, read.Count);
        Assert.True(read.Whole);

        session.Feed(new Input.UploadRead(read.Epoch, id, null, new byte[10], true));
        Assert.Equal(0x02, Kind(Assert.Single(session.Of<Output.Send>())));
    }

    [Fact]
    public void A_stream_of_unknown_length_is_chunked()
    {
        var session = Session.Opened();

        session.SetSource(Session.UploadOf(UploadContent.FromStream(() => new MemoryStream())));

        Assert.Equal("setSource", session.Sent().Single()["type"]!.GetValue<string>());
        Assert.Empty(session.Of<Output.ReadUpload>());
    }

    private static (Session, string) Chunked()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.UploadOf(UploadContent.FromStream(() => new MemoryStream())));
        return (session, id);
    }

    [Fact]
    public void Credit_is_spent_in_chunks_of_at_most_64_KiB_and_the_last_read_sends_uploaded()
    {
        var (session, id) = Chunked();

        session.Feed(new Send(id, 100_000));
        var first = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Equal(65_536, first.Count);

        session.Feed(new Input.UploadRead(first.Epoch, id, null, new byte[65_536], false));
        Assert.Equal(1, Kind(Assert.Single(session.Of<Output.Send>())));
        var second = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Equal(34_464, second.Count);

        session.Feed(new Input.UploadRead(first.Epoch, id, null, new byte[100], true));
        Assert.Equal(1, Kind(session.Of<Output.Send>().First()));
        var uploaded = session.Sent().Single();
        Assert.Equal("uploaded", uploaded["type"]!.GetValue<string>());
        Assert.Equal(id, uploaded["id"]!.GetValue<string>());
        Assert.Null(uploaded["member"]);
    }

    [Fact]
    public void No_read_is_asked_while_the_credit_is_spent_and_a_credit_message_resumes_it()
    {
        var (session, id) = Chunked();
        session.Feed(new Send(id, 10));
        var read = Assert.Single(session.Of<Output.ReadUpload>());

        session.Feed(new Input.UploadRead(read.Epoch, id, null, new byte[10], false));
        Assert.Empty(session.Of<Output.ReadUpload>());

        session.Feed(new Credit(id, 20));
        Assert.Equal(20, Assert.Single(session.Of<Output.ReadUpload>()).Count);
    }

    [Fact]
    public void A_final_empty_read_sends_uploaded_without_an_empty_chunk()
    {
        var (session, id) = Chunked();
        session.Feed(new Send(id, 10));
        var read = Assert.Single(session.Of<Output.ReadUpload>());

        session.Feed(new Input.UploadRead(read.Epoch, id, null, Array.Empty<byte>(), true));

        Assert.DoesNotContain(session.Of<Output.Send>(), s => s.Frame is BinaryFrame);
        Assert.Equal("uploaded", session.Sent().Single()["type"]!.GetValue<string>());
    }

    [Fact]
    public void Only_one_upload_reads_at_a_time_and_the_next_starts_when_the_first_is_uploaded()
    {
        var session = Session.Opened();
        var first = session.SetSource(Session.UploadOf(UploadContent.FromStream(() => new MemoryStream())));
        var second = session.SetSource(Session.UploadOf(UploadContent.FromStream(() => new MemoryStream())));

        session.Feed(new Send(second, 100));
        Assert.Empty(session.Of<Output.ReadUpload>());

        session.Feed(new Send(first, 100));
        var read = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Equal(first, read.Id);

        session.Feed(new Input.UploadRead(read.Epoch, first, null, new byte[5], true));
        var next = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Equal(second, next.Id);
    }

    [Fact]
    public void A_group_sends_one_header_and_uploads_each_upload_member_in_order_by_member_index()
    {
        var session = Session.Opened();
        var group = new Media.Group(new Media.Member[]
        {
            new Media.Upload("image/png", UploadContent.FromBytes(new byte[2048])),
            new Media.Url("https://example.com/a.jpg"),
            new Media.Upload("image/jpeg", UploadContent.FromStream(() => new MemoryStream())),
        });

        var id = session.SetSource(new Source(group));

        var header = Assert.Single(session.Sent());
        var members = header["group"]!.AsArray();
        Assert.Equal(2048, members[0]!["upload"]!["bytes"]!.GetValue<int>());
        Assert.Equal("https://example.com/a.jpg", members[1]!["url"]!.GetValue<string>());
        Assert.Null(members[2]!["upload"]!["bytes"]);

        session.Feed(new Send(id, 1000, 2));
        Assert.Empty(session.Of<Output.ReadUpload>());
        session.Feed(new Send(id, 3000, 0));
        var first = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Equal(0, first.Member);

        session.Feed(new Input.UploadRead(first.Epoch, id, 0, new byte[2048], true));
        Assert.Equal(0, session.Sent().Single()["member"]!.GetValue<int>());
        var next = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Equal(2, next.Member);
        Assert.Equal(1000, next.Count);
    }

    [Fact]
    public void An_ended_source_stops_its_upload_and_a_read_that_was_already_in_flight_is_ignored()
    {
        var (session, id) = Chunked();
        session.Feed(new Send(id, 100));
        var read = Assert.Single(session.Of<Output.ReadUpload>());
        session.Feed(new End(id, EndReason.Error));

        session.Feed(new Input.UploadRead(read.Epoch, id, null, new byte[5], false));

        Assert.Empty(session.Out);
    }

    [Fact]
    public void After_a_reconnect_the_upload_starts_again_from_the_header_with_no_credit()
    {
        var (session, id) = Chunked();
        session.Feed(new Send(id, 100));
        var stale = Assert.Single(session.Of<Output.ReadUpload>());
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());

        var resent = session.Sent().Single(m => m["id"]!.GetValue<string>() == id);
        Assert.Equal("image/jpeg", resent["upload"]!["contentType"]!.GetValue<string>());
        Assert.Empty(session.Of<Output.ReadUpload>());

        session.Feed(new Input.UploadRead(stale.Epoch, id, null, new byte[5], false));
        Assert.Empty(session.Out);
    }

    private static (Session, string) GroupOfTen()
    {
        var session = Session.Opened();
        var group = new Media.Group(new Media.Member[] { new Media.Upload("image/png", UploadContent.FromBytes(new byte[10])) });
        return (session, session.SetSource(new Source(group)));
    }

    [Fact]
    public void An_upload_of_known_length_sends_uploaded_when_the_bytes_sent_reach_the_length_even_if_the_credit_is_spent()
    {
        var (session, id) = GroupOfTen();
        session.Feed(new Send(id, 10, 0));
        var read = Assert.Single(session.Of<Output.ReadUpload>());
        Assert.Equal(10, read.Count);

        session.Feed(new Input.UploadRead(read.Epoch, id, 0, new byte[10], false));

        Assert.Equal("uploaded", session.Sent().Single()["type"]!.GetValue<string>());
        Assert.Empty(session.Of<Output.ReadUpload>());
    }

    [Fact]
    public void A_read_is_never_asked_for_more_than_the_bytes_left_of_a_known_length()
    {
        var (session, id) = GroupOfTen();

        session.Feed(new Send(id, 1000, 0));

        Assert.Equal(10, Assert.Single(session.Of<Output.ReadUpload>()).Count);
    }

    public static IEnumerable<object[]> Removals() => new[]
    {
        new object[] { "stop" },
        new object[] { "end" },
        new object[] { "rejected" },
        new object[] { "overloaded" },
    };

    [Theory]
    [MemberData(nameof(Removals))]
    public void When_the_current_upload_goes_away_the_next_credited_upload_starts_reading(string how)
    {
        var session = Session.Opened();
        var a = session.SetSource(new Source(new Media.Upload("image/jpeg", UploadContent.FromStream(() => new MemoryStream())), new SourceOptions(Live: true)));
        var b = session.SetSource(Session.UploadOf(UploadContent.FromStream(() => new MemoryStream())));
        session.Feed(new Send(b, 100));
        Assert.Empty(session.Of<Output.ReadUpload>());

        switch (how)
        {
            case "stop": session.Feed(new Input.StopSource(a)); break;
            case "end": session.Feed(new End(a, EndReason.Stopped)); break;
            case "rejected": session.Feed(new ErrorMessage("queue_full", "no", a)); break;
            default: session.Feed(new ErrorMessage("overloaded", "busy", a)); break;
        }

        Assert.Equal(b, Assert.Single(session.Of<Output.ReadUpload>()).Id);
    }
}
