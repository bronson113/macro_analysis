import json
import re
import shutil
from pathlib import Path
from typing import List, Dict

from config import OUTPUT_DIR


REPORT_PATTERN = re.compile(r"^macro_report_(\d{4}-\d{2}-\d{2})\.md$")
DIGEST_PATTERN = re.compile(r"^weekly_digest_(\d{4}-\d{2}-\d{2})\.md$")


def build_weekly_digest_manifest(output_dir: Path = OUTPUT_DIR, public_dir: Path = Path("web/public")) -> List[Dict[str, Any]]:
    """Copy weekly digest markdown files into web/public/digests and write their index."""
    output_dir = Path(output_dir)
    public_dir = Path(public_dir)
    digests_dir = public_dir / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)

    index_file = output_dir / "weekly_digests_index.json"
    index_data_by_date = {}
    if index_file.exists():
        try:
            entries = json.loads(index_file.read_text(encoding="utf-8"))
            for entry in entries:
                if isinstance(entry, dict) and "date" in entry:
                    index_data_by_date[entry["date"]] = entry
        except Exception:
            pass

    digests = []
    for digest_path in sorted(output_dir.glob("weekly_digest_*.md"), reverse=True):
        match = DIGEST_PATTERN.match(digest_path.name)
        if not match:
            continue
        date_str = match.group(1)
        dest = digests_dir / digest_path.name
        shutil.copy2(digest_path, dest)

        if date_str in index_data_by_date:
            digests.append(index_data_by_date[date_str])
        else:
            digests.append({
                "date": date_str,
                "path": f"digests/{digest_path.name}",
                "label": f"Week ending {date_str}",
            })

    latest_digest = output_dir / "latest_weekly_digest.md"
    if latest_digest.exists():
        shutil.copy2(latest_digest, public_dir / "latest_weekly_digest.md")

    index_path = digests_dir / "index.json"
    index_path.write_text(json.dumps(digests, indent=2) + "\n", encoding="utf-8")
    return digests


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
            "path": f"reports/{report_path.name}",
        })

    index_path = reports_dir / "index.json"
    index_path.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")

    # Also build weekly digest manifest if any digests exist
    build_weekly_digest_manifest(output_dir=output_dir, public_dir=public_dir)

    return reports


if __name__ == "__main__":
    build_report_manifest()

