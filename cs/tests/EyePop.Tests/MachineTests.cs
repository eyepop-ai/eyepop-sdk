using System.Text.Json.Nodes;
using EyePop.Core;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class MachineTests
{
    private static string Type(JsonNode n) => n["type"]!.GetValue<string>();

    [Fact]
    public void A_url_source_sends_a_setSource_with_the_id_the_state_assigned()
    {
        var session = Session.Opened();

        var id = session.SetSource(Session.Url());

        var sent = Assert.Single(session.Sent());
        Assert.Equal("setSource", Type(sent));
        Assert.Equal(id, sent["id"]!.GetValue<string>());
        Assert.Equal("https://example.com/a.jpg", sent["url"]!.GetValue<string>());
    }

    [Fact]
    public void Source_ids_are_unique_and_the_state_keeps_them_while_the_sources_are_open()
    {
        var session = Session.Opened();

        var first = session.SetSource(Session.Url());
        var second = session.SetSource(Session.Url());

        Assert.NotEqual(first, second);
        Assert.Equal(new[] { first, second }, session.State.Sources.Select(s => s.Id));
    }

    [Fact]
    public void The_options_reach_the_wire_and_no_mode_is_ever_sent()
    {
        var session = Session.Opened();
        var options = new SourceOptions(Fps: "5", Live: true, Roi: new RoiRectangle(0, 0, 1, 1));

        session.SetSource(new Source(new Media.Asset("uuid-1"), options));

        var sent = Assert.Single(session.Sent());
        Assert.Equal("uuid-1", sent["assetUuid"]!.GetValue<string>());
        Assert.Equal("5", sent["fps"]!.GetValue<string>());
        Assert.True(sent["live"]!.GetValue<bool>());
        Assert.Equal("rectangle", sent["roi"]!["type"]!.GetValue<string>());
        Assert.Null(sent["mode"]);
    }

    [Fact]
    public void A_source_that_is_not_live_sends_no_live_key()
    {
        var session = Session.Opened();

        session.SetSource(Session.Url());

        Assert.Null(Assert.Single(session.Sent())["live"]);
    }

    [Fact]
    public void A_setPop_changes_the_pop_only_when_the_server_answers_result()
    {
        var session = Session.Opened();
        var pop = new Pop(new PopComponent[] { new RawComponent("source") });

        session.Feed(new Input.SetPop(pop));
        var id = session.Issued();
        var before = session.State.Pop;
        session.Feed(new Result(id));

        Assert.NotSame(pop, before);
        Assert.Same(pop, session.State.Pop);
        Assert.Equal(id, Assert.Single(session.Of<Output.Completed>()).CommandId);
    }

    [Fact]
    public void A_refused_setPop_fails_that_command_with_the_servers_code_and_keeps_the_last_pop()
    {
        var session = Session.Opened();
        var applied = session.State.Pop;
        session.Feed(new Input.SetPop(new Pop(new PopComponent[] { new RawComponent("source") })));
        var id = session.Issued();

        session.Feed(new ErrorMessage("pop_invalid", "no such ability", id));

        var failed = Assert.Single(session.Of<Output.CommandFailed>());
        Assert.Equal(id, failed.CommandId);
        Assert.Equal(ErrorKind.CommandRejected, failed.Error.Kind);
        Assert.Equal("pop_invalid", failed.Error.Error);
        Assert.Same(applied, session.State.Pop);
        Assert.DoesNotContain(session.Out, o => o is Output.GoIdle or Output.Connect);
    }

    [Fact]
    public void A_ping_completes_on_pong_and_getGraph_on_result()
    {
        var session = Session.Opened();

        session.Feed(new Input.Ping());
        var ping = session.Issued();
        session.Feed(new Pong(ping));
        Assert.Equal(ping, Assert.Single(session.Of<Output.Completed>()).CommandId);

        session.Feed(new Input.GetGraph(GetGraphFormat.Dot, true));
        var graph = session.Issued();
        Assert.Equal("getGraph", Type(session.Sent().Single()));
        session.Feed(new Result(graph));
        Assert.Equal(graph, Assert.Single(session.Of<Output.Completed>()).CommandId);
    }

    [Fact]
    public void A_job_message_goes_to_its_own_job_only()
    {
        var session = Session.Opened();
        var a = session.SetSource(Session.Url());
        session.SetSource(Session.Url());

        session.Feed(new Dropped(a, 3));

        var delivered = Assert.Single(session.Of<Output.Deliver>());
        Assert.Equal(a, delivered.JobId);
        Assert.IsType<Dropped>(delivered.Message);
    }

    [Fact]
    public void A_message_for_an_id_that_is_not_open_and_an_unknown_message_are_ignored()
    {
        var session = Session.Opened();

        session.Feed(new Dropped("999", 1));
        Assert.Empty(session.Out);

        session.Feed(new UnknownMessage(new JsonObject { ["type"] = "from-the-future" }));
        Assert.Empty(session.Out);
    }

    [Fact]
    public void An_error_with_no_id_goes_to_status()
    {
        var session = Session.Opened();

        session.Feed(new ErrorMessage("internal", "boom"));

        var status = Assert.Single(session.Of<Output.Status>());
        Assert.Equal("internal", status.Error.Error);
    }

    [Fact]
    public void The_end_of_a_finite_source_is_delivered_and_ends_the_job()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());

        session.Feed(new End(id, EndReason.Error));

        Assert.IsType<End>(Assert.Single(session.Of<Output.Deliver>()).Message);
        var closed = Assert.Single(session.Of<Output.CloseJob>());
        Assert.Equal(id, closed.JobId);
        Assert.Null(closed.Error);
        Assert.Empty(session.State.Sources);
    }

    [Fact]
    public void An_error_for_a_command_other_than_overloaded_ends_that_job_and_leaves_the_socket_open()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());

        session.Feed(new ErrorMessage("queue_full", "too many open sources", id));

        var closed = Assert.Single(session.Of<Output.CloseJob>());
        Assert.Equal(ErrorKind.CommandRejected, closed.Error!.Kind);
        Assert.Equal("queue_full", closed.Error.Error);
        Assert.Empty(session.State.Sources);
        Assert.DoesNotContain(session.Out, o => o is Output.Connect or Output.GoIdle);
    }

    [Fact]
    public void Overloaded_for_a_setSource_sends_that_source_again_after_a_backoff_with_the_same_id()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());

        session.Feed(new ErrorMessage("overloaded", "busy", id), random: 1.0);
        var scheduled = Assert.Single(session.Of<Output.ScheduleResend>());
        Assert.Equal(id, scheduled.Id);
        Assert.Equal(TimeSpan.FromSeconds(1), scheduled.Delay);
        Assert.Empty(session.Of<Output.CloseJob>());

        session.Feed(new Input.ResendDue(id));
        Assert.Equal(id, Assert.Single(session.Sent())["id"]!.GetValue<string>());
    }

    [Fact]
    public void A_resend_that_is_already_covered_by_a_reconnect_is_not_sent_twice()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());
        session.Feed(new ErrorMessage("overloaded", "busy", id));
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());

        session.Feed(new Input.ResendDue(id));

        Assert.Empty(session.Out);
    }

    [Theory]
    [InlineData(EndReason.Eos)]
    [InlineData(EndReason.Error)]
    public void A_live_source_that_ends_with_eos_or_error_is_sent_again_and_its_end_is_not_delivered(EndReason reason)
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url(live: true));

        session.Feed(new End(id, reason));

        Assert.Equal(id, Assert.Single(session.Of<Output.ScheduleResend>()).Id);
        Assert.Empty(session.Of<Output.Deliver>());
        Assert.Empty(session.Of<Output.CloseJob>());
        Assert.Single(session.State.Sources);
    }

    [Fact]
    public void A_live_source_that_is_preempted_ends_the_job()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url(live: true));

        session.Feed(new End(id, EndReason.Preempted));

        Assert.Single(session.Of<Output.CloseJob>());
    }

    [Fact]
    public void Cancelling_sends_stopSource_and_the_job_ends_with_the_servers_end()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());

        session.Feed(new Input.StopSource(id));
        var sent = Assert.Single(session.Sent());
        Assert.Equal("stopSource", Type(sent));
        Assert.Equal(id, sent["id"]!.GetValue<string>());

        session.Feed(new End(id, EndReason.Stopped));
        Assert.Single(session.Of<Output.CloseJob>());
    }

    [Fact]
    public void A_message_received_while_not_connected_is_from_the_old_socket_and_is_dropped()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Dropped(id, 1));

        Assert.Empty(session.Out);
    }

    [Fact]
    public void A_command_while_idle_opens_a_socket_and_is_sent_when_it_opens()
    {
        var session = new Session();

        var id = session.SetSource(Session.Url());
        Assert.Equal(TimeSpan.Zero, Assert.Single(session.Of<Output.Connect>()).Delay);
        Assert.Empty(session.Sent());

        session.Feed(new Input.Opened());
        Assert.Equal(id, Assert.Single(session.Sent())["id"]!.GetValue<string>());
    }

    [Fact]
    public void A_command_while_reconnecting_waits_for_the_socket()
    {
        var session = Session.Opened();
        session.Feed(new Failure.SocketClosed(1001, null));

        var id = session.SetSource(Session.Url());

        Assert.Empty(session.Sent());
        session.Feed(new Input.Opened());
        Assert.Equal(id, session.Sent().Last()["id"]!.GetValue<string>());
    }

    [Fact]
    public void Quit_sends_quit_then_closes_the_socket_and_ends_every_job_normally()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());

        session.Feed(new Input.Quit());

        Assert.Equal("quit", Type(Assert.Single(session.Sent())));
        Assert.IsType<Output.GoIdle>(session.Out.Last());
        var closed = Assert.Single(session.Of<Output.CloseJob>());
        Assert.Equal(id, closed.JobId);
        Assert.Null(closed.Error);
    }

    [Fact]
    public void Quit_while_connecting_or_backing_off_cancels_the_connect()
    {
        var session = Session.Opened();
        session.SetSource(Session.Url());
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Input.Quit());

        Assert.Single(session.Of<Output.GoIdle>());
        Assert.Empty(session.Sent());
    }

    [Fact]
    public void An_open_that_arrives_after_quit_closes_the_socket()
    {
        var session = Session.Opened();
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Quit());

        session.Feed(new Input.Opened());

        Assert.Single(session.Of<Output.CloseSocket>());
        Assert.Empty(session.Sent());
    }

    [Fact]
    public void After_quit_a_command_fails_with_closed_instead_of_being_ignored()
    {
        var session = Session.Opened();
        session.Feed(new Input.Quit());

        var job = session.SetSource(Session.Url());
        Assert.Equal(job, Assert.Single(session.Of<Output.CloseJob>()).JobId);
        Assert.Equal(ErrorKind.Closed, session.Of<Output.CloseJob>().Single().Error!.Kind);

        session.Feed(new Input.Ping());
        var ping = session.Issued();
        var failed = Assert.Single(session.Of<Output.CommandFailed>());
        Assert.Equal(ping, failed.CommandId);
        Assert.Equal(ErrorKind.Closed, failed.Error.Kind);
    }

    [Fact]
    public void The_old_socket_is_closed_before_the_connect_that_replaces_it()
    {
        var session = Session.Opened();
        session.SetSource(Session.Url());

        session.Feed(Failure.Silent);

        var close = session.Out.FindIndex(o => o is Output.CloseSocket);
        var connect = session.Out.FindIndex(o => o is Output.Connect);
        Assert.True(close >= 0 && close < connect);
    }

    [Fact]
    public void The_done_message_changes_nothing()
    {
        var session = Session.Opened();

        session.Feed(new Done());

        Assert.Empty(session.Out);
    }

    [Fact]
    public void A_source_being_cancelled_is_not_sent_again_after_a_reconnect_and_its_job_ends_stopped()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url(live: true));
        session.Feed(new Input.StopSource(id));
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Input.Opened());

        Assert.DoesNotContain(session.Sent(), m => m["type"]!.GetValue<string>() == "setSource");
        var end = Assert.IsType<End>(session.Of<Output.Deliver>().Single(d => d.Message is End).Message);
        Assert.Equal(EndReason.Stopped, end.Reason);
        Assert.Equal(id, Assert.Single(session.Of<Output.CloseJob>()).JobId);
        Assert.Empty(session.State.Sources);
    }

    [Fact]
    public void A_live_source_being_cancelled_is_not_sent_again_when_the_server_ends_it_with_eos()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url(live: true));
        session.Feed(new Input.StopSource(id));

        session.Feed(new End(id, EndReason.Eos));

        Assert.Empty(session.Of<Output.ScheduleResend>());
        Assert.Single(session.Of<Output.CloseJob>());
    }

    [Fact]
    public void A_source_being_cancelled_is_not_sent_again_when_the_server_answers_overloaded()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url(live: true));
        session.Feed(new Input.StopSource(id));

        session.Feed(new ErrorMessage("overloaded", "busy", id));

        Assert.Empty(session.Of<Output.ScheduleResend>());
        Assert.Single(session.Of<Output.CloseJob>());
    }

    [Fact]
    public void A_source_waiting_to_be_sent_again_gets_no_messages()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());
        session.Feed(new ErrorMessage("overloaded", "busy", id));

        session.Feed(new Dropped(id, 1));

        Assert.Empty(session.Out);
    }

    [Fact]
    public void The_result_of_the_setPop_a_reconnect_sent_completes_no_command_and_keeps_the_pop()
    {
        var session = Session.Opened();
        var pop = session.State.Pop;
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());
        var replay = session.Sent().Single()["id"]!.GetValue<string>();

        session.Feed(new Result(replay));

        Assert.Empty(session.Out);
        Assert.Same(pop, session.State.Pop);
        Assert.DoesNotContain(session.State.Pending, p => p.Id == replay);
    }

    [Fact]
    public void A_second_reconnect_sends_one_setPop_not_the_stale_one_from_the_first()
    {
        var session = Session.Opened();
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Input.Opened());

        Assert.Single(session.Sent());
    }

    [Fact]
    public void Cancelling_while_reconnecting_sends_nothing_and_ends_the_job_stopped()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Input.StopSource(id));

        Assert.Empty(session.Of<Output.Send>());
        Assert.Equal(EndReason.Stopped, ((End)session.Of<Output.Deliver>().Single().Message).Reason);
        Assert.Single(session.Of<Output.CloseJob>());
    }

    [Fact]
    public void A_cancelled_source_the_server_refuses_for_any_code_ends_stopped_without_an_error()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());
        session.Feed(new Input.StopSource(id));

        session.Feed(new ErrorMessage("queue_full", "no", id));

        Assert.Equal(EndReason.Stopped, ((End)Assert.Single(session.Of<Output.Deliver>()).Message).Reason);
        Assert.Null(Assert.Single(session.Of<Output.CloseJob>()).Error);
    }

    [Fact]
    public void An_open_for_a_socket_that_is_already_open_changes_nothing()
    {
        var session = Session.Opened();

        session.Feed(new Input.Opened());

        Assert.Empty(session.Out);
    }
}
