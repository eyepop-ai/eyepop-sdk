using System.Collections;
using EyePop;
using EyePop.Demo;

// Exit codes: 0 every scenario passed, 1 a scenario failed, 2 the command line or environment is wrong.

Options options;
try
{
    options = Options.Parse(args, Scenarios.All.Select(s => s.Name).ToList());
}
catch (UsageException e)
{
    Console.Error.WriteLine(e.Message);
    return 2;
}

if (options.Command == "help")
{
    Console.WriteLine(Options.Usage);
    return 0;
}

if (options.Command == "list")
{
    foreach (var (name, _) in Scenarios.All) Console.WriteLine(name);
    return 0;
}

var environment = Environment.GetEnvironmentVariables().Cast<DictionaryEntry>()
    .ToDictionary(e => (string)e.Key, e => (string)(e.Value ?? ""));
// Config decides whether a key is needed: every environment with an auth URL needs one, local needs none.
Config config;
try
{
    config = Config.FromEnvironment(environment);
}
catch (EyePopException e)
{
    Console.Error.WriteLine(string.IsNullOrWhiteSpace(environment.GetValueOrDefault("EYEPOP_API_KEY"))
        ? "Set EYEPOP_API_KEY to your EyePop API key; you can create one in the EyePop dashboard at https://dashboard.eyepop.ai"
        : Failure.Describe(e));
    return 2;
}

(string Name, Func<Run, Task> Execute)[] scenarios = options.Command switch
{
    "all" => Scenarios.All,
    "pop" => [("pop", Scenarios.Custom)],
    var name => Scenarios.All.Where(s => s.Name == name).ToArray(),
};

var failed = false;
foreach (var (name, execute) in scenarios)
{
    // A fresh deadline per scenario, so one slow pop does not eat the next one's time.
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(options.TimeoutSeconds));
    Run? run = null;
    try
    {
        run = new Run(config, Run.SourceFor(options), options, timeout.Token);
        await execute(run);
        Console.WriteLine($"PASS {name}");
    }
    catch (Exception e)
    {
        Console.WriteLine($"FAIL {name}: {Failure.Describe(e, options.TimeoutSeconds, run?.Predictions > 0)}");
        failed = true;
    }
}

return failed ? 1 : 0;
