# Core Overview

This directory is the platform-agnostic methodology behind the family trip
research agent. Nothing in here names a specific tool, CLI, or platform —
every instruction is phrased as plain prose ("search the web for X", "ask
the user Y") so the same docs can back any agent or chat assistant that can
read them, with or without the ability to run commands.

Read in this order for a full research-and-planning session:

1. **`intake-questions.md`** — what to ask the traveler before researching
   anything, establishing the trip outline (cities, dates, lodging, daily
   rhythm). Always first.
2. **`city-planning-loop.md`** — the per-city loop that runs after intake:
   the traveler's must-visit places, suggestions around them, picks, a
   capacity check, then scheduling and saving each city in turn. The docs
   below are what each step of the loop draws on.
3. **`research-methodology.md`** — what to research and how to judge
   candidates (places, neighborhoods, must-visit highlights, airlines).
4. **`corroboration-and-trust.md`** — how to decide a claim or place is
   trustworthy enough to recommend, and how to source safety information.
5. **`itinerary-and-pacing.md`** — how to turn researched candidates into an
   actual day-by-day schedule.
6. **`preview-content-rules.md`** — how to write about a place or activity
   concisely without padding or repetition.
7. **`output-format-spec.md`** — the exact markdown shape the finished trip
   plan must follow. This is the one doc with a hard, non-negotiable
   contract (it's what makes `.ics` calendar export possible) — everything
   else above is judgment and methodology, this one is format.

## Optional tool integrations

If you can run commands, the sibling `integrations/` directory documents
specific external tools for restaurant search, flight search, and table
reservations. Each one is optional and each documents its own fallback to
plain web search; every step in this directory works without them. Where a
doc here says "if a structured tool is available," that's where to look.

Specific tools belong in `integrations/`, and platform-specific syntax
belongs in `adapters/`. If you're writing or editing a core doc and you find
yourself naming a specific tool or platform, stop — that content belongs in
one of those, not here.
