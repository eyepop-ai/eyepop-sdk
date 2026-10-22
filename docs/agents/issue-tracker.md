# Issue tracker: Beads

Issues live in beads (`bd`), a local Dolt-backed tracker. There is no GitHub remote. Do not use TodoWrite, TaskCreate, or markdown TODO lists.

## Conventions

- **Create an issue**: `bd create --title="..." --description="..." --type=task|bug|feature --priority=2` (priority 0-4, 0 = critical)
- **Child issue**: add `--parent=<id>`. Children inherit the parent's labels.
- **Read an issue**: `bd show <id>`
- **List issues**: `bd list --status=open`, `bd ready` (unblocked work), `bd search <query>`
- **Comment on an issue**: `bd comment <id> "text"`
- **Apply / remove a label**: `bd label add <id> <label>` / `bd label remove <id> <label>`. Filter with `bd list --label <label>`.
- **Claim work**: `bd update <id> --claim`
- **Dependencies**: `bd dep add <issue> <depends-on>`
- **Flag for a human decision**: `bd human <id>`
- **Close**: `bd close <id> --reason="..."`
- Never use `bd edit`. It opens `$EDITOR` and blocks the agent.

## When a skill says "publish to the issue tracker"

Create a beads issue with `bd create`.

## When a skill says "fetch the relevant ticket"

Run `bd show <id>`.

## Git

Per `CLAUDE.md`, do not commit, push, or sync Dolt remotes unless asked.
