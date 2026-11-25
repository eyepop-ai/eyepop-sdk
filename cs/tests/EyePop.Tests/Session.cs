using System.Text.Json.Nodes;
using EyePop.Core;
using EyePop.Protocol;

namespace EyePop.Tests;

/// <summary>Drives the pure step with a replayable input sequence and a clock the test advances.</summary>
internal sealed class Session
{
    private static readonly DateTimeOffset Start = new(2026, 1, 1, 0, 0, 0, TimeSpan.Zero);

    public State State { get; private set; }
    public DateTimeOffset Now { get; private set; } = Start;
    public List<Output> Out { get; private set; } = new();

    public Session(State? state = null) => State = state ?? State.Initial();

    /// <summary>A session whose socket is open and whose pop (an empty one) has applied. Job ids continue from "2".</summary>
    public static Session Opened()
    {
        var session = new Session()
            .Feed(new Input.SetPop(new Pop(Array.Empty<PopComponent>())))
            .Feed(new Input.Opened())
            .Feed(new Input.Received(new Result("1")));
        session.Out.Clear();
        return session;
    }

    public Session Feed(Input input, double advanceSeconds = 0, double random = 0.5)
    {
        Now += TimeSpan.FromSeconds(advanceSeconds);
        var (state, outputs) = Machine.Step(State, input, new Moment(Now, random));
        State = state;
        Out = outputs.ToList();
        return this;
    }

    public Session Feed(IMessage message, double advanceSeconds = 0, double random = 0.5) =>
        Feed(new Input.Received(message), advanceSeconds, random);

    public Session Feed(Failure failure, double advanceSeconds = 0, double random = 0.5) =>
        Feed(new Input.Failed(failure), advanceSeconds, random);

    public IEnumerable<T> Of<T>() where T : Output => Out.OfType<T>();

    public IEnumerable<JsonNode> Sent() =>
        Of<Output.Send>().Select(s => s.Frame).OfType<TextFrame>().Select(f => JsonNode.Parse(f.Text)!);

    /// <summary>The shell's answer to a read request: it echoes the epoch and the token.</summary>
    public static Input.UploadRead Reply(Output.ReadUpload read, ReadOnlyMemory<byte> data, bool last) =>
        new(read.Epoch, read.Id, read.Token, read.Member, data, last);

    public string Issued() => Of<Output.Issued>().Single().Id;

    public string SetSource(Source source)
    {
        Feed(new Input.SetSource(source));
        return Issued();
    }

    public static Source Url(bool live = false) => new(new Media.Url("https://example.com/a.jpg"), new SourceOptions(Live: live));

    public static Source UploadOf(UploadContent content) => new(new Media.Upload("image/jpeg", content));

    public static UploadContent Bytes(int length) => UploadContent.FromBytes(new byte[length]);
}
