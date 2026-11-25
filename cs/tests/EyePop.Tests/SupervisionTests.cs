using EyePop.Core;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

// Each test is a row of the supervision failure table in docs/sdk-interface.md.
public class SupervisionTests
{
    private static Session WithLiveJob(out string id)
    {
        var session = Session.Opened();
        id = session.SetSource(Session.Url(live: true));
        return session;
    }

    private static void AssertRetries(Session session, TimeSpan? delay = null, bool forceExchange = false)
    {
        var connect = Assert.Single(session.Of<Output.Connect>());
        if (delay is { } d) Assert.Equal(d, connect.Delay);
        Assert.Equal(forceExchange, connect.ForceExchange);
        Assert.Empty(session.Of<Output.CloseJob>());
        Assert.DoesNotContain(session.Out, o => o is Output.GoIdle);
    }

    private static void AssertTerminal(Session session, string id, ErrorKind kind)
    {
        var closed = Assert.Single(session.Of<Output.CloseJob>());
        Assert.Equal(id, closed.JobId);
        Assert.Equal(kind, closed.Error!.Kind);
        Assert.Single(session.Of<Output.GoIdle>());
        Assert.Empty(session.Of<Output.Connect>());
        Assert.Empty(session.State.Sources);
    }

    [Theory]
    [InlineData(null)]
    [InlineData(429)]
    [InlineData(500)]
    [InlineData(503)]
    public void An_exchange_that_cannot_connect_or_answers_429_or_5xx_is_retried_with_backoff(int? status)
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.Exchange(status), random: 1.0);

        AssertRetries(session, TimeSpan.FromSeconds(1));
    }

    [Theory]
    [InlineData(401)]
    [InlineData(403)]
    public void An_exchange_that_answers_401_or_403_is_a_terminal_exchange_failed(int status)
    {
        var session = WithLiveJob(out var id);

        session.Feed(new Failure.Exchange(status));

        AssertTerminal(session, id, ErrorKind.ExchangeFailed);
        Assert.Equal(status, session.Of<Output.CloseJob>().Single().Error!.Status);
    }

    [Theory]
    [InlineData(null)]
    [InlineData(502)]
    public void An_upgrade_that_cannot_connect_is_reset_or_times_out_is_retried_with_backoff(int? status)
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.Upgrade(status), random: 1.0);

        AssertRetries(session, TimeSpan.FromSeconds(1));
    }

    [Fact]
    public void An_upgrade_that_answers_503_waits_at_least_the_retry_after()
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.Upgrade(503, TimeSpan.FromSeconds(30)), random: 0.0);

        AssertRetries(session, TimeSpan.FromSeconds(30));
    }

    [Fact]
    public void An_upgrade_401_exchanges_again_and_retries_once_and_a_second_refusal_is_terminal()
    {
        var session = WithLiveJob(out var id);

        session.Feed(new Failure.Upgrade(401));
        AssertRetries(session, TimeSpan.Zero, forceExchange: true);

        session.Feed(new Failure.Upgrade(403));
        AssertTerminal(session, id, ErrorKind.UpgradeRefused);
    }

    [Fact]
    public void A_successful_open_gives_the_next_upgrade_refusal_its_retry_back()
    {
        var session = WithLiveJob(out _);
        session.Feed(new Failure.Upgrade(401));
        session.Feed(new Input.Opened());

        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Failure.Upgrade(401));

        AssertRetries(session, forceExchange: true);
    }

    [Fact]
    public void Close_1011_while_a_setPop_is_pending_fails_that_setPop_with_closed_keeps_the_last_pop_and_reconnects()
    {
        var session = WithLiveJob(out _);
        var applied = session.State.Pop;
        session.Feed(new Input.SetPop(new Pop(new PopComponent[] { new RawComponent("source") })));
        var pending = session.Issued();

        session.Feed(new Failure.SocketClosed(1011, "pipeline_stopped"));

        var failed = Assert.Single(session.Of<Output.CommandFailed>());
        Assert.Equal(pending, failed.CommandId);
        Assert.Equal(ErrorKind.Closed, failed.Error.Kind);
        Assert.Equal(1011, failed.Error.CloseCode);
        Assert.Same(applied, session.State.Pop);
        AssertRetries(session);

        session.Feed(new Input.Opened());
        Assert.Equal("setPop", session.Sent().First()["type"]!.GetValue<string>());
        Assert.DoesNotContain(session.Sent(), m => m["id"]!.GetValue<string>() == pending);
    }

    [Fact]
    public void The_same_failure_for_the_setPop_a_reconnect_sends_ends_every_job_and_goes_idle()
    {
        var session = Session.Opened();
        var a = session.SetSource(Session.Url(live: true));
        var b = session.SetSource(Session.Url());
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());
        var replay = session.Sent().First()["id"]!.GetValue<string>();

        session.Feed(new ErrorMessage("pop_invalid", "no such ability", replay));

        Assert.Equal(new[] { a, b }.Order(), session.Of<Output.CloseJob>().Select(c => c.JobId).Order());
        Assert.All(session.Of<Output.CloseJob>(), c => Assert.Equal(ErrorKind.CommandRejected, c.Error!.Kind));
        Assert.Single(session.Of<Output.GoIdle>());
        Assert.Null(session.State.Pop);
    }

    [Fact]
    public void Close_1011_while_the_reconnect_setPop_is_pending_ends_every_job_and_goes_idle()
    {
        var session = WithLiveJob(out var id);
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());

        session.Feed(new Failure.SocketClosed(1011, "pipeline_stopped"));

        AssertTerminal(session, id, ErrorKind.Closed);
    }

    [Fact]
    public void A_setPop_with_a_pop_that_works_brings_an_idle_pipeline_back_and_other_commands_fail_until_then()
    {
        var session = WithLiveJob(out _);
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());
        var replay = session.Sent().First()["id"]!.GetValue<string>();
        session.Feed(new ErrorMessage("pop_invalid", "no such ability", replay));

        var job = session.SetSource(Session.Url());
        Assert.Equal(ErrorKind.CommandRejected, Assert.Single(session.Of<Output.CloseJob>()).Error!.Kind);
        Assert.Empty(session.Of<Output.Connect>());
        Assert.Empty(session.State.Sources);

        session.Feed(new Input.SetPop(new Pop(new PopComponent[] { new RawComponent("source") })));
        Assert.Single(session.Of<Output.Connect>());
        session.Feed(new Input.Opened());
        var sent = Assert.Single(session.Sent());
        Assert.Equal("setPop", sent["type"]!.GetValue<string>());
        Assert.NotEqual(job, sent["id"]!.GetValue<string>());
    }

    [Theory]
    [InlineData(1001, null)]
    [InlineData(1011, "internal")]
    [InlineData(1008, "slow_client")]
    [InlineData(1008, "client_gone")]
    [InlineData(null, null)]
    public void These_closes_and_a_drop_with_no_close_frame_reconnect_with_backoff(int? code, string? reason)
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.SocketClosed(code, reason), random: 1.0);

        AssertRetries(session, TimeSpan.FromSeconds(1));
    }

    [Fact]
    public void Close_1008_credential_expired_exchanges_again_and_reconnects_at_once()
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.SocketClosed(1008, "credential_expired"), random: 1.0);

        AssertRetries(session, TimeSpan.Zero, forceExchange: true);
    }

    [Theory]
    [InlineData("unexpected_bytes")]
    [InlineData("credit_exceeded")]
    public void Close_1008_for_a_broken_upload_protocol_is_terminal_closed(string reason)
    {
        var session = WithLiveJob(out var id);

        session.Feed(new Failure.SocketClosed(1008, reason));

        AssertTerminal(session, id, ErrorKind.Closed);
        Assert.Equal(1008, session.Of<Output.CloseJob>().Single().Error!.CloseCode);
    }

    [Fact]
    public void A_socket_that_says_nothing_for_the_liveness_window_is_treated_as_dead_and_reconnected()
    {
        var session = WithLiveJob(out _);

        session.Feed(Failure.Silent, random: 1.0);

        AssertRetries(session, TimeSpan.FromSeconds(1));
    }

    [Fact]
    public void Close_1000_idle_leaves_the_pipeline_idle_when_nothing_is_open_and_reconnects_when_something_is()
    {
        var idle = Session.Opened();
        idle.Feed(new Failure.SocketClosed(1000, "idle"));
        Assert.Single(idle.Of<Output.GoIdle>());
        Assert.Empty(idle.Of<Output.Connect>());

        var busy = WithLiveJob(out _);
        busy.Feed(new Failure.SocketClosed(1000, "idle"));
        Assert.Single(busy.Of<Output.Connect>());
    }

    // The rest of the supervision rules.

    [Fact]
    public void Every_job_in_flight_sees_reconnecting_before_the_attempt_and_reconnected_after_it()
    {
        var session = Session.Opened();
        var a = session.SetSource(Session.Url(live: true));
        var b = session.SetSource(Session.Url());

        session.Feed(new Failure.SocketClosed(1001, null), random: 1.0);
        var reconnecting = session.Of<Output.Deliver>().ToList();
        Assert.Equal(new[] { a, b }, reconnecting.Select(d => d.JobId));
        var message = Assert.IsType<Reconnecting>(reconnecting[0].Message);
        Assert.Equal(1, message.Attempt);
        Assert.Equal(TimeSpan.FromSeconds(1), message.Delay);
        Assert.Equal(1001, message.Cause.CloseCode);

        session.Feed(new Input.Opened());
        var after = session.Of<Output.Deliver>().ToList();
        Assert.Equal(new[] { a, b }, after.Select(d => d.JobId));
        Assert.All(after, d => Assert.IsType<Reconnected>(d.Message));
    }

    [Fact]
    public void A_reconnect_sets_the_current_pop_then_sends_every_unended_source_in_order_with_its_id()
    {
        var session = Session.Opened();
        var a = session.SetSource(Session.Url());
        var ended = session.SetSource(Session.Url());
        var c = session.SetSource(Session.Url(live: true));
        session.Feed(new End(ended, EndReason.Eos));
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Input.Opened());

        var sent = session.Sent().ToList();
        Assert.Equal(new[] { "setPop", "setSource", "setSource" }, sent.Select(m => m["type"]!.GetValue<string>()));
        Assert.Equal(new[] { a, c }, sent.Skip(1).Select(m => m["id"]!.GetValue<string>()));
    }

    [Fact]
    public void A_setPop_still_pending_when_the_socket_drops_is_sent_again_after_the_current_pop()
    {
        var session = Session.Opened();
        session.Feed(new Input.SetPop(new Pop(new PopComponent[] { new RawComponent("source") })));
        var pending = session.Issued();
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Input.Opened());

        var ids = session.Sent().Select(m => m["id"]!.GetValue<string>()).ToList();
        Assert.Equal(2, ids.Count);
        Assert.Equal(pending, ids[1]);
    }

    [Fact]
    public void Backoff_grows_with_each_failure_and_resets_after_30_seconds_open()
    {
        var session = Session.Opened();

        session.Feed(new Failure.SocketClosed(1001, null), random: 1.0);
        Assert.Equal(TimeSpan.FromSeconds(1), session.Of<Output.Connect>().Single().Delay);
        session.Feed(new Failure.Upgrade(null), random: 1.0);
        Assert.Equal(TimeSpan.FromSeconds(2), session.Of<Output.Connect>().Single().Delay);
        session.Feed(new Failure.Upgrade(null), random: 1.0);
        Assert.Equal(TimeSpan.FromSeconds(4), session.Of<Output.Connect>().Single().Delay);

        session.Feed(new Input.Opened());
        session.Feed(new Failure.SocketClosed(1001, null), advanceSeconds: 5, random: 1.0);
        Assert.Equal(TimeSpan.FromSeconds(8), session.Of<Output.Connect>().Single().Delay);

        session.Feed(new Input.Opened());
        session.Feed(new Failure.SocketClosed(1001, null), advanceSeconds: 31, random: 1.0);
        Assert.Equal(TimeSpan.FromSeconds(1), session.Of<Output.Connect>().Single().Delay);
    }

    [Fact]
    public void After_15_minutes_of_failing_a_finite_job_ends_with_the_last_error_and_a_live_job_keeps_going()
    {
        var session = Session.Opened();
        var finite = session.SetSource(Session.Url());
        var live = session.SetSource(Session.Url(live: true));
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Failure.Upgrade(503), advanceSeconds: 15 * 60);

        var closed = Assert.Single(session.Of<Output.CloseJob>());
        Assert.Equal(finite, closed.JobId);
        Assert.Equal(ErrorKind.UpgradeRefused, closed.Error!.Kind);
        Assert.Single(session.Of<Output.Connect>());
        Assert.Equal(live, Assert.Single(session.State.Sources).Id);
    }

    [Fact]
    public void After_15_minutes_of_failing_with_no_live_source_left_the_pipeline_goes_idle()
    {
        var session = Session.Opened();
        var finite = session.SetSource(Session.Url());
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Failure.Upgrade(null), advanceSeconds: 15 * 60);

        Assert.Equal(finite, Assert.Single(session.Of<Output.CloseJob>()).JobId);
        Assert.Single(session.Of<Output.GoIdle>());
        Assert.Empty(session.Of<Output.Connect>());
    }

    [Fact]
    public void Just_under_15_minutes_keeps_every_job()
    {
        var session = Session.Opened();
        session.SetSource(Session.Url());
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Failure.Upgrade(null), advanceSeconds: 15 * 60 - 1);

        Assert.Empty(session.Of<Output.CloseJob>());
        Assert.Single(session.Of<Output.Connect>());
    }

    [Fact]
    public void A_terminal_failure_fails_the_pending_commands_too()
    {
        var session = WithLiveJob(out _);
        session.Feed(new Input.Ping());
        var ping = session.Issued();

        session.Feed(new Failure.Exchange(401));

        Assert.Equal(ping, Assert.Single(session.Of<Output.CommandFailed>()).CommandId);
    }

    [Fact]
    public void Close_1011_with_a_setPop_pending_for_any_reason_but_pipeline_stopped_reconnects_and_sends_the_setPop_again()
    {
        var session = WithLiveJob(out _);
        session.Feed(new Input.SetPop(new Pop(new PopComponent[] { new RawComponent("source") })));
        var pending = session.Issued();

        session.Feed(new Failure.SocketClosed(1011, "internal"));

        Assert.Empty(session.Of<Output.CommandFailed>());
        AssertRetries(session);
        session.Feed(new Input.Opened());
        Assert.Contains(session.Sent(), m => m["id"]!.GetValue<string>() == pending);
    }

    [Fact]
    public void The_credential_expired_reconnect_at_once_is_for_the_first_failure_of_a_series_only()
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.SocketClosed(1008, "credential_expired"), random: 1.0);
        Assert.Equal(TimeSpan.Zero, session.Of<Output.Connect>().Single().Delay);

        session.Feed(new Input.Opened());
        session.Feed(new Failure.SocketClosed(1008, "credential_expired"), advanceSeconds: 2, random: 1.0);
        var second = session.Of<Output.Connect>().Single();
        Assert.Equal(TimeSpan.FromSeconds(2), second.Delay);
        Assert.True(second.ForceExchange);
    }

    [Fact]
    public void The_credential_expired_reconnect_at_once_comes_back_after_30_healthy_seconds()
    {
        var session = WithLiveJob(out _);
        session.Feed(new Failure.SocketClosed(1008, "credential_expired"));
        session.Feed(new Input.Opened());

        session.Feed(new Failure.SocketClosed(1008, "credential_expired"), advanceSeconds: 31, random: 1.0);

        Assert.Equal(TimeSpan.Zero, session.Of<Output.Connect>().Single().Delay);
    }

    [Theory]
    [InlineData(400)]
    [InlineData(404)]
    public void An_exchange_status_other_than_401_403_429_and_5xx_is_terminal(int status)
    {
        var session = WithLiveJob(out var id);

        session.Feed(new Failure.Exchange(status));

        AssertTerminal(session, id, ErrorKind.ExchangeFailed);
    }

    [Theory]
    [InlineData(400)]
    [InlineData(404)]
    public void An_upgrade_status_other_than_401_403_429_and_5xx_is_terminal(int status)
    {
        var session = WithLiveJob(out var id);

        session.Feed(new Failure.Upgrade(status));

        AssertTerminal(session, id, ErrorKind.UpgradeRefused);
    }

    [Fact]
    public void An_upgrade_that_answers_429_is_retried_with_backoff()
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.Upgrade(429), random: 1.0);

        AssertRetries(session, TimeSpan.FromSeconds(1));
    }

    [Fact]
    public void A_retry_after_longer_than_the_backoff_cap_is_capped_at_it()
    {
        var session = WithLiveJob(out _);

        session.Feed(new Failure.Upgrade(503, TimeSpan.FromHours(6)), random: 0.0);

        AssertRetries(session, TimeSpan.FromSeconds(60));
    }

    [Fact]
    public void A_finite_source_the_server_keeps_refusing_as_overloaded_ends_after_the_give_up_window()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());
        var live = session.SetSource(Session.Url(live: true));

        for (var i = 0; i < 60 && !session.Of<Output.CloseJob>().Any(); i++)
        {
            session.Feed(new ErrorMessage("overloaded", "busy", id), advanceSeconds: 1, random: 1.0);
            if (session.Of<Output.ScheduleResend>().SingleOrDefault() is { } resend)
            {
                session.Feed(new Input.ResendDue(id), advanceSeconds: resend.Delay.TotalSeconds);
            }
        }

        var closed = Assert.Single(session.Of<Output.CloseJob>());
        Assert.Equal(id, closed.JobId);
        Assert.Equal(ErrorKind.CommandRejected, closed.Error!.Kind);
        Assert.Equal("overloaded", closed.Error.Error);
        Assert.Equal(live, Assert.Single(session.State.Sources).Id);
    }

    [Fact]
    public void A_socket_that_opens_and_fails_again_and_again_still_reaches_the_give_up_limit()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());

        for (var i = 0; i < 60 && !session.Of<Output.CloseJob>().Any(); i++)
        {
            session.Feed(new Failure.SocketClosed(1001, null), advanceSeconds: 5, random: 1.0);
            if (!session.Of<Output.CloseJob>().Any())
            {
                session.Feed(new Input.Opened(), advanceSeconds: 54);
            }
        }

        Assert.Equal(id, Assert.Single(session.Of<Output.CloseJob>()).JobId);
    }

    [Fact]
    public void A_socket_healthy_for_30_seconds_starts_the_give_up_clock_again()
    {
        var session = Session.Opened();
        session.SetSource(Session.Url());
        session.Feed(new Failure.SocketClosed(1001, null));
        session.Feed(new Input.Opened());

        session.Feed(new Failure.SocketClosed(1001, null), advanceSeconds: 16 * 60);

        Assert.Empty(session.Of<Output.CloseJob>());
    }

    [Fact]
    public void Cancelling_a_source_that_waits_to_be_sent_again_does_not_leave_the_healthy_clock_stopped()
    {
        var session = Session.Opened();
        var cancelled = session.SetSource(Session.Url());
        var other = session.SetSource(Session.Url());
        session.Feed(new ErrorMessage("overloaded", "busy", cancelled), advanceSeconds: 1, random: 1.0);
        session.Feed(new Input.StopSource(cancelled));

        session.Feed(new Failure.SocketClosed(1001, null), advanceSeconds: 16 * 60, random: 1.0);

        Assert.DoesNotContain(session.Of<Output.CloseJob>(), c => c.JobId == other);
        Assert.Equal(TimeSpan.FromSeconds(1), session.Of<Output.Connect>().Single().Delay);
    }

    [Fact]
    public void A_resend_that_went_out_starts_the_healthy_time()
    {
        var session = Session.Opened();
        var id = session.SetSource(Session.Url());
        session.Feed(new ErrorMessage("overloaded", "busy", id), advanceSeconds: 1, random: 1.0);
        session.Feed(new Input.ResendDue(id), advanceSeconds: 1);

        session.Feed(new Failure.SocketClosed(1001, null), advanceSeconds: 31, random: 1.0);

        Assert.Equal(TimeSpan.FromSeconds(1), session.Of<Output.Connect>().Single().Delay);
    }

    [Fact]
    public void The_wait_for_a_resend_is_not_healthy_time()
    {
        var session = Session.Opened();
        var a = session.SetSource(Session.Url());
        var b = session.SetSource(Session.Url());
        session.Feed(new ErrorMessage("overloaded", "busy", a), advanceSeconds: 40, random: 1.0);
        Assert.Equal(TimeSpan.FromSeconds(1), session.Of<Output.ScheduleResend>().Single().Delay);

        session.Feed(new ErrorMessage("overloaded", "busy", b), advanceSeconds: 1, random: 1.0);

        Assert.Equal(TimeSpan.FromSeconds(2), session.Of<Output.ScheduleResend>().Single().Delay);
    }

    [Fact]
    public void A_cancelled_finite_source_met_by_the_give_up_limit_ends_stopped_not_with_the_error()
    {
        var session = Session.Opened();
        var cancelled = session.SetSource(Session.Url());
        session.SetSource(Session.Url(live: true));
        session.Feed(new Input.StopSource(cancelled));
        session.Feed(new Failure.SocketClosed(1001, null));

        session.Feed(new Failure.Upgrade(null), advanceSeconds: 15 * 60);

        Assert.Equal(EndReason.Stopped, ((End)session.Of<Output.Deliver>().Single(d => d.Message is End).Message).Reason);
        var closed = Assert.Single(session.Of<Output.CloseJob>());
        Assert.Equal(cancelled, closed.JobId);
        Assert.Null(closed.Error);
    }

    [Fact]
    public void A_cancelled_finite_source_met_by_a_terminal_failure_ends_stopped_too()
    {
        var session = Session.Opened();
        var cancelled = session.SetSource(Session.Url());
        session.Feed(new Input.StopSource(cancelled));

        session.Feed(new Failure.Exchange(401));

        Assert.Null(Assert.Single(session.Of<Output.CloseJob>()).Error);
    }

    [Fact]
    public void A_refused_first_setPop_keeps_other_commands_failing_until_a_pop_works()
    {
        var session = new Session();
        session.Feed(new Input.SetPop(new Pop(new PopComponent[] { new RawComponent("source") })));
        var pop = session.Issued();
        session.Feed(new Input.Opened());

        session.Feed(new ErrorMessage("pop_invalid", "no such ability", pop));
        session.Feed(new Input.SetSource(Session.Url()));

        Assert.Equal(ErrorKind.CommandRejected, Assert.Single(session.Of<Output.CloseJob>()).Error!.Kind);
        Assert.Empty(session.Of<Output.Send>());
    }

    [Fact]
    public void A_first_setPop_that_fails_with_1011_keeps_other_commands_failing_until_a_pop_works()
    {
        var session = new Session();
        session.Feed(new Input.SetPop(new Pop(new PopComponent[] { new RawComponent("source") })));
        session.Feed(new Input.Opened());
        session.Feed(new Failure.SocketClosed(1011, "pipeline_stopped"));

        session.Feed(new Input.Ping());

        Assert.Equal(ErrorKind.Closed, Assert.Single(session.Of<Output.CommandFailed>()).Error.Kind);
    }
}
