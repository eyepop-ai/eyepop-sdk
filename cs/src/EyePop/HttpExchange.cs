using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace EyePop;

/// <summary>Trades the API key for a short-lived token. Nothing it throws holds the key or the token.</summary>
internal sealed class HttpExchange : IExchange
{
    // One client for the process, as HttpClient is meant to be used. Pooled connections are recycled, so a
    // long-running process notices a changed DNS record of the auth service.
    private static readonly HttpClient Shared = new(new SocketsHttpHandler { PooledConnectionLifetime = TimeSpan.FromMinutes(5) })
    {
        Timeout = Timeout.InfiniteTimeSpan,
    };
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(30);

    private readonly HttpClient _http;
    private readonly Auth.Exchange _auth;
    private readonly Guid? _accountUuid;
    private readonly TimeProvider _time;

    public HttpExchange(Auth.Exchange auth, Guid? accountUuid, TimeProvider time, HttpClient? http = null)
    {
        _auth = auth;
        _accountUuid = accountUuid;
        _time = time;
        _http = http ?? Shared;
    }

    public async Task<Token> ExchangeAsync(CancellationToken ct)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, Url());
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _auth.ApiKey);
        using var timeout = new CancellationTokenSource(RequestTimeout, _time);
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(ct, timeout.Token);
        try
        {
            using var response = await _http.SendAsync(request, linked.Token).ConfigureAwait(false);
            var status = (int)response.StatusCode;
            if (!response.IsSuccessStatusCode)
            {
                var after = response.Headers.TryGetValues("Retry-After", out var values) ? values.FirstOrDefault() : null;
                throw new ExchangeException(status, RetryAfter.Parse(after, _time.GetUtcNow()));
            }
            var body = await response.Content.ReadAsStringAsync(linked.Token).ConfigureAwait(false);
            return ParseToken(body, status);
        }
        catch (HttpRequestException)
        {
            throw new ExchangeException(null, null);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            throw new ExchangeException(null, null);
        }
    }

    // A 200 that is not a token is not something a retry would fix.
    private Token ParseToken(string body, int status)
    {
        try
        {
            if (JsonNode.Parse(body) is JsonObject obj
                && obj["access_token"] is JsonValue jwt && jwt.TryGetValue<string>(out var text) && text.Length > 0
                && obj["expires_in"] is JsonValue expires && expires.TryGetValue<double>(out var seconds) && seconds > 0)
            {
                return new Token(text, _time.GetUtcNow() + TimeSpan.FromSeconds(seconds));
            }
        }
        catch (JsonException)
        {
        }
        throw new ExchangeException(status, null);
    }

    private Uri Url()
    {
        var builder = new UriBuilder(_auth.AuthUrl);
        builder.Path = builder.Path.TrimEnd('/') + "/v1/auth/authenticate";
        builder.Query = _accountUuid is { } account ? $"account_uuid={account}" : "";
        return builder.Uri;
    }
}
