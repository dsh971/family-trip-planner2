# City Planning Loop

Run this once per city, in travel order, after intake has written the trip
outline to the plan file (see `intake-questions.md`). Start at the first
city whose `status` is `outlined` in the plan's frontmatter. Each pass ends
with that city's days scheduled and saved, so the next pass — or the next
session — starts from the file, not from memory.

The traveler's own must-visit places are the backbone of each city's plan.
Research fills in around them; it doesn't replace them.

## Pick-for-me mode

When the traveler asked for a plan without being asked questions ("pick for
me", "don't ask"), every point below where the traveler would decide uses
its default instead, and each default you apply is recorded under "Open
Questions for the Traveler" so they can change it later:

- **Must-visit places (step 1)** — use the places the traveler already
  named, if any; otherwise the city's top places as in step 2.
- **A named place that could mean several places (step 1)** — use the
  most likely one in or near the city, and say which one you used under
  "Open Questions for the Traveler". A place you can't find at all isn't
  scheduled; list it under both "Needs Attention" and "Open Questions for
  the Traveler".
- **A place whose kind is unclear (step 1)** — a place outside the city is
  a day-trip town, an area is a neighborhood, and anything else is an
  attraction; say which you chose under "Open Questions for the Traveler".
- **No suggestions found for an anchor (step 2)** — say so in the plan, and
  choose from the city's top places instead, as in step 3's default.
- **Which suggestions to schedule (step 3)** — the highest-ranked ones that
  fit the city's time (step 5). Record them under **Chosen for you**, not
  **Picked from suggestions**.
- **A named place that can't work (step 4)** — keep it, and list it under
  both "Needs Attention" and "Open Questions for the Traveler".
- **A day-trip town when the nap needs a bed (step 4)** — the half-day
  visit around the nap.
- **Picks that need more time than there is (step 5)** — drop the
  lowest-ranked to **Suggested, not picked**.
- **A half day or more left open (step 5)** — leave it open and say so.
- **Restaurants, when help with every meal is on (step 7)** — the top option
  for each meal, marked "chosen for you" in **Meals**.
- **A restaurant that takes reservations** — never book it; list it under
  "Open Questions for the Traveler".
- **Resuming a city that already has a places record** — keep the record
  as it is, without confirming it (nothing to record for this one).

## 1. Ask for must-visit places

Ask: "Are there specific places in <city> you plan to visit?" Each answer
is a must-visit place (an **anchor**) of one of three kinds:

- **A neighborhood** — an area to spend time in ("Le Marais").
- **An attraction** — a single place ("Sagrada Família").
- **A day-trip town** — a town outside the city, visited for the day from
  the city's lodging ("Sintra" while staying in Lisbon). It is not a
  separate stop in the trip outline.

A large park, campus, or market district with several separate places
inside it ("Balboa Park") is a neighborhood: suggest places inside it.

If you can't tell which kind a place is, or can't find it at all, ask the
traveler — never guess at which place they meant. Pick-for-me mode has
its own default for this (above).

If the traveler names nothing, that's fine: go to step 2 and suggest the
city's top places instead.

## 2. Find suggestions

For each anchor, research a short list of places worth adding — aim for
three to five, and never pad the list to reach a number:

- **Neighborhood** — places inside it.
- **Attraction** — places within walking range of it.
- **Day-trip town** — places in that town.

For a city with no anchors, suggest the city's most highly recommended
places and neighborhoods instead.

Places to eat depend on the intake answer about food (`meal_help`):

- **Just the standouts** — include notable places to eat among the
  suggestions, like any other place.
- **Every meal** — leave restaurants out here; each meal gets its own
  options once the days are scheduled (step 7).
- **No** — don't suggest restaurants unless the traveler asks.

Meal times themselves are never suggestions — they're scheduled anyway
(step 3).

Every suggestion goes through `research-methodology.md` as usual — hard
excludes, ranking, corroboration — with one change: measure distance from
the anchor it's grouped under, not from the lodging, since it would be
visited alongside that anchor.

Give each suggestion a one-line reason (per `preview-content-rules.md`) and
a rough time needed, worded as an estimate ("about 2 hours"). If research
finds nothing worth suggesting for an anchor, say so plainly and ask
whether the traveler has places of their own to add there.

## 3. Let the traveler pick

Show the suggestions grouped by anchor, as choices the traveler can tick.
Also let them type in places of their own. Nothing is scheduled unless the
traveler named it or picked it, or it was chosen for them in pick-for-me
mode — travel, rest, bedtime, and meal slots are the only exceptions, and a
meal slot names a specific venue only when one was named, picked, or chosen
that way.

A place the traveler types in becomes an anchor. Clarify it as in step 1
and check it as in step 4; it doesn't get its own round of suggestions.

As soon as picking ends, write the city's places record to the plan
(**Named by you**, **Picked from suggestions**, **Suggested, not picked** —
see `output-format-spec.md`), so an interrupted session keeps the picks.

## 4. Flag anchors that can't work

A traveler-named anchor is never dropped silently and never scheduled
silently when it can't work. Flag it, say why, and let the traveler decide
whether to keep it, when:

- It conflicts with a need the traveler stated (e.g. confirmed stairs-only
  access for a wheelchair user).
- It falls under a hard exclude in `research-methodology.md` (e.g. an
  adults-only venue, or one whose only hours fall after bedtime).
- It can't fit in the city's days — closed on every day the family is
  there, or too far to reach and visit within any day's open hours.

As with hard excludes, flag only *confirmed* conflicts — missing
information is not a conflict; note it as unconfirmed instead.

A **day-trip town** takes a full day when naps can happen on the go. When
the nap needs a bed, offer the traveler a choice: a full day in the town
without the bed nap that day, or a half-day visit around the nap at the
lodging. Schedule whichever they choose.

An anchor the traveler keeps but that still can't be scheduled goes to
"Needs Attention" with the reason — and, when the problem is its opening
days, to "Open Questions for the Traveler" too (see
`itinerary-and-pacing.md`, "Opening days and hours").

## 5. Check capacity before scheduling

Compare what was picked against the time the city actually has:

- **Available** — for each of the city's days, the hours inside its pacing
  windows, minus blocking windows (naps, bedtime), about an hour per meal,
  and any fixed bookings.
- **Needed** — the rough time for each anchor and pick, plus travel between
  them and to and from anything beyond walking range of the lodging.

Tell the traveler both, as estimates ("about 14 hours of picks for about 9
hours available"). If the picks need noticeably more time than there is —
more than about an hour over — ask the traveler to drop items, or to accept
that whatever doesn't fit goes to "Needs Attention". Don't schedule until
they've answered. When it's close, schedule and let the itinerary rules
decide what fits.

If the picks leave a half day or more with nothing in it, say how much
time is open and offer another round of suggestions — more around the
existing anchors, or the city's top places — before scheduling. If the
traveler adds places, check them as in step 4. If they'd rather keep the
time free, leave it unscheduled and note the open time under "Open
Questions for the Traveler", so it reads as a choice, not a gap.

## 6. Schedule

Build the city's days per `itinerary-and-pacing.md` and write them to the
plan file. A restaurant picked as a standout goes in the meal slot of a day
it's near, at a time it's open.

## 7. Pick places to eat — only for "every meal"

Skip this step unless the traveler asked for help with every meal. For each
lunch and dinner slot that doesn't already name a restaurant:

- Suggest two or three places within walking range of where the family is
  right before the meal (the previous row's location; the lodging if the
  meal starts the day's plan or ends it).
- Each must be open at that weekday and time, and clear the hard excludes
  and budget in `research-methodology.md` — dietary needs especially.
  Give each a one-line reason and its price level.
- The traveler picks one, types in their own, or skips (the slot stays
  without a restaurant). If research finds nothing suitable, say so and
  leave the slot without a restaurant.

Put the picked restaurant in its row ("Lunch at Taverna Minor", with its
address as the Location), and record every meal's pick and the
alternatives not chosen in the city's places record (**Meals**, see
`output-format-spec.md`), so swapping one later needs no new research. If
a picked restaurant takes reservations, offer to book it with the
reservation step.

## 8. Check and save

Check the plan before saving it. If you can run commands, run
`../scripts/check_plan.py` on the plan file; otherwise apply the rules in
`output-format-spec.md`'s "Checking a plan" by reading. Fix every error and
check again. An error you can't fix — a booked flight inside the bedtime
window, say — goes under "Needs Attention" by its row title, which marks it
acknowledged. Warnings don't block saving.

Then set the city's `status` to `planned`, and start the next `outlined`
city at step 1.

## Resuming an interrupted session

Open the plan file and continue at the first city whose `status` is
`outlined`. Check these in order and use the first that matches:

1. **It has a places record and scheduled days** — any of the city's days
   holds a row beyond its fixed rows (see `output-format-spec.md`). Keep
   what's scheduled. Schedule each named, picked, or chosen place that isn't
   in a row or under "Needs Attention" yet (step 6), as the session may have
   stopped partway through. If the traveler wanted help with every meal,
   continue at step 7 for the meals the **Meals** record doesn't cover yet.
   Then go to step 8.
2. **It has a places record** — picking is done. Show the traveler the
   record and confirm it still stands (in pick-for-me mode, keep it without
   asking), then go to step 4.
3. **Neither** — start at step 1. Keep any rows already on the city's days;
   with no places record, they're the traveler's own, so treat them like
   fixed bookings.

Revising a city that's already `planned` follows `itinerary-and-pacing.md`'s
"Revising one city" section.
