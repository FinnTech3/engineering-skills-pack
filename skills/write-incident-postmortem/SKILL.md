---
name: write-incident-postmortem
description: >
  Use when the user asks to "write the postmortem", "write up the outage", "do a
  blameless review" or "document what happened in the incident", after it is
  mitigated. Do not use during live incident response (mitigate first), or to
  judge an individual's performance.
---

# Write an incident postmortem

## Purpose

Record what happened, why the system allowed it, and which checkable actions will prevent a repeat, without blame.

## Inputs needed

- The incident ticket and the chat or call transcript.
- Alerts, dashboards, deploy and flag change logs for the incident window.
- Customer reports and support tickets.
- Names of the responders, who can correct the facts.
- The team's severity definitions and its detection and mitigation time targets.

## Steps

1. Start within two business days of resolution. Assign one author and, where possible, a facilitator who was not the main responder. Set the draft due date at no more than five business days.
2. Collect evidence before writing any narrative: alerts, graphs, deploy history, flag changes, transcripts, commands that were run. Save exports or permanent links, because logs expire.
3. Build the timeline in UTC from system timestamps, not memory. Entries: first trigger, first signal, detection, first response, each mitigation attempt (what, who, effect), resolution. Cite the source for each entry. Compute time to detect, time to mitigate and time to resolve.
4. Quantify impact: affected users or requests, error percentage, duration, money, whether data was lost, and how much of the service-level objective's error budget was spent.
5. Ask "why" repeatedly until you reach a system or process condition that can be changed. "The engineer forgot" is a stopping signal: ask why the system let a forgotten step cause an outage. Separate the trigger, the conditions that made it possible, why detection was slow and why mitigation was slow. Expect at least three contributing factors.
6. Record what worked, as facts: "the alert fired within 2 minutes", "rollback took 6 minutes".
7. Write action items. Each has one named owner, a due date, a ticket link, a type (prevent, detect or mitigate) and a done condition anyone can check, such as "alert X exists and fired during a test". Keep to at most eight, ranked by risk reduction. If time to detect or mitigate missed its target, include at least one detect or mitigate item. Reject "be more careful" and "improve monitoring".
8. Circulate to the responders for factual corrections for 48 hours, then to a wider audience. For incidents at or above your review severity, hold a review of at most 45 minutes. Describe actions and system states, not character.
9. Publish where people search for it, link it from the incident ticket, tag it by system and cause class, and put a summary of at most five lines at the top. Use [the template](references/template.md) for structure.
10. Track action items weekly until each is closed. If the same cause returns, reopen the postmortem.

## Output

Return the postmortem in the layout of `references/template.md`: summary, quantified impact, the UTC timeline with sources, the detect, mitigate and resolve times, contributing factors, and the action-item table with owner, due date, ticket and done condition. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] Every timeline entry has a UTC timestamp and a cited source.
- [ ] Time to detect, time to mitigate and time to resolve are stated as numbers.
- [ ] Impact is quantified in at least users or requests, and duration.
- [ ] At least 3 contributing factors are listed, or the text explains why fewer apply.
- [ ] Every action item has owner, due date, ticket and a checkable done condition.
- [ ] No sentence in the causes names a person as the cause.
- [ ] Responders confirmed the facts, and the document is published and linked from the incident ticket.
- [ ] The action items are in the owning team's backlog with dates.

## Failure modes

- **Blame in disguise.** "Human error" as the root cause ends the analysis. Ask what made the error easy to make and hard to notice.
- **Timeline from memory.** Memory reorders events and shifts blame. Use logs and chat timestamps.
- **Unverifiable actions.** "Improve alerting" cannot be checked. State the alert and the test.
- **Action item flood.** Thirty items and none completed. Keep the few that cut the most risk.
- **Only the trigger examined.** The deploy that started it is the easy part. Look at detection time and recovery time too.
- **Hindsight bias.** "They should have known." Describe what information was available at that moment.
- **Skipping near misses.** They are cheap lessons. Write a short version for them.
- **Nobody reads it.** Written for management in vague terms. Write for the engineers who will face the same system.

## When to stop and ask

- The incident involves a breach, legal exposure or customer data disclosure. Involve security and legal before circulating anything.
- An individual's conduct appears to be at issue. Route that to their manager separately from the postmortem.
- Accounts of the incident conflict and logs cannot settle it.
- A statement to customers is needed. The communications owner writes it.
- No one can be named as owner for a high-value action item.
