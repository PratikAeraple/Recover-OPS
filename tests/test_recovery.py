import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "src" / "recoverops.py"
spec = importlib.util.spec_from_file_location("recoverops", MODULE)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def test_disposable_lab_restores_and_detects_corruption(self):
        result = recovery.run_demo()
        self.assertEqual(result["status"], "LAB VALIDATED")
        self.assertEqual(result["files_restored_and_verified"], 2)
        self.assertTrue(result["corruption_detected"])
        self.assertIn("no production data", result["scope"])
        self.assertEqual(result["service_drill"]["observed_states"], ["UP", "DOWN_DETECTED", "UP_RECOVERED"])

    def test_path_traversal_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                recovery.safe_destination(root, "../outside")

    def test_absolute_manifest_path_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                recovery.safe_destination(root, "/etc/passwd")

    def test_corrupt_fixture_fails_verification(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            data = root / "data.txt"
            data.write_text("expected")
            manifest = recovery.make_manifest(root)
            data.write_text("tampered")
            self.assertFalse(recovery.verify_manifest(root, manifest)["ok"])

    def test_symlink_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "outside").mkdir()
            (root / "link").symlink_to(root / "outside", target_is_directory=True)
            with self.assertRaises(ValueError):
                recovery.safe_destination(root, "link/anything")

    def test_retention_report_is_fixture_scoped_and_never_deletes(self):
        with tempfile.TemporaryDirectory(prefix="recoverops-lab-test-") as root:
            p = Path(root) / "copy"; p.mkdir(); (p / "f").write_text("fixture")
            report = recovery.retention_report(p)
            self.assertEqual(report["files_observed"], 1)
            self.assertEqual(report["deletions"], 0)
            self.assertEqual(report["status"], "LAB FIXTURE ONLY")
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError): recovery.retention_report(root)

    def test_restore_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            src = root / "source"; src.mkdir(); (src / "f").write_text("x")
            manifest = recovery.make_manifest(src)
            with self.assertRaises(ValueError):
                recovery.restore(src, src, manifest)


if __name__ == "__main__":
    unittest.main()
