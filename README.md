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

- **`skills/travel-planner/`** — the skill itself, self-contained so it can
  be copied into any agent's skill folder:
  - `SKILL.md` — the workflow every agent loads first.
  - `references/` — the methodology. Platform-agnostic prose: what to
    research, how to judge candidates, how to pace an itinerary, what the
    output document must look like. Start at `references/00-overview.md`.
  - `integrations/` — optional external CLIs (flight search, Japanese
    restaurant search, table reservations). Only usable where the agent can
    run commands; each documents its own web-search fallback.
  - `scripts/md_to_ics.py` — a dependency-free Python script that converts a
    trip-plan markdown file into a `.ics` calendar file, importable into
    Google/Apple/Outlook calendars.
- **`tests/`** — stdlib tests for the scripts.
- **`examples/`** — a worked example trip plan, used as a test fixture too.
- **`docs/`** — the install guide and the plans behind each change.

## Quick start

```bash
npx skills add dsh971/family-trip-planner2 --skill travel-planner
```

That installs the skill into Claude Code, Codex, Cursor, or any other agent
that reads `SKILL.md` skills. Then ask your agent to plan a family trip — or
say "pick for me" to get a full plan without being asked questions. See
`docs/install.md` for installing by hand, what the skill needs from the
agent, and the current state of chat-app support.

## What's been tested

**Expected to work, and checked:**

- **Installing.** CI runs the real installer (`skills@1.5.22`) on every push
  and checks the installed copy for Claude Code (`~/.claude/skills`) and for
  Codex and Cursor (both read `~/.agents/skills`).
- **Claude Code.** In a real run, Claude Code planned the test trip (three
  days in San Diego, "pick for me"). On 2026-10-20 it passed the full
  scripted run: it loaded the skill through its own skill tool, ran the
  checker itself, and wrote a plan that passed the checker and the run's
  trip-specific checks.
- **The scripts.** `check_plan.py` and `md_to_ics.py` have unit tests, run
  in CI on Python 3.12 (Linux) and locally on macOS.

**To do:**

- **Run Cursor and Codex on the skill.** It already installs where they
  look for it. The scripted-run harness needs a Codex command, and the
  Cursor run needs a logged-in Cursor account.
- **Try another agent that reads `SKILL.md`** without a question tool or a
  shell. The instructions are written for that case.
- **Package the skill for chat apps** (claude.ai, ChatGPT, Perplexity).
- **Test on Windows and on Python 3.10–3.11.** The docs say 3.10 or later.
- **Fix two plan-checker gaps.** A nap row titled "Naptime" is flagged
  as overlapping the `nap` window. A row that falls on the previous evening
  after a time-zone conversion isn't checked yet.
- **Add automated tests for the optional CLIs** below. So far they've been
  tried by hand at the pinned version.

## Optional tool integrations

The skill can shell out to external CLIs from the third-party
[Printing Press](https://printingpress.dev/) project when they're installed,
falling back to plain web search otherwise. You install them yourself — the
skill checks for them but never installs anything — with commands pinned to
the package version these docs were tested against
(`@mvanhorn/printing-press-library@0.1.21`; see `docs/install.md`):

- [`flight-goat`](https://printingpress.dev/library/travel/flight-goat) —
  flight search (Google Flights, Kayak, FlySoar), no API key required.
- [`tabelog`](https://printingpress.dev/library/food-and-dining/tabelog) —
  Japanese restaurant search, no API key required.
- [`table-reservation-goat`](https://printingpress.dev/library/food-and-dining/table-reservation-goat) —
  restaurant reservation search and booking across OpenTable/Tock/Resy;
  booking requires the traveler's own connected accounts and is always
  confirmed before executing.

None of these are required — every doc in `skills/travel-planner/integrations/` documents its own
web-search fallback. Place discovery itself is plain web search:
[`wanderlust-goat`](https://printingpress.dev/library/travel/wanderlust-goat)
is deliberately not used, because its discovery commands need a Google
Places key (see `skills/travel-planner/integrations/place-research-tools.md`).

## Calendar export

`skills/travel-planner/scripts/md_to_ics.py` converts a trip-plan markdown
file (see `skills/travel-planner/references/output-format-spec.md`) into a
standard `.ics` calendar file. Python 3.10+, stdlib only — no install step.

```bash
python3 skills/travel-planner/scripts/md_to_ics.py <trip-plan.md> <output.ics>
```

Exit code `0` on success, `1` on malformed input (missing timezone, bad
table header, bad date/time), `2` on a usage error (wrong number of
arguments). Errors are printed to stderr with enough detail to find and fix
the problem in the source markdown — this script never silently drops a row
or produces partial output on an error.

It reads only: `timezone` and `trip_name` from the frontmatter, each
`## Day N — YYYY-MM-DD` heading (with its optional ` · <zone>` override), and
the GFM table immediately following each one. Nothing else in
the file is parsed — new frontmatter fields or prose sections can always be
added safely.

Beyond the table shape in the spec, the script rejects (exit `1`, row named
in the error):

- a line starting `## Day <number>` that doesn't match the day-heading
  pattern (the separator may be `—`, `–`, or `-`);
- an `End` earlier than `Start` that would roll past midnight into a row
  longer than 12 hours (an overnight window like `19:30 | 07:00` is fine;
  `09:00 | 08:30` is treated as a typo), or longer than 20 hours when `Start`
  and `End` are in different zones (a flight);
- a local time that daylight saving skips;
- table rows after a blank line inside a day's table;
- an unknown timezone name (reported separately when the machine has no
  timezone database at all, as on some Windows installs);
- two rows on the same day with the same `Start` and `Title` (their calendar
  event IDs would collide).

Each event's `UID` is a hash of the trip's `trip_name` and the row's date,
`Start`, and `Title`, so converting an unchanged plan twice yields identical
UIDs, and re-importing it updates events instead of duplicating them (in
calendar apps that honor `UID`). Editing a row's date, start time, or title —
or renaming the trip — produces a **new** UID: re-importing adds the new event
and leaves the old one in place, to be deleted by hand.

## Testing

```bash
python3 -m unittest discover -s tests -v   # from the repo root
python3 tests/install_smoke.py             # installs with the real installer; needs npx
```

`python3 tests/run_agent_smoke.py` runs real agents (Claude Code, and
Cursor when you're logged in; a logged-out Cursor is skipped) on a fixed
San Diego "pick for me" trip, then checks each plan and Claude Code's run
log. It spends your subscriptions, so it never runs in CI.

GitHub Actions runs the first two on every push (`.github/workflows/checks.yml`). The
tests also convert `examples/trip-plans/sample-trip-lilliput.md`, so a
spec change that breaks the example fails the suite.

## Non-goals

No database. No live Calendar API write access (export is `.ics`-file-based
by design). No API keys: nothing in this project asks for Google Places or
any other key.
