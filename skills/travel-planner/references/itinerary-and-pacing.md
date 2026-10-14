# Itinerary and Pacing

## Use the family's actual rhythm, not a generic template

Never assume a fixed nap time, bedtime, or daily structure. Use whatever the
traveler gave you in intake (see `intake-questions.md`) as named windows
with real start/end times — e.g. "nap: 13:00-15:00," "bedtime: 19:30
onward." If the traveler didn't mention a rhythm constraint, don't invent
one; proceed without it and note the assumption under "Open Questions for
the Traveler" in the output.

## Rest/nap windows are hard blocks on time, not just activity

A stated nap or rest window blocks **both** scheduling an activity across it
**and** scheduling travel across it. A family can't be commuting to the next
stop any more than they can be sightseeing during a nap window — don't
schedule an activity that ends at the edge of the window and assume travel
to the next stop happens instantly. Still give the window its own row in the
day's schedule table (e.g. "Nap / rest at hotel") — it occupies real time
and belongs on the calendar like anything else.

Where the rest happens depends on the intake answer about naps on the go
(`naps_on_the_go` in the plan's frontmatter). If the nap needs a bed, the
rest row is at the lodging and the family must be back there before it
starts. If it can happen on the go, the rest row can be wherever the day is
("Nap in stroller — Sintra"), and no travel back to the lodging is needed.

## Build each day around the traveler's must-visit places

Each city's days are built only from what the traveler named and picked,
or what was chosen for them in pick-for-me mode (`city-planning-loop.md`, step 3, says what else may be scheduled). Give
each day a center: a must-visit place
(an anchor), with the picks grouped under it on the same day. A pick that
doesn't fit on its anchor's day goes on another day of the same city —
say so in its Notes cell. A day with no anchor is centered on the lodging. Nothing from one city lands on another
city's days.

Use walking distance to decide what belongs together. Treat roughly 1200
meters as a reasonable default walking radius for what's "in range" of a
day's center — but treat that number as genuinely tunable, not a universal
constant: a family with a stroller and young children may want a tighter
radius, a group of mobile adults may tolerate significantly more. If
lodging isn't booked yet, use the likely neighborhood's center and flag it
as an assumption in "Open Questions for the Traveler".

## Far-away must-visit places

A must-visit place beyond walking range of the lodging still goes in —
distance only decides how much of a day it takes:

- **Naps can happen on the go** — it can take a full day, with an on-the-go
  rest row there.
- **The nap needs a bed** — it gets a half-day block before or after the
  rest window at the lodging. The block must hold the round trip **and**
  the visit: a place 45 minutes away needs 90 minutes of travel reserved on
  top of the visit itself. If even that doesn't fit, it's a conflict for the
  traveler to decide (`city-planning-loop.md`, step 4).

A day-trip town follows the traveler's choice from the planning loop: a
full day, or a half-day visit around the nap.

## Opening days and hours

Check the opening days and hours of everything you schedule — must-visit
places, picks, and restaurants alike — and place each on a day and time
when it's open. Tours and timed entries count too: a tower open daily but
toured only Wednesday to Sunday goes on one of those days. If none of the
city's days works for a must-visit place, don't schedule it: list it under
both "Needs Attention" and "Open Questions for the Traveler" with the
reason (e.g. "Blefuscu: the Emperor's Palace is open only Mondays; the
Blefuscu days are Thursday and Friday"). A pick that can't be placed goes
under "Needs Attention".

## Meals

Every day gets a lunch row and a dinner row, about an hour each, unless
travel covers that time (a midday flight, an evening arrival). Dinner ends
before the bedtime window, or by early evening if the traveler gave no
bedtime. Breakfast isn't scheduled; it's assumed at the lodging. A meal row
names a restaurant only when the traveler picked or named one (see
`city-planning-loop.md`, steps 2 and 7); otherwise its title says where
("Lunch near the harbour") and its Notes say no restaurant was picked.

## Travel days between cities

A travel day belongs to the city being arrived in: its free hours count
toward that city, and its heading carries that city's name and zone. Give
the journey its own row, with each end's time in its own city's zone, and
mark every earlier row with the departure city's zone (see
`output-format-spec.md`'s "Time zones"). Its rest row follows the nap
answer — on the go, or at the arrival lodging after the journey.

## "Worth the detour" items need double the time budget

Before slotting a place that required the higher "worth the detour" bar
(see `research-methodology.md`) into a day, confirm the day actually has
enough remaining time for **both** the time at the place **and** the
round-trip travel to and from it — not just one or the other. A detour that
takes 45 minutes each way needs 90 minutes of travel budget reserved in
addition to however long the visit itself takes.

## Revising one city

When the traveler changes an existing plan, rerun only what the change
touches:

- **Changing a city's must-visit places or picks** — rerun that city's
  planning loop. Other cities keep their days as they are.
- **Changing a city's dates** — rerun that city, renumber every later
  `## Day N` heading, and recheck every city whose dates moved: keep
  its picks, but check again that each place is open on its new day and
  that the city's picks still fit its time. Surface anything that no longer
  works instead of leaving it on a day it can't happen. If the trip's total
  length is fixed, ask the traveler which city gains or loses the day.

Edit the plan file in place rather than regenerating it, so the traveler's
own edits survive.

## Never silently drop something that didn't fit

If a day (or the whole trip) fills up before everything the traveler named,
picked, or had chosen for them fits, don't just quietly leave it out of the plan. List it
explicitly under "Needs Attention" in the output, with a one-line reason it
didn't fit (ran out of day capacity, didn't clear the detour time budget,
etc.) — see `output-format-spec.md`. The traveler should always be able to
see what got cut and why, not just notice something's absent.

## Safety is a warning in routing, a deprioritization in selection — not a block in either

This asymmetry is deliberate, repeated from `research-methodology.md`: an
official-source safety flag should push a place or route down in preference
when you're choosing what to recommend, but if the itinerary ends up routing
near or through a flagged area anyway (e.g. it's unavoidably on the way to
something else), surface it as a visible warning in the plan rather than
refusing to route through it. Don't "fix" this into a hard block when
writing or editing this methodology — that's a considered choice, not a gap.
