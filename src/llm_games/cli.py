"""Command line entry point for CPU-only dataset generation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from .games.countdown import generate_puzzles, write_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate-countdown")
    generate.add_argument("--count", type=int, default=200)
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--split", default="pilot")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.manifest.resolve():
        parser.error("Dataset and manifest paths must differ")
    if args.output.exists() or args.manifest.exists():
        parser.error("Output and manifest must not already exist")
    puzzles = generate_puzzles(args.count, seed=args.seed, split=args.split)
    write_jsonl(puzzles, args.output)
    manifest = {
        "schema_version": 1, "dataset": str(args.output),
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "count": len(puzzles), "seed": args.seed, "split": args.split,
        "rules": {"tile_count": 4, "tile_min": 1, "tile_max": 20,
                  "target_min": 1, "target_max": 200, "unused_tiles_allowed": True,
                  "positive_integer_intermediates": True},
        "sampling": "Uniform independent tiles, then uniform reachable target; reject duplicate identities",
        "reference_selection": "Minimum operations, then minimum depth, then deterministic expression ordering",
        "min_operations_histogram": dict(sorted(Counter(p.min_operations for p in puzzles).items())),
        "solution_depth_histogram": dict(sorted(Counter(p.solution_depth for p in puzzles).items())),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
