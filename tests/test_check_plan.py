"""Tests for check_plan.py. Stdlib only.

Run from the repo root:
    python3 -m unittest discover -s tests -v
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "skills", "travel-planner", "scripts"))

import check_plan  # noqa: E402

SAMPLE = os.path.join(REPO, "examples", "trip-plans", "sample-trip-lilliput.md")

HEADER = "| Start | End | Title | Location | Notes |\n|---|---|---|---|---|\n"

NAP_AND_BEDTIME = """pacing_windows:
  - name: "nap"
    start: "13:00"
    end: "15:00"
    blocking: true
  - name: "afternoon"
    start: "15:00"
    end: "18:00"
  - name: "bedtime"
    start: "19:30"
    end: "07:00"
    blocking: true
"""

ONE_CITY = """cities:
  - name: "Lilliput"
    start_date: 2026-11-10
    end_date: 2026-11-11
    status: planned
"""

TWO_CITIES = """cities:
  - name: "Lilliput"
    start_date: 2026-11-10
    end_date: 2026-11-10
    status: planned
  - name: "Blefuscu"
    start_date: 2026-11-11
    end_date: 2026-11-11
    timezone: "Europe/Paris"
    status: planned
"""


def plan(*sections: str, extra_frontmatter: str = NAP_AND_BEDTIME) -> str:
    return (
        '---\ntrip_name: "T"\ntimezone: "Europe/London"\n'
        + extra_frontmatter
        + "---\n\n# T\n\n"
        + "\n".join(sections)
    )


def day(heading: str, *rows: str) -> str:
    return f"{heading}\n\n{HEADER}" + "".join(r + "\n" for r in rows)


MEALS_ROWS = (
    "| 12:00 | 12:45 | Lunch near the hotel | Main Square | Meal slot |",
    "| 17:30 | 18:30 | Dinner near the hotel | Main Square | Meal slot |",
)


def places(city: str, **groups: list[str]) -> str:
    labels = {
        "named": "Named by you",
        "picked": "Picked from suggestions",
        "chosen": "Chosen for you",
        "not_picked": "Suggested, not picked",
        "meals": "Meals",
    }
    out = [f"### {city}: places", ""]
    for key, items in groups.items():
        out.append(f"**{labels[key]}:**")
        out += [f"- {item}" for item in items]
        out.append("")
    return "\n".join(out)


def needs_attention(*items: str) -> str:
    return "## Needs Attention\n\n" + "".join(f"- {item}\n" for item in items)


def run(text: str) -> list:
    return check_plan.check(text)


def messages(findings, severity=None) -> list[str]:
    return [f.message for f in findings if severity is None or f.severity == severity]


class SampleTest(unittest.TestCase):
    def test_sample_plan_has_no_errors(self):
        with open(SAMPLE, encoding="utf-8") as f:
            findings = run(f.read())
        self.assertEqual(messages(findings, "error"), [])


class BlockingWindowTest(unittest.TestCase):
    def test_row_running_into_the_nap_window_fails_naming_row_and_window(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 14:00 | 15:30 | Museum visit | Museum | |", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Museum visit", errors[0])
        self.assertIn("nap", errors[0])

    def test_early_row_inside_the_overnight_bedtime_window_fails(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 06:00 | 06:45 | Flight out | Airport | Booked |", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("bedtime", errors[0])

    def test_flagged_overlap_is_acknowledged_and_passes(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 06:00 | 06:45 | Flight out | Airport | Booked |", *MEALS_ROWS),
                    needs_attention("Flight out leaves inside the bedtime window; it's already booked."))
        findings = run(text)
        self.assertEqual(messages(findings, "error"), [])
        self.assertEqual(len(messages(findings, "acknowledged")), 1)

    def test_the_windows_own_rows_are_not_reported(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 13:00 | 15:00 | Nap / rest at hotel | Hotel | Blocking window |",
                        "| 19:30 | 07:00 | Bedtime | Hotel | Blocking window |", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])

    def test_blank_end_counts_as_one_hour(self):
        inside = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                          "| 12:30 |  | Quick stop | Shop | |", *MEALS_ROWS))
        self.assertEqual(len(messages(run(inside), "error")), 1)
        outside = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                           "| 11:00 |  | Quick stop | Shop | |", *MEALS_ROWS))
        self.assertEqual(messages(run(outside), "error"), [])


class PlacesTest(unittest.TestCase):
    def test_picked_place_on_no_day_and_not_flagged_fails_naming_it(self):
        text = plan(places("Lilliput", picked=["Museum of Miniatures (near the gardens)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Museum of Miniatures", errors[0])

    def test_short_name_matches_as_a_phrase_in_a_row_title(self):
        text = plan(places("Lilliput", named=["Royal Gardens (attraction)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:30 | Visit Royal Gardens | Lilliput | |", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])

    def test_short_name_needs_the_whole_phrase(self):
        text = plan(places("Lilliput", named=["Royal Gardens"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:30 | Royal Library | Lilliput | |", *MEALS_ROWS))
        self.assertEqual(len(messages(run(text), "error")), 1)

    def test_long_name_matches_on_most_words(self):
        text = plan(places("Lilliput", named=["Imperial Fleet Museum"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:30 | Fleet Museum | Imperial Quay | |", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])

    def test_place_listed_under_needs_attention_passes(self):
        text = plan(places("Lilliput", named=["Emperor's Palace"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS),
                    needs_attention("Lilliput: Emperor's Palace is open only Mondays."))
        self.assertEqual(messages(run(text), "error"), [])

    def test_chosen_for_you_place_is_checked_like_a_pick(self):
        text = plan(places("Lilliput", chosen=["USS Midway Museum (downtown waterfront)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS))
        self.assertEqual(len(messages(run(text), "error")), 1)

    def test_suggested_not_picked_is_not_checked(self):
        text = plan(places("Lilliput", not_picked=["Toy Market"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])


class MealsTest(unittest.TestCase):
    def test_day_without_dinner_warns_but_does_not_fail(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 12:00 | 12:45 | Lunch near the hotel | Main Square | |"))
        findings = run(text)
        self.assertEqual(messages(findings, "error"), [])
        warnings = messages(findings, "warning")
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("Dinner", warnings[0])
        self.assertEqual(check_plan.exit_code(findings), 0)

    def test_meals_restaurant_without_a_matching_row_fails(self):
        text = plan(places("Lilliput", meals=["Day 1 lunch: Pocket Pizza (also offered: Deli)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Pocket Pizza", errors[0])

    def test_meals_restaurant_with_a_matching_row_passes(self):
        text = plan(places("Lilliput", meals=["Day 1 lunch: Pocket Pizza (chosen for you)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 12:00 | 12:45 | Lunch at Pocket Pizza | Main Square | |",
                        "| 17:30 | 18:30 | Dinner near the hotel | Main Square | |"))
        self.assertEqual(messages(run(text), "error"), [])

    def test_skipped_meal_is_ignored(self):
        text = plan(places("Lilliput", meals=["Day 1 dinner: none (you skipped this one)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])


class CitiesTest(unittest.TestCase):
    def test_one_city_plan_without_cities_or_heading_names_passes(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])

    def test_planned_city_without_places_record_fails(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday) — Lilliput", *MEALS_ROWS),
                    day("## Day 2 — 2026-11-11 (Wednesday) — Lilliput", *MEALS_ROWS),
                    extra_frontmatter=NAP_AND_BEDTIME + ONE_CITY)
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("places record", errors[0])

    def test_two_city_plan_with_matching_headings_passes(self):
        text = plan(places("Lilliput"), places("Blefuscu"),
                    day("## Day 1 — 2026-11-10 (Tuesday) — Lilliput", *MEALS_ROWS),
                    day("## Day 2 — 2026-11-11 (Wednesday) — Blefuscu · Europe/Paris", *MEALS_ROWS),
                    extra_frontmatter=NAP_AND_BEDTIME + TWO_CITIES)
        self.assertEqual(messages(run(text), "error"), [])

    def test_heading_dated_outside_its_city_range_fails(self):
        text = plan(places("Lilliput"), places("Blefuscu"),
                    day("## Day 1 — 2026-11-10 (Tuesday) — Blefuscu · Europe/Paris", *MEALS_ROWS),
                    day("## Day 2 — 2026-11-11 (Wednesday) — Blefuscu · Europe/Paris", *MEALS_ROWS),
                    extra_frontmatter=NAP_AND_BEDTIME + TWO_CITIES)
        errors = messages(run(text), "error")
        self.assertTrue(any("2026-11-10" in e and "Blefuscu" in e for e in errors), errors)
        self.assertTrue(any("Lilliput" in e and "no day" in e for e in errors), errors)


class FormatAndCliTest(unittest.TestCase):
    def test_malformed_day_table_fails_with_the_converter_message(self):
        text = plan("## Day 1 — 2026-11-10 (Tuesday)\n\n| Start | Title |\n|---|---|\n| 09:00 | X |\n")
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("table header", errors[0])

    def run_cli(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = check_plan.main(["check_plan.py", *args])
        return code, out.getvalue()

    def test_missing_file_exits_2(self):
        code, _ = self.run_cli(os.path.join(tempfile.gettempdir(), "no-such-plan-file.md"))
        self.assertEqual(code, 2)

    def test_wrong_argument_count_exits_2(self):
        code, _ = self.run_cli()
        self.assertEqual(code, 2)

    def test_plan_with_errors_exits_1_and_prints_them(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                             "| 14:00 | 15:30 | Museum visit | Museum | |", *MEALS_ROWS)))
        try:
            code, out = self.run_cli(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(code, 1)
        self.assertIn("ERROR", out)
        self.assertIn("Museum visit", out)

    def test_sample_exits_0(self):
        code, out = self.run_cli(SAMPLE)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
