"""Package checks for the travel-planner skill folder. Stdlib only.

The skill folder is what installers copy into each agent's skill directory,
so it must be self-contained and follow the Agent Skills spec. Run from the
repo root:
    python3 -m unittest discover -s tests -v
"""
import os
import re
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SKILL_DIR = os.path.join(REPO, "skills", "travel-planner")

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Backticked text that looks like a relative file path. Placeholders such as
# `<a reasonable filename>.md` or a bare `.md` are not paths.
PATH_TOKEN_RE = re.compile(r"`((?:\.\./)*[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:md|py))`")
PURITY_RE = re.compile(r"claude|codex|perplexity|google|goat|tabelog", re.IGNORECASE)
MAX_SKILL_LINES = 500
MAX_DESCRIPTION = 1024


def read_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


def doc_files(skill_dir: str) -> list[str]:
    files = [os.path.join(skill_dir, "SKILL.md")]
    for sub in ("references", "integrations"):
        folder = os.path.join(skill_dir, sub)
        if os.path.isdir(folder):
            files += sorted(
                os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".md")
            )
    return files


def check_package(skill_dir: str) -> list[str]:
    """Return one problem string per broken rule; empty when the folder is valid."""
    problems: list[str] = []
    skill_dir = os.path.realpath(skill_dir)
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return [f"missing SKILL.md in {skill_dir}"]

    for dirpath, dirnames, filenames in os.walk(skill_dir):
        for entry in dirnames + filenames:
            full = os.path.join(dirpath, entry)
            if os.path.islink(full):
                problems.append(f"symlink not allowed: {os.path.relpath(full, skill_dir)}")

    with open(skill_md, encoding="utf-8") as f:
        text = f.read()
    fields = read_frontmatter(text)
    name = fields.get("name", "")
    folder = os.path.basename(skill_dir)
    if not NAME_RE.match(name) or len(name) > 64:
        problems.append(f"invalid name {name!r}: lowercase letters, digits, single hyphens, at most 64")
    if name != folder:
        problems.append(f"name {name!r} does not match folder {folder!r}")
    description = fields.get("description", "")
    if not 1 <= len(description) <= MAX_DESCRIPTION:
        problems.append(f"description must be 1-{MAX_DESCRIPTION} characters, got {len(description)}")
    line_count = len(text.splitlines())
    if line_count >= MAX_SKILL_LINES:
        problems.append(f"SKILL.md has {line_count} lines; keep it under {MAX_SKILL_LINES}")

    for path in doc_files(skill_dir):
        rel_doc = os.path.relpath(path, skill_dir)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for token in PATH_TOKEN_RE.findall(content):
            target = os.path.realpath(os.path.join(os.path.dirname(path), token))
            if not target.startswith(skill_dir + os.sep):
                problems.append(f"{rel_doc}: `{token}` points outside the skill folder")
            elif not os.path.isfile(target):
                problems.append(f"{rel_doc}: `{token}` does not exist")

    references = os.path.join(skill_dir, "references")
    for path in doc_files(skill_dir):
        if os.path.dirname(path) != references:
            continue
        with open(path, encoding="utf-8") as f:
            for number, line in enumerate(f, 1):
                match = PURITY_RE.search(line)
                if match:
                    problems.append(
                        f"references/{os.path.basename(path)}:{number} names a tool or platform ({match.group(0)})"
                    )
    return problems


class RealSkillFolderTest(unittest.TestCase):
    def test_real_skill_folder_passes(self):
        self.assertEqual(check_package(SKILL_DIR), [])


class BrokenCopyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.copy = os.path.join(self.tmp, "travel-planner")
        shutil.copytree(SKILL_DIR, self.copy, symlinks=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel: str, old: str, new: str) -> None:
        path = os.path.join(self.copy, rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new, 1))

    def assertProblem(self, fragment: str) -> None:
        problems = check_package(self.copy)
        self.assertTrue(
            any(fragment in p for p in problems),
            f"expected a problem containing {fragment!r}, got {problems}",
        )

    def test_copy_passes_before_any_change(self):
        self.assertEqual(check_package(self.copy), [])

    def test_symlink_pointing_outside_fails_and_is_named(self):
        os.symlink(self.tmp, os.path.join(self.copy, "references", "outside"))
        self.assertProblem("symlink not allowed: references/outside")

    def test_name_not_matching_folder_fails(self):
        self.edit("SKILL.md", "name: travel-planner", "name: trip-planner")
        self.assertProblem("does not match folder")

    def test_uppercase_name_fails(self):
        self.edit("SKILL.md", "name: travel-planner", "name: Travel-Planner")
        self.assertProblem("invalid name")

    def test_overlong_description_fails(self):
        fields = read_frontmatter(open(os.path.join(self.copy, "SKILL.md"), encoding="utf-8").read())
        self.edit("SKILL.md", fields["description"], "x" * (MAX_DESCRIPTION + 1))
        self.assertProblem("description must be")

    def test_skill_md_at_line_limit_fails(self):
        with open(os.path.join(self.copy, "SKILL.md"), "a", encoding="utf-8") as f:
            f.write("\n" * MAX_SKILL_LINES)
        self.assertProblem("keep it under")

    def test_missing_reference_fails_and_is_named(self):
        self.edit("SKILL.md", "`references/intake-questions.md`", "`references/no-such-doc.md`")
        self.assertProblem("`references/no-such-doc.md` does not exist")

    def test_reference_pointing_outside_folder_fails(self):
        self.edit("references/00-overview.md", "`intake-questions.md`", "`../../../README.md`")
        self.assertProblem("points outside the skill folder")

    def test_placeholder_tokens_are_not_paths(self):
        self.edit("SKILL.md", "## Workflow", "Save as `<a reasonable filename>.md` or `.md`.\n\n## Workflow")
        self.assertEqual(check_package(self.copy), [])

    def test_tool_name_in_reference_fails_purity(self):
        self.edit("references/intake-questions.md", "# Intake Questions", "# Intake Questions\n\nUse Codex here.")
        self.assertProblem("references/intake-questions.md:3 names a tool or platform")


if __name__ == "__main__":
    unittest.main()
