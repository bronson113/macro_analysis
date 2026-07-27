import json
import tempfile
import unittest
from pathlib import Path

from report_manifest import build_report_manifest


class TestReportManifest(unittest.TestCase):
    def test_build_report_manifest_copies_reports_and_writes_newest_first_index(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_dir = root / "output"
            public_dir = root / "web" / "public"
            output_dir.mkdir(parents=True)
            public_dir.mkdir(parents=True)

            (output_dir / "macro_report_2026-07-22.md").write_text("older", encoding="utf-8")
            (output_dir / "macro_report_2026-07-23.md").write_text("newer", encoding="utf-8")
            (output_dir / "latest_report.md").write_text("latest alias", encoding="utf-8")

            manifest = build_report_manifest(output_dir=output_dir, public_dir=public_dir)

            self.assertEqual(
                manifest,
                [
                    {"date": "2026-07-23", "path": "reports/macro_report_2026-07-23.md"},
                    {"date": "2026-07-22", "path": "reports/macro_report_2026-07-22.md"},
                ],
            )
            self.assertEqual((public_dir / "reports" / "macro_report_2026-07-23.md").read_text(encoding="utf-8"), "newer")
            self.assertEqual((public_dir / "reports" / "macro_report_2026-07-22.md").read_text(encoding="utf-8"), "older")

            index = json.loads((public_dir / "reports" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index, manifest)


if __name__ == "__main__":
    unittest.main()
