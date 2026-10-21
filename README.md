# llm_games

Verifiable games for language model post-training experiments. The first package
is a CPU-only Countdown engine with no runtime dependencies. Model inference and
training are future work.

## Setup

Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

An editable install makes the package available to notebooks using that Python
environment. Select the same environment as your notebook kernel.

## Explore the package

```python
from llm_games.games.countdown import (
    generate_puzzles, reachable_targets, solve, validate_expression,
)

numbers = [2, 3, 5, 7]
solution = solve(numbers, target=26)
print(solution)  # expression, value, operations, depth; None if unreachable

result = validate_expression(solution.expression, numbers, target=26)
assert result.legal and result.correct

# Legal arithmetic can miss the requested target.
result = validate_expression("7 + 3", numbers, target=26)
assert result.legal and not result.correct and result.value == 10

# All reachable values, with one reference expression per value.
solutions = reachable_targets(numbers)
print(sorted(solutions))

puzzles = generate_puzzles(count=10, seed=42)
print(puzzles[0])
```

Rules: positive integer tiles; each physical tile may be used at most once;
unused tiles are allowed. Repeated values are separate tiles. Only `+`, `-`, `*`,
and `/` are accepted; division must be exact, and every intermediate value must
be a positive integer. The validator accepts a bare arithmetic expression,
without an `Expression:` prefix, and never executes Python code. Invalid output
returns `ValidationResult(legal=False, ...)`; invalid puzzle definitions raise
`ValueError`.

The exhaustive solver uses subsets of physical tiles, retaining one expression
per subset and reachable value. References minimize operation count, then tree
depth, with deterministic expression ordering to break ties. `solution_depth`
is the depth of the chosen minimum-operation reference, not an independent
minimum across all solutions. The solver does not enumerate or count every
possible expression. It supports up to eight tiles, but cost grows rapidly;
four tiles is the intended starting point.

## Generate the pilot

```bash
llm-games generate-countdown \
  --count 200 --seed 42 --split pilot \
  --output data/generated/countdown-pilot-v1.jsonl \
  --manifest data/manifests/countdown-pilot-v1.json
```

The command refuses to overwrite an existing dataset or manifest. For a fresh
checkout, where the reference manifest already exists, use a different manifest
path (for example `/tmp/countdown-pilot-v1.json`) and compare its SHA-256 with the
committed manifest.

Tiles are sampled independently and uniformly from 1–20, then a target is sampled
uniformly from that tile set's reachable values in 1–200. Duplicate identities
`(sorted tiles, target)` are rejected. This sampling is **not uniform over all
solvable puzzles**. Every reference is checked by the validator before inclusion.
The generator has a bounded attempt count and raises if it cannot fill the
requested dataset.

For disjoint splits, pass prior puzzle keys explicitly:

```python
from llm_games.games.countdown import puzzle_key

train = generate_puzzles(100, seed=1, split="train")
train_keys = {puzzle_key(p.numbers, p.target) for p in train}
validation = generate_puzzles(
    20, seed=2, split="validation", exclude_keys=train_keys,
)
```

The initial 200-puzzle pilot (seed 42) has minimum-operation counts:

| Operations | Puzzles |
| --- | ---: |
| 0 | 3 |
| 1 | 28 |
| 2 | 80 |
| 3 | 89 |

These are structural difficulty proxies, not measured model difficulty. Generated
JSONL files are ignored by Git; small manifests record rules, sampling, seeds,
checksums, and summary statistics. The pilot is for exploration, not a final
held-out test set.

## Tests

```bash
python -m unittest discover -s tests -v
```

Without installing, prefix commands with `PYTHONPATH=src` and invoke the CLI as
`python3 -m llm_games.cli`. Tests cover illegal expressions, repeated and unused
tiles, exact division, solver reachability against an independent pair-reduction
oracle, deterministic generation, split exclusion, and JSONL persistence.

## Layout

- `src/llm_games/games/countdown/`: rules, validation, solver, and dataset API.
- `src/llm_games/cli.py`: dataset generation command.
- `tests/countdown/`: CPU-only standard-library tests.
- `data/manifests/`: committed dataset provenance and summaries.
- `data/generated/`: local generated datasets, ignored by Git.
- `runs/`: future local experiment outputs, ignored by Git.

Add model, evaluation, and training modules when the baselines need them.
