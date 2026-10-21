# Intake Questions

Ask these before researching anything. They establish the **trip outline**
— where the family goes, when, where they sleep, and how their days run —
that every later step plans inside. The point is to avoid building a plan
on guessed constraints — a wrong assumption about nap times or mobility
needs invalidates an entire itinerary, while asking a few short questions
up front costs nothing. Ask every question that applies in one turn — the
ones that depend on another answer are worded so they can go in the same
turn — and let the traveler answer in whatever shape is natural. Follow up
only on what's missing or ambiguous.

Where a question has a small set of likely answers (whether naps can happen
on the go, help with where to eat, nonstop-only or not, budget level), offer those answers as
choices the traveler can pick from. Keep open answers — cities, dates,
addresses, place names — as free text.

If the traveler already gave some answers — in their first message, or in
a written brief — don't ask those again; ask only for what's missing. If they
said "pick for me", "don't ask", or otherwise asked for a plan without
questions, ask nothing: use the defaults below and record each one, and
plan every city with the planning loop's pick-for-me defaults
(`city-planning-loop.md`).

Must-visit places are **not** asked here. They're asked city by city once
the outline is set (see `city-planning-loop.md`), so each city's list stays
short and specific.

## Always ask

1. **Cities and dates.** Which cities, in what order, and which dates in
   each? A one-city trip is just one entry. For a multi-city trip, also ask
   how they travel between cities and on which days. A town they'll visit for the day from a
   city they're staying in is not a separate city here; it comes up as a
   must-visit place for that city. Also ask where they're starting from
   and how they get to the first city and home from the last (flight,
   drive, train) — that journey goes on the first and last days, like
   travel between cities. Searching for flights is a separate offer
   (question 8). If dates are flexible, ask for a rough window instead of
   forcing a false precision.
2. **Who's traveling.** Number of travelers, ages of any children, and any
   mobility/accessibility needs (wheelchair, stroller, limited walking
   distance) or dietary restrictions that should hard-exclude certain venues
   (see `research-methodology.md`'s hard-exclude rules — these only apply to
   *confirmed* needs the traveler actually states, never assumed ones).
3. **Daily rhythm.** Does the group have a nap window, an early bedtime, or
   other fixed-time constraints? Get actual start/end times, not just "yes
   we nap" — the itinerary methodology treats these as hard blocks and needs
   real times to schedule around (see `itinerary-and-pacing.md`). Times are
   local clock times wherever the family is that day.
4. **Naps on the go.** Ask it alongside question 3, worded so it only
   applies to a nap: "If there's a nap or rest window, can it happen on the
   go (stroller, car, carrier), or does it need a bed back at the lodging?"
   This decides whether a far-away place can take a full day or only half
   of one. If the traveler already said there's no nap window, leave this
   question out. With no nap window, or no answer, record "needs a bed"
   (`naps_on_the_go: false`), the conservative default.
5. **Lodging, per city.** Already booked (get the address — it anchors
   rest and the days without a must-visit place), or not yet (use the likely
   neighborhood's center as a placeholder, record it as "not booked yet",
   and flag it under "Open Questions for the Traveler" per
   `output-format-spec.md`).
6. **Fixed bookings.** Anything already booked at a set time — a show, a
   tour, a restaurant reservation — that the plan must schedule around
   rather than duplicate or override.
7. **Help with where to eat.** Offer three choices:
   - **Every meal** — a few options for each lunch and dinner, near where
     the family will be at that time.
   - **Just the standouts** — a few places worth planning around, offered
     alongside the other suggestions.
   - **No** — meal times stay in the plan, with no restaurant named.
   Record the answer as `meal_help: every_meal | standouts | none` in the
   plan's frontmatter. Dietary needs (question 2) and budget (question 9)
   filter whatever gets suggested.

## Ask only if relevant

8. **Flights — ask only if the traveler mentions needing flight info, a
   specific route, or says something like "help me find flights."** Don't
   volunteer flight search for a trip where the traveler already has
   flights booked or didn't ask. If they do want it, ask:
   - Departure city/airport (and return, if round-trip).
   - Preferred or flexible dates — a fixed date, or a window to scan for the
     cheapest option?
   - Cabin class preference, and whether nonstop-only matters (worth asking
     explicitly for a trip with small children, where a layover changes the
     trip's difficulty a lot more than it does for adults alone).
   - Budget ceiling, if they have one — otherwise just surface price
     alongside other factors.
   Use these answers to search for flights — with a structured flight-
   search tool if one is available (see `../integrations/`), otherwise by
   searching the web.
9. **Budget overall**, if the traveler wants cost considered in place/
   activity selection (e.g. avoid consistently expensive venues). Don't ask
   if they haven't signaled cost is a constraint — assume moderate by
   default and let the traveler correct you if wrong.

## What NOT to do with the answers

Don't treat a missing answer as a reason to stall. If the traveler skips a
question, proceed with a clearly-stated, reasonable default (e.g. "assuming
no nap window since none was mentioned") and record it under "Open Questions
for the Traveler" in the output rather than re-asking — matching the
research methodology's own "never silently drop, never silently assume
without saying so" discipline. The same goes for every question skipped in
pick-for-me mode; for help with where to eat, the default there is
"just the standouts".

## Right after intake: write the outline

As soon as the outline is known, write the plan file (per
`output-format-spec.md`): frontmatter with the `cities` list (each
`status: outlined`), and every day heading with only the rows an
`outlined` day may hold. Nothing is researched yet. Writing now means an interrupted session loses none of these answers,
and the per-city loop (`city-planning-loop.md`) picks up from the file.
