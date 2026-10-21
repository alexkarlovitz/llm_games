"""Exhaustive subset dynamic programming with one best expression per value."""
from dataclasses import dataclass

from .rules import check_numbers, puzzle_key


@dataclass(frozen=True)
class Solution:
    expression: str
    value: int
    operations: int
    depth: int


def _rank(solution: Solution):
    return solution.operations, solution.depth, solution.expression


def reachable_targets(numbers) -> dict[int, Solution]:
    """Return all reachable positive integers, allowing unused tiles.

    Physical tiles occupy separate bit positions, including repeated values.
    For each subset/value, retain the expression with lowest depth, then lexical
    order. Across subsets, prefer fewest operations first. This enumerates values,
    not every distinct expression or a solution count.
    """
    tiles = check_numbers(numbers)
    if len(tiles) > 8:
        raise ValueError("Exhaustive solver supports at most eight tiles")
    tables: dict[int, dict[int, Solution]] = {}
    answers: dict[int, Solution] = {}

    def keep(table, candidate):
        old = table.get(candidate.value)
        if old is None or _rank(candidate) < _rank(old):
            table[candidate.value] = candidate

    for mask in range(1, 1 << len(tiles)):
        table: dict[int, Solution] = {}
        if mask & (mask - 1) == 0:
            n = tiles[mask.bit_length() - 1]
            table[n] = Solution(str(n), n, 0, 0)
        else:
            left_mask = (mask - 1) & mask
            while left_mask:
                right_mask = mask ^ left_mask
                if left_mask < right_mask:
                    for a in tables[left_mask].values():
                        for b in tables[right_mask].values():
                            candidates = [(a, b, "+", a.value + b.value),
                                          (a, b, "*", a.value * b.value)]
                            for x, y in ((a, b), (b, a)):
                                if x.value > y.value:
                                    candidates.append((x, y, "-", x.value - y.value))
                                if x.value % y.value == 0:
                                    candidates.append((x, y, "/", x.value // y.value))
                            for x, y, op, value in candidates:
                                keep(table, Solution(
                                    f"({x.expression} {op} {y.expression})", value,
                                    x.operations + y.operations + 1,
                                    max(x.depth, y.depth) + 1))
                left_mask = (left_mask - 1) & mask
        tables[mask] = table
        for solution in table.values():
            keep(answers, solution)
    return answers


def solve(numbers, target: int) -> Solution | None:
    """Return a deterministic minimum-operation solution, or None."""
    tiles, _ = puzzle_key(numbers, target)
    return reachable_targets(tiles).get(target)
