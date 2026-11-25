using System.Text.Json.Nodes;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Demo.Tests;

public class RunTests
{
    private static readonly Options Plain = Options.Parse([], ["objects"]);

    private static (Run Run, StringWriter Output) NewRun(Options options)
    {
        var output = new StringWriter();
        var config = Config.Create(new Uri("https://pipeline.example.com"), Auth.Anonymous);
        return (new Run(config, new Source(new Media.Url("https://example.com/a.jpg")), options, default, output), output);
    }

    private static PredictionMessage Prediction() =>
        new("s1", Protocol.Prediction.FromJson(JsonNode.Parse("""{"objects":[{"classLabel":"person"}]}""")));

    [Fact]
    public void A_prediction_prints_its_summary_and_is_counted()
    {
        var (run, output) = NewRun(Plain);

        run.Report(Prediction());

        Assert.Equal("prediction objects=1 [person]" + Environment.NewLine, output.ToString());
        Assert.Equal(1, run.Predictions);
    }

    [Fact]
    public void Json_prints_the_prediction_as_one_line_of_json()
    {
        var (run, output) = NewRun(Plain with { Json = true });

        run.Report(Prediction());

        Assert.Equal("""{"objects":[{"classLabel":"person"}]}""" + Environment.NewLine, output.ToString());
    }

    [Fact]
    public void Reconnects_print_as_progress_lines()
    {
        var (run, output) = NewRun(Plain);

        run.Report(new Reconnecting(new EyePopException(ErrorKind.ConnectionFailed, "x"), 2, TimeSpan.FromSeconds(1)));
        run.Report(new Reconnected());

        Assert.Equal(
            "reconnecting (attempt 2): cannot reach EyePop; check your network connection" + Environment.NewLine + "reconnected" + Environment.NewLine,
            output.ToString());
    }

    [Theory]
    [InlineData(EndReason.Error, "boom", "boom")]
    [InlineData(EndReason.Error, null, "the job ended with an error")]
    [InlineData(EndReason.Preempted, null, "job was preempted")]
    public void A_job_that_ends_badly_fails_the_scenario(EndReason reason, string? message, string expected)
    {
        var (run, _) = NewRun(Plain);

        var failure = Assert.Throws<DemoFailure>(() => run.Report(new End("s1", reason, message)));

        Assert.Equal(expected, failure.Message);
    }

    [Theory]
    [InlineData(EndReason.Eos)]
    [InlineData(EndReason.Stopped)]
    public void A_job_that_ends_normally_does_not_fail(EndReason reason)
    {
        var (run, _) = NewRun(Plain);

        run.Report(new End("s1", reason));
    }

    [Theory]
    [InlineData("a.jpg", "image/jpeg")]
    [InlineData("a.JPEG", "image/jpeg")]
    [InlineData("a.png", "image/png")]
    [InlineData("a.webp", "image/webp")]
    [InlineData("a.mp4", "video/mp4")]
    [InlineData("a.bin", "application/octet-stream")]
    public void A_file_is_uploaded_with_a_content_type_from_its_extension(string name, string contentType)
    {
        var path = Path.Combine(Path.GetTempPath(), Guid.NewGuid() + name);
        File.WriteAllBytes(path, [1, 2, 3]);
        try
        {
            var upload = Assert.IsType<Media.Upload>(Run.SourceFor(Plain with { File = path }).Media);

            Assert.Equal(contentType, upload.ContentType);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void A_missing_file_fails_before_any_network()
    {
        var failure = Assert.Throws<DemoFailure>(() => Run.SourceFor(Plain with { File = "/no/such/a.jpg" }));

        Assert.Equal("file not found: /no/such/a.jpg", failure.Message);
    }

    [Fact]
    public void A_url_is_sent_as_a_url() =>
        Assert.Equal(
            new Media.Url("https://example.com/a.jpg"),
            Run.SourceFor(Plain with { Url = "https://example.com/a.jpg" }).Media);
}
