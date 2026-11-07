import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class CorrectionMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "nexora-test.db"
        self.db_patch = patch.object(app, "DB_PATH", self.db_path)
        self.db_patch.start()
        with app.db():
            pass

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_unverified_fix_is_saved_as_pending(self):
        item = app.CorrectionIn(
            error_signature="Gradle resource merge failure",
            error_type="android-build",
            root_cause="Resource path was not generated before packaging.",
            resolution="Run resource generation before the APK packaging task.",
        )
        result = app.save_correction(item)
        self.assertEqual(result["validation_status"], "pending")
        self.assertFalse(result["reusable_automatically"])

    def test_fix_with_test_evidence_can_be_reused(self):
        item = app.CorrectionIn(
            error_signature="Gradle resource merge failure",
            error_type="android-build",
            root_cause="Resource path was not generated before packaging.",
            resolution="Run resource generation before the APK packaging task.",
            test_evidence="CI run 123: assembleDebug and regression tests passed.",
            tests_passed=True,
        )
        result = app.save_correction(item)
        self.assertEqual(result["validation_status"], "verified")
        self.assertTrue(result["reusable_automatically"])

    def test_search_prioritizes_verified_solutions(self):
        app.save_correction(app.CorrectionIn(
            error_signature="APK path missing",
            error_type="android-build",
            root_cause="The workflow expected the old output directory.",
            resolution="Normalize the generated APK path before artifact upload.",
            test_evidence="CI run 124 passed.",
            tests_passed=True,
        ))
        app.save_correction(app.CorrectionIn(
            error_signature="APK path missing",
            error_type="android-build",
            root_cause="The artifact upload path was not verified.",
            resolution="Inspect the build output directory before uploading.",
        ))
        result = app.search_corrections("APK path")
        self.assertEqual(len(result["matches"]), 2)
        self.assertEqual(result["matches"][0]["validation_status"], "verified")
        self.assertEqual(result["verified_count"], 1)

    def test_duplicate_solution_updates_existing_record(self):
        item = app.CorrectionIn(
            error_signature="APK path missing",
            root_cause="Build output path changed.",
            resolution="Discover and normalize the output path.",
        )
        first = app.save_correction(item)
        second = app.save_correction(item)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["id"], second["id"])


if __name__ == "__main__":
    unittest.main()
