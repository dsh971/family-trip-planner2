# Working in this repo

This repo has three kinds of docs, and the split is load-bearing:

- **`core/*` must stay platform-agnostic.** No tool names, no product names
  for how the reasoning happens — phrase everything as plain instructions a
  reasoning model could follow by reading prose ("search the web for X",
  "ask the user Y"). No exceptions: `grep -rniE 'claude|codex|perplexity|google|goat|tabelog' core/`
  should come back empty.
- **`integrations/*` documents specific external CLIs** (the `pp-*` tools
  from printingpress.dev). Each one is optional, documents its own web-search
  fallback, and pins its install command to a tested package version.
- **`adapters/*` is where platform-specific tool syntax belongs.** Before
  editing anything in `core/`, check you haven't introduced an
  adapter-specific assumption (a specific tool-call API, a specific
  platform's file-write mechanism).

`tools/md-to-ics/md_to_ics.py` is the only executable code in this repo. It
must stay dependency-free (Python stdlib only) and its contract is
`core/output-format-spec.md` — if you change the day-table shape or the
frontmatter fields the converter reads, update the parser and
`examples/trip-plans/sample-trip-lilliput.md` in the same change, and
re-run the converter against the example to confirm it still works.

This is a from-scratch project, distilled from (but not derived as code
from) an older Next.js app called `travel-planner`. Don't assume any code
patterns from that app apply here — this repo has no framework, no
database, no UI; it's markdown methodology plus one conversion script.
