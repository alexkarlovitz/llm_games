import itertools
import json
from pathlib import Path
import tempfile
import unittest

from llm_games.games.countdown import (
    generate_puzzles, puzzle_key, reachable_targets, solve,
    validate_expression, write_jsonl,
)


def brute_values(values):
    """Independent pair-reduction oracle; stopping early allows unused tiles."""
    answers = set(values)
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            a, b = values[i], values[j]
            remaining = [v for k, v in enumerate(values) if k not in (i, j)]
            results = {a + b, a * b}
            for x, y in ((a, b), (b, a)):
                if x > y:
                    results.add(x - y)
                if x % y == 0:
                    results.add(x // y)
            for value in results:
                answers.update(brute_values(remaining + [value]))
    return answers


class ValidationTests(unittest.TestCase):
    def test_valid_and_wrong_target(self):
        result = validate_expression("(7 * 3) + 5", [2, 3, 5, 7], 26)
        self.assertTrue(result.correct)
        self.assertEqual(result.used_tiles, (7, 3, 5))
        result = validate_expression("7 + 3", [2, 3, 5, 7], 26)
        self.assertTrue(result.legal)
        self.assertFalse(result.correct)
        self.assertEqual(result.value, 10)

    def test_repeated_tiles(self):
        self.assertTrue(validate_expression("3 + 3", [3, 3, 5, 7], 6).correct)
        self.assertFalse(validate_expression("3 + 3", [2, 3, 5, 7], 6).legal)
        self.assertTrue(validate_expression("7", [2, 3, 5, 7], 7).correct)

    def test_exact_division(self):
        self.assertTrue(validate_expression("(7 + 5) / 3", [2, 3, 5, 7], 4).correct)
        self.assertFalse(validate_expression("7 / 3", [2, 3, 5, 7], 2).legal)

    def test_invalid_intermediates(self):
        for expression, numbers in [
            ("5 / (3 - 3)", [5, 3, 3, 2]),
            ("(2 - 3) + 5", [2, 3, 5, 7]),
            ("(3 - 3) + 5", [3, 3, 5, 7]),
            ("(3 / 2) * 2", [3, 2, 2, 7]),
        ]:
            with self.subTest(expression=expression):
                self.assertFalse(validate_expression(expression, numbers, 5).legal)

    def test_malformed_and_unsupported(self):
        for expression in ["", "(", "2 +", "Expression: 2 + 3", "2 ** 3",
                           "5 // 2", "5 % 2", "-2 + 3", "True", "2.0",
                           "foo", "abs(2)", "[2]", "2; 3", "2 + 0", "2" * 5000]:
            with self.subTest(expression=expression):
                self.assertFalse(validate_expression(expression, [2, 3, 5, 7], 5).legal)

    def test_bad_puzzle_definitions(self):
        for numbers, target in [([], 1), ([0, 2], 2), ([True, 2], 2), ([2], 0)]:
            with self.assertRaises(ValueError):
                validate_expression("2", numbers, target)


class SolverTests(unittest.TestCase):
    def test_completeness_against_pair_reduction(self):
        for numbers in itertools.combinations_with_replacement(range(1, 5), 3):
            with self.subTest(numbers=numbers):
                solutions = reachable_targets(numbers)
                self.assertEqual(set(solutions), brute_values(list(numbers)))
                for target, solution in solutions.items():
                    self.assertTrue(validate_expression(solution.expression, numbers, target).correct)

    def test_four_tile_reference_validity(self):
        for numbers in ([2, 3, 5, 7], [1, 1, 1, 1], [3, 3, 7, 7]):
            solutions = reachable_targets(numbers)
            self.assertEqual(set(solutions), brute_values(list(numbers)))
            for target, solution in solutions.items():
                result = validate_expression(solution.expression, numbers, target)
                self.assertTrue(result.correct, solution)
                self.assertEqual(solution.operations, len(result.used_tiles) - 1)

    def test_minimum_operations_and_determinism(self):
        self.assertEqual(solve([2, 3, 5, 7], 5).operations, 0)
        self.assertEqual(solve([2, 3, 5, 7], 10).operations, 1)
        self.assertEqual(solve([2, 3, 5, 7], 26).operations, 2)
        self.assertEqual(solve([7, 5, 3, 2], 26), solve([2, 3, 5, 7], 26))
        self.assertIsNone(solve([1, 1], 99))
        with self.assertRaises(ValueError):
            reachable_targets([1] * 9)


class DatasetTests(unittest.TestCase):
    def test_reproducibility_and_disjointness(self):
        first = generate_puzzles(20, seed=7)
        self.assertEqual(first, generate_puzzles(20, seed=7))
        keys = {puzzle_key(p.numbers, p.target) for p in first}
        self.assertEqual(len(keys), 20)
        second = generate_puzzles(20, seed=7, split="validation", exclude_keys=keys)
        self.assertTrue(keys.isdisjoint(puzzle_key(p.numbers, p.target) for p in second))
        for puzzle in first + second:
            self.assertTrue(validate_expression(puzzle.reference_expression, puzzle.numbers, puzzle.target).correct)
        self.assertEqual(puzzle_key([3, 2, 3], 6), puzzle_key([3, 3, 2], 6))

    def test_exhausted_space_and_bad_settings(self):
        with self.assertRaises(ValueError):
            generate_puzzles(2, tile_count=1, tile_min=1, tile_max=1, max_attempts=3)
        with self.assertRaises(ValueError):
            generate_puzzles(1, target_min=0)
        self.assertEqual(generate_puzzles(0), [])

    def test_jsonl_round_trip_and_overwrite_protection(self):
        puzzles = generate_puzzles(3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "puzzles.jsonl"
            write_jsonl(puzzles, path)
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([r["id"] for r in records], [p.id for p in puzzles])
            for record in records:
                self.assertTrue(validate_expression(record["reference_expression"], record["numbers"], record["target"]).correct)
            with self.assertRaises(FileExistsError):
                write_jsonl(puzzles, path)


if __name__ == "__main__":
    unittest.main()
