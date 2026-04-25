# ic_binder/

Full IC binder — every analytic module's output bound into a single navigable HTML or Markdown document. The "deal book" version of `ic_memo/`.

| File | Purpose |
|------|---------|
| `html.py` | HTML renderer — table of contents, anchored sections per module, exhibits embedded inline |
| `markdown.py` | Markdown renderer — same structure, suitable for piping into Word or pasting into Notion |

## When to use which

- **`ic_memo/`** for the partner pre-read (5–10 min skim)
- **`ic_binder/`** for the IC meeting itself (50–100 pages, every exhibit, full Q&A backup)
- **`reports/full_report.py`** for the deeply technical appendix (engineering-grade audit trail)

The binder pulls from the same `DealAnalysisPacket` that drives every other surface, so an analyst override on one screen propagates everywhere.
