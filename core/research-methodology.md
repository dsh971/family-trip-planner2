# Research Methodology

## Scope

Research isn't limited to "find restaurants/attractions near X." Treat these
as equally in-scope, since a model doing live web research isn't limited to
structured place lookups the way a single-places-API pipeline would be:

- Neighborhood/area recommendations for families specifically (not generic
  "top neighborhoods" lists aimed at any traveler).
- Must-visit places and highlights for the destination as a whole.
- Flights and airline considerations, when the traveler asked for it.
- Practical logistics questions: "is this area walkable with a stroller,"
  "do I need a car," "is public transit stroller/wheelchair accessible."

## Hard excludes (apply before ranking anything)

A hard exclude means: don't recommend it at all, don't mention it as an
option even with caveats. A place the traveler named themselves is the one
exception: flag the conflict instead of excluding it (`city-planning-loop.md`,
step 4). Apply these only on *confirmed* information:

- **Adult-oriented venues** — bars, nightclubs, casinos, liquor stores — are
  never appropriate recommendations for a family trip, regardless of rating.
- **Late-night-only venues** — a place whose only hours fall after a
  family's stated bedtime window is not a usable recommendation.
- **Dietary conflicts** — exclude a place only when you've confirmed an
  actual conflict with a stated restriction (e.g. a seafood-only restaurant
  for a family with a declared shellfish allergy). Never exclude a place
  just because you couldn't find its menu or dietary info — missing
  information is not grounds for exclusion.
- **Accessibility conflicts** — exclude lodging or venues you've confirmed
  are incompatible with a stated mobility need (e.g. no elevator, stairs-
  only access, for a wheelchair user). This is a narrow, confirmed-conflict
  check, not a general accessibility audit of every venue.

## Ranking judgment (after hard excludes)

There's no single formula — use judgment, but weigh these in this rough
order of importance when deciding what to feature prominently in a plan:

1. **Corroboration across sources** (see `corroboration-and-trust.md`) beats
   a single glowing mention. A place that shows up independently in a
   travel guide, a local blog, and community discussion is a stronger pick
   than one you found in exactly one place, even if that one source was
   enthusiastic.
2. **Rating and review volume**, when available — prefer well-reviewed
   places with real review counts over high-rated places with only a
   handful of reviews (a 5.0 average from 3 reviews is weaker evidence than
   a 4.5 average from 500).
3. **Explicit kid-friendliness signals** — a venue explicitly described as
   good for children, or with a kids' menu, is worth surfacing even if nothing
   else distinguishes it from alternatives.
4. **Proximity to lodging** — prefer closer options. Treat the preference as
   fading out gradually past roughly a 20-minute walk (not a hard cutoff)
   and disappearing beyond about 2km, rather than a binary in/out radius.
5. **Price**, as a soft factor — expensive options aren't excluded, just
   deprioritized somewhat relative to similarly-good cheaper alternatives,
   unless the traveler explicitly asked for budget to be a hard constraint.
6. **Safety** — if a place or area has been flagged by an official source
   (see `corroboration-and-trust.md`'s safety-sourcing rule) as being in or
   near a higher-risk area, deprioritize it in your recommendations, but
   don't hard-exclude it — mention it with the caveat and let the traveler
   decide. This asymmetry (deprioritize in selection, warn-don't-block in
   routing) is deliberate, not an oversight — see `itinerary-and-pacing.md`.

## The "worth the detour" judgment call

A place outside the normal walking radius of lodging should only be
suggested if it clears a noticeably higher bar than an in-radius pick would
need to:

- Exceptionally strong rating *and* substantial review volume (not just one
  of the two), **or**
- Corroborated by three or more genuinely different *kinds* of sources — a
  travel guide, a local blog, and community discussion, not three mentions
  scraped from the same site or three near-identical blog posts.

If a far-away place doesn't clear that bar, don't suggest it at all — don't
pad the plan with mediocre far-flung options just to have more content.
In-radius places only need to clear the baseline ranking judgment above, not
this higher detour bar.

This bar applies to places *you* suggest, never to the traveler's own
must-visit places. How those are scheduled is in `itinerary-and-pacing.md`
("Far-away must-visit places"), and how the suggestions around them are
measured is in `city-planning-loop.md` (step 2).

## Flights and reservations

When the traveler asked for flights:

- Summarize the 2-4 best options (balancing price, stops, and any filters
  from intake) under `## Destination Research` → `### Flights` in the output,
  with price, airline, stops, and a booking link for each.
- Once a flight is picked (or you're recommending one), also add it as a row
  in that day's schedule table — it's a fixed-time event like anything else.
  Departure and arrival are usually in different time zones; see
  `output-format-spec.md` for how to mark each time's zone.
- Never present a price as final. Flight prices change constantly — note
  when you found it ("as of <date>"), and say whether it came from a
  structured flight-search tool or general web search, since web search
  often surfaces stale aggregator pages rather than live prices.

When the traveler wants a table booked and you can't book it yourself, say
so plainly and point them to the restaurant or its booking platform —
don't describe a booking flow you can't execute. Anything you do book goes
into the day's schedule table as its own row.

## Honesty about unknowns

Never state an opening hour, price, or other fact as if confirmed when you
couldn't actually verify it from a source. Say "hours unconfirmed" or
similar, rather than guessing a plausible-sounding value. This matters more
than it might seem — a prior version of this project had a real bug where a
broken data pipeline silently invented/nulled facts instead of reporting
them as unknown, and travelers made decisions based on fabricated data. The
discipline here is the same whether the unreliable source is a broken API or
a model's own unverified guess: say what you don't know.
