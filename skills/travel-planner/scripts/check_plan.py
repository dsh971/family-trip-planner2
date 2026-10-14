#!/usr/bin/env python3
"""Check a trip-plan markdown file against ../references/output-format-spec.md
and the methodology's mechanically checkable rules. Stdlib only.

Usage:
    python3 check_plan.py <trip-plan.md>

Errors (exit 1 unless every one is acknowledged):
  - the plan doesn't convert to a calendar (md_to_ics.py's own checks);
  - a row overlaps a blocking pacing window and isn't that window's own row;
  - a place under Named by you / Picked from suggestions / Chosen for you, or
    a Meals restaurant, appears in no day's rows and not under Needs Attention;
  - with more than one city, a day heading doesn't name a city whose dates
    cover it, or a city's date has no day naming it;
  - a city marked `planned` has no places record.
An error about a row whose title is named under Needs Attention is reported
as acknowledged and doesn't fail the check.

Warnings (never fail): a day with no Lunch or Dinner row.

Exit codes: 0 no unacknowledged errors, 1 errors, 2 file unreadable or bad
usage.
"""
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from typing import NamedTuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import md_to_ics  # noqa: E402

DAY_HEADING_RE = re.compile(r"^##\s+Day\s+(\d+)\s*[—–-]\s*(\d{4}-\d{2}-\d{2})(.*)$")
PLACES_HEADING_RE = re.compile(r"^###\s+(.+?):\s*places\s*$", re.IGNORECASE)
GROUP_LABEL_RE = re.compile(r"^\*\*(.+?):?\*\*:?\s*$")
MEAL_LINE_RE = re.compile(r"^Day\s+(\d+)\s+(lunch|dinner):\s*(.+)$", re.IGNORECASE)
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})")
WORD_RE = re.compile(r"[a-z0-9']+")
STOPWORDS = {"the", "a", "an", "of", "at", "in", "on", "and", "to", "for", "by", "near"}
CHECKED_GROUPS = {"named by you", "picked from suggestions", "chosen for you"}
DAY_MINUTES = 24 * 60


class BlockingWindow(NamedTuple):
    name: str
    start_cell: str
    end_cell: str
    start: int
    end: int
    spans: list[tuple[int, int]]


@dataclass
class Finding:
    severity: str  # "error", "acknowledged", or "warning"
    where: str
    message: str


# --- frontmatter ----------------------------------------------------------

def _scalar(raw: str) -> str:
    raw = raw.strip()
    if raw[:1] in "\"'" and raw[-1:] == raw[:1] and len(raw) >= 2:
        return raw[1:-1]
    return raw.split(" #", 1)[0].strip()


def frontmatter_list(frontmatter: str, key: str) -> list[dict]:
    """Read a top-level list of mappings, the only list shape the spec uses
    (`pacing_windows`, `cities`). One level of nesting (e.g. `lodging:`) is
    kept as a dict. Not a general YAML reader."""
    lines = frontmatter.splitlines()
    items: list[dict] = []
    in_list = False
    current: dict | None = None
    nested_key: str | None = None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_list = line.split(":", 1)[0].strip() == key
            current = None
            continue
        if not in_list:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            current = {}
            items.append(current)
            nested_key = None
            stripped = stripped[2:]
            indent += 2
        if current is None or ":" not in stripped:
            continue
        field, value = stripped.split(":", 1)
        field = field.strip()
        if indent <= 4:
            if value.strip():
                current[field] = _scalar(value)
                nested_key = None
            else:
                current[field] = {}
                nested_key = field
        elif nested_key and isinstance(current.get(nested_key), dict):
            current[nested_key][field] = _scalar(value)
    return items


# --- plan structure -------------------------------------------------------

def section_text(text: str, heading: str) -> str:
    """Body of a `## <heading>` section, up to the next `## ` heading."""
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    rest = text[match.end():]
    end = re.search(r"^##\s", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def heading_cities(text: str) -> list[tuple[str, str, str]]:
    """(day number, date, city) for each day heading, in order. The city is
    the text after the weekday and before any ' · <zone>' suffix; empty when
    not named."""
    out = []
    for line in text.splitlines():
        match = DAY_HEADING_RE.match(line)
        if not match:
            continue
        rest = match.group(3).split("·", 1)[0]
        rest = re.sub(r"^\s*\([^)]*\)", "", rest)
        city = rest.strip().lstrip("—–-").strip()
        out.append((match.group(1), match.group(2), city))
    return out


def places_records(text: str) -> dict[str, dict[str, list[str]]]:
    """{city: {group label (lowercase): [bullet text, ...]}}."""
    records: dict[str, dict[str, list[str]]] = {}
    city = None
    group = None
    for line in text.splitlines():
        heading = PLACES_HEADING_RE.match(line)
        if heading:
            city = heading.group(1).strip()
            records[city] = {}
            group = None
            continue
        if line.startswith("#"):
            city = None
            continue
        if city is None:
            continue
        label = GROUP_LABEL_RE.match(line.strip())
        if label:
            group = label.group(1).strip().rstrip(":").lower()
            records[city].setdefault(group, [])
            continue
        if group and line.startswith("- "):
            records[city][group].append(line[2:].strip())
    return records


def strip_note(item: str) -> str:
    """'Royal Gardens (attraction)' -> 'Royal Gardens'."""
    return re.sub(r"\s*\(.*$", "", item).strip().rstrip(".")


# --- name matching --------------------------------------------------------

def significant_words(value: str) -> list[str]:
    words = WORD_RE.findall(value.lower().replace("’", "'"))
    return [w for w in words if w not in STOPWORDS]


def name_matches(name: str, text: str) -> bool:
    """A one- or two-word name must appear as a whole phrase; a longer name
    matches when 60% or more of its significant words appear."""
    name_words = significant_words(name)
    text_words = significant_words(text)
    if not name_words:
        return False
    if len(name_words) <= 2:
        size = len(name_words)
        return any(text_words[i : i + size] == name_words for i in range(len(text_words) - size + 1))
    present = sum(1 for w in name_words if w in text_words)
    return present / len(name_words) >= 0.6


# --- times ----------------------------------------------------------------

def minutes(cell: str) -> int | None:
    match = TIME_RE.match(cell.strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def row_interval(start_cell: str, end_cell: str) -> tuple[int, int] | None:
    start = minutes(start_cell)
    if start is None:
        return None
    end = minutes(end_cell)
    if end is None:
        end = start + 60  # a blank End is one hour, as in the converter
    elif end <= start:
        end += DAY_MINUTES
    return start, end


def is_meal_row(row: list[str], meal: str) -> bool:
    """Meal rows are titled starting "Lunch" or "Dinner" (the spec's convention)."""
    return row[2].lower().startswith(meal.lower())


def window_intervals(start: int, end: int) -> list[tuple[int, int]]:
    """A window's span on one day's clock; an overnight window covers the
    early morning (from the night before) and the late evening."""
    if end > start:
        return [(start, end)]
    return [(0, end), (start, DAY_MINUTES + end)]


# --- the check ------------------------------------------------------------

def check(text: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        frontmatter = md_to_ics.read_frontmatter(text)
        tz_name = md_to_ics.extract_timezone(text)
        trip_name = md_to_ics.frontmatter_value(frontmatter, "trip_name") or ""
        days = md_to_ics.parse_days(text)
        md_to_ics.build_events(days, tz_name, trip_name)
    except md_to_ics.TripPlanError as exc:
        return [Finding("error", "format", str(exc))]

    # The converter rejects any "## Day" line it can't parse, so these headings
    # line up one-to-one with `days`.
    headings = heading_cities(text)
    rows_by_number = {number: d["rows"] for (number, _date, _city), d in zip(headings, days)}
    attention = section_text(text, "Needs Attention")
    attention_items = [line[2:] for line in attention.splitlines() if line.startswith("- ")]

    def report(where: str, message: str, row_title: str | None = None) -> None:
        flagged = row_title and any(name_matches(row_title, item) or row_title.lower() in item.lower()
                                    for item in attention_items)
        findings.append(Finding("acknowledged" if flagged else "error", where, message))

    # Blocking windows.
    windows = []
    for window in frontmatter_list(frontmatter, "pacing_windows"):
        if str(window.get("blocking", "")).lower() != "true":
            continue
        start, end = minutes(window.get("start", "")), minutes(window.get("end", ""))
        if start is None or end is None:
            continue
        windows.append(BlockingWindow(window.get("name", "blocking window"), window["start"], window["end"],
                                      start, end, window_intervals(start, end)))
    for d in days:
        for start_cell, end_cell, title, _location, _notes in d["rows"]:
            interval = row_interval(start_cell, end_cell)
            if interval is None:
                continue
            row_bounds = (minutes(start_cell), minutes(end_cell))
            for w in windows:
                if row_bounds == (w.start, w.end):
                    continue
                if any(interval[0] < b and a < interval[1] for a, b in w.spans):
                    report(d["label"], f"row '{title}' overlaps the {w.name} window {w.start_cell}–{w.end_cell}", title)

    # Places and meals.
    all_rows = [row for d in days for row in d["rows"]]
    row_texts = [f"{row[2]} {row[3]}" for row in all_rows]
    records = places_records(text)
    for city, groups in records.items():
        for group, items in groups.items():
            if group in CHECKED_GROUPS:
                for item in items:
                    name = strip_note(item)
                    if not any(name_matches(name, t) for t in row_texts) and not any(
                        name_matches(name, a) for a in attention_items
                    ):
                        report(f"{city}: places", f"'{name}' ({group}) is on no day and not under Needs Attention")
            if group == "meals":
                for item in items:
                    match = MEAL_LINE_RE.match(item)
                    if not match:
                        continue
                    number, meal, restaurant = match.group(1), match.group(2).lower(), strip_note(match.group(3))
                    if restaurant.lower().startswith("none"):
                        continue
                    meal_rows = [r for r in rows_by_number.get(number, []) if is_meal_row(r, meal)]
                    if not any(name_matches(restaurant, f"{r[2]} {r[3]}") for r in meal_rows):
                        report(f"{city}: places",
                               f"Meals says Day {number} {meal} is '{restaurant}', but no {meal.title()} row on Day {number} names it")

    for d in days:
        for meal in ("Lunch", "Dinner"):
            if not any(is_meal_row(row, meal) for row in d["rows"]):
                findings.append(Finding("warning", d["label"], f"no {meal} row"))

    # Cities.
    cities = frontmatter_list(frontmatter, "cities")
    if len(cities) > 1:
        names = {c.get("name", ""): c for c in cities}
        for _number, date_str, city in headings:
            entry = names.get(city)
            if entry is None:
                report(f"Day {date_str}", f"heading for {date_str} names city '{city}', which isn't in `cities`")
            elif not entry.get("start_date", "") <= date_str <= entry.get("end_date", ""):
                report(f"Day {date_str}", f"heading for {date_str} names {city}, whose dates are "
                                          f"{entry.get('start_date')} to {entry.get('end_date')}")
        named = {(date_str, city) for _number, date_str, city in headings}
        for c in cities:
            try:
                first = date.fromisoformat(c.get("start_date", ""))
                last = date.fromisoformat(c.get("end_date", ""))
            except ValueError:
                report("cities", f"city '{c.get('name')}' has no valid start_date and end_date")
                continue
            current = first
            while current <= last:
                if (current.isoformat(), c.get("name")) not in named:
                    report("cities", f"{c.get('name')} has no day heading for {current.isoformat()}")
                current += timedelta(days=1)
    for c in cities:
        if c.get("status") == "planned" and c.get("name") not in records:
            report("cities", f"{c.get('name')} is marked planned but has no places record ('### {c.get('name')}: places')")

    return findings


def exit_code(findings: list[Finding]) -> int:
    return 1 if any(f.severity == "error" for f in findings) else 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <trip-plan.md>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    findings = check(text)
    for f in findings:
        print(f"{f.severity.upper()} {f.where}: {f.message}")
    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("error", "acknowledged", "warning")}
    print(f"{counts['error']} error(s), {counts['acknowledged']} acknowledged, {counts['warning']} warning(s)")
    return exit_code(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
