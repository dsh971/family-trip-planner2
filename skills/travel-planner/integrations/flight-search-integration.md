# Flight Search Integration

Documents a specific external tool, unlike the methodology in `../references/`.
Only use this when the traveler asked for flight search or flight
information (see `../references/intake-questions.md` — don't volunteer this for a
trip where flights are already booked or weren't mentioned).

## Capability gate: shell/command execution required

This integration shells out to a CLI binary, so it only works where you can
run commands. **If you can't**, skip straight to the fallback below — do not describe this
section's CLI commands to the user as something they should run themselves
unless they've explicitly asked for the raw command.

## The tool: `pp-flight-goat`

[Flight GOAT](https://printingpress.dev/library/travel/flight-goat) is an
agent-native CLI (`flight-goat-pp-cli`) from the Printing Press project. It
searches Google Flights, Kayak long-haul routes, and FlySoar (NDC/GDS)
pricing, with no API key required for its core commands.

Source: [pp-flight-goat SKILL.md](https://github.com/mvanhorn/printing-press-library/blob/main/cli-skills/pp-flight-goat/SKILL.md), [printingpress.dev](https://printingpress.dev/)

### Installing it (once per machine)

The traveler runs this themselves — an agent checks whether the CLI is
already installed but never installs it (it's an unvetted third-party
package, pinned to a known version here).

```bash
npx -y @mvanhorn/printing-press-library@0.1.21 install flight-goat --cli-only
```

Installs to `$HOME/.local/bin` (macOS/Linux). Check whether it's present
with `flight-goat-pp-cli --version`. If it isn't, use the fallback below —
don't block the trip-planning session on getting this CLI installed.

### Core commands (no API key required)

Always pass `--agent` — it expands to `--json --compact --no-input
--no-color --yes`, which gives clean JSON suited for programmatic reading
rather than a human-formatted table.

| Command | Use it for |
|---|---|
| `flights <origin> <dest> <date> --agent` | A specific one-way fare search. Add `--return <date>` for round trip. |
| `dates <origin> <dest> --agent` | Scanning for the cheapest dates across a flexible window — use this when the traveler gave a date *range* rather than fixed dates. |
| `explore <airport> --agent` / `longhaul <airport> --agent` | Discovering nonstop/long-haul route options from a given airport, useful for "what are my options from X" questions. |
| `soar <origin> <dest> <date> --agent` | A second price opinion (NDC/GDS pricing) to cross-check the Google Flights result. |

Add `--currency <ISO-4217 code>` if the traveler's booking currency differs
from the default. Add `--stops`, `--class`, `--airlines`, or `--time H-H` to
apply filters the traveler specified during intake (e.g. nonstop-only for a
trip with small children — see `../references/intake-questions.md`).

Parse the response's `.results` field (the envelope also carries `.meta`
with `source` and `synced_at` — worth noting in the output if `source` is
`"local"`/cached rather than `"live"`, so the traveler knows how fresh the
price is). Booking links are in each result's `booking_urls` field.

### Out of scope: live flight status

The tool's flight-status, delay-alert, and tracking commands (FlightAware
AeroAPI) need a paid API key, and this project uses no API keys. Don't use
them or suggest setting one up; if the traveler asks about a booked flight's
status, point them to the airline's app or website.

### What to do with the result

Follow `../references/research-methodology.md`'s "Flights and reservations"
section — the presentation rules are the same whatever the source. Booking
links are in each result's `booking_urls`. A flight row in the day table
marks each time with its own zone, e.g. `| 08:00 Europe/Lisbon | 10:30
Europe/London | Flight XY123 LIS → LHR | Lisbon Airport (LIS) | Economy, not
yet booked |` (see `../references/output-format-spec.md`).

## Fallback: no shell access, or the CLI isn't installed/working

Fall back to a plain web search for flight options (e.g. search "flights
<origin> to <destination> <dates>" and read the results directly). Be
explicit in the output that this came from general web search rather than a
structured flight-search tool, as `../references/research-methodology.md`
requires.
