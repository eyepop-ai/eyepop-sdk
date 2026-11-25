using System.Net;
using System.Net.WebSockets;
using System.Text;
using EyePop.Core;
using Xunit;

namespace EyePop.Tests;

/// <summary>The real client socket against an in-process server on a loopback port. No network beyond loopback.</summary>
public sealed class ClientWebSocketFactoryTests : IDisposable
{
    private readonly HttpListener _listener = new();
    private readonly Uri _url;

    public ClientWebSocketFactoryTests()
    {
        // Port 0 is not allowed by HttpListener, so take a free one.
        var probe = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0);
        probe.Start();
        var port = ((IPEndPoint)probe.LocalEndpoint).Port;
        probe.Stop();
        _listener.Prefixes.Add($"http://127.0.0.1:{port}/");
        _listener.Start();
        _url = new Uri($"http://127.0.0.1:{port}");
    }

    public void Dispose() => _listener.Close();

    [Fact]
    public void The_endpoint_is_the_pipeline_path_over_ws_or_wss()
    {
        Assert.Equal("ws://127.0.0.1:9002/api/v1/pipeline", ClientWebSocketFactory.Endpoint(new Uri("http://127.0.0.1:9002")).ToString());
        Assert.Equal("wss://pipeline.example.com/api/v1/pipeline", ClientWebSocketFactory.Endpoint(new Uri("https://pipeline.example.com/")).ToString());
    }

    [Fact]
    public async Task Connects_with_the_subprotocol_and_the_bearer_token_then_exchanges_text_and_binary_frames_and_the_close_code()
    {
        var served = Task.Run(async () =>
        {
            var context = await _listener.GetContextAsync();
            var auth = context.Request.Headers["Authorization"];
            var upgrade = await context.AcceptWebSocketAsync("eyepop.v1");
            var socket = upgrade.WebSocket;
            var buffer = new byte[1024];
            var received = await socket.ReceiveAsync(buffer, default);
            await socket.SendAsync(Encoding.UTF8.GetBytes($"{auth}|{socket.SubProtocol}|{Encoding.UTF8.GetString(buffer, 0, received.Count)}"), WebSocketMessageType.Text, true, default);
            await socket.SendAsync(new byte[] { 1, 2, 3 }, WebSocketMessageType.Binary, true, default);
            await socket.CloseAsync((WebSocketCloseStatus)1008, "credential_expired", default);
        });

        var socket = await new ClientWebSocketFactory().ConnectAsync(_url, "the-jwt", default);
        await socket.SendAsync(new TextFrame("hello"), default);
        var text = await socket.ReceiveAsync(default);
        var binary = await socket.ReceiveAsync(default);
        var closed = await socket.ReceiveAsync(default);

        Assert.Equal("Bearer the-jwt|eyepop.v1|hello", ((TextFrame)((Inbound.Message)text).Frame).Text);
        Assert.Equal(new byte[] { 1, 2, 3 }, ((BinaryFrame)((Inbound.Message)binary).Frame).Bytes.ToArray());
        Assert.Equal(new Inbound.Closed(1008, "credential_expired"), closed);
        await socket.DisposeAsync();
        await served.WaitAsync(TimeSpan.FromSeconds(5));
    }

    [Fact]
    public async Task An_upgrade_the_server_refuses_reports_its_status_and_Retry_After()
    {
        var served = Task.Run(async () =>
        {
            var context = await _listener.GetContextAsync();
            context.Response.StatusCode = 503;
            context.Response.Headers["Retry-After"] = "12";
            context.Response.Close();
        });

        var failure = await Assert.ThrowsAsync<UpgradeException>(() => new ClientWebSocketFactory().ConnectAsync(_url, null, default));

        Assert.Equal(503, failure.Status);
        Assert.Equal(TimeSpan.FromSeconds(12), failure.RetryAfter);
        await served;
    }

    [Fact]
    public async Task A_server_that_is_not_there_is_an_upgrade_failure_with_no_status()
    {
        _listener.Close();

        var failure = await Assert.ThrowsAsync<UpgradeException>(() => new ClientWebSocketFactory().ConnectAsync(_url, null, default));

        Assert.Null(failure.Status);
    }

    [Fact]
    public async Task A_dropped_connection_with_no_close_frame_is_Closed_with_no_code()
    {
        var served = Task.Run(async () =>
        {
            var context = await _listener.GetContextAsync();
            var upgrade = await context.AcceptWebSocketAsync("eyepop.v1");
            upgrade.WebSocket.Abort();
            context.Response.Abort();
        });

        await using var socket = await new ClientWebSocketFactory().ConnectAsync(_url, null, default);
        var closed = await socket.ReceiveAsync(default).WaitAsync(TimeSpan.FromSeconds(5));

        Assert.Equal(new Inbound.Closed(null, null), closed);
        await served.WaitAsync(TimeSpan.FromSeconds(5));
    }
}
