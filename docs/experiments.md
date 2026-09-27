# Experiments

**English** · [Русский](experiments.ru.md)

The full log of the experiments behind the library's settings and recommendations. Each
experiment is run by the script `experiments/expN_*.py` (the setting is described at the top of
the file), writes tables to `results/expN_tables.md` and figures to `results/figures/`. The
commands are at the end of this file. Tables and figure labels in `results/` are in Russian.

## Stage 1: calibration and the multiplicity correction

All numbers are on synthetic data: model error signals as AR(1) with φ = 0.5, in 10% of the
streams the mean shifts by one standard deviation at a random time, streams of 5000 steps, window
100, reference 300, horizon 5 windows, B = 500 bootstrap replicates. FDR and other metrics are
averaged over 10 independent scenarios (experiment 2) or 6 (experiment 3). Full tables are in
`results/*.md`, raw runs in `results/*.csv`.

### Experiment 1. Do the calibrated p-values hold their level

![Calibration of p-values](../results/figures/exp1_calibration.png)

1000 stationary streams × 20 windows per cell. The closer a line is to the grey diagonal, the
more accurate the calibration. Without autocorrelation (φ = 0) all schemes are on target. At
φ ≥ 0.5 the iid bootstrap loses control completely, the block bootstrap is noticeably
anti-conservative (1.5–3.5 times), and the AR-sieve comes closest to nominal. The hardest part is
the deep tail: at α = 0.001 the sieve is off by a factor of 1.3–3 for PH and KS and 5–8 for
ADWIN. These are exactly the levels online FDR needs over hundreds of streams, so the tail is the
main bottleneck of calibration.

![Benchmark at an equal FAR](../results/figures/exp1_benchmark.png)

Half of the streams shift at a known time, φ = 0.5. At river's thresholds PH and ADWIN look
equally powerful (detection 1.00), but at an FAR of 0.34 and 0.15 respectively. After calibration
to a common FAR ≈ 0.05 the order is: ADWIN 0.99, PH 0.83, KS 0.33, DDM 0.26. ADWIN's advantage is
partly due to its slightly anti-conservative calibration (FAR 0.084). DDM is the weakest after
calibration: its error rate is counted from the start of the stream and reacts slowly to a shift.

### Experiment 2. What happens as the number of streams grows

![Scaling with the number of streams](../results/figures/exp2_scaling_rho0.3.png)

Page-Hinkley, level 0.05 for every rule. Without a correction the share of false alarms among
alarms stays around 0.8 at any K, and the probability of at least one false alarm in a window
grows from 0.12 at K = 10 to 0.81 at K = 500. LORD++ keeps FDR at or below 0.05 for every K.
Bonferroni keeps the probability of a false alarm in a window below 0.05, but its FDR is high at
small K (0.47 at K = 10), because alarms are few there and a single false one weighs a lot. The
price of the correction is delay: 330 steps on a stale model for LORD++ and 275 for Bonferroni
against 132 without a correction at K = 500. LOND is too conservative and misses 10% of the
drifts. Alpha-investing has a delay of 630–870 steps and misses up to 20%. The variant with
independent streams: `results/figures/exp2_scaling_rho0.png`.

![Dependence between streams](../results/figures/exp2_dependence.png)

The same rules with independent (ρ = 0) and correlated (ρ = 0.3) streams, K = 500. In correlated
streams the common factor and the shared initial reference period shift the p-values of all
streams at once. Hence the bursts of false alarms that the review predicted. Procedures whose
guarantee relies on independence (SAFFRON, alpha-investing) and BH within a window lose control.
LORD++, LOND and Bonferroni hold.

The break-even point against the uncorrected rule at level 0.05 (ρ = 0.3): every rule saves 5–6
false retrains per drift, and pays for each saved retrain:

| K | BH within a window | Bonferroni within a window | LORD++ | LOND |
|---|---|---|---|---|
| 10 | 4 | 4 | 66 | 49 |
| 100 | 13 | 13 | 47 | 78 |
| 500 | 20 | 25 | 34 | 94 |

The numbers are steps spent on a degraded model. The correction pays off if a false retrain costs
more than that many steps. Note that at small K the uncorrected rule is not fast by itself: a
false alarm pauses the stream while a new reference is collected, and if a drift falls into that
pause, the delay grows.

Comparison of detectors at K = 100: after calibration PH gives the best balance. ADWIN's p-value
tail is so anti-conservative that even Bonferroni gives an FDR of 0.48, and LORD++ 0.24. KS keeps
FDR at 0.07 with LORD++, but with Bonferroni and BH it is slower than PH (about 295 steps against
210). DDM finds almost nothing with corrections. Details: `results/exp2_tables.md`.

### Experiment 3. The trade-off frontier

![False retrains vs delay](../results/figures/exp3_tradeoff.png)

For every rule the level α ranges from 1e-4 to 0.2, giving a "false retrains ↔ delay" curve.
Lower and further left is better. The key result: at an equal number of false retrains the
"uncorrected" curve (a fixed per-stream threshold lowered to the required level) lies no higher
than LORD++ and BH within a window, and lower at K = 500. For example, at K = 500 the uncorrected
threshold with α = 1e-4 and Bonferroni with α = 0.05 (essentially the same rule, α/K per stream)
give 0.00085 false retrains per 1000 steps at a delay of 265 steps. LORD++ with the same number of
false retrains gives 324 steps. At K = 100 the picture is the same: BH within a window with
α = 0.05 and the uncorrected threshold with α = 0.001 give the same 0.0064 false retrains per 1000
steps, but a delay of 212 and 201 steps respectively.

Interpretation: in this scenario drifts are rare and spread out in time, a window usually holds at
most one, and the adaptivity of FDR has nothing to adapt to. The gain over current practice comes
from calibration making it possible to set a per-stream level at all, and that level scales with
K. Online procedures with decreasing levels (LORD++, LOND) spend the error budget unevenly over
time, which is a poor fit for open-ended monitoring.

## What stage 1 showed

1. **A binary signal is not enough; a score is needed.** A p-value from a black box with one
   threshold takes two values, and online FDR over hundreds of streams will never reject it. The
   solution is the "least sensitivity" score; for PH and DDM it matches river exactly.
2. **Evidence must accumulate.** If each window is tested on its own, LORD++, SAFFRON and LOND
   find almost nothing: their levels fall with the number of tests faster than evidence grows. A
   horizon of several windows solves this, and causal scores make it possible to calibrate every
   horizon length with one bootstrap.
3. **The bottleneck of calibration is the deep tail.** With an exponential tail, a 10% error in
   its scale gives a 2–6-fold error in the p-value at levels around 1e-5, and the estimate from a
   300-point reference is noisier than that. This agrees with the effect described by Wu & Apley;
   a correction for the variability of the null estimate is needed. *(Later done: `sieve_pu`,
   exp. 6; a GPD tail and B = 2000, exp. 10.)*
4. **Dependence between streams is not a detail.** A common factor produces bursts of false
   alarms and breaks procedures that rely on independence.
5. **The two-sided hypothesis leans towards the second outcome so far.** In a homogeneous
   scenario with rare drifts the FDR layer is no better than a properly scaled per-stream
   threshold. Where it could pay off is an open question for stage 2. *(Later refined: BH within a
   window wins with clustered drifts, exp. 4; online FDR loses everywhere, exp. 12, 21; the
   correction for the number of models itself pays off in every benchmark scenario, exp. 21.)*

## Stage 2: when the correction pays off, real data, the null hypothesis

Stage 2 of the proposal is the FDR layer itself, dependence between streams, the retraining
policy and the Pareto frontier. After the MVP the main open question was where the adaptivity of
FDR can beat a per-stream threshold scaled to K at all. For it the following were added:

- **Scenarios with clustered drifts** (`drift_events`, `event_fraction` in `ScenarioConfig`): one
  event shifts a group of streams at once, as when the data source of many models changes.
- **BatchBH** (Zrnic et al., 2020): BH within a window at levels that control FDR across all
  windows.
- **Storey's BH within a window** (Storey, Taylor & Siegmund, 2004): BH at level α/π̂₀, which
  raises the threshold by itself when many streams drift at once.
- **The `window_fdp` metric** — the share of false alarms among the alarms in a window, averaged
  over windows. BH and Storey's BH within a window control it. Their share of false alarms over
  the whole run (`fdp`) is above α: in a simulation with independent p-values and α = 0.1 it is
  0.14–0.17 against 0.09–0.11 within a window. Which of the two errors to control in monitoring
  has to be chosen explicitly, and this is a separate point for the paper.

### Experiment 4. Does adaptivity pay off with clustered drifts

In 20% of the streams the mean changes: either each at its own time, or in two events of 10% of
the streams, or in one event of 20%. For each rule the level α ranges from 1e-5 to 0.2. The rules
are compared by the best delay they reach without exceeding a budget of false retrains. PH,
φ = 0.5, ρ = 0.3, 6 scenarios per cell.

![Best delay within a budget of false retrains](../results/figures/exp4_budget_0.01.png)

- **With clustered drifts BH within a window beats the best fixed per-stream threshold.** In 7 of
  8 cells (K × scenario × budget) the delay is 16–22% smaller, in one 6%. At K = 500 and one event
  this is 172 steps against 206 with a budget of 0.01 false retrains per 1000 steps, and 216
  against 271 with a budget of 0.001. When many streams drift in the same window, BH raises the
  threshold and catches them earlier.
- **With scattered drifts there is no gain,** as in experiment 3: 219 against 199 at K = 500.
- **BatchBH is the slowest almost everywhere, LORD++ is usually slower than the fixed
  threshold.** Their levels decrease with the number of windows: the error budget is stretched
  over the whole open-ended history of monitoring.
- **Storey's BH within a window is usually worse than plain BH.** The estimate of the share of
  nulls from one window is too noisy. Its share of false alarms over the run is 0.28–0.40 at
  α = 0.05, although 0.03 within a window.

This is the first confirmation of the applied hypothesis in its strong form: a region where the
FDR approach dominates exists, and it is defined not by the number of streams but by whether
drifts come in clusters. Caveats: the α grid is coarse (7 values), 6 scenarios per cell, and with
a budget of 0.001 at K = 100 the spread between scenarios is large. Full curves:
`results/figures/exp4_clustered_curves.png`, tables: `results/exp4_tables.md`.

### Experiment 5. How much does accounting for dependence between streams give

The proposal expected naive corrections to become overly conservative with correlated streams, so
that block procedures for joint resampling would be needed. Before building such a procedure, the
ceiling of its gain was measured. On streams without drift, with correlation ρ from 0 to 0.9,
three things were computed: the probability of a false alarm in a window under Bonferroni; the
oracle per-stream level at which that probability is exactly 0.05, and the corresponding effective
number of tests M_eff; and the clustering of false alarms. Under strong correlation all streams of
a scenario move together, so the effective sample is the number of scenarios (60 at K = 100 and 16
at K = 500). Intervals come from resampling whole scenarios.

![Dependence between streams](../results/figures/exp5_dependence.png)

- **False alarms come in bursts, and this is the most robust effect.** The ratio of the variance
  of the number of false alarms per window to its mean is about 1 for independent streams, 6–29 at
  ρ = 0.3 and 50–230 at ρ = 0.9. In practice this means that several dozen false retrains can
  arrive in one window.
- **Even without correlation Bonferroni gives 0.09–0.11 instead of 0.05.** This is not dependence
  but the roughly 2-fold calibration error of the deep tail at levels of 1e-4…5e-4, the same as in
  experiment 1.
- **As correlation grows Bonferroni does become more conservative,** but noticeably only under
  strong correlation. M_eff falls to roughly 0.3–0.5·K at ρ = 0.9. At ρ = 0.3 the ceiling of the
  gain from accounting for dependence is about 1.3–1.7 times in the per-stream level, the same
  order as the tail calibration error. The intervals are wide, especially at K = 500.

Conclusion for the plan: joint bootstrap of the streams is justified if the models' errors are
strongly correlated in real data. In the data of Rombouts & Wilms the correlation of demand
between districts is 77%, but the correlation of the models' errors may be lower, and it has to
be measured (done in experiment 20). With moderate correlation the tail calibration should be
fixed first. A separate open question is how to tell a burst of false alarms caused by a common
factor from a real clustered drift as in experiment 4: from the outside they look the same
(answered in experiment 18).

### Experiment 6. Can the deep tail of the calibration be fixed

Hypothesis: the p-values are too small at levels around α/K because the bootstrap treats the AR
model estimated from the 300 points of the reference as exact (the Wu & Apley effect). The new
scheme `sieve_pu` re-estimates the coefficients from the simulated reference in every bootstrap
replicate, so the estimation uncertainty enters the null distribution.

![Calibration of the deep tail](../results/figures/exp6_tail.png)

- **It helps, but only partly.** With Bonferroni over 100 independent streams the probability of
  a false alarm in a window fell from 0.090 to 0.077 for PH and from 0.25 to 0.18 for ADWIN
  (target 0.05, 40 scenarios). For KS it did not change (0.06).
- **Power barely suffers:** within 1–4 percentage points.
- **The remaining error is probably the shape of the tail.** Especially for ADWIN: its statistic
  is a maximum over many split points, and its tail is heavier than the exponential used for
  extrapolation. Next candidates: a GPD tail with the shape estimated from more replicates
  (B = 2000+) or a double bootstrap for the tail only.

`sieve_pu` was kept as the default method for real data (experiment 7), and is now the library
default.

### Experiment 7. Real data

A fleet of 50 models (logistic regressions on random subsets of features, trained on an initial
segment) on two real data sets, rows **not shuffled**, `sieve_pu` calibration, α = 0.05, 3 repeats
with different models (`src/driftfdr/datasets.py`).

**INSECTS** (Souza et al., 2020). The documented drifts hit all models at once — a natural
clustered case; the models' errors correlate at 0.77. In river's copy, the documented change
points are preceded by long blocks of a single class that the models never predict, and the error
there is 100%. This is a real but unlabelled change; so results are given for two labellings: the
documented one and an extended one (plus the starts of such blocks, found from the labels alone).

![INSECTS: alarms by window](../results/figures/exp7_insects_timeline.png)

| PH, extended labelling | alarms | false | FDP | mean delay |
|---|---|---|---|---|
| river thresholds | 911 | 680 | 0.75 | 1620 |
| uncorrected | 165 | 26 | 0.15 | 162 |
| Bonferroni within a window | 120 | 4 | 0.03 | 218 |
| BH within a window | 123 | 2.7 | 0.02 | 166 |
| LORD++ | 117 | 1.3 | 0.01 | 244 |

- **On real data the method works.** Calibrated p-values plus a correction cut the share of false
  alarms from 75% (river's defaults) and 15% (uncorrected) to 1–3%. BH within a window is also the
  fastest: on a clustered event it retrains all 50 models in one window, while Bonferroni and
  LORD++ stretch this over 2–3 windows (as in exp. 4).
- **With the documented labelling the FDP is about 0.45 for every rule:** almost half of the alarms
  fall into the unlabelled single-class blocks. The labelling of real data shapes the conclusions
  no less than the method does.
- **There are many misses (MDR ≈ 0.7),** but these are mostly changes after which the error
  *falls*: PH and DDM watch only for a rise in the error and deliberately ignore such changes.
- On the first stable concept there are almost no false alarms (FAR 0.0007 at α = 0.05): the
  models' loss decreases slightly there, and a one-sided test does not react.

**Electricity** (Harries, 1999). There are no labels, so in 20% of the models the labels are
flipped with probability 0.5 after a known time (the model loses the concept completely) — a real
p(y|X) drift injected into a real temporal structure.

- **Here the method does not work, and this is an important result.** FDP is about 0.97 for every
  rule, and the injected drift is caught only in half of the cases. Electricity is non-stationary
  by itself (seasonality, error autocorrelation 0.84): "stable" models alarm on natural changes,
  and the regime null is violated all the time.
- **A long reference helps little:** with 700 and 1400 steps instead of 300 (more than the weekly
  cycle of 336 steps), Bonferroni's false alarms per window are 0.37 and 0.32 instead of 0.48, and
  the FDP is still 0.96.
- This is the second risk from the proposal: on streams where the distribution drifts all the
  time, a binary "drift / no drift" does not work. Either a model of seasonality in the null or a
  move to "material" drift (a change in error above a threshold) is needed.

Tables: `results/exp7_tables.md`.

### Experiment 8. The null hypothesis of "material and persistent degradation"

Experiment 7 showed that on constantly changing data the question "is there drift" loses its
meaning. For a retraining decision something else matters: did the model become **materially**
worse, and for long. Hence two changes:

- **In the test** H₀: "the error rose by no more than δ". Calibration shifts the bootstrap
  continuation up by δ (for 0/1 errors, the required share of zeros is flipped); this is the least
  favourable point of the null, so the p-value is valid for any smaller rise
  (`CalibrationConfig(tolerance=δ)`).
- **In the evaluation** the truth is what the model will cost if it is not retrained: its error
  over the next 1000 steps against its error on the reference (`datasets.error_rate_view`). A
  short spike that passes by itself does not require a retrain and counts as null. No drift
  labels are needed at all.

Found and fixed along the way: a reference consisting only of errors (a model inside a
single-class block) gave a degenerate null distribution and alarms when the error *fell*. Such
streams are now treated as untestable (p = 1).

![Rejection curve](../results/figures/exp8_oc.png)

On synthetic data with shifts from 0 to 1σ the test with a tolerance behaves as intended: shifts
smaller than δ give almost no alarms (0–1.7% at δ = 0.3 against 12–58% for the ordinary test),
at the boundary δ about α (0.10 at δ = 0.3, the same slight anti-conservativeness of the tail),
and beyond it the power grows.

| Real data, 50 models, δ = 5 points of error | FDP uncorrected | FDP Bonferroni | FDP BH within a window |
|---|---|---|---|
| INSECTS, ordinary test | 0.39 | 0.24 | 0.24 |
| INSECTS, test with tolerance | **0.013** | **0.007** | **0.007** |
| Electricity, ordinary test | 0.58 | 0.31 | 0.25 |
| Electricity, test with tolerance | 0.35 | 0.35 | 0.32 |

- **On INSECTS the problem is solved:** with a tolerance there are almost no false retrains even
  without a multiplicity correction — the right null hypothesis does the main work.
- **On Electricity the share of false alarms fell from 0.97 (experiment 7) to 0.25–0.35.** The
  remainder is mostly short-lived spikes of the error: PH takes the maximum score within a window
  and reacts to them. The next step is a statistic that requires persistence (the mean over the
  whole horizon instead of the maximum within a window).
- The share of rejected non-null tests is low (`power_per_test` ≈ 0.01–0.1), but this is expected:
  after the first alarm the model is retrained, and later windows of the same degradation are no
  longer tested against the old level.

Tables: `results/exp8_tables.md`.

### Experiment 9. Requiring persistence

A new detector `MeanShift(persistence=m)`: the statistic is the smallest excess of the mean error
over the reference level among the last m windows; until m windows have passed, no alarm is
possible. A one-window spike cannot pass such a statistic. The same calibration (bootstrap with
tolerance δ = 5 points), 50 models, 3 fleets per data set.

| Electricity, FDP | uncorrected | Bonferroni | BH within a window |
|---|---|---|---|
| PH | 0.35 | 0.35 | 0.32 |
| MeanShift(1) — no persistence | 0.44 | 0.36 | 0.34 |
| MeanShift(3) | **0.12** | 0.27 | **0.00** |
| MeanShift(5) | 0.40 | **0.01** | 0.55 |

- **Persistence helps, but the result is noisy.** The remaining false alarms on Electricity are
  episodes where the whole fleet gets worse for several weeks and then recovers by itself: 26–27
  false alarms at once. Whether such an episode falls into a run depends on when the models were
  retrained, so the FDP jumps between 0 and 0.55 for similar settings. Dozens of fleets are
  needed, not three.
- **On INSECTS every variant gives 0–2% false alarms;** persistence costs a little power (the
  share of rejected non-null tests is 0.08 at m = 3 against 0.10 for PH).
- Episodes of "the whole fleet is worse for a while" are the same problem as in experiment 5: a
  burst from a common factor is hard to tell from a real clustered drift. The answer is a matter
  of horizon: what counts as "for long" (here 1000 steps ≈ 3 weeks) is decided by the cost of a
  retrain.

Tables: `results/exp9_tables.md`.

### Experiment 10. More replicates and a heavy tail

Two more levers on the same check (100 independent streams, 30 scenarios, `sieve_pu`): B = 2000
bootstrap replicates instead of 500 and a GPD tail with an estimated shape instead of the
exponential one.

| Bonferroni, P(false alarm in a window), target 0.05 | B = 500, exponential | B = 500, GPD | B = 2000, GPD |
|---|---|---|---|
| PH | 0.081 | 0.073 | **0.056** ± 0.015 |
| KS | 0.059 | 0.049 | **0.046** ± 0.015 |
| ADWIN | 0.177 | 0.148 | 0.147 ± 0.021 |

- **For PH and KS the tail of the calibration is fixed:** with a GPD tail and 2000 replicates the
  error is within the error bars of nominal. GPD beats the exponential in all 6 comparisons.
- **ADWIN stays about three times anti-conservative.** Its statistic is a maximum over many split
  points, and its tail is heavier than these methods can extrapolate. For strict control of false
  alarms PH, KS or MeanShift are better.

Tables: `results/exp10_tables.md`.

### Experiment 11. Which detector sees which drift: p(X) vs p(y|X)

A scenario with a feature, a label and a fixed linear model (`make_supervised_scenario`). Virtual
drift shifts the feature's distribution, but the model stays correct; real drift changes the
slope, and the error grows; "both" does both at once; cyclic switches the slope every 1000 steps.
300 models × 3 repeats, calibration, Bonferroni within a window, α = 0.05. The table gives the
share of models that received at least one alarm after the drift began.

| detector | no drift | p(X), model not worse | p(y\|X) | both | cyclic |
|---|---|---|---|---|---|
| KS on the feature | 1% | **100%** | 0.6% | 100% | 0% |
| PH on the feature (two-sided) | 0.6% | **99%** | 0% | 100% | 0% |
| PH on the loss | 2% | 2% | 28% | 72% | 21% |
| MeanShift(3) on the loss | 2% | 0.6% | 20% | 62% | 12% |
| DDM on 0/1 errors | 1% | 0% | 0% | 1% | 0% |

- **Feature detectors answer the wrong question.** They alarm on every model with virtual drift,
  that is, cause needless retrains, and do not see real drift at all. This is a quantitative
  answer to the conflation of the two kinds of drift in the applied literature.
- **Detectors on the model's error barely react to virtual drift** and catch real drift. But with
  300 models and Bonferroni a loss shift of 0.25 (with a strongly skewed squared loss) is caught
  in only 20–28% of the models: for weak real drift the multiplicity correction is expensive.
- **Cyclic drift is caught worse than a persistent one:** half of the time the model is right
  again, and evidence has no time to accumulate.
- **DDM on 0/1 errors finds almost nothing** — as in experiments 1 and 2.

Conclusion for practice: retraining decisions should be based on the model's error, and feature
detectors used as diagnostics ("what changed"), not as a trigger.

Tables: `results/exp11_tables.md`.

### Experiment 12. The trade-off frontier by type and size of drift

As experiment 3, but separately for abrupt and gradual (a 500-step ramp) drift of 0.5σ and 1σ;
K = 100, 10% of the models with scattered drifts, ρ = 0.3, 6 scenarios. The best delay (steps on a
stale model) within a budget of false retrains per 1000 steps:

| drift | budget | uncorrected / Bonferroni | BH within a window | LORD++ |
|---|---|---|---|---|
| abrupt, 0.5σ | 0.001 | **1300** | 1710 | 1940 |
| abrupt, 0.5σ | 0.01 | **741** | 1190 | 1940 |
| abrupt, 1σ | 0.001 | **252** | 339 | 478 |
| abrupt, 1σ | 0.01 | **201** | 212 | 332 |
| gradual, 0.5σ | 0.001 | 1510 | **1460** | 1970 |
| gradual, 0.5σ | 0.01 | **1100** | 1460 | 1970 |
| gradual, 1σ | 0.001 | **556** | 692 | 656 |
| gradual, 1σ | 0.01 | **441** | 462 | 612 |

- **The conclusion of experiment 3 holds for every type and size of drift:** with scattered drifts
  the best fixed per-stream threshold is no worse than BH and always better than LORD++ (at an
  equal budget "uncorrected" and "Bonferroni" are the same rule α/K). The only exception (gradual
  0.5σ, budget 0.001) is within noise.
- **Weak drift is caught several times more slowly:** 740–2000 steps at 0.5σ against 200–550 at
  1σ; gradual drift is slower than abrupt.
- **MTR (Bifet et al., 2013) is not very informative here:** rules with a correction have no false
  alarm at all in some runs, so MTFA and MTR are infinite. Trade-off curves are more useful for
  comparing rules.

Tables: `results/exp12_tables.md`.

### Experiment 13. e-BH: FDR control under any dependence

e-BH (Wang & Ramdas, 2022) controls FDR under any dependence between models; p-values are turned
into e-values with the calibrator e = 0.5 / √p. K = 200, 10% of the models drift, 10 scenarios,
α = 0.05.

| ρ | Bonferroni: FDR / delay | BH within a window: FDR / delay | e-BH: FDR / delay / misses |
|---|---|---|---|
| 0 | 0.03 / 237 | 0.07 / 221 | 0 / 1310 / 37% |
| 0.3 | 0.05 / 228 | 0.11 / 213 | 0 / 1210 / 34% |
| 0.6 | 0.05 / 223 | **0.17** / 217 | 0 / 1040 / 26% |

- **e-BH is too cautious for monitoring:** not a single false alarm, but a third of the drifts
  missed and five times the delay. The price of a guarantee "under any dependence" does not pay
  off here.
- **BH within a window loses control of the overall share of false alarms as correlation grows**
  (0.07 → 0.17), although within a window it keeps its 0.02 — the very bursts of experiment 5.
- **Bonferroni within a window stays around 0.05 under any correlation** and at almost the same
  delay as BH. For correlated models it is the most reliable practical choice; BH is worth taking
  when clustered drifts are expected (experiment 4) and the correlation of errors is moderate.

Tables: `results/exp13_tables.md`.

### Experiment 14. Four real data sets

INSECTS and Electricity (natural changes only, no injected drift) in full, the first 100 thousand
rows of Airlines and Covertype; rows in their original order, 50 models each, 2 fleets. The truth
is material degradation: the error over the next 1000 steps exceeds the reference error by more
than 5 points. "river" is Page-Hinkley at its default threshold on the 0/1 error series. The share
of false alarms among alarms:

| data | river | PH, uncorrected | PH, Bonferroni | MeanShift(3), uncorrected | MeanShift(3), Bonferroni | MeanShift(3), BH |
|---|---|---|---|---|---|---|
| INSECTS | 0.50 | 0.01 | **0** | 0.01 | **0** | **0** |
| Electricity | 0.56 | 0.34 | 0.30 | 0.08 | 0.27 | **0** |
| Covertype | 0.75 | 0.50 | 0.29 | 0.24 | **0.15** | 0.21 |
| Airlines | **0.26** | 0.37 | 0.33 | 0.35 | 0.35 | 0.32 |

- **On three data sets out of four, calibration with the material-degradation null sharply cuts
  the share of false retrains:** INSECTS 50% → 0%, Electricity 56% → 0–8%, Covertype 75% → 15%.
  The best combination almost everywhere is the persistent MeanShift(3).
- **On Airlines the method does not help.** 1000 rows there are about an hour and a half of
  flights, and the share of delays depends strongly on the time of day; "the future error over
  1000 steps" oscillates within a day, and the null on such a horizon is poorly posed. For such
  data the horizon and the reference should be measured in days, not rows (experiment 16).
- river's threshold on Airlines alarms rarely and therefore looks better, but this is an accident
  of tuning, not control of the error.

Tables: `results/exp14_tables.md`.

### Experiment 15. A benchmark of all detectors at a single FAR

Like the second part of experiment 1, but with every detector of the package and the stage 2
calibration (`sieve_pu`, block bootstrap for 0/1 errors). In half of 1000 streams (φ = 0.5) the
mean shifts at a known time; every detector is calibrated to a nominal FAR of 0.05.

| detector | actual FAR | 0.5σ: 1st window | 0.5σ: 3rd window | 1σ: 1st window |
|---|---|---|---|---|
| MeanShift(1) | 0.062 | **0.82** | 0.81 | **1.00** |
| KS-sliding | 0.064 | 0.49 | 0.72 | 0.99 |
| ADWIN | 0.073 | 0.52 | 0.89 | 0.98 |
| PH | 0.062 | 0.31 | 0.90 | 0.84 |
| MeanShift(3) | **0.044** | 0.11 | **0.93** | 0.11 |
| KS | 0.059 | 0.12 | 0.59 | 0.28 |
| DDM | 0.065 | 0.09 | 0.31 | 0.24 |

- **For a shift in the mean error the most powerful detector is the simplest, MeanShift(1),**
  comparing the window mean with the reference: 0.82 already in the first window at 0.5σ against
  0.31 for PH and 0.52 for ADWIN. Popular detectors lose to it in a fair comparison at one
  false-alarm rate.
- **MeanShift(3) is the most conservative (FAR 0.044) and the most powerful by the third window**
  (0.93), but by construction it cannot fire earlier: the price of persistence, which paid off on
  real data (experiment 14).
- **Sliding KS is clearly better than batch KS** in the first window (0.49 against 0.12), but does
  not catch up with MeanShift, because KS reacts to any change in the distribution, not
  specifically to a rise in the mean.
- **DDM is the weakest at any shift,** as in experiments 1, 2 and 11.
- ADWIN is powerful, but its FAR of 0.073 is above nominal — the same tail problem as in
  experiment 10.

Tables: `results/exp15_tables.md`.

### Experiment 16. Time in hours, not rows

In experiment 14 the method did not help on Airlines: 1000 rows are an hour and a half of flights,
and the share of delays depends on the time of day (0.26 in the morning, 0.53 in the evening).
Here each model's errors are averaged per hour (`bucket_means`) over all 31 days; the reference is
a week (168 hours), the window a day (24 hours), the truth the error over the next week,
δ = 5 points; 50 models, 3 fleets.

| detector | uncorrected | Bonferroni | BH within a window |
|---|---|---|---|
| PH | 0.15 | 0 | 0 |
| MeanShift(1) | **0** | **0** | **0** |
| MeanShift(2) | 0.06 | 0 | 0.04 |

- **The share of false retrains fell from 0.31–0.37 (per row) to 0–0.06.** When a window covers a
  whole daily cycle, the cycle cancels out, and only real changes remain.
- Rule of thumb: the reference and the window should be set in units of time that are multiples of
  the data's natural cycle (day, week), not in numbers of observations. `bucket_means` also solves
  the problem of irregular streams: however many events arrive in an hour, it is one point.
- The tolerance δ can be chosen from the cost of a retrain: `tolerance_from_cost(cost, horizon)` =
  the cost of a retrain / the number of steps until the next scheduled retrain (retraining pays
  off if a rise of δ in the error over that period costs more than the retrain itself).

Tables: `results/exp16_tables.md`.

### Experiment 17. Comparison with Evidently and NannyML

All tools look at the same 0/1 error series of each model, against the same static reference
(the first 1000 steps after training, no retraining), in windows of 100 steps, and are judged by
the same truth — material degradation (δ = 5 points). 20 models, 2 fleets.

- **Evidently 0.7**, `ValueDrift` on the error column: for a binary column the default is a
  two-proportion Z-test, drift at p < 0.05. The test is reimplemented in code (an Evidently report
  for every window of every model takes about 36 ms, tens of minutes per run) and checked against
  the real Evidently on 300 random cases: p-values differ by at most 1e-16.
- **NannyML 0.13**, `PerformanceCalculator` on accuracy, chunk = window, default thresholds (mean ±
  3σ of the accuracy over the reference chunks); an alarm is a drop below the lower threshold.
- **driftfdr**: MeanShift(1) with calibrated p-values, with and without a tolerance δ, for each
  model (α = 0.05) and with Bonferroni across models.

| data | method | FAR | power | FDP |
|---|---|---|---|---|
| Electricity | Evidently | 0.51 | 0.71 | 0.28 |
| Electricity | NannyML | 0.014 | 0.11 | 0.06 |
| Electricity | driftfdr, δ = 0.05, Bonferroni | 0.016 | 0.13 | 0.06 |
| INSECTS | Evidently | 0.20 | 0.89 | 0.07 |
| INSECTS | NannyML | 0.031 | 0.81 | 0.013 |
| INSECTS | driftfdr, δ = 0.05, uncorrected | 0.021 | 0.78 | 0.010 |
| Airlines | Evidently | 0.54 | 0.64 | 0.82 |
| Airlines | NannyML | 0.006 | 0.38 | 0.08 |
| Airlines | driftfdr, δ = 0, Bonferroni | 0.006 | 0.37 | 0.08 |
| Covertype | Evidently | 0.78 | 0.77 | 0.87 |
| Covertype | NannyML | 0.004 | 0.05 | 0.47 |
| Covertype | driftfdr, δ = 0.05, Bonferroni | 0.028 | 0.34 | 0.36 |

FAR is the share of alarms in windows without material degradation, power the share in windows
with it.

- **Evidently's standard drift test on the error series is nearly useless as a retraining
  trigger:** alarms in 20–78% of the windows where the model did not get worse. The test assumes
  independent observations, reacts to any change (including an improvement) and knows nothing about
  a tolerance.
- **NannyML and driftfdr catch degradations about equally well at a comparable false-alarm
  rate.** NannyML's performance monitoring also calibrates its threshold on the spread of the
  reference data, and this works.
- **The difference is in control, not in power.** In driftfdr the false-alarm rate is set
  explicitly (α) and accounts for the number of models and the tolerance δ; NannyML's ±3σ
  threshold is fixed and does not depend on the fleet size — on Covertype it catches almost
  nothing (power 0.05), and on INSECTS it allows more false alarms. Only driftfdr lets you choose
  the trade-off point for the cost of a retrain.

Tables: `results/exp17_tables.md`. Running it requires `pip install evidently nannyml`.

### Experiment 18. Bursts of false alarms vs fleet-wide drift

When models share a common factor (a common data stream, a common source of features), many of
them look worse at once even without any drift (exp. 5), as they do after a real fleet-wide drift
(exp. 4). `split_common` standardises the series by the reference and subtracts the
cross-sectional median at every step: the residuals are tested per model as usual, and the common
component as one more stream in the same procedure; its alarm means an event across the whole
fleet. K = 200 AR(1) streams (φ = 0.5), correlation through a common factor ρ ∈ {0.3, 0.6},
Page-Hinkley, α = 0.05, 10 runs. Scenarios: no drift; a drift in 20% of the models at once; a
drift in all models.

| rule | scenario | ρ | method | false alarms | max burst | delay | fleet alarm |
|---|---|---|---|---|---|---|---|
| Bonferroni | no drift | 0.6 | raw series | 1.4 | 0.7 | — | — |
| Bonferroni | no drift | 0.6 | residuals | 0.9 | 0.8 | — | — |
| Bonferroni | 20% of models | 0.6 | raw series | 2.0 | 0.6 | 244 | — |
| Bonferroni | 20% of models | 0.6 | residuals | 0.7 | 0.6 | 190 | — |
| Bonferroni | all models | 0.6 | raw series | 0.1 | 0.1 | 236 | — |
| Bonferroni | all models | 0.6 | residuals + fleet test | 0.2 | 0.2 | 191 | 1.0 |
| BH within a window | no drift | 0.6 | raw series | **22.9** | **15.3** | — | — |
| BH within a window | no drift | 0.6 | residuals | 0.9 | 0.8 | — | — |
| BH within a window | 20% of models | 0.6 | raw series | 12.6 | 5.3 | 167 | — |
| BH within a window | 20% of models | 0.6 | residuals | 1.4 | 1.1 | 138 | — |
| BH within a window | all models | 0.6 | raw series | 6.7 | 6.5 | 115 | — |
| BH within a window | all models | 0.6 | residuals | 0.2 | 0.2 | not caught | — |
| BH within a window | all models | 0.6 | residuals + fleet test | 0.2 | 0.2 | 191 | 1.0 |

False alarms and bursts are per run (a burst is the largest number of false alarms in one
window), the delay is in steps until an affected model alarms, and the fleet alarm is the share of
runs in which the test of the common component fired after the event. The fleet test gives 0.1–0.2
false alarms per run.

- **Bursts are a problem of BH, not of Bonferroni.** With Bonferroni on the raw series there are
  few false alarms even at ρ = 0.6. BH within a window at the same correlation and without any
  drift gives 23 false retrains per run, up to 15 in one window: the common factor shifts all
  p-values at once, and BH takes it for a fleet-wide drift.
- **Residuals remove the bursts and speed up the reaction.** After subtracting the common
  component BH gives 0.9 false alarms instead of 23, and with a drift in 20% of the models both
  fewer false alarms (1.4 against 12.6) and a shorter delay (138 against 167 steps): the common
  noise no longer masks the signal of an individual model. With Bonferroni the gain goes the same
  way but is smaller (0.7 against 2 false alarms, 190 against 244).
- **Residuals cannot see a drift of the whole fleet by construction** — it goes entirely into the
  common component. That is why a separate test of the common component is needed: it catches
  such a drift in every run within 131–191 steps (raw series with Bonferroni: 236) at 0.1–0.2 false
  fleet alarms per run.
- **Practical conclusion.** If the models are noticeably correlated and BH is needed, monitor the
  residuals plus the common component, not the raw series. An alarm of the common component
  signals that "something shared broke" (a data source, a feature pipeline), which is better
  handled as an incident than by retraining every model. With weak correlation (ρ = 0.3) the
  difference is small.

Limitation: the common component is estimated by the median across models, so the scheme assumes
fleets in which fewer than half of the models drift at once. In the streaming monitor the scheme
is enabled with `StreamingMonitor(..., split_common=True)`; an alarm of the common component sets
`monitor.fleet_alarm`. Tables: `results/exp18_tables.md`.

### Experiment 19. Runtime

One process, one core, window 100 steps, reference 300, horizon 5 windows; median of 10 repeats.
The comparison with Evidently and NannyML uses the same calls as experiment 17.

| detector | calibration of one model, B = 2000, GPD | B = 500, exponential | monitoring step |
|---|---|---|---|
| MeanShift(1), MeanShift(3) | 0.03–0.04 s | 0.005 s | 0.7 µs |
| Page-Hinkley | 0.07 s | 0.013 s | 0.9 µs |
| KS | 0.48 s | 0.11 s | 3.5 µs |
| ADWIN | 0.68 s | 0.11 s | 8 µs |
| river Page-Hinkley / ADWIN, no calibration | — | — | 0.7 / 0.1 µs |

| fleet, Page-Hinkley | calibration of the whole fleet | step for all models | with `split_common` |
|---|---|---|---|
| 100 models | 10 s | 0.11 ms | 0.18 ms |
| 1000 models | 99 s | 1.3 ms | 1.7 ms |

| per model, 0/1 errors | time per window of 100 steps |
|---|---|
| driftfdr, MeanShift(1) | 0.05 ms |
| NannyML, all windows in one call / one call per window | 6.5 / 10.9 ms |
| Evidently, a `ValueDrift` report | 36 ms |

- **Monitoring costs as much as the river detector itself.** A p-value from a ready null
  distribution and the multiplicity correction add almost nothing; `split_common` adds about
  0.5 µs per model.
- **The only noticeable cost is calibration:** a fraction of a second per model once after each
  retrain, up to 100 s for a fleet of 1000 models at start-up. It parallelises across models. For
  PH and MeanShift it is under 0.1 s; KS and ADWIN are an order of magnitude more expensive.
- **Evidently and NannyML are orders of magnitude slower per window,** but they are general
  frameworks with reports and pandas, not lightweight detectors; the conclusion is that driftfdr's
  overhead is negligible, not that it is "faster than the competition".
- In the fleet table, with 10 models the step time is higher because of one false alarm: the
  recalibration after an alarm is included in the step time.

Tables: `results/exp19_tables.md`. The comparison with other tools requires
`pip install evidently nannyml`, otherwise that part is skipped.

### Experiment 20. How correlated are models on real data

Experiment 5 showed that joint bootstrap of the streams can noticeably beat Bonferroni only under
strong dependence between models, and the decision about it was postponed until that dependence
was measured on real data. Here it is measured. On each of the four data sets, 50 models;
MeanShift(1) gives a p-value for every window of 100 steps of 0/1 errors against a static
reference (1000 steps, as in exp. 17). Only windows without material degradation (δ = 5 points)
count, that is, the correlation of null p-values — the one a correction has to deal with. The
scale is given by the same numbers on synthetic data with a common-factor share ρ. 2 repeats.

| data | correlation of p-values: raw errors | after `split_common` | clustering: raw | after `split_common` |
|---|---|---|---|---|
| Airlines | 0.88 | 0.24 | 16 | 6.4 |
| INSECTS | 0.71 | 0.19 | 25 | 4.5 |
| Electricity | 0.65 | 0.33 | 18 | 13 |
| Covertype | 0.40 | 0.17 | 8.1 | 2.8 |
| synthetic ρ = 0 / 0.3 / 0.6 / 0.9 | 0 / 0.29 / 0.59 / 0.89 | | 0.9 / 5.5 / 14 / 30 | |

Correlation is the mean rank (Spearman) correlation over pairs of models; clustering is the
variance / mean of the number of models with p < 0.05 in a window (1 without dependence).

- **On real data the models are strongly correlated:** on the synthetic scale this is ρ ≈ 0.4–0.9.
  Partly this is by construction: all models of a fleet predict the same target on the same rows.
  But in production fleets models also often share a data source and features.
- **`split_common` removes most of the dependence:** the correlation falls to 0.17–0.33, that is,
  to the moderate zone ρ ≈ 0.15–0.35, where according to experiment 5 the ceiling of the gain of a
  joint bootstrap is 1.3–1.7 times in the per-model level, the same order as the tail calibration
  error. The clustering of false alarms falls 2.5–6 times, on Electricity only 1.3 times.
- **Conclusion for the plan:** a joint bootstrap is not needed if the residuals come from
  `split_common`; the dependence it would account for is mostly shared and goes into the common
  component. Without `split_common`, Bonferroni is the safe choice on real fleets.
- On Electricity there are few windows in which almost all models are in the null regime (12 per
  repeat on average), so its numbers are rough.

Tables: `results/exp20_tables.md`.

### Experiment 21. A single benchmark of 100 scenarios

The fixed suite `benchmark_suite()`: 25 cases × 4 seeds. The cases are abrupt or gradual (500
steps) drift of 0.5σ or 1σ × correlation between models ρ = 0, 0.3, 0.6 × scattered drifts (10% of
100 models) or two events (5% of the models each at once), plus a case without drift. All
calibrated detectors with all main rules at α = 0.05, on the raw series and on the residuals of
`split_common`; the baseline is river's Page-Hinkley at its default threshold. F1 is event-level,
as in Cerqueira et al.: a detection counts within 1000 steps after the drift.

| method | F1 | precision | recall | P(false alarm in a window) | delay |
|---|---|---|---|---|---|
| **MeanShift(3), residuals, BH within a window** | **0.88** | 0.85 | 0.90 | 0.016 | 507 |
| PH, residuals, BH within a window | 0.88 | 0.85 | 0.89 | 0.013 | 460 |
| PH, residuals, Bonferroni | 0.86 | 0.85 | 0.86 | 0.011 | 499 |
| PH, raw, Bonferroni | 0.78 | 0.82 | 0.77 | 0.013 | 575 |
| PH, raw, BH within a window | 0.77 | 0.77 | 0.83 | 0.018 | 534 |
| ADWIN, raw, Bonferroni | 0.65 | 0.55 | 0.81 | **0.096** | 496 |
| PH, raw, LORD++ | 0.48 | 0.84 | 0.47 | 0.001 | 656 |
| PH, raw, uncorrected | 0.33 | 0.20 | 0.99 | 0.42 | 310 |
| river PH at its defaults | **0.06** | 0.03 | 1.00 | 0.89 | 208 |

The delay is the mean over caught drifts, in steps. The full table and F1 broken down by every
factor: `results/exp21_tables.md`.

| F1 by correlation between models | ρ = 0 | ρ = 0.3 | ρ = 0.6 |
|---|---|---|---|
| PH, raw, Bonferroni | 0.80 | 0.79 | 0.74 |
| PH, residuals, Bonferroni | 0.78 | 0.85 | 0.95 |
| MeanShift(3), residuals, BH within a window | 0.81 | 0.89 | 0.95 |

- **The best configuration over the whole suite is `split_common` residuals plus a correction:**
  F1 0.86–0.88 against 0.78 for the best on the raw series, 0.33 without a correction and 0.06 for
  river's defaults. river catches every drift, but 97% of its alarms are false — the same profile
  of "recall near 1, precision 0.03–0.08" that the review cites for GMA and RDDM in the benchmark
  of Cerqueira et al.
- **The gain from residuals grows with correlation** (F1 0.74 → 0.95 at ρ = 0.6) and costs almost
  nothing with independent models (0.80 → 0.78). On the raw series correlation hurts: the common
  factor masks an individual model's signal. Residuals remove it, and the signal becomes cleaner
  than without correlation.
- **The multiplicity correction is the main lever:** without it F1 is 0.13–0.33 for any detector.
  The choice between Bonferroni and BH within a window is secondary (±0.02 F1); BH is slightly
  faster.
- **Online FDR (LORD++) almost never catches weak drifts:** F1 0.01–0.08 at a 0.5σ shift, although
  its precision is high. This confirms experiments 3 and 12.
- **ADWIN is the only detector whose false-alarm level does not hold:** the probability of a
  false alarm in a window is 0.10–0.15 instead of ≤ 0.05 (exp. 10).
- In the scenario without drift, Bonferroni on the raw series at ρ = 0.3 gave no false alarm at
  all — it is conservative under correlation (exp. 5); on the residuals, 0.016 per window, within
  α.

### Experiment 22. A fleet of volatility models on hourly exchange rates

Data close to production: hourly quotes of five currency pairs (AUD/USD, EUR/USD, GBP/USD,
NZD/USD, USD/CAD) from 2010 to March 2026, ~100 thousand hours per pair (a MetaTrader 5 export; not
part of the repository, the loader is `fx_scenario`). On each pair eight models forecast the
absolute return of the next hour, that is, volatility: static ones (unconditional mean, daily
profile, HAR, HAR with the hour, ridge regression on lags) are trained once on 2010–2011; adaptive
ones (EWMA 0.94, EWMA 0.99, EWMA with the daily profile) adjust their level themselves. 40 models
in total. The loss of a forecast is `|log(|r| + c) − log(f + c)|`, a step is a trading day (the
mean loss over the day), the reference 120 days, the window 20 days, the horizon 3 windows. There
are no drift labels: an alarm is right if the model's mean loss over the next 60 days exceeds the
reference by more than δ. Changes of volatility regime (the calm of 2012–2014, 2015, 2020, 2022)
break the simplest static models for real: for the mean and the daily profile the loss wanders
between 0.76 and 1.03 from year to year; for HAR, the lag regression and EWMA, 0.6–0.76.

| δ = 0.05 | false alarms per model per year | share of false | persistent degradations caught (≥ 60 days) | degradations above 0.2 | delay, days |
|---|---|---|---|---|---|
| river Page-Hinkley at its defaults | 0 | — | **0%** | 0% | — |
| MeanShift(3), uncorrected | 0.004 | 0.05 | 57% | 100% | 100 |
| MeanShift(3), Bonferroni | 0 | 0 | 31% | 72% | 140 |
| MeanShift(3), BH within a window | 0.002 | 0.04 | 29% | 63% | 120 |
| MeanShift(3), BH within a window + `split_common` | 0.007 | 0.10 | 50% | 77% | 80 |
| PH, Bonferroni | 0 | 0 | 20% | 36% | 130 |

A persistent degradation is a run of at least three non-null windows; the breakdown by the size
of the degradation rests on a small number of episodes (dozens), so it is rough. Three bootstrap
seeds.

- **river's defaults stay silent for all 14 years.** Its threshold λ = 50 is set in signal units,
  and the daily loss is about 0.7, so it can never accumulate 50. On 0/1 errors the same threshold
  produced a flood of false alarms (exp. 14): a default threshold does not transfer between tasks
  in either direction. A calibrated threshold does not depend on the units of the signal.
- **There are almost no false alarms:** with a correction 0–0.007 per model per year, that is, one
  false alarm for a fleet of 40 models every few years. The material-degradation null is strict
  here: in null windows models improve more often than they get worse.
- **Large degradations are caught, small ones are not.** Degradations above 0.2 (roughly +30% of
  the loss) are caught in 63–100% of cases, up to 0.12 rarely. The noise of a window mean (about
  0.05–0.07) is comparable to small degradations, and 20 trading days per window cannot tell them
  apart.
- **With 40 models and a strict null, the correction costs power:** without a correction
  MeanShift(3) catches 57% of persistent degradations at a false share of 0.05, with Bonferroni
  31% with no false alarms. The multiplicity correction pays off when there are hundreds of models
  or the null is loose (exp. 2, 14); on a small fleet with a strict δ it can be relaxed (BH instead
  of Bonferroni, or a larger α).
- **`split_common` helps here too:** with BH it catches 50% of persistent degradations against 29%
  on the raw series, with a delay of 80 days instead of 120, at a false share of 0.10. The common
  component fired once in 14 years, falsely at δ = 0.05.
- **The delay is 3–7 windows (80–140 trading days).** For models retrained every quarter this is
  acceptable; for a fast reaction the window must be shorter, and small degradations become even
  less distinguishable.

Tables: `results/exp22_tables.md`. Run: `python experiments/exp22_fx.py DIRECTORY_WITH_CSV`.

### Experiment 23. Faster at the same false-alarm budget

Three ways to cut the delay, all through `StreamingMonitor` step by step, with Bonferroni and one
false-alarm budget: α = 0.05 per 100 steps across the fleet.

- **Whitening** (`Prewhitened`): the detector runs on standardised innovations of an AR model
  estimated on the reference.
- **Shorter windows:** 25 steps instead of 100 at α/4, so that the budget per 100 steps is the same.
- **A sequential e-detector** (`ECUSUM`): a mixture CUSUM e-detector on whitened innovations, in the
  windowed mode and checked at every step (`sequential=True`).

Synthetic data: K = 100 AR(1) models, φ = 0.5; abrupt or gradual drift of 0.5σ or 1σ in 10% of the
models; ρ = 0 or 0.6; 2 seeds per case, plus drift-free scenarios with 6 seeds each. An alarm is
false if the model's mean did not change from the start of its current reference to the alarm.
Real data: the 40 FX volatility models of experiment 22 (window of 20 trading days).

| method | delay, steps | 1σ abrupt | missed | F1 | false alarm per 100 steps without drift, ρ = 0 / 0.6 | µs per model per step |
|---|---|---|---|---|---|---|
| **e-CUSUM, every step** | **375** | **101–104** | 5% | 0.77 | 0.025 / 0.046 | 7.5 |
| e-CUSUM, window 100 | 427 | 140–155 | 4% | 0.76 | 0.025 / 0.046 | 2.1 |
| MeanShift(3), window 100 | 504 | 280–295 | 4% | 0.78 | 0.018 / 0.035 | 1.6 |
| PH, window 100 | 506 | 210–230 | 11% | 0.75 | 0.011 / 0.025 | 1.8 |
| PH + whitening, window 100 | 506 | 205–230 | 14% | 0.76 | 0.011 / 0.025 | 2.0 |
| PH, window 25 | 521 | 197–229 | 23% | 0.73 | 0.007 / 0.011 | 5.4 |
| PH + whitening, window 25 | 561 | 200–230 | 23% | 0.72 | 0.011 / 0.004 | 6.1 |

| FX rates, δ = 0.05 | false alarms per model per year | share of false | days on a degraded model per year |
|---|---|---|---|
| PH, window of 20 days | 0 | 0 | 26.1 |
| MeanShift(3) | 0.011 | 0.22 | 28.4 |
| e-CUSUM, window of 20 days | 0 | 0 | **21.2** |
| e-CUSUM, every step | 0.002 | 0.06 | **21.3** |

- **e-CUSUM is the only one of the three that really speeds things up.** At the same false-alarm
  budget the sequential e-CUSUM catches drift 26% faster than PH and MeanShift(3), and twice as fast
  on an abrupt 1σ shift (about 100 steps against 210–295). This is close to a rough theoretical lower
  bound for this scenario (about 75 steps); the earlier detectors were 2.5–4 times above it. The
  windowed e-CUSUM already gives most of the gain (427 steps): *how* the detector accumulates
  evidence matters more than how often a decision is taken.
- **On FX rates e-CUSUM cuts the time spent on a degraded model** from 26 to 21 days per model per
  year, with no false alarms in the windowed mode.
- **Whitening PH did not help** (506 against 506 steps, even more misses). For a shift in the mean a
  calibrated PH is already nearly efficient: partial sums of an AR series carry the same information
  as sums of its innovations. Whitening is useful as part of e-CUSUM, where it yields proper
  e-values, not as a separate wrapper.
- **Shorter windows are worse:** more misses (23% against 11%) and no shorter delay. The gain from
  more frequent decisions is eaten by the stricter level per test (α/4), and a step costs three
  times more.
- **The sequential mode must be bounded by the horizon.** The first version accumulated the CUSUM
  forever since the retrain and exceeded the budget 1.5–3 times: a small error in the estimated
  reference mean acts like a weak permanent shift, and an unbounded sum finds it. The stream now
  keeps one CUSUM per start of each of the last h windows and scores the oldest — exactly the
  statistic the threshold is calibrated on. The price is h updates per step: 7.5 µs per model
  instead of 2.
- **Batched window statistics** (one vectorised call per group of equal detectors at a window end)
  make the windowed step 16–22% cheaper: in a direct comparison on one machine, 1.97 against
  2.34 µs per model with 100 models and 2.13 against 2.72 with 1000.

Tables: `results/exp23_tables.md`. The FX part needs the data:
`python experiments/exp23_speed.py --fx DIRECTORY_WITH_CSV`; without the flag it is taken from the
last run.

### Experiment 24. Monitoring without labels through CBPE

When labels arrive late, the model's true error is unknown. NannyML's CBPE estimates it from the
predicted probabilities (`driftfdr.integrations.cbpe_estimated_error`). This checks whether that
estimate can be monitored instead of the true error. Electricity, 50 logistic models, 2 repeats,
in two variants: natural changes only, and with real p(y|X) drift injected into 20% of the models
(labels flipped with probability 0.3). A step is 100 rows; the reference is 40 steps (with labels,
CBPE is fitted on it); window 10, horizon 4, δ = 5 points, Bonferroni. An alarm is right if the
true error over the next 20 steps exceeds the reference by more than δ.

| signal | correlation with the true error | alarms (MeanShift(1)) | share of false | degradations caught | injected drifts caught |
|---|---|---|---|---|---|
| true error, with labels | 1 | 10–12 | 0 | 13–14% | 18% |
| CBPE estimate, no labels | **−0.21…−0.25** | **0** | — | **0%** | **0%** |

- **On these data CBPE does not replace labels.** The error estimate is unrelated to the true error
  (the correlation is even negative) and systematically too low: about 0.10–0.16 against a true
  0.32–0.53 on the models checked. For a model with injected drift the true error rose from 0.21 to
  0.42 while the CBPE estimate fell. CBPE relies on calibrated probabilities and an unchanged
  p(y|X); on the non-stationary Electricity both are violated, and monitoring the estimate stays
  silent — no false alarms, but no detections either.
- **Practical conclusion:** CBPE is a signal for the case where only the input distribution changes
  and the model's probabilities are calibrated. Check it on your own data: compare the CBPE estimate
  with the true error on a period for which labels have arrived. Real p(y|X) drift is invisible
  without labels (exp. 11).
- **The data are hard even with labels:** the error of a 100-row step varies with an sd of about
  0.19 and an autocorrelation of 0.6, so only a seventh of the degradations are caught, with no
  false alarms.
- **e-CUSUM raised no alarm with a 40-step reference.** Its calibration is right, but from 40 points
  it has to estimate the mean and an AR model, and the bootstrap turns that uncertainty into a wide
  null distribution. MeanShift(1) estimates only the mean and is more powerful on a short reference.
  e-CUSUM needs a reference of at least a few hundred points (300 in exp. 23).

Tables: `results/exp24_tables.md`. Running it requires `pip install nannyml river`.

## Limitations

- Most conclusions come from synthetic data; there are five real data sources (four public data
  sets and hourly FX rates), of which only one is labelled (INSECTS, and incompletely); the rest
  are judged by the oracle of future error. In every real fleet the models predict one target on
  the same data, which overstates their correlation compared with a heterogeneous production fleet.
- Models on real data are not actually retrained: "retraining" means collecting a new reference
  for the same model.
- The AR-sieve bootstrap is correctly specified on AR synthetic data, so its accuracy here is
  optimistic.
- ADWIN's tail calibration is about three times anti-conservative (experiment 10).
- ADWIN is implemented on a fixed grid of cuts; shrinking the window is not needed, because after
  an alarm the detector restarts from a new reference anyway.
- The guarantees of online FDR and BH are derived for independent (or PRDS) p-values, whereas here
  the p-values are dependent both in time (overlapping horizons) and across models.
- Decisions are made only at the end of a window. In the streaming monitor each model has its own
  clock, but in `split_common` mode every model must report at every step; irregular events are
  reduced to steps with `bucket_means`.
- With a tolerance δ > 0 the level α holds at the boundary of the null; when the error did not
  rise at all the false-alarm rate is far below α (0.3% instead of 5% on 0/1 errors in a check
  with MeanShift(1), 300-step reference, window 100): conservative by design.
- On rare events (error rate 0.05) and Poisson counts the calibration is slightly
  anti-conservative at small levels: 2.5% instead of 1% at α = 0.01, 5–7% at α = 0.05.
- LORD++ with its default sequence γ spends 21% of α over the first 100 tests, 30% over 1000 and
  52% over a million: too little on short series, and ever smaller levels on long ones.
- On a noisy signal only material degradations are caught: on FX rates a rise of the loss below
  ~15% is indistinguishable from the noise of a window (exp. 22).

## Next steps

Done: calibration and the multiplicity correction (exp. 1–3), clustered drifts and dependence
(4, 5, 13), tail calibration (6, 10), real data and the material-degradation null (7–9, 14, 16),
p(X) vs p(y|X) and cyclic drift (11), types and sizes of drift (12), a benchmark of detectors
(15), comparison with Evidently and NannyML (17), bursts of false alarms vs fleet-wide drift (18),
runtime (19), dependence between models on real data (20), a single benchmark of 100 scenarios
(21), a fleet of volatility models on exchange rates (22), faster at the same budget: whitening,
shorter windows, a sequential e-CUSUM (23), monitoring without labels through CBPE (24).

Closed with conclusions:

- **Which error to control** (exp. 4, 13, 18). Bonferroni within a window holds the probability of
  at least one false alarm in a window, that is, the rate of false alarms over time, under any
  correlation between models. BH within a window holds the share of false alarms within a window,
  but over the whole run it grows to 0.17 with correlated models; with `split_common` the bursts
  disappear. e-BH and online FDR lose on delay. A formal guarantee for BH with dependent p-values
  has not been proven.
- **ADWIN's tail calibration** (exp. 10). A GPD tail and 2000 replicates do not help: the
  statistic is a maximum over many cuts, and the error stays three times above nominal. For strict
  control use PH, KS or MeanShift; `StreamingMonitor` warns when ADWIN is chosen.

Open items are in [the research plan](#research-plan).

## The original research plan and status

| Item of the proposal | Done | Remaining |
|---|---|---|
| 4 basic detectors | PH, DDM, ADWIN, windowed and sliding KS; plus MeanShift; PH and DDM match river, `from_river` | — (shrinking ADWIN's window is not needed: after an alarm the detector restarts anyway) |
| Calibration by block resampling to a single FAR, signal → p-value, uniformity check | block, stationary, AR-sieve bootstrap, parameter uncertainty (`sieve_pu`), GPD tail (exp. 1, 6, 10) | ADWIN's tail — closed with a conclusion (exp. 10) |
| The null hypothesis on real data | regime null between change points; material-degradation null with tolerance δ, persistence (exp. 7–9, 14, 16) | — |
| Synthetic test bed: abrupt, gradual, cyclic drift; p(X) and p(y\|X) separately; 1–500 streams | all of it, in experiments 1–5, 11–13, 18; the fixed suite of 100 scenarios `benchmark_suite` (exp. 21) | — |
| Metrics MTFA, MDR, MTD, FAR, R-measure | MTFA, MDR, MTD, FAR, plus FDR, MTR, cost of delay, event-level precision / recall / F1 as in Cerqueira et al. (`summarize`) | — (R-measure is not defined in the review's sources; F1 is used instead) |
| Online FDR: alpha-investing, LORD, SAFFRON and relatives | plus LOND, BatchBH, BH, Storey's BH, e-BH, Bonferroni within a window (exp. 2–4, 12, 13); a sequential e-CUSUM checked at every step (exp. 23) | a formal comparison with the error over patience (EOP, Dandapanthula–Ramdas) — for the paper |
| Dependence between streams | the ceiling of the gain (exp. 5), Bonferroni under any correlation (exp. 13), residuals and the fleet test (exp. 18), correlation on real data (exp. 20) | — (a joint bootstrap is not needed with `split_common`, exp. 20) |
| Retraining policy, Pareto frontier by number of streams and type of drift | exp. 2–4, 12; tolerance from the cost of a retrain | — |
| Real data: Electricity, Airlines, Covertype, INSECTS | all four (exp. 7, 14, 16); plus a fleet of volatility models on five currency pairs for 2010–2026 (exp. 22) | — |
| Comparison with existing tools | Evidently and NannyML (exp. 17), runtime (exp. 19) | — |
| Open repository on top of river, real-time demonstration | package, streaming monitor with persistent state, console example, replayable demo (`examples/live_demo.py`, `results/demo.html`) | — |
| Paper, validation with a practitioner | draft of related work ([related_work.md](related_work.md)) | text of the paper; production logs with a partner |

## Research plan

1. **Related work for the paper:** draft in [related_work.md](related_work.md); what remains is to
   check the works outside the review against the originals and to compare the per-window error
   with EOP (Dandapanthula–Ramdas) formally.
2. **Production logs** — a partner is needed.

## Running the experiments

```bash
pip install -e ".[dev,datasets]"
python experiments/exp1_calibration.py     # ~15 min on 4 cores; --quick for a trial run
python experiments/exp2_scaling.py         # ~7 min
python experiments/exp3_tradeoff.py        # ~3 min
python experiments/exp4_clustered.py       # ~9 min
python experiments/exp5_dependence.py      # ~6 min
python experiments/exp6_tail.py            # ~20 min
python experiments/exp7_real.py --method sieve_pu
python experiments/exp8_material.py
python experiments/exp9_persistence.py
python experiments/exp10_tail_shape.py     # ~40 min
python experiments/exp11_px_pyx.py
python experiments/exp12_drift_types.py
python experiments/exp13_ebh.py
python experiments/exp14_real_all.py
python experiments/exp15_benchmark.py
python experiments/exp16_time_buckets.py
python experiments/exp17_tools.py          # needs pip install evidently nannyml
python experiments/exp18_bursts.py         # ~12 min
python experiments/exp19_runtime.py        # ~10 min, one process
python experiments/exp20_real_correlation.py  # ~2 min
python experiments/exp21_benchmark.py      # ~1 h
python experiments/exp22_fx.py DATA_DIR    # ~2 min; MetaTrader 5 hourly CSVs, not in the repository
python experiments/exp23_speed.py --fx DATA_DIR  # ~40 min; without --fx the FX part comes from the last run
python experiments/exp24_cbpe.py           # ~10 min; needs pip install nannyml
```
