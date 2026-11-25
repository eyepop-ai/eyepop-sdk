using EyePop.Protocol;

namespace EyePop.Demo;

/// <summary>What one scenario needs to run: where to connect, what to send, and how to print.</summary>
public sealed class Run(Config config, Source source, Options options, CancellationToken ct, TextWriter? output = null)
{
    private readonly TextWriter _out = output ?? Console.Out;

    public Config Config => config;
    public Source Source => source;
    public Options Options => options;
    public CancellationToken Ct => ct;

    /// <summary>How many predictions arrived: a timeout with none points at the network.</summary>
    public int Predictions { get; private set; }

    /// <summary>Prints one job message the way every language's demo does. A job that ends in error or is preempted fails the scenario.</summary>
    public void Report(JobMessage message)
    {
        switch (message)
        {
            case PredictionMessage p:
                Predictions++;
                _out.WriteLine(options.Json ? p.Prediction.ToJson().ToJsonString() : Summary.Line(p.Prediction));
                break;
            case Reconnecting r:
                _out.WriteLine($"reconnecting (attempt {r.Attempt}): {Failure.Describe(r.Cause)}");
                break;
            case Reconnected:
                _out.WriteLine("reconnected");
                break;
            case End { Reason: EndReason.Error } end:
                throw new DemoFailure(end.Message ?? "the job ended with an error");
            case End { Reason: EndReason.Preempted }:
                throw new DemoFailure("job was preempted");
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
