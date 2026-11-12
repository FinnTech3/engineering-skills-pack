# Search patterns for dangerous sinks

Use these with `git grep -nE` or your editor. A match is a lead, not a finding: follow the
value back to its source and decide whether an attacker controls it.

| Sink class | Look for | Safe form |
|---|---|---|
| SQL built from strings | `execute(f"`, `execute("..." +`, `"SELECT ... " %`, string concatenation near `query(` | Parameterized queries with bound values. |
| Shell execution | a `shell` argument set to true, `system(` from the `os` module, `exec(`, backticks, `child_process.exec(` | Argument list without a shell: `subprocess.run([...])`, `execFile`. |
| Code evaluation | `eval(`, `exec(`, `new Function(`, `compile(` on input | Remove it, or parse a restricted data format. |
| Unsafe deserialization | `pickle.loads`, `yaml.load(` without a safe loader, `ObjectInputStream`, `unserialize(` | JSON, or the safe loader (`yaml.safe_load`). |
| HTML injection | `innerHTML`, `dangerouslySetInnerHTML`, the `safe` template filter, `mark_safe`, `v-html`, raw template output | Auto-escaping output, or a sanitizer with an allow-list. |
| Path traversal | `open(`, `send_file(`, `Path(` joined with a request value | Resolve the path, then check that it stays inside the allowed directory. |
| Open redirect | `redirect(` or a `Location` header built from a request value | Allow-list of destinations, or relative paths only. |
| Server-side request forgery | `requests.get(`, `fetch(`, `http.Get(` on a URL from input | Allow-list of hosts, block private and link-local address ranges, no redirects. |
| XML external entities | XML parsers with entity resolution on | Disable DTDs and external entities. |
| Weak randomness | `random.`, `Math.random()`, `rand()` used for tokens or identifiers | `secrets`, `crypto.randomBytes`, `/dev/urandom`. |
| Weak password storage | `md5(`, `sha1(`, `sha256(` applied to passwords | argon2id, bcrypt or scrypt with a per-user salt. |
| Disabled verification | `verify=False`, `rejectUnauthorized: false`, `InsecureSkipVerify` | Remove it. Install the right CA instead. |
| Secrets in code | `AKIA`, `-----BEGIN`, `password =`, `token =`, high-entropy strings | Environment or a secret store, plus rotation. |
| Permissive CORS | `Access-Control-Allow-Origin: *` with credentials, reflected `Origin` | Explicit list of origins. |
