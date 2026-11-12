---
name: review-security-surface
description: >
  Use when the user asks for a "security review", "check this for
  vulnerabilities", "is this endpoint safe" or "audit the auth code", on a
  change touching input handling, authentication, secrets, file or network
  access or dependencies. Do not use for a full penetration test, a compliance
  audit, or changes that cross no trust boundary.
---

# Review the security surface of a change

## Purpose

Find exploitable weaknesses by tracing untrusted data to dangerous operations, with a scenario, a fix and a test each.

## Inputs needed

- The diff and the files around it, including callers of the changed code.
- A description of who can reach the feature: anonymous users, signed-in users, other tenants, other services.
- The data classes involved: public, internal, personal, secret.
- Access to run dependency and secret scanners (for example `pip-audit`, `npm audit`, `osv-scanner`, `gitleaks`).

## Steps

1. Build a boundary table from the diff. Columns: source (HTTP parameter, header, file, queue message, environment, database row written by another system), sink (query, shell command, file path, HTML, redirect, outbound request, log line), and whether validation exists today.
2. Trace each source to each sink through the code. At each hop note whether the value is checked (type, length, range, allow-list) and whether it is encoded for the sink's context: parameterized query, escaped HTML, argument list without a shell, canonicalized path.
3. Search for dangerous sinks, using the patterns in [sink patterns](references/sink-patterns.md). For every hit, either fix it or write why the input cannot be attacker-controlled.
4. Check authentication and authorization for every new route, handler and job. Take the tenant and user identity from the session, never from the request body. Write a test where user A requests user B's object by identifier and expect a 403 or 404.
5. Check secrets. Scan the diff and the branch history for keys, tokens and passwords. Configuration must come from the environment or a secret store. A secret that was ever committed counts as leaked and must be rotated.
6. Check data handling. Classify each new field. Personal and secret data need encryption in transit and at rest, a retention rule, and no appearance in logs or error messages.
7. Check cryptography. Use library primitives only. Hash passwords with argon2id, bcrypt or scrypt. Take random tokens from a cryptographically secure generator. Compare secrets in constant time. Never disable TLS verification.
8. Audit dependencies. List added and upgraded packages, run the advisory scanner, confirm the lockfile changed, and question any new package that replaces fewer than 20 lines of code.
9. Write five abuse cases for the feature and try them: oversized body, rapid repetition, replayed request, malformed encoding, concurrent double submit. Record the observed behavior.
10. For each confirmed finding, write a test whose input exploits it. It must fail before the fix and pass after.
11. Report findings with a severity: critical (remote, unauthenticated, or exposes data), high (authorization bypass or privilege escalation), medium, low. Each entry gives the location, an exploit scenario, the fix and the test. Separate confirmed findings from suspected ones.

### Example boundary table

```
Source                 Sink                                   Validated today?
filename form field    open(os.path.join(UPLOAD_DIR, name))   no: "../" is accepted
X-Tenant header        WHERE tenant_id = <header value>       no: client controls it
callback_url JSON      requests.post(callback_url)            no: private ranges reachable
```

## Output

Return a security review report: the boundary table, then the findings sorted by severity, each with location (`file:line`), exploit scenario, severity, fix and test. Add the dependency audit and secret scan results, the five abuse cases with what you observed, and any accepted risk with its owner. End with the exit criteria below as a checklist, each marked met or not met with one line of evidence.

## Exit criteria

- [ ] The boundary table exists and no row has "unknown" in the validation column.
- [ ] Each finding has location, exploit scenario, severity, fix and a test that fails before the fix.
- [ ] No critical or high finding is open, or the owner's written risk acceptance is linked.
- [ ] Dependency audit and secret scan output are attached and every hit is resolved or explained.
- [ ] A cross-tenant access test exists and passes.
- [ ] `git log -p` for the branch shows no secret values.
- [ ] The five abuse cases and their observed results are listed.

## Failure modes

- **Client-side validation only.** Anyone can skip the browser. Validate on the server.
- **Deny-list filtering.** Blocking known bad strings misses variants. Use allow-lists and context-correct encoding.
- **Route-level auth, no object-level auth.** Any signed-in user can read any record by changing an identifier.
- **Trusting forwarded identity.** Headers such as `X-Forwarded-For` or a `user_id` field in the body are attacker-controlled unless a trusted proxy sets them.
- **Logging whole requests.** Tokens, passwords and personal data end up in log storage.
- **Fixing one sink.** The same input reaches two more sinks. Trace all of them.
- **Obscurity as control.** Random identifiers are not authorization.
- **Scanner output without triage.** Forty findings pasted into a report help nobody. Mark each as exploitable, not reachable or accepted, with a reason.
- **Time-of-check to time-of-use.** A file or permission is checked and then used in a separate step. Combine the check and the use.

## When to stop and ask

- You find an issue that is exploitable in production now. Tell the security contact privately and immediately; do not post details in a public channel.
- A secret was committed. The owner must rotate it before anything else.
- The change handles regulated data such as health records, payment cards or data about minors.
- The fix needs a cryptographic design decision or would break existing clients.
- The tenancy or permission model is undefined, so no check can be written.
