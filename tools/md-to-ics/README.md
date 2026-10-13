# md-to-ics

Converts a trip-plan markdown file (see `../../core/output-format-spec.md`)
into a standard `.ics` calendar file. Python 3, stdlib only — no install
step.

## Usage

```bash
python3 md_to_ics.py <trip-plan.md> <output.ics>
```

Exit code `0` on success, `1` on malformed input (missing timezone, bad
table header, bad date/time), `2` on a usage error (wrong number of
arguments). Errors are printed to stderr with enough detail to find and fix
the problem in the source markdown — this script never silently drops a row
or produces partial output on an error.

## Contract

This script's only contract is `../../core/output-format-spec.md`. If you
change the day-table column names, the day-heading pattern, or the
frontmatter `timezone` field's name/shape there, update the parsing in
`md_to_ics.py` and the fixture at `../../examples/trip-plans/sample-trip-lilliput.md`
in the same change.

It reads only: `timezone` and `trip_name` from the frontmatter, each
`## Day N — YYYY-MM-DD` heading (with its optional ` · <zone>` override), and
the GFM table immediately following each one. Nothing else in
the file is parsed — new frontmatter fields or prose sections can always be
added safely.

## Validation rules

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

## Testing changes

```bash
python3 -m unittest discover -s tools/md-to-ics -v   # from the repo root
```

The tests also convert `examples/trip-plans/sample-trip-lilliput.md`, so a
spec change that breaks the example fails the suite.

## Re-importing an updated plan

Each event's `UID` is a hash of the trip's `trip_name` and the row's date,
`Start`, and `Title`, so converting
an unchanged plan twice yields identical UIDs, and re-importing it updates
events instead of duplicating them (in calendar apps that honor `UID`). Editing
a row's date, start time, or title — or renaming the trip — produces a **new** UID: re-importing adds
the new event and leaves the old one in place, to be deleted by hand.
