# Engineering Workflow Skills

Fourteen workflow skills that make an AI coding agent work like a careful senior engineer: clarify first, plan in small steps, prove each change, and ship with a way back.

Each skill gives the agent numbered steps, a defined output, exit criteria it can check, the common ways the work goes wrong, and the points where it must stop and ask you.

## The skills

| Phase | Skill | Use it when |
|---|---|---|
| Define | `clarify-requirements` | A request is vague and you need facts, assumptions and the few questions that block work |
| Define | `write-feature-spec` | A change needs a spec another engineer can build and test from |
| Plan | `break-down-tasks` | A spec must be split into small, ordered, verifiable tasks |
| Build | `design-http-api` | You are adding or changing an HTTP API that clients depend on |
| Build | `plan-database-migration` | A live schema or its data must change without downtime |
| Build | `test-first-change` | You are adding behaviour or fixing a bug whose cause is known |
| Build | `refactor-without-behavior-change` | Code needs restructuring and behaviour must stay the same |
| Verify | `debug-from-evidence` | Something fails and the cause is unknown |
| Verify | `investigate-performance` | Something is slow and you need a measured fix |
| Review | `give-and-receive-code-review` | You are reviewing a change, or answering a review |
| Review | `review-security-surface` | A change touches input handling, auth, secrets or dependencies |
| Ship | `release-with-rollback` | A change goes to production in stages with abort thresholds |
| Operate | `write-incident-postmortem` | An incident is over and you need a blameless record with real actions |
| Any stage | `write-technical-docs` | Someone must be able to finish a task from a document alone |

## How to use it

Ask your agent for the job in your own words, such as "debug this failing test", "plan this migration" or "review my PR". The agent picks the matching skill from its description.

## What it needs

Nothing to install. The skills are instructions. They ask the agent to use tools your project already has, such as git, your test runner and your linter. They never ask for credentials.

## Limits

These are process skills. They do not know your stack's conventions, so the agent still reads your code and config first. They do not replace human approval for releases, migrations or security decisions, and each skill says when the agent must stop and ask.
