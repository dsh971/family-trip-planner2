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

sys.path.insert(0, HERE)
from test_md_to_ics import day  # noqa: E402

SAMPLE = os.path.join(REPO, "examples", "trip-plans", "sample-trip-lilliput.md")

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

    def test_row_at_the_windows_times_but_not_named_for_it_fails(self):
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 13:00 | 15:00 | Royal Library | Library | |", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("nap", errors[0])

    def test_underscored_window_name_matches_its_own_row(self):
        quiet = 'pacing_windows:\n  - name: "quiet_time"\n    start: "13:00"\n    end: "14:00"\n    blocking: true\n'
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 13:00 | 14:00 | Quiet time at the hotel | Hotel | |", *MEALS_ROWS), extra_frontmatter=quiet)
        self.assertEqual(messages(run(text), "error"), [])

    def test_cell_zone_is_read_on_the_days_clock(self):
        westbound = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                             "| 09:00 Europe/Paris | 08:15 | Flight in | Airport | Lands 08:15 London |", *MEALS_ROWS))
        self.assertEqual(messages(run(westbound), "error"), [])
        early = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                         "| 07:30 Europe/Paris | 08:30 | Flight in | Airport | Leaves 06:30 London |", *MEALS_ROWS))
        errors = messages(run(early), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("bedtime", errors[0])

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

    def test_long_name_needs_the_whole_name(self):
        text = plan(places("Lilliput", named=["Imperial Fleet Museum"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:30 | Fleet Museum | Imperial Quay | |", *MEALS_ROWS))
        self.assertEqual(len(messages(run(text), "error")), 1)

    def test_leading_article_and_accents_still_match(self):
        text = plan(places("Lilliput", named=["The Thimble Café"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:30 | Coffee at Thimble Café | Main Square | |", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])

    def test_travel_row_to_a_place_is_not_a_visit(self):
        text = plan(places("Lilliput", named=["Mildendo Sea Cliffs (attraction)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 09:45 | Travel to the Mildendo Sea Cliffs | Hotel | |",
                        "| 11:15 | 12:00 | Return from Mildendo Sea Cliffs | Mildendo Sea Cliffs | |", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Mildendo Sea Cliffs", errors[0])

    def test_name_inside_a_longer_recorded_name_is_not_a_visit(self):
        text = plan(places("Blefuscu", named=["Old Harbour (attraction)"], picked=["Old Harbour Bakery"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:00 | Old Harbour Bakery | Old Harbour, Blefuscu | |", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("'Old Harbour'", errors[0])

    def test_neighborhood_is_visited_by_a_row_located_in_it(self):
        text = plan(places("Blefuscu", named=["Old Harbour (neighborhood)"], picked=["Little Lighthouse Park"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:00 | Little Lighthouse Park | Old Harbour, Blefuscu | |", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])

    def test_attraction_is_not_visited_by_a_row_located_at_it(self):
        text = plan(places("Lilliput", named=["Royal Gardens (attraction)"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:00 | Coffee stop | Royal Gardens gate | |", *MEALS_ROWS))
        self.assertEqual(len(messages(run(text), "error")), 1)

    def test_possessive_still_names_the_place(self):
        text = plan(places("Lilliput", picked=["Taverna Minor"], meals=["Day 1 lunch: Taverna Minor"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 12:00 | 12:45 | Lunch at Taverna Minor's terrace | Main Square | |",
                        "| 17:30 | 18:30 | Dinner near the hotel | Main Square | |"))
        self.assertEqual(messages(run(text), "error"), [])

    def test_accents_and_ampersands_are_spelling_not_names(self):
        text = plan(places("Lilliput", named=["The Thimble Café", "Main Square Deli & Bar"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:00 | Coffee at Thimble Cafe | Main Square | |",
                        "| 10:30 | 11:00 | Main Square Deli and Bar | Main Square | |", *MEALS_ROWS))
        self.assertEqual(messages(run(text), "error"), [])

    def test_passing_mention_under_needs_attention_does_not_acknowledge(self):
        text = plan(places("Lilliput", named=["Royal Gardens"], picked=["Taverna Minor"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 12:00 | 12:45 | Lunch at Taverna Minor | Main Square | |",
                        "| 17:30 | 18:30 | Dinner near the hotel | Main Square | |"),
                    needs_attention("Taverna Minor (by the Royal Gardens): step-free entrance unconfirmed."))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Royal Gardens", errors[0])

    def test_bold_city_prefixed_attention_item_acknowledges(self):
        text = plan(places("Blefuscu", named=["Emperor's Palace"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS),
                    needs_attention("**Blefuscu: Emperor's Palace** (named by you) is open only Mondays."))
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

    def test_restaurant_sharing_most_words_with_the_row_fails(self):
        text = plan(places("Lilliput", meals=["Day 1 dinner: Harbour Chowder House"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 12:00 | 12:45 | Lunch near the hotel | Main Square | |",
                        "| 17:30 | 18:30 | Dinner at Harbour Fish House | Old Harbour | |"))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Harbour Chowder House", errors[0])

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

    def test_city_names_compare_without_case(self):
        text = plan(places("lilliput"), places("Blefuscu"),
                    day("## Day 1 — 2026-11-10 (Tuesday) — lilliput", *MEALS_ROWS),
                    day("## Day 2 — 2026-11-11 (Wednesday) — BLEFUSCU · Europe/Paris", *MEALS_ROWS),
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


RETURN_TRIP = """cities:
  - name: "Lilliput"
    start_date: 2026-11-10
    end_date: 2026-11-10
    status: planned
  - name: "Blefuscu"
    start_date: 2026-11-11
    end_date: 2026-11-11
    timezone: "Europe/Paris"
    status: planned
  - name: "Lilliput"
    start_date: 2026-11-12
    end_date: 2026-11-12
    status: planned
"""


class MultiCityEdgeTest(unittest.TestCase):
    def test_return_visit_to_an_earlier_city_passes(self):
        text = plan(places("Lilliput", named=["Royal Gardens"]), places("Blefuscu"),
                    places("Lilliput", named=["Sea Cliffs"]),
                    day("## Day 1 — 2026-11-10 (Tuesday) — Lilliput",
                        "| 09:00 | 10:00 | Royal Gardens | Lilliput | |", *MEALS_ROWS),
                    day("## Day 2 — 2026-11-11 (Wednesday) — Blefuscu · Europe/Paris", *MEALS_ROWS),
                    day("## Day 3 — 2026-11-12 (Thursday) — Lilliput",
                        "| 09:00 | 10:00 | Sea Cliffs | Lilliput | |", *MEALS_ROWS),
                    extra_frontmatter=NAP_AND_BEDTIME + RETURN_TRIP)
        self.assertEqual(messages(run(text), "error"), [])

    def test_repeated_places_records_for_one_city_are_both_checked(self):
        text = plan(places("Lilliput", named=["Royal Gardens"]), places("Lilliput", named=["Sea Cliffs"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 09:00 | 10:00 | Royal Gardens | Lilliput | |", *MEALS_ROWS))
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Sea Cliffs", errors[0])

    def test_heading_naming_a_city_not_in_the_list_fails(self):
        text = plan(places("Lilliput"), places("Blefuscu"),
                    day("## Day 1 — 2026-11-10 (Tuesday) — Mildendo", *MEALS_ROWS),
                    day("## Day 2 — 2026-11-11 (Wednesday) — Blefuscu · Europe/Paris", *MEALS_ROWS),
                    extra_frontmatter=NAP_AND_BEDTIME + TWO_CITIES)
        errors = messages(run(text), "error")
        self.assertTrue(any("isn't in `cities`" in e for e in errors), errors)

    def test_city_with_invalid_dates_fails(self):
        broken = TWO_CITIES.replace("end_date: 2026-11-11", "end_date: not-a-date")
        text = plan(places("Lilliput"), places("Blefuscu"),
                    day("## Day 1 — 2026-11-10 (Tuesday) — Lilliput", *MEALS_ROWS),
                    day("## Day 2 — 2026-11-11 (Wednesday) — Blefuscu · Europe/Paris", *MEALS_ROWS),
                    extra_frontmatter=NAP_AND_BEDTIME + broken)
        errors = messages(run(text), "error")
        self.assertTrue(any("no valid start_date" in e for e in errors), errors)

    def test_meals_restaurant_named_under_needs_attention_passes(self):
        text = plan(places("Lilliput", meals=["Day 1 dinner: Harbour Chowder House"]),
                    day("## Day 1 — 2026-11-10 (Tuesday)", *MEALS_ROWS),
                    needs_attention("Harbour Chowder House is closed for a private event that night."))
        self.assertEqual(messages(run(text), "error"), [])


class FrontmatterListTest(unittest.TestCase):
    def test_quoted_value_with_a_comment_drops_quotes_and_comment(self):
        items = check_plan.frontmatter_list('w:\n  - name: "bed"   # night\n    end: "07:00"   # next morning\n', "w")
        self.assertEqual(items, [{"name": "bed", "end": "07:00"}])

    def test_list_indented_four_spaces_is_read(self):
        items = check_plan.frontmatter_list('w:\n    - name: "nap"\n      start: "13:00"\n', "w")
        self.assertEqual(items, [{"name": "nap", "start": "13:00"}])

    def test_unindented_list_is_read(self):
        items = check_plan.frontmatter_list('w:\n- name: "nap"\n  start: "13:00"\nother: 1\n', "w")
        self.assertEqual(items, [{"name": "nap", "start": "13:00"}])

    def test_one_level_of_nesting_is_kept(self):
        items = check_plan.frontmatter_list('c:\n  - name: "L"\n    lodging:\n      name: "Inn"\n    status: planned\n', "c")
        self.assertEqual(items, [{"name": "L", "lodging": {"name": "Inn"}, "status": "planned"}])

    def test_commented_window_time_still_blocks(self):
        windows = NAP_AND_BEDTIME.replace('end: "07:00"', 'end: "07:00"   # next morning')
        text = plan(day("## Day 1 — 2026-11-10 (Tuesday)",
                        "| 12:00 | 12:45 | Lunch near the hotel | Main Square | |",
                        "| 18:30 | 20:30 | Dinner late | Main Square | |"), extra_frontmatter=windows)
        errors = messages(run(text), "error")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("bedtime", errors[0])


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
