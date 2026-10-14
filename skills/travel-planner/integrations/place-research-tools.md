# Place Research Tools (Tabelog)

Like `flight-search-integration.md`, this doc documents specific external
tools rather than pure methodology. Place research everywhere runs on plain
web search, with the cross-source judgment in
`../references/corroboration-and-trust.md` applied by hand. The one CLI here,
Tabelog, is an optional extra for restaurants in Japan.

## Capability gate

Same as flight search: these are CLIs you shell out to. If you can't run
commands, use plain web search, applying
`../references/corroboration-and-trust.md`'s judgment by hand.

## Finding suggestions around a must-visit place

In the per-city planning loop (`../references/city-planning-loop.md`, step 2),
search once per must-visit place, with that place in the query — the
neighborhood, attraction, or day-trip town the traveler named (e.g. "best
things to see in Balboa Park", "kid-friendly places near Sagrada Família")
— so results are already grouped the way the pick list shows them. For a
city with no must-visit places, search for the city's top places. Then
check each candidate's hours on its own website where it has one.

## Not used: Wanderlust GOAT

[Wanderlust GOAT](https://printingpress.dev/library/travel/wanderlust-goat)
looks like a fit (cross-source place discovery around an anchor), but its
discovery commands need a Google Places key, and this project uses no API
keys. Tested against the CLI (`wanderlust-goat-pp-cli` 2026.6.2; the
latest package at the time was `@mvanhorn/printing-press-library@0.1.21`)
on 2026-10-13:

- `goat`, `near`, and `why` exit with code 4: `GOOGLE_PLACES_API_KEY is not
  set`. Its `doctor` command lists the key as required for the first
  (seeding) stage of `near`/`goat`. "No LLM" in `goat`'s description means
  no Anthropic key — not no Google key.
- Without the key, what's left is too thin to rely on: `sync-city` for
  San Diego got 25 Wikipedia entries and nothing from Atlas Obscura or
  Reddit (its OpenStreetMap query timed out); `status` reports "not closed"
  with no evidence behind it, which is worse than no answer.

The tool's own docs disagree with each other on this (its skill file says
no authentication is required; its library page says the key is required
for seeding), so don't take a "no key" claim at face value — run the
command. Don't use it, and don't suggest the traveler get a key for it.

## Tabelog (direct, no API key)

The [Tabelog CLI](https://printingpress.dev/library/food-and-dining/tabelog)
searches/curates Japanese restaurants directly from Tabelog's public English
pages. Its docs say no API key or auth is required. Use it for Japan dining
research when it's installed, or when the traveler specifically wants
Tabelog-sourced picks; otherwise search the web.

Source: [printingpress.dev/library/food-and-dining/tabelog](https://printingpress.dev/library/food-and-dining/tabelog)

### Installing

The traveler runs this themselves — an agent checks whether the CLI is
already installed but never installs it (it's an unvetted third-party
package, pinned to a known version here).

```bash
npx -y @mvanhorn/printing-press-library@0.1.21 install tabelog --cli-only
```

If a command fails asking for a key or login, treat the CLI as unavailable
and search the web instead.

### Core commands

| Command | Use it for |
|---|---|
| `find --area <area> --cuisine <type> --agent` | Search with filters (area, cuisine, meal type, budget, result limit). |
| `show <url-or-id> --agent` | Full detail on one restaurant — rating, budget, hours, payment methods, reservation policy. |
| `lists add` / `lists compare` | Build and compare an offline shortlist across a research session. |
| `lists audit` | Flags incomplete data/unknowns in your saved shortlist — run this before finalizing a plan, so unconfirmed fields get surfaced rather than silently included as if confirmed. |

The tool distinguishes listed budgets from review-estimated ones, and
leaves unknown values unpopulated rather than inferring them — the same
"never fabricate" discipline as `../references/preview-content-rules.md`.

## What to do with the results

Fold corroborated picks into the `## Destination Research` section's
highlights and the day-by-day schedule, same as any other researched place
— this is a better-sourced input to the same methodology in
`../references/research-methodology.md`/`../references/itinerary-and-pacing.md`, not a separate output
format.
