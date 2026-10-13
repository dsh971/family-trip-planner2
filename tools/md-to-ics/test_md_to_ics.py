"""Tests for md_to_ics.py. Stdlib only.

Run from the repo root:
    python3 -m unittest discover -s tools/md-to-ics -v
"""
import contextlib
import io
import os
import re
import tempfile
import unittest
from unittest import mock

import md_to_ics

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "..", "..", "examples", "trip-plans", "sample-trip-lilliput.md")

HEADER = "| Start | End | Title | Location | Notes |\n|---|---|---|---|---|\n"


def plan(*days: str, timezone: str = "Europe/London", trip_name: str = "T") -> str:
    return f'---\ntrip_name: "{trip_name}"\ntimezone: "{timezone}"\n---\n\n# T\n\n' + "\n".join(days)


def day(heading: str, *rows: str) -> str:
    return f"{heading}\n\n{HEADER}" + "".join(r + "\n" for r in rows)


def convert_text(text: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "plan.md")
        out = os.path.join(tmp, "plan.ics")
        with open(src, "w", encoding="utf-8") as f:
            f.write(text)
        with contextlib.redirect_stdout(io.StringIO()):
            md_to_ics.convert(src, out)
        with open(out, "rb") as f:
            return f.read()


def unfold(data: bytes) -> list[str]:
    return data.decode("utf-8").replace("\r\n ", "").split("\r\n")


def prop(data: bytes, name: str) -> list[str]:
    return [line.split(":", 1)[1] for line in unfold(data) if line.startswith(name + ":")]


class SampleTest(unittest.TestCase):
    def test_sample_converts(self) -> None:
        with open(SAMPLE, encoding="utf-8") as f:
            text = f.read()
        data = convert_text(text)
        day_headings = len(re.findall(r"^## Day ", text, re.MULTILINE))
        self.assertGreater(day_headings, 0)
        self.assertEqual(len(prop(data, "UID")), len(set(prop(data, "UID"))))

    def test_uids_stable_across_runs(self) -> None:
        with open(SAMPLE, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(prop(convert_text(text), "UID"), prop(convert_text(text), "UID"))


class FrontmatterTest(unittest.TestCase):
    def test_timezone_with_comment_or_single_quotes(self) -> None:
        for line in ['timezone: "Europe/London"   # IANA tz name', "timezone: 'Europe/London'"]:
            with self.subTest(line=line):
                self.assertEqual(md_to_ics.extract_timezone(f"---\n{line}\n---\n"), "Europe/London")

    def test_utf8_bom_is_accepted(self) -> None:
        data = convert_text("\ufeff" + plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | | |")))
        self.assertEqual(prop(data, "SUMMARY"), ["A"])

    def test_uids_differ_between_trips(self) -> None:
        row = day("## Day 1 — 2026-11-10 (Tuesday)", "| 08:00 | 09:00 | Breakfast | | |")
        self.assertNotEqual(
            prop(convert_text(plan(row, trip_name="Lilliput")), "UID"),
            prop(convert_text(plan(row, trip_name="Brobdingnag")), "UID"),
        )


class LineEndingTest(unittest.TestCase):
    def test_every_line_ends_in_single_crlf(self) -> None:
        data = convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | B | C |")))
        self.assertNotIn(b"\r\r", data)
        self.assertTrue(data.endswith(b"END:VCALENDAR\r\n"))
        self.assertNotIn(b"\n", data.replace(b"\r\n", b""))


class HeadingTest(unittest.TestCase):
    def test_accepts_em_dash_en_dash_and_hyphen(self) -> None:
        for sep in ["—", "–", "-"]:
            with self.subTest(sep=sep):
                text = plan(
                    day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | | |"),
                    day(f"## Day 2 {sep} 2026-11-11 (Wednesday)", "| 09:00 | 10:00 | B | | |"),
                )
                self.assertEqual(len(md_to_ics.parse_days(text)), 2)

    def test_unparseable_day_heading_is_an_error_not_a_skip(self) -> None:
        text = plan(
            day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | | |"),
            day("## Day 2: 2026-11-11", "| 09:00 | 10:00 | B | | |"),
        )
        with self.assertRaises(md_to_ics.TripPlanError):
            md_to_ics.parse_days(text)

    def test_non_day_heading_starting_with_day_is_ignored(self) -> None:
        text = plan("## Day trips worth considering\n\nProse.\n", day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | | |"))
        self.assertEqual(len(md_to_ics.parse_days(text)), 1)


class FoldTest(unittest.TestCase):
    def test_folds_by_octets_without_splitting_characters(self) -> None:
        line = "DESCRIPTION:" + "Café — 東京 " * 12
        folded = md_to_ics.fold_line(line)
        for segment in folded.split("\r\n"):
            self.assertLessEqual(len(segment.encode("utf-8")), 75)
        self.assertEqual(folded.replace("\r\n ", ""), line)

    def test_short_line_unchanged(self) -> None:
        self.assertEqual(md_to_ics.fold_line("SUMMARY:x"), "SUMMARY:x")


class TimeRangeTest(unittest.TestCase):
    def test_overnight_window_rolls_to_next_day(self) -> None:
        data = convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 19:30 | 07:00 | Bedtime | Hotel | |")))
        self.assertEqual(prop(data, "DTSTART"), ["20261110T193000Z"])
        self.assertEqual(prop(data, "DTEND"), ["20261111T070000Z"])

    def test_end_before_start_typo_is_an_error(self) -> None:
        with self.assertRaises(md_to_ics.TripPlanError):
            convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 08:30 | Gardens | | |")))

    def test_blank_end_defaults_to_one_hour(self) -> None:
        data = convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 15:00 | | Museum | | |")))
        self.assertEqual(prop(data, "DTEND"), ["20261110T160000Z"])


class TimezoneTest(unittest.TestCase):
    def test_day_heading_overrides_trip_zone(self) -> None:
        data = convert_text(plan(day(
            "## Day 1 — 2026-11-10 (Tuesday) · Asia/Tokyo", "| 09:00 | 10:00 | Temple | | |",
        )))
        self.assertEqual(prop(data, "DTSTART"), ["20261110T000000Z"])

    def test_override_applies_only_to_its_own_day(self) -> None:
        data = convert_text(plan(
            day("## Day 1 — 2026-11-10 (Tuesday) · Asia/Tokyo", "| 09:00 | 10:00 | A | | |"),
            day("## Day 2 — 2026-11-11 (Wednesday)", "| 09:00 | 10:00 | B | | |"),
        ))
        self.assertEqual(prop(data, "DTSTART"), ["20261110T000000Z", "20261111T090000Z"])

    def test_cell_zone_beats_day_and_trip_zone(self) -> None:
        # Overnight transatlantic flight: 18:00 New York (23:00Z) -> 07:00 London next morning.
        data = convert_text(plan(day(
            "## Day 1 — 2026-11-10 (Tuesday)",
            "| 18:00 America/New_York | 07:00 Europe/London | Flight JFK → LHR | JFK | |",
        )))
        self.assertEqual(prop(data, "DTSTART"), ["20261110T230000Z"])
        self.assertEqual(prop(data, "DTEND"), ["20261111T070000Z"])

    def test_long_haul_can_land_two_local_days_later(self) -> None:
        # 23:00 New York on the 10th (04:00Z on the 11th) -> 05:00 Hong Kong on the 12th (21:00Z on the 11th).
        data = convert_text(plan(day(
            "## Day 1 — 2026-11-10 (Tuesday)",
            "| 23:00 America/New_York | 05:00 Asia/Hong_Kong | Flight JFK → HKG | JFK | |",
        )))
        self.assertEqual(prop(data, "DTSTART"), ["20261111T040000Z"])
        self.assertEqual(prop(data, "DTEND"), ["20261111T210000Z"])

    def test_same_zone_named_explicitly_still_catches_typos(self) -> None:
        with self.assertRaises(md_to_ics.TripPlanError):
            convert_text(plan(day(
                "## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 Europe/London | 08:30 Europe/London | A | | |",
            )))

    def test_arrival_zone_may_come_from_day_heading(self) -> None:
        data = convert_text(plan(day(
            "## Day 1 — 2026-11-10 (Tuesday) · Asia/Hong_Kong",
            "| 23:00 America/New_York | 05:00 | Flight JFK → HKG | JFK | |",
        )))
        self.assertEqual(prop(data, "DTEND"), ["20261111T210000Z"])

    def test_missing_tz_database_is_reported_as_such(self) -> None:
        with mock.patch.object(md_to_ics, "available_timezones", return_value=set()):
            with self.assertRaisesRegex(md_to_ics.TripPlanError, "timezone database"):
                md_to_ics.load_zone("Mars/Olympus", "test")

    def test_unknown_cell_zone_is_an_error(self) -> None:
        with self.assertRaises(md_to_ics.TripPlanError):
            convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 Mars/Olympus | 10:00 | A | | |")))

    def test_unknown_heading_zone_is_an_error(self) -> None:
        with self.assertRaises(md_to_ics.TripPlanError):
            convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday) · Mars/Olympus", "| 09:00 | 10:00 | A | | |")))


class TableShapeTest(unittest.TestCase):
    def test_row_without_trailing_pipe_is_kept(self) -> None:
        data = convert_text(plan(day(
            "## Day 1 — 2026-11-10 (Tuesday)",
            "| 09:00 | 10:00 | A | | |",
            "| 11:00 | 12:00 | B | | x",
            "| 13:00 | 14:00 | C | | |",
        )))
        self.assertEqual(prop(data, "SUMMARY"), ["A", "B", "C"])

    def test_rows_after_a_blank_line_are_an_error(self) -> None:
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | | |", "", "| 13:00 | 14:00 | C | | |"))
        with self.assertRaises(md_to_ics.TripPlanError):
            md_to_ics.parse_days(text)

    def test_escaped_pipe_stays_in_cell(self) -> None:
        data = convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | | a \\| b |")))
        self.assertEqual(prop(data, "DESCRIPTION"), ["a | b"])


class DstTest(unittest.TestCase):
    def test_nonexistent_local_time_is_an_error(self) -> None:
        # Europe/London skips 01:00-02:00 on 2026-03-29.
        with self.assertRaises(md_to_ics.TripPlanError):
            convert_text(plan(day("## Day 1 — 2026-03-29 (Sunday)", "| 01:30 | 02:15 | X | | |")))

    def test_overnight_across_fall_back_uses_real_elapsed_time(self) -> None:
        # Clocks go back 02:00 -> 01:00 on 2026-10-25: 19:30 BST -> 07:00 GMT.
        data = convert_text(plan(day("## Day 1 — 2026-10-24 (Saturday)", "| 19:30 | 07:00 | Bedtime | | |")))
        self.assertEqual(prop(data, "DTSTART"), ["20261024T183000Z"])
        self.assertEqual(prop(data, "DTEND"), ["20261025T070000Z"])


class MultiCityFormatTest(unittest.TestCase):
    """The multi-city trip-file shape (core/output-format-spec.md) must convert
    with the converter unchanged: it ignores the `cities` list and reads the
    city name in a day heading as plain text."""

    CITIES_FRONTMATTER = (
        '---\n'
        'trip_name: "Two Cities"\n'
        'destination: "Lilliput and Blefuscu"\n'
        'start_date: 2026-11-10\n'
        'end_date: 2026-11-12\n'
        'timezone: "Europe/London"\n'
        'naps_on_the_go: false\n'
        'cities:\n'
        '  - name: "Lilliput"\n'
        '    start_date: 2026-11-10\n'
        '    end_date: 2026-11-11\n'
        '    lodging: { name: "Hotel Lilliput Central", address: "1 Main Square" }\n'
        '    status: planned\n'
        '  - name: "Blefuscu"\n'
        '    start_date: 2026-11-12\n'
        '    end_date: 2026-11-12\n'
        '    timezone: "Europe/Paris"\n'
        '    lodging: { name: "Blefuscu Harbour Inn", address: "not booked yet" }\n'
        '    status: outlined\n'
        '---\n\n# Two Cities\n\n'
    )

    def test_city_in_heading_uses_trip_zone(self) -> None:
        data = convert_text(plan(day("## Day 1 — 2026-11-10 (Tuesday) — Lilliput", "| 09:00 | 10:00 | A | | |")))
        self.assertEqual(prop(data, "DTSTART"), ["20261110T090000Z"])

    def test_city_and_zone_suffix_in_heading(self) -> None:
        data = convert_text(plan(day("## Day 3 — 2026-11-12 (Thursday) — Blefuscu · Europe/Paris", "| 09:00 | 10:00 | A | | |")))
        self.assertEqual(prop(data, "DTSTART"), ["20261112T080000Z"])

    def test_hyphenated_city_name_is_not_mistaken_for_the_date_separator(self) -> None:
        days = md_to_ics.parse_days(plan(day("## Day 1 — 2026-11-10 (Tuesday) — Saint-Malo", "| 09:00 | 10:00 | A | | |")))
        self.assertEqual(days[0]["date"], "2026-11-10")

    def test_outlined_day_with_no_rows_converts_to_no_events(self) -> None:
        text = plan(
            day("## Day 1 — 2026-11-10 (Tuesday) — Lilliput", "| 09:00 | 10:00 | A | | |"),
            day("## Day 2 — 2026-11-11 (Wednesday) — Lilliput"),
        )
        self.assertEqual(len(md_to_ics.parse_days(text)), 2)
        self.assertEqual(prop(convert_text(text), "SUMMARY"), ["A"])

    def test_cities_frontmatter_converts_and_nested_timezone_is_ignored(self) -> None:
        text = self.CITIES_FRONTMATTER + day("## Day 1 — 2026-11-10 (Tuesday) — Lilliput", "| 09:00 | 10:00 | A | | |")
        self.assertEqual(md_to_ics.extract_timezone(text), "Europe/London")
        self.assertEqual(prop(convert_text(text), "DTSTART"), ["20261110T090000Z"])

    def test_legacy_single_lodging_frontmatter_still_converts(self) -> None:
        text = (
            '---\ntrip_name: "Old"\ntimezone: "Europe/London"\n'
            'lodging:\n  name: "Hotel"\n  address: "1 Main Square"\n---\n\n'
            + day("## Day 1 — 2026-11-10 (Tuesday)", "| 09:00 | 10:00 | A | | |")
        )
        self.assertEqual(prop(convert_text(text), "SUMMARY"), ["A"])


class DuplicateTest(unittest.TestCase):
    def test_duplicate_date_start_title_is_an_error(self) -> None:
        text = plan(day(
            "## Day 1 — 2026-11-10 (Tuesday)",
            "| 09:00 | 10:00 | Gardens | | |",
            "| 09:00 | 11:00 | Gardens | | |",
        ))
        with self.assertRaises(md_to_ics.TripPlanError):
            convert_text(text)


if __name__ == "__main__":
    unittest.main()
