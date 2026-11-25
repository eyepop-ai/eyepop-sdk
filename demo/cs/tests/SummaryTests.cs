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
    public void Classes_list_their_labels() =>
        Assert.Equal(
            "prediction classes=2 [tabby, tiger cat]",
            Line("""{"classes":[{"classLabel":"tabby"},{"classLabel":"tiger cat"}]}"""));

    [Fact]
    public void Results_nested_in_objects_are_counted() =>
        Assert.Equal(
            "prediction objects=1 [text] texts=1 [\"STOP\"] keypoints=2 contours=1",
            Line("""
                {"objects":[{"classLabel":"text","texts":[{"text":"STOP"}],
                  "keyPoints":[{"points":[]},{"points":[]}],"contours":[{"points":[]}]}]}
                """));

    [Fact]
    public void Depth_shows_its_size() =>
        Assert.Equal("prediction depth=640x480", Line("""{"depth":{"width":640,"height":480}}"""));

    [Fact]
    public void A_caption_comes_from_the_tokens() =>
        Assert.Equal("prediction caption=\"a silver car\"", Line("""{"tokens":{"text":"a silver car"}}"""));
}
