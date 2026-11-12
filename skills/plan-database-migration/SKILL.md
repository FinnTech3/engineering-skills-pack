---
name: plan-database-migration
description: >
  Use when the user asks to "add a column", "rename a table", "backfill this
  data", "add an index" or "plan this migration" on a live database. Do not use
  for disposable development databases, ORM model edits with no schema effect,
  or read-only queries.
---

# Plan a database migration

## Purpose

Change a live schema or its data in reversible steps, with measured lock time and a tested rollback.

## Inputs needed

- The exact change and the reason for it.
- Database engine and version, table sizes in rows and bytes, write rate and peak queries per second.
- Replica lag baseline and the longest transaction that normally runs.
- Every reader and writer of the table: services, jobs, reports, exports.
- The deploy process: is rollout rolling, and can an old version run beside a new one.
- A recent backup and the time its restore takes.

## Steps

1. Classify the change: additive (new nullable column or table), constraint-adding, destructive (drop, rename, retype) or data backfill. A destructive change uses expand, migrate, contract across at least two releases.
2. Look up the lock each statement takes on your engine and version (start with [lock levels](references/lock-levels.md)). Write the lock and the expected hold time next to each statement.
3. Write the compatibility matrix with two rows: old application on new schema, and new application on old schema. Both must work, because deploys roll and rollbacks happen. If either row fails, split the migration.
4. Plan the phases. Expand: add the new column, table or index without blocking writes. Dual-write: the application writes both forms. Backfill: copy existing data in batches. Verify. Switch reads. Stop writing the old form. Contract: drop the old form in a later release, after metrics show zero reads of it.
5. Write each DDL step as its own migration. Set a lock timeout (for example 3 seconds) and retry on timeout, so a waiting statement cannot queue every other query behind it. Build indexes with the engine's non-blocking option and outside a transaction where required.
6. Write the backfill as a resumable job: batches of 1,000 to 5,000 rows by primary key range, a pause between batches, a stop when replica lag passes your threshold (for example 5 seconds), progress stored by last key, and a condition that makes reruns harmless (`WHERE new_col IS NULL`). Never run it inside the schema migration transaction.
7. Add constraints in two stages: create them unvalidated, then validate in a separate statement that does not block writes. Where the engine lacks that, count violations first and require zero.
8. Rehearse on a copy with production-scale row counts. Record duration, longest lock wait and peak replica lag. Compare against your thresholds before touching production.
9. Write a rollback for each step: the command, the data it would lose, and its duration. For the contract step the rollback is a restore, so take a snapshot and test the restore first.
10. Write verification queries and save their output before and after each phase: row counts per side, a checksum or a sample of at least 1,000 rows compared old to new, and zero nulls where a value is now required.
11. Decide abort thresholds before starting, for example lock wait over 5 seconds, replica lag over 30 seconds, error rate up by 1 percentage point. Watch those dashboards while each step runs.
12. Run the contract step as its own change, in a later release, after the observation period ends.

### Example: guarded DDL and one backfill batch (PostgreSQL)

```sql
SET lock_timeout = '3s';
ALTER TABLE orders ADD COLUMN total_cents bigint;   -- retry on timeout

-- one rerunnable batch; record :last_id, check replica lag, pause, repeat
UPDATE orders SET total_cents = (total * 100)::bigint
WHERE id > :last_id AND id <= :last_id + 5000 AND total_cents IS NULL;
```

## Output

Return the migration plan in this order: the compatibility matrix; the steps, each with its statement, lock, expected hold time and rollback; the rehearsal numbers; the verification queries with their results; the abort thresholds and who watches them; and the dated ticket for the contract step. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] The compatibility matrix is written and both rows were exercised in a test.
- [ ] Each statement lists its lock and expected hold time, and the rehearsal's longest lock wait is under the abort threshold.
- [ ] Every step has a written rollback, and the restore from snapshot was tested.
- [ ] Verification queries show equal counts and 0 mismatches in the compared sample.
- [ ] The migration and the backfill can be rerun without error and without duplicate effects.
- [ ] Abort thresholds are written down and a person is assigned to watch them.
- [ ] A dated ticket exists for the contract step.

## Failure modes

- **Rewrite under a lock.** A type change or a volatile default rewrites the whole table while writes wait. Check the lock table for your version.
- **Index build blocks writes.** The default build takes a lock that stops writes. Use the non-blocking form.
- **Lock queue pile-up.** A short statement waits behind a long transaction and everything queues behind it. Use a lock timeout and retry.
- **Backfill saturates the database.** Large batches without pauses raise replica lag and slow production. Batch, pause and throttle.
- **Rename in one release.** Old instances still use the old name during rollout and fail. Add, migrate, then drop.
- **Dropping a column something still reads.** Nightly jobs, exports and dashboards often do. Check query logs for reads before the contract step.
- **Migrations racing at startup.** Several instances run the same migration at boot. Run migrations as a single separate job.
- **Tested on an empty database.** Timing and locks look fine until production size. Rehearse at scale.

## When to stop and ask

- The table has tens of millions of rows and you cannot confirm how your engine locks for this statement.
- A step loses data and no restore has been tested.
- The change needs an exclusive lock and no maintenance window exists.
- Another team's jobs or reports read the table and you cannot find their owners.
- The data moves between regions or systems with different compliance rules.
