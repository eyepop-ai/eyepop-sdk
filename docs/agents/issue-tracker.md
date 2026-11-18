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

## Sharing the database

The beads database is shared through the Dolt ref `refs/dolt/data` on `origin`, which is a public repository: write nothing in a bead you would not put in a public issue.

- **Fresh clone**: `bd bootstrap` pulls the database, then `bd hooks install --beads` points git at the hooks in `.beads/hooks`.
- **Push and pull**: the `pre-push` hook runs `bd dolt push` and the `post-merge` hook runs `bd dolt pull`. Neither blocks git when it fails. Run `bd dolt push` or `bd dolt pull` yourself after a bead change that should not wait for a code push.
- **Not automatic**: `dolt.auto-push` does nothing in embedded mode (verified 2026-11-18: a write left `refs/dolt/data` unchanged), so do not rely on it.
- The two custom blocks sit below the `END BEADS INTEGRATION` marker in those hooks; `bd hooks install` keeps content outside its markers.
