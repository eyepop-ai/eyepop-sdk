using Xunit;

namespace EyePop.Demo.Tests;

public class OptionsTests
{
    private static readonly string[] Names = ["objects", "classes"];

    private static Options Parse(params string[] args) => Options.Parse(args, Names);

    [Fact]
    public void A_bare_run_is_the_objects_scenario_with_the_defaults()
    {
        var options = Parse();

        Assert.Equal(new Options("objects", null, null, null, false, 60), options);
    }

    [Theory]
    [InlineData("list")]
    [InlineData("all")]
    [InlineData("classes")]
    public void A_command_is_taken_as_given(string command) => Assert.Equal(command, Parse(command).Command);

    [Fact]
    public void Flags_can_come_before_or_after_the_command()
    {
        var options = Parse("--json", "classes", "--timeout", "5", "--file", "a.jpg");

        Assert.Equal(new Options("classes", "a.jpg", null, null, true, 5), options);
    }

    [Fact]
    public void A_pop_file_is_its_own_command()
    {
        var options = Parse("--pop", "p.json");

        Assert.Equal("pop", options.Command);
        Assert.Equal("p.json", options.PopFile);
    }

    [Theory]
    [InlineData("nope")]
    [InlineData("--nope")]
    [InlineData("objects", "classes")]
    [InlineData("--file")]
    [InlineData("--timeout", "0")]
    [InlineData("--timeout", "soon")]
    [InlineData("--file", "a.jpg", "--url", "http://x")]
    [InlineData("--pop", "p.json", "objects")]
    public void A_wrong_command_line_is_a_usage_error(params string[] args) =>
        Assert.Throws<UsageException>(() => Parse(args));
}
