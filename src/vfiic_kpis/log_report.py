from __future__ import annotations

import json
from pathlib import Path

from vfiic_kpis.manifest import ReconciliationReport
from vfiic_kpis.user_messages import (
    format_reconciliation_summary,
    reconciliation_report_to_user_dict,
)


def write_json_sidecar(report: ReconciliationReport, output_path: Path) -> None:
    """Write the reconciliation summary as indented UTF-8 JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(reconciliation_report_to_user_dict(report), handle, ensure_ascii=False, indent=2)


def print_and_persist(report: ReconciliationReport, json_path: Path) -> None:
    print(format_reconciliation_summary(report, detail_json_path=json_path.resolve()))
    write_json_sidecar(report, json_path)
