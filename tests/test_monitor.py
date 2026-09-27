import numpy as np
import pytest

from driftfdr import (
    CalibrationConfig,
    MonitorConfig,
    PageHinkley,
    RawThreshold,
    Scenario,
    ScenarioConfig,
    Uncorrected,
    make_procedure,
    make_scenario,
    run_monitor,
    summarize,
)

CONFIG = MonitorConfig(n_ref=200, window=100, horizon=3, calibration=CalibrationConfig(n_boot=100))


@pytest.fixture(scope="module")
def scenario():
    return make_scenario(
        ScenarioConfig(n_streams=20, n_steps=2000, phi=0.3, drift_fraction=0.25, magnitude=1.5),
        seed=0,
    )


def test_scenario_ground_truth(scenario):
    drifting = scenario.drifting
    assert drifting.size == 5
    k = drifting[0]
    tau = scenario.change_start[k]
    assert scenario.is_null([k], 0, tau)[0]
    assert not scenario.is_null([k], 0, tau + 1)[0]
    assert scenario.is_null([k], scenario.change_end[k], scenario.n_steps)[0]


def test_retrained_stream_pauses_for_reference(scenario):
    result = run_monitor(scenario, PageHinkley(), Uncorrected(0.2), CONFIG, seed=0)
    tests = result.tests
    for _, alarm in tests[tests["rejected"]].iterrows():
        later = tests[(tests["stream"] == alarm["stream"]) & (tests["t_end"] > alarm["t_end"])]
        if not later.empty:
            assert later["t_end"].min() >= alarm["t_end"] + CONFIG.n_ref + CONFIG.window
            assert later["ref_start"].iloc[0] == alarm["t_end"]


def test_strong_drifts_are_detected(scenario):
    result = run_monitor(scenario, PageHinkley(), make_procedure("LORD++", 0.1), CONFIG, seed=0)
    s = summarize(result)
    assert s["n_drifts"] == 5
    assert s["detected"] >= 4
    assert s["mean_delay"] < 400


def test_cache_is_reused_across_procedures(scenario):
    cache = {}
    run_monitor(scenario, PageHinkley(), make_procedure("bh_window", 0.1), CONFIG, cache=cache)
    n_before = len(cache)
    run_monitor(scenario, PageHinkley(), make_procedure("SAFFRON", 0.1), CONFIG, cache=cache)
    assert n_before >= scenario.n_streams
    assert len(cache) <= n_before + scenario.drifting.size + 5


def test_raw_threshold_needs_no_calibration(scenario):
    result = run_monitor(scenario, PageHinkley(), RawThreshold(50.0), CONFIG)
    assert result.tests["pvalue"].isna().all()
    assert np.isfinite(summarize(result)["fdp"])


def test_lookback_grows_up_to_horizon(scenario):
    tests = run_monitor(scenario, PageHinkley(), None, CONFIG).tests
    first = tests[tests["stream"] == 0]["windows_seen"].to_numpy()
    assert first[:4].tolist() == [1, 2, 3, 3]
    assert not tests["rejected"].any()


def test_summarize_delays_and_misses():
    import pandas as pd

    from driftfdr import MonitorResult

    sc = make_scenario(
        ScenarioConfig(n_streams=4, n_steps=1000, drift_fraction=0.5, fixed_onset=500), seed=1
    )
    d0, d1 = sc.drifting
    null_stream = [k for k in range(4) if k not in (d0, d1)][0]
    tests = pd.DataFrame(
        {
            "window": [0, 1, 2],
            "t_end": [400, 700, 600],
            "stream": [null_stream, d0, d1],
            "rejected": [True, True, False],
            "is_null": [True, False, False],
        }
    )
    s = summarize(MonitorResult(tests, n_windows=7, scenario=sc, config=CONFIG))
    assert s["alarms"] == 2 and s["false_alarms"] == 1 and s["fdp"] == 0.5
    assert s["detected"] == 1 and s["mdr"] == 0.5
    assert s["mean_delay"] == 200
    # the missed drift keeps degrading until the end of the run
    assert s["degraded_per_drift"] == (200 + 500) / 2
    # event level: one of two alarms is a detection, one of two drifts is detected
    assert s["precision"] == 0.5 and s["recall"] == 0.5 and s["f1"] == 0.5
    late = summarize(MonitorResult(tests, n_windows=7, scenario=sc, config=CONFIG), max_delay=100)
    assert late["precision"] == 0 and late["recall"] == 0 and late["f1"] == 0


def test_drift_events_shift_groups_together():
    sc = make_scenario(
        ScenarioConfig(n_streams=50, n_steps=2000, drift_fraction=0.1, drift_events=2, event_fraction=0.2),
        seed=2,
    )
    assert sc.drifting.size == 5 + 2 * 10
    for e in (0, 1):
        members = np.flatnonzero(sc.event == e)
        assert members.size == 10
        assert np.unique(sc.change_start[members]).size == 1


def test_window_fdp_is_reported(scenario):
    s = summarize(run_monitor(scenario, PageHinkley(), Uncorrected(0.2), CONFIG))
    assert 0 <= s["window_fdp"] <= s["p_any_false_alarm_per_window"]


def test_supervised_scenario_separates_virtual_and_real_drift():
    from driftfdr import SupervisedConfig, make_supervised_scenario

    sc = make_supervised_scenario(SupervisedConfig(n_streams=40, kinds=("virtual", "real", "cyclic")), seed=3)
    for kind, loss_up, x_up in (("virtual", False, True), ("real", True, False)):
        k = np.flatnonzero(sc.drift_kind == kind)[0]
        tau = sc.change_start[k]
        assert (sc.values[k, tau:].mean() - sc.values[k, :tau].mean() > 0.08) == loss_up
        assert (sc.features[k, tau:].mean() - sc.features[k, :tau].mean() > 0.5) == x_up
        assert (sc.mean_shift[k, -1] > 0) == loss_up
    k = np.flatnonzero(sc.drift_kind == "cyclic")[0]
    cs, _ = sc.changes()
    assert (cs[k] < 10**9).sum() >= 2


def test_scenario_from_arrays_supports_run_monitor_and_metrics():
    rng = np.random.default_rng(5)
    values = rng.normal(size=(4, 1500))
    values[1, 800:] += 2.0
    values[2, 600:900] += np.linspace(0, 2, 300)
    values[2, 900:] += 2.0
    sc = Scenario.from_arrays(values, change_points=[None, 800, (600, 900), None], names=list("abcd"))
    assert sc.drifting.tolist() == [1, 2] and sc.change_end[2] == 900 and list(sc.drift_kind) == list("abcd")
    res = run_monitor(sc, PageHinkley(), make_procedure("bonferroni", 0.05), CONFIG, seed=0)
    s = summarize(res)
    assert s["n_drifts"] == 2 and s["detected"] == 2

    several = Scenario.from_arrays(values, change_points={1: [300, 800]})
    assert several.changes()[0][1].tolist() == [300, 800]
    with pytest.raises(ValueError):
        Scenario.from_arrays(values, change_points=[5000, None, None, None])
    with_truth = Scenario.from_arrays(values, truth=values, tolerance=0.5)
    assert with_truth.tolerance == 0.5 and with_truth.truth is not None


def test_procedure_names_are_forgiving_and_errors_list_valid_names():
    from driftfdr import Rule

    assert make_procedure("lord++").name == "LORD++"
    assert make_procedure(Rule.BH_WINDOW, 0.1).alpha == 0.1
    assert make_procedure("Alpha_Investing").name == "alpha-investing"
    with pytest.raises(ValueError, match="Did you mean 'bh_window'.*Valid names"):
        make_procedure("bh_windw")
