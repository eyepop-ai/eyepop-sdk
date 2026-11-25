# EyePop.Sdk

.NET client for the EyePop pipeline API.

> **Pre-release.** 4.x is in development and its API will change.

```
dotnet add package EyePop.Sdk --prerelease
```

## Use

```csharp
using EyePop;
using EyePop.Protocol;

var config = Config.FromEnvironment(
    System.Environment.GetEnvironmentVariables().Cast<System.Collections.DictionaryEntry>()
        .ToDictionary(e => (string)e.Key, e => (string)e.Value!));
var pop = new Pop(new PopComponent[] { new InferenceComponent(Ability: "eyepop.person:latest") });

await using var pipeline = await Pipeline.ConnectAsync(config, pop);
await using var job = pipeline.SetSource(new Source(new Media.Url("https://example.com/photo.jpg")));

await foreach (var prediction in job.Predictions())
{
    Console.WriteLine(prediction.Objects?.Count);
}
```

`EYEPOP_API_KEY` supplies the key. `Pipeline` reconnects on its own when the socket fails; read every `Job` you open, because the socket is read only while a `Job` is read.

Source and issues: https://github.com/eyepop-ai/eyepop-sdk
