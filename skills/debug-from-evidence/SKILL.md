---
name: debug-from-evidence
description: >
  Use when the user says "this test is failing", "find the bug", "why is this
  crashing", "it fails sometimes" or "this worked yesterday". Builds a
  reproduction, tests ranked hypotheses by observation and fixes the root cause.
  Do not use when the cause is already known (use test-first-change) or for
  slowness (use investigate-performance).
---

# Debug from evidence

## Purpose

Find the root cause of a defect by observation, prove it with a prediction, and fix it with a regression test.

## Inputs needed

- The observed behavior and the expected behavior, with the exact error text, input, version and environment.
- Raw evidence: stack trace, log lines, failing test output. Not a summary of them.
- The last known good version or date, if there is one.
- Permission to run the code, and to read logs for the affected environment.

## Steps

1. Write the symptom as "observed X, expected Y" and paste the raw evidence under it. Record the commit hash you are debugging and confirm the running binary was built from it.
2. Reproduce it with one command. Record the failure rate (for example 7 of 10 runs). If you cannot reproduce it, do not guess: add logging that would capture the failing case and wait for the next occurrence.
3. Shrink the reproduction until removing anything makes it pass. Halve the input repeatedly. If a known good version exists, run `git bisect run <command>`.
4. Write at least three hypotheses. For each, write a prediction: "If H is true, then log line Y will show Z, or changing W will flip the result."
5. Rank the hypotheses by likelihood multiplied by how cheap they are to test. Test the top one by observation first: a log line, a debugger breakpoint, a query. Change one variable per experiment and record each outcome as confirmed or refuted.
6. Trace backward from the symptom. Find the first point where actual state differs from what the code should have at that point. The defect is at or before that point. Check inputs and outputs on both sides of each boundary you cross.
7. State the root cause in one sentence: "Because A, when B, C happens; the fix belongs in D." Then predict an observation you have not yet made and check it. If the prediction fails, the sentence is wrong.
8. Write a failing regression test at the lowest layer that exposes the defect (see `test-first-change`). Fix the cause, not the symptom: a catch block or a null check around the damage is not a fix.
9. Search for the same pattern elsewhere with `git grep` or a syntax-tree search. Fix the siblings or file a ticket for each.
10. Remove temporary instrumentation. Keep any log line that would have shortened this investigation.
11. Write the commit message as four lines: symptom, root cause, the evidence that proves it, the test that guards it.

### Example hypothesis list

```
Symptom: GET /orders returns 500 on about 1 request in 10 since release 4.12
H1  stale cache entry        predicts: failures cluster on entries older than the TTL
H2  order without customer   predicts: every failing id has customer_id NULL (run the query)
H3  new serializer           predicts: release 4.11 code fails the same way on the same payload
```

## Output

Return a debugging report in this order: the symptom as "observed X, expected Y", the one-command reproduction with its failure rate, the hypothesis list with each prediction and its result, the root-cause sentence, the fix and regression test with file paths, and the sibling-search result. Finish with the four-line commit message. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] A single reproduction command is stored in a test or in the PR description.
- [ ] The root cause sentence exists, and a prediction made from it was confirmed.
- [ ] The regression test fails without the fix and passes with it.
- [ ] The original reproduction passes 10 of 10 runs (20 of 20 for an intermittent failure).
- [ ] `git diff` contains no leftover `print`, `console.log`, debugger statement or commented-out code.
- [ ] The sibling search is done and its result is written down.

## Failure modes

- **Shotgun changes.** Several edits at once, then the bug disappears and nobody knows why. One variable per experiment.
- **Fix at the symptom.** A null check hides the line that produced the null. Keep asking why until the cause is in code you can change.
- **Stopping at the first plausible cause.** Check it with a prediction before building on it.
- **Blaming the dependency early.** Rule out your own code and configuration first; confirm with a minimal program that uses the library alone.
- **Stale artifact.** The running process is not the code you edited: old build, cached bytecode, wrong container. Compare a version string or hash.
- **Observer effect.** Added logging changes timing and hides a race. Use lower-overhead capture or reason from the trace.
- **Confirmation bias.** Looking only for evidence that supports the favorite hypothesis. Write what result would refute it before you run the experiment.
- **Wrong environment.** Reading logs from staging while the bug is in production, or mixing time zones. Note the environment on every piece of evidence.

## When to stop and ask

- You need production data, credentials or access you do not have.
- The next experiment would interrupt live users or change production state.
- The evidence suggests data corruption, data loss or a security problem. Escalate before continuing.
- Three hypotheses are refuted and no new one exists. Share the evidence log and ask for a second pair of eyes.
- Two hours have passed without new evidence.
