from types import SimpleNamespace as NS

import pytest

from splitpoint import judge
from splitpoint.categories import CATEGORY_IDS
from splitpoint.models import Alignment, Candidate, PairMeta, Row, Run, Step


def step(i, action, files=(), thought="", output="ok"):
    return Step(index=i, thought=thought, tool="bash", command=f"{action} {' '.join(files)}".strip(),
                action=action, files=list(files), output=output, truncated=False, test_result=None)


META = PairMeta(pair_id="p1", instance_id="o__r.1.x", repo="o/r", pass_traj="tp", pass_model="m1",
                fail_traj="tf", fail_model="m2", cross_model=True)
PASSING = Run(traj_id="tp", model="m1", resolved=True, issue="Crop fails on odd sizes",
              steps=[step(0, "view", ["crop.py"], "look at crop"), step(1, "edit", ["crop.py"]), step(2, "submit")],
              patch="diff --git a/crop.py b/crop.py")
FAILING = Run(traj_id="tf", model="m2", resolved=False, issue="Crop fails on odd sizes",
              steps=[step(0, "view", ["crop.py"]), step(1, "view", ["utils.py"], "maybe the helper"),
                     step(2, "edit", ["utils.py"], output="edited utils"), step(3, "submit")],
              patch="diff --git a/utils.py b/utils.py")
ALIGNMENT = Alignment(pair_id="p1", rows=[Row(p=0, f=0, match=True)],
                      candidates=[Candidate(step=2, rule="foreign_edit")])

GOOD = {"split_step": 2, "reason": "Edited utils.py although the bug is in crop.py.",
        "category": "wrong_location", "confidence": 0.8}


def test_prompt_contains_everything_the_judge_needs():
    prompt = judge.build_prompt(META, PASSING, FAILING, ALIGNMENT)
    assert "Crop fails on odd sizes" in prompt
    for s in PASSING.steps + FAILING.steps:
        assert judge.summary_line(s) in prompt
    assert "edited utils" in prompt  # detail window around the candidate
    assert "diff --git a/utils.py" in prompt and "diff --git a/crop.py" in prompt
    system = judge.system_prompt()
    assert all(c in system for c in CATEGORY_IDS)


def test_summary_line_is_one_line():
    line = judge.summary_line(step(4, "view", ["a.py"], "first line\nsecond line " + "x" * 200))
    assert "\n" not in line and line.startswith("4 view a.py")


@pytest.mark.parametrize("bad,why", [
    ({**GOOD, "split_step": 9}, "out of range"),
    ({**GOOD, "category": "bad_luck"}, "category"),
    ({**GOOD, "reason": ""}, "reason"),
    ({**GOOD, "reason": " ".join(["word"] * 45)}, "words"),
    ({**GOOD, "confidence": 3}, "confidence"),
])
def test_check_answer_rejects_bad_answers(bad, why):
    verdict, errors = judge.check_answer(bad, n_steps=4)
    assert verdict is None and errors


def test_check_answer_accepts_good_answer():
    verdict, errors = judge.check_answer(GOOD, n_steps=4)
    assert errors == [] and verdict.split_step == 2


def test_estimate_arithmetic():
    tokens_in, tokens_out, usd = judge.estimate(["a" * 4000, "b" * 4000], system="s" * 400)
    assert tokens_in == 2 * (1000 + 100 + judge.TOOL_TOKENS)
    assert tokens_out == 2 * judge.OUTPUT_TOKENS_GUESS
    assert usd == pytest.approx((tokens_in * judge.PRICE_IN + tokens_out * judge.PRICE_OUT) / 1e6 * judge.BATCH_DISCOUNT)


def tool_message(answer, tokens_in=1000, tokens_out=60):
    return NS(content=[NS(type="tool_use", name="record_verdict", input=answer)],
              usage=NS(input_tokens=tokens_in, output_tokens=tokens_out))


class FakeClient:
    def __init__(self, batch_results=(), retry_answers=()):
        self.created, self.retries = [], []
        self._results, self._retry = list(batch_results), list(retry_answers)
        self.messages = NS(create=self._create, batches=NS(create=self._batch_create,
                                                           retrieve=lambda _id: NS(processing_status="ended"),
                                                           results=lambda _id: iter(self._results)))

    def _batch_create(self, requests):
        self.created.append(requests)
        return NS(id="batch_1", processing_status="in_progress")

    def _create(self, **params):
        self.retries.append(params)
        return tool_message(self._retry.pop(0))


def test_collect_records_good_answers_and_retries_bad_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(judge, "JUDGE", tmp_path)
    requests = {"p1": {"model": judge.MODEL}, "p2": {"model": judge.MODEL}, "p3": {"model": judge.MODEL}}
    results = [
        NS(custom_id="p1", result=NS(type="succeeded", message=tool_message(GOOD))),
        NS(custom_id="p2", result=NS(type="succeeded", message=tool_message({**GOOD, "category": "nope"}))),
        NS(custom_id="p3", result=NS(type="errored", error=NS(type="api_error"))),
    ]
    client = FakeClient(results, retry_answers=[GOOD, {**GOOD, "split_step": 99}])
    records = judge.collect(client, "batch_1", requests, n_steps={"p1": 4, "p2": 4, "p3": 4})
    assert records["p1"].status == "judged" and records["p1"].attempts == 1
    assert records["p2"].status == "judged" and records["p2"].attempts == 2
    assert records["p3"].status == "not_judged" and records["p3"].errors
    assert (tmp_path / "p1.json").exists()
    assert records["p1"].cost_usd == pytest.approx((1000 * 1 + 60 * 5) / 1e6 * 0.5)


def test_submit_skips_cached_and_needs_yes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(judge, "JUDGE", tmp_path)
    judge.save_record(judge.JudgeRecord(pair_id="p1", status="judged", verdict=GOOD, attempts=1,
                                        input_tokens=1, output_tokens=1, cost_usd=0.0, errors=[]))
    client = FakeClient()
    todo = judge.pending({"p1": {"model": judge.MODEL}, "p2": {"model": judge.MODEL}})
    assert list(todo) == ["p2"]
    batch_id = judge.submit(client, todo, yes=False)
    assert batch_id is None and client.created == []
    assert "estimated" in capsys.readouterr().out.lower()
