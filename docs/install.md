# Installing the travel-planner skill

The skill is one self-contained folder, `skills/travel-planner/`. Any agent
that reads skills in the Agent Skills format (`SKILL.md`) can load it.

## One command

```bash
npx skills add dsh971/family-trip-planner2 --skill travel-planner
```

This uses the [`skills` installer](https://www.npmjs.com/package/skills),
which detects the agents on your machine and copies or links the folder into
each one's skill directory. Add `-g` to install for your user rather than the
current project, and `-a claude-code -a codex -a cursor` to choose agents
explicitly. Then ask your agent to plan a family trip — in Claude Code you can
also type `/travel-planner`.

## By hand

Copy (or symlink) `skills/travel-planner/` into your agent's skill directory:

| Agent | For your user | For one project |
|---|---|---|
| Claude Code | `~/.claude/skills/travel-planner/` | `.claude/skills/travel-planner/` |
| Codex | `~/.agents/skills/travel-planner/` | `.agents/skills/travel-planner/` |
| Cursor | `~/.agents/skills/travel-planner/` or `~/.cursor/skills/travel-planner/` | `.agents/skills/travel-planner/` or `.cursor/skills/travel-planner/` |

Codex and Cursor share `~/.agents/skills/`, which is where the installer puts
their copy. Cursor's docs say it also reads Claude Code's skill folders, so a
Claude Code install may already show up there. From a clone of this repo, a symlink keeps
the skill up to date as you pull:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/skills/travel-planner" ~/.claude/skills/travel-planner
```

Moving the clone breaks the symlink; re-run `ln -s` from the new location.

## What the skill needs from the agent

- **Web search** — all place, opening-hours, and restaurant research.
- **Writing files** — the trip plan is a markdown file you keep.
- **Running `python3`** (3.10 or later) — for the plan checker and calendar
  export. Without a shell the agent applies the checker's rules by reading
  them, and you can run the export yourself later:
  `python3 skills/travel-planner/scripts/md_to_ics.py <plan.md> <plan.ics>`.

## Optional CLI tools

None are required — the skill falls back to plain web search for anything
it can't shell out to. The skill never installs them itself; install the
ones you want (pinned to the version the docs were written against):

```bash
npx -y @mvanhorn/printing-press-library@0.1.21 install flight-goat --cli-only
npx -y @mvanhorn/printing-press-library@0.1.21 install tabelog --cli-only
npx -y @mvanhorn/printing-press-library@0.1.21 install table-reservation-goat --cli-only
```

Their docs say none of them needs an API key. `wanderlust-goat` isn't listed
because its place-discovery commands do need one (Google Places) — see
`skills/travel-planner/integrations/place-research-tools.md`.

## Chat apps (claude.ai, ChatGPT, Perplexity)

Not supported yet — a later round will package the skill for chat apps.
Until then, a workaround on claude.ai: create a Project, add every file in
`skills/travel-planner/references/` to its knowledge, and ask Claude to
follow them (starting with `00-overview.md`), producing the plan as an
Artifact it keeps updating. Calendar export then happens outside the chat:
download the plan and run `md_to_ics.py` on it yourself. Perplexity has no
skill system or file output, so a pasted, condensed version of the
methodology is the most it can do.
