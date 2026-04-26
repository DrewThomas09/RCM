33fda80 | 2026-04-26 | CRITICAL | Report-0131 | configs/playbook.yaml unparseable — stripped leading space from 6 keys
cb84f07 | 2026-04-26 | CRITICAL | Report-0136 | pyarrow CVE-2023-47248 RCE — tightened pin to >=18.1,<19.0
5d91bda | 2026-04-26 | CRITICAL | Report-0251 | rcm-intake console-script broken — added rcm_mc/intake.py shim
53f67c4 | 2026-04-26 | CRITICAL | Report-0246 | audit chain stranded on laptop — pushed Reports 0001-0254 + TRIAGE.md to origin/audit/reports-and-triage (data-loss risk closed; main-merge is a separate follow-up)
b31aecd | 2026-04-26 | HIGH     | Report-0150 | profiles.yml not in .gitignore — added **/profiles.yml block (preserves profiles.example.yml + vendor fixtures)
a53321f | 2026-04-26 | HIGH     | Report-0254 | infra/README.md described nonexistent ConfigValidationError + write_yaml — corrected to ConfigError + cross-link to core/calibration.py
5685af4 | 2026-04-26 | HIGH     | Report-0247 | _chartis_kit_v2 deletion on feat/ui-rework-v3 documented in MERGE-CONFLICTS.md (4 main refs at _chartis_kit.py L9/L46/L90/L190) with merge-time resolution recipe
9287908 | 2026-04-26 | HIGH     | Report-0119 | RCM_MC_AUTH unset = open server — added stderr warning at server start when bound non-loopback with no auth + no DB users
f4ffdac | 2026-04-26 | HIGH     | Report-0211 | CLAUDE.md SQLite table count drift (said 17, audit found 21, grep finds 89) — doc now says ~89 with a self-derivable grep recipe
f1039f8 | 2026-04-26 | HIGH     | Report-0251 | Python version drift between CLAUDE.md (3.14) and pyproject (>=3.10) — doc aligned to "Python 3.10+"
4abc310 | 2026-04-26 | HIGH     | Report-0001 | three-way version drift across pyproject/__init__/CHANGELOG — added v1.0.0 CHANGELOG entry consolidating audit/fix-loop hardening
e624c0c | 2026-04-26 | HIGH     | Report-0249 | get_member_role public-by-use, private-by-export — added to engagement/__init__.py public __all__ (34 tests pass)
127a9f9 | 2026-04-26 | HIGH     | Report-0250 | RCM_MM/ inspected — empty 0-byte scratch dir, closed in Report-0255
127a9f9 | 2026-04-26 | HIGH     | Report-0250 | vendor/ChartisDrewIntel/ inspected — Tuva Project (Apache 2.0 dbt), closed in Report-0255
2fc6715 | 2026-04-26 | HIGH     | Report-0162 | hash_inputs missing actual.yaml/benchmark.yaml content fingerprints — added optional kwargs + analysis_store wires through deal_sim_inputs paths
8d355d2 | 2026-04-26 | MEDIUM   | Report-0253 | 6 untested public helpers in infra/config.py — added 17 focused tests (is_multi_site, expand_multi_site, canonical_payer_name, export/import_config_json, flatten_config); also pins MR1049 alias contract
