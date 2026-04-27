import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Literal

ChartMetric = Literal["ndmi", "valid_pixels", "cloud_pct"]

_WIDTH = 900
_HEIGHT = 420
_LEFT = 72
_RIGHT = 28
_TOP = 52
_BOTTOM = 82
_PLOT_WIDTH = _WIDTH - _LEFT - _RIGHT
_PLOT_HEIGHT = _HEIGHT - _TOP - _BOTTOM
_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class ChartSeries:
    label: str
    values: list[float | None]
    color: str
    stroke_dasharray: str | None = None


def write_mask_benchmark_charts(
    summary: dict[str, Any],
    output_dir: Path,
    *,
    aoi_id: str | None = None,
) -> list[dict[str, str]]:
    """Write per-variant SVG chart artifacts for one mask benchmark summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_aoi_id = aoi_id or str(summary.get("region", "benchmark"))
    artifacts: list[dict[str, str]] = []

    for variant in _completed_variants(summary):
        variant_name = str(variant.get("variant", "unknown_variant"))
        periods = _periods(variant)
        if not periods:
            continue

        for metric in ("ndmi", "valid_pixels", "cloud_pct"):
            chart = _chart_for_metric(
                metric,
                periods=periods,
                title=f"{chart_aoi_id} / {variant_name} / {metric}",
            )
            if chart is None:
                continue
            path = output_dir / f"{_slug(chart_aoi_id)}__{_slug(variant_name)}__{metric}.svg"
            path.write_text(chart, encoding="utf-8")
            artifacts.append(
                {
                    "aoi_id": chart_aoi_id,
                    "region": str(summary.get("region", "")),
                    "variant": variant_name,
                    "metric": metric,
                    "path": str(path),
                }
            )

    return artifacts


def write_mask_benchmark_batch_charts(
    summary: dict[str, Any],
    output_dir: Path,
) -> list[dict[str, str]]:
    """Write SVG chart artifacts for each successful AOI in a batch summary."""
    artifacts: list[dict[str, str]] = []
    for result in summary.get("aois", []):
        if not isinstance(result, dict) or result.get("status") != "success":
            continue
        benchmark = result.get("benchmark")
        if not isinstance(benchmark, dict):
            continue
        aoi_id = str(result.get("aoi_id", "unknown_aoi"))
        artifacts.extend(
            write_mask_benchmark_charts(
                benchmark,
                output_dir / _slug(aoi_id),
                aoi_id=aoi_id,
            )
        )
    return artifacts


def _completed_variants(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        variant
        for variant in summary.get("variants", [])
        if isinstance(variant, dict) and variant.get("status") != "skipped"
    ]


def _periods(variant: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        period
        for period in variant.get("ndmi_periods", [])
        if isinstance(period, dict)
    ]


def _chart_for_metric(
    metric: ChartMetric,
    *,
    periods: list[dict[str, Any]],
    title: str,
) -> str | None:
    labels = [_period_label(period) for period in periods]
    if metric == "ndmi":
        return _render_line_chart(
            title=title,
            y_label="NDMI",
            x_labels=labels,
            series=[
                ChartSeries("NDMI mean", _period_values(periods, "ndmi_mean"), "#1f77b4"),
                ChartSeries("NDMI EMA", _period_values(periods, "ndmi_ema"), "#d62728"),
            ],
        )
    if metric == "valid_pixels":
        return _render_line_chart(
            title=title,
            y_label="Valid pixels",
            x_labels=labels,
            series=[
                ChartSeries(
                    "Valid pixels",
                    _period_values(periods, "valid_pixel_count"),
                    "#2ca02c",
                )
            ],
            y_min=0.0,
        )
    return _render_line_chart(
        title=title,
        y_label="Cloud %",
        x_labels=labels,
        series=[ChartSeries("Cloud %", _period_values(periods, "cloud_pct"), "#7f7f7f")],
        y_min=0.0,
        y_max=100.0,
    )


def _period_label(period: dict[str, Any]) -> str:
    value = period.get("date") or period.get("period") or ""
    return str(value)


def _period_values(periods: list[dict[str, Any]], key: str) -> list[float | None]:
    values: list[float | None] = []
    for period in periods:
        value = period.get(key)
        values.append(float(value) if value is not None else None)
    return values


def _render_line_chart(
    *,
    title: str,
    y_label: str,
    x_labels: list[str],
    series: list[ChartSeries],
    y_min: float | None = None,
    y_max: float | None = None,
) -> str | None:
    numeric = [
        value
        for candidate in series
        for value in candidate.values
        if value is not None
    ]
    if not numeric or not x_labels:
        return None

    low = min(numeric) if y_min is None else y_min
    high = max(numeric) if y_max is None else y_max
    if low == high:
        padding = max(abs(low) * 0.1, 1.0)
        low -= padding
        high += padding
    elif y_min is None or y_max is None:
        padding = (high - low) * 0.08
        if y_min is None:
            low -= padding
        if y_max is None:
            high += padding

    elements = _base_svg_elements(title=title, y_label=y_label)
    elements.extend(_axis_elements(x_labels=x_labels, y_min=low, y_max=high))
    elements.extend(_series_elements(series=series, y_min=low, y_max=high))
    elements.extend(_legend_elements(series))
    elements.append("</svg>")
    return "\n".join(elements)


def _base_svg_elements(*, title: str, y_label: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_WIDTH}" height="{_HEIGHT}" '
        f'viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" aria-label="{escape(title)}">',
        "<style>"
        "text{font-family:Arial,sans-serif;fill:#1f2937}"
        ".axis{stroke:#4b5563;stroke-width:1.2}"
        ".grid{stroke:#e5e7eb;stroke-width:1}"
        ".tick{font-size:11px;fill:#4b5563}"
        ".title{font-size:18px;font-weight:700}"
        ".label{font-size:12px;font-weight:700}"
        ".legend{font-size:12px}"
        "</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text class="title" x="{_LEFT}" y="28">{escape(title)}</text>',
        (
            f'<text class="label" x="20" y="{_TOP + _PLOT_HEIGHT / 2:.1f}" '
            f'transform="rotate(-90 20 {_TOP + _PLOT_HEIGHT / 2:.1f})">'
            f"{escape(y_label)}</text>"
        ),
        f'<line class="axis" x1="{_LEFT}" y1="{_TOP}" x2="{_LEFT}" y2="{_TOP + _PLOT_HEIGHT}"/>',
        (
            f'<line class="axis" x1="{_LEFT}" y1="{_TOP + _PLOT_HEIGHT}" '
            f'x2="{_LEFT + _PLOT_WIDTH}" y2="{_TOP + _PLOT_HEIGHT}"/>'
        ),
    ]


def _axis_elements(*, x_labels: list[str], y_min: float, y_max: float) -> list[str]:
    elements: list[str] = []
    for tick in range(5):
        fraction = tick / 4
        y = _TOP + _PLOT_HEIGHT - (fraction * _PLOT_HEIGHT)
        value = y_min + fraction * (y_max - y_min)
        elements.extend(
            [
                f'<line class="grid" x1="{_LEFT}" y1="{y:.1f}" '
                f'x2="{_LEFT + _PLOT_WIDTH}" y2="{y:.1f}"/>',
                f'<text class="tick" x="{_LEFT - 10}" y="{y + 4:.1f}" text-anchor="end">'
                f"{value:.3g}</text>",
            ]
        )

    for index in _x_tick_indexes(len(x_labels)):
        x = _x_position(index, len(x_labels))
        elements.append(
            f'<text class="tick" x="{x:.1f}" y="{_HEIGHT - 28}" text-anchor="middle">'
            f"{escape(x_labels[index])}</text>"
        )
    return elements


def _series_elements(
    *,
    series: list[ChartSeries],
    y_min: float,
    y_max: float,
) -> list[str]:
    elements: list[str] = []
    for candidate in series:
        points = [
            (_x_position(index, len(candidate.values)), _y_position(value, y_min, y_max))
            for index, value in enumerate(candidate.values)
            if value is not None
        ]
        if not points:
            continue
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        dash = (
            f' stroke-dasharray="{candidate.stroke_dasharray}"'
            if candidate.stroke_dasharray is not None
            else ""
        )
        if len(points) > 1:
            elements.append(
                f'<polyline fill="none" stroke="{candidate.color}" stroke-width="2.4"{dash} '
                f'points="{point_text}"/>'
            )
        for x, y in points:
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{candidate.color}"/>'
            )
    return elements


def _legend_elements(series: list[ChartSeries]) -> list[str]:
    elements: list[str] = []
    x = _LEFT
    y = _HEIGHT - 10
    for candidate in series:
        elements.append(
            f'<line x1="{x}" y1="{y - 4}" x2="{x + 24}" y2="{y - 4}" '
            f'stroke="{candidate.color}" stroke-width="2.4"/>'
        )
        elements.append(
            f'<text class="legend" x="{x + 30}" y="{y}">{escape(candidate.label)}</text>'
        )
        x += 132
    return elements


def _x_tick_indexes(count: int) -> list[int]:
    if count <= 0:
        return []
    if count == 1:
        return [0]
    indexes = {0, count // 2, count - 1}
    return sorted(indexes)


def _x_position(index: int, count: int) -> float:
    if count <= 1:
        return _LEFT + (_PLOT_WIDTH / 2)
    return _LEFT + (index / (count - 1)) * _PLOT_WIDTH


def _y_position(value: float, y_min: float, y_max: float) -> float:
    return _TOP + _PLOT_HEIGHT - ((value - y_min) / (y_max - y_min)) * _PLOT_HEIGHT


def _slug(value: str) -> str:
    slug = _SLUG_RE.sub("-", value).strip("-._")
    return slug or "artifact"
