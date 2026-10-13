#!/usr/bin/env python3
"""Convert a trip-plan markdown file (see core/output-format-spec.md) into a
standard .ics calendar file. Stdlib only — no pip install required.

Usage:
    python3 md_to_ics.py <trip-plan.md> <output.ics>

The only things this script reads from the input file:
  - `timezone` from the YAML frontmatter (an IANA name), and `trip_name`
    (only to keep event UIDs unique across trips).
  - Each "## Day N — YYYY-MM-DD" heading, for that day's date and its
    optional " · <IANA zone>" override.
  - The GFM table immediately following each day heading, with the exact
    header "Start | End | Title | Location | Notes". A Start/End cell may be
    "HH:MM" or "HH:MM <IANA zone>".

Everything else in the file (prose sections, other frontmatter fields) is
ignored. See core/output-format-spec.md for the full contract this script
implements.
"""
import hashlib
import re
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

EXPECTED_COLUMNS = ["Start", "End", "Title", "Location", "Notes"]

# The separator after the day number may be an em dash, en dash, or hyphen —
# models and editors swap these freely. Any "## Day" line that still doesn't
# match is an error, never a silent skip. An optional trailing "· <IANA zone>"
# overrides the trip timezone for that day.
DAY_HEADING_RE = re.compile(
    r"^##\s+Day\s+(\d+)\s*[—–-]\s*(\d{4}-\d{2}-\d{2})\b[^·]*(?:·\s*(\S+)\s*)?$"
)
DAY_HEADING_PREFIX_RE = re.compile(r"^##\s+Day\s+\d")
# GFM lets a row omit its trailing pipe, so a row is any line starting with one.
TABLE_ROW_RE = re.compile(r"^\s*\|")
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")
UTC = ZoneInfo("UTC")
SEPARATOR_ROW_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


class TripPlanError(Exception):
    """A clear, user-facing error about malformed input — never a silent skip."""


def load_zone(name: str, where: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        if not available_timezones():
            raise TripPlanError(
                f"{where}: can't resolve {name!r} — this machine has no IANA timezone database "
                "(common on Windows). The plan may be fine; run the converter where one is installed."
            ) from exc
        raise TripPlanError(f"{where}: {name!r} is not a recognized IANA timezone name.") from exc


def read_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        raise TripPlanError("File does not start with YAML frontmatter (expected a leading '---' line).")
    end = text.find("\n---", 3)
    if end == -1:
        raise TripPlanError("Frontmatter is not closed with a second '---' line.")
    return text[3:end]


def frontmatter_value(frontmatter: str, key: str) -> str | None:
    """A top-level scalar, quoted or not, with an optional trailing # comment."""
    match = re.search(
        rf"""^{key}:\s*(?:"([^"]*)"|'([^']*)'|([^#\s][^#]*?))\s*(?:#.*)?$""", frontmatter, re.MULTILINE
    )
    if not match:
        return None
    return next(group for group in match.groups() if group is not None)


def extract_timezone(text: str) -> str:
    tz_name = frontmatter_value(read_frontmatter(text), "timezone")
    if not tz_name:
        raise TripPlanError(
            "Frontmatter is missing a `timezone` field (required, IANA name, e.g. \"America/Los_Angeles\")."
        )
    load_zone(tz_name, "Frontmatter `timezone`")
    return tz_name


def split_row(line: str) -> list[str]:
    # Strip one leading/trailing '|' (if present) before splitting, so a row
    # like "| a | b |" doesn't produce empty leading/trailing cells. An escaped
    # "\|" is a literal pipe inside a cell, per GFM.
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    return [cell.strip().replace("\\|", "|") for cell in UNESCAPED_PIPE_RE.split(stripped)]


def find_table_after(lines: list[str], start_index: int, day_label: str) -> tuple[list[list[str]], int]:
    """Find and parse the first GFM table starting at or after start_index.
    Returns (data_rows, index_after_table). Raises TripPlanError if no valid
    table is found before the next section heading or end of day-chunk.
    """
    i = start_index
    n = len(lines)
    while i < n and not lines[i].strip():
        i += 1
    if i >= n or not TABLE_ROW_RE.match(lines[i]):
        raise TripPlanError(f"{day_label}: no schedule table found immediately after the day heading.")

    header_cells = split_row(lines[i])
    if header_cells != EXPECTED_COLUMNS:
        raise TripPlanError(
            f"{day_label}: table header is {header_cells}, expected exactly {EXPECTED_COLUMNS}."
        )
    i += 1
    if i >= n or not SEPARATOR_ROW_RE.match(lines[i]):
        raise TripPlanError(f"{day_label}: table is missing its '|---|...' separator row.")
    i += 1

    rows = []
    while i < n and TABLE_ROW_RE.match(lines[i]):
        cells = split_row(lines[i])
        if len(cells) != len(EXPECTED_COLUMNS):
            raise TripPlanError(
                f"{day_label}: row {i + 1} has {len(cells)} columns, expected {len(EXPECTED_COLUMNS)}: {lines[i]!r}"
            )
        rows.append(cells)
        i += 1
    next_content = i
    while next_content < n and not lines[next_content].strip():
        next_content += 1
    if next_content < n and TABLE_ROW_RE.match(lines[next_content]):
        raise TripPlanError(
            f"{day_label}: line {next_content + 1} is a table row after a blank line — a blank line ends "
            "a markdown table, so it wouldn't be part of this day. Remove the blank line."
        )
    return rows, i


def parse_days(text: str) -> list[dict]:
    lines = text.splitlines()
    days = []
    i = 0
    n = len(lines)
    while i < n:
        match = DAY_HEADING_RE.match(lines[i])
        if match:
            day_num, date_str, zone_name = match.group(1), match.group(2), match.group(3)
            day_label = f"Day {day_num} ({date_str})"
            zone = load_zone(zone_name, f"{day_label} heading") if zone_name else None
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError as exc:
                raise TripPlanError(f"{day_label}: heading date is not a valid calendar date.") from exc
            rows, next_i = find_table_after(lines, i + 1, day_label)
            days.append({"label": day_label, "date": date_str, "zone": zone, "rows": rows})
            i = next_i
            continue
        if DAY_HEADING_PREFIX_RE.match(lines[i]):
            raise TripPlanError(
                f"Line {i + 1}: {lines[i]!r} looks like a day heading but doesn't match "
                "'## Day N — YYYY-MM-DD (Weekday)'."
            )
        i += 1
    if not days:
        raise TripPlanError("No '## Day N — YYYY-MM-DD' headings found — nothing to convert.")
    return days


def parse_time(
    value: str, day_label: str, row_title: str, field: str
) -> tuple[int, int, ZoneInfo | None] | None:
    """Parse "HH:MM" or "HH:MM <IANA zone>". The zone is None when the cell
    doesn't name one (the caller falls back to the day's or trip's zone)."""
    value = value.strip()
    if not value:
        return None
    where = f"{day_label}, row '{row_title}', {field}"
    match = re.match(r"^(\d{1,2}):(\d{2})(?:\s+(\S+))?$", value)
    if not match:
        raise TripPlanError(f"{where}: {value!r} is not HH:MM 24-hour time (optionally followed by an IANA zone).")
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise TripPlanError(f"{where}: {value!r} is out of range.")
    zone = load_zone(match.group(3), where) if match.group(3) else None
    return hour, minute, zone


def escape_text(value: str) -> str:
    # RFC 5545 §3.3.11 escaping for TEXT values.
    value = value.replace("\\", "\\\\")
    value = value.replace(";", "\\;")
    value = value.replace(",", "\\,")
    value = value.replace("\n", "\\n")
    return value


def fold_line(line: str) -> str:
    # RFC 5545 §3.1 line folding: at most 75 octets per line (UTF-8 bytes, not
    # characters), never splitting a multi-byte character; continuation lines
    # start with a single space, which counts toward their 75.
    parts = []
    current = ""
    current_octets = 0
    for char in line:
        char_octets = len(char.encode("utf-8"))
        if current_octets + char_octets > 75:
            parts.append(current)
            current = " "
            current_octets = 1
        current += char
        current_octets += char_octets
    parts.append(current)
    return "\r\n".join(parts)


def local_time(date_str: str, hm: tuple[int, int], tz: ZoneInfo, where: str) -> datetime:
    year, month, dom = (int(p) for p in date_str.split("-"))
    value = datetime(year, month, dom, hm[0], hm[1], tzinfo=tz)
    round_trip = value.astimezone(UTC).astimezone(tz)
    if (round_trip.hour, round_trip.minute) != hm:
        raise TripPlanError(
            f"{where}: {hm[0]:02d}:{hm[1]:02d} doesn't exist in {tz.key} on {date_str} "
            "(clocks skip it for daylight saving)."
        )
    return value


def build_events(days: list[dict], tz_name: str, trip_name: str = "") -> list[str]:
    trip_tz = ZoneInfo(tz_name)
    now_utc = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    # Overnight rows (e.g. a 19:30-07:00 bedtime window) roll End forward to
    # the next day; past 12 hours, End-before-Start is far likelier a typo.
    # A row whose Start and End are in different zones is a journey (a flight),
    # which may legitimately take up to 20 hours.
    max_rollover = timedelta(hours=12)
    max_rollover_cross_zone = timedelta(hours=20)
    seen_uids: dict[str, str] = {}
    events = []
    for day in days:
        date_str = day["date"]
        day_tz = day["zone"] or trip_tz
        for row in day["rows"]:
            start_cell, end_cell, title, location, notes = row
            start_hm = parse_time(start_cell, day["label"], title or "(untitled)", "Start")
            if start_hm is None:
                raise TripPlanError(f"{day['label']}, row '{title}': Start time is required and cannot be blank.")
            end_hm = parse_time(end_cell, day["label"], title or "(untitled)", "End")

            where = f"{day['label']}, row '{title}'"
            start_tz = start_hm[2] or day_tz
            start_at = local_time(date_str, start_hm[:2], start_tz, f"{where}, Start").astimezone(UTC)
            if end_hm is not None:
                end_tz = end_hm[2] or day_tz
                end_local = local_time(date_str, end_hm[:2], end_tz, f"{where}, End")
                # Compare in UTC: aware datetimes sharing a tzinfo compare by wall
                # clock, which is wrong across a daylight-saving change.
                rolled_over = end_local.astimezone(UTC) <= start_at
                while end_local.astimezone(UTC) <= start_at:
                    end_local += timedelta(days=1)
                end_at = end_local.astimezone(UTC)
                if end_tz.key != start_tz.key:
                    limit, length = max_rollover_cross_zone, end_at - start_at
                else:
                    # Same zone: judge the typo check by the wall clock the plan's
                    # author wrote, so a 19:30-07:00 bedtime stays 11.5h even on
                    # the night clocks go back.
                    start_wall = start_at.astimezone(start_tz).replace(tzinfo=None)
                    limit, length = max_rollover, end_local.replace(tzinfo=None) - start_wall
                if rolled_over and length > limit:
                    raise TripPlanError(
                        f"{where}: End {end_cell} is before Start {start_cell}. "
                        f"Rolling it past midnight would make the row {length} long "
                        f"(limit {limit}) — check for a typo."
                    )
            else:
                end_at = start_at + timedelta(hours=1)

            start_utc = start_at.strftime("%Y%m%dT%H%M%SZ")
            end_utc = end_at.strftime("%Y%m%dT%H%M%SZ")

            # trip_name keeps two plans' same-day, same-time, same-title rows
            # (e.g. "08:00 Breakfast") from overwriting each other on import.
            uid_source = f"{trip_name}|{date_str}|{start_cell}|{title}".encode("utf-8")
            uid = hashlib.sha1(uid_source).hexdigest() + "@trip-plan"
            if uid in seen_uids:
                raise TripPlanError(
                    f"{day['label']}, row '{title}': same date, Start, and Title as an earlier row "
                    f"({seen_uids[uid]}) — calendar event IDs would collide. Make the titles distinct."
                )
            seen_uids[uid] = f"{day['label']} {start_cell}"

            lines = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_utc}",
                f"DTSTART:{start_utc}",
                f"DTEND:{end_utc}",
                f"SUMMARY:{escape_text(title)}",
            ]
            if location:
                lines.append(f"LOCATION:{escape_text(location)}")
            if notes:
                lines.append(f"DESCRIPTION:{escape_text(notes)}")
            lines.append("END:VEVENT")
            events.extend(fold_line(line) for line in lines)
    return events


def convert(input_path: str, output_path: str) -> int:
    # utf-8-sig: tolerate the byte-order mark some Windows editors add.
    with open(input_path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    tz_name = extract_timezone(text)
    trip_name = frontmatter_value(read_frontmatter(text), "trip_name") or ""
    days = parse_days(text)
    events = build_events(days, tz_name, trip_name)

    calendar = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//travel-planner2//md-to-ics//EN",
        "CALSCALE:GREGORIAN",
        *events,
        "END:VCALENDAR",
    ]

    # newline="" — lines are already joined with CRLF; any other mode would
    # translate each "\n" again and produce "\r\r\n".
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(calendar) + "\r\n")

    event_count = sum(1 for line in events if line == "BEGIN:VEVENT")
    print(f"Wrote {event_count} event(s) across {len(days)} day(s) to {output_path}")
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <trip-plan.md> <output.ics>", file=sys.stderr)
        return 2
    try:
        return convert(sys.argv[1], sys.argv[2])
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except TripPlanError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
