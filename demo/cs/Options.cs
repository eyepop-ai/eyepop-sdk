namespace EyePop.Demo;

/// <summary>The command line was wrong. The message says how to fix it.</summary>
public sealed class UsageException(string message) : Exception(message);

/// <summary>What the command line asked for. Command is "help", "list", "all", "pop" (a pop from --pop) or a scenario name.</summary>
public sealed record Options(string Command, string? File, string? Url, string? PopFile, bool Json, int TimeoutSeconds)
{
    public const int DefaultTimeoutSeconds = 60;
    public const string DefaultCommand = "objects";

    // The README's options table repeats these words.
    private static readonly (string Name, string Meaning)[] Documented =
    [
        ("list", "Print the scenario names and exit."),
        ("<scenario>", "Run one scenario. With no command, objects runs."),
        ("all", "Run every scenario in turn."),
        ("--file <path>", "Process this file instead of the sample."),
        ("--url <url>", "Process this URL instead of the sample. Not with --file."),
        ("--pop <file.json>", "Run the pop in this JSON file instead of a scenario."),
        ("--json", "Print each prediction as raw JSON instead of the summary line."),
        ("--timeout <seconds>", "Give up on a scenario after this long. Default 60."),
        ("--help, -h", "Print this text and exit."),
    ];

    public static string Usage =>
        "Usage: dotnet run --project demo/cs -- [command] [options]\n\n"
        + string.Join("\n", Documented.Select(d => $"  {d.Name,-20} {d.Meaning}"))
        + "\n\nNeeds EYEPOP_API_KEY in the environment, except with EYEPOP_ENV=local.";

    public static Options Parse(string[] args, IReadOnlyCollection<string> scenarios)
    {
        string? command = null, file = null, url = null, popFile = null;
        var json = false;
        var timeout = DefaultTimeoutSeconds;
        var seen = new HashSet<string>();

        for (var i = 0; i < args.Length; i++)
        {
            string Value() => i + 1 < args.Length && !args[i + 1].StartsWith("--") ? args[++i] : throw new UsageException($"{args[i]} needs a value");

            if (args[i] is "--help" or "-h") return new Options("help", null, null, null, false, DefaultTimeoutSeconds);
            if (args[i].StartsWith("--") && !seen.Add(args[i])) throw new UsageException($"{args[i]} given twice");

            switch (args[i])
            {
                case "--file": file = Value(); break;
                case "--url": url = Value(); break;
                case "--pop": popFile = Value(); break;
                case "--json": json = true; break;
                case "--timeout":
                    var text = Value();
                    timeout = int.TryParse(text, out var seconds) && seconds > 0
                        ? seconds
                        : throw new UsageException($"--timeout needs a number of seconds above 0, not '{text}'");
                    break;
                case var flag when flag.StartsWith("--"):
                    throw new UsageException($"unknown option {flag}; see demo/README.md for the options");
                case var word when command is null:
                    command = word;
                    break;
                case var word:
                    throw new UsageException($"one command at a time: got '{command}' and '{word}'");
            }
        }

        if (file is not null && url is not null) throw new UsageException("use --file or --url, not both");
        if (popFile is not null && command is not null) throw new UsageException("--pop runs its own pop; drop the scenario name");

        if (command == "pop") throw new UsageException("pop needs --pop <file>");
        command ??= popFile is null ? DefaultCommand : "pop";
        if (command is not ("list" or "all" or "pop") && !scenarios.Contains(command))
            throw new UsageException($"unknown scenario '{command}'; run 'list' to see the scenarios");

        return new Options(command, file, url, popFile, json, timeout);
    }
}
