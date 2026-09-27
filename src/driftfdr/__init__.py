"""Calibrated p-values and multiplicity control on top of practical drift detectors, for fleets of ML models."""

from importlib.metadata import PackageNotFoundError, version

from .calibration import CalibrationConfig, NullDistribution, calibrate, calibrate_many
from .detectors import (
    ADWIN,
    DDM,
    ECUSUM,
    Detector,
    KSSliding,
    KSWindow,
    MeanShift,
    PageHinkley,
    Prewhitened,
    ar_whiten,
    default_detectors,
)
from .metrics import summarize
from .monitor import MonitorConfig, MonitorResult, run_monitor
from .online_fdr import (
    LOND,
    SAFFRON,
    AlphaInvesting,
    BatchBH,
    BHWindow,
    BonferroniWindow,
    EBHWindow,
    LORDpp,
    RawThreshold,
    Rule,
    StoreyBHWindow,
    Uncorrected,
    make_procedure,
)
from .preprocess import bucket_means, split_common, tolerance_from_cost
from .streaming import CalibratedDetector, StreamingMonitor, from_river
from .streams import Scenario, ScenarioConfig, SupervisedConfig, benchmark_suite, make_scenario, make_supervised_scenario

__all__ = [
    "ADWIN",
    "DDM",
    "ECUSUM",
    "LOND",
    "SAFFRON",
    "AlphaInvesting",
    "BHWindow",
    "BatchBH",
    "CalibratedDetector",
    "BonferroniWindow",
    "CalibrationConfig",
    "EBHWindow",
    "Detector",
    "KSSliding",
    "KSWindow",
    "LORDpp",
    "MeanShift",
    "MonitorConfig",
    "MonitorResult",
    "NullDistribution",
    "PageHinkley",
    "Prewhitened",
    "RawThreshold",
    "Rule",
    "Scenario",
    "ScenarioConfig",
    "StoreyBHWindow",
    "StreamingMonitor",
    "SupervisedConfig",
    "Uncorrected",
    "calibrate",
    "calibrate_many",
    "default_detectors",
    "from_river",
    "make_procedure",
    "make_scenario",
    "make_supervised_scenario",
    "run_monitor",
    "summarize",
    "ar_whiten",
    "benchmark_suite",
    "bucket_means",
    "tolerance_from_cost",
    "split_common",
]

try:
    __version__ = version("driftfdr")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0"
