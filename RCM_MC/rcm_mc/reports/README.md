# Reports

Report generation across multiple formats: HTML, Markdown, PowerPoint, and narrative text. Ranges from the full audit-grade HTML report to the one-page partner brief, with shared styling and helper infrastructure.

| File | Purpose |
|------|---------|
| `reporting.py` | Core reporting utilities: distribution summarization, metric labels, pretty-money formatting, summary tables, and matplotlib chart generation |
| `html_report.py` | Client-ready HTML report generator with executive-facing sections and clear explanations |
| `full_report.py` | Comprehensive HTML report including input requirements, config reference, and numbers source map |
| `markdown_report.py` | GitHub-flavored Markdown report with the same key sections as the HTML report |
| `narrative.py` | Natural-language 3-paragraph plain-English summary of simulation results |
| `pptx_export.py` | 5-slide IC deck generator (requires `python-pptx`) |
| `exit_memo.py` | Exit-readiness HTML memo with deal facts, track record, peer percentile, and remaining opportunity sections |
| `lp_update.py` | Standalone LP-update HTML builder for scheduled delivery via external cron |
| `report_themes.py` | CSS theme system: default, dark, print-optimized, and minimal themes for HTML reports |
| `_partner_brief.py` | One-page IC-ready partner brief: headline KPIs, key insights, benchmark gaps, and management-plan miss summary |
| `_report_css.py` | Shared CSS styles and head markup for the HTML report |
| `_report_helpers.py` | Standalone helpers (base64 encoding, HTML escaping, data formatting) used by the report generator |
| `_report_sections.py` | Static HTML/JS scaffolding blocks assembled into the executive report alongside dynamic data sections |
