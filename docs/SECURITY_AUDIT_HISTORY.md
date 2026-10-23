# Repository security review — Historical Data Engine (2026-10-23)

**Scope:** read-only code investigation covering `backend/app` (scanner, provider, data normalization, persistence and API), `scripts/` (launchers, smoke tests, universe sync, Flutter tooling), `web/` (JS, PWA/service worker), `apps/mobile` (network/mobile), `infra/` (Docker), CI configuration and dependency manifests. Static review, plus tests; **not a notarized malware scan** or inspection of the user's actual Mac processes/extensions.

## What code analysis establishes

- `web/app.js` Run Scan posts to `/v1/screeners/runs`; FastAPI calls `service.scan` → `providers.load_bars` → Yahoo/ Binance → `domain.analyze`. No explicit `osascript`, AppleScript, Python `eval`, shell command, or dynamic process execution appears in this call path.
- `scripts/start.sh` and `scripts/start.bat` had previously installed packages on every startup. They were hardened in earlier commits to check installed packages and launch only; no automatic `pip install` at application startup.
- `scripts/browser_e2e.py` and `scripts/server_smoke.py` use `subprocess.Popen` with **argument lists** to start the local **DEMO** development server in tests. These are not invoked by Run Scan and contain no `shell=True`.
- `web/pwa.js` unregisters the old service worker on loopback; it is not a malware remediation measure. `web/sw.js` still exists for approved HTTPS deployments, but is not evidence of the macOS popup.
- Python backend source uses allowlisted provider names/symbols, typed screener AST instead of `eval`, parameterized SQLite, localhost-first server config with bearer token required on non-loopback host. Dynamic universe has hardcoded external discovery endpoints; IDX XLSX ingestion has compressed/uncompressed size limits.
- Third-party `yfinance`, its transitive packages and compiled native components, installed VS Code extensions, and actual macOS XProtect/signature event details are **outside what repository static inspection can establish**. macOS `Code Helper (Plugin)` provenance sandbox logs are **not** evidence that a specific extension is malicious. Do **not** label warning a false positive.

## Risks and mitigations

| Finding | Risk | Status |
|---|---|---|
| Auto-install on startup | Supply-chain code runs on ordinary launch | Previously removed, verified source |
| Unversioned/non-locked Python transitive dependencies | Dependency drift or compromised supply-chain artifact | OPEN; CI/live dependencies should use reviewed hashes and a vulnerability process |
| LIVE Yahoo/Binance provider execution | Network/native library exposure; unknown relationship to Mac warning | OPEN; no LIVE command executed on user's Mac here |
| Yahoo historical basis and revision provenance | Split/look-ahead bias masquerades as credible backtest | Mitigated at data-archive boundary: vendor basis explicitly unverified; first-observed metadata |
| Suspicious equity moves/calendar gaps | Unsupported raw/adjusted interpretation | Flagged for review; no fabricated repairs |
| Archive tampering or overwritten prices | Silent research result changes | SHA-256 checked reads, correction revisions append-only; no cryptographic tamper-proof guarantee against attacker with DB write access |
| HTTP API exposure | Local journal/history leakage on public bind | Existing bearer guard for `/v1/`; loopback-only default; TLS/private VPN still required for remote access |
| No corporate action reconciling / delisted historical universe | Biased live-market extrapolation | OPEN — cannot call profitable/validated |

## Next forensic action for original macOS alert

Do **not** repeatedly run LIVE scan to reproduce XProtect warning. Determine the original blocked script or executable's **path, quarantine provenance, timestamp and signed process** from authoritative macOS security evidence; preserve logs and avoid disabling OS protections. If no path is visible, use trusted macOS security support/incident response. This repository audit cannot attribute causation, and it would be unsound to patch `yfinance`/Roo Code based on coincidence alone.
