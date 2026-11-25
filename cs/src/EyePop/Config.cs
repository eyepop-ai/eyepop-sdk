using System.Text;

namespace EyePop;

/// <summary>A named pair of pipeline and auth URLs. A null auth URL means no exchange: the pipeline takes anonymous sockets.</summary>
public sealed record EyePopEnvironment(string Name, Uri PipelineUrl, Uri? AuthUrl)
{
    public static readonly EyePopEnvironment Production = new("production", new("https://pipeline.eyepop.ai"), new("https://compute.eyepop.ai"));
    public static readonly EyePopEnvironment Staging = new("staging", new("https://pipeline.staging.eyepop.xyz"), new("https://compute.staging.eyepop.xyz"));
    public static readonly EyePopEnvironment Local = new("local", new("http://127.0.0.1:9002"), null);

    public static EyePopEnvironment Named(string name) => name switch
    {
        "production" => Production,
        "staging" => Staging,
        "local" => Local,
        _ => throw Refusal("unknown environment: use production, staging or local"),
    };

    private static EyePopException Refusal(string message) => new(ErrorKind.InvalidConfig, message);
}

public abstract record Auth
{
    public static readonly Auth Anonymous = new AnonymousAuth();

    private Auth() { }

    public sealed record AnonymousAuth : Auth;

    public sealed record Exchange : Auth
    {
        public Uri AuthUrl { get; }
        public string ApiKey { get; }

        public Exchange(Uri authUrl, string apiKey)
        {
            if (string.IsNullOrWhiteSpace(apiKey))
            {
                throw new EyePopException(ErrorKind.InvalidConfig, "an exchange needs an API key");
            }
            AuthUrl = Urls.Checked(authUrl);
            ApiKey = apiKey;
        }

        // The default print would write the key into logs.
        protected override bool PrintMembers(StringBuilder builder)
        {
            builder.Append($"AuthUrl = {AuthUrl}, ApiKey = ***");
            return true;
        }
    }
}

/// <summary>What a Pipeline needs. A Config that exists is valid: nothing downstream checks it again.</summary>
public sealed record Config
{
    public Uri PipelineUrl { get; }
    public Auth Auth { get; }
    public Guid? AccountUuid { get; }

    private Config(Uri pipelineUrl, Auth auth, Guid? accountUuid)
    {
        PipelineUrl = pipelineUrl;
        Auth = auth;
        AccountUuid = accountUuid;
    }

    public static Config Create(Uri pipelineUrl, Auth auth, Guid? accountUuid = null) =>
        new(Urls.Checked(pipelineUrl), auth ?? throw new EyePopException(ErrorKind.InvalidConfig, "a config needs an auth"), accountUuid);

    /// <summary>
    /// Reads only the map it is given, never the process environment. Precedence: explicit argument, then
    /// EYEPOP_URL and EYEPOP_AUTH_URL, then the EYEPOP_ENV row, then production. An empty value counts as unset.
    /// </summary>
    public static Config FromEnvironment(IReadOnlyDictionary<string, string> environment, ConfigArgs? args = null)
    {
        args ??= new ConfigArgs();
        string? Get(string name) => environment.TryGetValue(name, out var value) ? Set(value) : null;

        var row = Get("EYEPOP_ENV") is { } name ? EyePopEnvironment.Named(name) : EyePopEnvironment.Production;
        var pipelineUrl = ParseUrl(Set(args.PipelineUrl) ?? Get("EYEPOP_URL")) ?? row.PipelineUrl;
        var authUrl = ParseUrl(Set(args.AuthUrl) ?? Get("EYEPOP_AUTH_URL")) ?? row.AuthUrl;
        var apiKey = Set(args.ApiKey) ?? Get("EYEPOP_API_KEY");

        Auth auth = (authUrl, apiKey) switch
        {
            (null, null) => Auth.Anonymous,
            (null, _) => throw new EyePopException(ErrorKind.InvalidConfig, "an API key needs an auth URL"),
            (_, null) => throw new EyePopException(ErrorKind.InvalidConfig, "an auth URL needs an API key: set EYEPOP_API_KEY, or EYEPOP_ENV=local for a pipeline without auth"),
            var (url, key) => new Auth.Exchange(url, key),
        };

        return Create(pipelineUrl, auth, ParseGuid(Set(args.AccountUuid) ?? Get("EYEPOP_ACCOUNT_UUID")));
    }

    private static string? Set(string? value) => string.IsNullOrWhiteSpace(value) ? null : value;

    private static Uri? ParseUrl(string? text) =>
        text is null ? null
        : Uri.TryCreate(text, UriKind.Absolute, out var url) ? url
        : throw new EyePopException(ErrorKind.InvalidConfig, "a URL is not an absolute URL");

    private static Guid? ParseGuid(string? text) =>
        text is null ? null
        : Guid.TryParse(text, out var id) ? id
        : throw new EyePopException(ErrorKind.InvalidConfig, "the account UUID is not a UUID");
}

/// <summary>Explicit values, which win over the environment. Raw text: parsing happens in <see cref="Config.FromEnvironment"/>.</summary>
public sealed record ConfigArgs(string? PipelineUrl = null, string? AuthUrl = null, string? ApiKey = null, string? AccountUuid = null);

internal static class Urls
{
    // Plain http would send the API key or the token in the clear, so only a loopback host may use it.
    // A password in a URL would be printed wherever the URL is.
    public static Uri Checked(Uri url) =>
        url is { IsAbsoluteUri: true, UserInfo: "" } && (url.Scheme == Uri.UriSchemeHttps || (url.Scheme == Uri.UriSchemeHttp && url.IsLoopback))
            ? url
            : throw new EyePopException(ErrorKind.InvalidConfig, "a URL must be https, or http to a loopback host, and hold no user info");
}
