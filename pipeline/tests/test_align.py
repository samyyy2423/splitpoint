import json
from pathlib import Path

from splitpoint.align import align_pair, candidates, needleman_wunsch, token
from splitpoint.models import Row, Run, Step, TestResult
from splitpoint.steps import parse_run

FIXTURES = Path(__file__).parent / "fixtures"


def step(i, action, files=(), command="", test=None):
    return Step(index=i, thought="", tool="bash", command=command or f"{action} {' '.join(files)}",
                action=action, files=list(files), output="out", truncated=False,
                test_result=TestResult(passed=test[0], failed=test[1], errors=0) if test else None)


def run(steps, resolved):
    return Run(traj_id="t", model="m", resolved=resolved, issue="i", steps=steps, patch="")


def test_token_uses_file_or_command():
    assert token(step(0, "edit", ["a.py"])) == "edit:a.py"
    assert token(step(0, "run", command="cd /testbed && python   reproduce.py\nmore")) == "run:python reproduce.py"
    assert token(step(0, "submit", command="submit")) == "submit:"


def test_identical_sequences_all_match():
    rows = needleman_wunsch(["a", "b", "c"], ["a", "b", "c"])
    assert rows == [Row(p=i, f=i, match=True) for i in range(3)]


def test_single_insertion_becomes_one_gap():
    rows = needleman_wunsch(["a", "b", "c"], ["a", "x", "b", "c"])
    assert Row(p=None, f=1, match=False) in rows
    assert sum(r.match for r in rows) == 3 and len(rows) == 4


def test_same_file_different_action_aligns_but_does_not_match():
    rows = needleman_wunsch(["view:a.py", "edit:a.py"], ["view:a.py", "view:a.py"])
    assert rows[1] == Row(p=1, f=1, match=False)


def test_foreign_edit_rule():
    passing = run([step(0, "view", ["a.py"]), step(1, "edit", ["a.py"]), step(2, "submit")], True)
    failing = run([step(0, "view", ["a.py"]), step(1, "edit", ["b.py"]), step(2, "edit", ["a.py"]), step(3, "submit")], False)
    cands = candidates(passing, failing, align_rows(passing, failing))
    assert {"step": 1, "rule": "foreign_edit"} in [c.model_dump() for c in cands]


def test_lost_thread_rule():
    passing = run([step(0, "view", ["a.py"]), step(1, "edit", ["a.py"]), step(2, "submit")], True)
    failing = run([step(0, "view", ["a.py"]), step(1, "view", ["c.py"]), step(2, "run", command="python x.py")], False)
    cands = candidates(passing, failing, align_rows(passing, failing))
    assert [c.model_dump() for c in cands] == [{"step": 1, "rule": "lost_thread"}]


def test_lost_thread_ignores_shared_submit_and_scratch_files():
    passing = run([step(0, "view", ["a.py"]), step(1, "edit", ["a.py"]), step(2, "run", ["repro.py"]), step(3, "submit")], True)
    failing = run([step(0, "view", ["a.py"]), step(1, "view", ["c.py"]), step(2, "create", ["repro.py"]),
                   step(3, "run", ["repro.py"]), step(4, "submit")], False)
    rules = {c.rule: c.step for c in candidates(passing, failing, align_rows(passing, failing))}
    assert rules["lost_thread"] == 1


def test_unfixed_test_failure_rule():
    passing = run([step(0, "test", command="pytest", test=(3, 1)), step(1, "submit")], True)
    failing = run([step(0, "test", command="pytest", test=(3, 1)), step(1, "edit", ["a.py"]),
                   step(2, "test", command="pytest", test=(3, 1)), step(3, "submit")], False)
    rules = {c.rule: c.step for c in candidates(passing, failing, align_rows(passing, failing))}
    assert rules["unfixed_test_failure"] == 0


def test_fixed_test_failure_does_not_fire():
    passing = run([step(0, "submit")], True)
    failing = run([step(0, "test", command="pytest", test=(3, 1)), step(1, "test", command="pytest", test=(4, 0))], False)
    rules = [c.rule for c in candidates(passing, failing, align_rows(passing, failing))]
    assert "unfixed_test_failure" not in rules


def test_fallback_when_no_rule_fires():
    passing = run([step(0, "view", ["a.py"]), step(1, "submit")], True)
    failing = run([step(0, "view", ["a.py"]), step(1, "submit")], False)
    assert [c.model_dump() for c in candidates(passing, failing, align_rows(passing, failing))] == [
        {"step": 1, "rule": "fallback"}]


def align_rows(passing, failing):
    return needleman_wunsch([token(s) for s in passing.steps], [token(s) for s in failing.steps])


def test_fixture_pair_aligns():
    raw = {n: json.loads((FIXTURES / f"run_{n}.json").read_text(encoding="utf-8")) for n in ("pass", "fail")}
    runs = {n: parse_run(r["messages"], r["patch"], r["traj_id"], r["model"], r["resolved"]) for n, r in raw.items()}
    alignment = align_pair("pid", runs["pass"], runs["fail"])
    assert {r.p for r in alignment.rows if r.p is not None} == set(range(len(runs["pass"].steps)))
    assert {r.f for r in alignment.rows if r.f is not None} == set(range(len(runs["fail"].steps)))
    assert 1 <= len(alignment.candidates) <= 3
    assert all(0 <= c.step < len(runs["fail"].steps) for c in alignment.candidates)
