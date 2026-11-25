using System.Net;
using Xunit;

namespace EyePop.Tests;

public class HttpExchangeTests
{
    private const string ApiKey = "sk-test-key-value";
    private static readonly Auth.Exchange Auth = new(new Uri("https://auth.example.com/base/"), ApiKey);

    private sealed class Stub(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
    {
        public HttpRequestMessage? Seen { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Seen = request;
            return Task.FromResult(respond(request));
        }
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body) };

    private static (HttpExchange, Stub, FakeTime) Exchange(Func<HttpRequestMessage, HttpResponseMessage> respond, Guid? account = null)
    {
        var stub = new Stub(respond);
        var time = new FakeTime();
        return (new HttpExchange(Auth, account, time, new HttpClient(stub)), stub, time);
    }

    [Fact]
    public async Task Posts_the_key_as_a_bearer_credential_and_returns_the_token_with_its_expiry()
    {
        var (exchange, stub, time) = Exchange(_ => Json(HttpStatusCode.OK, """{"access_token":"the-jwt","expires_in":3600}"""));

        var token = await exchange.ExchangeAsync(default);

        Assert.Equal(HttpMethod.Post, stub.Seen!.Method);
        Assert.Equal("https://auth.example.com/base/v1/auth/authenticate", stub.Seen.RequestUri!.ToString());
        Assert.Equal($"Bearer {ApiKey}", stub.Seen.Headers.Authorization!.ToString());
        Assert.Equal("the-jwt", token.Jwt);
        Assert.Equal(time.GetUtcNow() + TimeSpan.FromHours(1), token.ExpiresAt);
    }

    [Fact]
    public async Task Sends_the_account_uuid_as_a_query_parameter_when_set()
    {
        var account = Guid.NewGuid();
        var (exchange, stub, _) = Exchange(_ => Json(HttpStatusCode.OK, """{"access_token":"j","expires_in":60}"""), account);

        await exchange.ExchangeAsync(default);

        Assert.Equal($"?account_uuid={account}", stub.Seen!.RequestUri!.Query);
    }

    [Fact]
    public async Task A_refusal_carries_the_status_and_never_the_key_or_the_body()
    {
        var (exchange, _, _) = Exchange(_ => Json(HttpStatusCode.Unauthorized, $"bad key {ApiKey}"));

        var failure = await Assert.ThrowsAsync<ExchangeException>(() => exchange.ExchangeAsync(default));

        Assert.Equal(401, failure.Status);
        Assert.DoesNotContain(ApiKey, failure.ToString());
    }

    [Fact]
    public async Task A_429_carries_its_Retry_After()
    {
        var (exchange, _, _) = Exchange(_ =>
        {
            var response = Json(HttpStatusCode.TooManyRequests, "");
            response.Headers.TryAddWithoutValidation("Retry-After", "7");
            return response;
        });

        var failure = await Assert.ThrowsAsync<ExchangeException>(() => exchange.ExchangeAsync(default));

        Assert.Equal(429, failure.Status);
        Assert.Equal(TimeSpan.FromSeconds(7), failure.RetryAfter);
    }

    [Fact]
    public async Task A_connection_failure_has_no_status()
    {
        var (exchange, _, _) = Exchange(_ => throw new HttpRequestException($"cannot reach auth.example.com with {ApiKey}"));

        var failure = await Assert.ThrowsAsync<ExchangeException>(() => exchange.ExchangeAsync(default));

        Assert.Null(failure.Status);
        Assert.DoesNotContain(ApiKey, failure.ToString());
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("""{"access_token":"","expires_in":60}""")]
    [InlineData("""{"access_token":"j"}""")]
    [InlineData("""{"access_token":"j","expires_in":0}""")]
    public async Task A_200_that_is_not_a_token_fails_with_its_status(string body)
    {
        var (exchange, _, _) = Exchange(_ => Json(HttpStatusCode.OK, body));

        var failure = await Assert.ThrowsAsync<ExchangeException>(() => exchange.ExchangeAsync(default));

        Assert.Equal(200, failure.Status);
    }

    [Fact]
    public async Task A_request_that_outlasts_the_timeout_fails_as_a_connection_failure()
    {
        var time = new FakeTime();
        var hang = new HangingHandler();
        var exchange = new HttpExchange(Auth, null, time, new HttpClient(hang));

        var pending = exchange.ExchangeAsync(default);
        await Eventually.True(() => hang.Started);
        time.Advance(TimeSpan.FromSeconds(31));

        var failure = await Assert.ThrowsAsync<ExchangeException>(() => pending);
        Assert.Null(failure.Status);
    }

    private sealed class HangingHandler : HttpMessageHandler
    {
        public volatile bool Started;

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Started = true;
            await Task.Delay(Timeout.Infinite, ct);
            throw new InvalidOperationException();
        }
    }

    [Fact]
    public void The_token_prints_without_its_jwt()
    {
        var token = new Token("secret-jwt", DateTimeOffset.UnixEpoch);

        Assert.DoesNotContain("secret-jwt", token.ToString());
    }
}

public class RetryAfterTests
{
    private static readonly DateTimeOffset Now = new(2026, 1, 1, 0, 0, 0, TimeSpan.Zero);

    [Fact]
    public void Seconds_are_a_delay() => Assert.Equal(TimeSpan.FromSeconds(30), RetryAfter.Parse("30", Now));

    [Fact]
    public void An_HTTP_date_is_the_time_until_then() =>
        Assert.Equal(TimeSpan.FromSeconds(90), RetryAfter.Parse("Thu, 01 Jan 2026 00:01:30 GMT", Now));

    [Fact]
    public void A_date_in_the_past_is_no_wait() =>
        Assert.Equal(TimeSpan.Zero, RetryAfter.Parse("Wed, 31 Dec 2025 00:00:00 GMT", Now));

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("soon")]
    [InlineData("-5")]
    public void Anything_else_is_no_hint(string? value) => Assert.Null(RetryAfter.Parse(value, Now));

    [Fact]
    public void A_huge_number_does_not_overflow() =>
        Assert.True(RetryAfter.Parse("99999999999999999", Now) > TimeSpan.FromDays(1));
}
