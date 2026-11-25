using System.Text.Json.Nodes;
using EyePop.Protocol;

namespace EyePop.Demo;

public static class Summary
{
    /// <summary>
    /// One line per prediction: "prediction", then a field for each kind of result that is present, always in this
    /// order: objects, keypoints, caption. "prediction empty" when nothing is.
    /// </summary>
    public static string Line(Prediction prediction)
    {
        var parts = new List<string>();

        if (prediction.Objects is { Count: > 0 } objects)
            parts.Add($"objects={objects.Count} [{string.Join(", ", objects.Select(o => o.ClassLabel).OfType<string>().Distinct())}]");

        // The joints of a person hang off that person, however deep the cascade nests it.
        var keyPoints = (prediction.KeyPoints?.Count ?? 0) + Flatten(prediction.Objects).Sum(o => o.KeyPoints?.Count ?? 0);
        if (keyPoints > 0) parts.Add($"keypoints={keyPoints}");

        if (Caption(prediction) is { } caption) parts.Add($"caption=\"{caption}\"");

        return parts.Count == 0 ? "prediction empty" : "prediction " + string.Join(" ", parts);
    }

    // A vision language model answers in texts[], which is what the live pipeline sends; the protocol's own
    // example puts the text in tokens.text. Both are read, texts first. tokens is free-form JSON, so only a string counts.
    private static string? Caption(Prediction prediction) =>
        prediction.Texts?.Select(t => t.Text).OfType<string>().FirstOrDefault()
        ?? (prediction.Tokens is { } tokens && tokens.TryGetPropertyValue("text", out var node)
            && node is JsonValue value && value.TryGetValue<string>(out var text) ? text : null);

    private static IEnumerable<PredictedObject> Flatten(IReadOnlyList<PredictedObject>? objects) =>
        (objects ?? []).SelectMany(o => Flatten(o.Objects).Prepend(o));
}
