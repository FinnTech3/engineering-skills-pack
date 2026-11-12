---
name: break-down-tasks
description: >
  Use when the user asks to "break this down into tasks", "split this spec into
  work items", "plan the work", "estimate this" or "what order should we build
  this in", and an approved spec or large change exists. Do not use for a change
  under about one hour, or while the spec is unsettled.
---

# Break down tasks

## Purpose

Split a spec into small, ordered, independently verifiable tasks, each tied to the requirements it delivers.

## Inputs needed

- An approved spec with numbered requirements (see `write-feature-spec`).
- The repository layout and its test and deploy commands.
- Team constraints: who can work in parallel, release cadence, freeze windows.
- Access or approvals that work will need (credentials, environments, other teams).

## Steps

1. Pick the riskiest requirement or assumption. Make the thinnest end-to-end slice that exercises it task 1. It must run through every layer, even if it only handles one input.
2. List the remaining deliverables as vertical slices: one user-visible behavior through every layer it touches. A layer on its own ("add the table", "build the UI") is a task only when it can ship by itself.
3. Size each task to at most one working day and about 400 changed lines including tests. Split anything bigger. Merge anything under 15 minutes into its neighbor.
4. Write each task in the same five fields:
   - **Title:** verb and object, such as "Reject expired tokens at login".
   - **Scope:** the modules or files expected to change.
   - **Done when:** an observable check, as a command, a test name or a request and response.
   - **Depends on:** task ids, or none.
   - **Delivers:** the R-numbers from the spec.
5. Draw the dependency list and confirm it has no cycle. Order by risk first, then critical path, then independent work that can run in parallel.
6. For each task, decide whether it can merge alone without breaking the main branch. If not, put it behind a flag or merge it with the task that completes it.
7. Add tasks that are easy to forget: migrations, the flag and its removal date, metrics and logs, documentation, a rollback rehearsal, and cleanup of temporary code.
8. Insert a checkpoint after every third task: a demo, an integration run or a review of remaining estimates.
9. Estimate each task in hours. Add 30% only to tasks tagged risky. Record your confidence as low, medium or high.
10. Cross-check against the spec. Every R-number must be delivered by at least one task, and every task must deliver an R-number or be labelled "enabling" with a reason.

### Example task card

```
Title:       Reject expired tokens at login
Scope:       auth/session.py, tests/test_session.py
Done when:   pytest tests/test_session.py::test_expired_token passes, and
             POST /sessions with an expired token returns 401 token_expired
Depends on:  T1
Delivers:    R3
```

## Output

Return the task list in dependency order, one task per row with all five fields. After it, give the requirement-to-task mapping, the total estimate and the share of work tagged risky. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] Every task has all five fields filled in.
- [ ] No task is estimated above 8 hours or planned above 400 changed lines.
- [ ] Every R-number in the spec maps to at least 1 task, and every task maps to an R-number or an "enabling" reason.
- [ ] The dependency list has no cycles.
- [ ] Task 1 is a working end-to-end slice, not a layer.
- [ ] Each task says whether it merges alone, and if not, how it is gated.
- [ ] Migration, flag removal, observability and rollback tasks exist if the spec needs them.
- [ ] Total estimate and the share of work tagged risky are stated.

## Failure modes

- **Horizontal layering.** Database first, then API, then UI. Nothing works until the last task and integration problems surface late. Slice vertically.
- **Unverifiable tasks.** "Improve error handling" has no finish line. Rewrite it with a check.
- **The big integration task.** A final "wire everything together" task hides the largest risk. Integrate in task 1 and keep it integrated.
- **Hidden prerequisites.** Credentials, environment access or a decision from another team stalls work on day three. List them in step 7.
- **Frozen plan.** Reality moves. Re-plan whenever a task exceeds twice its estimate or a checkpoint changes the facts.
- **Micro-tasks.** Forty tasks of ten minutes cost more to track than to do. Merge them.
- **Sizing by calendar guess.** Size by observable outcome and changed lines, then convert to hours.

## When to stop and ask

- The critical path exceeds two weeks. Ask whether to cut scope or add people before starting.
- A task needs access, data or a decision from a team that has not agreed to provide it.
- A spec requirement cannot be mapped to any task you can verify.
- The total estimate exceeds the budget given in the spec.
- Two tasks would change the same module in conflicting ways and the owner is unknown.
