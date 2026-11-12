---
name: release-with-rollback
description: >
  Use when the user asks to "ship this", "deploy to production", "plan the
  release", "roll this out gradually" or "how do we roll back", for a change
  users would notice failing. Do not use for local or throwaway environments, or
  for documentation-only changes.
---

# Release with rollback

## Purpose

Ship a change in stages with pre-agreed abort thresholds, and be able to reverse it within a stated time.

## Inputs needed

- The commit range to ship, with its flags, migrations, configuration and infrastructure changes.
- CI status for the exact commit and the list of environments.
- Baseline production metrics: error rate, p95 latency, saturation and one business metric.
- Who is on call, who can approve, and any freeze window.
- The rollback command or procedure for the current deploy system.

## Steps

1. Freeze the scope: list every pull request, flag, migration, config change and dependency change in the release. Anything not on the list does not ship. Build the artifact once and record its digest or tag; promote that same artifact through every environment.
2. Classify risk. Low: configuration or copy. Medium: new code paths behind a flag. High: migrations, authentication, billing, data model or protocol changes. High risk requires the staged rollout in step 6.
3. Check preconditions: CI is green on the exact commit, migrations are already applied in a compatible form (see `plan-database-migration`), release notes are written, on-call knows, no other release is in flight, and the change is not scheduled for a time when nobody can respond.
4. Write the rollback plan before deploying: the exact command, who runs it, the expected duration, and whether data written by the new version can be read by the old one. If the change is irreversible, write the forward-fix plan and get explicit approval.
5. Write the abort thresholds before deploying, with baselines beside them. Examples: error rate above baseline by 1 percentage point for 5 minutes, p95 above baseline by 20%, one business metric down 10%, any crash loop.
6. Roll out in stages: 1 to 5% (one instance or region), hold for at least one full cycle of the traffic that exercises the change (at least 15 minutes), then 25%, 50% and 100%. Compare each stage with baseline and with the untouched group. Ramp feature flags as a separate step from the code deploy.
7. After each stage run scripted smoke checks on the critical paths: sign-in, a core read, a core write, and a payment in sandbox if it applies. Record pass or fail.
8. If any threshold is crossed, roll back first and diagnose afterwards. Do not debug live inside a bad deploy. Announce the rollback in the team channel.
9. Hold at 100% for the agreed bake time (at least one hour). Then remove temporary flags, with a ticket and date, publish release notes, tag the release and update docs.
10. For a library or package: choose the version by semantic versioning (a breaking change is a major version), inspect the built artifact's contents, install it in a clean environment and import it, test an upgrade from the previous release, and document that a published version cannot be unpublished, so rollback means yanking it and publishing a fix.
11. Record the actual timeline, every manual step and every surprise for the next release.

### Example abort thresholds

```
Abort if any line holds for 5 minutes during a stage:
  HTTP 5xx rate       above baseline + 1 percentage point   (baseline 0.2%)
  p95 latency         above baseline x 1.20                 (baseline 310 ms)
  checkouts per min   below baseline x 0.90                 (baseline 42)
  pod restarts        any new crash loop
Rollback: redeploy the previous artifact tag, about 4 minutes, run by the on-call engineer.
```

## Output

Return a release record: the artifact digest or tag, the rollback plan (executor, duration, when it was last exercised), the log of each stage with its metrics against the abort thresholds, the smoke-check results, the decision (completed or rolled back) with its reason, and links to the release notes and the flag cleanup ticket. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] The artifact digest or tag is recorded and identical in every environment.
- [ ] The rollback plan names the executor and the duration, and was exercised within the last 90 days or in staging for this release.
- [ ] Baselines and abort thresholds were captured before the first stage.
- [ ] Metrics at every stage are logged and none crossed a threshold, or the release was rolled back.
- [ ] Smoke checks passed at 100%.
- [ ] No alert attributable to the release fired during the bake time.
- [ ] Release notes are published and a flag cleanup ticket has a date.

## Failure modes

- **Rebuild between environments.** What was tested is not what shipped. Promote one artifact.
- **Rollback equals "revert the commit".** The migration cannot be reversed, so the revert fails. Write the real procedure and test it.
- **Code and migration in one step.** An old version cannot run against the new schema. Ship the expand step first.
- **No baseline.** A number without a comparison proves nothing. Capture it beforehand.
- **Watching only errors.** A bug that breaks checkout without raising errors needs a business metric.
- **Canary too small.** 1% of a quiet hour produces no signal. Size the stage and the hold time to the traffic.
- **Roll forward under pressure.** Teams improvise a fix on production. Roll back unless a forward fix was planned and approved.
- **Flags that never leave.** Every flag left behind doubles a code path. Date each one.
- **Overlapping releases.** Two changes in flight make a regression impossible to attribute.

## When to stop and ask

- The change cannot be rolled back and no forward-fix plan exists.
- The error budget is spent or a freeze is in effect.
- Nobody on call can respond during the rollout.
- Abort thresholds or baselines are missing and nobody can supply them.
- A dependent service has not deployed the version this change needs.
- Legal, security or compliance sign-off is required and not recorded.
