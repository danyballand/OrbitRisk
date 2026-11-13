"""Offline replay of the tracked 2022 drought validation results.

Reads the batch validation JSON files committed under ``reports/`` and renders a
per-parcel summary. No network access and no satellite downloads are needed, so
anyone who clones the repository can see what the engine produced.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_REPORTS = (
    Path("reports/bordeaux-2022-batch-validation.json"),
    Path("reports/languedoc-2022-batch-validation.json"),
)

VERDICT_ORDER = ("accepted", "ambiguous", "rejected")


def load_replay_rows(report_paths: list[Path]) -> list[dict[str, Any]]:
    """Flatten tracked batch validation reports into one row per parcel."""
    rows: list[dict[str, Any]] = []
    for path in report_paths:
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Run this command from the repository root.")
        document = json.loads(path.read_text(encoding="utf-8"))
        for aoi in document.get("aois", []):
            assessment = aoi.get("validation", {}).get("validation_assessment", {})
            inputs = assessment.get("inputs", {})
            rows.append(
                {
                    "aoi_id": aoi.get("aoi_id"),
                    "region": aoi.get("region"),
                    "classification": assessment.get("classification", "unknown"),
                    "trigger_candidate": inputs.get("trigger_candidate"),
                    "min_baseline_percentile": inputs.get("min_baseline_percentile"),
                    "min_valid_pixel_count": inputs.get("min_valid_pixel_count"),
                    "reasons": list(assessment.get("reasons", [])),
                }
            )
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["classification"] for row in rows)
    summary = {"analysed": len(rows)}
    for verdict in VERDICT_ORDER:
        summary[verdict] = counts.get(verdict, 0)
    return summary


def _fmt_percentile(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.2f}"


def render_replay_table(rows: list[dict[str, Any]]) -> str:
    """Render rows as a plain-text table followed by verdict counts."""
    headers = ("Parcel", "Region", "Verdict", "Min pct", "Min px", "Reasons")
    body = [
        (
            str(row["aoi_id"]).removeprefix("FR_RPG23_"),
            str(row["region"]),
            str(row["classification"]),
            _fmt_percentile(row["min_baseline_percentile"]),
            str(row["min_valid_pixel_count"]),
            ", ".join(row["reasons"]) or "-",
        )
        for row in rows
    ]
    widths = [
        max(len(headers[i]), *(len(line[i]) for line in body)) if body else len(headers[i])
        for i in range(len(headers))
    ]

    def fmt(cells: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    lines = [fmt(headers), fmt(tuple("-" * w for w in widths))]
    lines.extend(fmt(line) for line in body)
    summary = summarize_rows(rows)
    lines.append("")
    lines.append(
        f"{summary['analysed']} parcels analysed: "
        + ", ".join(f"{summary[v]} {v}" for v in VERDICT_ORDER)
    )
    lines.append(
        "Min pct = lowest seasonal percentile vs the parcel's own 2019-2021 history "
        "(low means unusually dry)."
    )
    return "\n".join(lines)
