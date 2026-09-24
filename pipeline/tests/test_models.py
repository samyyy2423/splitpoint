import json

import jsonschema
import pytest
from pydantic import ValidationError

from splitpoint.categories import CATEGORIES, CATEGORY_IDS
from splitpoint.models import SiteData, Verdict, write_schema


def test_eight_categories_with_unique_ids():
    assert len(CATEGORIES) == 8
    assert len(set(CATEGORY_IDS)) == 8
    assert all(c.label and c.definition for c in CATEGORIES)


def test_verdict_rejects_unknown_category():
    with pytest.raises(ValidationError):
        Verdict(split_step=3, reason="Edited the wrong file.", category="bad_luck", confidence=0.5)


def test_verdict_rejects_confidence_out_of_range():
    with pytest.raises(ValidationError):
        Verdict(split_step=3, reason="Edited the wrong file.", category="wrong_location", confidence=1.5)


def minimal_site_data() -> dict:
    step = {
        "index": 0, "thought": "look around", "tool": "bash", "command": "ls", "action": "search",
        "files": [], "output": "a.py", "truncated": False, "test_result": None,
    }
    run = {"traj_id": "t1", "model": "m", "resolved": True, "issue": "bug", "steps": [step], "patch": ""}
    return {
        "index": [{
            "pair_id": "abc", "instance_id": "o__r.1.x", "repo": "o/r", "pass_model": "m",
            "fail_model": "n", "category": None, "split_step": None, "fail_steps": 1, "validation": False,
        }],
        "pair": {
            "pair_id": "abc", "instance_id": "o__r.1.x", "repo": "o/r", "issue": "bug",
            "pass_run": run, "fail_run": {**run, "traj_id": "t2", "resolved": False},
            "rows": [{"p": 0, "f": 0, "match": True}], "candidates": [{"step": 0, "rule": "fallback"}],
            "verdict": None, "validation": False,
        },
        "findings": {
            "n_pairs": 1, "n_judged": 0, "categories": {}, "by_model": {}, "split_fraction_hist": [0] * 10,
            "median_split_fraction": None, "validation": None, "judge_input_tokens": 0,
            "judge_output_tokens": 0, "judge_cost_usd": 0.0,
        },
        "category_defs": [c.model_dump() for c in CATEGORIES],
    }


def test_schema_validates_minimal_site_data(tmp_path):
    path = tmp_path / "schema.json"
    write_schema(path)
    schema = json.loads(path.read_text(encoding="utf-8"))
    data = minimal_site_data()
    SiteData.model_validate(data)
    jsonschema.validate(data, schema)


def test_schema_rejects_bad_category(tmp_path):
    path = tmp_path / "schema.json"
    write_schema(path)
    schema = json.loads(path.read_text(encoding="utf-8"))
    data = minimal_site_data()
    data["index"][0]["category"] = "bad_luck"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, schema)
