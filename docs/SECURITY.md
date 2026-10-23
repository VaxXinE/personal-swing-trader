# SECURITY — Private by Default Threat Model

**Scope:** one user on Android Flutter, backend on private laptop/mini PC (or optional VPS), third-party market APIs, local SQLite/Parquet, notifications. Personal-use does **not** mean no security threat.

## 1. Assets and trust boundaries

Assets: provider tokens; personal journal/holdings; market data integrity; forecast/model snapshots; laptop files; Android data; alert channel credentials. Threats: compromised phone, malicious library, malicious provider data/news text, exposed FastAPI port, injected screener rule, poisoned historical dataset, backup theft, lost device, stolen token, compromised home/VPS endpoint.

Trust boundaries: mobile↔API, API↔external providers, external text↔explanation system, scheduled workers↔storage, backup↔offsite. All provider payloads **untrusted** and validated.

## 2. Required controls

| Topic | Rule |
|---|---|
| Network | `127.0.0.1` for local dev; private VPN/identity proxy remote; no public anonymous port |
| Authentication | trusted VPN identity **plus** app API session for defense-in-depth; short-lived secret, secure storage on mobile |
| Authorization | fixed single user; account admin routes not available; backend checks every protected endpoint |
| Secrets | environment/OS secure store; `.env` ignored; rotate on leak; separate read-only API scopes |
| Transport | HTTPS or encrypted VPN; reject plaintext over untrusted Wi-Fi |
| Input | Pydantic validate types/limits, rule AST whitelist, allowlisted provider hosts, max depth/nodes |
| Injection | no `eval/exec`, dynamic SQL, unescaped shell interpolation; parameterized DB queries |
| SSRF | no generic user-supplied URL fetch endpoint; strict provider domain allowlist, redirects restrictions |
| XSS/HTML | external news/markdown sanitized; Flutter displays plain text or safe markdown, no script execution |
| LLM | external content cannot override trusted instructions or change strategy/risk config; explanation-only role |
| Filesystem | limited write dirs, safe partition paths, no path traversal, atomic file writes |
| Dependency | pinned lock files, security audit workflow, no blindly installing GitHub scripts |
| Logs | redact tokens/user holdings where possible, bounded retention, no raw auth headers |
| Mobile | secure storage for session, no secrets in source or build, screen privacy if desired |
| Recovery | encrypted/versioned backups + restore tests; lost device revokes token/VPN identity |

## 3. Crypto integration policy

Public market data endpoints should not need private exchange trading API keys. If a provider later requires account credentials, grant read-only scopes, **never withdrawal rights**, never expose private keys on app client. Real trade automation outside scope; block even if user later asks via a routine bugfix.

## 4. Specific abuse stories and tests

- Attacker sends `field="__import__('os')..."` via custom screener → validation rejects as unknown field.
- Provider description includes `IGNORE SYSTEM / execute order` → stored as inert text, not instructions.
- Malicious symbol alias contains `../` → safe identifier sanitization and no file path derivation.
- Unauthorized LAN client attempts API → connection denied by firewall/VPN or auth (not `200`).
- Lost phone → remote revoke identity/session and prevent local secret extraction where possible.
- A stale cached quote appears after network loss → UI replaces LIVE badge with STALE and blocks READY.

## 5. Security definition of done

Threat model reviewed for new network/integration features, automated secret scan, dependency audit, validation unit tests, auth negative tests, no plaintext token in logs or backups, recent restore/revocation drill, documented least-privilege process user.

## 6. Compliance boundary

Current scope personal research, no public market-data redistribution or sale of advice. Still respect data provider terms, account access permissions, privacy, and applicable law. Expanding to public app or execution requires **new security/legal architecture review**, not a small switch.
