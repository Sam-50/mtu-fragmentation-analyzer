"""Report generation utilities."""

from __future__ import annotations

import csv
from pathlib import Path

from app.config import settings


def build_run_report(run: dict[str, object]) -> dict[str, object]:
    """Return a JSON-serializable report object."""

    return run


def export_run_csv(run: dict[str, object], run_id: int) -> Path:
    """Export probe data for a run to CSV."""

    output_path = settings.export_path / f"run_{run_id}_probes.csv"
    fieldnames = [
        "payload_size",
        "mtu_estimate",
        "success",
        "rtt_ms",
        "error_type",
        "detail",
        "method",
        "sequence_no",
        "created_at",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for probe in run["probes"]:
            writer.writerow({name: probe.get(name) for name in fieldnames})
    return output_path


def build_human_summary(run: dict[str, object]) -> str:
    """Create a concise, demo-friendly text summary."""

    summary = run["summary"]
    recommendations = run["recommendations"]
    lines = [
        f"Target: {run['target']} ({run.get('target_ip') or 'unresolved'})",
        f"Run status: {run['status']}",
        f"Inferred path MTU: {summary.get('inferred_path_mtu') or 'not determined'}",
        f"Recommended MTU: {summary.get('recommended_mtu') or 'not available'}",
        f"Recommended TCP MSS: {summary.get('recommended_mss') or 'not available'}",
        "Key recommendations:",
    ]
    for item in recommendations[:5]:
        suffix = f" [{item['value']}]" if item.get("value") else ""
        lines.append(f"- {item['title']}{suffix}: {item['detail']}")
    return "\n".join(lines)
