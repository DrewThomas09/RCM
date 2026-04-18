# Math

Plain-language tour of the formulas driving the bridges, Monte
Carlo, and prediction intervals. For the code-level references see
[`RCM_MC/docs/README_LAYER_PE.md`](../RCM_MC/docs/README_LAYER_PE.md)
(bridges), [`RCM_MC/docs/README_LAYER_MC.md`](../RCM_MC/docs/README_LAYER_MC.md)
(Monte Carlo), and
[`RCM_MC/docs/README_LAYER_ML.md`](../RCM_MC/docs/README_LAYER_ML.md)
(prediction + conformal).

## 1. v1 research-band EBITDA bridge

File: [`RCM_MC/rcm_mc/pe/rcm_ebitda_bridge.py`](../RCM_MC/rcm_mc/pe/rcm_ebitda_bridge.py).

Seven levers sum to the EBITDA delta:

$$
\Delta\text{EBITDA}_{\text{v1}} = \sum_{\ell \in \mathcal{L}}
f_\ell(m^{\text{cur}}_\ell, m^{\text{tgt}}_\ell, \theta)
$$

where $\mathcal{L} = \{\text{denial rate}, \text{days-in-AR},
\text{clean-claim rate}, \text{net-collection rate},
\text{cost-to-collect}, \text{first-pass resolution},
\text{CMI}\}$ and $\theta$ bundles the financial profile (NPR,
claims volume, FTE costs, rework costs).

Representative lever — denial rate:

$$
f_{\text{denial}}(m^{\text{cur}}, m^{\text{tgt}}) =
\frac{\lvert m^{\text{cur}} - m^{\text{tgt}} \rvert}{100}
\cdot \text{NPR} \cdot 0.35 \; + \; \text{rework}_{\text{saved}}
$$

The `0.35` coefficient is sized so a 12% → 5% reduction on a $400M
NPR reference hospital lands in the $8–15M research band. Enterprise
value:

$$
\Delta\text{EV}_{\text{v1}} = \Delta\text{EBITDA}_{\text{v1}} \cdot m_{\text{exit}}
$$

reported side-by-side at $m_{\text{exit}} \in \{10, 12, 15\}$.

29 regression tests lock each lever's output band.

## 2. v2 unit-economics bridge

File: [`RCM_MC/rcm_mc/pe/value_bridge_v2.py`](../RCM_MC/rcm_mc/pe/value_bridge_v2.py).

v2 reads a `ReimbursementProfile` — an inferred exposure to six
payer classes weighted by reimbursement method. A recovered denied
claim is worth:

$$
\text{recovery}_p = \text{claim}_p \cdot w_p,\quad
w_p = \begin{cases}
1.00 & \text{Commercial} \\
0.80 & \text{Medicare Advantage} \\
0.75 & \text{Medicare FFS} \\
0.55 & \text{Managed Government} \\
0.50 & \text{Medicaid} \\
0.40 & \text{Self-pay}
\end{cases}
$$

(From `_PAYER_REVENUE_LEVERAGE`.) This is the mechanism that makes
commercial-heavy denial recovery worth more than Medicare-heavy
recovery; v1 cannot express this because it applies a uniform
coefficient.

Every lever produces **four** separate flows:

$$
\text{LeverImpact}_\ell = (r_{\text{rev},\ell},\; r_{\text{cost},\ell},
\; c_{\text{wc},\ell},\; r_{\text{fin},\ell})
$$

- $r_{\text{rev}}$ — recurring revenue uplift
- $r_{\text{cost}}$ — recurring cost savings
- $c_{\text{wc}}$ — one-time working-capital release (**never**
  capitalized into EV)
- $r_{\text{fin}}$ — ongoing financing benefit

Recurring EBITDA:

$$
\Delta\text{EBITDA}^{\text{rec}}_\ell =
r_{\text{rev},\ell} + r_{\text{cost},\ell} + r_{\text{fin},\ell}
$$

Enterprise value — applied to recurring only:

$$
\Delta\text{EV}_{\text{v2}} = \biggl(\sum_\ell
\Delta\text{EBITDA}^{\text{rec}}_\ell\biggr) \cdot m_{\text{exit}}
$$

Cash release $c_{\text{wc}}$ reports side-by-side but never
multiplies. This is the load-bearing invariant — partners never see
inflated EV on timing-only wins.

### Default avoidable-share

$$
\text{AVOIDABLE} = 1 - (\text{appeal-rate} \cdot \text{success-rate})
= 1 - 0.6 \cdot 0.65 = 0.39
$$

(`_DEFAULT_AVOIDABLE_SHARE`.) Partner-overridable via
`BridgeAssumptions`.

## 3. Cross-lever dependency adjustment

File: [`RCM_MC/rcm_mc/pe/lever_dependency.py`](../RCM_MC/rcm_mc/pe/lever_dependency.py).

The ontology DAG carries `MechanismEdge.magnitude_hint` labels
(`strong` / `moderate` / `weak`). These map to overlap fractions:

$$
\alpha_{\text{hint}} = \begin{cases}
0.60 & \text{strong} \\
0.35 & \text{moderate} \\
0.15 & \text{weak}
\end{cases}
$$

When lever $\ell_{\text{child}}$ fires alongside parents
$\ell_{\text{p}_1}, \ldots, \ell_{\text{p}_k}$, its revenue
component is reduced:

$$
r^{\text{adj}}_{\text{rev},\text{child}} = r_{\text{rev},\text{child}}
\cdot \bigl(1 - \min(0.75,\; \textstyle\sum_i \alpha_{\text{hint},i})\bigr)
$$

where 0.75 = `_MAX_TOTAL_OVERLAP` (safety cap — a heavily-connected
child can still retain at least a quarter of its raw revenue
impact). Only the **revenue** flow is reduced; cost savings, WC
release, and financing benefit operate through independent
pathways. Adjustments only shrink, never inflate — monotonicity
locked by test.

The ontology is walked in topological order (Kahn's algorithm) so
parents are always processed before children. Unknown keys go at the
end; cycles (shouldn't exist in the shipped ontology) fall back to
input-preserving order.

## 4. Ramp curves

File: [`RCM_MC/rcm_mc/pe/ramp_curves.py`](../RCM_MC/rcm_mc/pe/ramp_curves.py).

A single-scalar ramp overstates Year 1 and understates Year 3. Per-
lever-family logistic S-curves replace the scalar:

$$
\text{ramp}(t) = \frac{1}{1 + e^{-k(t - t_{50})}},
\quad \text{anchored so } \text{ramp}(0) = 0,\; \text{ramp}(t_{\text{full}}) = 1
$$

with family-specific quartile months from `DEFAULT_RAMP_CURVES`:

| Family | 25% | 75% | 100% |
|---|---|---|---|
| Denial management | 3 | 6 | 12 |
| AR / collections | 2 | 4 | 9 |
| CDI / coding | 6 | 12 | 18 |
| Payer renegotiation | 6 | 12 | 24 |
| Cost optimization | 3 | 6 | 12 |
| Default | 3 | 6 | 12 |

At `evaluation_month = 36` every default curve returns 1.0 (identity
lock by test) — existing callers see identical output until they
opt in.

## 5. Two-source Monte Carlo

File: [`RCM_MC/rcm_mc/mc/ebitda_mc.py`](../RCM_MC/rcm_mc/mc/ebitda_mc.py).

For each simulation $i \in \{1, \ldots, N\}$:

**Prediction draw.** From the ridge predictor's conformal CI:

$$
\sigma_\ell = \frac{\text{ci}_{\text{high}} - \text{ci}_{\text{low}}}{2 \cdot 1.645}
$$

$$
\tilde{m}^{\text{tgt}}_{\ell,i} \sim \mathcal{N}(m^{\text{tgt}}_\ell,\; \sigma_\ell)
$$

The 1.645 is the one-sided 95% normal quantile — treating the CI
bounds as the 5th and 95th percentiles.

**Execution draw.** Per-lever-family beta distribution:

$$
e_{\ell,i} \sim \text{Beta}(\alpha_{\text{fam}(\ell)},\; \beta_{\text{fam}(\ell)})
$$

| Family | $\alpha$ | $\beta$ | $\mathbb{E}[e]$ |
|---|---|---|---|
| Denial management | 7 | 3 | 0.70 |
| AR / collections | 8 | 2 | 0.80 |
| CDI / coding | 6 | 4 | 0.60 |
| Payer renegotiation | 5 | 5 | 0.50 |

**Final value.**

$$
m^{\text{final}}_{\ell,i} = m^{\text{cur}}_\ell +
(\tilde{m}^{\text{tgt}}_{\ell,i} - m^{\text{cur}}_\ell) \cdot e_{\ell,i}
$$

**Bridge.** $\text{EBITDA}_i = \text{bridge}(m^{\text{cur}},\;
m^{\text{final}}_i)$.

Aggregate → `DistributionSummary` with percentiles
$p_5, p_{10}, p_{25}, p_{50}, p_{75}, p_{90}, p_{95}$, mean, std.

### Variance attribution

Normalized correlation-squared between each lever's sample column
and the EBITDA output:

$$
v_\ell = \frac{\rho^2(m^{\text{final}}_\ell,\; \text{EBITDA})}{\sum_{\ell'} \rho^2(m^{\text{final}}_{\ell'},\; \text{EBITDA})}
$$

so $\sum_\ell v_\ell = 1$ by construction (first-order Sobol-style).

### Zero-variance identity

When every uncertainty source has zero spread, the MC P50 matches
the deterministic bridge exactly. Locked by test.

## 6. Correlated prediction draws

For correlated levers, the simulator draws from a correlated
multivariate normal via Cholesky:

$$
\tilde{\mathbf{m}}_i = \boldsymbol{\mu} + \mathbf{L} \mathbf{z}_i,
\quad \mathbf{L} \mathbf{L}^\top = \boldsymbol{\Sigma},
\quad \mathbf{z}_i \sim \mathcal{N}(\mathbf{0}, \mathbf{I})
$$

where $\boldsymbol{\Sigma}$ is the partner-supplied correlation
matrix. The uniform quantiles $\Phi(z_i)$ then drive the per-lever
marginals via inverse-CDF (so lever-specific distributions can
differ while honoring cross-lever correlations).

All of `erf` / `erfinv` implemented inline (Abramowitz & Stegun
7.1.26 and Winitzki approximations) — no `scipy` dependency.

## 7. MOIC, IRR, covenant

File: [`RCM_MC/rcm_mc/pe/pe_math.py`](../RCM_MC/rcm_mc/pe/pe_math.py).

**MOIC (Multiple on Invested Capital).**

$$
\text{MOIC} = \frac{\text{exit proceeds}}{\text{entry equity}}
$$

**IRR.** Bisection on non-integer hold years:

$$
0 = -\text{equity}_{\text{entry}} + \sum_t \frac{\text{CF}_t}{(1 + r)^t}
$$

Bisected to converge on $r$ within the range $[-0.99,\; 10]$.

**Value-creation bridge reconciliation.** Exit EV is identically:

$$
\text{EV}_{\text{exit}} = \text{EV}_{\text{entry}} \;+\; \Delta_{\text{organic}}
\;+\; \Delta_{\text{rcm}} \;+\; \Delta_{\text{multiple}}
$$

where each piece is sized from its own formula; total reconciles
to `exit_ev` exactly (locked by test).

**Covenant check.**

$$
\text{leverage turns} = \frac{\text{net debt at exit}}{\text{EBITDA at exit}}
$$

Flag when `leverage turns > covenant threshold`.

## 8. Split conformal prediction

File: [`RCM_MC/rcm_mc/ml/conformal.py`](../RCM_MC/rcm_mc/ml/conformal.py).

Given a training set $\mathcal{D}_{\text{train}}$, a fitted base
model $\hat{f}$, and a held-out calibration set
$\{(x_j, y_j)\}_{j=1}^n$, compute absolute residuals:

$$
R_j = \lvert y_j - \hat{f}(x_j) \rvert
$$

Take the quantile:

$$
q = R_{(\lceil (1-\alpha)(n+1) \rceil)}
$$

Then for any new $x^*$ exchangeable with the calibration set:

$$
\Pr\bigl[\, y^* \in [\,\hat{f}(x^*) - q,\; \hat{f}(x^*) + q\,] \,\bigr]
\geq 1 - \alpha
$$

**No distributional assumption.** Only exchangeability between the
calibration set and the new point is required. Calibrates per-
metric — a poorly-fit Ridge gets a wide margin; a well-fit one gets
a tight one.

Implementation is ~230 lines of numpy. Empirical coverage on 1,000
simulated held-out samples: 85–96% for a nominal 90% target, locked
by `test_ridge_predictor.py::test_coverage_property_on_simulated_data`.

## 9. Ridge regression

File: [`RCM_MC/rcm_mc/ml/ridge_predictor.py`](../RCM_MC/rcm_mc/ml/ridge_predictor.py).

Closed-form solution on z-scored features with intercept:

$$
\hat{\boldsymbol{\beta}} = (\mathbf{X}^\top \mathbf{X} + \alpha \mathbf{I})^{-1} \mathbf{X}^\top \mathbf{y}
$$

with $\alpha = 1.0$ (`_RIDGE_ALPHA`). Zero-variance columns handled
by replacing sd with 1.0. Feature importances reported as normalized
$\lvert \hat{\beta}_j \rvert$ — a rough heuristic, not SHAP.

## 10. Size-gated fallback

Per target metric, the predictor chooses among three methods by
cohort size $n$:

$$
\text{method}(n) = \begin{cases}
\text{Ridge + split conformal} & n \geq 15 \\
\text{similarity-weighted median + bootstrap} & 5 \leq n \leq 14 \\
\text{benchmark P50 with P25–P75 band} & n < 5
\end{cases}
$$

Reliability grade `A` / `B` / `C` / `D` is assigned by the
combination of method, $n$, and $R^2$ (full ladder in
`_grade` in `ridge_predictor.py`).
