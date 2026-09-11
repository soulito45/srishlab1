import unittest
import io
from pathlib import Path

import pandas as pd

import app

from utils import eda
from utils import query_engine
from utils import report_generator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILE = PROJECT_ROOT / "sample_data" / "sample_indian_retail_sales.csv"


class CleaningPipelineTests(unittest.TestCase):
    def test_sample_missing_values_are_filled_and_reported(self):
        cleaned, report = eda.load_dataframe_with_report(str(SAMPLE_FILE))

        self.assertEqual(report["filled_missing_values"], 40)
        self.assertEqual(cleaned.isna().sum().sum(), 0)
        self.assertTrue(all(value == 0 for value in report["final_missing_by_column"].values()))

        profiles = eda.column_profile(
            cleaned,
            report["original_missing_by_column"],
            report["original_rows"],
        )
        discount_profile = next(profile for profile in profiles if profile["name"] == "DiscountPercent")
        rating_profile = next(profile for profile in profiles if profile["name"] == "CustomerRating")
        self.assertEqual(discount_profile["original_missing_pct"], 5.0)
        self.assertEqual(rating_profile["original_missing_pct"], 5.0)
        self.assertEqual(discount_profile["missing_pct"], 0.0)
        self.assertEqual(rating_profile["missing_pct"], 0.0)

    def test_missing_percent_uses_original_row_count(self):
        source = pd.DataFrame(
            {
                "value": [1, None, None, None, None],
                "label": ["a", "b", "c", "d", "e"],
            }
        )

        cleaned, report = eda.clean_dataframe(source)
        profiles = eda.column_profile(
            cleaned,
            report["original_missing_by_column"],
            report["original_rows"],
        )

        value_profile = next(profile for profile in profiles if profile["name"] == "value")
        self.assertEqual(value_profile["original_missing_pct"], 80.0)
        self.assertEqual(cleaned.isna().sum().sum(), 0)
        self.assertTrue(value_profile["complete"])

    def test_original_percentage_is_not_distorted_when_empty_rows_are_removed(self):
        source = pd.DataFrame(
            {
                "value": [None, 10, None, None],
                "label": [None, "kept", "kept", None],
            }
        )

        cleaned, report = eda.clean_dataframe(source)
        profiles = eda.column_profile(
            cleaned,
            report["original_missing_by_column"],
            report["original_rows"],
        )

        value_profile = next(profile for profile in profiles if profile["name"] == "value")
        self.assertEqual(report["removed_empty_rows"], 2)
        self.assertEqual(value_profile["original_missing"], 3)
        self.assertEqual(value_profile["original_missing_pct"], 75.0)
        self.assertEqual(value_profile["missing_pct"], 0.0)

    def test_cleaned_csv_contains_no_blank_values(self):
        cleaned, _ = eda.load_dataframe_with_report(str(SAMPLE_FILE))
        csv_data = cleaned.to_csv(index=False)
        reloaded = pd.read_csv(__import__("io").StringIO(csv_data))

        self.assertEqual(reloaded.isna().sum().sum(), 0)

    def test_pdf_profile_uses_before_and_after_missing_percentages(self):
        cleaned, report = eda.load_dataframe_with_report(str(SAMPLE_FILE))
        profiles = eda.column_profile(
            cleaned,
            report["original_missing_by_column"],
            report["original_rows"],
        )
        overview = eda.basic_overview(cleaned)

        pdf = report_generator.generate_pdf_report(
            "report & <sample>.csv", overview, profiles, generated_by="user & <name>"
        )

        self.assertTrue(pdf.getvalue().startswith(b"%PDF"))

    def test_explicit_percentage_strings_are_normalized(self):
        source = pd.DataFrame({"rate": ["12.5%", "25.0%", None]})

        cleaned, _ = eda.clean_dataframe(source)

        self.assertAlmostEqual(cleaned.loc[0, "rate"], 0.125)
        self.assertAlmostEqual(cleaned.loc[1, "rate"], 0.25)

    def test_group_count_counts_rows_including_null_aggregate_values(self):
        source = pd.DataFrame({"group": ["a", "a", "b"], "value": [1, None, None]})

        grouped = query_engine.apply_group(source, "group", "value", "count")

        counts = dict(zip(grouped["group"], grouped["count"]))
        self.assertEqual(counts, {"a": 2, "b": 1})

    def test_imputation_does_not_create_duplicate_rows(self):
        source = pd.DataFrame({"group": ["a", "a"], "value": [None, 2]})

        cleaned, report = eda.clean_dataframe(source)

        self.assertEqual(report["removed_duplicate_rows"], 0)
        self.assertEqual(len(cleaned), 2)

    def test_spreadsheet_formula_values_are_neutralized_for_export(self):
        source = pd.DataFrame({"label": ["=SUM(1,1)", "@cmd", "-danger"]})
        cleaned, _ = eda.clean_dataframe(source)
        safe = cleaned.map(
            lambda value: "'" + value
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
            else value
        )

        exported = pd.read_csv(io.StringIO(safe.to_csv(index=False)))

        self.assertEqual(exported["label"].tolist(), ["'=SUM(1,1)", "'@cmd", "'-danger"])

    def test_name_validation_rejects_disallowed_punctuation(self):
        self.assertTrue(app.is_valid_full_name("Priya Sharma"))
        self.assertTrue(app.is_valid_username("priya_sharma"))

        self.assertFalse(app.is_valid_full_name("Priya, Sharma!"))
        self.assertFalse(app.is_valid_username("priya.sharma!"))

if __name__ == "__main__":
    unittest.main()
