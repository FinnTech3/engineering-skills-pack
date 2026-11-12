---
name: refactor-without-behavior-change
description: >
  Use when the user asks to "refactor this", "clean this up", "extract this into
  a function", "rename this everywhere" or "deduplicate this" and behavior must
  stay identical. Do not use when behavior is meant to change (do that in a
  separate change), or when no test or other check can observe current behavior
  and none can be added.
---

# Refactor without behavior change

## Purpose

Restructure code in small mechanical steps, with tests bracketing every step, so that behavior is provably unchanged.

## Inputs needed

- A goal with a measurable end state, such as "`parse_order` is under 40 lines" or "`billing` no longer imports `web`".
- The commands for the fast tests, the full suite, the type checker and the linter.
- The list of public entry points: exported symbols, endpoints, CLI flags, file formats.
- Knowledge of who else edits these files right now.

## Steps

1. Write the goal as one sentence with a number or a checkable fact. If you cannot, this is not yet a refactor; stop and ask.
2. Measure the baseline: test results, type-check and lint status, the list of public symbols (`git grep` for each), and a timing for any hot path.
3. Pin current behavior. Run the tests with coverage on the lines you will move. Where lines are uncovered, write characterization tests that record what the code does today, including odd outputs. Commit them on their own before any structural change.
4. Plan the work as a list of mechanical moves, each producing at most about 50 changed lines and leaving the build green. Prefer tool-driven moves (IDE rename, codemod) over hand edits for renames and relocations.
5. Do one move. Run the fast tests. Commit with a message that names the move, for example "extract: parse_header out of handler".
6. If a move turns the tests red, revert that move. Do not debug forward. Split it into smaller moves and retry.
7. Keep the change pure. Do not fix bugs, change messages, upgrade dependencies or reformat unrelated files in these commits. Write each bug you notice on a list and fix it afterwards in its own commit.
8. When callers outside the plan must change, leave a thin wrapper at the old name that forwards to the new one, and migrate callers later.
9. After the last move run the full suite, the type checker and the linter. Compare the public symbol list with the baseline. Re-time hot paths.
10. Review the diff with `git diff -M --stat` to confirm moves register as renames, and with whitespace changes hidden (`git diff -w`) to see real edits.
11. Delete dead code only after a search for its name finds no references in code, config, templates, scripts and docs, including dynamic uses such as strings and reflection.

## Output

Return the goal metric before and after, the commits in order with one line each, the test results at baseline and at the end, the public symbol comparison, the hot-path timing against baseline, and the output of `git diff --stat`. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] Every test that passed at baseline still passes, with no assertion edited.
- [ ] Characterization tests were committed before the first structural commit and pass at the end.
- [ ] The goal metric from step 1 is met, and the number is quoted in the PR description.
- [ ] The public symbol list is identical to the baseline, or each difference has a wrapper.
- [ ] Every commit builds and passes the fast tests.
- [ ] Timing of hot paths is within 5% of baseline.
- [ ] `git diff --stat` lists only files named in the plan.

## Failure modes

- **Refactor plus feature.** Reviewers cannot tell which edit changed behavior. Split the work into separate changes.
- **Big-bang rewrite.** One step touches 2000 lines and cannot be bisected. Cut into moves that each stay green.
- **Refactoring blind.** No tests cover the code and the work starts anyway. Pin behavior first (step 3).
- **Editing tests to match.** A changed expectation is a behavior change. Stop and treat it as one.
- **Renames that miss dynamic use.** String lookups, reflection, config keys, templates and serialized names do not appear in a symbol search. Search for the literal text too.
- **Silently fixing a bug.** Callers may depend on the old output. Record it and fix it separately.
- **Two paths left behind.** The new code is added and the old stays "for now". Remove the old path or file a dated ticket.

## When to stop and ask

- No test, snapshot or manual procedure can observe the current behavior and you cannot add one.
- Pinning behavior reveals a bug that other code may rely on. Ask whether to preserve it.
- The goal needs a change to a public API, a wire format or a stored data format.
- Another team owns the files, or someone has open work in them.
- Scope has grown by more than half compared with the plan from step 4.
