# TODO

Not yet implemented, and may never be a full adapter — Perplexity has no
public agentic skill/plugin system comparable to Claude Code or Codex. It's
fundamentally a search-and-answer product with custom instructions ("Spaces"),
not a framework that loads and executes a skill/agent file with tool access.

What's realistically possible: a condensed, single-block version of the
`skills/travel-planner/references/` methodology pasted into a Perplexity Space's custom instructions
field (which has a length limit — likely can't fit all of `skills/travel-planner/references/` verbatim,
needs summarizing). No file output, no tool integrations
(everything in `integrations/` is out of reach — no shell access), no
`.ics` conversion (no local file system) — the user would copy the resulting
plan out manually and run `skills/travel-planner/scripts/md_to_ics.py` themselves elsewhere.

Open question: is a degraded, research-only experience worth building a
dedicated condensed-instructions file for, or is directing a Perplexity user
toward the Claude Code or claude.ai adapters the better answer?
