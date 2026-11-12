---
name: design-http-api
description: >
  Use when the user asks to "design an API", "add an endpoint", "review this
  OpenAPI spec", "add pagination" or "design the webhook", for an HTTP or JSON
  API that other programs depend on. Do not use for internal function
  signatures, GraphQL or RPC schema design, or user-interface work.
---

# Design an HTTP API

## Purpose

Define an HTTP contract that clients can depend on, and prove with checks that later changes do not break it.

## Inputs needed

- The use cases and the confirmed requirements (see `write-feature-spec`).
- The list of consumers: browsers, mobile apps, partners, internal services, and how fast each can upgrade.
- The existing API description (OpenAPI or similar) and the naming and error conventions already in use.
- The authentication model and the tenancy model.

## Steps

1. List the consumers and their upgrade speed. A contract change is judged against the slowest consumer, not the one you are building for.
2. Model resources as nouns with stable identifiers. Write an operation table: method, path, purpose, idempotent or not, required permission. Use a verb in the path only for a real action, such as `POST /orders/{id}/cancel`.
3. Write the request and response schemas before any handler code. For every field give type, required or optional, nullable or not, allowed values, and size or range limits. Use RFC 3339 timestamps in UTC. Send money as an integer in minor units with a currency code.
4. Fix the status code for each outcome and write it in a table: 200, 201 with `Location`, 204, 400 for malformed input, 422 for well-formed but invalid input (choose one convention and document it), 401, 403, 404, 409, 412 or 428 for preconditions, 429 with `Retry-After`. Never return 200 with an error body.
5. Use one error envelope for every endpoint, for example `{"error": {"code": "token_expired", "message": "...", "details": [], "request_id": "..."}}`. The `code` values are part of the contract; messages are not.
6. Define idempotency. `PUT` and `DELETE` must be idempotent. A `POST` that creates something with a cost (a payment, an email) accepts an `Idempotency-Key` header, stores the key with the response for at least 24 hours, and rejects a reused key with a different body.
7. Define list behavior: cursor pagination with an opaque cursor, a default and a maximum page size (for example 50 and 200), a stable sort with a unique tiebreaker, and an allow-list of filter fields.
8. Write the evolution rules. Adding an optional field or response field is compatible. Removing, renaming, retyping or tightening validation is breaking and needs a new version or a deprecation period with `Deprecation` and `Sunset` headers. Pick one versioning scheme and document it.
9. Set limits and publish them: request size, rate per key, timeouts, maximum page size.
10. Apply security defaults: authorize against the specific object, not only the route; keep secrets and personal data out of URLs; use an explicit CORS allow-list; choose one policy for 403 versus 404 so existence is not leaked.
11. Add contract tests that validate every example against its schema, and a compatibility check in CI that diffs the new description against the last released one.
12. For each endpoint, write a working command-line request example and a failing one. Run both against a real instance.

### Example: idempotent create

```
POST /v1/payments        Idempotency-Key: 6f1c2a3e
  -> 201 Created         Location: /v1/payments/pay_123
Same key, same body      -> 201 with the stored response, no second charge
Same key, different body -> 422 {"error": {"code": "idempotency_key_reused", ...}}
```

## Output

Return the API description file and a short design note: the operations, the error responses for each, the pagination and idempotency rules, the result of the compatibility check, and each request example with the response you observed. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] The schema file validates with a linter and is the source of the examples.
- [ ] Every operation lists its success response and at least 3 error responses.
- [ ] The compatibility check against the last release reports no breaking change, or an approver is named.
- [ ] A test requests page size max plus 1 and gets the documented result.
- [ ] A test sends the same `Idempotency-Key` twice and shows exactly one side effect.
- [ ] A test asks for another tenant's object and gets the documented 403 or 404.
- [ ] Every documented request example ran against a live instance and matched.

## Failure modes

- **Leaking the database schema.** Column names and join tables become the contract and cannot change. Design for consumers.
- **200 with an error inside.** Clients and proxies treat it as success. Use status codes.
- **Unbounded lists.** One large tenant takes the service down. Always page.
- **Closed enums.** Adding a value later breaks clients that switch on them. Tell clients to tolerate unknown values from day one.
- **Undefined `PATCH`.** State whether it follows JSON Merge Patch and how null is handled.
- **Mixed naming.** `userId` in one place and `user_id` in another. Pick one case style for the whole API.
- **Breaking change disguised as a fix.** Clients depend on observed behavior, such as field order or error text. Treat visible behavior changes as contract changes.
- **Error text as API.** Clients parse messages. Give them `code` and keep messages free to change.

## When to stop and ask

- The change breaks a consumer you cannot contact or cannot make upgrade.
- The authentication or tenancy model is not defined.
- An endpoint exposes personal, financial or regulated data that no one has classified.
- You need a new versioning scheme or a new error envelope.
- Expected payload sizes or request rates are unknown and could affect capacity.
