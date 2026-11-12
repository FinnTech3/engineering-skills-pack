# Lock levels for common schema changes

Behavior depends on engine and version. Treat this table as a starting point and confirm
each row against the documentation for the exact version you run, then rehearse on a copy.

## PostgreSQL

| Change | What happens | Safer path |
|---|---|---|
| Add a nullable column, no default | Metadata change. Brief `ACCESS EXCLUSIVE` lock. | Use as is, with a lock timeout. |
| Add a column with a constant default | Metadata only on version 11 and later. Rewrites the table on older versions. | Check your version. On old versions add the column, then backfill in batches. |
| Add a column with a volatile default | Full table rewrite under `ACCESS EXCLUSIVE`. | Add the column without a default, backfill in batches, then set the default. |
| Change a column type | Usually a full rewrite under `ACCESS EXCLUSIVE`. Some binary-compatible changes skip the rewrite. | Add a new column, dual-write, backfill, switch reads, drop the old one. |
| `SET NOT NULL` | Scans the table under `ACCESS EXCLUSIVE`. | Add `CHECK (col IS NOT NULL) NOT VALID`, run `VALIDATE CONSTRAINT`, then `SET NOT NULL` (version 12 and later skip the scan), then drop the check. |
| Add a `CHECK` constraint | Scans the table under `ACCESS EXCLUSIVE`. | Add it `NOT VALID`, then `VALIDATE CONSTRAINT` separately. |
| Add a foreign key | Locks both tables while it validates. | Add it `NOT VALID`, then validate separately. |
| `CREATE INDEX` | Blocks writes for the duration of the build. | `CREATE INDEX CONCURRENTLY`. It cannot run in a transaction block, and a failed build leaves an invalid index to drop and retry. |
| Add a unique constraint | Builds an index and blocks writes. | Build a unique index concurrently, then `ADD CONSTRAINT ... USING INDEX`. |
| `DROP INDEX` | Takes `ACCESS EXCLUSIVE` on the table. | `DROP INDEX CONCURRENTLY`. |
| Rename a column or table | Instant, but old application versions break. | Expand and contract: add new, migrate, drop old. |
| Drop a column | Instant, and space is reclaimed later, but code that reads it breaks. | Remove all readers first, then drop in a separate release. |

A statement that needs `ACCESS EXCLUSIVE` queues behind any open transaction that touched the table,
and every query that arrives after it queues behind the statement. Set `lock_timeout` and retry.

## MySQL 8.0 (InnoDB)

| Change | What happens | Safer path |
|---|---|---|
| Add a column | `ALGORITHM=INSTANT` for most cases on 8.0.12 and later. | Name the algorithm so the statement fails instead of falling back to a copy. |
| Add a secondary index | In place, with concurrent writes allowed. | `ALGORITHM=INPLACE, LOCK=NONE`. |
| Change a column type | Usually a table copy that blocks writes. | Add a new column and backfill, or use an online schema-change tool. |
| Drop a column | In place table rebuild, or instant on 8.0.29 and later. | Remove readers first. |
| Rename a column | Metadata change, but application versions must agree. | Expand and contract. |

Always write `ALGORITHM=` and `LOCK=` explicitly. If the server cannot honor them it raises an error,
which is better than a silent copy of a large table.
