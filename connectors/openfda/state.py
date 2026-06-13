"""Filesystem-as-memory: per-endpoint STATE.md + append-only progress log.

The pipeline is resumable from a hard kill. After every ``fetch`` step we
persist the endpoint's cursor, cumulative row count, last window, and a
timestamp to ``STATE.md`` (human-readable Markdown with a fenced JSON
block per endpoint so a person and a machine can both read it). On
restart the pipeline reloads STATE.md and resumes from the saved cursor.

We also append to ``PROGRESS.md`` (never rewritten) and surface a helper
to append rationale to ``DECISIONS.md`` when the pipeline hits an
ambiguity it resolved without stopping.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_BLOCK_RE = re.compile(
    r"<!--\s*state:(?P<ep>[\w]+)\s*-->\s*```json\s*(?P<json>\{.*?\})\s*```",
    re.DOTALL)


@dataclass
class EndpointState:
    endpoint: str
    cursor: Optional[Dict[str, Any]] = None
    rows_ingested: int = 0
    raw_rows_seen: int = 0
    requests_made: int = 0
    last_window: Optional[str] = None
    status: str = "pending"          # pending|in_progress|complete|failed
    last_error: str = ""
    last_run_at: str = ""

    def touch(self) -> None:
        self.last_run_at = _utc_now()


class StateStore:
    """Reads/writes STATE.md, PROGRESS.md, DECISIONS.md under a root dir."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "STATE.md"
        self.progress_path = self.root / "PROGRESS.md"
        self.decisions_path = self.root / "DECISIONS.md"

    # ── STATE.md ──────────────────────────────────────────────────────
    def load(self) -> Dict[str, EndpointState]:
        if not self.state_path.exists():
            return {}
        text = self.state_path.read_text(encoding="utf-8")
        out: Dict[str, EndpointState] = {}
        for m in _BLOCK_RE.finditer(text):
            try:
                data = json.loads(m.group("json"))
                out[data["endpoint"]] = EndpointState(**data)
            except Exception:
                continue  # tolerate a hand-edited/corrupt block, skip it
        return out

    def save(self, states: Dict[str, EndpointState]) -> None:
        lines = [
            "# openFDA connector — STATE",
            "",
            f"_Last updated {_utc_now()} (UTC). Machine-readable; the fenced "
            "JSON blocks are the source of truth for resume._",
            "",
            "| Endpoint | Status | Rows | Last window | Last run |",
            "|---|---|---:|---|---|",
        ]
        for ep in sorted(states):
            s = states[ep]
            lines.append(
                f"| {ep} | {s.status} | {s.rows_ingested} | "
                f"{s.last_window or '—'} | {s.last_run_at or '—'} |")
        lines.append("")
        for ep in sorted(states):
            s = states[ep]
            lines.append(f"<!-- state:{ep} -->")
            lines.append("```json")
            lines.append(json.dumps(asdict(s), indent=2, sort_keys=True))
            lines.append("```")
            lines.append("")
        tmp = self.state_path.with_suffix(".md.tmp")
        tmp.write_text("\n".join(lines), encoding="utf-8")
        tmp.replace(self.state_path)

    # ── PROGRESS.md (append-only) ─────────────────────────────────────
    def log(self, message: str) -> None:
        if not self.progress_path.exists():
            self.progress_path.write_text(
                "# openFDA connector — progress log\n\n"
                "_Append-only. Each line is one pipeline event._\n\n",
                encoding="utf-8")
        with self.progress_path.open("a", encoding="utf-8") as fh:
            fh.write(f"- {_utc_now()} {message}\n")

    # ── DECISIONS.md (append rationale) ───────────────────────────────
    def decide(self, title: str, rationale: str) -> None:
        if not self.decisions_path.exists():
            self.decisions_path.write_text(
                "# openFDA connector — DECISIONS\n\n"
                "_When uncertain, we record the call and its rationale here "
                "and keep going._\n\n",
                encoding="utf-8")
        with self.decisions_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {_utc_now()} — {title}\n\n{rationale}\n")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
