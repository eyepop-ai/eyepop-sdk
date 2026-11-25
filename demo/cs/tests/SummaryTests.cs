using System.Text.Json.Nodes;
using EyePop.Protocol;
using Xunit;

namespace EyePop.Demo.Tests;

public class SummaryTests
{
    private static string Line(string prediction) => Summary.Line(Prediction.FromJson(JsonNode.Parse(prediction)));

    [Fact]
    public void Nothing_found_is_empty() => Assert.Equal("prediction empty", Line("{}"));

    [Fact]
    public void Objects_are_counted_with_their_distinct_labels() =>
        Assert.Equal(
            "prediction objects=3 [person, dog]",
            Line("""{"objects":[{"classLabel":"person"},{"classLabel":"dog"},{"classLabel":"person"}]}"""));

    [Fact]
    public void Key_points_on_objects_are_counted() =>
        Assert.Equal(
            "prediction objects=1 [person] keypoints=2",
            Line("""{"objects":[{"classLabel":"person","keyPoints":[{"points":[]},{"points":[]}]}]}"""));

    [Fact]
    public void Key_points_on_a_nested_object_are_counted() =>
        Assert.Equal(
            "prediction objects=1 [person] keypoints=1",
            Line("""{"objects":[{"classLabel":"person","objects":[{"classLabel":"pose","keyPoints":[{"points":[]}]}]}]}"""));

    [Fact]
    public void A_caption_comes_from_texts() =>
        Assert.Equal("prediction caption=\"a crowd\"", Line("""{"texts":[{"text":"a crowd"}]}"""));

    [Fact]
    public void Texts_without_text_are_skipped() =>
        Assert.Equal("prediction caption=\"b\"", Line("""{"texts":[{"confidence":0.5},{"text":"b"}]}"""));

    [Fact]
    public void A_caption_can_come_from_the_tokens() =>
        Assert.Equal("prediction caption=\"a silver car\"", Line("""{"tokens":{"text":"a silver car"}}"""));

    [Fact]
    public void Texts_win_over_tokens() =>
        Assert.Equal("prediction caption=\"x\"", Line("""{"texts":[{"text":"x"}],"tokens":{"text":"y"}}"""));

    [Fact]
    public void A_caption_that_is_not_a_string_is_left_out() =>
        Assert.Equal("prediction empty", Line("""{"tokens":{"text":5}}"""));
}
