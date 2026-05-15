#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calibration.objective import comparison_rows, load_json


def svg_bar_plot(rows: list[dict[str, float | str]], title: str) -> str:
    width = 1300
    row_h = 28
    margin_left = 360
    margin_right = 80
    height = 90 + row_h * len(rows)
    max_abs = max(abs(float(row["relative_error"])) for row in rows) or 1.0
    max_abs = max(max_abs, 0.25)
    scale = (width - margin_left - margin_right) / (2.0 * max_abs)
    zero_x = margin_left + (width - margin_left - margin_right) / 2.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="40" y="42" font-family="Arial" font-size="24" font-weight="700">{title}</text>',
        f'<line x1="{zero_x}" y1="65" x2="{zero_x}" y2="{height - 20}" stroke="#344054" stroke-width="2"/>',
    ]
    for i, row in enumerate(rows):
        y = 82 + i * row_h
        rel = float(row["relative_error"])
        x = min(zero_x, zero_x + rel * scale)
        w = abs(rel * scale)
        color = "#b42318" if abs(rel) > 0.10 else "#027a48"
        label = str(row["target_name"])
        pct = f"{100.0 * rel:+.1f}%"
        parts.extend(
            [
                f'<text x="40" y="{y + 14}" font-family="Arial" font-size="14" fill="#101828">{label}</text>',
                f'<rect x="{x}" y="{y}" width="{w}" height="18" fill="{color}" opacity="0.85"/>',
                f'<text x="{width - 70}" y="{y + 14}" font-family="Arial" font-size="14" text-anchor="end" fill="#101828">{pct}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write an SVG target-error plot.")
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--source-id", default="direct_measurement")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = comparison_rows(load_json(args.metrics), args.source_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        svg_bar_plot(rows, f"Calibration target errors ({args.source_id})"),
        encoding="utf-8",
    )
    print(json.dumps({"wrote": str(args.out), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
