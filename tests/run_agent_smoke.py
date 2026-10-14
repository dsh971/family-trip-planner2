#!/usr/bin/env python3
"""Run the travel-planner skill non-interactively in each installed agent CLI
on a fixed pick-for-me trip, then check the plan each one writes. Stdlib only.

Run from the repo root, by hand:
    python3 tests/run_agent_smoke.py [--timeout SECONDS] [--allow-cursor-force]

This spends the owner's Claude and Cursor subscriptions and reads live web
pages, so it is never part of CI or unit-test discovery. Each agent runs in
its own throwaway workspace with the skill copied in; the owner's home
directory and logins are NOT isolated, which is why Claude Code runs with a
narrow tool allowlist (no general shell, no reservation commands) and Cursor
runs without its "allow all commands" flag unless --allow-cursor-force is
given. Workspaces are deleted after a pass and kept after a failure.

Exit codes: 0 when no agent failed (skipped agents don't fail the run), 1
otherwise.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SKILL_DIR = os.path.join(REPO, "skills", "travel-planner")
PROMPT_FILE = os.path.join(HERE, "fixtures", "san-diego-pick-for-me.md")
PLAN_NAME = "trip-plan.md"
MUST_VISIT = "Balboa Park"
SKILL_INSTALL_DIRS = [os.path.join(".claude", "skills"), os.path.join(".agents", "skills")]

sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

import check_plan  # noqa: E402
import md_to_ics  # noqa: E402


@dataclass
class Result:
    agent: str
    status: str  # "pass", "fail", or "skipped"
    detail: str
    workspace: str = ""


def claude_allowed_tools(workspace: str) -> list[str]:
    """Read/write files, web search and fetch, and python3 only for the
    skill's own scripts — never a general shell."""
    tools = ["Skill", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"]
    for script in ("check_plan.py", "md_to_ics.py"):
        for base in (".claude/skills/travel-planner/scripts", os.path.join(workspace, ".claude/skills/travel-planner/scripts")):
            tools.append(f"Bash(python3 {base}/{script}:*)")
    return tools


def build_claude_command(binary: str, workspace: str, prompt: str) -> list[str]:
    return [binary, "-p", prompt, "--allowedTools", *claude_allowed_tools(workspace)]


def build_cursor_command(binary: str, workspace: str, prompt: str, allow_force: bool = False) -> list[str]:
    command = [binary, "-p", "--trust", "--workspace", workspace, "--output-format", "text"]
    if allow_force:
        command.append("--force")
    return command + [prompt]


AGENTS = {
    "claude-code": "claude",
    "cursor": "cursor-agent",
    "codex": "codex",
}


def prepare_workspace(agent: str) -> str:
    workspace = tempfile.mkdtemp(prefix=f"travel-planner-{agent}-")
    for rel in SKILL_INSTALL_DIRS:
        shutil.copytree(SKILL_DIR, os.path.join(workspace, rel, "travel-planner"))
    return workspace


def evaluate_plan(path: str) -> list[str]:
    """Structural checks only: the plan checker's rules plus the must-visit
    place, a Chosen for you record, planned cities, and every-meal help."""
    if not os.path.isfile(path):
        return [f"no plan file written at {path}"]
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    failures = [f"checker: {f.where}: {f.message}" for f in check_plan.check(text) if f.severity == "error"]
    if MUST_VISIT.lower() not in text.lower():
        failures.append(f"'{MUST_VISIT}' does not appear in the plan")
    records = check_plan.places_records(text)
    if not any(group.get("chosen for you") for group in records.values()):
        failures.append("no place recorded under Chosen for you")
    try:
        frontmatter = md_to_ics.read_frontmatter(text)
    except md_to_ics.TripPlanError as exc:
        return failures + [str(exc)]
    cities = check_plan.frontmatter_list(frontmatter, "cities")
    if not cities or any(c.get("status") != "planned" for c in cities):
        failures.append("not every city is marked planned")
    if md_to_ics.frontmatter_value(frontmatter, "meal_help") != "every_meal":
        failures.append("meal_help is not every_meal")
    return failures


def run_agent(agent: str, binary: str | None, prompt: str, timeout: int, allow_cursor_force: bool,
              runner=subprocess.run) -> Result:
    if binary is None:
        return Result(agent, "skipped", f"{AGENTS[agent]} is not installed")
    if agent == "codex":
        return Result(agent, "skipped", "codex is installed but this runner has no Codex command yet")
    workspace = prepare_workspace(agent)
    if agent == "claude-code":
        command = build_claude_command(binary, workspace, prompt)
    else:
        command = build_cursor_command(binary, workspace, prompt, allow_cursor_force)
    try:
        completed = runner(command, cwd=workspace, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Result(agent, "fail", f"timed out after {timeout}s", workspace)
    with open(os.path.join(workspace, "agent-output.txt"), "w", encoding="utf-8") as f:
        f.write(completed.stdout or "")
        f.write(completed.stderr or "")
    if completed.returncode != 0:
        return Result(agent, "fail", f"exited {completed.returncode}", workspace)
    failures = evaluate_plan(os.path.join(workspace, PLAN_NAME))
    if failures:
        return Result(agent, "fail", "; ".join(failures), workspace)
    shutil.rmtree(workspace, ignore_errors=True)
    return Result(agent, "pass", "plan passed the checker and structural checks")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--timeout", type=int, default=1800, help="seconds per agent (default 1800)")
    parser.add_argument("--allow-cursor-force", action="store_true",
                        help="let Cursor run any command (its --force flag); off by default")
    args = parser.parse_args(argv[1:])
    with open(PROMPT_FILE, encoding="utf-8") as f:
        prompt = f.read()
    results = [
        run_agent(agent, shutil.which(binary), prompt, args.timeout, args.allow_cursor_force)
        for agent, binary in AGENTS.items()
    ]
    for r in results:
        line = f"{r.status.upper():8} {r.agent:12} {r.detail}"
        if r.workspace:
            line += f" (workspace kept: {r.workspace})"
        print(line)
    return 1 if any(r.status == "fail" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
