# TODO

Not yet implemented. See `skills/travel-planner/references/` for the platform-agnostic methodology and
`skills/travel-planner/references/output-format-spec.md` for the required output shape — any adapter
implementation must produce output conforming to that spec so
`skills/travel-planner/scripts/md_to_ics.py` keeps working unmodified.

Open questions to resolve when building this adapter:

- Can Codex load the Claude Code adapter's `skills/travel-planner/` folder
  (a `SKILL.md` plus its `references/`, `integrations/`, and `scripts/` folders) as-is,
  or does it need its own wrapper?
- What's the equivalent of Claude Code's `tools:` frontmatter field for
  granting Bash/WebSearch/WebFetch access in a Codex agent definition?
- Codex has its own `spawn_agent` dispatch primitive (seen referenced
  throughout this project's own development environment) — confirm whether
  a Codex "agent" is the right unit to define here, or whether Codex's
  skill/prompt mechanism is the closer analog to Claude Code's
  `skills/travel-planner/SKILL.md`.

The `skills/travel-planner/references/` and `integrations/` docs should all work as-is once the adapter
wrapper exists, since Codex's sandbox also provides shell access and the `pp-*` CLIs are plain binaries, not Claude-specific.
