import pytest

from splitpoint.models import Alignment, Candidate, Verdict
from splitpoint.validate import cohen_kappa, score


def test_kappa_hand_computed():
    # 2x2 table: agree a/a 20, b/b 15, disagree 5 + 10 -> po = 0.7, pe = 0.5*0.6 + 0.5*0.4 = 0.5
    a = ["a"] * 20 + ["a"] * 5 + ["b"] * 10 + ["b"] * 15
    b = ["a"] * 20 + ["b"] * 5 + ["a"] * 10 + ["b"] * 15
    assert cohen_kappa(a, b) == pytest.approx(0.4)


def test_kappa_perfect_and_degenerate():
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert cohen_kappa(["a", "a"], ["a", "a"]) == 1.0
    assert cohen_kappa([], []) is None


def verdict(step, category):
    return Verdict(split_step=step, reason="r", category=category, confidence=0.5)


def alignment(step):
    return Alignment(pair_id="x", rows=[], candidates=[Candidate(step=step, rule="lost_thread")])


def test_score_counts_exact_and_within_two():
    labels = [
        {"pair_id": "p1", "split_step": 5, "category": "wrong_location"},
        {"pair_id": "p2", "split_step": 5, "category": "incomplete_fix"},
        {"pair_id": "p3", "split_step": 5, "category": "never_verified"},
        {"pair_id": "p4", "split_step": 5, "category": "other"},  # no verdict -> skipped
    ]
    verdicts = {"p1": verdict(5, "wrong_location"), "p2": verdict(7, "incomplete_fix"), "p3": verdict(9, "other")}
    alignments = {"p1": alignment(5), "p2": alignment(1), "p3": alignment(6), "p4": alignment(5)}
    v = score(labels, verdicts, alignments)
    assert v.n == 3
    assert v.split_exact == pytest.approx(1 / 3)
    assert v.split_within_2 == pytest.approx(2 / 3)
    assert v.category_agreement == pytest.approx(2 / 3)
    assert v.baseline_split_exact == pytest.approx(1 / 3)
    assert v.baseline_split_within_2 == pytest.approx(2 / 3)


def test_score_with_no_overlap():
    v = score([{"pair_id": "p9", "split_step": 1, "category": "other"}], {}, {})
    assert v.n == 0 and v.split_exact is None and v.category_kappa is None
