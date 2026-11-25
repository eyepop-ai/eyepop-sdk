using System.Text.Json.Nodes;
using EyePop.Protocol;

namespace EyePop.Demo;

// One scenario is one block: its pop, then the same few lines every time. Copy a block, change the pop.
// A pop is plain JSON: the typed Pop and InferenceComponent hold only id, ability and params, and every other
// field (categoryName, forward, thresholds) passes through unchanged in the raw JSON.
public static class Scenarios
{
    public static readonly (string Name, Func<Run, Task> Execute)[] All =
    [
        ("objects", Objects),
        ("pose", Pose),
        ("caption", Caption),
    ];

    // People and where they are: a box and a label for each.
    public static async Task Objects(Run run)
    {
        var pop = Pop.FromJson(JsonNode.Parse("""
            {
              "components": [
                {
                  "type": "inference",
                  "ability": "eyepop.person:latest",
                  "categoryName": "person"
                }
              ]
            }
            """));

        await using var pipeline = await Pipeline.ConnectAsync(run.Config, pop, run.Ct);
        await using var job = pipeline.SetSource(run.Source);
        await foreach (var message in job.Messages().WithCancellation(run.Ct))
        {
            run.Report(message);
        }
    }

    // Body pose: find each person, then crop to the person and find the pose.
    public static async Task Pose(Run run)
    {
        var pop = Pop.FromJson(JsonNode.Parse("""
            {
              "components": [
                {
                  "type": "inference",
                  "ability": "eyepop.person:latest",
                  "categoryName": "person",
                  "confidenceThreshold": 0.5,
                  "forward": {
                    "operator": {
                      "type": "crop_with_full_fallback",
                      "includeClasses": ["person"],
                      "crop": { "boxPadding": 0.1 }
                    },
                    "targets": [
                      {
                        "type": "inference",
                        "ability": "eyepop.person.pose:latest",
                        "categoryName": "pose",
                        "confidenceThreshold": 0.25
                      }
                    ]
                  }
                }
              ]
            }
            """));

        await using var pipeline = await Pipeline.ConnectAsync(run.Config, pop, run.Ct);
        await using var job = pipeline.SetSource(run.Source);
        await foreach (var message in job.Messages().WithCancellation(run.Ct))
        {
            run.Report(message);
        }
    }

    // A sentence describing the image, from a vision language model.
    public static async Task Caption(Run run)
    {
        var pop = Pop.FromJson(JsonNode.Parse("""
            {
              "components": [
                {
                  "type": "inference",
                  "ability": "eyepop.vlm.image:latest",
                  "categoryName": "description",
                  "params": {
                    "prompts": [
                      {
                        "prompt": "Describe the scene in one sentence."
                      }
                    ]
                  }
                }
              ]
            }
            """));

        await using var pipeline = await Pipeline.ConnectAsync(run.Config, pop, run.Ct);
        await using var job = pipeline.SetSource(run.Source);
        await foreach (var message in job.Messages().WithCancellation(run.Ct))
        {
            run.Report(message);
        }
    }

    // Any pop you have: --pop pop.json. The file holds the same JSON as the blocks above.
    public static async Task Custom(Run run)
    {
        var path = run.Options.PopFile!;
        if (!File.Exists(path)) throw new DemoFailure($"file not found: {path}");
        var pop = Pop.FromJson(JsonNode.Parse(File.ReadAllText(path)));

        await using var pipeline = await Pipeline.ConnectAsync(run.Config, pop, run.Ct);
        await using var job = pipeline.SetSource(run.Source);
        await foreach (var message in job.Messages().WithCancellation(run.Ct))
        {
            run.Report(message);
        }
    }
}
