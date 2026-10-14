# Claude.ai Adapter

No code here — claude.ai doesn't load agent/skill definition files the way
Claude Code does. This is a setup note for a human.

## Setup

1. Create a Claude Project.
2. Add every file under `skills/travel-planner/references/` to the project's knowledge.
3. Start a conversation and say something like: "Follow the methodology in
   the documents I've added (start with `00-overview.md`) to plan a family
   trip. Produce the output as an Artifact, following `output-format-spec.md`
   exactly."
4. Ask Claude to keep updating the same Artifact as the conversation
   continues, rather than creating a new one each turn — that's what gives
   you a persistent, re-editable trip plan across the session.

## What's different from the Claude Code adapter

- Only `skills/travel-planner/references/` goes into the Project. The CLIs in `integrations/` need a
  local shell, so Claude uses plain web search instead, which `skills/travel-planner/references/` already
  covers.
- No local file system, so `.ics` conversion has to happen out-of-band:
  download the Artifact's markdown content, then run
  `skills/travel-planner/scripts/md_to_ics.py` against it yourself (in a terminal, or via
  Claude Code).
