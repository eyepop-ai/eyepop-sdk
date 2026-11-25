using EyePop.Protocol;

namespace EyePop.Demo;

/// <summary>What one scenario needs to run: where to connect, what to send, and how to print.</summary>
public sealed class Run(Config config, Source source, Options options, CancellationToken ct)
{
    public Config Config => config;
    public Source Source => source;
    public Options Options => options;
    public CancellationToken Ct => ct;

    /// <summary>Prints one job message the way every language's demo does. A job that ends in error fails the scenario.</summary>
    public void Report(JobMessage message)
    {
        switch (message)
        {
            case PredictionMessage p:
                Console.WriteLine(options.Json ? p.Prediction.ToJson().ToJsonString() : Summary.Line(p.Prediction));
                break;
            case Reconnecting r:
                Console.WriteLine($"reconnecting (attempt {r.Attempt}): {Failure.Describe(r.Cause)}");
                break;
            case Reconnected:
                Console.WriteLine("reconnected");
                break;
            case End { Reason: EndReason.Error } end:
                throw new DemoFailure(end.Message ?? "the job ended with an error");
        }
    }

    /// <summary>The media to process: --url, else --file, else the bundled sample.</summary>
    public static Source SourceFor(Options options)
    {
        if (options.Url is { } url) return new Source(new Media.Url(url));

        var path = options.File ?? Path.Combine(AppContext.BaseDirectory, "media", "people-1.jpg");
        if (!File.Exists(path)) throw new DemoFailure($"file not found: {path}");

        var contentType = Path.GetExtension(path).ToLowerInvariant() switch
        {
            ".png" => "image/png",
            ".webp" => "image/webp",
            ".mp4" => "video/mp4",
            ".jpg" or ".jpeg" => "image/jpeg",
            _ => "application/octet-stream",
        };
        return new Source(new Media.Upload(contentType, UploadContent.FromBytes(File.ReadAllBytes(path))));
    }
}
