import unittest
import tempfile
from pathlib import Path

import pandas as pd

from compact_observations import compact_repeated_fred_vintages, compact_file
from storage import atomic_write_csv


class CompactObservationTests(unittest.TestCase):
    def test_keeps_first_vintage_of_each_value_run_and_all_other_rows(self):
        rows = [
            ("2026-01-01", 1.0, "2026-01-02", "https://fred.stlouisfed.org/series/X"),
            ("2026-01-01", 1.0, "2026-01-03", "https://fred.stlouisfed.org/series/X"),
            ("2026-01-01", 2.0, "2026-01-04", "https://fred.stlouisfed.org/series/X"),
            ("2026-01-01", 1.0, "2026-01-05", "https://fred.stlouisfed.org/series/X"),
            ("2026-01-01", 1.0, "2026-01-06", "https://other.test/data"),
        ]
        frame = pd.DataFrame(rows, columns=["date", "value", "vintage_date", "source_url"])
        frame["indicator_key"] = "cpi"
        frame["unit"] = "index"
        result = compact_repeated_fred_vintages(frame)
        self.assertEqual(result["vintage_date"].tolist(), [
            "2026-01-02", "2026-01-04", "2026-01-05", "2026-01-06"
        ])

    def test_compressed_csv_can_be_compacted_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "observations.csv.gz"
            frame = pd.DataFrame([
                {"indicator_key": "cpi", "date": "2026-01-01", "value": 1, "vintage_date": day,
                 "source_url": "https://fred.stlouisfed.org/series/X"}
                for day in ("2026-01-02", "2026-01-03")
            ])
            atomic_write_csv(path, frame)
            self.assertEqual(compact_file(path), (2, 1))
            self.assertEqual(len(pd.read_csv(path)), 1)


if __name__ == "__main__":
    unittest.main()
