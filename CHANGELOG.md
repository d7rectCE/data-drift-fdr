# Changelog

## 0.1.1

- `Scenario.from_arrays(values, errors=None, change_points=None, truth=None, tolerance=0, names=None)`:
  build a scenario from your own data without the internal conventions (`NO_CHANGE`, events,
  `dataclasses.replace`); change points can be steps, `(start, end)` pairs or lists of them.
- `Rule` enum for the decision rules (`Rule.BONFERRONI`, `Rule.BH_WINDOW`, …); `make_procedure`
  ignores case, `-` and `_`, and an unknown name raises a `ValueError` that suggests the closest
  name and lists the valid ones.
- Documented limitations: the tolerance test is conservative by design when the error does not rise
  (0.3% instead of 5% on 0/1 errors; α holds at the boundary of the null); slight
  anti-conservativeness on rare events and counts at small levels (2.5% at α = 0.01); LORD++ with
  its default sequence spends 21% of α over the first 100 tests.

## 0.1.0 — first release

- **Detectors as calibrated scores:** Page-Hinkley and DDM matching river exactly, ADWIN,
  windowed and sliding KS, MeanShift (with persistence), the sequential e-CUSUM e-detector, and
  AR prewhitening for any value detector; `from_river` builds them from configured river detectors.
- **Calibration:** moving-block, stationary, AR-sieve and AR-sieve with parameter uncertainty
  bootstraps; exponential or GPD tail extrapolation; the material-degradation null with a tolerance
  δ, which `tolerance_from_cost` derives from the cost of a retrain.
- **Decision rules:** uncorrected, Bonferroni, BH, Storey's BH and e-BH within a window; BatchBH,
  LOND, LORD++, SAFFRON, alpha-investing.
- **Streaming monitor:** `StreamingMonitor` with model ids, irregular reporting, adding and
  removing models, saving and restoring its state, the fleet's common component (`split_common`,
  `fleet_alarm`) and a sequential mode that checks every model at every step.
- **Integrations:** Prometheus exporter, MLflow reporter, NannyML CBPE signal; an example service
  with alert rules.
- **Evaluation:** synthetic scenarios, the fixed 100-scenario `benchmark_suite`, fleets of models
  on INSECTS, Electricity, Airlines, Covertype and hourly FX rates; FDR, delay, MTR and event-level
  precision / recall / F1 metrics; 24 experiments documented in `docs/experiments.md`.
