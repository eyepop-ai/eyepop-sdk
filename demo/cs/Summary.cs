using EyePop.Protocol;

namespace EyePop.Demo;

public static class Summary
{
    /// <summary>
    /// One line per prediction: "prediction", then a field for each kind of result that is present, always in this
    /// order: objects, classes, texts, keypoints, contours, depth, caption. "prediction empty" when nothing is.
    /// </summary>
    public static string Line(Prediction prediction)
    {
        // Crop-forwarded results (keypoints, text, contours) hang off the object they were found in.
        var all = Flatten(prediction.Objects).ToList();
        var parts = new List<string>();

        if (prediction.Objects is { Count: > 0 } objects)
            parts.Add($"objects={objects.Count} [{Labels(objects.Select(o => o.ClassLabel))}]");
        if (prediction.Classes is { Count: > 0 } classes)
            parts.Add($"classes={classes.Count} [{Labels(classes.Select(c => c.ClassLabel))}]");

        var texts = (prediction.Texts ?? []).Concat(all.SelectMany(o => o.Texts ?? [])).Select(t => t.Text).OfType<string>().ToList();
        if (texts.Count > 0)
            parts.Add($"texts={texts.Count} [{string.Join(", ", texts.Select(t => $"\"{t}\""))}]");

        var keyPoints = (prediction.KeyPoints?.Count ?? 0) + all.Sum(o => o.KeyPoints?.Count ?? 0);
        if (keyPoints > 0) parts.Add($"keypoints={keyPoints}");

        var contours = all.Sum(o => o.Contours?.Count ?? 0);
        if (contours > 0) parts.Add($"contours={contours}");

        if (prediction.Depth is { Width: { } w, Height: { } h }) parts.Add($"depth={w}x{h}");

        if (prediction.Tokens?["text"]?.GetValue<string>() is { } caption) parts.Add($"caption=\"{caption}\"");

        return parts.Count == 0 ? "prediction empty" : "prediction " + string.Join(" ", parts);
    }

    // Distinct labels in first-seen order, so the same picture always prints the same line.
    private static string Labels(IEnumerable<string?> labels) =>
        string.Join(", ", labels.OfType<string>().Distinct());

    private static IEnumerable<PredictedObject> Flatten(IReadOnlyList<PredictedObject>? objects) =>
        (objects ?? []).SelectMany(o => Flatten(o.Objects).Prepend(o));
}
