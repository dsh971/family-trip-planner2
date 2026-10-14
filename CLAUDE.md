# Working in this repo

The product is one self-contained skill folder, `skills/travel-planner/`,
that installers copy as-is into each agent's skill directory. Everything the
agent reads or runs lives inside it — no symlinks, no paths pointing outside
it. Inside the folder the split is load-bearing:

- **`references/*` must stay platform-agnostic.** No tool names, no product
  names for how the reasoning happens — phrase everything as plain
  instructions a reasoning model could follow by reading prose ("search the
  web for X", "ask the user Y"). No exceptions:
  `grep -rniE 'claude|codex|perplexity|google|goat|tabelog' skills/travel-planner/references/`
  should come back empty.
- **`integrations/*` documents specific external CLIs** (the `pp-*` tools
  from printingpress.dev). Each one is optional, documents its own web-search
  fallback, and pins its install command to a tested package version.
- **`SKILL.md` is the entry point every agent loads.** Keep it
  platform-neutral too: name one platform's tool only as an example, and keep
  it under 500 lines (the Agent Skills spec limit).
- **`scripts/*` must stay dependency-free (Python stdlib only).**

Links resolve from the file that contains them: `SKILL.md` names
`references/x.md`; a doc in `references/` names a sibling as `x.md`, an
integration doc as `../integrations/x.md`, and a script as `../scripts/x.py`.

`scripts/md_to_ics.py` and `scripts/check_plan.py` share one contract,
`references/output-format-spec.md`. If you change the day-table shape, the
frontmatter fields they read, or the places-record format, update the scripts,
the spec, and `examples/trip-plans/sample-trip-lilliput.md` in the same
change, then run both scripts against the example and run the tests with
`python3 -m unittest discover -s tests -v`.

Tests, fixtures, and examples live outside the skill folder (`tests/`,
`examples/`) so nothing test-only ships to travelers.

This is a from-scratch project, distilled from (but not derived as code
from) an older Next.js app called `travel-planner`. Don't assume any code
patterns from that app apply here — this repo has no framework, no
database, no UI; it's markdown methodology plus small stdlib scripts.
