---
name: give-and-receive-code-review
description: >
  Use when the user says "review this PR", "review my changes", "give feedback
  on this diff" or "reply to these review comments". Covers labelling findings,
  proving blockers and replying with evidence. Do not use for the checks you
  run on your own work before committing, a whole-system security audit (use
  review-security-surface), or settling design before any code exists.
---

# Give and receive code review

## Purpose

Catch defects and maintenance costs before merge, and resolve feedback quickly without losing technical accuracy.

## Inputs needed

- The change (pull request or diff), its description and any linked spec or ticket.
- Ability to check out the branch and run its tests.
- The team's review conventions: size limits, required approvals, who owns which area.
- For the author: all review comments, and the CI status of the latest commit.

## Steps

### Reviewing

1. Read the description and the linked spec first. State the intent of the change in one sentence. If you cannot, the first comment asks for a better description.
2. Check the size. Above about 400 changed lines (excluding generated files and lockfiles), ask for a split unless the change is mechanical.
3. Review in this order and stop to comment at the first layer that fails: intent and behavior, tests, failure handling and data safety, security and privacy, public interfaces and compatibility, readability, style. Skip style rules that a linter already enforces.
4. Run it. Check out the branch, run the tests, and exercise the changed path by hand when it is user-facing. Read the callers of any changed function, not only the diff.
5. Label every comment `blocker`, `suggestion`, `question` or `nit`. A blocker is a correctness, security, data-loss or contract problem. An unlabelled comment forces the author to guess.
6. Write each blocker as a scenario: input, actual outcome, expected outcome, plus a fix or a test that shows it. "This looks wrong" is not a comment.
7. Cap nits at five per review. If a pattern repeats, say so once and propose a lint rule.
8. Give a verdict: approve (no blockers), request changes (one or more blockers) or comment. List the files and areas you did not review. Respond within one working day.

### Responding

9. Read every comment before changing code. Group them by theme and by file.
10. For each comment choose one: fix it, explain with evidence, or defer with a ticket link. Disagreement needs evidence such as a test, a benchmark or a documentation link, not preference.
11. Fix blockers first. Reply in each thread with the commit hash that addresses it. Leave resolving the thread to the reviewer unless the team's rule says otherwise.
12. Keep unrelated changes out of the review round. Push fixes as new commits so the reviewer can see only what changed.
13. If a comment is unclear, ask one specific question instead of guessing.
14. Run the tests and linters, then request re-review with a short list of what changed since the last round.
15. After two rounds without agreement, move to a call or name a tie-breaker, and write the decision in the thread.

## Output

As reviewer, return a summary (verdict, tests run and their result, areas not reviewed) followed by comments grouped by file, each with one of the four labels; every blocker states its failing scenario and a fix or a test. As author, return one reply per thread that cites a commit or evidence, then a re-review request listing the changes since the last round. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] Every review comment carries one of the four labels.
- [ ] Every blocker states a failing scenario and a fix or a test.
- [ ] The reviewer ran the tests locally and recorded the result in the summary.
- [ ] The summary lists the verdict and the files or areas not reviewed.
- [ ] Every thread has a reply that cites a commit or evidence.
- [ ] No blocker is open and CI is green on the latest commit.
- [ ] Re-review was requested with a list of changes since the last round.

## Failure modes

- **Rubber stamp.** Approval in minutes on a change of hundreds of lines. Run the code and trace one path end to end.
- **Style-only review.** Naming and spacing get attention while a missing transaction passes. Follow the order in step 3.
- **Diff-only reading.** The bug is in a caller that the diff does not show. Read call sites.
- **Preference as blocker.** Blocking on taste stalls delivery. Label it `suggestion`.
- **Defensive replies.** Arguing without evidence. Either supply the evidence or apply the change.
- **Applying every suggestion blindly.** A suggestion can be wrong. Verify it before applying.
- **Review scope creep.** Requesting unrelated cleanups. File a ticket instead.
- **Stale approval.** Commits were pushed after approval. Re-review the new commits.

## When to stop and ask

- The change touches authentication, cryptography, payments or other sensitive code and you are not its owner. Pull in the owner.
- You find a defect that predates the change. File it separately and do not block on it.
- The change contradicts the spec or a recorded design decision.
- Two rounds of discussion did not resolve a disagreement.
- The change is too large to review in one sitting and the author cannot split it.
