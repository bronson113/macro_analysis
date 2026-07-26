import json
import re
import shutil
from pathlib import Path
from typing import List, Dict

from config import OUTPUT_DIR


REPORT_PATTERN = re.compile(r"^macro_report_(\d{4}-\d{2}-\d{2})\.md$")


def build_report_manifest(output_dir: Path = OUTPUT_DIR, public_dir: Path = Path("web/public")) -> List[Dict[str, str]]:
    """Copy dated markdown reports into web/public/reports and write their index."""
    output_dir = Path(output_dir)
    public_dir = Path(public_dir)
    reports_dir = public_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    reports = []
    for report_path in sorted(output_dir.glob("macro_report_*.md"), reverse=True):
        match = REPORT_PATTERN.match(report_path.name)
        if not match:
            continue

        destination = reports_dir / report_path.name
        shutil.copy2(report_path, destination)
        reports.append({
            "date": match.group(1),
            "path": f"/reports/{report_path.name}",
        })

    index_path = reports_dir / "index.json"
    index_path.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    return reports


if __name__ == "__main__":
    build_report_manifest()
