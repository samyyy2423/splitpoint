from splitpoint.pick import pair_id, pick_validation, repo_of, select_pairs


def row(traj, task, model, resolved):
    return {"traj_id": traj, "instance_id": task, "model": model, "resolved": resolved}


ROWS = [
    # task A: cross-model possible (m1 passes, m2 fails)
    row("a1", "o__ra.1.x", "m1", True), row("a2", "o__ra.1.x", "m2", False), row("a3", "o__ra.1.x", "m1", False),
    # task B: same model only
    row("b1", "o__rb.1.x", "m1", True), row("b2", "o__rb.1.x", "m1", False),
    # task C: all pass, task D: all fail
    row("c1", "o__rc.1.x", "m1", True), row("c2", "o__rc.1.x", "m2", True),
    row("d1", "o__rd.1.x", "m1", False),
    # task E: same model only
    row("e1", "o__re.1.x", "m2", True), row("e2", "o__re.1.x", "m2", False),
]


def test_repo_of():
    assert repo_of("Project-MONAI__MONAI.a09c1f08.pr_4662") == "Project-MONAI/MONAI"


def test_pair_id_is_stable_and_short():
    assert pair_id("x", "y") == pair_id("x", "y")
    assert pair_id("x", "y") != pair_id("y", "x")
    assert len(pair_id("x", "y")) == 10


def test_only_mixed_tasks_and_cross_model_preferred():
    pairs = select_pairs(ROWS, n=10, seed=1)
    tasks = {p.instance_id for p in pairs}
    assert tasks == {"o__ra.1.x", "o__rb.1.x", "o__re.1.x"}
    a = next(p for p in pairs if p.instance_id == "o__ra.1.x")
    assert (a.pass_traj, a.fail_traj, a.cross_model) == ("a1", "a2", True)
    assert a.repo == "o/ra"
    assert not next(p for p in pairs if p.instance_id == "o__rb.1.x").cross_model


def test_cross_model_pairs_come_first_when_capped():
    pairs = select_pairs(ROWS, n=2, seed=1)
    assert len(pairs) == 2
    assert pairs[0].instance_id == "o__ra.1.x"


def test_deterministic_for_a_seed():
    assert select_pairs(ROWS, n=2, seed=7) == select_pairs(ROWS, n=2, seed=7)


def test_pass_and_fail_are_the_right_way_round():
    for p in select_pairs(ROWS, n=10, seed=3):
        by_traj = {r["traj_id"]: r for r in ROWS}
        assert by_traj[p.pass_traj]["resolved"] and not by_traj[p.fail_traj]["resolved"]


def test_validation_sample():
    pairs = select_pairs(ROWS, n=10, seed=1)
    ids = pick_validation(pairs, k=2, seed=1)
    assert len(ids) == 2 and set(ids) <= {p.pair_id for p in pairs}
    assert pick_validation(pairs, k=50, seed=1) == sorted(p.pair_id for p in pairs)
