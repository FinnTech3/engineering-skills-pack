# Agensi listing copy

Paste these into the submit form at agensi.io/dashboard/submit. Upload `dist/engineering-workflow-skills.zip`
(build it with `python3 tools/agensi_build.py agensi/engineering-workflow-skills --with skills`, which also checks
this file against Agensi's field limits). Agensi lists it as a skill pack because the zip holds 14 `SKILL.md` files.
Logo and screenshots are in `agensi/media/`.

| Field | Value |
|---|---|
| Title | Engineering Workflow Skills: 14 Senior-Engineer Workflows |
| Categories | Code Quality & Review; Testing & Debugging; Technical Documentation |
| Suggested price | $19 one-time |
| Tags | code-review, debugging, testing, refactoring, release-management, api-design, postmortem |
| Compatibility note | Requires nothing to install. Works with any agent that supports SKILL.md. The skills use the project's own git, tests and linters. |
| Permissions | None of its own. When a skill runs, the agent may run git, the project's test runner and its linters. No network access, no credentials. |
| Docs link | https://github.com/FinnTech3/engineering-skills-pack |

## Summary

Fourteen checkable workflows, from clarifying a request to shipping with a rollback, that make an AI coding agent work like a careful senior engineer.

## Description

AI coding agents are fast. They also skip steps: they guess at requirements, fix symptoms, weaken a test to make
it pass, and ship with no way back. This pack gives your agent the workflow a careful senior engineer follows for
the fourteen jobs that matter most.

**How it works.** You ask for the job in your own words ("debug this failing test", "plan this migration",
"review my PR") and the agent picks the matching skill from its description. Every skill has the same shape, so
results are consistent: numbered steps, a defined output, exit criteria the agent can check with a command or a
number, the ways that job usually goes wrong, and the points where the agent must stop and ask you.

**The fourteen skills.** Clarify requirements, write a feature spec, break down tasks, design an HTTP API, plan a
database migration, make a test-first change, refactor without behaviour change, debug from evidence,
investigate performance, give and receive code review, review the security surface, release with rollback,
write an incident postmortem, and write technical docs.

**What makes it different.** Exit criteria are checkable ("the reproduction passes 10 of 10 runs"), never
"looks good". Each skill says when not to use it, so the right one triggers. Each defines its output, so you get
the same report layout every time.

**Where it stops.** These are process skills. They do not know your stack's conventions, so the agent still reads
your code first. They do not replace human approval for releases, migrations or security decisions, and each
skill says when the agent must hand the decision to you.

## See it in action

**Request:** "`test_summary_lists_categories` passes on my machine and fails about half the time in CI. Find out why."

**Result:**

#### Symptom

Observed: `assert summarize(ORDER) == "3 items in: books, games"` fails with `'3 items in: games, books'`.
Expected: `"3 items in: books, games"`. Commit debugged: the project's `base` commit.

#### Reproduction

```sh
for i in $(seq 1 20); do python3 -m pytest -q tests >/dev/null 2>&1 || fails=$((fails+1)); done; echo $fails
```

Failure rate: 13 of 20 runs. Each run is a new process. A fixed hash seed makes it repeatable:

```sh
PYTHONHASHSEED=2 python3 -m pytest -q tests     # failed
PYTHONHASHSEED=0 python3 -m pytest -q tests     # passed
```

Seeds 0, 1 and 4 passed. Seeds 2, 3 and 5 failed.

#### Hypotheses

| # | Hypothesis | Prediction | Result |
|---|---|---|---|
| H1 | Output depends on set iteration order | Same input prints a different order under different `PYTHONHASHSEED` values | Confirmed: seed 2 printed `games, books`, seed 0 printed `books, games` |
| H2 | The test depends on test order or shared state | The failure would not follow the hash seed | Refuted: the failure follows the seed and the test runs alone |
| H3 | Locale or encoding changes the sort | Failure would change with `LC_ALL` | Not tested: H1 explained every observation |

#### Root cause

Because `summarize` builds `tags` as a set and joins it directly, when Python randomises string hashing in each new
process, the categories come out in a different order; the fix belongs in `orders/summary.py:6`, where the join
happens. A prediction made from this sentence was checked: with `PYTHONHASHSEED=2` the set prints as
`{'games', 'books'}`.

#### Fix and regression test

- Fix, `orders/summary.py:6`: `', '.join(tags)` became `', '.join(sorted(tags))`.
- Regression test, `tests/test_summary_order.py`: runs `summarize` in a new process for hash seeds 0 to 5.
  On the parent commit: 3 failed, 3 passed. With the fix: all pass.
- Original reproduction after the fix: 0 failures in 20 runs. Full suite: `7 passed`.

#### Sibling search

```sh
git grep -n "join(" -- '*.py'
```

One match, the line just fixed. No other place joins an unordered collection.

#### Commit message

```
Fix flaky category order in order summary
Cause: summarize() joined a set, whose order changes with Python's per-process hash seed.
Evidence: PYTHONHASHSEED=2 prints "games, books"; seeds 2, 3 and 5 failed, 0, 1 and 4 passed.
Test: tests/test_summary_order.py runs seeds 0 to 5; it fails 3 of 6 before the fix and passes after.
```

## Limitations

- Process guidance, not code generation: the agent still does the engineering work.
- Written for general software teams. Your own conventions win where they differ.
- Skills ask the agent to run commands your project already has; they cannot supply tools you lack.
- No skill replaces human sign-off on releases, migrations or security findings.

## FAQ

**Do I need to install anything?** No. The skills are instructions.

**Does the agent run all fourteen at once?** No. It picks the one that matches your request.

**Can I use one skill without the rest?** Yes. Each skill stands alone and says when it applies.

**Does it work with my stack?** Yes. The skills do not assume a language or framework.

**Will it ask me before risky steps?** Yes. Each skill has a "when to stop and ask" section.

## Use cases

- Debug an intermittent failure from evidence instead of guesses
- Plan a zero-downtime database migration with a tested rollback
- Review a pull request with severity-labelled findings
- Write a blameless postmortem with owned, dated actions
