"""IFT sourcing prompts page — Part 1 (``/ift-sourcing``).

The evidence-acquisition companion to the diligence question architecture: the
exact, scope-bounded research prompts that go out to gather the proof, each with
the boundary line that keeps NEMT and 911 out, its prioritized public sources,
the real connector datasets that feed it, and a live link to where the answer
already lives (a sized page + the matching /ift-diligence slide). Every prompt is
copy-pasteable with the boundary prefixed.

Reads :mod:`ift_sourcing`; resolves connector references against the live
:mod:`ift_connectors` estate. Renders through ``chartis_shell`` + ``ck_*``;
degrades to honest notes and never raises.

Public API:
    render_ift_sourcing(qs=None) -> str
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional, Tuple

from ._chartis_kit import (
    chartis_shell, ck_next_section, ck_page_actions, ck_page_title, ck_panel,
    ck_section_header, ck_section_intro,
)
from ..market_reports import ift_sourcing as _sp


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


_BASIS_TITLES = {
    "FRAMEWORK": "An analytic framework / diligence prompt, not a figure.",
    "GOV": "A published government source (CMS, MedPAC, OIG, Census, CDC, statute).",
    "ACADEMIC": "A peer-reviewed / analyst source.",
    "INDUSTRY": "An industry / trade source (AHA, AAA, AIMHI).",
    "SOURCED": "Live — a registered dataset in our connector estate.",
    "CONNECTOR": "A registered connector dataset — ingest-ready offline.",
}
_BASIS_CLASS = {"FRAMEWORK": "framework", "GOV": "gov", "ACADEMIC": "academic",
                "INDUSTRY": "industry", "SOURCED": "sourced",
                "CONNECTOR": "connector"}


def _chip(basis: str) -> str:
    b = (basis or "FRAMEWORK").upper()
    key = b if b in _BASIS_TITLES else "FRAMEWORK"
    return (f'<span class="ifs-chip ifs-chip-{_BASIS_CLASS[key]}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


def _link_row(pairs: Tuple[Tuple[str, str], ...], *, label: str) -> str:
    if not pairs:
        return ""
    links = "".join(
        f'<a href="{_esc(href)}">{_esc(txt)} &rarr;</a>' for txt, href in pairs)
    return (f'<div class="ifs-answer"><span class="ifs-answer-lab">{_esc(label)}'
            f'</span><div class="ifs-links">{links}</div></div>')


def _connector_chips(keys: Tuple[str, ...], ce) -> str:
    if not (ce and ce.available and keys):
        return ""
    chips: List[str] = []
    for k in keys:
        p = ce.probes_by_key.get(k)
        if p is None:
            continue
        live = getattr(p, "available", False)
        cls = "ifs-cx-live" if live else "ifs-cx-gated"
        status = "LIVE" if live else "INGEST-READY"
        href = "/connector-estate?dataset=" + _esc(getattr(p, "dataset_id", ""))
        chips.append(
            f'<a class="ifs-cx {cls}" href="{href}" '
            f'title="{_esc(getattr(p, "ift_signal", ""))}">'
            f'{_esc(getattr(p, "title", k))} '
            f'<span class="ifs-cx-st">{status}</span></a>')
    if not chips:
        return ""
    return ('<div class="ifs-cxrow"><span class="ifs-cx-lab">Feeds from our '
            'connector estate</span>' + "".join(chips) + '</div>')


# ── Scoped stylesheet + copy-to-clipboard shim ───────────────────────────────
_STYLES = """<style>
.ifs-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:600;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;margin:0 2px 2px 0;}
.ifs-chip-framework{background:#ece9f2;color:#463a63;}
.ifs-chip-gov{background:#e7efe9;color:#154e36;}
.ifs-chip-academic{background:#efeae0;color:#6b5426;}
.ifs-chip-industry{background:#eef1f5;color:#31465e;}
.ifs-chip-sourced{background:#e7efe9;color:#154e36;}
.ifs-chip-connector{background:#eef1f5;color:#31465e;border:1px solid #cdd6e2;}
.ifs-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:90ch;margin:0 0 10px;}
.ifs-sub{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;
letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);
margin:14px 0 6px;}
.ifs-why{font-family:var(--sc-serif,Georgia,serif);font-size:14px;font-style:italic;
line-height:1.5;color:var(--sc-navy,#0b2341);border-left:3px solid var(--sc-teal,#155752);
padding:6px 0 6px 14px;margin:2px 0 10px;background:rgba(21,87,82,0.035);}
.ifs-boundary{border:1px solid var(--sc-warning,#b8732a);
background:rgba(184,115,42,0.06);border-radius:6px;padding:14px 16px;margin:8px 0 14px;}
.ifs-boundary-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--sc-warning,#b8732a);display:block;margin:0 0 6px;}
.ifs-pre{font-family:var(--sc-mono,Consolas,monospace);font-size:12px;line-height:1.55;
color:var(--sc-text,#1a2332);white-space:pre-wrap;word-break:break-word;margin:0;
padding:10px 12px;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-border,#e4dccb);border-radius:4px;}
.ifs-copy{font-family:var(--sc-mono,Consolas,monospace);font-size:10.5px;
font-weight:600;letter-spacing:.03em;color:var(--sc-teal,#155752);background:#fff;
border:1px solid var(--sc-teal,#155752);border-radius:3px;padding:4px 10px;
cursor:pointer;margin:6px 0 0;}
.ifs-copy:hover{background:var(--sc-teal,#155752);color:#fff;}
.ifs-priority-badge{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:700;letter-spacing:.06em;color:#fff;
background:var(--sc-teal,#155752);padding:2px 7px;border-radius:10px;margin-left:8px;
vertical-align:middle;}
.ifs-runthree{border:1px solid var(--sc-teal,#155752);border-radius:6px;
background:var(--sc-navy,#0b2341);color:#f3efe6;padding:14px 18px;margin:6px 0 16px;}
.ifs-runthree b{color:#fff;}
.ifs-runthree-eyebrow{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#a9c3bd;margin:0 0 6px;}
.ifs-runthree p{font-family:var(--sc-serif,Georgia,serif);font-size:15px;line-height:1.5;
margin:0;}
.ifs-runthree a{color:#a9c3bd;font-weight:700;text-decoration:none;}
.ifs-list{margin:2px 0 8px 18px;font-family:var(--sc-serif,Georgia,serif);
font-size:13px;line-height:1.55;color:var(--sc-text,#2a3340);}
.ifs-list li{margin:0 0 4px;}
.ifs-answer{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;margin:8px 0 4px;
padding:8px 12px;background:var(--sc-surface,#faf7f1);
border:1px solid var(--sc-border,#e4dccb);border-left:3px solid var(--sc-teal,#155752);
border-radius:4px;}
.ifs-answer-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);}
.ifs-links{display:flex;flex-wrap:wrap;gap:6px 16px;}
.ifs-links a{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;
font-weight:600;color:var(--sc-teal,#155752);text-decoration:none;}
.ifs-links a:hover{text-decoration:underline;}
.ifs-cxrow{margin:8px 0 2px;display:flex;flex-wrap:wrap;gap:5px;align-items:center;}
.ifs-cx-lab{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;font-weight:700;
letter-spacing:.05em;text-transform:uppercase;color:var(--sc-muted,#6b6357);margin-right:4px;}
.ifs-cx{display:inline-block;font-family:var(--sc-sans,Inter,system-ui,sans-serif);
font-size:11px;text-decoration:none;padding:3px 9px;border-radius:13px;
border:1px solid var(--sc-border,#e4dccb);background:#fff;color:var(--sc-text,#1a2332);}
.ifs-cx:hover{border-color:var(--sc-teal,#155752);}
.ifs-cx-st{font-family:var(--sc-mono,Consolas,monospace);font-size:8.5px;font-weight:700;
letter-spacing:.04em;margin-left:3px;}
.ifs-cx-live .ifs-cx-st{color:#154e36;}
.ifs-cx-gated{color:var(--sc-muted,#6b6357);}
.ifs-cx-gated .ifs-cx-st{color:#8a7f6b;}
.ifs-links-lg{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0 4px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;}
.ifs-links-lg a{color:var(--sc-teal,#155752);text-decoration:none;}
.ifs-num{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;font-weight:700;
letter-spacing:.08em;color:var(--sc-teal,#155752);display:inline-block;margin:0 0 2px;}
</style>
<script>
(function(){
  function copyText(t, btn){
    var done=function(){var o=btn.textContent;btn.textContent="Copied \\u2713";
      setTimeout(function(){btn.textContent=o;},1400);};
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(t).then(done,function(){fallback(t,done);});
    } else {fallback(t,done);}
  }
  function fallback(t,done){try{var ta=document.createElement("textarea");
    ta.value=t;ta.style.position="fixed";ta.style.opacity="0";
    document.body.appendChild(ta);ta.select();document.execCommand("copy");
    document.body.removeChild(ta);done();}catch(e){}}
  document.addEventListener("click",function(e){
    var b=e.target.closest?e.target.closest(".ifs-copy"):null;
    if(!b)return;var id=b.getAttribute("data-target");
    var el=id?document.getElementById(id):null;if(el){copyText(el.textContent,b);}
  });
})();
</script>"""


def _crosslinks() -> str:
    return (
        '<div class="ifs-links-lg">'
        '<a href="/ift-diligence">Diligence question architecture &rarr;</a>'
        '<a href="/ift-study">Investor market study &rarr;</a>'
        '<a href="/ift-markets">Geographic markets &amp; TAM/SAM/SOM &rarr;</a>'
        '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
        '<a href="/ift-research">Market research brief &rarr;</a>'
        '<a href="/connector-estate">Live data-connector estate &rarr;</a>'
        '</div>')


def _boundary_block(boundary: str) -> str:
    return (
        '<div class="ifs-boundary">'
        '<span class="ifs-boundary-lab">The scope boundary — paste into every '
        'prompt</span>'
        f'<pre class="ifs-pre" id="ifs-boundary-text">{_esc(boundary)}</pre>'
        '<button type="button" class="ifs-copy" data-target="ifs-boundary-text">'
        'Copy boundary</button>'
        '<p class="ifs-prose" style="margin-top:8px;font-size:12.5px;">Without this '
        'line the research drags Medicaid NEMT and 911/scene back into the '
        'denominator — every prompt below is emitted <em>with the boundary '
        'prefixed</em>, and the copy button on each one copies the full, '
        'ready-to-send text.</p>'
        '</div>')


def _runthree_block(priority: Tuple[int, ...]) -> str:
    nums = ", ".join(str(n) for n in priority) if priority else "2, 4, 6"
    anchors = "".join(
        f'<a href="#ifs-p{n}">{n}</a>' + ("" if n == priority[-1] else ", ")
        for n in priority) if priority else ""
    return (
        '<div class="ifs-runthree">'
        '<div class="ifs-runthree-eyebrow">If you only run three</div>'
        f'<p>Run <b>{anchors or nums}</b> — the claims method (2), prevalence per '
        'admission (4), and the post-acute backbone (6). Those three prove '
        'prevalence with a method that survives diligence.</p>'
        '</div>')


def _prompt_panel(p, ce) -> str:
    badge = ('<span class="ifs-priority-badge">RUN-THESE-3</span>'
             if p.priority else "")
    src_items = "".join(
        f'<li>{_esc(name)} {_chip(basis)}</li>' for name, basis in p.sources)
    pre_id = f"ifs-prompt-{_esc(p.slug)}"
    body = (
        f'<span class="ifs-num">PROMPT {p.num}</span>{badge}'
        f'<p class="ifs-why">{_esc(p.why)}</p>'
        '<p class="ifs-sub">The prompt (boundary prefixed — copy &amp; send)</p>'
        f'<pre class="ifs-pre" id="{pre_id}">{_esc(p.full_prompt)}</pre>'
        f'<button type="button" class="ifs-copy" data-target="{pre_id}">'
        'Copy prompt</button>'
        '<p class="ifs-sub">Prioritized sources</p>'
        f'<ul class="ifs-list">{src_items}</ul>'
        + _connector_chips(p.connector_keys, ce)
        + _link_row(p.answered_by, label="Where the answer already lives")
    )
    return ck_panel(body, title=f"{p.num}. {p.title}",
                    anchor_id=f"ifs-p{p.num}")


def render_ift_sourcing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the IFT sourcing-prompts page (Part 1). Degrades, never raises."""
    prompts = _sp.sourcing_prompts()
    priority = _sp.priority_prompts()
    ce = _sp.connector_evidence()
    summ = _sp.sourcing_summary()

    meta = (f"Part {summ['part']} · {summ['n_prompts']} scope-bounded prompts · "
            f"{summ['n_sources']} prioritized sources · "
            f"{summ['n_connectors_used']} connector datasets wired · "
            f"run-these-3: {', '.join(str(n) for n in summ['priority_set'])}")
    head = ck_page_title(
        "IFT Sourcing Prompts — Part 1",
        eyebrow="INTERFACILITY TRANSPORT · HOW THE EVIDENCE IS GATHERED",
        meta=meta)
    explainer = (
        '<p class="ifs-prose" style="font-size:15px;">The <strong>evidence-'
        'acquisition layer</strong> of the IFT study — the exact, scope-bounded '
        'research prompts that go out to gather the proof. Each carries the '
        'boundary line that keeps NEMT and 911 out, its prioritized public '
        'sources, the real <strong>connector datasets</strong> on this platform '
        'that feed it, and a live link to <strong>where the answer already '
        'lives</strong> (a sized page and the matching diligence slide). Prompts '
        'are authored diligence knowledge ' + _chip("FRAMEWORK") + '; sources are '
        + _chip("GOV") + ' ' + _chip("ACADEMIC") + ' ' + _chip("INDUSTRY")
        + '; the connector references resolve live ' + _chip("SOURCED") + ' '
        + _chip("CONNECTOR") + '. This is Part 1.</p>')

    panels = "".join(_prompt_panel(p, ce) for p in prompts)

    body = "".join([
        _STYLES,
        head,
        explainer,
        _crosslinks(),
        _boundary_block(_sp.scope_boundary()),
        _runthree_block(priority),
        ck_section_intro(
            "THE PROMPTS",
            "Ten prompts, each scope-bounded and wired to its evidence.",
            italic_word="wired",
            body=("Every prompt is emitted with the boundary prefixed and a copy "
                  "button, followed by its prioritized sources, the connector "
                  "datasets that feed it, and a link to the sized page and "
                  "diligence slide that already answer it.")),
        panels,
        _crosslinks(),
        ck_next_section(
            "See the question architecture these prompts source the answers for",
            "/ift-diligence", eyebrow="The questions", italic_word="architecture"),
        ck_next_section(
            "Browse the live data-connector estate behind the sources",
            "/connector-estate", eyebrow="The data", italic_word="live"),
        ck_page_actions(),
    ])
    return chartis_shell(
        body, "IFT Sourcing Prompts — Part 1", active_nav="/market",
        subtitle="Interfacility-transport sourcing prompts (Part 1) — the "
                 "scope-bounded research questions that gather the evidence")
