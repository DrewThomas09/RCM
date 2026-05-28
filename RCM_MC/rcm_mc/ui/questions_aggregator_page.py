"""Cross-deal diligence questions aggregator — ``/diligence/questions``.

Walks every ``rcm_deal_*_questions`` entry the partner has in their
browser's localStorage and renders an editorial portfolio-wide view
of open questions. Pre-IC, partners use it to confirm coverage:

  - 14 total open questions across 3 deals
  - 6 financial, 4 clinical, 2 regulatory, 1 legal, 1 operational
  - 2 questions still open on Aurora, 5 on Hawthorne, 7 on Sycamore

Filter chips by category and status; export combined Markdown or
CSV across all deals. Same JS-only data model as the per-deal
editor (Phase O–Q) — no server roundtrip, the page is pure
composition.
"""
from __future__ import annotations

from typing import Any

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_next_section, ck_panel,
    ck_section_intro,
)


_AGG_STYLES = """
<style>
.qa-toolbar {
  display: flex; align-items: baseline; gap: 18px; flex-wrap: wrap;
  padding: 14px 18px; margin-bottom: 18px;
  background: var(--sc-bone, #f2ede3);
  border: 1px solid var(--sc-rule, #d8d3c8); border-radius: 3px;
  font-family: "Source Serif 4", serif;
}
.qa-toolbar-eyebrow {
  font-family: "Inter Tight", sans-serif; font-size: 10px;
  font-weight: 700; letter-spacing: 1.4px;
  text-transform: uppercase; color: var(--sc-text-faint, #6e7787);
}
.qa-toolbar-meta { font-style: italic; font-size: 12px;
  color: var(--sc-text-dim, #37495e); flex: 1; }
.qa-toolbar-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.qa-toolbar-btn {
  background: none; border: 1px solid var(--sc-rule, #d8d3c8);
  border-radius: 3px; padding: 5px 10px; cursor: pointer;
  font-family: "Source Serif 4", serif; font-size: 11.5px;
  font-style: italic; color: var(--sc-text-dim, #37495e);
  transition: border-color 120ms ease, color 120ms ease;
}
.qa-toolbar-btn:hover {
  border-color: var(--sc-teal-ink, #0e3e3a);
  color: var(--sc-teal-ink, #0e3e3a);
}
.qa-toolbar-toast {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 11.5px; color: var(--sc-positive, #0a8a5f);
  align-self: center; opacity: 0;
  transition: opacity 200ms ease;
}
.qa-toolbar-toast.is-visible { opacity: 1; }

.qa-filters { display: flex; gap: 16px; flex-wrap: wrap;
  margin-bottom: 22px; align-items: baseline; }
.qa-filter-group {
  display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap;
}
.qa-filter-label {
  font-family: "Inter Tight", sans-serif; font-size: 10px;
  font-weight: 700; letter-spacing: 1.4px;
  text-transform: uppercase; color: var(--sc-text-faint, #6e7787);
}
.qa-chip {
  display: inline-flex; align-items: center;
  padding: 4px 10px; cursor: pointer;
  font-family: "Source Serif 4", serif; font-size: 12px;
  background: transparent;
  color: var(--sc-text-dim, #37495e);
  border: 1px solid var(--sc-rule, #d8d3c8); border-radius: 999px;
  transition: background 120ms ease, border-color 120ms ease,
              color 120ms ease;
  user-select: none;
}
.qa-chip:hover {
  border-color: var(--sc-teal-ink, #0e3e3a);
  color: var(--sc-teal-ink, #0e3e3a);
}
.qa-chip.is-active {
  background: var(--sc-navy, #0b2341); color: #fff;
  border-color: var(--sc-navy, #0b2341);
}

.qa-empty {
  padding: 22px 26px; max-width: 60ch;
  background: var(--sc-bone, #f2ede3);
  border-left: 3px solid var(--sc-teal, #155752);
  border-radius: 0 3px 3px 0;
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 14px; line-height: 1.6;
  color: var(--sc-text-dim, #37495e);
}
.qa-empty em { color: var(--sc-teal-ink, #0e3e3a); }

.qa-deal-section { margin-bottom: 22px; }
.qa-deal-head {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 14px; margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--sc-rule, #d8d3c8);
}
.qa-deal-slug {
  font-family: "Source Serif 4", serif; font-weight: 400;
  font-size: 22px; line-height: 1.2; letter-spacing: -0.012em;
  color: var(--sc-navy, #0b2341);
}
.qa-deal-slug em {
  font-style: italic; color: var(--sc-teal-ink, #0e3e3a);
}
.qa-deal-slug a { color: inherit; text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 120ms ease; }
.qa-deal-slug a:hover {
  border-bottom-color: var(--sc-navy, #0b2341);
}
.qa-deal-meta {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 12px; color: var(--sc-text-faint, #6e7787);
}

.qa-list { list-style: none; padding: 0; margin: 0; }
.qa-row {
  display: grid; grid-template-columns: 28px 1fr auto;
  gap: 12px; align-items: baseline; padding: 10px 0;
  border-bottom: 1px solid var(--sc-rule, #d8d3c8);
}
.qa-row:last-child { border-bottom: 0; }
.qa-row.is-asked .qa-text {
  text-decoration: line-through; color: var(--sc-text-faint, #6e7787);
}
.qa-num {
  font-family: "JetBrains Mono", monospace; font-size: 10px;
  font-weight: 700; letter-spacing: 0.12em;
  color: var(--sc-text-faint, #6e7787);
  text-align: right; align-self: center;
}
.qa-text {
  font-family: "Source Serif 4", serif; font-size: 14px;
  line-height: 1.5; font-style: italic;
  color: var(--sc-text, #1a2332);
}
.qa-ts {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 11px; color: var(--sc-text-faint, #6e7787);
  align-self: center; white-space: nowrap;
}

/* Same pill colors as the per-deal editor (Phase P). */
.qa-pill {
  display: inline-block; padding: 1px 7px; margin-right: 8px;
  font-family: "Inter Tight", sans-serif; font-size: 9px;
  font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  border-radius: 2px; vertical-align: 1px;
  border: 1px solid currentColor;
}
.qa-pill.cat-financial   { color: var(--sc-teal-ink, #0e3e3a); }
.qa-pill.cat-clinical    { color: var(--sc-positive, #0a8a5f); }
.qa-pill.cat-regulatory  { color: var(--sc-warning, #b8732a); }
.qa-pill.cat-legal       { color: var(--sc-text-dim, #37495e); }
.qa-pill.cat-operational { color: var(--sc-text, #1a2332); }
.qa-pill.cat-other       { color: var(--sc-text-faint, #6e7787); }

@media print { .qa-toolbar, .qa-filters { display: none; } }
</style>
"""


_AGG_JS = """
<script>
(function() {
  var CAT_LABELS = {
    financial: "Fin", clinical: "Clin", regulatory: "Reg",
    legal: "Leg", operational: "Ops", other: "Other",
  };
  var CAT_FULL = {
    financial: "Financial", clinical: "Clinical",
    regulatory: "Regulatory", legal: "Legal",
    operational: "Operational", other: "Other",
  };
  var STORAGE_KEY = "rcm_qa_filters_v1";
  var QS_RE = /^rcm_deal_(.+)_questions$/;
  var state = { cat: "all", status: "all" };

  function loadFilters() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var s = JSON.parse(raw);
        if (s && s.cat) state.cat = s.cat;
        if (s && s.status) state.status = s.status;
      }
    } catch (e) { /* ignore */ }
  }
  function saveFilters() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (e) { /* ignore */ }
  }
  function esc(s) {
    var d = document.createElement("div");
    d.textContent = String(s || "");
    return d.innerHTML;
  }
  function rel(ts) {
    if (!ts) return "";
    var d = Math.round((Date.now() - ts) / 60000);
    if (d < 1) return "just now";
    if (d < 60) return d + " min ago";
    if (d < 1440) return Math.round(d / 60) + " hr ago";
    return Math.round(d / 1440) + " d ago";
  }
  function nameForSlug(slug) {
    // Try to read the per-deal profile for a friendlier display name
    try {
      var raw = localStorage.getItem("rcm_deal_" + slug);
      if (raw) {
        var p = JSON.parse(raw);
        if (p && p.deal_name) return p.deal_name;
      }
    } catch (e) { /* ignore */ }
    return slug;
  }
  function readAll() {
    // Returns [{slug, name, rows: [...]}] sorted by most-recent ts desc
    var out = [];
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      var m = k && k.match(QS_RE);
      if (!m) continue;
      var slug = m[1];
      try {
        var rows = JSON.parse(localStorage.getItem(k) || "[]");
        if (!Array.isArray(rows) || rows.length === 0) continue;
        out.push({
          slug: slug, name: nameForSlug(slug), rows: rows,
        });
      } catch (e) { /* skip malformed */ }
    }
    // Sort deals by most-recent question ts desc
    out.forEach(function(d) {
      d.latest = d.rows.reduce(function(m, r) {
        return Math.max(m, r.ts || 0);
      }, 0);
    });
    out.sort(function(a, b) { return b.latest - a.latest; });
    return out;
  }
  function filterRows(rows) {
    return rows.filter(function(r) {
      if (state.status === "open" && r.asked) return false;
      if (state.status === "asked" && !r.asked) return false;
      if (state.cat !== "all") {
        var c = (r.category || "financial").toLowerCase();
        if (!CAT_LABELS[c]) c = "other";
        if (c !== state.cat) return false;
      }
      return true;
    });
  }
  function paint() {
    var root = document.querySelector("[data-rcm-qa-list]");
    var meta = document.querySelector("[data-rcm-qa-meta]");
    if (!root) return;
    var deals = readAll();
    if (deals.length === 0) {
      root.innerHTML =
        '<div class="qa-empty">No diligence questions captured yet. '
        + 'Open a deal profile (or press <em>Shift+Q</em> anywhere) '
        + 'to jot your first one — the aggregator will populate '
        + 'next time you visit.</div>';
      if (meta) meta.textContent = "0 questions across 0 deals.";
      return;
    }
    var totalRows = 0;
    var openRows = 0;
    var catTotals = {};
    var dealsHtml = deals.map(function(d) {
      var visible = filterRows(d.rows);
      totalRows += d.rows.length;
      d.rows.forEach(function(r) {
        if (!r.asked) openRows += 1;
        var c = (r.category || "financial").toLowerCase();
        if (!CAT_LABELS[c]) c = "other";
        catTotals[c] = (catTotals[c] || 0) + 1;
      });
      if (visible.length === 0) return "";
      var nOpen = d.rows.filter(function(r) { return !r.asked; }).length;
      var rowsHtml = visible.map(function(r, i) {
        var stateCls = r.asked ? " is-asked" : "";
        var cat = (r.category || "financial").toLowerCase();
        if (!CAT_LABELS[cat]) cat = "other";
        var pill = '<span class="qa-pill cat-' + cat + '">'
          + esc(CAT_LABELS[cat]) + '</span>';
        return '<li class="qa-row' + stateCls + '">'
          + '<span class="qa-num">'
          + String(i + 1).padStart(2, "0") + '</span>'
          + '<span class="qa-text">' + pill + esc(r.text) + '</span>'
          + '<span class="qa-ts">' + rel(r.ts) + '</span>'
          + '</li>';
      }).join("");
      return '<section class="qa-deal-section">'
        + '<div class="qa-deal-head">'
        + '<h3 class="qa-deal-slug">'
        + '<a href="/diligence/deal/' + encodeURIComponent(d.slug)
        + '#dp-questions"><em>' + esc(d.name) + '</em></a>'
        + '</h3>'
        + '<div class="qa-deal-meta">'
        + d.rows.length + ' total · ' + nOpen + ' still open '
        + '· ' + visible.length + ' shown</div>'
        + '</div>'
        + '<ol class="qa-list">' + rowsHtml + '</ol>'
        + '</section>';
    }).filter(Boolean).join("");
    root.innerHTML = dealsHtml || (
      '<div class="qa-empty">No questions match the current '
      + 'filter. <em>Clear the filters</em> above to see '
      + 'everything.</div>'
    );
    if (meta) {
      var catSum = Object.keys(catTotals)
        .map(function(c) { return catTotals[c] + " " + CAT_LABELS[c]; })
        .join(" · ");
      meta.textContent =
        totalRows + " question" + (totalRows === 1 ? "" : "s") +
        " across " + deals.length +
        " deal" + (deals.length === 1 ? "" : "s") +
        " · " + openRows + " still open" +
        (catSum ? " · " + catSum : "");
    }
  }
  function paintChips() {
    document.querySelectorAll("[data-rcm-qa-chip]").forEach(function(b) {
      var kind = b.getAttribute("data-rcm-qa-kind");
      var val = b.getAttribute("data-rcm-qa-chip");
      if (state[kind] === val) b.classList.add("is-active");
      else b.classList.remove("is-active");
    });
  }
  document.addEventListener("DOMContentLoaded", function() {
    loadFilters();
    paintChips();
    paint();
  });
  document.addEventListener("click", function(e) {
    var chip = e.target.closest && e.target.closest("[data-rcm-qa-chip]");
    if (chip) {
      var kind = chip.getAttribute("data-rcm-qa-kind");
      var val = chip.getAttribute("data-rcm-qa-chip");
      state[kind] = val;
      saveFilters();
      paintChips();
      paint();
      return;
    }
  });
  // Export across all deals
  function csvCell(v) {
    var s = String(v == null ? "" : v);
    if (/[",\\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }
  function buildMd(openOnly) {
    var deals = readAll();
    if (deals.length === 0) return "";
    var lines = [
      "# Diligence questions — portfolio-wide",
      "",
      "_Exported " + new Date().toISOString().slice(0, 10) +
        (openOnly ? " (open only)" : "") + " from your browser._",
      "",
    ];
    deals.forEach(function(d) {
      var rows = openOnly
        ? d.rows.filter(function(r) { return !r.asked; })
        : d.rows;
      if (rows.length === 0) return;
      lines.push("");
      lines.push("## " + d.name);
      lines.push("");
      rows.forEach(function(r, i) {
        var c = (r.category || "financial").toLowerCase();
        if (!CAT_FULL[c]) c = "other";
        var asked = r.asked ? " ✓ asked" : "";
        lines.push((i + 1) + ". **[" + CAT_FULL[c] + "]**" +
          asked + " — " + r.text);
      });
    });
    return lines.join("\\n");
  }
  function buildCsv() {
    var deals = readAll();
    var header = "slug,name,category,status,question,added_at";
    var body = [];
    deals.forEach(function(d) {
      d.rows.forEach(function(r) {
        var c = (r.category || "financial").toLowerCase();
        var st = r.asked ? "asked" : "open";
        var iso = new Date(r.ts || 0).toISOString();
        body.push([
          csvCell(d.slug), csvCell(d.name), csvCell(c),
          csvCell(st), csvCell(r.text || ""), csvCell(iso),
        ].join(","));
      });
    });
    return header + "\\n" + body.join("\\n");
  }
  function toast(msg, tone) {
    var t = document.querySelector("[data-rcm-qa-toast]");
    if (!t) return;
    t.textContent = msg;
    t.style.color = (tone === "neg") ? "#b5321e" : "";
    t.classList.add("is-visible");
    setTimeout(function() { t.classList.remove("is-visible"); }, 1500);
  }
  function copyToClipboard(text) {
    if (!text) { toast("Nothing to copy.", "neg"); return; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function() {
        toast("Copied to clipboard.");
      }).catch(function() { toast("Copy failed.", "neg"); });
    } else {
      var ta = document.createElement("textarea");
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); toast("Copied to clipboard."); }
      catch (e) { toast("Copy failed.", "neg"); }
      document.body.removeChild(ta);
    }
  }
  function downloadCsv() {
    var csv = buildCsv();
    if (!csv || csv.split("\\n").length < 2) {
      toast("Nothing to export.", "neg"); return;
    }
    var blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "diligence-questions-portfolio.csv";
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
    toast("CSV downloaded.");
  }
  document.addEventListener("click", function(e) {
    if (e.target.closest && e.target.closest("[data-rcm-qa-md]")) {
      copyToClipboard(buildMd(false));
    } else if (e.target.closest && e.target.closest("[data-rcm-qa-md-open]")) {
      copyToClipboard(buildMd(true));
    } else if (e.target.closest && e.target.closest("[data-rcm-qa-csv]")) {
      downloadCsv();
    }
  });
}());
</script>
"""


def render_questions_aggregator(
    store: Any = None,  # noqa: ARG001
    *,
    print_preview: bool = False,
) -> str:
    """Render the cross-deal aggregator. ``store`` is accepted to
    match the route-handler signature in server.py but the page is
    purely client-hydrated — every row lives in localStorage.

    ``print_preview`` (set when the route handler sees ``?print=1``)
    wraps the body in ``ck-print-preview`` so partners see the LP-
    facing question binder before they hit Cmd+P. Toolbar and
    filter chips stay visible in preview so the partner can adjust
    the cut before printing, but ``@media print`` hides them so
    the printed PDF shows only the question lists.
    """
    # 2026-05-28 batch 23 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    intro = ck_editorial_head(
        eyebrow="DILIGENCE QUESTIONS · PORTFOLIO",
        title="Every question, every deal, one ledger.",
        meta=(
            "BROWSER LOCALSTORAGE · "
            "MARKDOWN + CSV EXPORT · "
            "NO SERVER ROUNDTRIP"
        ),
        lede_italic_phrase=(
            "Every question, every deal, one ledger."
        ),
        lede_body=(
            "Reads your browser's saved question lists across every "
            "deal you've opened. Filter by category or status; copy "
            "the lot as Markdown to send to the seller; download a "
            "CSV for the IC binder. No server roundtrip — your notes "
            "stay on your machine."
        ),
    )

    chips_html = (
        '<div class="qa-filters">'
        '<div class="qa-filter-group">'
        '<span class="qa-filter-label">Status</span>'
        '<button class="qa-chip" data-rcm-qa-chip="all" '
        'data-rcm-qa-kind="status">All</button>'
        '<button class="qa-chip" data-rcm-qa-chip="open" '
        'data-rcm-qa-kind="status">Open</button>'
        '<button class="qa-chip" data-rcm-qa-chip="asked" '
        'data-rcm-qa-kind="status">Asked</button>'
        '</div>'
        '<div class="qa-filter-group">'
        '<span class="qa-filter-label">Category</span>'
        '<button class="qa-chip" data-rcm-qa-chip="all" '
        'data-rcm-qa-kind="cat">All</button>'
        '<button class="qa-chip" data-rcm-qa-chip="financial" '
        'data-rcm-qa-kind="cat">Financial</button>'
        '<button class="qa-chip" data-rcm-qa-chip="clinical" '
        'data-rcm-qa-kind="cat">Clinical</button>'
        '<button class="qa-chip" data-rcm-qa-chip="regulatory" '
        'data-rcm-qa-kind="cat">Regulatory</button>'
        '<button class="qa-chip" data-rcm-qa-chip="legal" '
        'data-rcm-qa-kind="cat">Legal</button>'
        '<button class="qa-chip" data-rcm-qa-chip="operational" '
        'data-rcm-qa-kind="cat">Operational</button>'
        '<button class="qa-chip" data-rcm-qa-chip="other" '
        'data-rcm-qa-kind="cat">Other</button>'
        '</div>'
        '</div>'
    )

    toolbar_html = (
        '<div class="qa-toolbar">'
        '<span class="qa-toolbar-eyebrow">Portfolio</span>'
        '<span class="qa-toolbar-meta" data-rcm-qa-meta>—</span>'
        '<div class="qa-toolbar-actions">'
        '<button class="qa-toolbar-btn" data-rcm-qa-md>'
        'Copy as Markdown</button>'
        '<button class="qa-toolbar-btn" data-rcm-qa-md-open>'
        'Copy open only</button>'
        '<button class="qa-toolbar-btn" data-rcm-qa-csv>'
        'Download CSV</button>'
        '<span class="qa-toolbar-toast" data-rcm-qa-toast></span>'
        '</div>'
        '</div>'
    )

    list_html = '<div data-rcm-qa-list></div>'

    next_up = ck_next_section(
        "Capture a question — Shift+Q anywhere",
        "/?v3=1",
        eyebrow="Shortcut —",
        italic_word="Shift",
    )

    if print_preview:
        body = (
            _AGG_STYLES
            + '<div class="ck-print-preview">'
            '<div class="ck-print-preview-bar">'
            '<span class="ck-print-preview-meta">'
            'Print preview · portfolio question ledger'
            '</span>'
            '<a href="/diligence/questions" '
            'class="ck-print-preview-exit">Exit preview</a>'
            '</div>'
            + intro
            + toolbar_html + chips_html + list_html
            + '</div>'
            + _AGG_JS
        )
    else:
        body = (
            _AGG_STYLES
            + '<div class="ck-print-preview-cta">'
            '<a href="/diligence/questions?print=1" '
            'class="ck-link">Preview print version →</a>'
            '</div>'
            + intro
            + ck_panel(
                toolbar_html + chips_html + list_html,
                title="Cross-deal question ledger",
            )
            + next_up
            + _AGG_JS
        )

    return chartis_shell(
        body,
        title="Diligence questions — portfolio ledger",
        active_nav="DILIGENCE",
        breadcrumbs=[
            ("Home", "/"),
            ("Diligence", "/diligence"),
            ("Questions ledger", None),
        ],
        subtitle="Every question, every deal, one editorial view",
    )
