using EyePop.Protocol;
using Xunit;

namespace EyePop.Tests;

public class MessageTests
{
    [Fact]
    public void Reconnecting_is_a_job_message_with_its_cause_attempt_and_delay()
    {
        var cause = new EyePopException(ErrorKind.Closed, "closed", closeCode: 1001);

        JobMessage message = new Reconnecting(cause, 3, TimeSpan.FromSeconds(4));

        var json = message.ToJson();
        Assert.Equal("reconnecting", json["type"]!.GetValue<string>());
        Assert.Equal(3, json["attempt"]!.GetValue<int>());
        Assert.Equal(4000, json["delay"]!.GetValue<long>());
        Assert.Equal("closed", json["cause"]!["kind"]!.GetValue<string>());
        Assert.Equal(1001, json["cause"]!["closeCode"]!.GetValue<int>());
    }

    [Fact]
    public void Reconnected_is_a_job_message()
    {
        JobMessage message = new Reconnected();

        Assert.Equal("reconnected", message.ToJson()["type"]!.GetValue<string>());
    }
}
