"""Power chart — interactive SVG line/bar chart with full UX.

Pairs with ``power_table.py`` as the chart half of the
power-user-basics directive. Pure SVG + vanilla JS, no chart
libraries, no runtime deps. Drop into any page that serves
dark-theme HTML.

Features:

  • **Hover details** — moving the cursor over the chart shows a
    tooltip with the nearest data point's value across every
    visible series.
  • **Click to drill down** — clicking a data point navigates to
    a configurable URL template (e.g.
    ``/deal/{series}?ts={x}``).
  • **Toggle series** — clicking a legend item hides or shows
    that series.
  • **Zoom time range** — drag horizontally on the x-axis to
    zoom into a sub-range; double-click to reset.
  • **Export** — buttons to save the chart as SVG (lossless) or
    PNG (rasterized via canvas).

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
                ("2023Q3", 35), ("2023Q4", 38)],
                color="#60a5fa"),
        ],
        x_kind="text",
        y_kind="money",
        drilldown_url="/deal/{series}?ts={x}")
"""
from __future__ import annotations

import html as _html
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


_DEFAULT_PALETTE = [
    "#60a5fa", "#10b981", "#f59e0b",
    "#ef4444", "#a78bfa", "#ec4899",
    "#fb923c", "#22d3ee",
]


@dataclass
class ChartSeries:
    """One series on the chart.

    Attributes:
      name: legend label.
      points: list of (x, y) tuples. x can be string (text x-axis)
        or number (numeric x-axis). y must be numeric.
      color: stroke color. Auto-assigned from palette if None.
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


def _format_y(value: float, kind: str) -> str:
    if kind == "money":
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
    return f"{value:,.3f}"


# Inline JS — namespaced by chart_id. Pure vanilla.
_CHART_JS = """
(function() {
  var chartId = %CHART_ID_JSON%;
  var config = %CONFIG_JSON%;
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

  var state = {
    visible: {},
    zoom: null  // {min: int, max: int} or null
  };
  config.series.forEach(function(s) {
    state.visible[s.name] = true;
  });

  function applyZoom() {
    var allPoints = [];
    config.series.forEach(function(s) {
      if (!state.visible[s.name]) return;
      s.points.forEach(function(p, i) {
        allPoints.push({i: i, ts: p[0], y: p[1],
                        series: s.name});
      });
    });
    var minI = state.zoom ? state.zoom.min : 0;
    var maxI = state.zoom ? state.zoom.max :
      (config.x_count - 1);
    config.series.forEach(function(s) {
      var seriesGroup = svg.querySelector(
        '[data-series="' + cssEscape(s.name) + '"]');
      if (!seriesGroup) return;
      seriesGroup.style.display =
        state.visible[s.name] ? "" : "none";
    });
    document.querySelectorAll(
      '#' + chartId + '-root .point').forEach(
      function(el) {
        var idx = +el.getAttribute("data-i");
        if (idx < minI || idx > maxI) {
          el.style.display = "none";
        } else {
          el.style.display = "";
        }
      });
  }

  function cssEscape(s) {
    return String(s).replace(/[^a-zA-Z0-9_-]/g, "_");
  }

  function setupHover() {
    var overlay = svg.querySelector(
      "#" + chartId + "-overlay");
    if (!overlay) return;
    overlay.addEventListener("mousemove", function(e) {
      var rect = overlay.getBoundingClientRect();
      var px = e.clientX - rect.left;
      var width = rect.width;
      var idx = Math.round(
        (px / width) * (config.x_count - 1));
      idx = Math.max(0, Math.min(
        config.x_count - 1, idx));
      var minI = state.zoom ? state.zoom.min : 0;
      var maxI = state.zoom ? state.zoom.max :
        (config.x_count - 1);
      idx = Math.max(minI, Math.min(maxI, idx));
      var lines = ['<div style="font-weight:600;' +
        'margin-bottom:4px;color:#f3f4f6;">' +
        escapeHtml(config.x_labels[idx]) + '</div>'];
      config.series.forEach(function(s) {
        if (!state.visible[s.name]) return;
        var p = s.points[idx];
        if (!p) return;
        lines.push(
          '<div style="color:' + s.color + ';' +
          'font-size:12px;">' +
          '<span style="display:inline-block;width:8px;' +
          'height:8px;background:' + s.color + ';' +
          'border-radius:50%;margin-right:6px;"></span>' +
          escapeHtml(s.name) + ': ' +
          escapeHtml(formatY(p[1])) + '</div>');
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
      var x1 = Math.min(dragStart, dragEnd) / rect.width;
      var x2 = Math.max(dragStart, dragEnd) / rect.width;
      var minI = Math.round(x1 * (config.x_count - 1));
      var maxI = Math.round(x2 * (config.x_count - 1));
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
        applyZoom();
      });
    });
  }

  function setupDrilldown() {
    if (!config.drilldown_url) return;
    document.querySelectorAll(
      '#' + chartId + '-root .point').forEach(
      function(el) {
        el.style.cursor = "pointer";
        el.addEventListener("click", function() {
          var x = el.getAttribute("data-x");
          var s = el.getAttribute("data-series");
          var url = config.drilldown_url
            .replace("{series}", encodeURIComponent(s))
            .replace("{x}", encodeURIComponent(x));
          window.location.href = url;
        });
      });
  }

  function setupExport() {
    if (exportSvgBtn) {
      exportSvgBtn.addEventListener("click", function() {
        var clone = svg.cloneNode(true);
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
        clone.setAttribute("xmlns",
          "http://www.w3.org/2000/svg");
        var serializer = new XMLSerializer();
        var src = serializer.serializeToString(clone);
        var img = new Image();
        var canvas = document.createElement("canvas");
        canvas.width = svg.clientWidth || 720;
        canvas.height = svg.clientHeight || 360;
        var ctx = canvas.getContext("2d");
        var dataUrl = "data:image/svg+xml;base64," +
          btoa(unescape(encodeURIComponent(src)));
        img.onload = function() {
          ctx.fillStyle = "#0f172a";
          ctx.fillRect(0, 0,
            canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0);
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

  function formatY(v) {
    var k = config.y_kind;
    if (k === "money") {
      var av = Math.abs(v);
      if (av >= 1e9) return "$" +
        (v / 1e9).toFixed(2) + "B";
      if (av >= 1e6) return "$" +
        (v / 1e6).toFixed(1) + "M";
      if (av >= 1e3) return "$" +
        (v / 1e3).toFixed(0) + "K";
      return "$" + v.toFixed(0);
    }
    if (k === "pct") {
      return (v * 100).toFixed(1) + "%";
    }
    if (k === "int") {
      return Math.round(v).toLocaleString();
    }
    return v.toFixed(2);
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
) -> str:
    """Render an interactive SVG chart.

    Args:
      chart_id: alphanumeric identifier (used for JS namespacing
        + export filenames).
      title: chart heading.
      series: list of ChartSeries. Auto-assigns colors if missing.
      x_kind: 'text' (categorical) or 'number'. Drives x-axis
        rendering.
      y_kind: 'number' / 'money' / 'pct' / 'int'.
      width / height: SVG dimensions.
      drilldown_url: optional template like
        '/deal/{series}?ts={x}'. When set, clicking a point
        navigates there.

    Returns: complete HTML+SVG+JS string.
    """
    if not chart_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError(
            f"chart_id must be alphanumeric: {chart_id!r}")
    if not series:
        raise ValueError("Need ≥1 series")

    # Assign palette colors to series without one
    for i, s in enumerate(series):
        if s.color is None:
            s.color = _DEFAULT_PALETTE[
                i % len(_DEFAULT_PALETTE)]

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
        return margin_l + (i / (n - 1)) * plot_w

    def _y_to_px(y: float) -> float:
        return (margin_t + plot_h
                - (y - y_min) / (y_max - y_min) * plot_h)

    # Axis ticks (y: 5 evenly spaced)
    y_ticks = []
    for i in range(5):
        v = y_min + (y_max - y_min) * i / 4
        y_ticks.append(
            (v, _y_to_px(v),
             _format_y(v, y_kind)))

    # x-axis labels — show every nth so they don't overlap
    n_labels = min(n, max(2, plot_w // 80))
    label_indices = (
        [round(i * (n - 1) / (n_labels - 1))
         for i in range(n_labels)]
        if n_labels > 1 else [n // 2])
    label_indices = sorted(set(label_indices))

    # SVG elements
    elements: List[str] = []

    # Background grid + y ticks
    for v, py, label in y_ticks:
        elements.append(
            f'<line x1="{margin_l}" y1="{py}" '
            f'x2="{margin_l + plot_w}" y2="{py}" '
            f'stroke="#374151" stroke-width="0.5" '
            f'stroke-dasharray="2,3"/>')
        elements.append(
            f'<text x="{margin_l - 6}" y="{py + 4}" '
            f'fill="#9ca3af" font-size="10" '
            f'text-anchor="end" '
            f'font-family="ui-monospace,monospace">'
            f'{_html.escape(label)}</text>')

    # x-axis labels
    for i in label_indices:
        if 0 <= i < n:
            elements.append(
                f'<text x="{_x_to_px(i):.1f}" '
                f'y="{margin_t + plot_h + 16}" '
                f'fill="#9ca3af" font-size="10" '
                f'text-anchor="middle">'
                f'{_html.escape(str(canonical_x[i]))}'
                f'</text>')

    # Series
    for s in series:
        sname_safe = "".join(
            c if c.isalnum() else "_" for c in s.name)
        if s.kind == "line":
            # Build polyline
            pts = []
            for i in range(min(n, len(s.points))):
                p = s.points[i]
                if p[1] is None:
                    continue
                pts.append(
                    f"{_x_to_px(i):.1f},"
                    f"{_y_to_px(p[1]):.1f}")
            elements.append(
                f'<g data-series="{sname_safe}">'
                f'<polyline points="{" ".join(pts)}" '
                f'fill="none" stroke="{s.color}" '
                f'stroke-width="2" '
                f'stroke-linejoin="round" '
                f'stroke-linecap="round"/>'
                + "".join(
                    f'<circle class="point" '
                    f'cx="{_x_to_px(i):.1f}" '
                    f'cy="{_y_to_px(s.points[i][1]):.1f}" '
                    f'r="3.5" fill="{s.color}" '
                    f'data-i="{i}" '
                    f'data-x="{_html.escape(str(s.points[i][0]))}" '
                    f'data-series="{_html.escape(s.name)}">'
                    f'<title>{_html.escape(s.name)}: '
                    f'{_html.escape(_format_y(s.points[i][1], y_kind))}'
                    f'</title></circle>'
                    for i in range(min(n, len(s.points)))
                    if s.points[i][1] is not None)
                + '</g>')
        else:  # bar
            bar_w = max(2, plot_w / n / max(1, len(series)))
            bar_offset = (
                series.index(s) - len(series) / 2 + 0.5)
            elements.append(
                f'<g data-series="{sname_safe}">'
                + "".join(
                    f'<rect class="point" '
                    f'x="{_x_to_px(i) + bar_offset * bar_w - bar_w / 2:.1f}" '
                    f'y="{_y_to_px(s.points[i][1]):.1f}" '
                    f'width="{bar_w * 0.85:.1f}" '
                    f'height="{(_y_to_px(min(0, s.points[i][1])) - _y_to_px(s.points[i][1])):.1f}" '
                    f'fill="{s.color}" data-i="{i}" '
                    f'data-x="{_html.escape(str(s.points[i][0]))}" '
                    f'data-series="{_html.escape(s.name)}">'
                    f'<title>{_html.escape(s.name)}: '
                    f'{_html.escape(_format_y(s.points[i][1], y_kind))}'
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
            f'fill="#f3f4f6" font-size="13" '
            f'font-weight="600">'
            f'{_html.escape(title)}</text>')

    svg = (
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="background:#1f2937;border-radius:8px;">'
        + "".join(elements)
        + '</svg>'
    )

    # Legend
    legend_html = (
        f'<div id="{chart_id}-legend" '
        f'style="display:flex;flex-wrap:wrap;gap:14px;'
        f'margin-top:8px;font-size:12px;">'
        + "".join(
            f'<div data-series-toggle="{_html.escape(s.name)}" '
            f'style="display:flex;align-items:center;gap:6px;'
            f'color:#d1d5db;user-select:none;">'
            f'<span style="display:inline-block;width:10px;'
            f'height:10px;background:{s.color};'
            f'border-radius:2px;"></span>'
            f'{_html.escape(s.name)}</div>'
            for s in series)
        + '</div>')

    # Toolbar
    toolbar_html = (
        f'<div style="display:flex;gap:8px;'
        f'margin-bottom:8px;align-items:center;">'
        f'<div style="flex:1;color:#9ca3af;font-size:11px;">'
        f'Drag x-axis to zoom · double-click to reset</div>'
        f'<button id="{chart_id}-reset" type="button" '
        f'style="background:#1f2937;border:1px solid '
        f'#374151;border-radius:6px;padding:4px 10px;'
        f'color:#f3f4f6;font-size:11px;cursor:pointer;">'
        f'Reset</button>'
        f'<button id="{chart_id}-export-svg" type="button" '
        f'style="background:#1f2937;border:1px solid '
        f'#374151;border-radius:6px;padding:4px 10px;'
        f'color:#f3f4f6;font-size:11px;cursor:pointer;">'
        f'SVG</button>'
        f'<button id="{chart_id}-export-png" type="button" '
        f'style="background:#1f2937;border:1px solid '
        f'#374151;border-radius:6px;padding:4px 10px;'
        f'color:#f3f4f6;font-size:11px;cursor:pointer;">'
        f'PNG</button>'
        f'</div>')

    # Tooltip
    tooltip_html = (
        f'<div id="{chart_id}-tooltip" '
        f'style="position:absolute;display:none;'
        f'background:#111827;border:1px solid #374151;'
        f'border-radius:6px;padding:8px 10px;font-size:11px;'
        f'pointer-events:none;z-index:100;'
        f'box-shadow:0 4px 12px rgba(0,0,0,0.4);"></div>')

    config = {
        "x_count": n,
        "x_labels": [str(x) for x in canonical_x],
        "x_kind": x_kind,
        "y_kind": y_kind,
        "drilldown_url": drilldown_url,
        "series": [
            {"name": s.name, "color": s.color,
             "kind": s.kind,
             "points": [
                 [str(p[0]),
                  float(p[1]) if p[1] is not None
                  else None]
                 for p in s.points],
             }
            for s in series
        ],
    }
    js = (_CHART_JS
          .replace("%CHART_ID_JSON%",
                   json.dumps(chart_id))
          .replace("%CONFIG_JSON%",
                   json.dumps(config, default=str)))

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
