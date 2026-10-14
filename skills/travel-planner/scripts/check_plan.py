#!/usr/bin/env python3
"""Check a trip-plan markdown file against ../references/output-format-spec.md
and the methodology's mechanically checkable rules. Stdlib only.

Usage:
    python3 check_plan.py <trip-plan.md>

Errors (exit 1 unless every one is acknowledged):
  - the plan doesn't convert to a calendar (md_to_ics.py's own checks);
  - a row overlaps a blocking pacing window and isn't that window's own row
    (same times, titled with the window's name);
  - a place under Named by you / Picked from suggestions / Chosen for you, or
    a Meals restaurant, isn't visited on any day and isn't under Needs
    Attention. A row visits a place when its title names the place in full,
    not right after "to", "from", or "near", and not only as part of a longer
    recorded name; a neighborhood (noted "(neighborhood)") is also visited by
    any row located in it. A Needs Attention item covers a place only when it
    leads with the place's name (after an optional "City:");
  - with more than one city, a day heading doesn't name a city whose dates
    cover it, or a city's date has no day naming it (city names compare
    without case);
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
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import NamedTuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import md_to_ics  # noqa: E402

DAY_HEADING_RE = re.compile(r"^##\s+Day\s+(\d+)\s*[—–-]\s*(\d{4}-\d{2}-\d{2})(.*)$")
PLACES_HEADING_RE = re.compile(r"^###\s+(.+?):\s*places\s*$", re.IGNORECASE)
GROUP_LABEL_RE = re.compile(r"^\*\*(.+?):?\*\*:?\s*$")
MEAL_LINE_RE = re.compile(r"^Day\s+(\d+)\s+(lunch|dinner):\s*(.+)$", re.IGNORECASE)
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})")
WORD_RE = re.compile(r"[^\W_]+")
ARTICLES = {"the", "a", "an"}
REFERENCE_WORDS = {"to", "from", "near", "toward", "towards"}
NEIGHBORHOOD_RE = re.compile(r"\bneighbou?rhood\b", re.IGNORECASE)
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
    if raw[:1] in ("\"", "'"):
        close = raw.find(raw[0], 1)
        if close > 0:
            return raw[1:close]
    return raw.split(" #", 1)[0].strip()


def frontmatter_list(frontmatter: str, key: str) -> list[dict]:
    """Read a top-level list of mappings, the only list shape the spec uses
    (`pacing_windows`, `cities`), at any indentation. One level of nesting
    (e.g. `lodging:`) is kept as a dict. Not a general YAML reader."""
    items: list[dict] = []
    in_list = False
    current: dict | None = None
    field_indent = 0
    nested_key: str | None = None
    for line in frontmatter.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        is_item = stripped.startswith("- ")
        if indent == 0 and not (in_list and is_item):
            in_list = line.split(":", 1)[0].strip() == key
            current = None
            continue
        if not in_list:
            continue
        if is_item:
            current = {}
            items.append(current)
            nested_key = None
            rest = stripped[1:]
            field_indent = indent + 1 + len(rest) - len(rest.lstrip())
            stripped = rest.strip()
            indent = field_indent
        if current is None or ":" not in stripped:
            continue
        field, value = stripped.split(":", 1)
        field = field.strip()
        if indent <= field_indent:
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
            records.setdefault(city, {})
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


def is_neighborhood(item: str) -> bool:
    """'Old Harbour (neighborhood)' -> True: the note after the name says so."""
    return bool(NEIGHBORHOOD_RE.search(item[len(strip_note(item)):]))


# --- name matching --------------------------------------------------------

def words(value: str) -> list[str]:
    """Lowercase words with spelling noise removed: accents, possessive 's,
    apostrophes, and "&" (read as "and")."""
    value = unicodedata.normalize("NFKD", value.lower().replace("’", "'").replace("&", " and "))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"'s\b", "", value).replace("'", "")
    return WORD_RE.findall(value)


def name_words(name: str) -> list[str]:
    """A name's words without a leading article ("The Thimble Café")."""
    out = words(name)
    while out and out[0] in ARTICLES:
        out = out[1:]
    return out


def occurrences(needle: list[str], haystack: list[str]) -> list[int]:
    if not needle:
        return []
    return [i for i in range(len(haystack) - len(needle) + 1) if haystack[i : i + len(needle)] == needle]


def names(name: str, text: str, known_names: list[str] = (), visit: bool = False) -> bool:
    """`text` names `name` in full, not just as part of a longer known name
    ("Old Harbour" inside "Old Harbour Bakery"). With `visit`, a mention
    right after "to", "from", or "near" ("Travel to the Sea Cliffs") doesn't
    count."""
    needle, haystack = name_words(name), words(text)
    covered: set[int] = set()
    for other in map(name_words, known_names):
        if len(other) > len(needle) and occurrences(needle, other):
            for i in occurrences(other, haystack):
                covered.update(range(i, i + len(other)))
    for i in occurrences(needle, haystack):
        if covered.issuperset(range(i, i + len(needle))):
            continue
        before = i - 1
        while before >= 0 and haystack[before] in ARTICLES:
            before -= 1
        if visit and before >= 0 and haystack[before] in REFERENCE_WORDS:
            continue
        return True
    return False


# --- times ----------------------------------------------------------------

def minutes(cell: str) -> int | None:
    match = TIME_RE.match(cell.strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def row_interval(date_str: str, start_cell: str, end_cell: str, day_tz) -> tuple[int, int]:
    """A row's span in minutes on the day's own clock, with each cell read in
    its own zone and End rolled past Start as the converter does. Call only
    after build_events has accepted the plan."""
    start_hm = md_to_ics.parse_time(start_cell, "", "", "Start")
    end_hm = md_to_ics.parse_time(end_cell, "", "", "End")
    start_at = md_to_ics.local_time(date_str, start_hm[:2], start_hm[2] or day_tz, "")
    if end_hm is None:
        end_at = start_at + timedelta(hours=1)  # a blank End is one hour, as in the converter
    else:
        end_at = md_to_ics.local_time(date_str, end_hm[:2], end_hm[2] or day_tz, "")
        while end_at.astimezone(md_to_ics.UTC) <= start_at.astimezone(md_to_ics.UTC):
            end_at += timedelta(days=1)
    midnight = datetime.fromisoformat(date_str)

    def clock(moment: datetime) -> int:
        return int((moment.astimezone(day_tz).replace(tzinfo=None) - midnight).total_seconds() // 60)

    return clock(start_at), clock(end_at)


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
        flagged = row_title and any(row_title.lower() in item.lower() for item in attention_items)
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
    trip_tz = md_to_ics.ZoneInfo(tz_name)
    for d in days:
        for start_cell, end_cell, title, _location, _notes in d["rows"]:
            interval = row_interval(d["date"], start_cell, end_cell, d["zone"] or trip_tz)
            for w in windows:
                own_span = (w.start, w.end if w.end > w.start else w.end + DAY_MINUTES)
                if interval == own_span and names(w.name, title):
                    continue
                if any(interval[0] < b and a < interval[1] for a, b in w.spans):
                    report(d["label"], f"row '{title}' overlaps the {w.name} window {w.start_cell}–{w.end_cell}", title)

    # Places and meals.
    all_rows = [row for d in days for row in d["rows"]]
    records = places_records(text)
    known_names = [strip_note(item) for groups in records.values() for items in groups.values() for item in items]
    known_names += [strip_note(m.group(3)) for m in map(MEAL_LINE_RE.match, known_names) if m]

    def visited(name: str, rows: list[list[str]], by_location: bool = False) -> bool:
        return any(names(name, row[2], known_names, visit=True) or (by_location and names(name, row[3], known_names))
                   for row in rows)

    city_names = {city.casefold() for city in records}
    city_names |= {c.get("name", "").casefold() for c in frontmatter_list(frontmatter, "cities")}

    def flagged(name: str) -> bool:
        """A Needs Attention item covers a place when it leads with the name,
        after an optional "City:" ("**Blefuscu: Emperor's Palace** ...")."""
        needle = name_words(name)
        for item in attention_items:
            head, colon, rest = item.replace("*", "").partition(":")
            lead = name_words(rest if colon and head.strip().casefold() in city_names else head + colon + rest)
            if needle and lead[: len(needle)] == needle:
                return True
        return False

    for city, groups in records.items():
        for group, items in groups.items():
            if group in CHECKED_GROUPS:
                for item in items:
                    name = strip_note(item)
                    if not visited(name, all_rows, is_neighborhood(item)) and not flagged(name):
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
                    if not visited(restaurant, meal_rows) and not flagged(restaurant):
                        report(f"{city}: places",
                               f"Meals says Day {number} {meal} is '{restaurant}', but no {meal.title()} row on Day {number} names it")

    for d in days:
        for meal in ("Lunch", "Dinner"):
            if not any(is_meal_row(row, meal) for row in d["rows"]):
                findings.append(Finding("warning", d["label"], f"no {meal} row"))

    # Cities.
    cities = frontmatter_list(frontmatter, "cities")
    if len(cities) > 1:
        # A return to an earlier city is a separate entry with the same name.
        entries_by_name: dict[str, list[dict]] = {}
        for c in cities:
            entries_by_name.setdefault(c.get("name", "").casefold(), []).append(c)
        for _number, date_str, city in headings:
            entries = entries_by_name.get(city.casefold())
            if not entries:
                report(f"Day {date_str}", f"heading for {date_str} names city '{city}', which isn't in `cities`")
            elif not any(e.get("start_date", "") <= date_str <= e.get("end_date", "") for e in entries):
                ranges = ", ".join(f"{e.get('start_date')} to {e.get('end_date')}" for e in entries)
                report(f"Day {date_str}", f"heading for {date_str} names {city}, whose dates are {ranges}")
        named = {(date_str, city.casefold()) for _number, date_str, city in headings}
        for c in cities:
            try:
                first = date.fromisoformat(c.get("start_date", ""))
                last = date.fromisoformat(c.get("end_date", ""))
            except ValueError:
                report("cities", f"city '{c.get('name')}' has no valid start_date and end_date")
                continue
            current = first
            while current <= last:
                if (current.isoformat(), c.get("name", "").casefold()) not in named:
                    report("cities", f"{c.get('name')} has no day heading for {current.isoformat()}")
                current += timedelta(days=1)
    recorded = {city.casefold() for city in records}
    for c in cities:
        if c.get("status") == "planned" and c.get("name", "").casefold() not in recorded:
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
