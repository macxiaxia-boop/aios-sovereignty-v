"""test_experiment_engine.py - D003 Experiment Engine (A/B test) integration tests."""
from __future__ import annotations

from aios_kernel.business.experiment_engine import (
    WINNER_CONTROL,
    WINNER_INCONCLUSIVE,
    WINNER_TREATMENT,
    Experiment,
    ExperimentEngine,
)


def test_create_experiment():
    """create() returns an Experiment in 'draft' state with required fields populated."""
    eng = ExperimentEngine(seed=1)
    exp = eng.create(
        name="homepage_cta_test",
        hypothesis="New CTA copy will lift signup rate",
        metric="signup_rate",
    )
    assert isinstance(exp, Experiment)
    assert exp.name == "homepage_cta_test"
    assert exp.hypothesis == "New CTA copy will lift signup rate"
    assert exp.metric == "signup_rate"
    assert exp.status == "draft"
    assert exp.winner == ""           # not concluded
    assert exp.sample_size == 0
    assert exp.control_value == 0.0
    assert exp.treatment_value == 0.0
    # Should be in eng.all() and retrievable
    assert exp.id in [e.id for e in eng.all()]
    fetched = eng.get(exp.id)
    assert fetched.id == exp.id


def test_run_basic():
    """run() sets control/treatment values, sample size, status='running'."""
    eng = ExperimentEngine(seed=2)
    exp = eng.create("R1", "H", "ctr")
    result = eng.run(
        exp.id,
        control_size=200,
        treatment_size=200,
        true_control_rate=0.10,
        true_treatment_rate=0.10,  # null effect
    )
    assert result.status == "running"
    assert result.control_size == 200
    assert result.treatment_size == 200
    assert result.sample_size == 400
    # Means are bounded in [0, 1] (Bernoulli draws)
    assert 0.0 <= result.control_value <= 1.0
    assert 0.0 <= result.treatment_value <= 1.0


def test_winner_detection():
    """Large sample + real effect -> winner detection >= 80% over 100 experiments."""
    n_experiments = 100
    n_correct = 0
    n_treatment_wins = 0
    n_control_wins = 0
    n_inconclusive = 0

    for i in range(n_experiments):
        eng = ExperimentEngine(seed=1000 + i)
        # Strong, realistic lift (5% -> 10%) with 1000 per arm
        x = eng.create(f"detection_{i}", "h", "click_rate")
        eng.run(
            x.id,
            control_size=1000,
            treatment_size=1000,
            true_control_rate=0.05,
            true_treatment_rate=0.10,
        )
        eng.conclude(x.id)
        # We expect 'treatment' or 'inconclusive' (false negative is OK on small minority).
        # We do NOT expect 'control'.
        if x.winner == WINNER_TREATMENT:
            n_treatment_wins += 1
            n_correct += 1
        elif x.winner == WINNER_CONTROL:
            n_control_wins += 1
            # false positive — wrong direction
        elif x.winner == WINNER_INCONCLUSIVE:
            n_inconclusive += 1
            # inconclusive on its own is not a "correct" call, but it is not wrong direction.

    # Acceptance: at least 80% of trials detect treatment as winner.
    accuracy = n_correct / n_experiments
    assert accuracy >= 0.80, (
        f"winner detection accuracy {accuracy:.2f} ({n_correct}/{n_experiments}) "
        f"treatment={n_treatment_wins} control={n_control_wins} inconc={n_inconclusive}"
    )
    # We must never declare the *control* variant the winner when treatment is truly better.
    assert n_control_wins == 0, (
        f"never declare control winner when treatment is truly better; got {n_control_wins}"
    )


def test_inconclusive_low_sample():
    """When n < 30 per arm (total < 60), conclude() returns inconclusive with p_value=1.0."""
    eng = ExperimentEngine(seed=7)
    exp = eng.create("LowN", "h", "m")
    eng.run(
        exp.id,
        control_size=10,
        treatment_size=10,
        true_control_rate=0.5,
        true_treatment_rate=0.9,  # huge real effect — but sample is too small
    )
    eng.conclude(exp.id)
    assert exp.status == "concluded"
    assert exp.winner == WINNER_INCONCLUSIVE
    assert exp.p_value == 1.0  # short-circuit per MIN_SAMPLE_SIZE rule


def test_audit_and_persistence():
    """Audit: conclude() records p_value, winner, sample_size, control/treatment values."""
    eng = ExperimentEngine(seed=99)
    exp = eng.create("AuditTest", "H: new copy lifts CTR", "ctr")
    eng.run(
        exp.id,
        control_size=200,
        treatment_size=200,
        true_control_rate=0.08,
        true_treatment_rate=0.08,
    )
    eng.conclude(exp.id)

    # All required fields must be persisted on the experiment envelope.
    assert exp.status == "concluded"
    assert exp.winner in {WINNER_CONTROL, WINNER_TREATMENT, WINNER_INCONCLUSIVE}
    assert 0.0 <= exp.p_value <= 1.0
    assert exp.sample_size == 400
    assert exp.control_size == 200
    assert exp.treatment_size == 200
    assert exp.true_control_rate == 0.08
    assert exp.true_treatment_rate == 0.08
    # Updated timestamp is refreshed on conclude()
    assert exp.updated_at >= exp.created_at

    # conclude() on a 'concluded' experiment must raise — audit guard.
    try:
        eng.conclude(exp.id)
    except ValueError as e:
        assert "not in 'running'" in str(e)
    else:
        raise AssertionError("expected ValueError on re-conclude")


def test_100_experiments_robustness():
    """Run 100 experiments back-to-back to confirm no state leakage / crashes."""
    eng = ExperimentEngine(seed=2024)
    n = 100
    for i in range(n):
        x = eng.create(f"exp_{i}", "h", "m")
        eng.run(
            x.id,
            control_size=100,
            treatment_size=100,
            true_control_rate=0.10,
            true_treatment_rate=0.10,
        )
        eng.conclude(x.id)
        assert x.status == "concluded"
        assert x.winner in {WINNER_CONTROL, WINNER_TREATMENT, WINNER_INCONCLUSIVE}
        assert 0.0 <= x.p_value <= 1.0
        assert x.sample_size == 200

    assert len(eng.all()) == n
