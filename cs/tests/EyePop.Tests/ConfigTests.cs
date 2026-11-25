using Xunit;

namespace EyePop.Tests;

public class ConfigTests
{
    private static readonly Uri Auth = new("https://compute.example.com");
    private static readonly Uri Pipeline = new("https://pipeline.example.com");

    private static ErrorKind KindOf(Action refused) =>
        Assert.Throws<EyePopException>(refused).Kind;

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void Exchange_without_an_api_key_is_refused(string key) =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => new EyePop.Auth.Exchange(Auth, key)));

    [Fact]
    public void Exchange_over_plain_http_to_a_remote_host_is_refused() =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => new EyePop.Auth.Exchange(new Uri("http://compute.example.com"), "k")));

    [Fact]
    public void A_pipeline_url_over_plain_http_to_a_remote_host_is_refused() =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => Config.Create(new Uri("http://pipeline.example.com"), EyePop.Auth.Anonymous)));

    [Theory]
    [InlineData("http://localhost:9002")]
    [InlineData("http://127.0.0.1:9002")]
    [InlineData("http://127.4.5.6")]
    [InlineData("http://[::1]:9002")]
    public void Plain_http_to_a_loopback_host_is_accepted(string url) =>
        Assert.Equal(new Uri(url), Config.Create(new Uri(url), EyePop.Auth.Anonymous).PipelineUrl);

    [Fact]
    public void A_url_that_is_not_http_or_https_is_refused() =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => Config.Create(new Uri("ftp://pipeline.example.com"), EyePop.Auth.Anonymous)));

    [Fact]
    public void The_api_key_is_not_printed()
    {
        var config = Config.Create(Pipeline, new EyePop.Auth.Exchange(Auth, "secret-key"));

        Assert.DoesNotContain("secret-key", config.ToString());
    }

    private static Config FromEnv(Dictionary<string, string> env, ConfigArgs? args = null) =>
        Config.FromEnvironment(env, args);

    private static Dictionary<string, string> Env(params (string, string)[] pairs) =>
        pairs.ToDictionary(p => p.Item1, p => p.Item2);

    [Fact]
    public void With_no_variables_but_a_key_the_production_row_applies()
    {
        var config = FromEnv(Env(("EYEPOP_API_KEY", "k")));

        Assert.Equal(new Uri("https://pipeline.eyepop.ai"), config.PipelineUrl);
        Assert.Equal(new EyePop.Auth.Exchange(new Uri("https://compute.eyepop.ai"), "k"), config.Auth);
    }

    [Fact]
    public void EYEPOP_ENV_staging_selects_the_staging_row()
    {
        var config = FromEnv(Env(("EYEPOP_ENV", "staging"), ("EYEPOP_API_KEY", "k")));

        Assert.Equal(new Uri("https://pipeline.staging.eyepop.xyz"), config.PipelineUrl);
        Assert.Equal(new EyePop.Auth.Exchange(new Uri("https://compute.staging.eyepop.xyz"), "k"), config.Auth);
    }

    [Fact]
    public void EYEPOP_ENV_local_is_anonymous()
    {
        var config = FromEnv(Env(("EYEPOP_ENV", "local")));

        Assert.Equal(new Uri("http://127.0.0.1:9002"), config.PipelineUrl);
        Assert.Same(EyePop.Auth.Anonymous, config.Auth);
    }

    [Fact]
    public void EYEPOP_URL_and_EYEPOP_AUTH_URL_win_over_the_EYEPOP_ENV_row()
    {
        var config = FromEnv(Env(
            ("EYEPOP_ENV", "staging"), ("EYEPOP_URL", "https://p.example.com"),
            ("EYEPOP_AUTH_URL", "https://a.example.com"), ("EYEPOP_API_KEY", "k")));

        Assert.Equal(new Uri("https://p.example.com"), config.PipelineUrl);
        Assert.Equal(new EyePop.Auth.Exchange(new Uri("https://a.example.com"), "k"), config.Auth);
    }

    [Fact]
    public void Explicit_arguments_win_over_the_environment()
    {
        var env = Env(("EYEPOP_URL", "https://p.example.com"), ("EYEPOP_AUTH_URL", "https://a.example.com"), ("EYEPOP_API_KEY", "env-key"));
        var args = new ConfigArgs(PipelineUrl: "https://p2.example.com", AuthUrl: "https://a2.example.com", ApiKey: "arg-key");

        var config = FromEnv(env, args);

        Assert.Equal(new Uri("https://p2.example.com"), config.PipelineUrl);
        Assert.Equal(new EyePop.Auth.Exchange(new Uri("https://a2.example.com"), "arg-key"), config.Auth);
    }

    [Fact]
    public void EYEPOP_ACCOUNT_UUID_becomes_accountUuid()
    {
        var id = Guid.NewGuid();

        var config = FromEnv(Env(("EYEPOP_ENV", "local"), ("EYEPOP_ACCOUNT_UUID", id.ToString())));

        Assert.Equal(id, config.AccountUuid);
    }

    [Fact]
    public void An_explicit_account_uuid_wins_over_EYEPOP_ACCOUNT_UUID()
    {
        var id = Guid.NewGuid();

        var config = FromEnv(Env(("EYEPOP_ENV", "local"), ("EYEPOP_ACCOUNT_UUID", Guid.NewGuid().ToString())), new ConfigArgs(AccountUuid: id.ToString()));

        Assert.Equal(id, config.AccountUuid);
    }

    [Fact]
    public void An_empty_variable_counts_as_unset()
    {
        var config = FromEnv(Env(("EYEPOP_ENV", ""), ("EYEPOP_URL", " "), ("EYEPOP_API_KEY", "k")));

        Assert.Equal(new Uri("https://pipeline.eyepop.ai"), config.PipelineUrl);
    }

    public static IEnumerable<object[]> Refused() => new[]
    {
        new object[] { Env(("EYEPOP_ENV", "prod"), ("EYEPOP_API_KEY", "k")) },
        new object[] { Env() },
        new object[] { Env(("EYEPOP_ENV", "local"), ("EYEPOP_API_KEY", "k")) },
        new object[] { Env(("EYEPOP_API_KEY", "k"), ("EYEPOP_URL", "not a url")) },
        new object[] { Env(("EYEPOP_API_KEY", "k"), ("EYEPOP_AUTH_URL", "/relative")) },
        new object[] { Env(("EYEPOP_ENV", "local"), ("EYEPOP_ACCOUNT_UUID", "nope")) },
        new object[] { Env(("EYEPOP_URL", "http://pipeline.example.com"), ("EYEPOP_API_KEY", "k")) },
    };

    [Theory]
    [MemberData(nameof(Refused))]
    public void A_refused_environment_is_invalid_config(Dictionary<string, string> env) =>
        Assert.Equal(ErrorKind.InvalidConfig, KindOf(() => FromEnv(env)));
}
