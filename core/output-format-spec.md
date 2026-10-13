# Output Format Spec: the Trip Plan Document

This is the single source of truth for the trip-plan markdown shape. Every
adapter must produce output that conforms to this spec exactly — the table
shape in particular is what makes calendar (`.ics`) export possible. If you
change anything here, update `tools/md-to-ics/md_to_ics.py`'s parser and
`examples/trip-plans/sample-trip-lilliput.md` in the same change.

## Why this shape

Day/time entries need to be both human-readable and mechanically parseable.
A GFM (GitHub-flavored Markdown) table, one per day, was chosen over a
repeated heading-plus-metadata-line pattern because:

- **Self-delimiting.** The day's date lives once, in the day's heading —
  each row only needs a start/end *time*, so there's no way for a row to
  disagree with its own day about what date it's on.
- **Trivially parseable.** A table row is one line split on `|`. No
  multi-line state machine is needed to know where one entry ends and the
  next begins, unlike a heading+metadata pattern where a missing line
  silently shifts every field after it.
- **Still fully human-readable** — it renders natively in any markdown
  viewer.
- **Robust to missing data.** A blank cell (e.g. no known end time) is just
  an empty cell the parser can apply a sane default to, not a parse failure.

## Converter contract

The `.md` → `.ics` converter reads **only**:
- `timezone` from the frontmatter (an IANA name, e.g. `America/Los_Angeles`).
- `trip_name` from the frontmatter, only to keep calendar event IDs unique
  across different trips.
- Each `## Day N — YYYY-MM-DD (Weekday)` heading, for that day's date and
  its optional timezone override (see "Time zones" below). Anything between
  the date and the override, such as the city name, is not read.
- The GFM table immediately following each day heading.

It does **not** read `travelers`, `pacing_windows`, `naps_on_the_go`,
`meal_help`, `cities`, `lodging`, or any prose section. Frontmatter values may be double-quoted, single-quoted, or bare,
with an optional trailing `# comment`. Those fields exist for the research/planning process and for the
human reading the document — adding new frontmatter fields or prose sections
later is always safe and will never break the converter, as long as the
fields above keep their exact names and shapes.

## Frontmatter

Required fields — trip-wide, even when the trip spans several cities:

```yaml
trip_name: "Family Trip to Lilliput and Blefuscu"
destination: "Lilliput and Blefuscu"
start_date: 2026-11-10        # first day of the whole trip
end_date: 2026-11-13          # last day of the whole trip
timezone: "Europe/London"     # IANA name of the first city's zone — required for .ics conversion
```

Optional, for the researching/planning process and the human reader (the
converter ignores these):

```yaml
travelers:
  - name: "Gulliver"
    notes: "wheelchair user"
  - name: "Kid, age 4"
    notes: "stroller, early bedtime"
pacing_windows:
  - name: "morning"
    start: "09:00"
    end: "12:00"
  - name: "nap"
    start: "13:00"
    end: "15:00"
    blocking: true           # hard block: no activity or travel scheduled across this window
  - name: "afternoon"
    start: "15:00"
    end: "18:00"
  - name: "bedtime"
    start: "19:30"
    end: "07:00"
    blocking: true
naps_on_the_go: false        # can the nap happen in a stroller/car/carrier? false when not asked
meal_help: every_meal        # every_meal | standouts | none — help with where to eat
cities:                      # one entry per stop, in travel order
  - name: "Lilliput"
    start_date: 2026-11-10
    end_date: 2026-11-11
    lodging:
      name: "Hotel Lilliput Central"
      address: "1 Main Square, Lilliput"
    status: planned          # outlined = days listed, not yet scheduled; planned = scheduled
  - name: "Blefuscu"
    start_date: 2026-11-12
    end_date: 2026-11-13
    timezone: "Europe/Paris"   # only when it differs from the trip's `timezone`
    lodging:
      name: "Blefuscu Harbour Inn"
      address: "not booked yet"
    status: outlined
```

`pacing_windows` times are local clock times in whichever city the day is
in. A stop's dates include its arrival travel day. Returning to an earlier
city later in the trip is a separate `cities` entry. City names must not
contain `·`, which marks the timezone override in day headings.

The plan file is the planning session's state: written right after intake
(`intake-questions.md`), resumed from the first `outlined` city
(`city-planning-loop.md`). What an `outlined` city's days contain is under
"Body sections" below.

An older plan with a single top-level `lodging` (name, address) and no
`cities` list is a one-city trip; read it as one `cities` entry spanning
the whole trip.

## Body sections

In order:

1. `# <trip_name>` — H1, matches frontmatter `trip_name`.
2. `## Overview` — free-form prose: trip summary, why this destination, family
   constraints noted.
3. `## Destination Research` — free-form prose, organized by sub-heading
   (e.g. `### Neighborhoods`, `### Must-Visit Highlights`, `### Flights`,
   `### Safety Notes`). Each city also gets a `### <City>: places` record of
   the traveler's choices, which revisions rely on to know what must not be
   dropped:
   - **Named by you** — the traveler's must-visit places (anchors).
   - **Picked from suggestions** — suggestions the traveler chose.
   - **Suggested, not picked** — kept so a later revision can offer them
     again without new research.
   - **Meals** — only when the traveler asked for help with every meal:
     one line per lunch or dinner with the restaurant picked (or "none")
     and the alternatives offered, e.g. "Day 2 lunch: The Thimble Café
     (also offered: Pocket Pizza, Main Square Deli)".
   When it's written is part of the planning loop (`city-planning-loop.md`,
   steps 3 and 7). Follow `core/corroboration-and-trust.md` for how to
   back claims here — e.g. a highlight should note it has 2+ independent
   source mentions, a safety note should cite its official source and say
   what level it covers (country, region, city), since an advisory that
   doesn't mention a neighborhood says nothing about that neighborhood.
4. One `## Day N — YYYY-MM-DD (Weekday) — <City>` section per day of the
   trip, each immediately followed by a schedule table (shape below). `N`
   starts at 1 and increments once per calendar day in the trip — not
   optional, not renumbered around skip days; changing a city's dates
   renumbers every later day. `— <City>` names the city the day belongs to
   (for travel days, see `itinerary-and-pacing.md`); a one-city trip may
   omit it. A day of a city still marked `outlined` holds only its fixed
   rows — rest, bedtime, travel between cities, and bookings the traveler
   already made — or no rows at all.
5. `## Needs Attention` — bullet list of anything that didn't fit in any
   day's capacity. Never omit this section if something didn't fit — see
   `core/itinerary-and-pacing.md`'s "never silently drop" rule. If nothing
   needed to be cut, the section may say so plainly ("Everything fit.") or be
   omitted entirely — omission means "nothing to report," not "didn't check."
   On a multi-city trip, start each item with its city ("Blefuscu: ...").
6. `## Open Questions for the Traveler` — bullet list of anything the
   research couldn't resolve and needs the traveler's input (e.g. "Hotel not
   yet booked — Day 2's walking radius assumes the Hotel Lilliput Central
   address above."). Omit if there are none. On a multi-city trip, start
   each item with its city, as in Needs Attention.

## Day table shape

Immediately under each `## Day N — YYYY-MM-DD (Weekday)` heading:

```markdown
| Start | End   | Title                 | Location                       | Notes                         |
|-------|-------|------------------------|---------------------------------|--------------------------------|
| 09:00 | 10:30 | Visit Royal Gardens    | Royal Gardens, Lilliput        | Stroller-friendly; free entry |
| 10:30 | 12:00 | Lunch at Taverna Minor | 12 Small St, Lilliput Quarter | Kids' menu confirmed          |
| 13:00 | 15:00 | Nap / rest at hotel    | Hotel Lilliput Central         | Blocking window — no travel scheduled across this |
```

Rules:

- The header row's columns must be exactly, in this order:
  `Start | End | Title | Location | Notes`.
- `Start`/`End` are 24-hour `HH:MM`, optionally followed by a timezone (see
  "Time zones" below). `End` may be blank — the converter then assumes a
  1-hour duration from `Start`.
- An `End` earlier than `Start` means the row runs past midnight (e.g. a
  `19:30 | 07:00` bedtime window). That's allowed for up to 12 hours; a
  longer rollover is rejected as a likely typo — unless `Start` and `End`
  are in different time zones, as a flight's are, which allows up to 20
  hours of actual travel time.
- A time that doesn't exist locally because clocks jump forward for daylight
  saving (e.g. 01:30 in London on the last Sunday in March) is an error.
- Keep each day's table contiguous: a blank line ends a markdown table, so
  rows after one would fall outside the day (the converter rejects this).
  A literal `|` inside a cell must be escaped as `\|`.
- Two rows on the same day can't share both `Start` and `Title` — their
  calendar event IDs would collide. Make the titles distinct.
- `Location` should be a real, geocodable address or place name where
  possible — this becomes the `.ics` event's `LOCATION`.
- `Notes` becomes the `.ics` event's `DESCRIPTION`. Use it for anything that
  doesn't fit the title: confirmation status, accessibility notes, whether a
  fact (like hours) is unconfirmed — never invent a fact to fill this cell;
  say "unconfirmed" instead, per `core/preview-content-rules.md`.
- A nap/rest or other blocking pacing window still gets a row, like any
  other scheduled item — it occupies real time and should show up on the
  calendar, even though nothing is "visited."
- The dash after the day number may be `—`, `–`, or `-`. Any other heading
  starting `## Day <number>` that doesn't match the pattern is an error,
  not something the converter skips — so never use `## Day N` headings for
  anything but schedule days.
- Rows in sections other than a `## Day N — ...` table (e.g. a markdown table
  accidentally included under `## Destination Research`) are never
  calendar events — only tables directly under a day heading are in scope.

## Time zones

Each time is interpreted in the most specific zone given, in this order:

1. **The cell's own zone** — `HH:MM <IANA zone>`, e.g. `08:00 Europe/Lisbon`.
   Use this for anything that crosses time zones, a flight above all: its
   departure and arrival are local times in two different zones.
2. **The day's zone** — a day heading may end with ` · <IANA zone>`, e.g.
   `## Day 3 — 2026-11-12 (Thursday) — Tokyo · Asia/Tokyo`. Every unmarked
   time that day is in that zone. Every day of a city whose `cities` entry
   names a `timezone` different from the trip's must carry that zone here —
   the converter reads zones only from headings and cells, never from the
   `cities` list.
3. **The trip's zone** — `timezone` in the frontmatter, for everything else.

A travel day's heading carries the arrival city's zone, so every row before
arrival (checkout, the walk to the station) names the departure city's zone
in its own time cells — otherwise it converts in the arrival zone and lands
at the wrong hour.

```markdown
## Day 3 — 2026-11-12 (Thursday) — Tokyo · Asia/Tokyo

| Start               | End                | Title                    | Location           | Notes                 |
|---------------------|--------------------|--------------------------|--------------------|-----------------------|
| 08:00 Europe/Lisbon | 10:30 Europe/London | Flight XY123 LIS → LHR  | Lisbon Airport (LIS) | Economy, not yet booked |
| 15:00               | 16:30              | Ueno Zoo                 | Ueno Park, Tokyo   | Hours unconfirmed     |
```

Zones must be IANA names (`Europe/London`, not `BST` or `GMT+1`). An
unrecognized name is an error, never a guess.

