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
2fc6715 | 2026-04-26 | HIGH     | Report-0162 | hash_inputs missing actual.yaml/benchmark.yaml content fingerprints — added optional kwargs + analysis_store wires through deal_sim_inputs paths | verified-2026-04-26-iter16 (5 invariants: back-compat, distinct hashes, slot non-interchangeability, determinism, e2e benchmark-edit invalidates cache; 58 analysis tests green)
8d355d2 | 2026-04-26 | MEDIUM   | Report-0253 | 6 untested public helpers in infra/config.py — added 17 focused tests (is_multi_site, expand_multi_site, canonical_payer_name, export/import_config_json, flatten_config); also pins MR1049 alias contract
110f2cf | 2026-04-26 | HIGH×2   | Report-0001 | extras graph fixes — added [stats] for scipy (MR17) + folded [diligence] into [all] so `pip install ".[all]"` is genuinely complete (MR18)
d3f23b3 | 2026-04-26 | HIGH     | Report-0094 | ReimbursementProfile name-collision (domain alias vs finance class) — deprecated the domain alias via PEP 562 __getattr__ with DeprecationWarning; back-compat preserved
442bb98 | 2026-04-26 | HIGH     | Report-0212 | ai/document_qa.answer_question hardened against prompt injection — 2000-char question cap + <document>/<question> tagged delimiters + defensive system prompt
488e3c8 | 2026-04-26 | HIGH     | Report-0181 | unified delete-policy missing — added 5-row decision matrix to CLAUDE.md (CASCADE/SET NULL/NO ACTION/soft-delete/hard-delete with on-disk examples + rule of thumb)
c4b6421 | 2026-04-26 | HIGH     | Report-0180 | deal-child FK frontier walked — 13 tables surveyed in Report-0256 (4 CASCADE-clean, 4 NO ACTION, 5 no-FK); surfaced MR1057 (HIGH, 5 silent-orphan tables) + MR1058 (MEDIUM, 3 NO ACTION upgrades)
91097a1 | 2026-04-26 | HIGH     | Report-0256 | 5 deal-child tables (deal_sim_inputs, deal_owner_history, deal_health_history, deal_deadlines, deal_stars) — added ON DELETE CASCADE FK on deal_id; fresh-DB only, live-DB ALTER migration tracked as MR1059
4a79bf1 | 2026-04-26 | HIGH     | Report-0102 | CMS loader audit (MR985) — 13 cms_* modules inventoried in Report-0257, single _cms_download.py seam, no trust-boundary or secret findings; surfaced MR1060 LOW
c2f968d | 2026-04-26 | HIGH     | Report-0247 | dev/seed.py audited from feat/ui-rework-v3 (Report-0258); 896-LOC seeder API + production guard documented; merge handoff added to MERGE-CONFLICTS.md entry 2; surfaced MR1061+MR1062+MR1063
f0f4fc2 | 2026-04-26 | HIGH     | Report-0247 | exports/canonical_facade.py audited from feat/ui-rework-v3 (Report-0259); 424-LOC 11-facade non-invasive layer; merge handoff added to MERGE-CONFLICTS.md entry 3; surfaced MR1064 (HIGH must-land-together) + MR1065 LOW + MR1066 MEDIUM
