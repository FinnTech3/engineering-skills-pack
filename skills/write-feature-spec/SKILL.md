---
name: write-feature-spec
description: >
  Use when the user asks to "write a spec", "write a design doc", "spec this
  feature out" or "turn this into requirements", for a clarified feature over
  about one day or touching more than one team. Do not use for one-line fixes or
  spikes, an HTTP API contract (use design-http-api), or while blocking
  questions are still open (run clarify-requirements first).
---

# Write a feature spec

## Purpose

Produce a spec that a different engineer can implement and test without asking the author a question.
Target length is one to three pages.

## Inputs needed

- The confirmed requirements note (see `clarify-requirements`).
- Read access to the code that will change and to its current tests.
- Known constraints: latency or cost budgets, compatibility promises, deadlines.
- The names of the person who will implement it and the owner of each affected system.

## Steps

1. Ask where specs live in this repository (for example `docs/specs/`). Create `<slug>.md` there with a status line: `Draft`.
2. Write the problem in at most five lines, then a goals list and a non-goals list. At least two non-goals; they stop scope creep later.
3. Number the behaviors R1, R2, ... Each is one testable sentence with "must" or "must not", for example: "R3: Given an expired token, `POST /sessions` returns 401 with code `token_expired`." An adjective without a number ("fast", "simple", "secure") is rewritten or deleted.
4. Define data and interfaces exactly: field names, types, nullability, allowed values, size limits. State what existing clients and stored data see after the change.
5. Add an edge-case table: condition, then outcome. Cover empty input, maximum size, duplicate or retried requests, concurrent writers, partial failure, permission denied and dependency timeout.
6. Set budgets with numbers: p95 latency, throughput, storage growth per month, availability. For each, say how it will be measured.
7. Describe the chosen design in at most ten lines. List two rejected alternatives with one reason each. Name the riskiest assumption and a test of it that takes under two hours.
8. Write the rollout: feature flag name, data migration, backward compatibility, and the exact action that turns the feature off.
9. Write the test plan as a table: each R-number, the test level (unit, integration, end to end, manual) and the file where the test will live.
10. List open questions, each with an owner and a date. The status becomes `Approved` only when no blocking question remains.
11. Ask the implementer and one owner of an affected system to review. Record each approval with the date and the commit hash of the spec.

## Output

Return the spec as one Markdown document with numbered requirements (R1, R2, ...), non-goals, rejected alternatives, the edge-case table, budgets with their measurement methods, the test plan mapped to R-numbers and the rollout section. List approvals still missing at the end. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] Every R-number appears in the test plan with a test level.
- [ ] `grep -Ein "fast|simple|easy|appropriate|secure|scalable" <spec>` finds nothing outside quoted examples.
- [ ] At least 2 non-goals and 2 rejected alternatives are written down.
- [ ] The edge-case table has at least 6 rows.
- [ ] The rollout section names an off switch and who can use it.
- [ ] Every budget has a number and a measurement method.
- [ ] Approval from the implementer and one system owner is recorded with a date.
- [ ] The spec is at most about 150 lines; longer means it should be split.

## Failure modes

- **Essay instead of requirements.** Pages of design prose and no R-numbers. Reviewers cannot tell what to test.
- **Spec written after the code.** It describes the implementation, including its accidents. Write it from the requirements note.
- **Tasks disguised as requirements.** "Add a column" is a task. Write the behavior it enables.
- **Unbounded scope.** "Support all file formats" has no end. Name the formats and put the rest under non-goals.
- **Ignoring current behavior.** Clients depend on what exists today. Section 4 must say what stays the same.
- **Stale spec.** Code diverges and nobody updates the file. Mark superseded specs `Superseded by <link>` instead of leaving them wrong.

## When to stop and ask

- A requirement contradicts an existing public contract or a recorded decision.
- The spec needs a security, privacy or legal decision that nobody on the thread owns.
- The estimate exceeds two weeks of work. Ask whether to split it into separately shippable specs.
- The riskiest assumption cannot be tested cheaply. Ask whether to fund a spike before approving.
- No approver is available within the agreed review window.
