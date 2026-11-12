# Worked example: `debug-from-evidence` on a flaky test

This is a real run of the `debug-from-evidence` skill on a small Python project. The commands and their output are
copied from the run (Python 3.13). The report follows the skill's `Output` section.

**Request:** "`test_summary_lists_categories` passes on my machine and fails about half the time in CI. Find out why."

## Symptom

Observed: `assert summarize(ORDER) == "3 items in: books, games"` fails with `'3 items in: games, books'`.
Expected: `"3 items in: books, games"`. Commit debugged: the project's `base` commit.

## Reproduction

```sh
for i in $(seq 1 20); do python3 -m pytest -q tests >/dev/null 2>&1 || fails=$((fails+1)); done; echo $fails
```

Failure rate: 13 of 20 runs. Each run is a new process. A fixed hash seed makes it repeatable:

```sh
PYTHONHASHSEED=2 python3 -m pytest -q tests     # failed
PYTHONHASHSEED=0 python3 -m pytest -q tests     # passed
```

Seeds 0, 1 and 4 passed. Seeds 2, 3 and 5 failed.

## Hypotheses

| # | Hypothesis | Prediction | Result |
|---|---|---|---|
| H1 | Output depends on set iteration order | Same input prints a different order under different `PYTHONHASHSEED` values | Confirmed: seed 2 printed `games, books`, seed 0 printed `books, games` |
| H2 | The test depends on test order or shared state | The failure would not follow the hash seed | Refuted: the failure follows the seed and the test runs alone |
| H3 | Locale or encoding changes the sort | Failure would change with `LC_ALL` | Not tested: H1 explained every observation |

## Root cause

Because `summarize` builds `tags` as a set and joins it directly, when Python randomises string hashing in each new
process, the categories come out in a different order; the fix belongs in `orders/summary.py:6`, where the join
happens. A prediction made from this sentence was checked: with `PYTHONHASHSEED=2` the set prints as
`{'games', 'books'}`.

## Fix and regression test

- Fix, `orders/summary.py:6`: `', '.join(tags)` became `', '.join(sorted(tags))`.
- Regression test, `tests/test_summary_order.py`: runs `summarize` in a new process for hash seeds 0 to 5.
  On the parent commit: 3 failed, 3 passed. With the fix: all pass.
- Original reproduction after the fix: 0 failures in 20 runs. Full suite: `7 passed`.

## Sibling search

```sh
git grep -n "join(" -- '*.py'
```

One match, the line just fixed. No other place joins an unordered collection.

## Commit message

```
Fix flaky category order in order summary
Cause: summarize() joined a set, whose order changes with Python's per-process hash seed.
Evidence: PYTHONHASHSEED=2 prints "games, books"; seeds 2, 3 and 5 failed, 0, 1 and 4 passed.
Test: tests/test_summary_order.py runs seeds 0 to 5; it fails 3 of 6 before the fix and passes after.
```
