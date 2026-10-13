# Restaurant Reservation Integration (Table Reservation GOAT)

Documents a specific tool, like `flight-search-integration.md` and
`place-research-tools.md`. Only relevant once the traveler wants an actual
table booked — not for general dining research (use
`place-research-tools.md` for that).

## Capability gate

Same as the other tool integrations: requires the ability to run commands.
If you can't → tell the traveler to book directly through the restaurant or the relevant
platform (OpenTable/Tock/Resy) themselves; don't attempt to describe a
booking flow you can't execute.

## The tool: Table Reservation GOAT

[Table Reservation GOAT](https://printingpress.dev/library/food-and-dining/table-reservation-goat)
unifies search and booking across OpenTable, Tock, and Resy in one CLI.

Source: [printingpress.dev/library/food-and-dining/table-reservation-goat](https://printingpress.dev/library/food-and-dining/table-reservation-goat)

### Installing

The traveler runs this themselves — an agent checks whether the CLI is
already installed but never installs it (it's an unvetted third-party
package, pinned to a known version here).

```bash
npx -y @mvanhorn/printing-press-library@0.1.21 install table-reservation-goat --cli-only
```

### Searching availability requires no auth

Checking availability (`availability`, `restaurants search/inspect`) works
with no account connected — use this freely while researching dining
options, same as any other research step.

### Booking requires the traveler's own accounts

Actually reserving a table (`reservations book`) requires real OpenTable/
Tock/Resy account credentials — **this agent cannot book on a traveler's
behalf without them having already connected their own account(s)** to this
tool. Don't attempt to prompt for or handle raw credentials yourself; if
asked to book and no account is connected, tell the traveler what's needed
(connecting the relevant account to this CLI) rather than guessing at a
workaround.

### Always confirm before booking or canceling

Searching availability is safe to do freely. **Booking or canceling a real
reservation is a consequential, real-world action with the traveler's own
accounts and potentially their money (deposits, no-show fees) — always
confirm the specific restaurant, date, time, and party size with the
traveler before running a `reservations book` or `reservations cancel`
command, even if they already said "book it" earlier in the conversation
for a different restaurant.** This mirrors the general principle of
pausing before any action that's hard to reverse or affects something
outside this conversation.

### Core commands

| Command | Use it for |
|---|---|
| `availability --date <date> --party <size> --location <place> --agent` | Check open slots across all three networks at once. |
| `restaurants search --agent` / `restaurants inspect <id> --agent` | Look up hours, cuisine, pricing, and accolades for a specific place before recommending or booking it. |
| `reservations book ...` | **Confirm with the traveler first (see above).** Books the reservation end-to-end. |
| `reservations list` / `reservations cancel` | Manage existing reservations — cancellation also needs confirmation first. |

### What to do with the result

If a reservation is booked, add it to the relevant day's schedule table in
the trip plan (see `../core/output-format-spec.md`) as its own row, so it shows up
on the exported calendar like any other scheduled item — a reservation is
exactly the kind of fixed-time commitment the calendar export exists for.
