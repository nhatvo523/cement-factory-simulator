"""Run one configured scenario and export its frames as JSON."""

import argparse
import json
from pathlib import Path

from factory_sim.core.results import build_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--plant", type=Path, default=Path("configs/plants/bulk_material_line.json"))
    parser.add_argument("--models", type=Path, default=Path("configs/model_types"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ground-truth", action=argparse.BooleanOptionalAction, default=None)
    args = parser.parse_args()
    try:
        result = build_result(args.models, args.plant, args.scenario, ground_truth=args.ground_truth)
    except (OSError, KeyError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Simulation failed: {error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{result['scenario_id']}: {len(result['frames'])} frames -> {args.output}")


if __name__ == "__main__":
    main()
