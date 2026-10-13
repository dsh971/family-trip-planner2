# Claude Code Adapter

`skills/travel-planner/` is a Claude Code skill. It runs in your main
conversation, so it can hold the multi-turn intake and the
confirm-before-booking step the methodology depends on.

## Install

Symlink the skill folder (don't copy it) so it keeps pointing at this repo.
From the repo root:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/adapters/claude-code/skills/travel-planner" ~/.claude/skills/travel-planner
```

Use a project's `.claude/skills/` instead of `~/.claude/skills/` to make it
available in one project only. Then ask Claude Code to plan a family trip,
or invoke it with `/travel-planner`.

The skill folder contains relative symlinks — `core`, `integrations`,
`tools` — back into this repo, so the skill's paths resolve no matter which
directory you run Claude Code from. Moving the repo breaks the install
symlink; re-run the `ln -s` above from the new location.

## Optional CLI tools

None are required — the skill falls back to plain web search for anything
it can't shell out to. The skill never installs them itself; install the
ones you want (pinned to the version these docs were written against):

```bash
npx -y @mvanhorn/printing-press-library@0.1.21 install flight-goat --cli-only
npx -y @mvanhorn/printing-press-library@0.1.21 install tabelog --cli-only
npx -y @mvanhorn/printing-press-library@0.1.21 install table-reservation-goat --cli-only
```

Their docs say none of them needs an API key. `wanderlust-goat` isn't
listed because its place-discovery commands do need one (Google Places) —
see `integrations/place-research-tools.md`.
