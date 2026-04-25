"""Power table — reusable sortable / filterable / exportable HTML table.

The existing tables across the platform are static HTML. The
directive calls these the 'power-user basics': sort by clicking
column headers, search across all rows, filter individual columns,
toggle which columns are visible, export the visible rows as CSV.

This module ships one component that any page can drop in:

    from rcm_mc.ui.power_table import render_power_table, Column
    html = render_power_table(
        table_id="deals",
        columns=[
            Column("name", "Deal", kind="text"),
            Column("npr", "NPR", kind="money"),
            Column("ebitda_margin", "EBITDA %",
                   kind="pct", filterable=False),
        ],
        rows=[
            {"name": "Aurora", "npr": 350_000_000,
             "ebitda_margin": 0.12},
            ...
        ])

All interactivity is **vanilla JS** — no dependencies, no
client-side framework. Each component instance is namespaced by
``table_id`` so multiple power tables can coexist on one page.

Public API::

    Column                # column-config dataclass
    render_power_table()  # produce HTML+JS string
"""
from __future__ import annotations

import html as _html
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


# Column kinds drive formatting + sort comparator behavior.
COLUMN_KINDS = {
    "text", "number", "money", "pct", "date", "int",
}


@dataclass
class Column:
    """One column in the power table.

    Attributes:
      key: dict-key in row data. Required.
      label: header text shown to the user. Defaults to key.
      kind: 'text'|'number'|'money'|'pct'|'date'|'int'. Drives
        formatting + numeric vs string sort.
      filterable: whether this column shows a filter input below
        the header. Default True; set False on derived/computed
        columns.
      visible: initial visibility. Toggle menu lets user override.
      align: 'left'|'right'|'center'. Defaults: numbers right,
        text/date left.
    """
    key: str
    label: str = ""
    kind: str = "text"
    filterable: bool = True
    visible: bool = True
    align: Optional[str] = None

    def __post_init__(self) -> None:
        if self.kind not in COLUMN_KINDS:
            raise ValueError(
                f"Unknown column kind: {self.kind}")
        if not self.label:
            self.label = self.key.replace(
                "_", " ").title()
        if self.align is None:
            self.align = ("right"
                          if self.kind in
                          ("number", "money", "pct", "int")
                          else "left")


def _format_cell(value: Any, kind: str) -> str:
    if value is None or value == "":
        return ""
    try:
        if kind == "money":
            v = float(value)
            if abs(v) >= 1e9:
                return f"${v / 1e9:,.2f}B"
            if abs(v) >= 1e6:
                return f"${v / 1e6:,.1f}M"
            if abs(v) >= 1e3:
                return f"${v / 1e3:,.0f}K"
            return f"${v:,.0f}"
        if kind == "pct":
            return f"{float(value) * 100:+.1f}%"
        if kind == "int":
            return f"{int(value):,}"
        if kind == "number":
            v = float(value)
            return (f"{v:,.0f}" if abs(v) >= 100
                    else f"{v:,.3f}")
    except (TypeError, ValueError):
        pass
    return str(value)


def _color_for_kind(kind: str) -> str:
    return ("#d1d5db" if kind in
            ("number", "money", "pct", "int")
            else "#f3f4f6")


# Inline JS — namespaced by table_id so multiple tables coexist.
# Pure vanilla JS; works in IE11+ but tested mainly in Chrome.
_TABLE_JS = """
(function() {
  var tableId = %TABLE_ID_JSON%;
  var columns = %COLUMNS_JSON%;
  var rows = %ROWS_JSON%;
  var state = {
    sortKey: null, sortDir: 0,
    search: "",
    filters: {},
    visible: {}
  };
  columns.forEach(function(c) {
    state.filters[c.key] = "";
    state.visible[c.key] = c.visible !== false;
  });

  var root = document.getElementById(tableId + "-root");
  if (!root) return;
  var tbody = root.querySelector("tbody");
  var searchInput = root.querySelector(
    "#" + tableId + "-search");
  var exportBtn = root.querySelector(
    "#" + tableId + "-export");
  var colMenuBtn = root.querySelector(
    "#" + tableId + "-cols-btn");
  var colMenu = root.querySelector(
    "#" + tableId + "-cols-menu");

  function visibleColumns() {
    return columns.filter(function(c) {
      return state.visible[c.key];
    });
  }

  function isNumeric(kind) {
    return kind === "number" || kind === "money" ||
           kind === "pct" || kind === "int";
  }

  function compare(a, b, key, kind, dir) {
    var av = a[key], bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return dir;
    if (bv == null) return -dir;
    if (isNumeric(kind)) {
      return dir * ((+av) - (+bv));
    }
    return dir * String(av).localeCompare(String(bv));
  }

  function sortedFilteredRows() {
    var s = (state.search || "").toLowerCase();
    var fr = rows.filter(function(r) {
      // Global search across all visible columns
      if (s) {
        var match = visibleColumns().some(function(c) {
          var v = r[c.key];
          return v != null &&
                 String(v).toLowerCase().indexOf(s) >= 0;
        });
        if (!match) return false;
      }
      // Per-column filters
      for (var k in state.filters) {
        var f = (state.filters[k] || "").toLowerCase();
        if (!f) continue;
        var v = r[k];
        if (v == null) return false;
        if (String(v).toLowerCase().indexOf(f) < 0) {
          return false;
        }
      }
      return true;
    });
    if (state.sortKey && state.sortDir !== 0) {
      var col = columns.find(function(c) {
        return c.key === state.sortKey;
      }) || {kind: "text"};
      fr.sort(function(a, b) {
        return compare(a, b, state.sortKey,
                       col.kind, state.sortDir);
      });
    }
    return fr;
  }

  function renderRows() {
    var visible = visibleColumns();
    var displayed = sortedFilteredRows();
    var html = "";
    if (displayed.length === 0) {
      html = '<tr><td colspan="' + visible.length +
        '" style="padding:24px;color:#9ca3af;' +
        'text-align:center;font-size:13px;">' +
        'No rows match the current filters.</td></tr>';
    } else {
      displayed.forEach(function(r) {
        html += "<tr>";
        visible.forEach(function(c) {
          var v = r[c.key];
          var formatted = r["_fmt_" + c.key] != null ?
            r["_fmt_" + c.key] :
            (v == null ? "" : String(v));
          html += '<td style="padding:10px 14px;' +
            'border-bottom:1px solid #374151;' +
            'text-align:' + (c.align || "left") + ';' +
            'color:' + (isNumeric(c.kind) ?
              "#d1d5db" : "#f3f4f6") + ';' +
            'font-variant-numeric:' +
            (isNumeric(c.kind) ?
              "tabular-nums" : "normal") + ';">' +
            escapeHtml(formatted) + "</td>";
        });
        html += "</tr>";
      });
    }
    tbody.innerHTML = html;
    var counter = root.querySelector(
      "#" + tableId + "-count");
    if (counter) {
      counter.textContent =
        displayed.length.toLocaleString() +
        " of " + rows.length.toLocaleString();
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function(c) {
      return ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#39;"
      })[c];
    });
  }

  function setupSort() {
    root.querySelectorAll("th[data-sortable]").forEach(
      function(th) {
        th.style.cursor = "pointer";
        th.addEventListener("click", function() {
          var key = th.getAttribute("data-key");
          if (state.sortKey === key) {
            state.sortDir = state.sortDir === 1 ?
              -1 : (state.sortDir === -1 ? 0 : 1);
          } else {
            state.sortKey = key;
            state.sortDir = 1;
          }
          if (state.sortDir === 0) state.sortKey = null;
          updateSortIndicators();
          renderRows();
        });
      });
  }

  function updateSortIndicators() {
    root.querySelectorAll("th[data-sortable]").forEach(
      function(th) {
        var key = th.getAttribute("data-key");
        var ind = th.querySelector(".sort-ind");
        if (!ind) return;
        if (state.sortKey === key) {
          ind.textContent = state.sortDir === 1 ?
            " ▲" : " ▼";
        } else {
          ind.textContent = "";
        }
      });
  }

  function setupFilters() {
    root.querySelectorAll("[data-filter-key]").forEach(
      function(input) {
        var key = input.getAttribute(
          "data-filter-key");
        input.addEventListener("input", function() {
          state.filters[key] = input.value;
          renderRows();
        });
      });
  }

  function setupSearch() {
    if (!searchInput) return;
    searchInput.addEventListener("input", function() {
      state.search = searchInput.value;
      renderRows();
    });
  }

  function setupExport() {
    if (!exportBtn) return;
    exportBtn.addEventListener("click", function() {
      var displayed = sortedFilteredRows();
      var visible = visibleColumns();
      var headers = visible.map(function(c) {
        return c.label;
      });
      var lines = [headers.map(csvCell).join(",")];
      displayed.forEach(function(r) {
        lines.push(visible.map(function(c) {
          var v = r[c.key];
          return csvCell(v == null ? "" : v);
        }).join(","));
      });
      var blob = new Blob([lines.join("\\n")],
        {type: "text/csv"});
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = tableId + ".csv";
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  function csvCell(v) {
    var s = String(v);
    // Defang Excel formula injection
    if (s && /^[=+\\-@]/.test(s)) {
      s = "'" + s;
    }
    if (s.indexOf(",") >= 0 || s.indexOf("\\"") >= 0 ||
        s.indexOf("\\n") >= 0) {
      s = '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  }

  function setupColumnToggle() {
    if (!colMenuBtn || !colMenu) return;
    colMenuBtn.addEventListener("click", function(e) {
      e.stopPropagation();
      colMenu.style.display =
        colMenu.style.display === "block" ?
          "none" : "block";
    });
    document.addEventListener("click", function(e) {
      if (!colMenu.contains(e.target) &&
          e.target !== colMenuBtn) {
        colMenu.style.display = "none";
      }
    });
    colMenu.querySelectorAll(
      "input[type=checkbox]").forEach(function(cb) {
      cb.addEventListener("change", function() {
        var key = cb.getAttribute("data-col-key");
        state.visible[key] = cb.checked;
        // Hide / show table column header + filter cell
        root.querySelectorAll(
          '[data-col="' + key + '"]').forEach(
            function(el) {
              el.style.display = cb.checked ?
                "" : "none";
            });
        renderRows();
      });
    });
  }

  setupSort();
  setupFilters();
  setupSearch();
  setupExport();
  setupColumnToggle();
  renderRows();
})();
"""


def render_power_table(
    *,
    table_id: str,
    columns: List[Column],
    rows: Iterable[Dict[str, Any]],
    show_search: bool = True,
    show_export: bool = True,
    show_column_toggle: bool = True,
) -> str:
    """Render a power table.

    Args:
      table_id: unique identifier (used to namespace JS state +
        as the export filename). Must be alphanumeric + dashes.
      columns: list of Column dataclass instances.
      rows: iterable of dicts with column.key → value.
      show_search: render the global search input.
      show_export: render the CSV export button.
      show_column_toggle: render the columns visibility menu.

    Returns: complete HTML+JS string. Drop into any page that
    serves dark-theme HTML.
    """
    if not table_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError(
            f"table_id must be alphanumeric: {table_id!r}")

    # Pre-format every cell server-side so JS doesn't need to
    # know our formatters. Stored on each row as
    # _fmt_<column_key> alongside the raw value.
    rows_list: List[Dict[str, Any]] = []
    for r in rows:
        row_copy = dict(r)
        for c in columns:
            v = r.get(c.key)
            row_copy[f"_fmt_{c.key}"] = _format_cell(
                v, c.kind)
        rows_list.append(row_copy)

    # Toolbar
    toolbar_parts: List[str] = []
    if show_search:
        toolbar_parts.append(
            f'<input id="{table_id}-search" type="search" '
            f'placeholder="Search…" '
            f'style="background:#1f2937;border:1px solid '
            f'#374151;border-radius:6px;padding:6px 10px;'
            f'color:#f3f4f6;font-size:13px;flex:1;'
            f'min-width:180px;">')
    if show_column_toggle:
        toggle_items = "".join([
            f'<label style="display:flex;align-items:center;'
            f'gap:8px;padding:6px 10px;color:#f3f4f6;'
            f'font-size:13px;cursor:pointer;">'
            f'<input type="checkbox" '
            f'data-col-key="{_html.escape(c.key)}" '
            f'{"checked" if c.visible else ""}> '
            f'{_html.escape(c.label)}</label>'
            for c in columns
        ])
        toolbar_parts.append(
            f'<div style="position:relative;">'
            f'<button id="{table_id}-cols-btn" '
            f'type="button" '
            f'style="background:#1f2937;border:1px solid '
            f'#374151;border-radius:6px;padding:6px 12px;'
            f'color:#f3f4f6;font-size:13px;cursor:pointer;">'
            f'Columns ▾</button>'
            f'<div id="{table_id}-cols-menu" '
            f'style="display:none;position:absolute;top:100%;'
            f'right:0;margin-top:4px;background:#111827;'
            f'border:1px solid #374151;border-radius:6px;'
            f'padding:4px;min-width:180px;z-index:10;">'
            f'{toggle_items}</div></div>')
    if show_export:
        toolbar_parts.append(
            f'<button id="{table_id}-export" '
            f'type="button" '
            f'style="background:#1f2937;border:1px solid '
            f'#374151;border-radius:6px;padding:6px 12px;'
            f'color:#f3f4f6;font-size:13px;cursor:pointer;">'
            f'Export CSV</button>')

    counter_html = (
        f'<span id="{table_id}-count" '
        f'style="color:#9ca3af;font-size:12px;'
        f'font-variant-numeric:tabular-nums;">'
        f'{len(rows_list):,} of {len(rows_list):,}</span>')

    toolbar = (
        f'<div style="display:flex;gap:10px;'
        f'align-items:center;margin-bottom:10px;">'
        f'{counter_html}'
        f'<div style="flex:1;"></div>'
        + "".join(toolbar_parts) + '</div>'
    )

    # Header row
    header_cells = []
    for c in columns:
        sort_attr = ' data-sortable="1"'
        sort_ind = '<span class="sort-ind"></span>'
        header_cells.append(
            f'<th data-key="{_html.escape(c.key)}" '
            f'data-col="{_html.escape(c.key)}"{sort_attr} '
            f'style="padding:10px 14px;text-align:'
            f'{c.align};font-size:11px;text-transform:'
            f'uppercase;letter-spacing:0.05em;'
            f'color:#9ca3af;background:#111827;'
            f'border-bottom:1px solid #374151;'
            f'{"display:none;" if not c.visible else ""}">'
            f'{_html.escape(c.label)}{sort_ind}</th>')

    # Filter row
    filter_cells = []
    for c in columns:
        if c.filterable:
            filter_cells.append(
                f'<th data-col="{_html.escape(c.key)}" '
                f'style="padding:6px 14px;'
                f'background:#1f2937;'
                f'border-bottom:1px solid #374151;'
                f'{"display:none;" if not c.visible else ""}">'
                f'<input type="text" '
                f'data-filter-key="{_html.escape(c.key)}" '
                f'placeholder="filter…" '
                f'style="width:100%;background:#0f172a;'
                f'border:1px solid #374151;border-radius:'
                f'4px;padding:3px 6px;color:#f3f4f6;'
                f'font-size:11px;"></th>')
        else:
            filter_cells.append(
                f'<th data-col="{_html.escape(c.key)}" '
                f'style="padding:6px 14px;'
                f'background:#1f2937;'
                f'border-bottom:1px solid #374151;'
                f'{"display:none;" if not c.visible else ""}">'
                f'</th>')

    table_html = (
        f'<div class="rs-table-wrap" '
        f'style="background:#1f2937;border:1px solid '
        f'#374151;border-radius:8px;'
        f'overflow:hidden;overflow-x:auto;'
        f'-webkit-overflow-scrolling:touch;">'
        f'<table style="width:100%;border-collapse:collapse;'
        f'min-width:max-content;">'
        f'<thead>'
        f'<tr>{"".join(header_cells)}</tr>'
        f'<tr>{"".join(filter_cells)}</tr>'
        f'</thead>'
        f'<tbody>'
        + "".join(
            f'<tr>{"".join(f"<td style=padding:10px-14px;border-bottom:1px-solid-#374151;>"+"X"+"</td>" for _ in range(len(columns)))}</tr>'
            for _ in range(0))  # placeholder; replaced below
        + ''.join(
            '<tr>' + ''.join(
                f'<td style="padding:10px 14px;'
                f'border-bottom:1px solid #374151;">'
                f'<span style="display:block;'
                f'background:linear-gradient(90deg,'
                f'#374151 0%,#4b5563 50%,#374151 100%);'
                f'background-size:200% 100%;'
                f'animation:skeleton-shimmer 1.4s '
                f'linear infinite;border-radius:4px;'
                f'height:12px;width:80%;"></span></td>'
                for _ in range(len(columns)))
            + '</tr>' for _ in range(min(5, len(rows_list)) or 5))
        + '<style>@keyframes skeleton-shimmer{'
        '0%{background-position:200% 0;}'
        '100%{background-position:-200% 0;}}</style>'
        + f'</tbody>'
        f'</table></div>'
    )

    columns_serializable = [
        {"key": c.key, "label": c.label, "kind": c.kind,
         "align": c.align, "visible": c.visible}
        for c in columns
    ]

    js = (_TABLE_JS
          .replace("%TABLE_ID_JSON%",
                   json.dumps(table_id))
          .replace("%COLUMNS_JSON%",
                   json.dumps(columns_serializable))
          .replace("%ROWS_JSON%",
                   json.dumps(rows_list, default=str)))

    return (
        f'<div id="{table_id}-root">'
        + toolbar
        + table_html
        + f'<script>{js}</script>'
        + '</div>'
    )
