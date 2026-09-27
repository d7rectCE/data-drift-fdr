"""Decision rules applied to the p-values of one monitoring window.

Every window produces a batch of p-values, one per actively monitored stream.
Per-window rules (``Uncorrected``, ``BonferroniWindow``, ``BHWindow``,
``StoreyBHWindow``) decide on each batch on its own. ``BatchBH`` runs BH inside
each batch at levels chosen to control FDR over all batches. Online rules
(``LOND``, ``LORDpp``, ``SAFFRON``, ``AlphaInvesting``) see hypotheses one at a
time; within a batch they are fed in a random order that does not depend on
the p-values.

References: Foster & Stine (2008), Storey, Taylor & Siegmund (2004),
Javanmard & Montanari (2018), Ramdas et al. (2017, LORD++), Ramdas et al.
(2018, SAFFRON), Zrnic, Jiang, Ramdas & Jordan (2020, BatchBH).
"""

from __future__ import annotations

import difflib
from abc import ABC, abstractmethod
from enum import Enum

import numpy as np

_LORD_CONST = 0.07720838
_SAFFRON_CONST = 0.4374901658


def gamma_lord(j: np.ndarray) -> np.ndarray:
    """Javanmard–Montanari sequence, sums to one over j >= 1."""
    j = np.asarray(j, dtype=float)
    return _LORD_CONST * np.log(np.maximum(j, 2)) / (j * np.exp(np.sqrt(np.log(j))))


def gamma_saffron(j: np.ndarray) -> np.ndarray:
    """``gamma_j ∝ j^-1.6``, sums to one over j >= 1."""
    return _SAFFRON_CONST / np.asarray(j, dtype=float) ** 1.6


class Procedure(ABC):
    """Base class of decision rules: given the p-values of one window, which models alarm."""

    name = "procedure"
    uses_statistics = False
    """If true, ``decide`` receives raw detector statistics instead of p-values."""

    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    @abstractmethod
    def decide(self, values: np.ndarray, rng) -> np.ndarray:
        """Boolean rejections for one window."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(alpha={self.alpha})"


class RawThreshold(Procedure):
    """Uncalibrated detector: alarm when the statistic crosses the default threshold."""

    name = "raw"
    uses_statistics = True

    def __init__(self, threshold: float):
        super().__init__(alpha=np.nan)
        self.threshold = threshold

    def decide(self, values, rng):
        return np.asarray(values) > self.threshold


class Uncorrected(Procedure):
    """Each stream tested at level alpha, as in current practice."""

    name = "uncorrected"

    def decide(self, values, rng):
        return np.asarray(values) <= self.alpha


class BonferroniWindow(Procedure):
    """Bonferroni within each window: controls P(any false alarm in a window)."""

    name = "bonferroni"

    def decide(self, values, rng):
        values = np.asarray(values)
        return values <= self.alpha / max(values.size, 1)


class BHWindow(Procedure):
    """Benjamini–Hochberg within each window."""

    name = "bh_window"

    def decide(self, values, rng):
        return benjamini_hochberg(values, self.alpha)


class StoreyBHWindow(Procedure):
    """Adaptive BH within each window: BH at ``alpha / pi0_hat``.

    ``pi0_hat = (1 + #{p > lam}) / (m (1 - lam))`` is the finite-sample Storey
    estimate of the fraction of nulls; when many streams drift at once it drops
    and the threshold rises.
    """

    name = "storey_bh"

    def __init__(self, alpha: float = 0.05, lam: float = 0.5):
        super().__init__(alpha)
        self.lam = lam

    def decide(self, values, rng):
        p = np.asarray(values, dtype=float)
        if p.size == 0:
            return np.zeros(0, dtype=bool)
        # not capped at one: the Storey–Taylor–Siegmund guarantee is for the uncapped estimate
        pi0 = (1 + np.sum(p > self.lam)) / (p.size * (1 - self.lam))
        return benjamini_hochberg(p, self.alpha / pi0) & (p <= self.lam)


class EBHWindow(Procedure):
    """e-BH within each window (Wang & Ramdas, 2022): FDR control under any dependence.

    p-values are turned into e-values by the calibrator ``e = kappa * p^(kappa - 1)``,
    which integrates to one over a uniform p, and the ``k`` largest e-values are
    rejected with ``k = max{k : e_(k) >= m / (alpha k)}``. Unlike BH it needs no
    assumption on how the streams depend on each other, at a price in power.
    """

    name = "e_bh"

    def __init__(self, alpha: float = 0.05, kappa: float = 0.5):
        super().__init__(alpha)
        self.kappa = kappa

    def decide(self, values, rng):
        p = np.clip(np.asarray(values, dtype=float), 1e-300, 1.0)
        m = p.size
        if m == 0:
            return np.zeros(0, dtype=bool)
        e = self.kappa * p ** (self.kappa - 1.0)
        order = np.argsort(-e)
        ok = np.flatnonzero(e[order] >= m / (self.alpha * np.arange(1, m + 1)))
        rejected = np.zeros(m, dtype=bool)
        if ok.size:
            rejected[order[: ok[-1] + 1]] = True
        return rejected


class BatchBH(Procedure):
    """BH inside each window at levels that control FDR across all windows.

    With ``R_s`` rejections and ``R_s^+`` the rejections BH would make in batch
    ``s`` if one of its p-values were set to zero, the level of batch ``t`` is

        (alpha * sum_{s<=t} gamma_s - sum_{s<t} alpha_s R_s^+ / (R_s^+ + sum_{r<s} R_r))
        * (n_t + sum_{r<t} R_r) / n_t,

    which keeps ``sum_s alpha_s R_s^+ / (R_s^+ + sum_{r<s} R_r) <= alpha``, the
    bound on FDR for independent p-values. Past rejections both refund budget
    and scale the level up.
    """

    name = "BatchBH"

    def __init__(self, alpha: float = 0.05):
        super().__init__(alpha)
        self.t = 0
        self.charged = 0.0
        self.n_rejections = 0
        self.levels: list[float] = []

    def decide(self, values, rng):
        p = np.asarray(values, dtype=float)
        n = p.size
        if n == 0:
            return np.zeros(0, dtype=bool)
        self.t += 1
        budget = self.alpha * gamma_saffron(np.arange(1, self.t + 1)).sum()
        level = min(1.0, max(0.0, budget - self.charged) * (n + self.n_rejections) / n)
        self.levels.append(level)
        rejected = benjamini_hochberg(p, level)
        r_plus = bh_count(np.concatenate([[0.0], np.sort(p)[:-1]]), level)
        self.charged += level * r_plus / (r_plus + self.n_rejections)
        self.n_rejections += int(rejected.sum())
        return rejected


def bh_count(p: np.ndarray, alpha: float) -> int:
    """Number of BH rejections at level ``alpha``."""
    m = p.size
    below = np.flatnonzero(np.sort(p) <= alpha * np.arange(1, m + 1) / m)
    return int(below[-1] + 1) if below.size else 0


def benjamini_hochberg(p: np.ndarray, alpha: float) -> np.ndarray:
    """Boolean rejections of the Benjamini–Hochberg step-up procedure at level ``alpha``."""
    p = np.asarray(p, dtype=float)
    k = bh_count(p, alpha)
    if k == 0:
        return np.zeros(p.size, dtype=bool)
    return p <= np.sort(p)[k - 1]


class OnlineProcedure(Procedure):
    """Sequential rule: hypotheses ``t = 1, 2, ...`` each get a level ``alpha_t``."""

    def __init__(self, alpha: float = 0.05):
        super().__init__(alpha)
        self.t = 0
        self.levels: list[float] = []

    def decide(self, values, rng):
        values = np.asarray(values, dtype=float)
        rejected = np.zeros(values.size, dtype=bool)
        for i in rng.permutation(values.size):
            rejected[i] = self.test(values[i])
        return rejected

    def test(self, p: float) -> bool:
        """Test the next hypothesis: compute its level, decide, update the state."""
        self.t += 1
        level = self.next_level()
        self.levels.append(level)
        rejected = bool(p <= level)
        self.update(p, rejected)
        return rejected

    @abstractmethod
    def next_level(self) -> float:
        """Level ``alpha_t`` of the hypothesis about to be tested."""

    @abstractmethod
    def update(self, p: float, rejected: bool) -> None:
        """Record the outcome of the hypothesis just tested."""


class LOND(OnlineProcedure):
    """``alpha_t = alpha * gamma_t * (D_{t-1} + 1)``; FDR control under PRDS."""

    name = "LOND"

    def __init__(self, alpha: float = 0.05):
        super().__init__(alpha)
        self.n_rejections = 0

    def next_level(self):
        return float(self.alpha * gamma_lord(self.t) * (self.n_rejections + 1))

    def update(self, p, rejected):
        self.n_rejections += rejected


class LORDpp(OnlineProcedure):
    """LORD++: wealth is earned back at every rejection."""

    name = "LORD++"

    def __init__(self, alpha: float = 0.05, w0: float | None = None):
        super().__init__(alpha)
        self.w0 = alpha / 2 if w0 is None else w0
        self.rejection_times: list[int] = []

    def next_level(self):
        t = self.t
        level = self.w0 * gamma_lord(t)
        if self.rejection_times:
            taus = np.asarray(self.rejection_times)
            g = gamma_lord(t - taus)
            level += (self.alpha - self.w0) * g[0] + self.alpha * g[1:].sum()
        return float(level)

    def update(self, p, rejected):
        if rejected:
            self.rejection_times.append(self.t)


class SAFFRON(OnlineProcedure):
    """SAFFRON: adapts to the fraction of nulls through candidates ``p <= lambda``."""

    name = "SAFFRON"

    def __init__(self, alpha: float = 0.05, lam: float = 0.5, w0: float | None = None):
        super().__init__(alpha)
        self.lam = lam
        self.w0 = (1 - lam) * alpha / 2 if w0 is None else w0
        self.n_candidates = 0
        self.rejection_times: list[int] = []
        self.candidates_at_rejection: list[int] = []

    def next_level(self):
        t = self.t
        level = self.w0 * gamma_saffron(t - self.n_candidates)
        if self.rejection_times:
            taus = np.asarray(self.rejection_times)
            after = self.n_candidates - np.asarray(self.candidates_at_rejection)
            g = gamma_saffron(t - taus - after)
            level += ((1 - self.lam) * self.alpha - self.w0) * g[0]
            level += (1 - self.lam) * self.alpha * g[1:].sum()
        return float(min(self.lam, level))

    def update(self, p, rejected):
        self.n_candidates += p <= self.lam
        if rejected:
            self.rejection_times.append(self.t)
            self.candidates_at_rejection.append(self.n_candidates)


class AlphaInvesting(OnlineProcedure):
    """Foster–Stine alpha-investing (mFDR control) with the ``W / (1 + t - k*)`` spending rule."""

    name = "alpha-investing"

    def __init__(self, alpha: float = 0.05, w0: float | None = None, payout: float | None = None):
        super().__init__(alpha)
        self.wealth = alpha / 2 if w0 is None else w0
        self.payout = alpha if payout is None else payout
        self.last_rejection = 0

    def next_level(self):
        return float(self.wealth / (1 + self.t - self.last_rejection))

    def update(self, p, rejected):
        level = self.levels[-1]
        if rejected:
            self.wealth += self.payout
            self.last_rejection = self.t
        else:
            self.wealth -= level / (1 - level)


PROCEDURES = {
    cls.name: cls
    for cls in (
        Uncorrected,
        BonferroniWindow,
        BHWindow,
        StoreyBHWindow,
        EBHWindow,
        BatchBH,
        LOND,
        LORDpp,
        SAFFRON,
        AlphaInvesting,
    )
}


class Rule(str, Enum):
    """Names of the decision rules, for autocompletion instead of strings.

    ``StreamingMonitor(procedure=Rule.BH_WINDOW)`` is the same as ``procedure="bh_window"``.
    """

    UNCORRECTED = "uncorrected"
    BONFERRONI = "bonferroni"
    BH_WINDOW = "bh_window"
    STOREY_BH = "storey_bh"
    E_BH = "e_bh"
    BATCH_BH = "BatchBH"
    LOND = "LOND"
    LORD_PP = "LORD++"
    SAFFRON = "SAFFRON"
    ALPHA_INVESTING = "alpha-investing"

    def __str__(self) -> str:
        return self.value


def _normalise(name: str) -> str:
    return str(name).lower().replace("-", "").replace("_", "").replace(" ", "")


def make_procedure(name, alpha: float = 0.05) -> Procedure:
    """A fresh procedure by name: a ``Rule`` or one of the keys of ``PROCEDURES``.

    Names are matched ignoring case, ``-``, ``_`` and spaces (``"lord++"``,
    ``"BH-window"`` work); an unknown name raises ``ValueError`` listing the valid ones.
    """
    key = name.value if isinstance(name, Rule) else str(name)
    if key not in PROCEDURES:
        matches = [k for k in PROCEDURES if _normalise(k) == _normalise(key)]
        if len(matches) != 1:
            close = difflib.get_close_matches(key, list(PROCEDURES), n=1)
            hint = f" Did you mean {close[0]!r}?" if close else ""
            raise ValueError(f"unknown procedure {name!r}.{hint} Valid names: {', '.join(PROCEDURES)}")
        key = matches[0]
    return PROCEDURES[key](alpha)
