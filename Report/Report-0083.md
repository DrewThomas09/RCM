# Report 0083: Version Drift — `openpyxl`

## Scope

Per pyproject.toml:31 `openpyxl>=3.1,<4.0`. Sister to Reports 0016 (pyyaml), 0046 (numpy), 0053 (pandas), 0076 (matplotlib).

## Findings

### Pin

`openpyxl>=3.1,<4.0` — declared in core deps AND `[exports]` extras (Report 0003 noted intentional duplication).

### Production usage

Per Report 0023, openpyxl is the Excel I/O library. Used by exports/packet_renderer for xlsx generation, plus tests. Estimated ~10-30 importing files.

### CVE history

openpyxl has had occasional issues (e.g. ZIP-bomb-style risks on parsing untrusted xlsx). Floor 3.1+ avoids historical issues.

### Trust boundary

The codebase WRITES xlsx (export), doesn't typically READ untrusted xlsx. But test fixtures may include uploaded xlsx — Report 0017 noted f-string SQL at dashboard_page:802 needs verification.

### Upstream

Active. Maintained by foss-team. Latest 3.1.5 as of audit.

### `[exports]` duplication

`[exports]` extras pin `openpyxl>=3.1` AND `python-pptx>=0.6`. The duplicated openpyxl is per Report 0003 line 37-41 comment: "openpyxl is also in base deps (the xlsx export is a core partner workflow)."

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR468** | **`<4.0` ceiling allows 3.x only — strict** | Tighter than pandas (`<4.0` allows 3.x untested). Good. | (advisory clean) |
| **MR469** | **No untrusted-xlsx-reading paths verified** | If a feature branch adds inbound xlsx upload, openpyxl read could be ZIP-bomb-vulnerable. | Medium |

## Dependencies

- **Incoming:** exports/packet_renderer.py, tests.
- **Outgoing:** stdlib zip + xml parsers.

## Open questions / Unknowns

- **Q1.** Does any production code call `openpyxl.load_workbook()` on user input?

## Suggested follow-ups

None new.

---

Report/Report-0083.md written.

