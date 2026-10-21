"""Deterministic solvable-puzzle generation and JSONL persistence."""
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random

from .parser import validate_expression
from .rules import puzzle_key
from .solver import reachable_targets


@dataclass(frozen=True)
class Puzzle:
    id: str
    numbers: tuple[int, ...]
    target: int
    reference_expression: str
    min_operations: int
    solution_depth: int
    split: str


def generate_puzzles(count: int = 200, *, seed: int = 42, split: str = "pilot",
                     tile_count: int = 4, tile_min: int = 1, tile_max: int = 20,
                     target_min: int = 1, target_max: int = 200,
                     exclude_keys=(), max_attempts: int | None = None) -> list[Puzzle]:
    """Sample tiles uniformly, then uniformly sample a reachable in-range target.

    Reject duplicate puzzle identities and tile sets with no eligible target.
    This is not uniform sampling over all solvable puzzle identities. Pass prior
    split keys in exclude_keys to enforce disjoint splits.
    """
    for name, value in (("count", count), ("seed", seed), ("tile_count", tile_count),
                        ("tile_min", tile_min), ("tile_max", tile_max),
                        ("target_min", target_min), ("target_max", target_max)):
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
    if count < 0 or not 1 <= tile_count <= 8 or not 1 <= tile_min <= tile_max or not 1 <= target_min <= target_max:
        raise ValueError("Invalid count, tile count, or number/target bounds")
    limit = max(1000, count * 100) if max_attempts is None else max_attempts
    if type(limit) is not int or limit < 0:
        raise ValueError("max_attempts must be a nonnegative integer")
    if not isinstance(split, str) or not split:
        raise ValueError("split must be a nonempty string")
    rng = random.Random(seed)
    seen = {puzzle_key(numbers, target) for numbers, target in exclude_keys}
    puzzles = []
    for _ in range(limit):
        if len(puzzles) == count:
            break
        numbers = tuple(sorted(rng.randint(tile_min, tile_max) for _ in range(tile_count)))
        reachable = reachable_targets(numbers)
        targets = sorted(t for t in reachable if target_min <= t <= target_max)
        if not targets:
            continue
        target = rng.choice(targets)
        key = puzzle_key(numbers, target)
        if key in seen:
            continue
        solution = reachable[target]
        if not validate_expression(solution.expression, numbers, target).correct:
            raise RuntimeError("Solver produced an invalid reference")
        seen.add(key)
        puzzles.append(Puzzle(f"{split}_{len(puzzles):06d}", numbers, target,
                              solution.expression, solution.operations,
                              solution.depth, split))
    if len(puzzles) != count:
        raise ValueError(f"Generated only {len(puzzles)}/{count} unique puzzles in {limit} attempts")
    return puzzles


def write_jsonl(puzzles: list[Puzzle], path: str | Path) -> None:
    """Write records, refusing to overwrite an existing dataset."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        for puzzle in puzzles:
            stream.write(json.dumps(asdict(puzzle), sort_keys=True) + "\n")
