---
name: clarify-requirements
description: >
  Use when the user gives a vague request such as "make it better", "add export"
  or "support teams", or asks "what are we actually building" or "what should I
  ask first". Produces confirmed facts, labelled assumptions and at most five
  blocking questions. Do not use when the request already has testable
  acceptance criteria, for a bug with a reproduction, or for slowness (use
  investigate-performance).
---

# Clarify requirements

## Purpose

Turn a vague request into confirmed facts, labelled assumptions and at most five blocking questions.
The result is a one-page requirements note that a spec or an implementation can start from.

## Inputs needed

- The original request, word for word.
- Read access to the repository, its history and any linked tickets or docs.
- A named person who can answer questions. If nobody can, the note stays a draft.

## Steps

1. Copy the request verbatim to the top of a new note. Do not paraphrase it until step 8.
2. Search before asking. Read the code, tickets and docs for the feature area and record each fact with its source (`path:line` or link). A question the repository can answer is never sent to a person.
3. Finish this sentence with a user outcome or a number: "This is done when ___, so that ___". If you cannot, that is question 1.
4. List the unknowns under six headings and tag each one `confirmed`, `assumed` or `blocking`:
   - **Who:** users, roles, permissions.
   - **What:** inputs, outputs, states, formats.
   - **How much:** volume, latency, data size, growth.
   - **Boundaries:** what is explicitly not included.
   - **Constraints:** deadline, compatibility, legal or compliance rules.
   - **Proof:** how a reviewer will observe that it works.
5. Estimate the cost of a wrong guess for each unknown, in hours of rework or in irreversible effects. Keep as `blocking` only the unknowns where a wrong guess costs more than about one hour or cannot be undone. Everything else becomes a written assumption.
6. Write each blocking question so it can be answered in one line. Give two or three concrete options and put your recommended default first, for example: "Deleting an account: soft-delete with 30-day restore (default), hard delete, or archive flag?"
7. Send all questions in one batch, at most five. While waiting, work only on parts that do not depend on the answers.
8. When answers arrive, rewrite the note: confirmed facts, remaining assumptions (each with the owner and what changes if it is wrong), the out-of-scope list, and at least three acceptance examples written as input and expected output. One example must be an error or empty case.
9. Read the note back to the requester in ten lines or fewer and ask for an explicit yes.

## Output

Return the one-page requirements note in this order: the original request quoted verbatim, the "done when ... so that ..." sentence, confirmed facts, labelled assumptions, blocking questions (five at most), acceptance examples, and the out-of-scope list. Mark it DRAFT until the requester confirms it. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] The original request is quoted verbatim.
- [ ] The "done when ... so that ..." sentence names a user outcome or a number.
- [ ] Every unknown is tagged; zero are untagged.
- [ ] No blocking question is open, or work is explicitly limited to the unblocked part.
- [ ] At least 3 acceptance examples exist, and at least 1 covers an error or empty input.
- [ ] The out-of-scope list has at least 1 entry.
- [ ] The requester confirmed the summary in writing, or the note is marked DRAFT and lists every assumption.

## Failure modes

- **Interrogation.** More than five questions at once, so the requester stops answering. Rank by cost of a wrong guess and turn the rest into assumptions.
- **Asking what the code already says.** Wastes the requester's time and shows the repository was not read. Do step 2 first.
- **Open questions.** "What do you want?" gets a shrug. Offer options with a default.
- **Solution smuggling.** The request is a mechanism ("add a cron job") rather than a need. Ask what outcome the mechanism is for before accepting it.
- **Silent assumptions.** An assumption that never reaches the requester surfaces during review as a defect. Every assumption goes in the note.
- **Scope drift through answers.** Each answer adds a feature. Compare the note with the original request and list additions separately.
- **Silence read as yes.** No reply is not agreement. Mark the note DRAFT and proceed only on unblocked work.

## When to stop and ask

- Two stakeholders give conflicting answers. Ask who owns the decision instead of choosing.
- An answer implies deleting data, changing billing, changing permissions or a compliance duty that the request never mentioned.
- After two rounds the goal still has no measurable form.
- The work you now estimate is more than five times what the request implied.
