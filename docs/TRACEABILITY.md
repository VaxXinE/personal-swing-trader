# TRACEABILITY — Requirements → Design → Tests → Tasks

Keep this matrix updated in same pull request as changed requirement. `T-` test IDs defined in [TEST_PLAN](TEST_PLAN.md); `TSK-` tasks from [TASKS](TASKS.md).

| Requirement | Authoritative spec | Tests | Implementation task(s) |
|---|---|---|---|
| FR-001 Registry | DATA_CONTRACTS, DATABASE_SCHEMA | T-001 | TSK-006 |
| FR-002 Ingestion | DATA_CONTRACTS, DATA_PROVIDERS | T-002, T-003 | TSK-008..011 |
| FR-003 Universe | UNIVERSE_LIQUIDITY | T-004, T-005 | TSK-013 |
| FR-004 Exclusions | UNIVERSE_LIQUIDITY, design.md | T-004 | TSK-013, TSK-022 |
| FR-005 Strategies | STRATEGY_SPEC | T-006, T-007, T-030 | TSK-017, TSK-018 |
| FR-006 Custom rules | API_CONTRACT, design.md | T-008 | TSK-015, TSK-023 |
| FR-007 Versioned screens | API_CONTRACT, DATABASE_SCHEMA | T-009 | TSK-016 |
| FR-008 Scoring | SCORING_RANKING | T-010 | TSK-019 |
| FR-009 Eligibility | UNIVERSE_LIQUIDITY, RISK_EXECUTION | T-005, T-011, T-029 | TSK-020 |
| FR-010 Ranking | SCORING_RANKING | T-012 | TSK-020 |
| FR-011 Trade plan | STRATEGY_SPEC, RISK_EXECUTION | T-007, T-013, T-030 | TSK-021 |
| FR-012 Sizing | RISK_EXECUTION | T-013, T-014 | TSK-021 |
| FR-013 Alerts | ARCHITECTURE, API_CONTRACT | T-015 | TSK-024 |
| FR-014 Signal audit | DATABASE_SCHEMA | T-016 | TSK-024, TSK-025 |
| FR-015 Backtest | BACKTESTING | T-017, T-018 | TSK-026, TSK-027 |
| FR-016 Flutter app | design.md | T-019, T-027 | TSK-022, TSK-023 |
| FR-017 Private security | SECURITY | T-020 | TSK-003 |
| FR-018 Scheduler | DATA_CONTRACTS, OPERATIONS | T-021, T-028 | TSK-007, TSK-028 |
| FR-019 Fundamental/events | DATA_PROVIDERS, PREDICTION_VALIDATION | additional P1 test TBD | P1 task TBD |
| FR-020 Forecast | PREDICTION_VALIDATION | T-022, T-023 | TSK-029, TSK-030 |
| FR-021 Historical replay | BACKTESTING, DATABASE_SCHEMA | additional P1 UI test TBD | P1 task TBD |
| FR-022 Streaming | DATA_PROVIDERS, API_CONTRACT | T-024 | TSK-010, P1 frontend TBD |
| NFR-001 Reproducibility | ARCHITECTURE, DATABASE_SCHEMA | T-026 | TSK-011, TSK-016 |
| NFR-002 Data source | DATA_CONTRACTS | T-002, T-005 | TSK-008..012 |
| NFR-003 Portability | ARCHITECTURE, OPERATIONS | smoke tests | TSK-001 |
| NFR-004 Security | SECURITY | T-020 | TSK-003 |
| NFR-005 Recoverability | OPERATIONS | T-025 | TSK-005 |
| NFR-006 Performance | ARCHITECTURE | benchmark test TBD | TSK-022 |
| NFR-007 Accessibility | design.md | T-027 | TSK-022 |
| NFR-008 Observability | OPERATIONS | T-028 | TSK-028 |
| NFR-009 Cost control | DATA_PROVIDERS | provider-degraded test T-005 | TSK-009..012 |

## Change control check

- [ ] All affected FR/NFR IDs reflected in domain specs.
- [ ] Tests and task IDs updated, no dangling references.
- [ ] Data providers/source provenance, as-of and strategy version preserved.
- [ ] Security and no-lookahead consequences reviewed.
