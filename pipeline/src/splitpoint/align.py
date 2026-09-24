"""Stage 3: line up a passing and a failing run, and propose where the failing one split off."""

import json

from .io import write_json
from .models import Alignment, Candidate, Row, Run
from .paths import ALIGNED, PAIRS
from .steps import load_run, main_command

MATCH, SAME_FILE, MISMATCH, GAP = 2, 1, -1, -1


def token(step) -> str:
    if step.files:
        return f"{step.action}:{step.files[0]}"
    if step.action == "submit":
        return "submit:"
    first_line = main_command(step.command).splitlines()[0] if step.command.strip() else ""
    return f"{step.action}:{' '.join(first_line.split())[:40]}"


def _file(tok: str) -> str | None:
    action, _, rest = tok.partition(":")
    return rest if action in {"view", "create", "edit"} and rest else None


def _score(a: str, b: str) -> int:
    if a == b:
        return MATCH
    fa, fb = _file(a), _file(b)
    return SAME_FILE if fa and fa == fb else MISMATCH


def needleman_wunsch(a: list[str], b: list[str]) -> list[Row]:
    """Global alignment of two token lists. Rows reference indexes into a (pass) and b (fail)."""
    n, m = len(a), len(b)
    score = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0] = i * GAP
    for j in range(1, m + 1):
        score[0][j] = j * GAP
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            score[i][j] = max(score[i - 1][j - 1] + _score(a[i - 1], b[j - 1]),
                              score[i - 1][j] + GAP, score[i][j - 1] + GAP)
    rows: list[Row] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and score[i][j] == score[i - 1][j - 1] + _score(a[i - 1], b[j - 1]):
            rows.append(Row(p=i - 1, f=j - 1, match=a[i - 1] == b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and score[i][j] == score[i - 1][j] + GAP:
            rows.append(Row(p=i - 1, f=None, match=False))
            i -= 1
        else:
            rows.append(Row(p=None, f=j - 1, match=False))
            j -= 1
    return rows[::-1]


def candidates(passing: Run, failing: Run, rows: list[Row]) -> list[Candidate]:
    found: list[Candidate] = []

    passing_edits = {f for s in passing.steps if s.action == "edit" for f in s.files}
    foreign = next((s.index for s in failing.steps if s.action == "edit" and s.files
                    and s.files[0] not in passing_edits), None)
    if foreign is not None:
        found.append(Candidate(step=foreign, rule="foreign_edit"))

    # Both runs usually end the same way (run the scratch repro script, submit), so those matches
    # say nothing about whether the failing run was still on track.
    scratch = {f for s in failing.steps if s.action == "create" for f in s.files}

    def meaningful(r: Row) -> bool:
        s = failing.steps[r.f]
        return s.action != "submit" and not (s.files and s.files[0] in scratch)

    matched = [r.f for r in rows if r.match and r.f is not None and meaningful(r)]
    last = matched[-1] if matched else -1
    after = next((s.index for s in failing.steps[last + 1:] if s.action != "submit"), None)
    if after is not None:
        found.append(Candidate(step=after, rule="lost_thread"))

    tests = [s for s in failing.steps if s.action == "test" and s.test_result]
    for k, s in enumerate(tests):
        broken = s.test_result.failed + s.test_result.errors > 0
        cleared = any(t.test_result.failed + t.test_result.errors == 0 for t in tests[k + 1:])
        if broken and not cleared:
            found.append(Candidate(step=s.index, rule="unfixed_test_failure"))
            break

    unique: dict[int, Candidate] = {}
    for c in found:
        unique.setdefault(c.step, c)
    if not unique:
        unmatched = next((r.f for r in rows if r.f is not None and not r.match), len(failing.steps) - 1)
        return [Candidate(step=unmatched, rule="fallback")]
    return sorted(unique.values(), key=lambda c: c.step)


def align_pair(pair_id: str, passing: Run, failing: Run) -> Alignment:
    rows = needleman_wunsch([token(s) for s in passing.steps], [token(s) for s in failing.steps])
    return Alignment(pair_id=pair_id, rows=rows, candidates=candidates(passing, failing, rows))


def run(args=None) -> None:
    from collections import Counter
    rules, matched = Counter(), []
    for line in PAIRS.read_text(encoding="utf-8").splitlines():
        pair = json.loads(line)
        passing, failing = load_run(pair["pass_traj"]), load_run(pair["fail_traj"])
        alignment = align_pair(pair["pair_id"], passing, failing)
        write_json(ALIGNED / f"{pair['pair_id']}.json", alignment.model_dump())
        rules.update(c.rule for c in alignment.candidates)
        matched.append(sum(r.match for r in alignment.rows) / max(1, len(failing.steps)))
    matched.sort()
    print(f"aligned {len(matched)} pairs; candidate rules: {dict(rules)}; "
          f"median share of failing steps matched: {matched[len(matched) // 2]:.2f}")
