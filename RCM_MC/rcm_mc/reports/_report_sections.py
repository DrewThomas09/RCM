"""Static HTML / JS blocks extracted from the executive report.

These are pure string constants — no Python-side templating, no variables.
They are assembled into the final HTML by ``html_report.generate_html_report``
alongside the dynamic data-driven sections (exec summary, payer dashboard,
waterfall, etc.).

Keeping them here makes ``html_report.py`` focused on the data-driven logic
and makes edits to scaffolding / boilerplate painless. Byte-for-byte identical
to the prior inlined versions — if you edit here, regenerate golden-master
baselines.
"""
from __future__ import annotations


RISK_REGISTER_HTML = """
    <h2 id="sec-risks">Risk Register</h2>
    <p class='section-desc'><strong>Why this matters:</strong> Every investment thesis has risks that could erode or delay value capture. This register identifies the key risks specific to the RCM opportunity, rates their probability and impact, and maps each to a concrete mitigation. Present this alongside the opportunity to demonstrate rigorous downside analysis.</p>
    <table>
      <tr><th>Risk</th><th>Probability</th><th>Impact</th><th>Risk Score</th><th>Mitigation</th></tr>
      <tr>
        <td>Payer denial rates increase due to policy changes</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-dot high"></span>High</td>
        <td><span class="risk-score critical">Critical</span></td>
        <td>Diversify payer mix; build automated prior-auth; negotiate escalation clauses in payer contracts</td>
      </tr>
      <tr>
        <td>Key RCM staff turnover during transformation</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-score elevated">Elevated</span></td>
        <td>Retention bonuses for key personnel; cross-train teams; document processes before redesign</td>
      </tr>
      <tr>
        <td>Technology implementation delays or vendor underperformance</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-score elevated">Elevated</span></td>
        <td>Phased rollout; milestone-based contracts; maintain manual fallback processes</td>
      </tr>
      <tr>
        <td>Actual denial data reveals lower opportunity than modeled</td>
        <td><span class="risk-dot low"></span>Low</td>
        <td><span class="risk-dot high"></span>High</td>
        <td><span class="risk-score elevated">Elevated</span></td>
        <td>Conservative underwriting (30-50% credit); calibrate model with actual data before close</td>
      </tr>
      <tr>
        <td>Regulatory changes (CMS reimbursement cuts, prior-auth reform)</td>
        <td><span class="risk-dot low"></span>Low</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-score moderate">Moderate</span></td>
        <td>Monitor CMS rulemaking; diversify revenue across payers; stress test under adverse scenarios</td>
      </tr>
      <tr>
        <td>Hospital operational resistance to process change</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-dot low"></span>Low</td>
        <td><span class="risk-score moderate">Moderate</span></td>
        <td>Executive sponsorship; quick wins first to build credibility; dedicated change management lead</td>
      </tr>
      <tr>
        <td>EMR data quality issues prevent accurate tracking</td>
        <td><span class="risk-dot med"></span>Medium</td>
        <td><span class="risk-dot low"></span>Low</td>
        <td><span class="risk-score moderate">Moderate</span></td>
        <td>Data cleanup sprint in Days 1-30; interim manual tracking for critical KPIs; invest in reporting layer</td>
      </tr>
    </table>
    """


MODEL_LIMITATIONS_HTML = """
    <h2 id="sec-limitations">10b. Model Limitations and Data Reality</h2>
    <p class='section-desc'><strong>Why this matters:</strong> Every model has boundaries. Understanding what the model does and does not capture helps the deal team appropriately risk-adjust the opportunity and prioritize diligence. Transparency here builds credibility with investment committees.</p>

    <div class="card" style="border-left: 4px solid #d97706;">
      <h3>What This Model Captures</h3>
      <table>
      <tr><th>Capability</th><th>Description</th></tr>
      <tr><td>Payer-Level Denial and Write-Off Dynamics</td><td>Stochastic simulation of initial denial rates, appeal success by stage, and final write-off rates across Medicare, Medicaid, and Commercial payers</td></tr>
      <tr><td>Underpayment Leakage</td><td>Models the gap between contracted and paid rates, including recovery economics</td></tr>
      <tr><td>A/R Velocity</td><td>Simulates days in accounts receivable by payer, translating collection delays into working capital cost</td></tr>
      <tr><td>Operational Cost</td><td>Rework costs for denial appeals and underpayment follow-up, calibrated to staffing and volume</td></tr>
      <tr><td>Benchmark Comparison</td><td>All metrics are computed for both the target and a best-practice benchmark, isolating the performance gap</td></tr>
      </table>
    </div>

    <div class="card" style="border-left: 4px solid #dc2626;">
      <h3>Known Limitations</h3>
      <table>
      <tr><th>Limitation</th><th>Impact on Results</th><th>Mitigation</th></tr>
      <tr><td><strong>Paper-Based Denial Data</strong></td><td>Many hospitals still receive denial notifications via fax, mail, or non-standardized payer portal formats. If this data is not digitized, the model relies on estimated rates rather than observed rates.</td><td>Use calibration mode with whatever electronic data is available. Flag payers with low sample sizes in the Data Confidence section.</td></tr>
      <tr><td><strong>Data Silos</strong></td><td>Denial data may live across the EMR, billing system, clearinghouse, and payer portals with no single source of truth. Reconciliation errors can bias model inputs.</td><td>Request a unified denial extract during diligence. The Data Aggregation Guide below describes how to consolidate these sources.</td></tr>
      <tr><td><strong>Payer Contract Opacity</strong></td><td>Underpayment severity depends on contracted rates, which are often confidential and vary by service line. The model uses aggregate severity estimates, not line-item contract audits.</td><td>When contract data is available, override the underpayment severity parameter per payer in the configuration.</td></tr>
      <tr><td><strong>Staffing and Capacity Estimates</strong></td><td>Denial rework costs assume an FTE count and cost per appeal. Actual staffing may differ, especially if work is outsourced or shared across departments.</td><td>Validate FTE counts and hourly rates during operational diligence. Adjust the operations section in the configuration.</td></tr>
      <tr><td><strong>Static Payer Behavior</strong></td><td>The model does not account for mid-year payer policy changes, prior-authorization rule shifts, or emerging regulations that could increase or decrease denial rates.</td><td>Use stress tests to model adverse payer scenarios. Re-run quarterly as payer landscapes change.</td></tr>
      <tr><td><strong>No Service Line Granularity (Default)</strong></td><td>The default configuration operates at the payer level, not the service line level. High-acuity service lines with outsized leakage may be masked.</td><td>When service-line-level data becomes available, extend the configuration to capture service line weights.</td></tr>
      <tr><td><strong>Distribution Assumptions</strong></td><td>The model uses beta and truncated normal distributions to represent uncertainty. If real-world data has heavy tails or bimodal patterns, these assumptions may understate extreme outcomes.</td><td>Calibrate from actual claims data to let observed distributions override defaults. Review trace output for outlier behavior.</td></tr>
      </table>
    </div>

    <div class="card" style="border-left: 4px solid #0891b2;">
      <h3>How to Collect Denial Data in Practice</h3>
      <p class='section-desc'>Feedback from hospital operators consistently highlights that denial data is fragmented and sometimes literally on paper. Here is a practical guide for aggregating the data needed to calibrate this model.</p>
      <table>
      <tr><th>Data Source</th><th>What It Provides</th><th>How to Access</th></tr>
      <tr><td><strong>EMR / Practice Management System</strong> (Epic, Cerner, MEDITECH, athenahealth)</td><td>Claim status, denial reason codes (CARC/RARC), remittance data, payer adjudication history</td><td>Request a bulk export of denied claims with remittance details for the trailing 12 months. Most EMRs have a standard denial report or revenue cycle dashboard.</td></tr>
      <tr><td><strong>Clearinghouse</strong> (Availity, Change Healthcare, Trizetto)</td><td>Electronic Remittance Advice (835), claim status (277), real-time eligibility</td><td>Download ERA/835 files or request a flat-file extract of all denied and adjusted claims. Clearinghouses often have analytics dashboards that summarize denial rates by payer and reason code.</td></tr>
      <tr><td><strong>Payer Portals</strong> (UHC, Anthem, Aetna, Humana)</td><td>Denial letters, appeal status, prior-auth decisions, EOBs</td><td>Many portals support bulk download of claims in denied status. For paper-only notifications, request that staff scan and code denial letters into a shared tracker during the diligence period.</td></tr>
      <tr><td><strong>RCM Vendor Dashboards</strong> (R1 RCM, Conifer, nThrive, Optum360)</td><td>Pre-built denial analytics, A/R aging, appeal success rates, cost-to-collect metrics</td><td>If the hospital outsources any RCM functions, the vendor typically provides a monthly dashboard. Request read access or a data extract covering the analysis period.</td></tr>
      <tr><td><strong>Manual / Paper Records</strong></td><td>Denial notifications received by fax or mail that were never entered into a system</td><td>This is the hardest gap. During diligence, request a sample audit: have staff pull a random sample of 30+ paper denials per payer and enter the denial reason, dollar amount, and resolution into a spreadsheet. Even partial data improves calibration.</td></tr>
      <tr><td><strong>Financial Reporting / GL</strong></td><td>Net revenue, bad debt write-offs, contractual adjustments by period</td><td>Pull the trailing-twelve-month income statement and balance sheet. Contractual adjustment and bad debt line items serve as a cross-check on modeled write-off rates.</td></tr>
      </table>
      <p class='section-desc' style="margin-top: 0.75rem;"><strong>Minimum viable dataset:</strong> To produce a calibrated run, the model needs (1) a claims summary with payer-level revenue and claim counts, and (2) a denials extract with payer, denial amount, write-off amount, and appeal level. A/R aging by payer is highly recommended but optional.</p>
    </div>
    """


KEY_ASSUMPTIONS_HTML = """
    <div class="card" style="border-left: 4px solid #6366f1;">
      <h3>Key Model Assumptions</h3>
      <p class='section-desc'>These assumptions are embedded in the configuration files and directly affect the output. Review during diligence and adjust as better data becomes available.</p>
      <table>
      <tr><th>Assumption</th><th>Default Basis</th><th>Sensitivity</th></tr>
      <tr><td>Payer mix (revenue share)</td><td>Configured per hospital; defaults based on regional averages</td><td>High: shifting 5% of revenue between payers can move EBITDA drag by 10-15%</td></tr>
      <tr><td>Initial Denial Rates (IDR)</td><td>AHA, Fierce Healthcare, HFMA published ranges by payer type</td><td>Very High: IDR is the single largest driver of total drag in most scenarios</td></tr>
      <tr><td>Final Write-Off Rates (FWR)</td><td>Kodiak/HealthLeaders top-decile benchmarks</td><td>High: FWR determines how much of the denied dollars are permanently lost</td></tr>
      <tr><td>Appeal success rates by stage</td><td>Industry averages (L1: 40-60%, L2: 30-40%, L3: 20-30%)</td><td>Medium: affects rework cost more than total write-off</td></tr>
      <tr><td>Days in A/R</td><td>Kodiak benchmarks (industry avg 56.9, top-decile 43.6)</td><td>Medium: primarily affects working capital cost, not EBITDA drag directly</td></tr>
      <tr><td>WACC / cost of capital</td><td>12% default (typical PE portfolio company)</td><td>Low-Medium: only affects the economic drag / financing cost calculation</td></tr>
      <tr><td>EBITDA multiple</td><td>8.0x default (healthcare services sector)</td><td>High for EV translation, but does not affect underlying EBITDA drag</td></tr>
      </table>
    </div>
    """


GLOSSARY_HTML = """
    <h2 id="glossary">Glossary of Terms</h2>
    <p class='section-desc'>Plain-English definitions for the healthcare revenue cycle and financial terms used throughout this report.</p>
    <div class="card">
    <dl class="glossary">
      <dt>A/R (Accounts Receivable)</dt>
      <dd>Money owed to the hospital for services already rendered. "Days in A/R" measures how long it takes to collect payment on average.</dd>

      <dt>Appeal (L1 / L2 / L3)</dt>
      <dd>When a claim is denied, the hospital can appeal the decision. L1 is the first appeal, L2 the second, L3 the third and final. Each stage costs more and takes longer.</dd>

      <dt>Benchmark</dt>
      <dd>The best-practice performance standard, derived from top-quartile hospital peers and published industry data (HFMA, AHA, Kodiak).</dd>

      <dt>CDI (Clinical Documentation Improvement)</dt>
      <dd>Programs that ensure clinical documentation accurately reflects the severity and complexity of patient conditions, reducing coding-related denials.</dd>

      <dt>Clean Claim</dt>
      <dd>A claim submitted to the payer without errors that requires no additional information. Clean claims are paid faster and denied less often.</dd>

      <dt>Cost to Collect</dt>
      <dd>Total RCM operating cost as a percentage of net patient revenue. Industry benchmark is 3-4% (HFMA). Higher ratios signal operational inefficiency.</dd>

      <dt>Denial Rate (IDR — Initial Denial Rate)</dt>
      <dd>The percentage of claims initially denied by payers. A high IDR means more revenue is at risk and more staff time is spent on appeals.</dd>

      <dt>EBITDA</dt>
      <dd>Earnings Before Interest, Taxes, Depreciation, and Amortization. The primary profitability measure used in healthcare PE valuation.</dd>

      <dt>EBITDA Drag</dt>
      <dd>The annual dollar difference in RCM losses between the target hospital and best-practice benchmark. This is the recoverable opportunity.</dd>

      <dt>Enterprise Value (EV)</dt>
      <dd>EBITDA multiplied by a market multiple (e.g., 8x). Represents the total value impact of closing the performance gap.</dd>

      <dt>FWR (Final Write-Off Rate)</dt>
      <dd>The percentage of denied claims that are never recovered after all appeal stages are exhausted. These dollars are permanently lost.</dd>

      <dt>Monte Carlo Simulation</dt>
      <dd>A statistical method that runs thousands of scenarios with randomized inputs to model the range of possible outcomes, rather than relying on a single point estimate.</dd>

      <dt>NPSR (Net Patient Service Revenue)</dt>
      <dd>Total revenue from patient care after contractual adjustments. This is the "top line" for hospital financial analysis.</dd>

      <dt>P10 / P90 (Percentiles)</dt>
      <dd>P10 is the 10th percentile (conservative: 90% of outcomes are higher). P90 is the 90th percentile (stress case: only 10% of outcomes are higher).</dd>

      <dt>Payer Mix</dt>
      <dd>The distribution of hospital revenue across payer types (Medicare, Medicaid, Commercial, Self-Pay). Each payer has different denial and payment behaviors.</dd>

      <dt>Prior Authorization</dt>
      <dd>Payer requirement to approve a procedure before it is performed. Missed prior-auths are a leading cause of denials.</dd>

      <dt>Underpayment</dt>
      <dd>When a payer pays less than the contracted rate for a service. The gap between what was paid and what was owed is "leakage."</dd>

      <dt>Quick Wins</dt>
      <dd>RCM improvements achievable in the first 90 days post-close, typically low-capital process fixes like coding audits and prior-auth automation.</dd>

      <dt>Risk-Adjusted Credit</dt>
      <dd>The portion of modeled EBITDA upside underwritten in the purchase price. Conservative (30%), Base (50%), or Aggressive (70%) depending on data confidence.</dd>

      <dt>Value Creation Ramp</dt>
      <dd>The projected timeline for capturing the EBITDA opportunity, typically reaching 55% in Year 1 and 95% by Month 24.</dd>

      <dt>WACC (Weighted Average Cost of Capital)</dt>
      <dd>The blended rate of return required by all capital providers (debt and equity). Used here to calculate the financing cost of cash trapped in A/R.</dd>
    </dl>
    </div>
    """


SCENARIO_EXPLORER_JS = """<script>
(function() {
  const d = window.RCM_DATA || {};
  if (!d.ebitda_drag) return;
  const baselineEbitda = d.ebitda_drag;
  const extraAr = d.extra_ar_days || 0;
  const daysPerYear = 365;

  function prettyMoney(x) {
    if (x >= 1e9) return '$' + (x/1e9).toFixed(1) + 'B';
    if (x >= 1e6) return '$' + (x/1e6).toFixed(1) + 'M';
    if (x >= 1e3) return '$' + (x/1e3).toFixed(0) + 'K';
    return '$' + Math.round(x);
  }

  function getEbitda() {
    const sel = document.getElementById('payer_shock');
    if (!sel || !d.shocks || d.shocks.length === 0) return baselineEbitda;
    const id = sel.value;
    if (!id) return baselineEbitda;
    const s = d.shocks.find(function(x) { return x.id === id; });
    return s ? s.ebitda_drag : baselineEbitda;
  }

  function update() {
    const ebitda = getEbitda();
    const mult = parseFloat(document.getElementById('ev_mult').value) || 8;
    const waccPct = parseFloat(document.getElementById('wacc_slider').value) || 12;
    const wacc = waccPct / 100;
    const rev = parseFloat(document.getElementById('annual_rev').value) || 0;

    document.getElementById('ev_mult_val').textContent = mult + 'x';
    document.getElementById('wacc_val').textContent = waccPct + '%';

    const evMean = ebitda.mean * mult;
    const evP10 = ebitda.p10 * mult;
    const evP90 = ebitda.p90 * mult;

    document.getElementById('live_ev_mean').textContent = prettyMoney(evMean);
    document.getElementById('live_ev_range').textContent = prettyMoney(evP10) + ' \u2013 ' + prettyMoney(evP90);

    if (extraAr && rev > 0) {
      const cash = (rev / daysPerYear) * extraAr;
      const financing = cash * wacc;
      document.getElementById('live_cash').textContent = prettyMoney(cash);
      document.getElementById('live_financing').textContent = prettyMoney(financing);
      const econCash = document.getElementById('econ_cash');
      const econFinancing = document.getElementById('econ_financing');
      const econWacc = document.getElementById('econ_wacc_pct');
      if (econCash) econCash.textContent = prettyMoney(cash);
      if (econFinancing) econFinancing.textContent = prettyMoney(financing);
      if (econWacc) econWacc.textContent = waccPct;
    } else {
      document.getElementById('live_cash').textContent = '\u2014';
      document.getElementById('live_financing').textContent = '\u2014';
    }

    const exEv = document.getElementById('ex_ev');
    const exMult = document.getElementById('ex_mult');
    const exRange = document.getElementById('ex_range');
    if (exEv) exEv.textContent = prettyMoney(evMean);
    if (exMult) exMult.textContent = mult;
    if (exRange) exRange.textContent = prettyMoney(evP10) + ' to ' + prettyMoney(evP90);
  }

  ['ev_mult','wacc_slider','annual_rev'].forEach(function(id) {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', update);
  });
  var payerShock = document.getElementById('payer_shock');
  if (payerShock) payerShock.addEventListener('change', update);
  update();
})();
</script>"""


BACK_TO_TOP_HTML = """
    <a href="#exec-summary" id="back-to-top" style="position:fixed;bottom:2rem;right:2rem;width:40px;height:40px;border-radius:50%;background:var(--primary);color:#fff;display:none;align-items:center;justify-content:center;text-decoration:none;box-shadow:0 4px 12px rgba(0,0,0,.15);font-size:1.2rem;z-index:99;transition:opacity 0.2s;" title="Back to top">&uarr;</a>
    <script>
    (function(){
      var btn=document.getElementById('back-to-top');
      if(!btn)return;
      window.addEventListener('scroll',function(){
        btn.style.display=window.scrollY>400?'flex':'none';
      });
      // Highlight active nav link on scroll
      var sections=document.querySelectorAll('h2[id]');
      var navLinks=document.querySelectorAll('.report-nav a[href^="#"]');
      if(sections.length&&navLinks.length){
        window.addEventListener('scroll',function(){
          var pos=window.scrollY+80;
          var current='';
          sections.forEach(function(s){if(s.offsetTop<=pos)current=s.id;});
          navLinks.forEach(function(a){
            a.style.background=a.getAttribute('href')==='#'+current?'#e0f2fe':'';
            a.style.color=a.getAttribute('href')==='#'+current?'var(--primary)':'';
          });
        });
      }
    })();
    </script>"""
