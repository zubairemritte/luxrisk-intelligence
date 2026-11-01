# Methodology: what every number means

## Definitions and frequencies

Inflation is the annual rate of change of the all-items HICP, not an index level. Unemployment is a seasonally adjusted percentage of the labour force. GDP is the seasonally/calendar-adjusted change in chain-linked volumes on the preceding quarter. The exchange rate is the monthly average **USD per EUR**.

Do not average these quantities together. A change in a percentage rate is reported in **percentage points**. A change in USD/EUR is in USD per EUR. Quarter labels remain quarter labels; the system does not stretch quarterly growth across months.

## Missingness and source checks

Missing source cells become `None`, serialize to JSON null and export as empty numeric cells. They are never zero or forward-filled. Mathematical checks enforce 0..100 for unemployment and positive exchange rates. Inflation and GDP are not clipped to arbitrary “normal” ranges.

Source dimensions must match the requested country, scope, unit, frequency and adjustment. Country configuration is separate from actual data availability. Source flags are retained. A break (`b`) or definition-difference (`d`) flag starts a new usable analytical segment; `p`/`e` flags remain visible but do not automatically discard the row.

## Level, movement and freshness

The summary selects the latest nonmissing observation, shows the last period returned (which can be missing), and computes a change only if the previous usable value is the immediately preceding period and the latest source flag does not indicate a break or differing definition. Freshness is calendar days since period end against a project-defined threshold: 65 days for inflation/FX, 95 for unemployment and 160 for GDP. These are operational investigation thresholds, not official publication schedules.

An old explicitly selected historical slice will naturally be stale today. Retrieval time, observation period and economic publication time are different concepts.

## Peer comparison

For every selected country, select the latest successful vintage in the requested mode. Check identical indicator definitions. Intersect the sets of nonmissing periods and select the latest common period. Compare observed values at that period, retaining each country's run ID and retrieval time. No common period means no comparison. Currency context is not a national ranking.

## Investigation rule

For the latest value x, use only the previous `window` consecutive values. Monthly default is 12; quarterly default is 8. Compute their mean m and **sample** standard deviation s:

`z = (x - m) / s`; flag when `abs(z) >= 3`.

Example: prior values `[1,2,3,4]` have mean 2.5 and s = sqrt(5/3). A latest value of 10 gives z approximately 5.81. The latest value never enters its own reference estimate.

If s is zero, the z-score is unavailable. A different latest value is labelled `flat_baseline_shift`; an unchanged value has no flag. Insufficient history, a latest missing cell, a calendar gap or a recent source break makes the statistical panel unavailable. This is a screening rule requiring investigation, with no claimed precision/recall or probability of crisis.

## Forecast baselines

For each expanding-window origin, fit only the prefix before the next observation:

- Naive: next value equals the most recent training value.
- Drift: next value equals `last + (last - first) / (n - 1)`.

Use a minimum 12 observations for monthly or 8 for quarterly series, and at most 24 recent origins. Both models receive the same target periods. Report MAE and RMSE in the original unit. Select lower MAE; a tie chooses naive. The next-period estimate uses all values in the latest contiguous segment. It is a transparent baseline, without clipping, an estimated crisis probability or a calibrated confidence interval.

Hand check: `[1,2,3,4,5,6]` with min_train=4 has two origins. Naive errors are both -1, so MAE=RMSE=1. Drift predicts 5 and 6 exactly, so both metrics are 0; its next estimate is 7.

**Evaluation limit:** training and targets use the currently selected revised vintage. They do not recreate what was published at each historical origin. Model selection reuses the reported evaluation window; no independent final holdout performance is claimed.

## Revisions and local vintages

Compare the selected successful slice with its immediately preceding collected slice. Distinguish added cells, changed values, changed status flags and cells outside the newer requested slice. A missing cell is different from an absent period. Different query windows can add/remove periods; that alone is not a provider revision.

Raw-response hashes support byte identity, not an endorsement of economic truth. Locally stored vintages start when this project first collects data. No historical release-date series is reconstructed from a later download.

## Scenario arithmetic

For a fixed USD invoice U and a baseline rate r measured in USD/EUR:

- Base EUR invoice = U / r.
- Stressed rate = r × (1 + FX shock % / 100).
- Stressed EUR invoice = U / stressed rate.
- Invoice delta = stressed minus base EUR cost.
- Annual extra floating-rate interest = EUR debt × rate shock bps / 10,000.

Example: U=USD 110,000, r=1.1 and FX shock=-10% gives EUR 100,000 initially and EUR 111,111.11 stressed. EUR 500,000 of floating debt at +100 bps adds EUR 5,000 for one year. The invoice change and annual interest effect are shown separately because their time bases differ.

Amounts must be finite, exposures nonnegative, r positive and FX shock above -100%. The assumptions exclude hedging, pass-through, offsetting revenues, amortisation and behavioural changes. A user changes assumptions; the model does not estimate them from macroeconomic observations.
