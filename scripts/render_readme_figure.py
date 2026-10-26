"""Render the README results figure from the tracked 2022 batch validation reports.

Usage:
    python scripts/render_readme_figure.py

Reads:
    reports/bordeaux-2022-batch-validation.json
    reports/languedoc-2022-batch-validation.json
Writes:
    docs/images/drought-2022-results.svg

Standard library only. Every plotted value comes from the report files.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
REPORTS = [
    ROOT / "reports" / "bordeaux-2022-batch-validation.json",
    ROOT / "reports" / "languedoc-2022-batch-validation.json",
]
OUTPUT = ROOT / "docs" / "images" / "drought-2022-results.svg"

ACCEPTED_EXAMPLE = "FR_RPG23_PIC_SAINT_LOUP_02"
AMBIGUOUS_EXAMPLE = "FR_RPG23_MINERVOIS_02"

NDMI_TRIGGER = 0.15
PERCENTILE_LIMIT = 0.25
WINDOW = (date(2022, 6, 28), date(2022, 9, 2))

WIDTH, HEIGHT = 960, 540
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e8e7e3"
COLORS = {"accepted": "#2a78d6", "ambiguous": "#eb6834"}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

DISPLAY_NAMES = {
    "FR_RPG23_BEZIERS_01": "Béziers 01",
    "FR_RPG23_BORDEAUX_RIGHT_BANK_01": "Bordeaux Right Bank 01",
    "FR_RPG23_BORDEAUX_RIGHT_BANK_02": "Bordeaux Right Bank 02",
    "FR_RPG23_MEDOC_01": "Médoc 01",
    "FR_RPG23_MEDOC_02": "Médoc 02",
    "FR_RPG23_MINERVOIS_01": "Minervois 01",
    "FR_RPG23_MINERVOIS_02": "Minervois 02",
    "FR_RPG23_PIC_SAINT_LOUP_01": "Pic Saint-Loup 01",
    "FR_RPG23_PIC_SAINT_LOUP_02": "Pic Saint-Loup 02",
    "FR_RPG23_SAUTERNES_01": "Sauternes 01",
}


def load_aois() -> dict[str, dict]:
    aois: dict[str, dict] = {}
    for path in REPORTS:
        report = json.loads(path.read_text())
        for aoi in report["aois"]:
            aois[aoi["aoi_id"]] = aoi["validation"]
    return aois


def text(x: float, y: float, value: str, *, size: int = 12, color: str = INK_2,
         weight: int = 400, anchor: str = "start", halo: bool = False) -> str:
    halo_attr = (
        f' stroke="{SURFACE}" stroke-width="4" stroke-linejoin="round" paint-order="stroke"'
        if halo
        else ""
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}" text-anchor="{anchor}"{halo_attr}>{escape(value)}</text>'
    )


def line(x1: float, y1: float, x2: float, y2: float, *, color: str = GRID,
         width: float = 1, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{width}"{dash_attr}/>'
    )


def marker(x: float, y: float, color: str, *, hollow: bool) -> str:
    if hollow:
        return (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{SURFACE}" '
            f'stroke="{color}" stroke-width="2"/>'
        )
    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}" '
        f'stroke="{SURFACE}" stroke-width="2"/>'
    )


class Axis:
    def __init__(self, lo: float, hi: float, px_lo: float, px_hi: float) -> None:
        self.lo, self.hi, self.px_lo, self.px_hi = lo, hi, px_lo, px_hi

    def __call__(self, value: float) -> float:
        frac = (value - self.lo) / (self.hi - self.lo)
        return self.px_lo + frac * (self.px_hi - self.px_lo)


def day_axis(px_lo: float, px_hi: float) -> Axis:
    return Axis(WINDOW[0].toordinal(), WINDOW[1].toordinal(), px_lo, px_hi)


def series_panel(
    out: list[str],
    *,
    aois: dict[str, dict],
    key: str,
    y_axis: Axis,
    x_axis: Axis,
    ticks: list[tuple[float, str]],
    rule: tuple[float, str],
    end_labels: bool,
) -> None:
    for value, label in ticks:
        out.append(line(x_axis.px_lo, y_axis(value), x_axis.px_hi, y_axis(value)))
        out.append(text(x_axis.px_lo - 8, y_axis(value) + 4, label, size=11,
                        color=MUTED, anchor="end"))
    rule_value, rule_label = rule
    out.append(line(x_axis.px_lo, y_axis(rule_value), x_axis.px_hi, y_axis(rule_value),
                    color=INK_2, width=1.2, dash="5 4"))
    out.append(text(x_axis.px_lo - 8, y_axis(rule_value) + 4, rule_label, size=11,
                    color=INK, weight=600, anchor="end"))

    for aoi_id in (AMBIGUOUS_EXAMPLE, ACCEPTED_EXAMPLE):
        validation = aois[aoi_id]
        color = COLORS[validation["validation_assessment"]["classification"]]
        points = []
        for period in validation["ndmi_periods"]:
            value = period.get(key)
            if value is None:
                continue
            x = x_axis(date.fromisoformat(period["date"]).toordinal())
            points.append((x, y_axis(value), bool(period["quality_flags"])))
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        out.append(
            f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for x, y, flagged in points:
            out.append(marker(x, y, color, hollow=flagged))
        if end_labels:
            x, y, _ = points[-1]
            name = DISPLAY_NAMES[aoi_id]
            label = validation["validation_assessment"]["classification"]
            out.append(text(x + 12, y + 15, name, size=12, color=INK, weight=600, halo=True))
            out.append(text(x + 12, y + 30, label, size=11, color=INK_2, halo=True))


def render() -> str:
    aois = load_aois()
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}" role="img" '
        f'aria-label="OrbitRisk 2022 drought validation results on 10 vineyard parcels">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="8" fill="{SURFACE}"/>',
        text(32, 38, "2022 drought check on 10 French vineyard parcels", size=19,
             color=INK, weight=700),
        text(32, 60, "Sentinel-2 NDMI (canopy water index), 10-day composites, "
             "July-August 2022", size=13),
    ]

    # Legend, one row under the subtitle.
    legend_y = 86
    lx = 32
    for label, color, hollow in (
        ("accepted", COLORS["accepted"], False),
        ("ambiguous (sent to review)", COLORS["ambiguous"], False),
        ("period with a cloud or pixel-quality warning", INK_2, True),
    ):
        out.append(marker(lx + 5, legend_y - 4, color, hollow=hollow))
        out.append(text(lx + 16, legend_y, label, size=12))
        lx += 16 + len(label) * 6.6 + 22

    # Panel A: two parcels, two measures, shared date axis.
    x_axis = day_axis(84, 404)
    out.append(text(32, 126, "Same signal, different verdict", size=14, color=INK, weight=700))
    out.append(text(32, 146, "Smoothed NDMI: both parcels sit below the 0.15 trigger (dashed)",
                    size=12))
    series_panel(
        out,
        aois=aois,
        key="ndmi_ema",
        y_axis=Axis(-0.06, 0.2, 254, 160),
        x_axis=x_axis,
        ticks=[(-0.05, "-0.05"), (0.05, "0.05")],
        rule=(NDMI_TRIGGER, "0.15"),
        end_labels=False,
    )
    out.append(text(32, 290, "Seasonal percentile vs the same dates in 2019-2021 "
                    "(accepted only if <= 0.25)", size=12))
    out.append(text(32, 306, "Only Pic Saint-Loup 02 is unusually dry for its own history",
                    size=12, color=MUTED))
    percentile_axis = Axis(0, 1, 450, 322)
    series_panel(
        out,
        aois=aois,
        key="ndmi_baseline_percentile",
        y_axis=percentile_axis,
        x_axis=x_axis,
        ticks=[(0, "0"), (0.5, "0.5"), (1, "1")],
        rule=(PERCENTILE_LIMIT, "0.25"),
        end_labels=True,
    )
    for day, label in ((date(2022, 7, 1), "1 Jul"), (date(2022, 7, 15), "15 Jul"),
                       (date(2022, 8, 1), "1 Aug"), (date(2022, 8, 15), "15 Aug"),
                       (date(2022, 8, 31), "31 Aug")):
        out.append(text(x_axis(day.toordinal()), 470, label, size=11, color=MUTED,
                        anchor="middle"))

    # Panel B: all ten parcels, lowest seasonal percentile in the target window.
    px_axis = Axis(0, 1, 742, 922)
    out.append(text(584, 126, "All 10 parcels", size=14, color=INK, weight=700))
    out.append(text(584, 146, "Lowest seasonal percentile in July-August 2022", size=12))
    rows = sorted(
        aois.items(),
        key=lambda item: (
            item[1]["validation_assessment"]["classification"] != "accepted",
            item[1]["validation_assessment"]["inputs"]["min_baseline_percentile"],
            item[0],
        ),
    )
    top, step = 176, 29
    bottom = top + step * (len(rows) - 1)
    for value in (0, 0.5, 1):
        out.append(line(px_axis(value), top - 14, px_axis(value), bottom + 12))
        out.append(text(px_axis(value), bottom + 28, f"{value:g}", size=11, color=MUTED,
                        anchor="middle"))
    out.append(line(px_axis(PERCENTILE_LIMIT), top - 14, px_axis(PERCENTILE_LIMIT), bottom + 12,
                    color=INK_2, width=1.2, dash="5 4"))
    out.append(text(px_axis(PERCENTILE_LIMIT), bottom + 28, "0.25", size=11, color=INK_2,
                    anchor="middle"))
    for index, (aoi_id, validation) in enumerate(rows):
        assessment = validation["validation_assessment"]
        y = top + index * step
        value = assessment["inputs"]["min_baseline_percentile"]
        needs_review = "quality_warnings_require_review" in assessment["reasons"]
        out.append(line(px_axis(0), y, px_axis(1), y, color=GRID))
        out.append(text(730, y + 4, DISPLAY_NAMES[aoi_id], size=12, color=INK, anchor="end"))
        out.append(marker(px_axis(value), y, COLORS[assessment["classification"]],
                          hollow=needs_review))

    counts = {"accepted": 0, "ambiguous": 0, "rejected": 0}
    for validation in aois.values():
        counts[validation["validation_assessment"]["classification"]] += 1
    out.append(text(
        584, 494,
        f"{counts['accepted']} accepted, {counts['ambiguous']} ambiguous, "
        f"{counts['rejected']} rejected",
        size=12, color=INK, weight=600,
    ))

    out.append(line(32, 508, WIDTH - 32, 508))
    out.append(text(
        32, 528,
        "Source: reports/bordeaux-2022-batch-validation.json, "
        "reports/languedoc-2022-batch-validation.json. "
        "Rebuild with scripts/render_readme_figure.py.",
        size=11, color=MUTED,
    ))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render())
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
