import json
from pathlib import Path

import pytest

from splitpoint.steps import (classify, issue_of, loads_loose, parse_run, parse_test_summary, render_command, trim,
                              trim_patch)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("tool,args,action,files", [
    ("str_replace_editor", {"command": "view", "path": "/testbed/src/a.py"}, "view", ["src/a.py"]),
    ("str_replace_editor", {"command": "create", "path": "/testbed/repro.py"}, "create", ["repro.py"]),
    ("str_replace_editor", {"command": "str_replace", "path": "/testbed/src/a.py"}, "edit", ["src/a.py"]),
    ("str_replace_editor", {"command": "insert", "path": "/testbed/src/a.py"}, "edit", ["src/a.py"]),
    ("str_replace_editor", {"command": "undo_edit", "path": "/testbed/src/a.py"}, "edit", ["src/a.py"]),
    ("submit", {}, "submit", []),
    ("bash", {"command": "cd /testbed && python -m pytest tests/test_a.py -x"}, "test", ["tests/test_a.py"]),
    ("bash", {"command": "pytest -q"}, "test", []),
    ("bash", {"command": "cd /testbed && python -m unittest discover"}, "test", []),
    ("bash", {"command": "grep -rn 'SpatialCrop' /testbed/monai"}, "search", []),
    ("bash", {"command": "find /testbed -name '*.py' | grep forms"}, "search", []),
    ("bash", {"command": "cat /testbed/setup.cfg"}, "view", ["setup.cfg"]),
    ("bash", {"command": "cd /testbed && python reproduce.py"}, "run", ["reproduce.py"]),
    ("bash", {"command": "pip install -e ."}, "run", []),
    ("mystery", {}, "other", []),
])
def test_classify(tool, args, action, files):
    assert classify(tool, args) == (action, files)


@pytest.mark.parametrize("output,expected", [
    ("===== 3 failed, 10 passed in 0.52s =====", (10, 3, 0)),
    ("== 12 passed, 1 warning in 1.0s ==", (12, 0, 0)),
    ("=== 1 passed, 2 errors in 0.1s ===", (1, 0, 2)),
    ("Ran 5 tests in 0.003s\n\nOK", (5, 0, 0)),
    ("Ran 5 tests in 0.003s\n\nFAILED (failures=2, errors=1)", (2, 2, 1)),
    ("no test output here", None),
])
def test_parse_test_summary(output, expected):
    result = parse_test_summary(output)
    assert (None if result is None else (result.passed, result.failed, result.errors)) == expected


def test_trim_keeps_head_and_tail():
    text = "a" * 3000 + "b" * 3000
    out, cut = trim(text, limit=4000)
    assert cut and out.startswith("a" * 2500) and out.endswith("b" * 1500)
    assert "2000 characters trimmed" in out
    assert trim("short", limit=4000) == ("short", False)


def test_trim_patch_caps_each_file_and_the_total():
    small = "diff --git a/a.py b/a.py\n+x = 1\n"
    huge = "diff --git a/data.csv b/data.csv\n" + "+row\n" * 10000
    patch, cut = trim_patch(small + huge + small.replace("a.py", "c.py"), per_file=1000, total=1500)
    assert cut
    assert patch.startswith(small)
    assert "diff --git a/data.csv" in patch and "characters of this file trimmed" in patch
    assert "diff --git a/c.py" in patch or "more files trimmed" in patch
    assert len(patch) < 2000
    assert trim_patch(small) == (small, False)


def test_issue_of_extracts_pr_description():
    text = "I've uploaded a repo.\n<pr_description>\nCrop fails on odd sizes\n</pr_description>\nPlease fix."
    assert issue_of(text) == "Crop fails on odd sizes"
    assert issue_of("plain text") == "plain text"


def test_loads_loose_handles_json_and_python_repr():
    assert loads_loose('[{"a": 1}]') == [{"a": 1}]
    assert loads_loose("[{'a': True}]") == [{"a": True}]


def test_render_command():
    assert render_command("bash", {"command": "ls"}) == "ls"
    edit = render_command("str_replace_editor", {"command": "str_replace", "path": "/testbed/a.py",
                                                  "old_str": "x = 1", "new_str": "x = 2"})
    assert edit.startswith("str_replace a.py") and "x = 1" in edit and "x = 2" in edit


def test_xml_function_call_runs_parse():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "<pr_description>\nBug in a.py\n</pr_description>"},
        {"role": "assistant", "content": "Let me look.\n\n<function=str_replace_editor>\n"
                                         "<parameter=command>view</parameter>\n<parameter=path>/testbed/a.py</parameter>\n</function>"},
        {"role": "user", "content": "OBSERVATION:\nx = 1"},
        {"role": "assistant", "content": "<function=bash>\n<parameter=command>cd /testbed && pytest</parameter>\n</function>"},
        {"role": "user", "content": "OBSERVATION:\n== 1 failed, 2 passed in 0.1s =="},
        {"role": "assistant", "content": "<function=submit>\n</function>"},
    ]
    run = parse_run(json.dumps(messages), "", "t", "m", False)
    assert run.issue == "Bug in a.py"
    assert [s.action for s in run.steps] == ["view", "test", "submit"]
    assert run.steps[0].thought == "Let me look." and run.steps[0].files == ["a.py"]
    assert run.steps[0].output == "x = 1"
    assert run.steps[1].test_result.failed == 1


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["run_pass.json", "run_fail.json"])
def test_fixture_runs_parse(name):
    raw = load_fixture(name)
    run = parse_run(raw["messages"], raw["patch"], raw["traj_id"], raw["model"], raw["resolved"])
    assert run.issue and "<pr_description>" not in run.issue
    assert run.steps and all(s.action for s in run.steps)
    assert [s.index for s in run.steps] == list(range(len(run.steps)))
    assert sum(1 for s in run.steps if s.output) >= len(run.steps) - 1
    assert run.steps[-1].action == "submit" or not run.resolved
