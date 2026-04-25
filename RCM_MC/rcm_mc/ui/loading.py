"""Loading states + skeleton screens.

Professional apps never show a blank page while data loads. They
show a skeleton — gray placeholder boxes shaped like the content
to come — so the user's eye fixes on the layout while the bytes
arrive. This module ships those building blocks.

Components:

  • ``skeleton_box(width, height)`` — animated rectangular
    placeholder.
  • ``skeleton_text(width, lines)`` — text-shaped placeholder
    lines.
  • ``skeleton_table(rows, cols, with_header)`` — full table-shape
    placeholder for the ms before a power_table hydrates.
  • ``skeleton_chart(height)`` — chart-shape placeholder for the
    ms before a power_chart's <svg> renders.
  • ``loading_spinner(label, size)`` — pure-CSS spinner.
  • ``progress_bar(percent, label)`` — determinate progress.
  • ``loading_overlay(label)`` — full-screen modal overlay used
    on long form submissions.
  • ``page_progress_bar()`` — Stripe-style 2px progress bar at
    the top of the page that shows during link-click navigation.

All animations are CSS-only — no JS, no dependencies. Each helper
optionally injects its stylesheet (`inject_css=True` default);
pages with multiple skeletons can pass `inject_css=False` after
the first to dedupe.

Public API::

    from rcm_mc.ui.loading import (
        skeleton_box,
        skeleton_text,
        skeleton_table,
        skeleton_chart,
        loading_spinner,
        progress_bar,
        loading_overlay,
        page_progress_bar,
    )
"""
from __future__ import annotations

import html as _html
from typing import Any, Optional


# Single shimmer animation reused by every skeleton component.
_SKELETON_CSS = """
<style>
@keyframes skeleton-pulse {
  0%   { opacity: 1; }
  50%  { opacity: 0.5; }
  100% { opacity: 1; }
}
.sk{background:linear-gradient(
  90deg,#374151 0%,#4b5563 50%,#374151 100%);
  background-size:200% 100%;
  animation:skeleton-shimmer 1.4s linear infinite;
  border-radius:4px;display:inline-block;}
@keyframes skeleton-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.spinner{display:inline-block;width:18px;height:18px;
  border:2px solid #374151;border-top-color:#60a5fa;
  border-radius:50%;animation:spin 0.7s linear infinite;
  vertical-align:middle;}
@keyframes spin{to{transform:rotate(360deg);}}
.progress-bar{height:6px;background:#1f2937;
  border-radius:3px;overflow:hidden;position:relative;}
.progress-bar-fill{height:100%;background:#60a5fa;
  transition:width 0.3s ease-out;}
.progress-bar-indet{height:100%;width:30%;
  background:linear-gradient(90deg,
    transparent 0%,#60a5fa 50%,transparent 100%);
  animation:progress-indet 1.5s ease-in-out infinite;}
@keyframes progress-indet {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}
.loading-overlay{position:fixed;top:0;left:0;right:0;
  bottom:0;background:rgba(15,23,42,0.85);
  display:flex;align-items:center;justify-content:center;
  flex-direction:column;gap:14px;z-index:5000;}
.loading-overlay-label{color:#f3f4f6;font-size:13px;
  font-family:system-ui;}
#page-progress{position:fixed;top:0;left:0;right:0;
  height:2px;background:#60a5fa;width:0;
  transition:width 0.2s ease-out;z-index:9999;}
#page-progress.active{width:80%;}
#page-progress.done{width:100%;opacity:0;
  transition:width 0.1s,opacity 0.3s 0.1s;}
</style>"""


def _maybe_css(inject_css: bool) -> str:
    return _SKELETON_CSS if inject_css else ""


# ── Skeleton primitives ─────────────────────────────────────

def skeleton_box(
    *,
    width: str = "100%",
    height: str = "20px",
    inline: bool = False,
    inject_css: bool = True,
) -> str:
    """Animated gray placeholder rectangle.

    Args:
      width / height: any valid CSS length ('120px', '40%', etc.)
      inline: render inline-block vs block.
    """
    display = "inline-block" if inline else "block"
    return (
        _maybe_css(inject_css)
        + f'<span class="sk" style="display:{display};'
        f'width:{width};height:{height};"></span>')


def skeleton_text(
    *,
    lines: int = 3,
    last_line_width: str = "70%",
    line_height: str = "14px",
    line_gap: str = "10px",
    inject_css: bool = True,
) -> str:
    """Multi-line text placeholder. Last line shorter to mimic
    natural paragraph endings."""
    if lines <= 0:
        return ""
    bits = []
    for i in range(lines):
        is_last = (i == lines - 1)
        width = last_line_width if is_last else "100%"
        bits.append(
            f'<span class="sk" style="display:block;'
            f'width:{width};height:{line_height};'
            f'margin-bottom:{line_gap};"></span>')
    return _maybe_css(inject_css) + "".join(bits)


def skeleton_table(
    *,
    rows: int = 5,
    cols: int = 4,
    with_header: bool = True,
    inject_css: bool = True,
) -> str:
    """Full table-shape placeholder."""
    if rows <= 0 or cols <= 0:
        return ""
    cell_w = f"{100 / cols:.2f}%"

    def _row(is_header: bool, height: str) -> str:
        bg = "#111827" if is_header else "transparent"
        bar_w = "60%" if is_header else "85%"
        cells = "".join([
            f'<td style="padding:10px 14px;border-bottom:'
            f'1px solid #374151;width:{cell_w};">'
            f'<span class="sk" style="display:block;'
            f'width:{bar_w};height:{height};"></span>'
            f'</td>' for _ in range(cols)])
        return f'<tr style="background:{bg};">{cells}</tr>'

    head = _row(True, "10px") if with_header else ""
    body = "".join(_row(False, "12px")
                   for _ in range(rows))
    return (
        _maybe_css(inject_css)
        + f'<table style="width:100%;border-collapse:collapse;'
        f'background:#1f2937;border:1px solid #374151;'
        f'border-radius:8px;overflow:hidden;">'
        f'{head}{body}</table>')


def skeleton_chart(
    *,
    height: str = "240px",
    inject_css: bool = True,
) -> str:
    """Chart-shape placeholder with simulated bar shapes.

    Renders a row of vertical 'bars' of varying heights to
    suggest a chart layout.
    """
    bars_html = "".join([
        f'<span class="sk" style="display:inline-block;'
        f'width:6%;margin:0 1%;height:{h}%;'
        f'vertical-align:bottom;"></span>'
        for h in [40, 65, 50, 80, 55, 75, 45, 70, 60]
    ])
    return (
        _maybe_css(inject_css)
        + f'<div style="background:#1f2937;border:1px solid '
        f'#374151;border-radius:8px;padding:18px;'
        f'height:{height};box-sizing:border-box;'
        f'display:flex;align-items:flex-end;'
        f'justify-content:space-evenly;">'
        f'{bars_html}</div>')


# ── Spinner / progress ──────────────────────────────────────

def loading_spinner(
    label: Optional[str] = None,
    *,
    size: str = "18px",
    inject_css: bool = True,
) -> str:
    """CSS-only spinning ring. Optional label aligned right."""
    safe_label = (
        f'<span style="margin-left:10px;color:#9ca3af;'
        f'font-size:13px;vertical-align:middle;">'
        f'{_html.escape(label)}</span>' if label else "")
    return (
        _maybe_css(inject_css)
        + f'<div style="display:inline-flex;'
        f'align-items:center;">'
        f'<span class="spinner" '
        f'style="width:{size};height:{size};"></span>'
        f'{safe_label}</div>')


def progress_bar(
    *,
    percent: Optional[float] = None,
    label: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Determinate or indeterminate progress bar.

    Args:
      percent: 0-100. None → indeterminate (animated stripe).
      label: optional caption above the bar.
    """
    label_html = (
        f'<div style="color:#9ca3af;font-size:11px;'
        f'margin-bottom:6px;">{_html.escape(label)}'
        f'</div>' if label else "")
    if percent is None:
        fill = '<div class="progress-bar-indet"></div>'
    else:
        pct = max(0, min(100, float(percent)))
        fill = (f'<div class="progress-bar-fill" '
                f'style="width:{pct:.1f}%;"></div>')
    return (
        _maybe_css(inject_css)
        + label_html
        + f'<div class="progress-bar">{fill}</div>')


def loading_overlay(
    label: str = "Loading…",
    *,
    inject_css: bool = True,
) -> str:
    """Full-screen modal overlay with spinner + label.

    Used on long-running form submissions. Caller is responsible
    for hiding it once the page navigates / the response arrives.
    """
    return (
        _maybe_css(inject_css)
        + f'<div class="loading-overlay" id="loading-overlay" '
        f'role="status" aria-live="polite">'
        f'<span class="spinner" '
        f'style="width:32px;height:32px;border-width:3px;">'
        f'</span>'
        f'<div class="loading-overlay-label">'
        f'{_html.escape(label)}</div></div>')


# ── Page-level progress bar (Stripe-style) ──────────────────

_PAGE_PROGRESS_JS = """
<script>
(function() {
  var bar = document.getElementById("page-progress");
  if (!bar) return;
  // Show on link click (internal links only)
  document.addEventListener("click", function(e) {
    var a = e.target.closest("a");
    if (!a || !a.href) return;
    if (a.target === "_blank" ||
        a.hasAttribute("download") ||
        a.href.indexOf("javascript:") === 0) return;
    var url;
    try { url = new URL(a.href); }
    catch (_) { return; }
    if (url.origin !== window.location.origin) return;
    if (url.pathname === window.location.pathname &&
        url.hash) return;  // intra-page anchor
    bar.classList.remove("done");
    bar.classList.add("active");
  });
  // Hide on navigation completion
  window.addEventListener("pageshow", function() {
    bar.classList.remove("active");
    bar.classList.add("done");
    setTimeout(function() {
      bar.classList.remove("done");
      bar.style.width = "0";
    }, 400);
  });
})();
</script>"""


def page_progress_bar(*, inject_css: bool = True) -> str:
    """Stripe-style 2px progress bar at the top of the page.

    Listens for clicks on internal <a> links and shows the bar
    until the next page renders. Drop this near the top of the
    <body> on every page that uses link-click navigation.
    """
    return (
        _maybe_css(inject_css)
        + '<div id="page-progress" '
        'aria-hidden="true"></div>'
        + _PAGE_PROGRESS_JS)
