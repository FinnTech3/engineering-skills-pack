# Postmortem: <short title>

- **Date of incident:** <YYYY-MM-DD>
- **Severity:** <level>
- **Author:** <name>
- **Reviewers:** <names>
- **Status:** Draft | In review | Published

## Summary

<At most five lines: what broke, who was affected, how long, how it was resolved.>

## Impact

- **Affected:** <users, requests or orders, with counts>
- **Duration:** <start to end in UTC, with the source of each time>
- **Error rate or degradation:** <peak and average>
- **Data loss:** <none | describe>
- **Error budget spent:** <percent of the period's budget>

## Timeline (UTC)

| Time | Event | Source |
|---|---|---|
| <hh:mm> | <what happened> | <link to graph, log or message> |

Time to detect: <minutes>. Time to mitigate: <minutes>. Time to resolve: <minutes>.

## Contributing factors

1. **Trigger:** <what started it>
2. **Condition that allowed it:** <why the trigger could cause this outcome>
3. **Detection gap:** <why it was noticed when it was>
4. **Mitigation gap:** <why recovery took as long as it did>

## What went well

- <fact with a number where possible>

## Action items

| Action | Type | Owner | Due | Ticket | Done when |
|---|---|---|---|---|---|
| <specific change> | prevent / detect / mitigate | <name> | <date> | <link> | <check anyone can run> |

## Evidence

- <links or exports: dashboards, logs, deploy history, chat transcript>
