/**
 * power_ui.js — PE-analyst power features.
 *
 * Zero dependencies. Vanilla JS only. Gracefully degrades: every
 * feature is opt-in via data-attributes, and missing support (no
 * clipboard API, no localStorage) falls back to a no-op without
 * throwing.
 *
 * Features:
 *   data-sortable     → click <th> to sort column
 *   data-filterable   → search input filters rows
 *   data-export       → CSV export button auto-injected
 *   data-export-json  → JSON export button for panels
 *   data-provenance   → hover tooltip with source info
 *   keyboard shortcuts (? overlay, / search focus, Cmd+K palette,
 *                        gd gr gq … nav jumps)
 *   save-view bookmark (localStorage)
 */
(function () {
  "use strict";

  const RCM_SAVED_VIEWS_KEY = "rcm_saved_views_v1";
  const RCM_BOOKMARK_STAR = "★";
  const RCM_BOOKMARK_HOLLOW = "☆";

  // ── Sortable tables ────────────────────────────────────────────
  function initSortable(table) {
    const tbody = table.querySelector("tbody");
    if (!tbody) return;
    const headers = table.querySelectorAll("thead th");
    headers.forEach((th, colIdx) => {
      th.style.cursor = "pointer";
      th.style.userSelect = "none";
      th.setAttribute("role", "button");
      th.setAttribute("tabindex", "0");
      if (!th.querySelector(".rcm-sort-arrow")) {
        const arrow = document.createElement("span");
        arrow.className = "rcm-sort-arrow";
        arrow.textContent = " ↕";
        arrow.style.opacity = "0.4";
        arrow.style.fontSize = "9px";
        th.appendChild(arrow);
      }
      const handler = () => sortByColumn(table, colIdx, th);
      th.addEventListener("click", handler);
      th.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handler();
        }
      });
    });
  }

  function sortByColumn(table, colIdx, headerEl) {
    const tbody = table.querySelector("tbody");
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll("tr")).filter(
      (r) => r.dataset.filterHidden !== "1",
    );
    if (!rows.length) return;
    const currentDir = headerEl.dataset.sortDir || "none";
    const newDir = currentDir === "asc" ? "desc" : "asc";
    // Clear arrows on other headers.
    const allHeaders = table.querySelectorAll("thead th");
    allHeaders.forEach((h) => {
      if (h !== headerEl) {
        delete h.dataset.sortDir;
        const a = h.querySelector(".rcm-sort-arrow");
        if (a) {
          a.textContent = " ↕";
          a.style.opacity = "0.4";
        }
      }
    });
    headerEl.dataset.sortDir = newDir;
    const arrow = headerEl.querySelector(".rcm-sort-arrow");
    if (arrow) {
      arrow.textContent = newDir === "asc" ? " ▲" : " ▼";
      arrow.style.opacity = "1";
    }
    rows.sort((a, b) => {
      const av = cellSortKey(a.cells[colIdx]);
      const bv = cellSortKey(b.cells[colIdx]);
      if (av === bv) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      const cmp =
        typeof av === "number" && typeof bv === "number"
          ? av - bv
          : String(av).localeCompare(String(bv), undefined, {
              numeric: true,
              sensitivity: "base",
            });
      return newDir === "asc" ? cmp : -cmp;
    });
    rows.forEach((r) => tbody.appendChild(r));
  }

  function cellSortKey(cell) {
    if (!cell) return null;
    const raw = (cell.dataset.sortKey || cell.textContent || "").trim();
    if (!raw) return null;
    // Strip currency / percent / commas for numeric compare.
    const cleaned = raw.replace(/[$,]/g, "").replace(/%$/, "");
    const num = parseFloat(cleaned);
    if (!Number.isNaN(num) && /^-?\d/.test(cleaned)) return num;
    return raw.toLowerCase();
  }

  // ── Filterable tables ──────────────────────────────────────────
  function initFilterable(table) {
    if (!table.id) table.id = "rcm-table-" + Math.random().toString(36).slice(2, 8);
    const container = document.createElement("div");
    container.className = "rcm-filter-bar";
    container.innerHTML =
      '<input type="search" class="rcm-filter-input" ' +
      'placeholder="Filter rows… (/ to focus)">' +
      '<span class="rcm-filter-count"></span>';
    table.parentNode.insertBefore(container, table);
    const input = container.querySelector(".rcm-filter-input");
    const counter = container.querySelector(".rcm-filter-count");
    input.addEventListener("input", () => applyFilter(table, input.value, counter));
    applyFilter(table, "", counter);
    input.dataset.rcmFilterInput = "1";
  }

  function applyFilter(table, query, counter) {
    const q = query.trim().toLowerCase();
    const tbody = table.querySelector("tbody");
    if (!tbody) return;
    const rows = tbody.querySelectorAll("tr");
    let shown = 0;
    rows.forEach((r) => {
      const text = r.textContent.toLowerCase();
      const match = !q || text.includes(q);
      r.style.display = match ? "" : "none";
      r.dataset.filterHidden = match ? "0" : "1";
      if (match) shown++;
    });
    if (counter) {
      counter.textContent = q
        ? `${shown} of ${rows.length}`
        : `${rows.length} rows`;
    }
  }

  // ── CSV export ─────────────────────────────────────────────────
  function initExport(table) {
    const wrapper = document.createElement("div");
    wrapper.className = "rcm-export-row";
    const csvBtn = document.createElement("button");
    csvBtn.className = "rcm-export-btn";
    csvBtn.type = "button";
    csvBtn.textContent = "Export CSV";
    csvBtn.addEventListener("click", () => exportTableCsv(table));
    wrapper.appendChild(csvBtn);
    table.parentNode.insertBefore(wrapper, table);
  }

  function exportTableCsv(table) {
    const rows = [];
    table.querySelectorAll("tr").forEach((tr) => {
      if (tr.dataset.filterHidden === "1") return;
      const cells = Array.from(tr.querySelectorAll("th,td")).map((c) =>
        csvEscape((c.dataset.exportValue || c.textContent || "").trim()),
      );
      rows.push(cells.join(","));
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    downloadBlob(
      blob,
      (table.dataset.exportName || "export") + ".csv",
    );
  }

  function csvEscape(v) {
    if (v == null) return "";
    if (/[",\n]/.test(v)) return '"' + v.replace(/"/g, '""') + '"';
    return v;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ── JSON export on panels ──────────────────────────────────────
  function initJsonExport(container) {
    const payload = container.getAttribute("data-export-json");
    if (!payload) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "rcm-export-btn rcm-export-btn-json";
    btn.textContent = "Export JSON";
    btn.addEventListener("click", () => {
      try {
        const obj = JSON.parse(payload);
        const blob = new Blob([JSON.stringify(obj, null, 2)], {
          type: "application/json",
        });
        downloadBlob(
          blob,
          (container.dataset.exportName || "export") + ".json",
        );
      } catch (e) {
        console.warn("rcm_power_ui: bad json", e);
      }
    });
    // Place at top-right corner of the panel.
    if (getComputedStyle(container).position === "static") {
      container.style.position = "relative";
    }
    btn.style.position = "absolute";
    btn.style.top = "8px";
    btn.style.right = "8px";
    container.appendChild(btn);
  }

  // ── Provenance tooltips ────────────────────────────────────────
  function initProvenance(el) {
    // Re-use a singleton tooltip element.
    let tip = document.getElementById("rcm-provenance-tip");
    if (!tip) {
      tip = document.createElement("div");
      tip.id = "rcm-provenance-tip";
      tip.className = "rcm-provenance-tip";
      tip.setAttribute("role", "tooltip");
      document.body.appendChild(tip);
    }
    el.style.borderBottom = el.style.borderBottom || "1px dotted currentColor";
    el.style.cursor = "help";
    el.addEventListener("mouseenter", (e) => {
      showProvenance(tip, el);
    });
    el.addEventListener("mouseleave", () => {
      tip.style.display = "none";
    });
    el.addEventListener("focus", () => showProvenance(tip, el));
    el.addEventListener("blur", () => {
      tip.style.display = "none";
    });
  }

  function showProvenance(tip, el) {
    const src = el.dataset.provenance || "";
    const formula = el.dataset.provenanceFormula || "";
    const detail = el.dataset.provenanceDetail || "";
    let html = '<div class="rcm-prov-label">Provenance</div>';
    if (src) html += '<div class="rcm-prov-src">' + escapeHtml(src) + "</div>";
    if (formula)
      html +=
        '<div class="rcm-prov-formula"><code>' +
        escapeHtml(formula) +
        "</code></div>";
    if (detail) html += '<div class="rcm-prov-detail">' + escapeHtml(detail) + "</div>";
    tip.innerHTML = html;
    tip.style.display = "block";
    const rect = el.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();
    let top = rect.bottom + 6 + window.scrollY;
    let left = rect.left + window.scrollX;
    // Clamp to viewport.
    if (left + tipRect.width > window.innerWidth - 8) {
      left = window.innerWidth - tipRect.width - 8;
    }
    if (left < 8) left = 8;
    tip.style.top = top + "px";
    tip.style.left = left + "px";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ── Keyboard shortcuts ─────────────────────────────────────────
  const SHORTCUTS = [
    { keys: "?", label: "Show this help overlay" },
    { keys: "/", label: "Focus the row filter on the current page" },
    { keys: "⌘K  /  Ctrl+K", label: "Open command palette" },
    { keys: "g then d", label: "Go to Risk Workbench (demo)" },
    { keys: "g then c", label: "Go to Counterfactual Advisor" },
    { keys: "g then b", label: "Go to Bankruptcy Scan" },
    { keys: "g then q", label: "Go to QoE Memo landing" },
    { keys: "g then e", label: "Go to Engagements" },
    { keys: "g then h", label: "Go to Home" },
    { keys: "b", label: "Bookmark this view to your saved views" },
    { keys: "s", label: "Open saved views" },
    { keys: "Esc", label: "Close overlays" },
  ];

  const NAV_JUMPS = {
    d: "/diligence/risk-workbench?demo=steward",
    c: "/diligence/counterfactual",
    b: "/screening/bankruptcy-survivor",
    q: "/diligence/qoe-memo",
    e: "/engagements",
    h: "/home",
    w: "/diligence/risk-workbench",
  };

  let gPendingTimeout = null;
  let gActive = false;

  function initKeyboard() {
    document.addEventListener("keydown", (e) => {
      // Don't fire when typing in a form field.
      const tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" ||
          e.target.isContentEditable) {
        if (e.key === "Escape") e.target.blur();
        return;
      }
      if (e.metaKey && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        openCommandPalette();
        return;
      }
      if (e.ctrlKey && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        openCommandPalette();
        return;
      }
      if (e.key === "?") {
        e.preventDefault();
        toggleHelpOverlay();
        return;
      }
      if (e.key === "/") {
        const input = document.querySelector('[data-rcm-filter-input]');
        if (input) {
          e.preventDefault();
          input.focus();
        }
        return;
      }
      if (e.key === "Escape") {
        closeOverlays();
        return;
      }
      if (e.key === "b" && !e.metaKey && !e.ctrlKey) {
        bookmarkCurrentView();
        return;
      }
      if (e.key === "s" && !e.metaKey && !e.ctrlKey) {
        openSavedViews();
        return;
      }
      if (e.key === "g") {
        gActive = true;
        if (gPendingTimeout) clearTimeout(gPendingTimeout);
        gPendingTimeout = setTimeout(() => {
          gActive = false;
        }, 1500);
        return;
      }
      if (gActive) {
        const target = NAV_JUMPS[e.key];
        if (target) {
          e.preventDefault();
          window.location.href = target;
        }
        gActive = false;
      }
    });
  }

  // ── Help overlay ───────────────────────────────────────────────
  function toggleHelpOverlay() {
    let overlay = document.getElementById("rcm-help-overlay");
    if (overlay) {
      overlay.remove();
      return;
    }
    overlay = document.createElement("div");
    overlay.id = "rcm-help-overlay";
    overlay.className = "rcm-overlay";
    overlay.innerHTML = `
      <div class="rcm-overlay-body">
        <div class="rcm-overlay-head">
          <div class="rcm-overlay-title">Keyboard Shortcuts</div>
          <button type="button" class="rcm-overlay-close" aria-label="Close">×</button>
        </div>
        <div class="rcm-overlay-content">
          ${SHORTCUTS.map(
            (s) => `
            <div class="rcm-shortcut-row">
              <kbd class="rcm-kbd">${escapeHtml(s.keys)}</kbd>
              <span class="rcm-shortcut-label">${escapeHtml(s.label)}</span>
            </div>
          `,
          ).join("")}
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector(".rcm-overlay-close").addEventListener(
      "click", () => overlay.remove(),
    );
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.remove();
    });
  }

  // ── Command palette ────────────────────────────────────────────
  function openCommandPalette() {
    let palette = document.getElementById("rcm-palette");
    if (palette) {
      palette.remove();
      return;
    }
    palette = document.createElement("div");
    palette.id = "rcm-palette";
    palette.className = "rcm-overlay rcm-palette";
    const options = [
      { label: "Risk Workbench (Steward demo)", url: "/diligence/risk-workbench?demo=steward" },
      { label: "Risk Workbench (empty)", url: "/diligence/risk-workbench" },
      { label: "Counterfactual Advisor", url: "/diligence/counterfactual" },
      { label: "Bankruptcy-Survivor Scan", url: "/screening/bankruptcy-survivor" },
      { label: "QoE Memo", url: "/diligence/qoe-memo" },
      { label: "Benchmarks (Phase 2)", url: "/diligence/benchmarks" },
      { label: "Ingestion (Phase 1)", url: "/diligence/ingest" },
      { label: "Engagements", url: "/engagements" },
      { label: "Admin: Audit Chain", url: "/admin/audit-chain" },
      { label: "Compare (side-by-side)", url: "/diligence/compare" },
    ];
    palette.innerHTML = `
      <div class="rcm-overlay-body rcm-palette-body">
        <input type="text" class="rcm-palette-input" placeholder="Jump to… (Esc to close)" autofocus>
        <div class="rcm-palette-list">
          ${options
            .map(
              (o) => `
            <div class="rcm-palette-item" data-url="${escapeHtml(o.url)}" tabindex="0">
              <span class="rcm-palette-label">${escapeHtml(o.label)}</span>
              <span class="rcm-palette-url">${escapeHtml(o.url)}</span>
            </div>
          `,
            )
            .join("")}
        </div>
      </div>
    `;
    document.body.appendChild(palette);
    const input = palette.querySelector(".rcm-palette-input");
    const items = palette.querySelectorAll(".rcm-palette-item");
    function filter() {
      const q = input.value.toLowerCase().trim();
      let firstVisible = null;
      items.forEach((it) => {
        const m = !q || it.textContent.toLowerCase().includes(q);
        it.style.display = m ? "" : "none";
        if (m && !firstVisible) firstVisible = it;
      });
      items.forEach((it) => it.classList.remove("rcm-palette-active"));
      if (firstVisible) firstVisible.classList.add("rcm-palette-active");
    }
    filter();
    input.addEventListener("input", filter);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const active = palette.querySelector(".rcm-palette-active");
        if (active) window.location.href = active.dataset.url;
      } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const visible = Array.from(items).filter(
          (it) => it.style.display !== "none",
        );
        const activeIdx = visible.findIndex((it) =>
          it.classList.contains("rcm-palette-active"),
        );
        let nextIdx = activeIdx;
        if (e.key === "ArrowDown") nextIdx = (activeIdx + 1) % visible.length;
        if (e.key === "ArrowUp")
          nextIdx = (activeIdx - 1 + visible.length) % visible.length;
        items.forEach((it) => it.classList.remove("rcm-palette-active"));
        if (visible[nextIdx]) visible[nextIdx].classList.add("rcm-palette-active");
      }
    });
    items.forEach((it) =>
      it.addEventListener("click", () => {
        window.location.href = it.dataset.url;
      }),
    );
    palette.addEventListener("click", (e) => {
      if (e.target === palette) palette.remove();
    });
    setTimeout(() => input.focus(), 10);
  }

  function closeOverlays() {
    ["rcm-help-overlay", "rcm-palette", "rcm-saved-overlay"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.remove();
    });
  }

  // ── Saved views / bookmarks ────────────────────────────────────
  function loadSavedViews() {
    try {
      const raw = localStorage.getItem(RCM_SAVED_VIEWS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }
  function storeSavedViews(list) {
    try {
      localStorage.setItem(RCM_SAVED_VIEWS_KEY, JSON.stringify(list));
      return true;
    } catch (e) {
      return false;
    }
  }

  function bookmarkCurrentView() {
    const url = window.location.pathname + window.location.search;
    const title =
      document.querySelector('[data-rcm-title]')?.textContent ||
      document.title ||
      url;
    const note = prompt("Label this view:", title.trim().slice(0, 80));
    if (note === null) return; // cancelled
    const list = loadSavedViews();
    // If an entry with the same URL exists, update.
    const existing = list.findIndex((v) => v.url === url);
    const entry = { label: note || title.trim(), url, saved_at: new Date().toISOString() };
    if (existing >= 0) list[existing] = entry;
    else list.unshift(entry);
    storeSavedViews(list);
    flashToast("Saved: " + entry.label);
  }

  function openSavedViews() {
    closeOverlays();
    const list = loadSavedViews();
    const panel = document.createElement("div");
    panel.id = "rcm-saved-overlay";
    panel.className = "rcm-overlay";
    const rows = list.length
      ? list
          .map(
            (v, i) => `
          <div class="rcm-saved-row">
            <a href="${escapeHtml(v.url)}" class="rcm-saved-link">
              ${escapeHtml(v.label)}
            </a>
            <span class="rcm-saved-url">${escapeHtml(v.url)}</span>
            <button type="button" class="rcm-saved-del"
              data-idx="${i}" aria-label="Remove">×</button>
          </div>
        `,
          )
          .join("")
      : '<div class="rcm-saved-empty">No saved views yet. Press <kbd>b</kbd> on any page to bookmark it.</div>';
    panel.innerHTML = `
      <div class="rcm-overlay-body">
        <div class="rcm-overlay-head">
          <div class="rcm-overlay-title">Saved Views</div>
          <button type="button" class="rcm-overlay-close" aria-label="Close">×</button>
        </div>
        <div class="rcm-overlay-content">${rows}</div>
      </div>
    `;
    document.body.appendChild(panel);
    panel.querySelector(".rcm-overlay-close").addEventListener("click", () => panel.remove());
    panel.addEventListener("click", (e) => {
      if (e.target === panel) panel.remove();
    });
    panel.querySelectorAll(".rcm-saved-del").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const idx = parseInt(btn.dataset.idx, 10);
        const list = loadSavedViews();
        list.splice(idx, 1);
        storeSavedViews(list);
        panel.remove();
        openSavedViews();
      });
    });
  }

  function flashToast(message) {
    let toast = document.getElementById("rcm-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "rcm-toast";
      toast.className = "rcm-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("rcm-toast-visible");
    setTimeout(() => toast.classList.remove("rcm-toast-visible"), 1800);
  }

  // ── Init ───────────────────────────────────────────────────────
  function init() {
    document.querySelectorAll("table[data-sortable]").forEach(initSortable);
    document.querySelectorAll("table[data-filterable]").forEach(initFilterable);
    document.querySelectorAll("table[data-export]").forEach(initExport);
    document.querySelectorAll("[data-export-json]").forEach(initJsonExport);
    document.querySelectorAll("[data-provenance]").forEach(initProvenance);
    initKeyboard();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Public API for dynamically injected content.
  window.rcmPowerUI = {
    refresh: init,
    bookmark: bookmarkCurrentView,
    openPalette: openCommandPalette,
    openSaved: openSavedViews,
    toggleHelp: toggleHelpOverlay,
  };
})();
