---
name: test-first-change
description: >
  Use when the user asks to "add this feature with tests", "write the test
  first", "fix this bug and add a regression test" or "do TDD", in code that
  automated tests can cover. Do not use for throwaway spikes, copy or config
  edits, generated code, or when the expected behavior or the cause of a
  failure is still unknown (use debug-from-evidence).
---

# Test-first change

## Purpose

Change behavior in small steps where every step is driven by a test that was seen failing first.

## Inputs needed

- The behavior to add or the bug report, stated as input and expected output.
- The command that runs the tests for the affected area, and the command for the full suite.
- A green baseline for that area. If it is red or flaky, see "When to stop and ask".

## Steps

1. Write the behavior as one sentence: "Given X, when Y, then Z." One sentence becomes one test.
2. Find the closest existing test file. Copy its style: fixtures, naming, assertions, runner flags.
3. Run the area's tests before touching anything and record the result (number passed, duration). This is the baseline.
4. Write one test for the smallest next behavior. Use concrete inputs and concrete expected values. Do not assert on internal calls unless the interaction itself is the contract.
5. Run it. It must fail, and the failure message must describe the missing behavior, not an import error, a typo or a fixture problem. Save the failure line. A test that passes on its first run is redundant or wrong: find out which.
6. Write the least code that makes the test pass. Returning a constant is allowed for the first test.
7. Run the new test and the area's tests. All must pass before moving on.
8. Add a second example that breaks the constant (triangulation). Then add edge cases that apply: empty, one, maximum, maximum plus one, wrong type, duplicate, reordered, time zone and locale.
9. Refactor only on green. Run the area's tests after each edit. Commit the test and the code in the same commit.
10. For a bug fix, first reproduce the bug as a failing test at the lowest level that shows it. Confirm it fails on the unfixed code (`git stash` the fix or check out the parent commit), then confirm it passes with the fix.
11. Run a mutation check on each new behavior: change one operator or constant in the new code (flip `<` to `<=`, replace a value). At least one new test must fail. Revert the change.
12. Run the full suite and the linters. Run the new tests three times in a row to expose order or timing dependence.

### Example: right and wrong reasons to fail

```
Right:  assert Decimal('100.00') == Decimal('90.00')      the discount is not applied yet
Wrong:  ImportError: cannot import name 'apply_discount'  fix the test setup, then rerun
```

## Output

Return one line per behavior: the test name, the first failing message you saw, and the passing result. Add the full-suite result, the mutation-check result for each behavior, and any assertion you weakened or deleted with the reason. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] For each new test, the first failing output was seen and its message matched the missing behavior.
- [ ] The area's tests and the full suite pass.
- [ ] The new tests passed 3 consecutive runs with no change in result.
- [ ] A bug fix has a regression test that fails on the parent commit and passes on the fix.
- [ ] Each new behavior survived the mutation check: a deliberate break made a test fail.
- [ ] No new test uses sleeps, the real network, the real clock or shared mutable state.
- [ ] No existing assertion was weakened or deleted, or the commit message says why.

## Failure modes

- **Test written after the code.** It mirrors the implementation, including its mistakes. Delete it and restart from step 4.
- **Testing the mocks.** The assertion checks that a mock was called, so the test passes while behavior is broken. Assert outputs and state.
- **Green by weakening.** An assertion is loosened or removed to make a failure disappear. Treat every edited assertion as a behavior change that needs a reason.
- **One giant test.** A failure does not say which behavior broke. One behavior per test.
- **Flaky by construction.** Real time, random data without a seed, shared database rows or test order. Inject the clock, seed the randomness and isolate state.
- **Testing private functions.** Tests break on every refactor. Test through the public entry point.
- **Skipping the red step.** Without seeing the failure you do not know the test can fail.

## When to stop and ask

- The baseline is red or flaky. Building on it hides new failures. Ask who owns the failing tests.
- The code cannot be tested without a redesign, such as a hidden global or a hard-wired network call. Ask before introducing a seam.
- The expected behavior is ambiguous or two sources disagree. Ask; do not pick one.
- A realistic test needs production data, credentials or a paid service.
- The change would need a test to be deleted or its assertion changed to pass.
