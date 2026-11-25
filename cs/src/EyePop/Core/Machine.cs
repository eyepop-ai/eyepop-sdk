using System.Collections.Immutable;
using System.Text.Json.Nodes;
using EyePop.Protocol;

namespace EyePop.Core;

/// <summary>
/// The Pipeline's decisions as one pure function. It holds the pop, the open sources, upload credit and when
/// reconnecting began; it sends nothing, reads nothing and has no clock. The shell applies the outputs in order.
/// </summary>
internal static class Machine
{
    // A known length up to this goes as one combined frame, anything else in chunks.
    private const long CombinedLimit = 8 * 1024 * 1024;
    private const long ChunkSize = 64 * 1024;

    public static (State State, IReadOnlyList<Output> Outputs) Step(State state, Input input, Moment moment)
    {
        var outputs = new List<Output>();
        if (state.Phase == Phase.Closed)
        {
            return (RefuseAfterClose(state, input, outputs), outputs);
        }
        var next = input switch
        {
            Input.SetPop i => Issue(state, id => new SetPop(id, i.Pop), moment, outputs),
            Input.GetGraph i => Issue(state, id => new GetGraph(id, i.Format, i.Verbose), moment, outputs),
            Input.Ping => Issue(state, id => new Ping(id), moment, outputs),
            Input.SetSource i => OpenSource(state, i.Source, moment, outputs),
            Input.StopSource i => Stop(state, i.Id, moment, outputs),
            Input.Quit => Close(state, outputs),
            Input.Received i when state.Phase == Phase.Open => Receive(state, i.Message, moment, outputs),
            Input.Failed i when state.Phase is Phase.Open or Phase.Connecting => Fail(state, i.Failure, moment, outputs),
            Input.Opened when state.Phase == Phase.Connecting => Open(state, moment, outputs),
            Input.Opened when state.Phase == Phase.Open => state,
            // The socket opened after the Pipeline stopped waiting for it.
            Input.Opened => Discard(state, outputs),
            Input.ResendDue i when state.Phase == Phase.Open => Resend(state, i.Id, moment, outputs),
            Input.UploadRead i when state.Phase == Phase.Open && i.Epoch == state.Epoch => ReadUploaded(state, i, outputs),
            // A message from a socket that is already closed, or a stale answer: nothing to decide.
            _ => state,
        };
        return (next, outputs);
    }

    // Commands from the caller

    private static State Discard(State state, List<Output> outputs)
    {
        outputs.Add(new Output.CloseSocket());
        return state;
    }

    // close() is final: later commands fail with closed instead of vanishing.
    private static State RefuseAfterClose(State state, Input input, List<Output> outputs)
    {
        var closed = new EyePopException(ErrorKind.Closed, "the pipeline was closed");
        switch (input)
        {
            case Input.SetPop or Input.GetGraph or Input.Ping:
                var (command, s) = NewId(state);
                outputs.Add(new Output.Issued(command));
                outputs.Add(new Output.CommandFailed(command, closed));
                return s;
            case Input.SetSource:
                var (job, t) = NewId(state);
                outputs.Add(new Output.Issued(job));
                outputs.Add(new Output.CloseJob(job, closed));
                return t;
            case Input.Opened:
                return Discard(state, outputs);
            default:
                return state;
        }
    }

    private static State Issue(State state, Func<string, Command> build, Moment moment, List<Output> outputs)
    {
        var (id, s) = NewId(state);
        outputs.Add(new Output.Issued(id));
        var command = build(id);
        if (s.PopError is { } popError && command is not SetPop)
        {
            outputs.Add(new Output.CommandFailed(id, popError));
            return s;
        }
        s = s with { Pending = s.Pending.Add(new PendingCommand(id, command, false)) };
        if (command is SetPop)
        {
            s = s with { PopError = null };
        }
        return Dispatch(s, command, moment, outputs);
    }

    private static State OpenSource(State state, Source source, Moment moment, List<Output> outputs)
    {
        var (id, s) = NewId(state);
        outputs.Add(new Output.Issued(id));
        if (s.PopError is { } popError)
        {
            outputs.Add(new Output.CloseJob(id, popError));
            return s;
        }
        var open = new OpenSource(id, source);
        s = s with { Sources = s.Sources.Add(open) };
        return s.Phase switch
        {
            Phase.Open => Start(s, open, outputs),
            Phase.Idle => Connect(s, moment, outputs),
            _ => s,
        };
    }

    private static State Stop(State state, string id, Moment moment, List<Output> outputs)
    {
        if (state.Sources.FirstOrDefault(x => x.Id == id) is not { Stopping: false } source)
        {
            return state;
        }
        if (state.Phase == Phase.Open && !source.AwaitingResend)
        {
            outputs.Add(new Output.Send(FrameCodec.Encode(new StopSource(id))));
            var stopping = state with { Sources = state.Sources.Replace(source, source with { Stopping = true }) };
            return RemoveUploads(stopping, id, outputs);
        }
        // The server has no such source right now, so it will never answer with an end. A source that waited out
        // a resend delay left the healthy clock stopped; it was in effect sent now.
        return EndStopped(source.AwaitingResend ? state with { HealthySince = moment.Now } : state, source, outputs);
    }

    private static State EndStopped(State state, OpenSource source, List<Output> outputs)
    {
        outputs.Add(new Output.Deliver(source.Id, new End(source.Id, EndReason.Stopped)));
        outputs.Add(new Output.CloseJob(source.Id, null));
        return Without(state, source, outputs);
    }

    private static State Close(State state, List<Output> outputs)
    {
        if (state.Phase == Phase.Open)
        {
            var (id, s) = NewId(state);
            outputs.Add(new Output.Send(FrameCodec.Encode(new Quit(id))));
            state = s;
        }
        var closed = new EyePopException(ErrorKind.Closed, "the pipeline was closed");
        foreach (var source in state.Sources) outputs.Add(new Output.CloseJob(source.Id, null));
        foreach (var pending in state.Pending.Where(p => !p.SentByReconnect)) outputs.Add(new Output.CommandFailed(pending.Id, closed));
        // Also cancels a connect that is waiting out its delay.
        outputs.Add(new Output.GoIdle());
        return state with { Phase = Phase.Closed, Sources = ImmutableList<OpenSource>.Empty, Pending = ImmutableList<PendingCommand>.Empty, Uploads = ImmutableList<UploadTask>.Empty };
    }

    private static State Dispatch(State state, Command command, Moment moment, List<Output> outputs)
    {
        switch (state.Phase)
        {
            case Phase.Open:
                outputs.Add(new Output.Send(FrameCodec.Encode(command)));
                return state;
            case Phase.Idle:
                return Connect(state, moment, outputs);
            default:
                return state;
        }
    }

    private static State Connect(State state, Moment moment, List<Output> outputs)
    {
        outputs.Add(new Output.Connect(TimeSpan.Zero, false));
        return state with { Phase = Phase.Connecting, ReconnectingSince = moment.Now, AfterFailure = false, Attempt = 0, HealthySince = null, UpgradeRetried = false };
    }

    private static (string Id, State State) NewId(State state) => (state.NextId.ToString(), state with { NextId = state.NextId + 1 });

    // Sources and uploads

    private static State Start(State state, OpenSource open, List<Output> outputs)
    {
        var header = ToCommand(open.Id, open.Source);
        var s = state with { Sources = state.Sources.Replace(open, open with { AwaitingResend = false }) };
        // Each task gets its own token, so an answer to a read of an earlier send of this source finds no task.
        UploadTask Task(int? member, UploadContent content, bool requested = false, SetSource? head = null)
        {
            var task = new UploadTask(open.Id, s.NextId, member, content, Requested: requested, Header: head);
            s = s with { NextId = s.NextId + 1 };
            return task;
        }
        switch (open.Source.Media)
        {
            case Media.Upload upload when upload.Content.Length is <= CombinedLimit and { } length:
                if (upload.Content is UploadContent.BytesContent bytes)
                {
                    outputs.Add(new Output.Send(FrameCodec.Combined(header, bytes.Bytes)));
                    return s;
                }
                var whole = Task(null, upload.Content, requested: true, head: header);
                outputs.Add(new Output.ReadUpload(s.Epoch, open.Id, whole.Token, null, upload.Content, length, true));
                return s with { Uploads = s.Uploads.Add(whole) };
            case Media.Upload upload:
                outputs.Add(new Output.Send(FrameCodec.Encode(header)));
                var chunked = Task(null, upload.Content);
                return s with { Uploads = s.Uploads.Add(chunked) };
            case Media.Group group:
                outputs.Add(new Output.Send(FrameCodec.Encode(header)));
                var tasks = group.Members
                    .Select((member, index) => (member, index))
                    .Where(m => m.member is Media.Upload)
                    .Select(m => Task(m.index, ((Media.Upload)m.member).Content))
                    .ToList();
                return s with { Uploads = s.Uploads.AddRange(tasks) };
            default:
                outputs.Add(new Output.Send(FrameCodec.Encode(header)));
                return s;
        }
    }

    private static SetSource ToCommand(string id, Source source)
    {
        var o = source.Options;
        var command = new SetSource(id, Params: o.Params, Fps: o.Fps, Roi: o.Roi, Camera: o.Camera, Live: o.Live ? true : null);
        return source.Media switch
        {
            Media.Url url => command with { Url = url.Address },
            Media.Asset asset => command with { AssetUuid = asset.AssetUuid },
            Media.Upload upload => command with { Upload = new SetSourceUpload(upload.ContentType) },
            Media.Group group => command with { Group = group.Members.Select(ToGroupMember).ToList() },
            _ => throw new InvalidOperationException("Media is a closed hierarchy"),
        };
    }

    private static GroupMember ToGroupMember(Media.Member member) => member switch
    {
        Media.Url url => new GroupMemberUrl(url.Address),
        Media.Upload upload => new GroupMemberUpload(new GroupMemberUploadUpload(upload.ContentType, upload.Content.Length)),
        _ => throw new InvalidOperationException("Member is a closed hierarchy"),
    };

    private static State AddCredit(State state, string id, long? member, long bytes, List<Output> outputs)
    {
        var task = state.Uploads.FirstOrDefault(t => t.Id == id && t.Member == (int?)member && t.Header is null);
        return task is null
            ? state
            : Pump(state with { Uploads = state.Uploads.Replace(task, task with { Credit = task.Credit + bytes }) }, outputs);
    }

    // Only the first chunked upload may send, because a chunk frame names no upload.
    private static State Pump(State state, List<Output> outputs)
    {
        var current = state.Uploads.FirstOrDefault(t => t.Header is null);
        if (current is null || current.Requested || current.Credit <= 0)
        {
            return state;
        }
        var left = current.Content.Length is { } length ? length - current.Sent : long.MaxValue;
        outputs.Add(new Output.ReadUpload(state.Epoch, current.Id, current.Token, current.Member, current.Content, Math.Min(Math.Min(current.Credit, ChunkSize), left), false));
        return state with { Uploads = state.Uploads.Replace(current, current with { Requested = true }) };
    }

    private static State ReadUploaded(State state, Input.UploadRead read, List<Output> outputs)
    {
        var task = state.Uploads.FirstOrDefault(t => t.Id == read.Id && t.Token == read.Token);
        if (task is null)
        {
            return state;
        }
        if (task.Header is { } header)
        {
            outputs.Add(new Output.Send(FrameCodec.Combined(header, read.Data)));
            return state with { Uploads = state.Uploads.Remove(task) };
        }
        if (read.Data.Length > 0)
        {
            outputs.Add(new Output.Send(FrameCodec.Chunk(read.Data)));
        }
        var spent = task with { Credit = task.Credit - read.Data.Length, Requested = false, Sent = task.Sent + read.Data.Length };
        // With a known length the upload is over when its bytes are sent: waiting for an empty read would stall on spent credit.
        if (read.Last || spent.Content.Length <= spent.Sent)
        {
            outputs.Add(new Output.Send(FrameCodec.Encode(new Uploaded(read.Id, read.Member))));
            return Pump(state with { Uploads = state.Uploads.Remove(task) }, outputs);
        }
        return Pump(state with { Uploads = state.Uploads.Replace(task, spent) }, outputs);
    }

    // What the server says

    private static State Receive(State state, IMessage message, Moment moment, List<Output> outputs)
    {
        switch (message)
        {
            case Result r:
                return Answer(state, r.Id, r.ToJson(), outputs);
            case Pong p:
                return Answer(state, p.Id, p.ToJson(), outputs);
            case Send send:
                return AddCredit(state, send.Id, send.Member, send.Credit, outputs);
            case Credit credit:
                return AddCredit(state, credit.Id, credit.Member, credit.Bytes, outputs);
            case End end:
                return Ended(state, end, moment, outputs);
            case JobMessage job:
                if (OpenJob(state, JobId(job)) is not null)
                {
                    outputs.Add(new Output.Deliver(JobId(job)!, job));
                }
                return state;
            case ErrorMessage error:
                return Refused(state, error, moment, outputs);
            default:
                return state;
        }
    }

    private static string? JobId(JobMessage message) => message switch
    {
        Start m => m.Id,
        PredictionMessage m => m.Id,
        Dropped m => m.Id,
        Usage m => m.Id,
        End m => m.Id,
        _ => null,
    };

    private static OpenSource? OpenJob(State state, string? id) =>
        state.Sources.FirstOrDefault(s => s.Id == id && !s.AwaitingResend);

    private static State Answer(State state, string id, JsonNode answer, List<Output> outputs)
    {
        if (state.Pending.FirstOrDefault(p => p.Id == id) is not { } pending)
        {
            return state;
        }
        var s = state with { Pending = state.Pending.Remove(pending) };
        if (pending.Command is SetPop setPop)
        {
            s = s with { Pop = setPop.Pop };
        }
        if (!pending.SentByReconnect)
        {
            outputs.Add(new Output.Completed(id, answer));
        }
        return s;
    }

    private static State Ended(State state, End end, Moment moment, List<Output> outputs)
    {
        if (OpenJob(state, end.Id) is not { } source)
        {
            return state;
        }
        // A live source that ends this way is a stream that stopped, not a result: it starts again.
        if (source.Source.Options.Live && !source.Stopping && end.Reason is EndReason.Eos or EndReason.Error)
        {
            return ScheduleResend(state, source, moment, outputs);
        }
        outputs.Add(new Output.Deliver(end.Id, end));
        outputs.Add(new Output.CloseJob(end.Id, null));
        return Without(state, source, outputs);
    }

    private static State Refused(State state, ErrorMessage error, Moment moment, List<Output> outputs)
    {
        var rejected = new EyePopException(ErrorKind.CommandRejected, "the server refused the command", error: error.Error);
        if (state.Pending.FirstOrDefault(p => p.Id == error.Id) is { } pending)
        {
            var s = state with { Pending = state.Pending.Remove(pending) };
            if (pending.SentByReconnect)
            {
                return StopForPop(s, rejected, outputs);
            }
            outputs.Add(new Output.CommandFailed(pending.Id, rejected));
            return pending.Command is SetPop ? NoPopApplied(s, rejected) : s;
        }
        if (OpenJob(state, error.Id) is { } source)
        {
            if (source.Stopping)
            {
                return EndStopped(state, source, outputs);
            }
            if (error.Error == "overloaded")
            {
                // The server keeps refusing a finite source: after the give-up window the caller learns why.
                if (!source.Source.Options.Live && moment.Now - SeriesStart(state, moment) >= state.Settings.GiveUpDuration)
                {
                    outputs.Add(new Output.CloseJob(source.Id, rejected));
                    return Without(state, source, outputs);
                }
                return ScheduleResend(state, source, moment, outputs);
            }
            outputs.Add(new Output.CloseJob(source.Id, rejected));
            return Without(state, source, outputs);
        }
        outputs.Add(new Output.Status(rejected));
        return state;
    }

    // The next upload may be waiting on this one, so every removal looks again.
    private static State RemoveUploads(State state, string id, List<Output> outputs) =>
        Pump(state with { Uploads = state.Uploads.RemoveAll(t => t.Id == id) }, outputs);

    private static State Without(State state, OpenSource source, List<Output> outputs) =>
        RemoveUploads(state with { Sources = state.Sources.Remove(source) }, source.Id, outputs);

    private static State ScheduleResend(State state, OpenSource source, Moment moment, List<Output> outputs)
    {
        var series = SeriesStart(state, moment);
        var (s, delay) = NextBackoff(state, moment);
        outputs.Add(new Output.ScheduleResend(source.Id, delay));
        return RemoveUploads(
            s with { ReconnectingSince = series, Sources = s.Sources.Replace(source, source with { AwaitingResend = true }) },
            source.Id,
            outputs);
    }

    private static State Resend(State state, string id, Moment moment, List<Output> outputs)
    {
        if (state.Sources.FirstOrDefault(s => s.Id == id && s.AwaitingResend) is not { } source)
        {
            return state;
        }
        return Start(state with { HealthySince = moment.Now }, source, outputs);
    }

    // A socket that stayed open past the healthy limit starts the backoff series again.
    private static int CurrentAttempt(State state, Moment moment) =>
        state.Phase == Phase.Open && state.HealthySince is { } since && moment.Now - since >= state.Settings.HealthyDuration
            ? 0
            : state.Attempt;

    private static DateTimeOffset SeriesStart(State state, Moment moment) =>
        CurrentAttempt(state, moment) == 0 ? moment.Now : state.ReconnectingSince ?? moment.Now;

    // The healthy time starts when the resend goes out, not while it waits out its delay.
    private static (State State, TimeSpan Delay) NextBackoff(State state, Moment moment)
    {
        var attempt = CurrentAttempt(state, moment);
        var delay = Core.Backoff.Delay(attempt, moment.Random, state.Settings);
        return (state with { Attempt = attempt + 1, HealthySince = null }, delay);
    }

    // Supervision

    private static State Fail(State state, Failure failure, Moment moment, List<Output> outputs)
    {
        var verdict = Supervision.Classify(
            failure,
            popPending: state.Pending.Any(p => p.Command is SetPop),
            state.UpgradeRetried,
            hasWork: state.Sources.Count > 0 || state.Pending.Count > 0);
        switch (verdict)
        {
            case Verdict.Idle:
                outputs.Add(new Output.GoIdle());
                return state with { Phase = Phase.Idle, Uploads = ImmutableList<UploadTask>.Empty };
            case Verdict.Terminal terminal:
                return Terminate(state, terminal.Cause, outputs);
            case Verdict.PopStopped stopped:
                return state.Pending.FirstOrDefault(p => p.Command is SetPop) is { SentByReconnect: true }
                    ? StopForPop(state, stopped.Cause, outputs)
                    : Reconnect(FailPendingPop(state, stopped.Cause, outputs), new Verdict.Retry(stopped.Cause), moment, outputs);
            case Verdict.Retry retry:
                return Reconnect(state, retry, moment, outputs);
            default:
                return state;
        }
    }

    private static State FailPendingPop(State state, EyePopException cause, List<Output> outputs)
    {
        var pending = state.Pending.First(p => p.Command is SetPop);
        outputs.Add(new Output.CommandFailed(pending.Id, cause));
        return NoPopApplied(state with { Pending = state.Pending.Remove(pending) }, cause);
    }

    // A setPop that fails while no pop ever applied leaves nothing to fall back on: other commands fail until one works.
    private static State NoPopApplied(State state, EyePopException cause) =>
        state.Pop is null ? state with { PopError = cause } : state;

    // The pop a reconnect sent failed, and sending it again would fail the same way.
    private static State StopForPop(State state, EyePopException cause, List<Output> outputs) =>
        Terminate(state with { Pop = null, PopError = cause }, cause, outputs);

    // A cancelled source's Job ends the way the caller asked for, whatever went wrong meanwhile.
    private static void CloseWithCause(OpenSource source, EyePopException cause, List<Output> outputs)
    {
        if (source.Stopping)
        {
            outputs.Add(new Output.Deliver(source.Id, new End(source.Id, EndReason.Stopped)));
            outputs.Add(new Output.CloseJob(source.Id, null));
        }
        else
        {
            outputs.Add(new Output.CloseJob(source.Id, cause));
        }
    }

    private static State Terminate(State state, EyePopException cause, List<Output> outputs)
    {
        foreach (var source in state.Sources)
        {
            CloseWithCause(source, cause, outputs);
        }
        foreach (var pending in state.Pending.Where(p => !p.SentByReconnect)) outputs.Add(new Output.CommandFailed(pending.Id, cause));
        outputs.Add(new Output.GoIdle());
        return state with
        {
            Phase = Phase.Idle,
            Sources = ImmutableList<OpenSource>.Empty,
            Pending = ImmutableList<PendingCommand>.Empty,
            Uploads = ImmutableList<UploadTask>.Empty,
        };
    }

    private static State Reconnect(State state, Verdict.Retry retry, Moment moment, List<Output> outputs)
    {
        var since = state.Phase == Phase.Open ? SeriesStart(state, moment) : state.ReconnectingSince ?? moment.Now;
        var attempt = CurrentAttempt(state, moment);
        // Reconnecting at once is for the first failure of a series; an endless run of them would hammer the server.
        var delay = retry.Immediate && attempt == 0
            ? TimeSpan.Zero
            : Max(Min(retry.Floor ?? TimeSpan.Zero, state.Settings.CapDelay), Core.Backoff.Delay(attempt, moment.Random, state.Settings));
        var s = state with
        {
            Phase = Phase.Connecting,
            Attempt = attempt + 1,
            ReconnectingSince = since,
            AfterFailure = true,
            UpgradeRetried = state.UpgradeRetried || retry.UpgradeRetry,
            Uploads = ImmutableList<UploadTask>.Empty,
        };

        var gaveUp = moment.Now - since >= s.Settings.GiveUpDuration;
        if (gaveUp && s.Sources.All(x => !x.Source.Options.Live))
        {
            return Terminate(s, retry.Cause, outputs);
        }
        outputs.Add(new Output.CloseSocket());
        if (gaveUp)
        {
            foreach (var finite in s.Sources.Where(x => !x.Source.Options.Live))
            {
                CloseWithCause(finite, retry.Cause, outputs);
            }
            s = s with { Sources = s.Sources.RemoveAll(x => !x.Source.Options.Live) };
        }

        foreach (var source in s.Sources)
        {
            outputs.Add(new Output.Deliver(source.Id, new Reconnecting(retry.Cause, attempt + 1, delay)));
        }
        outputs.Add(new Output.Connect(delay, retry.ForceExchange));
        return s;
    }

    private static TimeSpan Max(TimeSpan a, TimeSpan b) => a > b ? a : b;

    private static TimeSpan Min(TimeSpan a, TimeSpan b) => a < b ? a : b;

    private static State Open(State state, Moment moment, List<Output> outputs)
    {
        var s = state with
        {
            Phase = Phase.Open,
            Epoch = state.Epoch + 1,
            HealthySince = moment.Now,
            UpgradeRetried = false,
            Uploads = ImmutableList<UploadTask>.Empty,
            Pending = state.Pending.RemoveAll(p => p.SentByReconnect),
        };
        if (s.Pop is { } pop)
        {
            var (id, withId) = NewId(s);
            var command = new SetPop(id, pop);
            s = withId with { Pending = withId.Pending.Insert(0, new PendingCommand(id, command, true)) };
        }
        foreach (var pending in s.Pending)
        {
            outputs.Add(new Output.Send(FrameCodec.Encode(pending.Command)));
        }
        foreach (var source in s.Sources)
        {
            s = source.Stopping ? EndStopped(s, source, outputs) : Start(s, source, outputs);
        }
        if (s.AfterFailure)
        {
            foreach (var source in s.Sources) outputs.Add(new Output.Deliver(source.Id, new Reconnected()));
        }
        return s with { AfterFailure = false };
    }
}
