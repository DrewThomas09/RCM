"""CSS styles and head markup for the HTML report.

Kept as a single string constant so html_report.py stays focused on
structure and data. The content is identical to what was previously
inlined — do not hand-edit without regenerating golden-master baselines.
"""
from __future__ import annotations


REPORT_HEAD_STYLES = """
    :root {
      --primary: #0f4c81; --primary-light: #1a6bb3; --accent: #0891b2;
      --slate: #0f172a; --gray: #475569; --border: #e2e8f0;
      --bg: #f8fafc; --card-bg: #fff; --shadow: 0 4px 6px -1px rgba(0,0,0,.08), 0 2px 4px -2px rgba(0,0,0,.06);
      --green: #059669; --amber: #d97706; --red: #dc2626;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; scroll-padding-top: 60px; }
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: var(--bg); color: var(--slate); line-height: 1.6; }
    .container { max-width: 1024px; margin: 0 auto; padding: 2rem; padding-top: 70px; }
    h1 { font-size: 1.875rem; font-weight: 700; margin: 0 0 0.5rem 0; background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    h2 { font-size: 1.25rem; font-weight: 600; color: var(--slate); margin: 2.5rem 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid var(--border); }
    h3 { font-size: 1rem; font-weight: 600; color: var(--gray); margin: 1.5rem 0 0.5rem 0; }
    p { margin: 0.5rem 0; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; background: var(--card-bg); border-radius: 8px; overflow: hidden; box-shadow: var(--shadow); }
    th, td { border: 1px solid var(--border); padding: 12px 16px; text-align: left; }
    td.num { text-align: right; font-variant-numeric: tabular-nums; }
    table.money-table td:not(:first-child) { text-align: right; font-variant-numeric: tabular-nums; }
    th { background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%); font-weight: 600; color: var(--slate); }
    tr:nth-child(even) { background: #fafbfc; }
    .meta { color: var(--gray); font-size: 0.85rem; margin-bottom: 1.5rem; }
    .highlight { background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border-left: 4px solid var(--primary); box-shadow: var(--shadow); }
    .highlight strong { color: var(--primary); }
    .card { background: var(--card-bg); border: 1px solid var(--border); padding: 1.25rem; border-radius: 12px; margin: 1rem 0; box-shadow: var(--shadow); }
    .insight-list { margin: 0.5rem 0; padding-left: 1.5rem; }
    .insight-list li { margin: 0.5rem 0; line-height: 1.5; }
    .section-desc { color: var(--gray); font-size: 0.9rem; margin-bottom: 0.5rem; }
    code { background: #f1f5f9; padding: 2px 8px; border-radius: 6px; font-size: 0.85em; }
    details { margin: 0.5rem 0; }
    details summary { cursor: pointer; font-weight: 600; color: var(--primary); font-size: 0.9rem; padding: 0.5rem 0; }
    details summary:hover { color: var(--accent); }

    /* Sticky navigation bar */
    .report-nav { position: fixed; top: 0; left: 0; right: 0; z-index: 100; background: rgba(255,255,255,.97); backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,.06); }
    .report-nav-inner { max-width: 1024px; margin: 0 auto; padding: 0.5rem 2rem; display: flex; align-items: center; gap: 0.25rem; overflow-x: auto; white-space: nowrap; }
    .report-nav a { font-size: 0.75rem; color: var(--gray); text-decoration: none; padding: 6px 10px; border-radius: 6px; transition: all 0.15s; font-weight: 500; flex-shrink: 0; }
    .report-nav a:hover { background: #f1f5f9; color: var(--primary); }
    .report-nav .nav-brand { font-weight: 700; color: var(--primary); font-size: 0.8rem; margin-right: 0.5rem; }
    .report-nav .nav-sep { color: var(--border); margin: 0 0.1rem; }

    /* KPI dashboard cards */
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
    .kpi-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem; box-shadow: var(--shadow); text-align: center; transition: transform 0.15s, box-shadow 0.15s; }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px -4px rgba(0,0,0,.1); }
    .kpi-card .kpi-label { font-size: 0.75rem; font-weight: 600; color: var(--gray); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
    .kpi-card .kpi-value { font-size: 1.5rem; font-weight: 700; color: var(--primary); font-variant-numeric: tabular-nums; }
    .kpi-card .kpi-sub { font-size: 0.75rem; color: var(--gray); margin-top: 0.25rem; }
    .kpi-card.kpi-accent .kpi-value { color: var(--accent); }
    .kpi-card.kpi-green .kpi-value { color: var(--green); }

    /* Reading guide legend */
    .reading-guide { background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin: 1rem 0; }
    .reading-guide h3 { margin-top: 0; color: var(--slate); }
    .legend-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0.75rem; margin-top: 0.75rem; }
    .legend-item { display: flex; align-items: flex-start; gap: 0.5rem; font-size: 0.85rem; }
    .legend-icon { flex-shrink: 0; width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.7rem; color: #fff; }

    /* Status badges */
    .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .badge-green { background: #ecfdf5; color: #059669; }
    .badge-amber { background: #fffbeb; color: #d97706; }
    .badge-red { background: #fef2f2; color: #dc2626; }

    .scenario-explorer { background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); color: #fff; padding: 1.5rem; border-radius: 12px; margin: 1.5rem 0; box-shadow: 0 10px 25px -5px rgba(0,0,0,.15); }
    .scenario-explorer h3 { color: #e2e8f0; margin-top: 0; }
    .scenario-controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.25rem; margin: 1rem 0; }
    .control-group { display: flex; flex-direction: column; gap: 0.5rem; }
    .control-group label { font-size: 0.85rem; font-weight: 500; opacity: 0.9; }
    .control-group .control-help { font-size: 0.7rem; opacity: 0.7; margin-top: 0.15rem; line-height: 1.3; }
    .control-group input[type="range"] { width: 100%; accent-color: var(--accent); }
    .control-group input[type="number"] { padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,.3); background: rgba(255,255,255,.1); color: #fff; font-size: 1rem; }
    .live-results { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,.2); }
    .live-result { background: rgba(255,255,255,.1); padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.9rem; }
    .live-result .label { opacity: 0.8; font-size: 0.8rem; }
    .live-result .value { font-weight: 700; font-size: 1.1rem; color: #38bdf8; }
    img { border-radius: 8px; box-shadow: var(--shadow); }
    .exec-trio-viz { margin: 1rem 0; }
    .observation-box { background: #f8fafc; border-left: 4px solid var(--accent); padding: 0.75rem 1rem; margin-top: 1rem; font-size: 0.875rem; color: var(--gray); }
    .observation-box ul { margin: 0.25rem 0 0 1rem; padding: 0; }
    .observation-box li { margin: 0.2rem 0; }
    .tombstone { display: flex; flex-wrap: wrap; gap: 1rem; padding: 0.75rem 1rem; background: #f1f5f9; border-radius: 8px; font-size: 0.8rem; color: var(--gray); margin-bottom: 1.5rem; }
    .tombstone span { display: inline-block; }
    .tombstone .ev-sens { background: #fff; padding: 0.5rem 0.75rem; border-radius: 6px; border: 1px solid var(--border); }
    .seal-audit { font-size: 0.75rem; color: var(--gray); margin-top: 2rem; padding-top: 1rem; border-top: 1px dashed var(--border); font-style: italic; text-align: center; }
    .priority-table .p1 { border-left: 3px solid #059669; }
    .priority-table .p2 { border-left: 3px solid #0891b2; }
    .priority-table .p3 { border-left: 3px solid #64748b; }
    .diff-dots { font-size: 1rem; letter-spacing: 0.1em; }
    .diff-low { color: #059669; }
    .diff-med { color: #d97706; }
    .diff-high { color: #dc2626; }

    /* Payer dashboard cards */
    .payer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.25rem; margin: 1.25rem 0; }
    .payer-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; box-shadow: var(--shadow); transition: transform 0.15s, box-shadow 0.15s; }
    .payer-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px -4px rgba(0,0,0,.12); }
    .payer-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--border); }
    .payer-card-header h4 { margin: 0; font-size: 1rem; color: var(--slate); }
    .payer-card-header .payer-share { font-size: 0.8rem; color: var(--gray); background: #f1f5f9; padding: 3px 10px; border-radius: 12px; }
    .payer-metric { display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0; font-size: 0.85rem; }
    .payer-metric .pm-label { color: var(--gray); }
    .payer-metric .pm-value { font-weight: 600; font-variant-numeric: tabular-nums; }

    /* Progress / gap bars */
    .gap-bar-wrap { margin: 0.3rem 0 0.6rem 0; }
    .gap-bar { height: 8px; border-radius: 4px; background: #e2e8f0; overflow: hidden; position: relative; }
    .gap-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
    .gap-bar-fill.good { background: linear-gradient(90deg, #059669, #34d399); }
    .gap-bar-fill.warn { background: linear-gradient(90deg, #d97706, #fbbf24); }
    .gap-bar-fill.bad { background: linear-gradient(90deg, #dc2626, #f87171); }
    .gap-bar-labels { display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--gray); margin-top: 2px; }

    /* CSS mini waterfall */
    .mini-waterfall { display: flex; align-items: flex-end; gap: 3px; height: 120px; margin: 1rem 0; padding: 0 0.5rem; }
    .wf-bar-group { flex: 1; display: flex; flex-direction: column; align-items: center; }
    .wf-bar { border-radius: 4px 4px 0 0; min-height: 4px; width: 100%; max-width: 60px; transition: height 0.4s ease; }
    .wf-bar.denial { background: linear-gradient(180deg, #ef4444, #dc2626); }
    .wf-bar.underpay { background: linear-gradient(180deg, #f59e0b, #d97706); }
    .wf-bar.rework { background: linear-gradient(180deg, #8b5cf6, #7c3aed); }
    .wf-bar.economic { background: linear-gradient(180deg, #06b6d4, #0891b2); }
    .wf-bar.total { background: linear-gradient(180deg, #0f4c81, #1a6bb3); }
    .wf-label { font-size: 0.65rem; color: var(--gray); text-align: center; margin-top: 4px; line-height: 1.2; max-width: 70px; }
    .wf-amount { font-size: 0.7rem; font-weight: 700; color: var(--slate); margin-bottom: 2px; }

    /* Table hover */
    tr:hover { background: #f0f4ff !important; }
    th { position: sticky; top: 54px; z-index: 2; }

    /* Section collapse */
    .section-toggle { cursor: pointer; user-select: none; }
    .section-toggle::after { content: ' ▾'; font-size: 0.8em; color: var(--gray); }
    .section-toggle.collapsed::after { content: ' ▸'; }

    /* One-page print summary */
    .print-summary { display: none; }

    /* Glossary */
    .glossary { columns: 2; column-gap: 2rem; }
    .glossary dt { font-weight: 600; color: var(--slate); font-size: 0.9rem; margin-top: 0.75rem; break-after: avoid; }
    .glossary dd { margin: 0 0 0.25rem 0; font-size: 0.85rem; color: var(--gray); break-inside: avoid; }

    /* Confidence grade */
    .grade-card { display: inline-flex; align-items: center; gap: 1rem; background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 0.75rem 1.25rem; box-shadow: var(--shadow); }
    .grade-letter { font-size: 2.5rem; font-weight: 800; line-height: 1; width: 56px; height: 56px; display: flex; align-items: center; justify-content: center; border-radius: 12px; color: #fff; }
    .grade-A { background: linear-gradient(135deg, #059669, #34d399); }
    .grade-B { background: linear-gradient(135deg, #0891b2, #22d3ee); }
    .grade-C { background: linear-gradient(135deg, #d97706, #fbbf24); }
    .grade-D { background: linear-gradient(135deg, #dc2626, #f87171); }
    .grade-detail { font-size: 0.85rem; color: var(--gray); }
    .grade-detail strong { color: var(--slate); display: block; font-size: 0.95rem; }

    /* Value creation timeline */
    .timeline-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px; margin: 1rem 0; align-items: end; height: 160px; }
    .tl-bar-wrap { display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
    .tl-bar { width: 100%; border-radius: 4px 4px 0 0; transition: height 0.4s ease; min-height: 4px; }
    .tl-bar.q1 { background: linear-gradient(180deg, #94a3b8, #64748b); }
    .tl-bar.q2 { background: linear-gradient(180deg, #0891b2, #06b6d4); }
    .tl-bar.q3 { background: linear-gradient(180deg, #059669, #34d399); }
    .tl-bar.q4 { background: linear-gradient(180deg, #059669, #10b981); }
    .tl-pct { font-size: 0.7rem; font-weight: 700; color: var(--slate); margin-bottom: 2px; }
    .tl-amt { font-size: 0.6rem; font-weight: 600; color: var(--gray); margin-bottom: 1px; }
    .tl-label { font-size: 0.6rem; color: var(--gray); text-align: center; margin-top: 4px; line-height: 1.2; }

    /* Risk register */
    .risk-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
    .risk-dot.high { background: #dc2626; }
    .risk-dot.med { background: #d97706; }
    .risk-dot.low { background: #059669; }
    .risk-score { font-weight: 700; font-size: 0.85rem; padding: 2px 8px; border-radius: 6px; }
    .risk-score.critical { background: #fef2f2; color: #dc2626; }
    .risk-score.elevated { background: #fffbeb; color: #d97706; }
    .risk-score.moderate { background: #f0fdf4; color: #059669; }

    /* IC memo */
    .memo-block { background: #fffdf7; border: 1px solid #e5e0d5; border-radius: 8px; padding: 1.25rem 1.5rem; margin: 0.75rem 0; font-family: 'Georgia', 'Times New Roman', serif; font-size: 0.9rem; line-height: 1.7; color: #1a1a1a; position: relative; }
    .memo-block::before { content: 'IC MEMO'; position: absolute; top: -10px; left: 12px; background: #fffdf7; padding: 0 6px; font-family: 'Inter', sans-serif; font-size: 0.65rem; font-weight: 700; color: var(--gray); letter-spacing: 0.1em; }
    .memo-copy-btn { position: absolute; top: 8px; right: 8px; background: var(--primary); color: #fff; border: none; border-radius: 6px; padding: 4px 10px; font-size: 0.7rem; cursor: pointer; font-family: 'Inter', sans-serif; }
    .memo-copy-btn:hover { background: var(--primary-light); }

    /* Post-close tracker */
    .tracker-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; margin: 1rem 0; }
    .tracker-item { background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 0.75rem 1rem; box-shadow: var(--shadow); }
    .tracker-item .tk-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--gray); }
    .tracker-item .tk-target { font-size: 1.1rem; font-weight: 700; color: var(--primary); margin: 0.25rem 0; }
    .tracker-item .tk-current { font-size: 0.8rem; color: var(--gray); }
    .tracker-item .tk-bar { height: 4px; background: #e2e8f0; border-radius: 2px; margin-top: 0.4rem; overflow: hidden; }
    .tracker-item .tk-bar-fill { height: 100%; border-radius: 2px; background: var(--green); }

    @media print {
      .report-nav { display: none; }
      .container { padding-top: 0; }
      .scenario-explorer { break-inside: avoid; }
      .card { break-inside: avoid; }
      .payer-card { break-inside: avoid; }
      .tracker-item { break-inside: avoid; }
      .memo-block { break-inside: avoid; }
      .memo-copy-btn { display: none; }
      .print-summary { display: block; page-break-after: always; border: 2px solid var(--primary); padding: 2rem; margin: 0; border-radius: 0; }
      .print-summary h2 { border: none; margin-top: 0; }
      th { position: static; }
      tr:hover { background: inherit !important; }
      #back-to-top { display: none !important; }
      .timeline-grid { height: auto; }
      .tl-bar { min-height: 8px; }
    }
    @media (max-width: 640px) {
      .kpi-grid { grid-template-columns: 1fr 1fr; }
      .payer-grid { grid-template-columns: 1fr; }
      .glossary { columns: 1; }
      .report-nav-inner { padding: 0.5rem 1rem; }
      .mini-waterfall { height: 80px; }
    }
  </style>
</head>
<body>
<div class="container">"""
