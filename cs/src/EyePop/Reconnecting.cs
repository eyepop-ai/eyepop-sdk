using System.Text.Json.Nodes;
using EyePop.Protocol;

namespace EyePop;

/// <summary>Added by the Pipeline, never sent by the server: a Job in flight sees it before each reconnect attempt.</summary>
public sealed record Reconnecting(EyePopException Cause, int Attempt, TimeSpan Delay) : JobMessage
{
    public override JsonNode ToJson()
    {
        var cause = new JsonObject { ["kind"] = Cause.Kind.ToWire() };
        if (Cause.Status is { } status) cause["status"] = status;
        if (Cause.CloseCode is { } closeCode) cause["closeCode"] = closeCode;
        if (Cause.Error is { } error) cause["error"] = error;
        return new JsonObject
        {
            ["type"] = "reconnecting",
            ["cause"] = cause,
            ["attempt"] = Attempt,
            ["delay"] = (long)Delay.TotalMilliseconds,
        };
    }
}

/// <summary>Added by the Pipeline: the new socket is open and the sources were sent again.</summary>
public sealed record Reconnected : JobMessage
{
    public override JsonNode ToJson() => new JsonObject { ["type"] = "reconnected" };
}
