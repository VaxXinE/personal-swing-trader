# Security audit — macOS Malicious Script Blocked investigation (2026-10-23)

**Scope:** repository source/static path analysis; not an endpoint malware scan, no binary signing checks, no executed LIVE provider scan or verification on the user's Mac. This document does **not** assert the machine is clean, that the detection was a false positive, or that any extension caused the alert.

## Evidence supplied by user

- macOS repeatedly displayed **Malicious Script Blocked** when the UI **Run Scan** action was used.
- The application returned 178 strategy evaluations and three data acquisition failures: `US:NASDAQ:OIG` (`INSUFFICIENT_HISTORY`) and `IDX:IDX:ARMY` / `IDX:IDX:GAMA` (Yahoo returned no data). Those are data-coverage errors, not malware diagnoses.
- Unified logs reported `AppleSystemPolicy: Unable to apply provenance sandbox` for the signed VS Code `Code Helper (Plugin)` binary. User's `codesign --verify` passed and `spctl` reported an accepted, notarized Developer ID. Neither fact establishes the alert's origin.
- VS Code renderer logs show Roo Code's **terminal observation** messages for terminal commands the user typed to inspect XProtect. These messages do not prove Roo Code initiated those commands or the malware alert.

## Source code review and threat assessment

| Surface | Verified behavior | Risk and mitigation |
|---|---|---|
| `web/app.js` Run Scan | Browser calls `POST /v1/screeners/runs` with structured rules; no browser code downloads/runs shell scripts | Do not bypass macOS protection; avoid repeated LIVE reproduction |
| `backend/app/main.py` and `service.py` | API calls the synchronous scan and provider adapters, then stores immutable scan results | Provider/network execution remains subject to third-party dependency audit; API requires token when configured; loopback-only bind by default |
| `backend/app/providers.py` | Live equity uses optional `yfinance`; crypto uses `httpx` against a fixed Binance hostname | Dynamic package behavior and provider data not exhaustively audited; no direct `osascript`, process spawn or `eval` observed in this flow |
| `scripts/start.sh`, `scripts/start.bat` | **Before remediation:** automatically ran `pip install -r ...` on every startup | **Changed:** startup is offline with explicit dependency installation, avoiding unintended network/package code execution during normal launch |
| `scripts/browser_e2e.py`, `scripts/server_smoke.py` | Spawn a local Python test server through `subprocess.Popen` when manually invoked | Developer/testing-only; no shell=True, no user-supplied command in examined invocations |
| `scripts/flutter_setup.*`, CI, Docker | Explicit dependency downloads/build tooling during user-requested setup or automated CI | Third-party dependency supply-chain trust required; GitHub Actions referenced by tags rather than immutable SHA; pinning/auditing is future hardening |
| Web rendering | Frontend uses templated HTML and escaping helper | Full contextual XSS audit is not complete; do not assume all untrusted data sinks are safe |

## Controls introduced

1. **No automatic pip installs at startup.** Create venv and install dependencies explicitly by user action; the launcher checks imports before starting. Existing `.venv` and database remain intact.
2. Backtest V2 uses historical candle prefixes only and does not execute shell commands, install dependencies or call providers itself. Endpoint provider calls still happen when the user explicitly requests a live backtest.
3. No modifications to XProtect, quarantine attributes, SIP, Gatekeeper or system policies.

## Unresolved and follow-up

- The blocked script's hash, source path, process ancestry, and exact detection timestamp are unknown. **Do not run LIVE Run Scan again solely to reproduce the warning** without a controlled investigation.
- Perform an independent malware/security assessment on the Mac (security updates, built-in protection, Apple Support if repeated); evaluate VS Code extension executable permissions separately.
- Add lockfiles/hash verification and dependency vulnerability scanning, supply-chain integrity review (yfinance, pandas, numpy, platform wheels), and a request-origin control for local APIs; these are pending rather than claimed.
- A working API and valid VS Code signature do NOT prove endpoint safety.
