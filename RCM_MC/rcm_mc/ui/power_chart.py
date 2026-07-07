"""Power chart — interactive SVG line/bar chart with full UX.

Pairs with ``power_table.py`` as the chart half of the
power-user-basics directive. Pure SVG + vanilla JS, no chart
libraries, no runtime deps.

Renders in the editorial Chartis look by default (parchment-white
panel, house ``--sc-data-*`` series palette, JetBrains Mono ticks) so
it drops into any Chartis page; pass ``theme="dark"`` for the legacy
Bloomberg-dark frame this widget originally shipped with.

Kit boundaries (who owns what): this module is the *interactive*
chart (hover/zoom/toggle/drilldown); ``_chart_kit`` owns the static
editorial chart cards with PNG export used by the geo analysis pages;
``cdd_chart_kit`` owns the 30-type builder/exhibit family rendered
from pasted tables. Reach for the simplest layer that does the job.

Features:

  • **Hover details** — moving the cursor over the chart shows a
    tooltip with the nearest data point's value across every
    visible series (values are formatted server-side once, so the
    tooltip, the native <title>, and the axis all agree).
  • **Click to drill down** — clicking (or focusing + Enter on) a
    data point navigates to a configurable URL template (e.g.
    ``/deal/{series}?ts={x}``).
  • **Toggle series** — clicking a legend button hides or shows
    that series (keyboard accessible, ``aria-pressed`` tracked).
  • **Zoom time range** — drag horizontally on the chart to zoom
    into a sub-range; the series, points, and x-axis labels all
    rescale (not merely hide); double-click to reset.
  • **Export** — buttons to save the chart as SVG (lossless) or
    PNG (rasterized at 3× via canvas, theme-correct background).

Each instance is namespaced by ``chart_id`` so multiple charts
coexist.

Public API::

    from rcm_mc.ui.power_chart import (
        ChartSeries,
        render_power_chart,
    )
    html = render_power_chart(
        chart_id="ebitda-trend",
        title="EBITDA $M trend",
        series=[
            ChartSeries("Aurora", points=[
                ("2023Q1", 30), ("2023Q2", 32),
                ("2023Q3", 35), ("2023Q4", 38)]),
        ],
        x_kind="text",
        y_kind="money",
        drilldown_url="/deal/{series}?ts={x}")
"""
from __future__ import annotations

import html as _html
import json
import re as _re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ._chart_kit import DATA_SERIES_EXTENDED, ck_nice_ticks

# Legacy Tailwind-era palette — kept (name and values) for the dark theme
# and for any external caller that imported it directly.
_DEFAULT_PALETTE = [
    "#60a5fa", "#10b981", "#f59e0b",
    "#ef4444", "#a78bfa", "#ec4899",
    "#fb923c", "#22d3ee",
]

# Theme tokens. "editorial" is the house Chartis look (default);
# "dark" preserves the widget's original Bloomberg-dark strings.
_THEMES: Dict[str, Dict[str, Any]] = {
    "editorial": {
        "palette": list(DATA_SERIES_EXTENDED),
        "svg_style": ("background:#ffffff;border:1px solid #d6cfc0;"
                      "border-radius:4px;"),
        "grid": "#e4ddca",
        "zero": "#7a8699",
        "tick": "#7a8699",
        "tick_font": "'JetBrains Mono',ui-monospace,monospace",
        "xlabel": "#5b6b7a",
        "title": "#1a2332",
        "title_font": ("'Source Serif 4',Georgia,serif"),
        "legend_text": "#465366",
        "hint": "#7a8699",
        "btn": ("background:#ffffff;border:1px solid #d6cfc0;"
                "border-radius:3px;padding:4px 10px;color:#155752;"
                "font-size:11px;cursor:pointer;"),
        "export_bg": "#ffffff",
        "tooltip_head": "#1a2332",
    },
    "dark": {
        "palette": list(_DEFAULT_PALETTE),
        "svg_style": "background:#1f2937;border-radius:8px;",
        "grid": "#374151",
        "zero": "#6b7280",
        "tick": "#9ca3af",
        "tick_font": "ui-monospace,monospace",
        "xlabel": "#9ca3af",
        "title": "#f3f4f6",
        "title_font": "inherit",
        "legend_text": "#d1d5db",
        "hint": "#9ca3af",
        "btn": ("background:#1f2937;border:1px solid #374151;"
                "border-radius:6px;padding:4px 10px;color:#f3f4f6;"
                "font-size:11px;cursor:pointer;"),
        "export_bg": "#1a2332",
        "tooltip_head": "#1a2332",
    },
}


@dataclass
class ChartSeries:
    """One series on the chart.

    Attributes:
      name: legend label.
      points: list of (x, y) tuples. x can be string (text x-axis)
        or number (numeric x-axis). y must be numeric; ``None`` marks
        missing data and renders as a GAP in the line (never
        interpolated across, never plotted as zero).
      color: stroke color. Auto-assigned from the theme palette if
        None (note: assignment writes back onto this instance — a
        long-pinned behavior callers rely on to read the assigned
        color after rendering).
      kind: 'line' or 'bar'.
    """
    name: str
    points: List[Tuple[Any, float]]
    color: Optional[str] = None
    kind: str = "line"

    def __post_init__(self) -> None:
        if self.kind not in ("line", "bar"):
            raise ValueError(
                f"Unknown series kind: {self.kind}")


def _format_y(value: float, kind: str, precise: bool = False) -> str:
    """Axis/tooltip formatter.

    The default money buckets are deliberately coarse ("$2K" for 1500 —
    a long-pinned axis-tick behavior); ``precise=True`` opts into the
    house 2-decimal financial discipline ("$1.50K", "$1,204.50") and is
    what per-point tooltips use when ``render_power_chart`` is called
    with ``precise_values=True``."""
    if kind == "money":
        if precise:
            if abs(value) >= 1e9:
                return f"${value / 1e9:,.2f}B"
            if abs(value) >= 1e6:
                return f"${value / 1e6:,.2f}M"
            if abs(value) >= 1e3:
                return f"${value / 1e3:,.2f}K"
            return f"${value:,.2f}"
        if abs(value) >= 1e9:
            return f"${value / 1e9:,.2f}B"
        if abs(value) >= 1e6:
            return f"${value / 1e6:,.1f}M"
        if abs(value) >= 1e3:
            return f"${value / 1e3:,.0f}K"
        return f"${value:,.0f}"
    if kind == "pct":
        return f"{value * 100:+.1f}%"
    if kind == "int":
        return f"{int(value):,}"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


# Inline JS — namespaced by chart_id. Pure vanilla. The geometry
# constants (margins, plot size, y-range) ride in CONFIG_JSON so zoom
# can recompute the same x-mapping the server used: zoom genuinely
# rescales lines/bars/labels instead of merely hiding dots.
_CHART_JS = """
(function() {
  var chartId = %CHART_ID_JSON%;
  var config = %CONFIG_JSON%;
  var SVG_NS = "http://www.w3.org/2000/svg";
  var EXPORT_SCALE = 3;
  var root = document.getElementById(chartId + "-root");
  if (!root) return;
  var svg = root.querySelector("svg");
  var tooltip = root.querySelector(
    "#" + chartId + "-tooltip");
  var legend = root.querySelector(
    "#" + chartId + "-legend");
  var resetBtn = root.querySelector(
    "#" + chartId + "-reset");
  var exportSvgBtn = root.querySelector(
    "#" + chartId + "-export-svg");
  var exportPngBtn = root.querySelector(
    "#" + chartId + "-export-png");
  var L = config.layout;

  var state = {
    visible: {},
    zoom: null  // {min: int, max: int} or null
  };
  config.series.forEach(function(s) {
    state.visible[s.name] = true;
  });

  function zoomBounds() {
    var minI = state.zoom ? state.zoom.min : 0;
    var maxI = state.zoom ? state.zoom.max :
      (config.x_count - 1);
    return [minI, maxI];
  }

  function xToPx(i) {
    if (config.x_count === 1) return L.ml + L.pw / 2;
    var b = zoomBounds();
    if (L.band) {
      var count = b[1] - b[0] + 1;
      return L.ml + L.pw * ((i - b[0] + 0.5) / count);
    }
    var span = Math.max(1, b[1] - b[0]);
    return L.ml + ((i - b[0]) / span) * L.pw;
  }

  function yToPx(y) {
    var span = (L.ymax - L.ymin) || 1;
    return L.mt + L.ph - ((y - L.ymin) / span) * L.ph;
  }

  function rebuildLines(group, s) {
    group.querySelectorAll("polyline").forEach(
      function(pl) { pl.remove(); });
    var b = zoomBounds();
    var runs = [[]];
    for (var i = b[0]; i <= b[1]; i++) {
      var p = s.points[i];
      if (!p || p[1] === null || p[1] === undefined) {
        if (runs[runs.length - 1].length) runs.push([]);
        continue;
      }
      runs[runs.length - 1].push(
        xToPx(i).toFixed(1) + "," +
        yToPx(p[1]).toFixed(1));
    }
    runs.forEach(function(run) {
      if (run.length < 2) return;
      var pl = document.createElementNS(SVG_NS, "polyline");
      pl.setAttribute("points", run.join(" "));
      pl.setAttribute("fill", "none");
      pl.setAttribute("stroke", s.color);
      pl.setAttribute("stroke-width", "2");
      pl.setAttribute("stroke-linejoin", "round");
      pl.setAttribute("stroke-linecap", "round");
      group.insertBefore(pl, group.firstChild);
    });
  }

  function applyZoom() {
    var b = zoomBounds();
    var count = b[1] - b[0] + 1;
    config.series.forEach(function(s, si) {
      var seriesGroup = svg.querySelector(
        '[data-series-key="' + s.key + '"]');
      if (!seriesGroup) return;
      seriesGroup.style.display =
        state.visible[s.name] ? "" : "none";
      var marks = seriesGroup.querySelectorAll(".point");
      var nb = config.series.length || 1;
      var barW = Math.max(2, L.pw / count / nb);
      var barOffset = si - nb / 2 + 0.5;
      marks.forEach(function(el) {
        var idx = +el.getAttribute("data-i");
        if (idx < b[0] || idx > b[1]) {
          el.style.display = "none";
          return;
        }
        el.style.display = "";
        if (el.tagName.toLowerCase() === "circle") {
          el.setAttribute("cx", xToPx(idx).toFixed(1));
        } else {
          el.setAttribute("x",
            (xToPx(idx) + barOffset * barW - barW / 2)
              .toFixed(1));
          el.setAttribute("width",
            (barW * 0.85).toFixed(1));
        }
      });
      if (s.kind === "line") rebuildLines(seriesGroup, s);
    });
    // x labels: show an evenly spread subset of the zoomed range.
    var labels = svg.querySelectorAll(".xlabel");
    var want = {};
    var slots = Math.min(count, Math.max(2, L.maxLabels));
    for (var k = 0; k < slots; k++) {
      want[b[0] + Math.round(
        k * (count - 1) / Math.max(1, slots - 1))] = true;
    }
    labels.forEach(function(el) {
      var idx = +el.getAttribute("data-i");
      if (want[idx]) {
        el.style.display = "";
        el.setAttribute("x", xToPx(idx).toFixed(1));
      } else {
        el.style.display = "none";
      }
    });
  }

  function setupHover() {
    var overlay = svg.querySelector(
      "#" + chartId + "-overlay");
    if (!overlay) return;
    overlay.addEventListener("mousemove", function(e) {
      var rect = overlay.getBoundingClientRect();
      var px = e.clientX - rect.left;
      var width = rect.width || 1;
      var b = zoomBounds();
      var idx;
      if (L.band) {
        idx = b[0] + Math.floor(
          (px / width) * (b[1] - b[0] + 1));
      } else {
        idx = b[0] + Math.round(
          (px / width) * (b[1] - b[0]));
      }
      idx = Math.max(b[0], Math.min(b[1], idx));
      var lines = ['<div style="font-weight:600;' +
        'margin-bottom:4px;color:' + config.tooltip_head +
        ';">' +
        escapeHtml(config.x_labels[idx]) + '</div>'];
      config.series.forEach(function(s) {
        if (!state.visible[s.name]) return;
        var p = s.points[idx];
        if (!p || p[1] === null || p[1] === undefined)
          return;
        lines.push(
          '<div style="color:' + s.color + ';' +
          'font-size:12px;">' +
          '<span style="display:inline-block;width:8px;' +
          'height:8px;background:' + s.color + ';' +
          'border-radius:50%;margin-right:6px;"></span>' +
          escapeHtml(s.name) + ': ' +
          escapeHtml(p[2] || '') + '</div>');
      });
      tooltip.innerHTML = lines.join("");
      tooltip.style.display = "block";
      tooltip.style.left = (e.clientX -
        root.getBoundingClientRect().left + 12) + "px";
      tooltip.style.top = (e.clientY -
        root.getBoundingClientRect().top + 12) + "px";
    });
    overlay.addEventListener("mouseleave", function() {
      tooltip.style.display = "none";
    });
  }

  function setupZoom() {
    var overlay = svg.querySelector(
      "#" + chartId + "-overlay");
    if (!overlay) return;
    var dragStart = null;
    overlay.addEventListener("mousedown", function(e) {
      var rect = overlay.getBoundingClientRect();
      dragStart = e.clientX - rect.left;
    });
    overlay.addEventListener("mouseup", function(e) {
      if (dragStart === null) return;
      var rect = overlay.getBoundingClientRect();
      var dragEnd = e.clientX - rect.left;
      if (Math.abs(dragEnd - dragStart) < 8) {
        dragStart = null;
        return;
      }
      var b = zoomBounds();
      var span = b[1] - b[0];
      var x1 = Math.min(dragStart, dragEnd) / rect.width;
      var x2 = Math.max(dragStart, dragEnd) / rect.width;
      var minI = b[0] + Math.round(x1 * span);
      var maxI = b[0] + Math.round(x2 * span);
      if (maxI - minI >= 1) {
        state.zoom = {min: minI, max: maxI};
        applyZoom();
      }
      dragStart = null;
    });
    overlay.addEventListener("dblclick", function() {
      state.zoom = null;
      applyZoom();
    });
  }

  function setupLegend() {
    if (!legend) return;
    legend.querySelectorAll(
      "[data-series-toggle]").forEach(function(el) {
      el.style.cursor = "pointer";
      el.addEventListener("click", function() {
        var name = el.getAttribute(
          "data-series-toggle");
        state.visible[name] = !state.visible[name];
        el.style.opacity =
          state.visible[name] ? "1" : "0.4";
        el.setAttribute("aria-pressed",
          state.visible[name] ? "true" : "false");
        applyZoom();
      });
    });
  }

  function drill(el) {
    var x = el.getAttribute("data-x");
    var s = el.getAttribute("data-series");
    var url = config.drilldown_url
      .replace("{series}", encodeURIComponent(s))
      .replace("{x}", encodeURIComponent(x));
    window.location.href = url;
  }

  function setupDrilldown() {
    if (!config.drilldown_url) return;
    document.querySelectorAll(
      '#' + chartId + '-root .point').forEach(
      function(el) {
        el.style.cursor = "pointer";
        el.setAttribute("tabindex", "0");
        el.setAttribute("role", "link");
        el.addEventListener("click", function() {
          drill(el);
        });
        el.addEventListener("keydown", function(ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            drill(el);
          }
        });
      });
  }

  function setupExport() {
    if (exportSvgBtn) {
      exportSvgBtn.addEventListener("click", function() {
        var clone = svg.cloneNode(true);
        clone.setAttribute("xmlns", SVG_NS);
        var serializer = new XMLSerializer();
        var src = serializer.serializeToString(clone);
        var blob = new Blob(
          ['<?xml version="1.0"?>\\n', src],
          {type: "image/svg+xml"});
        downloadBlob(blob, chartId + ".svg");
      });
    }
    if (exportPngBtn) {
      exportPngBtn.addEventListener("click", function() {
        var clone = svg.cloneNode(true);
        clone.setAttribute("xmlns", SVG_NS);
        var serializer = new XMLSerializer();
        var src = serializer.serializeToString(clone);
        var img = new Image();
        var canvas = document.createElement("canvas");
        var w = svg.clientWidth || config.width;
        var h = svg.clientHeight || config.height;
        clone.setAttribute("width", w);
        clone.setAttribute("height", h);
        src = serializer.serializeToString(clone);
        canvas.width = w * EXPORT_SCALE;
        canvas.height = h * EXPORT_SCALE;
        var ctx = canvas.getContext("2d");
        var dataUrl = "data:image/svg+xml;base64," +
          btoa(unescape(encodeURIComponent(src)));
        img.onload = function() {
          ctx.fillStyle = config.bg;
          ctx.fillRect(0, 0,
            canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0,
            canvas.width, canvas.height);
          canvas.toBlob(function(blob) {
            downloadBlob(blob, chartId + ".png");
          });
        };
        img.src = dataUrl;
      });
    }
    if (resetBtn) {
      resetBtn.addEventListener("click", function() {
        state.zoom = null;
        config.series.forEach(function(s) {
          state.visible[s.name] = true;
        });
        legend.querySelectorAll(
          "[data-series-toggle]").forEach(function(el) {
          el.style.opacity = "1";
          el.setAttribute("aria-pressed", "true");
        });
        applyZoom();
      });
    }
  }

  function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function(c) {
      return ({"&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#39;"})[c];
    });
  }

  setupHover();
  setupZoom();
  setupLegend();
  setupDrilldown();
  setupExport();
})();
"""

_CHART_ID_RE = _re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def render_power_chart(
    *,
    chart_id: str,
    title: str = "",
    series: List[ChartSeries],
    x_kind: str = "text",
    y_kind: str = "number",
    width: int = 720,
    height: int = 360,
    drilldown_url: Optional[str] = None,
    theme: str = "editorial",
    precise_values: bool = False,
) -> str:
    """Render an interactive SVG chart.

    Args:
      chart_id: identifier used for JS namespacing + export filenames.
        Must start with a letter (a leading digit is a valid HTML id
        but an invalid CSS selector, which used to kill every
        querySelector-driven behavior silently).
      title: chart heading.
      series: list of ChartSeries. Auto-assigns theme palette colors
        to series without one (mutating the passed instances — pinned
        behavior).
      x_kind: 'text' (categorical) or 'number'. Drives x-axis
        rendering.
      y_kind: 'number' / 'money' / 'pct' / 'int'.
      width / height: SVG dimensions.
      drilldown_url: optional template like '/deal/{series}?ts={x}'.
        When set, clicking (or Enter on) a point navigates there.
      theme: 'editorial' (default — house Chartis look) or 'dark'
        (the widget's original palette-and-frame, preserved for any
        legacy embed).
      precise_values: when True, per-point tooltips/titles use the
        house 2-decimal financial formatting ("$1.50K") instead of
        the coarse axis buckets ("$2K"). Off by default for
        byte-compatibility with existing renders.

    Returns: complete HTML+SVG+JS string.
    """
    if not _CHART_ID_RE.match(chart_id):
        raise ValueError(
            f"chart_id must start with a letter and contain only "
            f"[A-Za-z0-9_-]: {chart_id!r}")
    if not series:
        raise ValueError("Need ≥1 series")
    tokens = _THEMES.get(theme)
    if tokens is None:
        raise ValueError(
            f"Unknown theme: {theme!r} (editorial|dark)")

    # Assign palette colors to series without one
    palette = tokens["palette"]
    for i, s in enumerate(series):
        if s.color is None:
            s.color = palette[i % len(palette)]

    # Build x-axis labels — assume all series share the same
    # x-axis (caller responsible). Use the longest series' x
    # values as canonical.
    canonical_x: List[Any] = []
    for s in series:
        if len(s.points) > len(canonical_x):
            canonical_x = [p[0] for p in s.points]
    n = len(canonical_x)
    if n == 0:
        raise ValueError("All series are empty")

    # Compute y-range across visible series
    all_y = [p[1] for s in series for p in s.points
             if p[1] is not None]
    if not all_y:
        raise ValueError(
            "All series have no numeric y-values")
    y_min = min(all_y)
    y_max = max(all_y)
    # Bars encode value as LENGTH from zero, so the y-range must
    # include zero — anchoring bars at an arbitrary padded data-min
    # both lies about magnitude and (the old bug) let bar rects
    # overflow the plot by hundreds of px.
    has_bar = any(s.kind == "bar" for s in series)
    if has_bar:
        y_min = min(y_min, 0.0)
        y_max = max(y_max, 0.0)
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    # Pad by 5%
    pad = (y_max - y_min) * 0.05
    y_min -= pad
    y_max += pad

    # Plot area
    margin_l = 60
    margin_r = 24
    margin_t = 24
    margin_b = 50
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b

    def _x_to_px(i: int) -> float:
        if n == 1:
            return margin_l + plot_w / 2
        if has_bar:
            # Band scale — bar groups (and any companion line) center
            # inside per-category bands so the first/last bars can't
            # hang off the left/right plot edges the way the
            # point-scale placed them.
            return margin_l + plot_w * ((i + 0.5) / n)
        return margin_l + (i / (n - 1)) * plot_w

    def _y_to_px(y: float) -> float:
        return (margin_t + plot_h
                - (y - y_min) / (y_max - y_min) * plot_h)

    # Axis ticks — round numbers via the shared nice-ticks helper
    # (falls back to even spacing on degenerate ranges).
    tick_vals = ck_nice_ticks(y_min, y_max, 5)
    if len(tick_vals) < 2:
        tick_vals = [y_min + (y_max - y_min) * i / 4
                     for i in range(5)]
    y_ticks = [(v, _y_to_px(v), _format_y(v, y_kind))
               for v in tick_vals]

    # x-axis labels — show every nth so they don't overlap
    n_labels = min(n, max(2, plot_w // 80))
    label_index_set = set(
        [round(i * (n - 1) / (n_labels - 1))
         for i in range(n_labels)]
        if n_labels > 1 else [n // 2])

    # SVG elements
    elements: List[str] = []

    # Background grid + y ticks
    for v, py, label in y_ticks:
        elements.append(
            f'<line x1="{margin_l}" y1="{py}" '
            f'x2="{margin_l + plot_w}" y2="{py}" '
            f'stroke="{tokens["grid"]}" stroke-width="0.5" '
            f'stroke-dasharray="2,3"/>')
        elements.append(
            f'<text x="{margin_l - 6}" y="{py + 4}" '
            f'fill="{tokens["tick"]}" font-size="10" '
            f'text-anchor="end" '
            f'font-family="{tokens["tick_font"]}">'
            f'{_html.escape(label)}</text>')

    # Zero axis line — bars hang off it; negative line series read
    # against it.
    if y_min < 0 < y_max and (has_bar or min(all_y) < 0):
        zero_py = _y_to_px(0.0)
        elements.append(
            f'<line x1="{margin_l}" y1="{zero_py:.1f}" '
            f'x2="{margin_l + plot_w}" y2="{zero_py:.1f}" '
            f'stroke="{tokens["zero"]}" stroke-width="1"/>')

    # x-axis labels — ALL indices render (each tagged data-i) so JS
    # zoom can re-space them; the non-selected ones start hidden so
    # the no-JS view matches the classic density.
    for i in range(n):
        hide = '' if i in label_index_set else 'display="none" '
        elements.append(
            f'<text class="xlabel" data-i="{i}" '
            f'x="{_x_to_px(i):.1f}" '
            f'y="{margin_t + plot_h + 16}" {hide}'
            f'fill="{tokens["xlabel"]}" font-size="10" '
            f'text-anchor="middle">'
            f'{_html.escape(str(canonical_x[i]))}'
            f'</text>')

    # Series
    series_keys: List[str] = []
    for si, s in enumerate(series):
        sname_safe = "".join(
            c if c.isalnum() else "_" for c in s.name)
        # Distinct names can sanitize to the same key ('A B' vs
        # 'A_B'); the index suffix keeps group lookup unambiguous.
        skey = f"{sname_safe}__{si}"
        series_keys.append(skey)
        if s.kind == "line":
            # Build polyline runs — a None y-value is a GAP: the line
            # breaks rather than interpolating across missing data
            # (same convention as the cdd kit, so a gap means one
            # thing estate-wide).
            runs: List[List[str]] = [[]]
            for i in range(min(n, len(s.points))):
                p = s.points[i]
                if p[1] is None:
                    if runs[-1]:
                        runs.append([])
                    continue
                runs[-1].append(
                    f"{_x_to_px(i):.1f},"
                    f"{_y_to_px(p[1]):.1f}")
            polylines = "".join(
                f'<polyline points="{" ".join(run)}" '
                f'fill="none" stroke="{s.color}" '
                f'stroke-width="2" '
                f'stroke-linejoin="round" '
                f'stroke-linecap="round"/>'
                for run in runs if len(run) >= 2)
            elements.append(
                f'<g data-series="{sname_safe}" '
                f'data-series-key="{skey}">'
                + polylines
                + "".join(
                    f'<circle class="point" '
                    f'cx="{_x_to_px(i):.1f}" '
                    f'cy="{_y_to_px(s.points[i][1]):.1f}" '
                    f'r="3.5" fill="{s.color}" '
                    f'data-i="{i}" '
                    f'data-x="{_html.escape(str(s.points[i][0]))}" '
                    f'data-series="{_html.escape(s.name)}">'
                    f'<title>{_html.escape(s.name)}: '
                    f'{_html.escape(_format_y(s.points[i][1], y_kind, precise=precise_values))}'
                    f'</title></circle>'
                    for i in range(min(n, len(s.points)))
                    if s.points[i][1] is not None)
                + '</g>')
        else:  # bar
            bar_w = max(2, plot_w / n / max(1, len(series)))
            bar_offset = (
                series.index(s) - len(series) / 2 + 0.5)
            # Bars anchor at the zero line (guaranteed in-range —
            # see y-range above), so positives grow up, negatives
            # grow down, and nothing overflows the plot.
            base_v = min(max(0.0, y_min), y_max)
            base_px = _y_to_px(base_v)

            def _bar_geom(v: float,
                          _base: float = base_px) -> Tuple[float, float]:
                py = _y_to_px(v)
                return (min(py, _base), abs(_base - py))
            elements.append(
                f'<g data-series="{sname_safe}" '
                f'data-series-key="{skey}">'
                + "".join(
                    f'<rect class="point" '
                    f'x="{_x_to_px(i) + bar_offset * bar_w - bar_w / 2:.1f}" '
                    f'y="{_bar_geom(s.points[i][1])[0]:.1f}" '
                    f'width="{bar_w * 0.85:.1f}" '
                    f'height="{_bar_geom(s.points[i][1])[1]:.1f}" '
                    f'fill="{s.color}" data-i="{i}" '
                    f'data-x="{_html.escape(str(s.points[i][0]))}" '
                    f'data-series="{_html.escape(s.name)}">'
                    f'<title>{_html.escape(s.name)}: '
                    f'{_html.escape(_format_y(s.points[i][1], y_kind, precise=precise_values))}'
                    f'</title></rect>'
                    for i in range(min(n, len(s.points)))
                    if s.points[i][1] is not None)
                + '</g>')

    # Hover overlay (last so it sits on top)
    elements.append(
        f'<rect id="{chart_id}-overlay" '
        f'x="{margin_l}" y="{margin_t}" '
        f'width="{plot_w}" height="{plot_h}" '
        f'fill="transparent" cursor="crosshair"/>')

    # Title text
    if title:
        elements.insert(
            0,
            f'<text x="{margin_l}" y="16" '
            f'fill="{tokens["title"]}" font-size="13" '
            f'font-family="{tokens["title_font"]}" '
            f'font-weight="600">'
            f'{_html.escape(title)}</text>')

    aria = title or f"{chart_id} chart"
    svg = (
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="{_html.escape(aria)}" '
        f'style="{tokens["svg_style"]}">'
        f'<title>{_html.escape(aria)}</title>'
        + "".join(elements)
        + '</svg>'
    )

    # Legend — real buttons so series toggling is keyboard/AT
    # reachable; aria-pressed mirrors visibility.
    legend_html = (
        f'<div id="{chart_id}-legend" '
        f'style="display:flex;flex-wrap:wrap;gap:14px;'
        f'margin-top:8px;font-size:12px;">'
        + "".join(
            f'<button type="button" '
            f'data-series-toggle="{_html.escape(s.name)}" '
            f'aria-pressed="true" '
            f'style="display:flex;align-items:center;gap:6px;'
            f'color:{tokens["legend_text"]};user-select:none;'
            f'background:transparent;border:none;padding:0;'
            f'font-size:12px;cursor:pointer;">'
            f'<span style="display:inline-block;width:10px;'
            f'height:10px;background:{s.color};'
            f'border-radius:2px;"></span>'
            f'{_html.escape(s.name)}</button>'
            for s in series)
        + '</div>')

    # Toolbar
    toolbar_html = (
        f'<div style="display:flex;gap:8px;'
        f'margin-bottom:8px;align-items:center;">'
        f'<div style="flex:1;color:{tokens["hint"]};font-size:11px;">'
        f'Drag x-axis to zoom · double-click to reset</div>'
        f'<button id="{chart_id}-reset" type="button" '
        f'style="{tokens["btn"]}">'
        f'Reset</button>'
        f'<button id="{chart_id}-export-svg" type="button" '
        f'style="{tokens["btn"]}">'
        f'SVG</button>'
        f'<button id="{chart_id}-export-png" type="button" '
        f'style="{tokens["btn"]}">'
        f'PNG</button>'
        f'</div>')

    # Tooltip
    tooltip_html = (
        f'<div id="{chart_id}-tooltip" '
        f'style="position:absolute;display:none;'
        f'background:#FAF7F0;border:1px solid #D6CFC0;'
        f'color:#1a2332;'
        f'border-radius:2px;padding:8px 10px;font-size:11px;'
        f'pointer-events:none;z-index:100;'
        f'font-family:\'Inter Tight\',\'Inter\',sans-serif;'
        f'box-shadow:0 8px 20px -8px rgba(15,28,46,.25);"></div>')

    # Per-point display strings are serialized once, server-side, so
    # the JS tooltip can never disagree with the native <title> (the
    # old client-side formatY drifted on sign and decimals).
    config = {
        "x_count": n,
        "x_labels": [str(x) for x in canonical_x],
        "x_kind": x_kind,
        "y_kind": y_kind,
        "drilldown_url": drilldown_url,
        "bg": tokens["export_bg"],
        "tooltip_head": tokens["tooltip_head"],
        "width": width,
        "height": height,
        "layout": {
            "ml": margin_l,
            "mt": margin_t,
            "pw": plot_w,
            "ph": plot_h,
            "ymin": y_min,
            "ymax": y_max,
            "band": has_bar,
            "maxLabels": n_labels,
        },
        "series": [
            {"name": s.name, "key": series_keys[si],
             "color": s.color,
             "kind": s.kind,
             "points": [
                 [str(p[0]),
                  float(p[1]) if p[1] is not None
                  else None,
                  (_format_y(p[1], y_kind,
                             precise=precise_values)
                   if p[1] is not None else "")]
                 for p in s.points],
             }
            for si, s in enumerate(series)
        ],
    }
    # "</" → "<\/" inside the JSON payload: identical once JSON-parsed,
    # but a series name / x label containing "</script>" can no longer
    # terminate the inline <script> block early (html.escape rule —
    # this is the script-context equivalent).
    config_json = json.dumps(config, default=str).replace("</", "<\\/")
    js = (_CHART_JS
          .replace("%CHART_ID_JSON%",
                   json.dumps(chart_id))
          .replace("%CONFIG_JSON%", config_json))

    return (
        f'<div id="{chart_id}-root" '
        f'style="position:relative;">'
        + toolbar_html
        + svg
        + legend_html
        + tooltip_html
        + f'<script>{js}</script>'
        + '</div>'
    )
