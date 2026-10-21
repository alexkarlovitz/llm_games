"""Countdown uses positive integer tiles, each at most once."""
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


def check_numbers(numbers: Iterable[int]) -> tuple[int, ...]:
    tiles = tuple(numbers)
    if not tiles or any(type(n) is not int or n <= 0 for n in tiles):
        raise ValueError("Tiles must be a nonempty collection of positive integers")
    return tiles


def puzzle_key(numbers: Iterable[int], target: int) -> tuple[tuple[int, ...], int]:
    tiles = check_numbers(numbers)
    if type(target) is not int or target <= 0:
        raise ValueError("Target must be a positive integer")
    return tuple(sorted(tiles)), target


@dataclass(frozen=True)
class ValidationResult:
    legal: bool
    correct: bool
    value: int | None = None
    error: str | None = None
    used_tiles: tuple[int, ...] = ()


def tiles_available(used: list[int], numbers: tuple[int, ...]) -> bool:
    return not (Counter(used) - Counter(numbers))
