#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calibration.objective import comparison_rows, load_json, weighted_rms


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare model metrics to direct, paper, or Nektar target summaries."
    )
    parser.add_argument("metrics", type=Path)
    parser.add_argument(
        "--source-id",
        choices=["direct_measurement", "paper_model", "nektar_closed_loop_1d"],
        default="paper_model",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = comparison_rows(load_json(args.metrics), args.source_id)
    payload = {
        "source_id": args.source_id,
        "weighted_rms_relative_error": weighted_rms(rows),
        "targets": rows,
    }
    text = json.dumps(payload, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
