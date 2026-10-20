"""Tests for run_agent_smoke.py's logic, with a fake agent in place of real
CLIs (no subscription spent, no network). Stdlib only.

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run_agent_smoke  # noqa: E402

REPO = os.path.dirname(HERE)
SAMPLE = os.path.join(REPO, "examples", "trip-plans", "sample-trip-lilliput.md")

GOOD_PLAN = """---
trip_name: "Trip to San Diego"
destination: "San Diego"
start_date: 2027-03-15
end_date: 2027-03-15
timezone: "America/Los_Angeles"
meal_help: every_meal
cities:
  - name: "San Diego"
    start_date: 2027-03-15
    end_date: 2027-03-15
    status: planned
---

# Trip to San Diego

### San Diego: places

**Named by you:**
- Balboa Park (neighborhood)

**Chosen for you:**
- Botanical Building (in Balboa Park)

## Day 1 — 2027-03-15 (Monday) — San Diego

| Start | End | Title | Location | Notes |
|---|---|---|---|---|
| 10:00 | 11:00 | Botanical Building | Balboa Park | Chosen for you |
| 12:00 | 13:00 | Lunch near El Prado | Balboa Park | |
| 18:00 | 19:00 | Dinner near the lodging | Bankers Hill | |
"""


def transcript(*events: dict) -> str:
    return "".join(json.dumps(e) + "\n" for e in events)


def tool_use(tool_id: str, name: str, **tool_input) -> dict:
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]}}


def tool_result(tool_id: str, is_error: bool = False) -> dict:
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tool_id, "is_error": is_error, "content": "ok"}]}}


GOOD_TRANSCRIPT = transcript(
    {"type": "system", "subtype": "init"},
    tool_use("t1", "Skill", skill="travel-planner"), tool_result("t1"),
    tool_use("t2", "Bash", command="python3 .claude/skills/travel-planner/scripts/check_plan.py trip-plan.md"),
    tool_result("t2"),
)


class FakeRunner:
    """Stands in for subprocess.run: writes `plan_text` (if any) into the
    workspace, then returns `returncode` with `stdout`, or raises a timeout."""

    def __init__(self, plan_text=None, returncode=0, timeout=False, stdout=GOOD_TRANSCRIPT):
        self.plan_text, self.returncode, self.timeout, self.stdout = plan_text, returncode, timeout, stdout
        self.commands = []

    def __call__(self, command, cwd, capture_output, text, timeout, stdin=None):
        self.commands.append(command)
        self.stdin = stdin
        if self.timeout:
            raise subprocess.TimeoutExpired(command, timeout)
        if self.plan_text is not None:
            with open(os.path.join(cwd, run_agent_smoke.PLAN_NAME), "w", encoding="utf-8") as f:
                f.write(self.plan_text)
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, "")


class RunAgentTest(unittest.TestCase):
    def tearDown(self):
        for result in getattr(self, "results", []):
            if result.workspace:
                run_agent_smoke.remove_workspace(result.workspace)

    def run_one(self, agent, runner, binary="/usr/bin/fake", allow_force=False):
        result = run_agent_smoke.run_agent(agent, binary, "prompt", 60, allow_force, runner=runner)
        self.results = [result]
        return result

    def test_missing_cli_is_skipped(self):
        result = self.run_one("codex", FakeRunner(), binary=None)
        self.assertEqual(result.status, "skipped")

    def test_good_plan_passes_and_workspace_is_removed(self):
        result = self.run_one("claude-code", FakeRunner(GOOD_PLAN))
        self.assertEqual(result.status, "pass", result.detail)
        self.assertEqual(result.workspace, "")

    def test_no_plan_file_fails_with_reason(self):
        result = self.run_one("cursor", FakeRunner(plan_text=None))
        self.assertEqual(result.status, "fail")
        self.assertIn("no plan file", result.detail)
        self.assertTrue(os.path.isdir(result.workspace))

    def test_timeout_fails_and_keeps_workspace(self):
        result = self.run_one("claude-code", FakeRunner(timeout=True))
        self.assertEqual(result.status, "fail")
        self.assertIn("timed out", result.detail)
        self.assertTrue(os.path.isdir(result.workspace))

    def test_plan_missing_chosen_for_you_and_must_visit_fails(self):
        with open(SAMPLE, encoding="utf-8") as f:
            sample = f.read()
        result = self.run_one("claude-code", FakeRunner(sample))
        self.assertEqual(result.status, "fail")
        self.assertIn("Balboa Park", result.detail)
        self.assertIn("Chosen for you", result.detail)

    def test_plan_without_every_meal_help_fails(self):
        result = self.run_one("claude-code", FakeRunner(GOOD_PLAN.replace("meal_help: every_meal\n", "")))
        self.assertEqual(result.status, "fail")
        self.assertIn("meal_help", result.detail)

    def test_copied_skill_scripts_are_read_only(self):
        result = self.run_one("cursor", FakeRunner(plan_text=None))
        for rel in run_agent_smoke.SKILL_INSTALL_DIRS:
            script = os.path.join(result.workspace, rel, "travel-planner", "scripts", "check_plan.py")
            self.assertFalse(os.access(script, os.W_OK), script)

    def test_unsupported_installed_agent_is_skipped(self):
        result = self.run_one("codex", FakeRunner())
        self.assertEqual(result.status, "skipped")
        self.assertIn("no command", result.detail)

    def test_agent_exiting_non_zero_fails(self):
        result = self.run_one("claude-code", FakeRunner(GOOD_PLAN, returncode=2))
        self.assertEqual(result.status, "fail")
        self.assertIn("exited 2", result.detail)

    def test_claude_run_that_never_loads_the_skill_fails(self):
        stdout = transcript(tool_use("t2", "Bash", command="python3 x/scripts/check_plan.py trip-plan.md"),
                            tool_result("t2"))
        result = self.run_one("claude-code", FakeRunner(GOOD_PLAN, stdout=stdout))
        self.assertEqual(result.status, "fail")
        self.assertIn("never loaded the travel-planner skill", result.detail)

    def test_claude_run_whose_checker_call_was_denied_fails(self):
        stdout = transcript(tool_use("t1", "Skill", skill="travel-planner"), tool_result("t1"),
                            tool_use("t2", "Bash", command="python3 x/scripts/check_plan.py ./trip-plan.md"),
                            tool_result("t2", is_error=True))
        result = self.run_one("claude-code", FakeRunner(GOOD_PLAN, stdout=stdout))
        self.assertEqual(result.status, "fail")
        self.assertIn("check_plan.py", result.detail)

    def test_permission_denied_event_with_a_text_message_is_read(self):
        denied = {"type": "system", "subtype": "permission_denied", "message": "Permission to use Bash has been denied"}
        stdout = GOOD_TRANSCRIPT + transcript(denied)
        result = self.run_one("claude-code", FakeRunner(GOOD_PLAN, stdout=stdout))
        self.assertEqual(result.status, "pass", result.detail)

    def test_agent_gets_no_stdin(self):
        runner = FakeRunner(GOOD_PLAN)
        self.run_one("claude-code", runner)
        self.assertIs(runner.stdin, subprocess.DEVNULL)

    def test_a_crash_while_judging_one_agent_fails_it_without_stopping_the_run(self):
        class Exploding(FakeRunner):
            def __call__(self, *args, **kwargs):
                raise RuntimeError("boom")
        result = self.run_one("claude-code", Exploding())
        self.assertEqual(result.status, "fail")
        self.assertIn("boom", result.detail)

    def test_failed_exit_reports_the_agents_last_words(self):
        class Crashed(FakeRunner):
            def __call__(self, command, cwd, **kwargs):
                return subprocess.CompletedProcess(command, 1, "", "Error: model overloaded.\n")
        result = self.run_one("cursor", Crashed())
        self.assertEqual(result.status, "fail")
        self.assertIn("exited 1: Error: model overloaded.", result.detail)

    def test_logged_out_cursor_is_skipped_and_its_workspace_removed(self):
        class LoggedOut(FakeRunner):
            def __call__(self, command, cwd, **kwargs):
                self.cwd = cwd
                return subprocess.CompletedProcess(
                    command, 1, "", "Error: Authentication required. Please run 'agent login' first.\n")
        runner = LoggedOut()
        result = self.run_one("cursor", runner)
        self.assertEqual(result.status, "skipped")
        self.assertIn("not logged in", result.detail)
        self.assertEqual(result.workspace, "")
        self.assertFalse(os.path.exists(runner.cwd))

    def test_cursor_run_is_judged_on_the_plan_alone(self):
        result = self.run_one("cursor", FakeRunner(GOOD_PLAN, stdout="plain text"))
        self.assertEqual(result.status, "pass", result.detail)

    def test_skill_is_copied_into_both_agent_folders(self):
        runner = FakeRunner(plan_text=None)
        result = self.run_one("cursor", runner)
        for rel in run_agent_smoke.SKILL_INSTALL_DIRS:
            self.assertTrue(os.path.isfile(os.path.join(result.workspace, rel, "travel-planner", "SKILL.md")))


class CommandTest(unittest.TestCase):
    def test_claude_command_uses_allowlist_without_general_shell(self):
        command = run_agent_smoke.build_claude_command("claude", "/tmp/ws", "prompt")
        self.assertIn("--allowedTools", command)
        self.assertNotIn("--dangerously-skip-permissions", command)
        shell_rules = [c for c in command if c.startswith("Bash(")]
        self.assertTrue(shell_rules)
        for rule in shell_rules:
            self.assertRegex(rule, r"^Bash\(python3 \S+/scripts/(check_plan\.py \S*trip-plan\.md"
                                   r"|md_to_ics\.py \S*trip-plan\.md \S*trip-plan\.ics)\)$")
        allowed = command[command.index("--allowedTools") + 1:command.index("--disallowedTools")]
        self.assertNotIn("Bash", allowed)
        self.assertNotIn("Bash(*)", allowed)

    def test_claude_command_loads_project_skills_but_not_the_owners_settings(self):
        command = run_agent_smoke.build_claude_command("claude", "/tmp/ws", "prompt")
        self.assertNotIn("--restricted", command)
        self.assertIn("--strict-mcp-config", command)
        self.assertEqual(command[command.index("--setting-sources") + 1], "project")
        allowed = command[command.index("--allowedTools") + 1:command.index("--disallowedTools")]
        for open_ended in ("Read", "Write", "Edit", "Glob", "Grep"):
            self.assertNotIn(open_ended, allowed)
        self.assertFalse([rule for rule in command if rule.startswith("Write(")],
                         "Claude Code never consults Write(path) rules; Edit(path) covers writes")
        self.assertEqual(command[command.index("--permission-mode") + 1], "acceptEdits")
        self.assertEqual(command[command.index("--permission-prompts") + 1], "none")
        tools = command[command.index("--tools") + 1].split(",")
        for tool in ("Skill", "Bash", "WebFetch"):
            self.assertIn(tool, tools)
        self.assertEqual(command[command.index("--output-format") + 1], "stream-json")
        self.assertIn("--verbose", command)

    def test_claude_checker_rule_accepts_a_dot_slash_plan_path(self):
        command = run_agent_smoke.build_claude_command("claude", "/tmp/ws", "prompt")
        self.assertIn("Bash(python3 .claude/skills/travel-planner/scripts/check_plan.py ./trip-plan.md)", command)

    def test_claude_prompt_comes_before_the_list_flags(self):
        command = run_agent_smoke.build_claude_command("claude", "/tmp/ws", "the prompt")
        self.assertEqual(command[1:3], ["-p", "the prompt"])

    def test_cursor_runs_in_its_sandbox(self):
        command = run_agent_smoke.build_cursor_command("cursor-agent", "/tmp/ws", "p")
        self.assertEqual(command[command.index("--sandbox") + 1], "enabled")

    def test_claude_command_blocks_writes_to_the_copied_skill(self):
        command = run_agent_smoke.build_claude_command("claude", "/tmp/ws", "prompt")
        self.assertIn("--disallowedTools", command)
        denied = command[command.index("--disallowedTools") + 1:]
        for rel in run_agent_smoke.SKILL_INSTALL_DIRS:
            self.assertIn(f"Edit({rel}/**)", denied)

    def test_cursor_force_only_when_opted_in(self):
        self.assertNotIn("--force", run_agent_smoke.build_cursor_command("cursor-agent", "/tmp/ws", "p"))
        self.assertIn("--force", run_agent_smoke.build_cursor_command("cursor-agent", "/tmp/ws", "p", True))


if __name__ == "__main__":
    unittest.main()
