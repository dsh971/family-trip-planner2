#!/usr/bin/env python3
"""Install the skill with the real `skills` installer into a throwaway HOME
and confirm each agent's copy is complete. Stdlib only.

Run from the repo root (needs `npx` and network access):
    python3 tests/install_smoke.py

Prints SKIPPED and exits 0 when `npx` isn't installed. Not part of unit-test
discovery because it downloads the installer from npm.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from test_skill_package import check_package  # noqa: E402

INSTALLER = "skills@1.5.22"
AGENT_DIRS = {
    "claude-code": os.path.join(".claude", "skills"),
    # Codex and Cursor both read the shared ~/.agents/skills folder, which is
    # where the installer puts their copy.
    "codex": os.path.join(".agents", "skills"),
    "cursor": os.path.join(".agents", "skills"),
}
REQUIRED_FILES = [
    "SKILL.md",
    os.path.join("references", "00-overview.md"),
    os.path.join("scripts", "md_to_ics.py"),
    os.path.join("scripts", "check_plan.py"),
]


def main() -> int:
    npx = shutil.which("npx")
    if npx is None:
        print("SKIPPED: npx is not installed")
        return 0
    home = tempfile.mkdtemp(prefix="travel-planner-install-")
    try:
        command = [npx, "-y", INSTALLER, "add", REPO, "--skill", "travel-planner",
                   "-g", "-y", "--copy"]
        for agent in AGENT_DIRS:
            command += ["-a", agent]
        env = dict(os.environ, HOME=home, CI="1")
        result = subprocess.run(command, env=env, cwd=home, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"FAIL: installer exited {result.returncode}")
            print(result.stdout[-2000:])
            print(result.stderr[-2000:], file=sys.stderr)
            return 1
        failures = []
        for rel in dict.fromkeys(AGENT_DIRS.values()):
            agents = ", ".join(a for a, r in AGENT_DIRS.items() if r == rel)
            installed = os.path.join(home, rel, "travel-planner")
            missing = [f for f in REQUIRED_FILES if not os.path.isfile(os.path.join(installed, f))]
            if missing:
                failures.append(f"{agents}: missing {', '.join(missing)} in {installed}")
                continue
            problems = check_package(installed)
            if problems:
                failures.append(f"{agents}: " + "; ".join(problems))
            else:
                print(f"PASS {agents}: {installed}")
        for failure in failures:
            print(f"FAIL {failure}")
        return 1 if failures else 0
    finally:
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
