---
name: write-technical-docs
description: >
  Use when the user asks to "write a README", "document this", "write a
  runbook", "write a how-to" or "write a setup guide" that other people will
  follow. Do not use for inline code comments alone, marketing copy, or
  generated API reference, a feature spec (use write-feature-spec) or an
  incident write-up (use write-incident-postmortem).
---

# Write technical docs

## Purpose

Write a document a named reader can follow to finish one task, with every command checked against the running system.

## Inputs needed

- The reader and the task they are trying to complete, in one sentence.
- Access to the system, or to a safe copy, so every command can be run.
- The code, configuration and existing docs for the area.
- The place where docs live in this repository and who owns them.

## Steps

1. Write the reader and task sentence first: "An on-call engineer at 3 a.m. restarting the ingest worker." One document serves one reader and one task.
2. Pick the document type and stay inside it: tutorial (learn by doing), how-to (finish a task), reference (look up a fact) or explanation (understand why). If the content spans types, write separate pages and link them.
3. Collect facts from the running system, not from memory. Run each command, copy real output, and read the code for defaults and limits. Tag anything you could not check as `UNVERIFIED` and resolve every tag before publishing.
4. Outline before writing: a title that names the task as a verb phrase, a one-sentence summary, prerequisites, numbered steps, the expected result, troubleshooting, and links to related pages.
5. Write steps as imperatives with one action each, the exact command, and the output the reader should see. Add the failure branch: "If the command prints `connection refused`, check that the worker is running with ...".
6. Define each term where it first appears. Use one word per concept throughout. Keep sentences under 25 words. Spell out acronyms once.
7. Make examples complete and copy-pasteable, with inputs and outputs shown. Run them in CI where practical, for example as doctests or a script.
8. For a decision record, write context, the options considered (at least two), the decision, the consequences including the negative ones, the status and the date. Never edit an accepted record; write a new one that supersedes it.
9. Test the document: have someone unfamiliar with the system follow it word for word in a clean environment. Note each point of confusion and each deviation. Fix the document, not the reader. If no such person is available, say so in the verification note and mark that exit criterion not met; do not claim it.
10. Run the link checker and spell checker. Add the page to the docs index or navigation. Name an owner in the file header or in the ownership file.
11. Keep the document next to the code it describes and add "update the docs" to the pull request checklist. Delete pages that are no longer true.

## Output

Return the finished document, then a verification note: the reader-and-task sentence, the date or version each command was checked against, the link-check result, what the test reader stumbled on and how you fixed it, and the page's owner and index link. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] The reader and task sentence is the first line of the draft notes and matches the title.
- [ ] Every command was executed and the date or version of the check is recorded.
- [ ] `grep -c UNVERIFIED <file>` prints 0.
- [ ] One unfamiliar person completed the task from the document alone, and every deviation was fixed.
- [ ] The link checker reports 0 broken links.
- [ ] The page is linked from an index and has a named owner.
- [ ] No section runs longer than about 40 lines without a heading.

## Failure modes

- **Describing the implementation instead of the task.** The reader wants to restart a worker, not learn its class hierarchy. Start from the task.
- **Examples that were never run.** They drift or never worked. Execute them.
- **Screenshots of text.** They cannot be searched, copied or updated. Use text blocks.
- **Assumed context.** The page uses a term defined three pages away. Define terms where they appear or link to the definition.
- **Passive voice hiding the actor.** "The service is restarted" does not say who restarts it. Say who.
- **Duplicated content.** The same procedure in three places diverges. Write it once and link.
- **Documentation written from memory after launch.** Details are wrong in ways nobody notices. Write from the live system.
- **"See the code."** Not documentation. State the behavior or link to the exact function.

## When to stop and ask

- A claim cannot be verified because you cannot reach the system. Ask the owner; do not guess.
- The code and the existing docs disagree. Ask which one reflects the intended behavior.
- The document would reveal secrets, internal hostnames or customer data in a public place.
- The audience is not known.
- No one owns the system the document describes.
