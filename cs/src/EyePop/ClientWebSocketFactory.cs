using System.Net.WebSockets;
using System.Text;
using EyePop.Core;

namespace EyePop;

/// <summary>Opens the pipeline socket with subprotocol eyepop.v1 and the token in the Authorization header.</summary>
internal sealed class ClientWebSocketFactory(TimeProvider time) : ISocketFactory
{
    // The server closes a socket silent for 40 s, so the client socket answers its pings (and sends its own) every 20 s.
    private static readonly TimeSpan KeepAlive = TimeSpan.FromSeconds(20);

    public async Task<ISocket> ConnectAsync(Uri pipelineUrl, string? jwt, CancellationToken ct)
    {
        var socket = new ClientWebSocket();
        socket.Options.AddSubProtocol("eyepop.v1");
        socket.Options.KeepAliveInterval = KeepAlive;
        socket.Options.CollectHttpResponseDetails = true;
        if (jwt is not null)
        {
            socket.Options.SetRequestHeader("Authorization", $"Bearer {jwt}");
        }
        try
        {
            await socket.ConnectAsync(Endpoint(pipelineUrl), ct).ConfigureAwait(false);
            return new ClientWebSocketAdapter(socket);
        }
        catch (Exception e) when (e is WebSocketException or HttpRequestException or IOException)
        {
            var status = (int)socket.HttpStatusCode is >= 100 and not 101 ? (int?)socket.HttpStatusCode : null;
            var after = socket.HttpResponseHeaders is { } headers && headers.TryGetValue("Retry-After", out var values)
                ? RetryAfter.Parse(values.FirstOrDefault(), time.GetUtcNow())
                : null;
            socket.Dispose();
            throw new UpgradeException(status, after);
        }
        catch
        {
            socket.Dispose();
            throw;
        }
    }

    internal static Uri Endpoint(Uri pipelineUrl)
    {
        var builder = new UriBuilder(pipelineUrl) { Scheme = pipelineUrl.Scheme == Uri.UriSchemeHttps ? "wss" : "ws" };
        builder.Path = builder.Path.TrimEnd('/') + "/api/v1/pipeline";
        return builder.Uri;
    }
}

internal sealed class ClientWebSocketAdapter(ClientWebSocket socket) : ISocket
{
    private static readonly TimeSpan CloseTimeout = TimeSpan.FromSeconds(5);

    public async Task SendAsync(Frame frame, CancellationToken ct)
    {
        try
        {
            var (bytes, type) = frame switch
            {
                TextFrame text => (new ReadOnlyMemory<byte>(Encoding.UTF8.GetBytes(text.Text)), WebSocketMessageType.Text),
                BinaryFrame binary => (binary.Bytes, WebSocketMessageType.Binary),
                _ => throw new InvalidOperationException("Frame is a closed hierarchy"),
            };
            await socket.SendAsync(bytes, type, true, ct).ConfigureAwait(false);
        }
        catch (Exception e) when (e is WebSocketException or ObjectDisposedException or InvalidOperationException)
        {
            throw new IOException("the socket is closed", e);
        }
    }

    public async Task<Inbound> ReceiveAsync(CancellationToken ct)
    {
        var message = new MemoryStream();
        var buffer = new byte[16 * 1024];
        try
        {
            while (true)
            {
                var result = await socket.ReceiveAsync(buffer, ct).ConfigureAwait(false);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    return new Inbound.Closed((int?)result.CloseStatus, result.CloseStatusDescription);
                }
                message.Write(buffer, 0, result.Count);
                if (result.EndOfMessage)
                {
                    return new Inbound.Message(result.MessageType == WebSocketMessageType.Text
                        ? new TextFrame(Encoding.UTF8.GetString(message.GetBuffer(), 0, (int)message.Length))
                        : new BinaryFrame(message.ToArray()));
                }
            }
        }
        catch (Exception e) when (e is WebSocketException or ObjectDisposedException or IOException)
        {
            return new Inbound.Closed(null, null);
        }
    }

    public async ValueTask DisposeAsync()
    {
        // After the server's close the handshake is finished by answering it.
        if (socket.State is WebSocketState.Open or WebSocketState.CloseReceived)
        {
            using var timeout = new CancellationTokenSource(CloseTimeout);
            try
            {
                await socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, null, timeout.Token).ConfigureAwait(false);
            }
            catch (Exception e) when (e is WebSocketException or OperationCanceledException or ObjectDisposedException)
            {
            }
        }
        socket.Dispose();
    }
}
