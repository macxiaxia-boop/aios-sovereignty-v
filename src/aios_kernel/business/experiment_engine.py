"""experiment_engine.py - D003 Experiment Engine (A/B test)."""
from __future__ import annotations

import math
import random
import uuid

from pydantic import Field

from aios_kernel.domain.envelope import Envelope

# Constants for z-test (two-proportion z-test).
Z_ALPHA = 1.96       # two-tailed 95% confidence
MIN_SAMPLE_SIZE = 30  # below this -> inconclusive per spec

WINNER_CONTROL = "control"
WINNER_TREATMENT = "treatment"
WINNER_INCONCLUSIVE = "inconclusive"


def _normal_cdf(x: float) -> float:
    """Standard normal CDF using math.erf (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class Experiment(Envelope):
    """A/B test experiment (control vs treatment).

    Captures design (hypothesis, metric) and result fields (winner, p_value,
    sample_size). control_value / treatment_value are the realized metric
    means after run() finishes sampling.
    """

    name: str = Field(..., min_length=1, max_length=200)
    hypothesis: str = Field(..., min_length=1, max_length=2000)
    metric: str = Field(..., min_length=1, max_length=200)

    # Filled in by run()
    control_value: float = Field(default=0.0, description="Control group mean (e.g. conversion rate).")
    treatment_value: float = Field(default=0.0, description="Treatment group mean.")
    sample_size: int = Field(default=0, ge=0, description="Total sample size (control + treatment).")

    # Filled in by conclude()
    winner: str = Field(default="", description="control | treatment | inconclusive | (empty=not concluded).")
    p_value: float = Field(default=1.0, ge=0.0, le=1.0, description="Two-tailed p-value.")

    status: str = Field(
        default="draft",
        description="draft | running | concluded",
    )

    # Internal seeds for deterministic re-simulation; not part of public schema output but kept as fields.
    control_size: int = Field(default=0, ge=0)
    treatment_size: int = Field(default=0, ge=0)
    true_treatment_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Simulated true rate for the treatment group (None = equal to control).",
    )
    true_control_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Simulated true rate for the control group (None = 0.10 default).",
    )


class ExperimentEngine:
    """A/B testing engine: create -> run -> conclude.

    Uses a deterministic two-proportion z-test for p_value; sample sizes
below MIN_SAMPLE_SIZE are flagged inconclusive to avoid misleading
detections on tiny samples.
    """

    def __init__(self, seed: int = 42):
        self._experiments: dict[str, Experiment] = {}
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------ create

    def create(self, name: str, hypothesis: str, metric: str) -> Experiment:
        """Create a new experiment in 'draft' state."""
        exp = Experiment(
            id=str(uuid.uuid4()),
            name=name,
            hypothesis=hypothesis,
            metric=metric,
        )
        self._experiments[exp.id] = exp
        return exp

    def get(self, exp_id: str) -> Experiment:
        """Fetch an experiment by id; raises KeyError if missing."""
        if exp_id not in self._experiments:
            raise KeyError(f"Experiment {exp_id!r} not found")
        return self._experiments[exp_id]

    def all(self) -> list[Experiment]:
        return list(self._experiments.values())

    # ------------------------------------------------------------------- run

    def run(
        self,
        exp_id: str,
        control_size: int,
        treatment_size: int,
        true_control_rate: float = 0.10,
        true_treatment_rate: float | None = None,
    ) -> Experiment:
        """Simulate the experiment: sample binary outcomes for both arms.

        For real production use, callers would feed observed data instead of
        simulated samples. Here we use a Bernoulli draw so the engine is
        self-contained and testable without external data sources.
        """
        if control_size < 0 or treatment_size < 0:
            raise ValueError("sample sizes must be non-negative")
        exp = self.get(exp_id)

        if true_treatment_rate is None:
            true_treatment_rate = true_control_rate  # null effect by default

        # Simulate Bernoulli draws and compute means.
        control_conversions = sum(
            1 for _ in range(control_size) if self._rng.random() < true_control_rate
        )
        treatment_conversions = sum(
            1 for _ in range(treatment_size) if self._rng.random() < true_treatment_rate
        )

        exp.control_size = control_size
        exp.treatment_size = treatment_size
        exp.true_control_rate = true_control_rate
        exp.true_treatment_rate = true_treatment_rate
        exp.control_value = (control_conversions / control_size) if control_size else 0.0
        exp.treatment_value = (treatment_conversions / treatment_size) if treatment_size else 0.0
        exp.sample_size = control_size + treatment_size
        exp.status = "running"
        exp.touch()
        return exp

    # ---------------------------------------------------------------- conclude

    def conclude(self, exp_id: str) -> Experiment:
        """Compute winner + p_value via two-proportion z-test.

        Winner rules:
          - sample_size < 2 * MIN_SAMPLE_SIZE  -> inconclusive
          - p_value < 0.05 AND treatment > control -> "treatment"
          - p_value < 0.05 AND control > treatment -> "control"
          - otherwise -> inconclusive
        """
        exp = self.get(exp_id)
        if exp.status != "running":
            raise ValueError(f"experiment {exp_id} is not in 'running' state (current: {exp.status})")

        # Pooled proportion z-test for two independent proportions.
        n_c = exp.control_size
        n_t = exp.treatment_size
        p_c = exp.control_value
        p_t = exp.treatment_value
        n_total = n_c + n_t

        if n_total < 2 * MIN_SAMPLE_SIZE:
            exp.p_value = 1.0
            exp.winner = WINNER_INCONCLUSIVE
            exp.status = "concluded"
            exp.touch()
            return exp

        pooled = ((p_c * n_c) + (p_t * n_t)) / n_total
        se_squared = pooled * (1.0 - pooled) * ((1.0 / n_c) + (1.0 / n_t))
        if se_squared <= 0.0:
            # both arms are constant -> no detectable effect
            exp.p_value = 1.0
            exp.winner = WINNER_INCONCLUSIVE
            exp.status = "concluded"
            exp.touch()
            return exp

        z = (p_t - p_c) / math.sqrt(se_squared)
        # Two-tailed p = 2 * (1 - Phi(|z|))
        p_val = 2.0 * (1.0 - _normal_cdf(abs(z)))
        p_val = max(0.0, min(1.0, p_val))
        exp.p_value = p_val

        if p_val < 0.05:
            exp.winner = WINNER_TREATMENT if p_t > p_c else WINNER_CONTROL
        else:
            exp.winner = WINNER_INCONCLUSIVE

        exp.status = "concluded"
        exp.touch()
        return exp


__all__ = [
    "Experiment",
    "ExperimentEngine",
    "WINNER_CONTROL",
    "WINNER_TREATMENT",
    "WINNER_INCONCLUSIVE",
    "MIN_SAMPLE_SIZE",
]
