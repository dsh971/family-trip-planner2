#!/usr/bin/env python3
"""Run the travel-planner skill non-interactively in each installed agent CLI
on a fixed pick-for-me trip, then check the plan each one writes. Stdlib only.

Run from the repo root, by hand:
    python3 tests/run_agent_smoke.py [--timeout SECONDS] [--allow-cursor-force]

This spends the owner's Claude and Cursor subscriptions and reads live web
pages, so it is never part of CI or unit-test discovery. Each agent runs in
its own throwaway workspace with the skill copied in; the owner's logins
are NOT isolated. Claude Code loads only the workspace's own settings and
skills (not the owner's settings, plugins, or MCP servers), accepts file edits
inside the workspace except to the skill copy, and denies anything else that
would ask for approval unless it's allowlisted: web search and fetch, and the
skill's two scripts on the plan file. Restricted mode would be tighter, but it hides
project skills. Its run log must show it loaded the skill and ran the checker
successfully. Cursor's shell commands run in its sandbox, without its "allow
all commands" flag unless --allow-cursor-force is given; Cursor is judged on
its plan alone. Workspaces are deleted after a pass and kept after a failure.

Exit codes: 0 when no agent failed (skipped agents, including a Cursor that
isn't logged in, don't fail the run), 1 otherwise.
"""
import argparse
import json
import os
import shutil
import stat
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


def workspace_roots(workspace: str) -> list[str]:
    """The workspace path as given and as resolved (/var vs /private/var)."""
    return list(dict.fromkeys([workspace, os.path.realpath(workspace)]))


CLAUDE_TOOLS = ["Skill", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "Bash"]


def claude_allowed_tools(workspace: str) -> list[str]:
    """The skill, web search and fetch, and exactly two shell commands: the
    checker on the plan and the converter from the plan to its .ics. Reading
    and (in acceptEdits mode) editing inside the workspace need no rule;
    anything outside it would need approval, which is denied. The converter writes
    wherever its second argument says, so neither script gets an open-ended
    rule. The scripts can't be rewritten first: claude_disallowed_tools
    blocks edits to the copied skill, and prepare_workspace makes it
    read-only."""
    tools = ["Skill", "WebSearch", "WebFetch"]
    roots = workspace_roots(workspace)
    bases = [".claude/skills/travel-planner/scripts"]
    bases += [os.path.join(root, ".claude/skills/travel-planner/scripts") for root in roots]
    plans = [PLAN_NAME, f"./{PLAN_NAME}"] + [os.path.join(root, PLAN_NAME) for root in roots]
    for base in bases:
        for plan in plans:
            calendar = os.path.splitext(plan)[0] + ".ics"
            tools.append(f"Bash(python3 {base}/check_plan.py {plan})")
            tools.append(f"Bash(python3 {base}/md_to_ics.py {plan} {calendar})")
    return tools


def claude_disallowed_tools(workspace: str) -> list[str]:
    """Edit(path) rules cover every file-writing tool (Write(path) rules are
    never consulted), and paths in CLI flags resolve from the working
    directory."""
    return [f"Edit({rel}/**)" for rel in SKILL_INSTALL_DIRS]


def build_claude_command(binary: str, workspace: str, prompt: str) -> list[str]:
    return [binary, "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--setting-sources", "project", "--strict-mcp-config",
            "--permission-mode", "acceptEdits", "--permission-prompts", "none",
            "--tools", ",".join(CLAUDE_TOOLS),
            "--allowedTools", *claude_allowed_tools(workspace),
            "--disallowedTools", *claude_disallowed_tools(workspace)]


def build_cursor_command(binary: str, workspace: str, prompt: str, allow_force: bool = False) -> list[str]:
    command = [binary, "-p", "--trust", "--sandbox", "enabled", "--workspace", workspace, "--output-format", "text"]
    if allow_force:
        command.append("--force")
    return command + [prompt]


AGENTS = {
    "claude-code": "claude",
    "cursor": "cursor-agent",
    "codex": "codex",
}


def _set_tree_writable(root: str, writable: bool) -> None:
    for dirpath, _dirnames, filenames in os.walk(root):
        for path in [dirpath] + [os.path.join(dirpath, f) for f in filenames]:
            mode = os.stat(path).st_mode
            os.chmod(path, mode | stat.S_IWUSR if writable else mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def prepare_workspace(agent: str) -> str:
    """A throwaway workspace with a read-only copy of the skill in each
    agent's skill folder, so an agent can run the scripts but not rewrite them."""
    workspace = tempfile.mkdtemp(prefix=f"travel-planner-{agent}-")
    for rel in SKILL_INSTALL_DIRS:
        copy = os.path.join(workspace, rel, "travel-planner")
        shutil.copytree(SKILL_DIR, copy)
        _set_tree_writable(copy, False)
    return workspace


def remove_workspace(workspace: str) -> None:
    for rel in SKILL_INSTALL_DIRS:
        copy = os.path.join(workspace, rel, "travel-planner")
        if os.path.isdir(copy):
            _set_tree_writable(copy, True)
    shutil.rmtree(workspace, ignore_errors=True)


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


def claude_transcript_failures(stdout: str) -> list[str]:
    """What a Claude Code stream-json run log must show: the skill loaded
    through the Skill tool, and at least one check_plan.py call that wasn't
    denied or failed."""
    uses: dict[str, dict] = {}
    errors: dict[str, bool] = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                uses[block.get("id")] = block
            elif block.get("type") == "tool_result":
                errors[block.get("tool_use_id")] = bool(block.get("is_error"))
    failures = []
    if not any(u.get("name") == "Skill" and "travel-planner" in str((u.get("input") or {}).get("skill", ""))
               for u in uses.values()):
        failures.append("the agent never loaded the travel-planner skill through its Skill tool")
    if not any(u.get("name") == "Bash" and "check_plan.py" in str((u.get("input") or {}).get("command", ""))
               and errors.get(tool_id) is False for tool_id, u in uses.items()):
        failures.append("the agent never ran check_plan.py successfully (denied, failed, or not called)")
    return failures


TRANSCRIPT_CHECKS = {"claude-code": claude_transcript_failures}
LOGGED_OUT_MARKERS = {"cursor": "Authentication required"}


def run_agent(agent: str, binary: str | None, prompt: str, timeout: int, allow_cursor_force: bool,
              runner=subprocess.run) -> Result:
    if binary is None:
        return Result(agent, "skipped", f"{AGENTS[agent]} is not installed")
    builders = {
        "claude-code": lambda ws: build_claude_command(binary, ws, prompt),
        "cursor": lambda ws: build_cursor_command(binary, ws, prompt, allow_cursor_force),
    }
    if agent not in builders:
        return Result(agent, "skipped", f"{AGENTS[agent]} is installed but this runner has no command for it yet")
    workspace = prepare_workspace(agent)
    try:
        return judge_run(agent, builders[agent](workspace), workspace, timeout, runner)
    except Exception as exc:  # one agent's crash must not cost the other agents' runs
        return Result(agent, "fail", f"runner error: {exc!r}", workspace)


def judge_run(agent: str, command: list[str], workspace: str, timeout: int, runner) -> Result:
    try:
        completed = runner(command, cwd=workspace, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return Result(agent, "fail", f"timed out after {timeout}s", workspace)
    with open(os.path.join(workspace, "agent-output.txt"), "w", encoding="utf-8") as f:
        f.write(completed.stdout or "")
        f.write(completed.stderr or "")
    if completed.returncode != 0:
        output = (completed.stderr or "").strip() or (completed.stdout or "").strip()
        if agent in LOGGED_OUT_MARKERS and LOGGED_OUT_MARKERS[agent] in output:
            remove_workspace(workspace)
            return Result(agent, "skipped", f"{AGENTS[agent]} is not logged in")
        last_line = output.splitlines()[-1] if output else ""
        return Result(agent, "fail", f"exited {completed.returncode}: {last_line}".rstrip(": "), workspace)
    failures = evaluate_plan(os.path.join(workspace, PLAN_NAME))
    if agent in TRANSCRIPT_CHECKS:
        failures += TRANSCRIPT_CHECKS[agent](completed.stdout or "")
    if failures:
        return Result(agent, "fail", "; ".join(failures), workspace)
    remove_workspace(workspace)
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
