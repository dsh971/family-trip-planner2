# Corroboration and Trust

**If a structured cross-source corroboration tool is available to you (see
`../integrations/`), prefer it over doing the matching below by hand** — a
tool that scores many sources with explicit trust weights is more rigorous
than ad-hoc judgment. Use this doc's judgment when no such tool is
available, or to sanity-check and explain a tool's output.

## Matching the same place/claim across sources

When checking whether two sources are describing the same place, don't
require an exact text match — names get abbreviated, translated, or
punctuated differently across sites. Treat two names as the same place when
most of their significant words overlap (roughly 60% or more of the words in
the shorter name also appear in the longer one). Fall back to requiring an
exact match only when one of the names is very short (one or two words) —
otherwise something like "Garden" will falsely match every other place with
"Garden" in the name.

## Source tiers for destination/neighborhood-level claims

Use this tiering when deciding how much weight to give a claim about a
*neighborhood or destination* (not an individual place — see the lighter-
weight rule below for that):

- **Tier 1 (highest weight):** established, editorially-reviewed travel
  publications — the kind of source with a reputation to protect (think
  Lonely Planet, Condé Nast Traveler, Time Out caliber).
- **Tier 2 (medium weight):** local or family-specific resources — a
  "[City] with Kids"-style guide, a local parenting blog, destination-
  specific family travel content.
- **Tier 3 (lowest weight):** community consensus — travel-subreddit
  threads, well-viewed family-travel video content. Useful for ground-
  truthing Tier 1/2 claims and surfacing things editorial sources miss, but
  weight it lightly on its own.

Don't present something as a strong recommendation ("a must-visit
highlight") on the strength of a single source, regardless of tier — require
at least two independent mentions before calling something a highlight. A
single enthusiastic blog post is a candidate worth checking further, not yet
a recommendation.

## Place-level corroboration (a lighter, separate check)

This is distinct from the destination/neighborhood tiering above — it's
about whether an individual place recommendation (a specific restaurant,
attraction) is trustworthy, not whether a whole area is good for families.

A baseline web search finding a place at all counts as one source of
confidence. If you can also confirm it independently through a local
review ecosystem (a region-specific review site, not just whatever
aggregator surfaced it first) and/or community discussion, that raises
confidence further.

Be honest in how you describe this: it's a **chain of increasingly specific
confirmation**, not independent statistical polling. Multiple sources that
themselves draw on the same underlying data (e.g. one source's "top 10"
list is itself sourced from another review site) aren't truly independent
evidence, even though they look like separate mentions. Don't describe a
place as "verified by 3 independent sources" in a way that implies more
rigor than this actually has — describe it plainly instead ("found in a web
search and corroborated by a local review site").

## Safety claims: a strict, separate sourcing rule

Safety and crime information about an area is held to a stricter standard
than ordinary place-quality judgments. Safety claims must come **only** from
official sources — government travel advisories (a foreign ministry's travel
advisory, a state department equivalent) — cited explicitly by name. Never
state a safety claim sourced only from crowdsourced "avoid this
neighborhood" comments, even if they're common/repeated — that kind of
community sentiment is fine evidence for "is this area touristy and
pleasant" but not for "is this area unsafe."

Official advisories are usually written at country or region level and
rarely say anything about an individual neighborhood. So "no advisory flags
this area" is not evidence that it's safe, and must never be worded as if it
were. When reporting what you checked, name the advisory, say what level it
covers, and state plainly that it doesn't assess the specific neighborhood
when it doesn't — e.g. "The [country] travel advisory (country-level) has no
warnings for [city]; it doesn't assess individual neighborhoods." Don't fill
that gap by inferring risk from informal chatter, either.
