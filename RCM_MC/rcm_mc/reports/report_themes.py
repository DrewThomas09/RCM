"""
Step 88: Report theme system.

Provides CSS themes for HTML reports: default, dark, print-optimized, minimal.
"""
from __future__ import annotations

from typing import Dict

THEMES: Dict[str, str] = {
    "default": """
        :root {
            --bg: #ffffff; --card: #ffffff; --text: #1a1a2e;
            --primary: #0f4c75; --accent: #3282b8; --success: #059669;
            --warning: #d97706; --danger: #dc2626; --gray: #6b7280;
            --border: #e5e7eb; --shadow: rgba(0,0,0,0.06);
        }
    """,
    "dark": """
        :root {
            --bg: #0f172a; --card: #1e293b; --text: #e2e8f0;
            --primary: #38bdf8; --accent: #818cf8; --success: #34d399;
            --warning: #fbbf24; --danger: #f87171; --gray: #94a3b8;
            --border: #334155; --shadow: rgba(0,0,0,0.3);
        }
        body { background: var(--bg); color: var(--text); }
        .card { background: var(--card); border-color: var(--border); }
        table th { background: #334155; color: var(--text); }
        table td { border-color: var(--border); }
    """,
    "print": """
        :root {
            --bg: #ffffff; --card: #ffffff; --text: #000000;
            --primary: #000000; --accent: #333333; --success: #000000;
            --warning: #333333; --danger: #000000; --gray: #666666;
            --border: #cccccc; --shadow: none;
        }
        body { font-size: 10pt; line-height: 1.4; }
        .card { box-shadow: none; border: 1px solid #ccc; }
        nav { display: none !important; }
    """,
    "minimal": """
        :root {
            --bg: #fafafa; --card: #ffffff; --text: #333333;
            --primary: #555555; --accent: #777777; --success: #4a9; 
            --warning: #a94; --danger: #a44; --gray: #999999;
            --border: #eeeeee; --shadow: none;
        }
        body { font-family: 'Georgia', serif; }
        .card { border-radius: 0; box-shadow: none; border-bottom: 1px solid var(--border); }
    """,
}


def get_theme_css(theme_name: str = "default") -> str:
    """Return CSS for the requested theme."""
    return THEMES.get(theme_name, THEMES["default"])
