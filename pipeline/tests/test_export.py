import json
from pathlib import Path

import jsonschema
import pytest

from splitpoint.align import align_pair
from splitpoint.export import build_site, doc_validator
from splitpoint.models import JudgeRecord, PairMeta, Validation, Verdict, write_schema
from splitpoint.steps import parse_run

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def site_inputs():
    raw = {n: json.loads((FIXTURES / f"run_{n}.json").read_text(encoding="utf-8")) for n in ("pass", "fail")}
    runs = {r["traj_id"]: parse_run(r["messages"], r["patch"], r["traj_id"], r["model"], r["resolved"]) for r in raw.values()}
    p, f = raw["pass"], raw["fail"]
    metas = [
        PairMeta(pair_id="aaa", instance_id="dask__dask.1.x", repo="dask/dask", pass_traj=p["traj_id"],
                 pass_model=p["model"], fail_traj=f["traj_id"], fail_model=f["model"], cross_model=True),
        PairMeta(pair_id="bbb", instance_id="dask__dask.2.x", repo="dask/dask", pass_traj=p["traj_id"],
                 pass_model=p["model"], fail_traj=f["traj_id"], fail_model=f["model"], cross_model=True),
        PairMeta(pair_id="ccc", instance_id="dask__dask.3.x", repo="dask/dask", pass_traj="missing",
                 pass_model="m", fail_traj=f["traj_id"], fail_model=f["model"], cross_model=True),
    ]
    alignments = {m.pair_id: align_pair(m.pair_id, runs[p["traj_id"]], runs[f["traj_id"]]) for m in metas[:2]}
    records = {
        "aaa": JudgeRecord(pair_id="aaa", status="judged", attempts=1, input_tokens=5000, output_tokens=80,
                           cost_usd=0.003, errors=[],
                           verdict=Verdict(split_step=2, reason="Wrong file.", category="wrong_location", confidence=0.7)),
        "bbb": JudgeRecord(pair_id="bbb", status="not_judged", verdict=None, attempts=2, input_tokens=9000,
                           output_tokens=100, cost_usd=0.005, errors=["bad"]),
    }
    return metas, runs, alignments, records


def test_build_site(site_inputs):
    metas, runs, alignments, records = site_inputs
    validation = Validation(n=1, category_kappa=1.0, category_agreement=1.0, split_exact=1.0,
                            split_within_2=1.0, baseline_split_exact=0.0, baseline_split_within_2=0.0)
    index, docs, findings, report = build_site(metas, runs.get, alignments, records, {"bbb"}, validation)
    assert [e.pair_id for e in index] == ["aaa", "bbb"]
    assert index[0].category == "wrong_location" and index[0].split_step == 2
    assert index[1].category is None and index[1].validation
    assert docs["bbb"].verdict is None
    assert findings.n_pairs == 2 and findings.n_judged == 1
    assert findings.categories == {"wrong_location": 1}
    assert sum(findings.split_fraction_hist) == 1
    assert findings.judge_input_tokens == 14000 and findings.judge_cost_usd == pytest.approx(0.008)
    assert findings.validation.n == 1
    assert report["skipped"] == [{"pair_id": "ccc", "reason": "missing run missing"}]
    assert report["not_judged"] == ["bbb"]


def test_exported_docs_match_schema(site_inputs, tmp_path):
    metas, runs, alignments, records = site_inputs
    schema_path = tmp_path / "schema.json"
    write_schema(schema_path)
    index, docs, findings, _ = build_site(metas, runs.get, alignments, records, set(), None)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    doc_validator(schema, "PairDoc").validate(docs["aaa"].model_dump())
    doc_validator(schema, "Findings").validate(findings.model_dump())
    for entry in index:
        doc_validator(schema, "IndexEntry").validate(entry.model_dump())
    broken = docs["aaa"].model_dump()
    broken["verdict"]["category"] = "nope"
    with pytest.raises(jsonschema.ValidationError):
        doc_validator(schema, "PairDoc").validate(broken)
