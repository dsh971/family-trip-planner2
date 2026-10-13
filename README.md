# travel-planner2 — Family Trip Research Agent

A portable family-trip research and planning agent, built from the
methodology distilled out of an earlier bespoke web app
(`travel-planner`), but platform-independent: no database, no hosted app,
no Google Places API dependency. State is a markdown file. Calendar export
is a deterministic script, not a live Calendar API integration.

## Why this exists

The original `travel-planner` app's core value — research destinations and
places for family travel, then build an itinerary — turned out to be mostly
a research-and-recommendation problem well-suited to a model's own
reasoning and web search, not something that strictly needed its own
Google Places integration (which was stuck behind a billing block for over
a month) and SQLite schema. This project re-platforms that same
methodology as an agent, and extends its scope to things the old pipeline
structurally couldn't answer — "must-visit places in this city," flight
search, restaurant reservations.

## How this repo is organized

- **`core/`** — the methodology. Platform-agnostic prose: what to research,
  how to judge candidates, how to pace an itinerary, what the output
  document must look like. Start at `core/00-overview.md`.
- **`integrations/`** — optional external CLIs (flight search, place
  corroboration, table reservations). Only usable where the agent can run
  commands; each documents its own web-search fallback.
- **`adapters/`** — the only platform-specific surface. Each platform gets a
  thin wrapper pointing at `core/`. Claude Code's is implemented; others are
  labeled TODOs.
- **`tools/md-to-ics/`** — the one piece of real code: a dependency-free
  Python script that converts a trip-plan markdown file into a `.ics`
  calendar file, importable into Google/Apple/Outlook calendars.
- **`examples/`** — a worked example trip plan, used as the converter's test
  fixture too.

## Quick start

**Claude Code:** see `adapters/claude-code/README.md` — symlink
`adapters/claude-code/skills/travel-planner` into `~/.claude/skills/` and ask
Claude Code to plan a trip (or run `/travel-planner`).

**claude.ai:** see `adapters/claude-ai/README.md` — add `core/` to a
Project's knowledge and ask Claude to follow it, producing an Artifact.

**Codex / Perplexity:** not yet built — see the TODO notes in
`adapters/codex/README.md` and `adapters/perplexity/README.md`.

## Optional tool integrations

The Claude Code skill can shell out to external CLIs from the third-party
[Printing Press](https://printingpress.dev/) project when they're installed,
falling back to plain web search otherwise. You install them yourself — the
skill checks for them but never installs anything — with commands pinned to
the package version these docs were tested against
(`@mvanhorn/printing-press-library@0.1.21`; see `adapters/claude-code/README.md`):

- [`flight-goat`](https://printingpress.dev/library/travel/flight-goat) —
  flight search (Google Flights, Kayak, FlySoar), no API key required.
- [`tabelog`](https://printingpress.dev/library/food-and-dining/tabelog) —
  Japanese restaurant search, no API key required.
- [`table-reservation-goat`](https://printingpress.dev/library/food-and-dining/table-reservation-goat) —
  restaurant reservation search and booking across OpenTable/Tock/Resy;
  booking requires the traveler's own connected accounts and is always
  confirmed before executing.

None of these are required — every doc in `integrations/` documents its own
web-search fallback. Place discovery itself is plain web search:
[`wanderlust-goat`](https://printingpress.dev/library/travel/wanderlust-goat)
is deliberately not used, because its discovery commands need a Google
Places key (see `integrations/place-research-tools.md`).

## Non-goals

No database. No live Calendar API write access (export is `.ics`-file-based
by design). No API keys: nothing in this project asks for Google Places or
any other key.
