# Trigger tests: Engineering Workflow Skills

Agensi's pre-publish rule: a skill triggers on its relevant prompts and not on unrelated ones. For a pack, the agent picks
one skill by name and description, so each prompt below must load the skill named beside it, and no other.

Status: **not yet run in an agent.** Run each prompt in a fresh session with the pack installed and tick the box when the
right skill loads. Run again after a model update.

## Should trigger (two prompts per skill)

| Skill | Prompt 1 | Prompt 2 |
|---|---|---|
| `clarify-requirements` | [ ] Add export to the app | [ ] What does 'done' mean for the export feature? I only have a one-line ask |
| `write-feature-spec` | [ ] Write a spec for CSV export | [ ] Turn this idea into a spec an engineer can build from |
| `break-down-tasks` | [ ] Split this spec into tasks | [ ] Plan the work for this feature in small steps |
| `design-http-api` | [ ] Design the REST API for invoices | [ ] Review my OpenAPI file before clients depend on it |
| `plan-database-migration` | [ ] Plan splitting the users.name column without downtime | [ ] How do I add a NOT NULL column to a big live table safely? |
| `test-first-change` | [ ] Add a discount rule, test first | [ ] Fix this bug and add a regression test |
| `refactor-without-behavior-change` | [ ] Refactor this module without changing behaviour | [ ] Extract this class safely |
| `debug-from-evidence` | [ ] This test fails one run in ten, find out why | [ ] Production returns 500 on some requests, find the cause |
| `investigate-performance` | [ ] The search endpoint is slow, find out why | [ ] This page takes 4 seconds to load, make it faster with proof |
| `give-and-receive-code-review` | [ ] Review my PR like a senior engineer | [ ] Reply to these review comments |
| `review-security-surface` | [ ] Security review of this change | [ ] Check this endpoint for injection and auth holes |
| `release-with-rollback` | [ ] Plan the release with a rollback | [ ] Ship this to production in stages |
| `write-incident-postmortem` | [ ] Write the postmortem for last night's outage | [ ] Blameless review of this incident |
| `write-technical-docs` | [ ] Write a setup guide for new developers | [ ] Document how to deploy this service |

## Should not trigger any skill

- [ ] Explain what a closure is
- [ ] Write a function that parses dates
- [ ] What is the capital of France?
- [ ] Translate this paragraph to Spanish
- [ ] Write a poem about the sea
- [ ] Help me pick a laptop
- [ ] Summarise this article
- [ ] What is 17 times 23?
