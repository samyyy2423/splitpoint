"""Stage 6: write the JSON the site reads, and check every file against the shared schema."""

import statistics
from collections import Counter, defaultdict
from typing import Callable

import jsonschema

from .categories import CATEGORIES
from .io import read_json, write_json
from .models import (Alignment, Findings, IndexEntry, JudgeRecord, PairDoc, PairMeta, Run, Validation,
                     write_schema)
from .paths import ALIGNED, EXPORT_REPORT, PAIRS, SCHEMA, VALIDATION, VALIDATION_IDS, WEB_DATA

BINS = 10


def build_site(metas: list[PairMeta], get_run: Callable[[str], Run | None], alignments: dict[str, Alignment],
               records: dict[str, JudgeRecord], validation_ids: set[str], validation: Validation | None):
    index, docs, skipped = [], {}, []
    for m in metas:
        passing, failing = get_run(m.pass_traj), get_run(m.fail_traj)
        missing = [t for t, r in ((m.pass_traj, passing), (m.fail_traj, failing)) if r is None]
        if missing or m.pair_id not in alignments:
            reason = f"missing run {missing[0]}" if missing else "missing alignment"
            skipped.append({"pair_id": m.pair_id, "reason": reason})
            continue
        record = records.get(m.pair_id)
        verdict = record.verdict if record and record.status == "judged" else None
        alignment = alignments[m.pair_id]
        docs[m.pair_id] = PairDoc(
            pair_id=m.pair_id, instance_id=m.instance_id, repo=m.repo, issue=failing.issue or passing.issue,
            pass_run=passing, fail_run=failing, rows=alignment.rows, candidates=alignment.candidates,
            verdict=verdict, validation=m.pair_id in validation_ids,
        )
        index.append(IndexEntry(
            pair_id=m.pair_id, instance_id=m.instance_id, repo=m.repo, pass_model=m.pass_model,
            fail_model=m.fail_model, category=verdict.category if verdict else None,
            split_step=verdict.split_step if verdict else None, fail_steps=len(failing.steps),
            validation=m.pair_id in validation_ids,
        ))

    judged = [e for e in index if e.category is not None]
    by_model: dict[str, Counter] = defaultdict(Counter)
    for e in judged:
        by_model[e.fail_model][e.category] += 1
    fractions = [min(e.split_step / max(e.fail_steps, 1), 0.999) for e in judged]
    hist = [0] * BINS
    for x in fractions:
        hist[int(x * BINS)] += 1
    exported = set(docs)
    spent = [r for pid, r in records.items() if pid in exported]
    findings = Findings(
        n_pairs=len(index), n_judged=len(judged),
        categories=dict(Counter(e.category for e in judged)),
        by_model={model: dict(counts) for model, counts in sorted(by_model.items())},
        split_fraction_hist=hist,
        median_split_fraction=statistics.median(fractions) if fractions else None,
        validation=validation,
        judge_input_tokens=sum(r.input_tokens for r in spent),
        judge_output_tokens=sum(r.output_tokens for r in spent),
        judge_cost_usd=round(sum(r.cost_usd for r in spent), 4),
    )
    report = {
        "skipped": skipped,
        "not_judged": sorted(pid for pid, r in records.items() if r.status == "not_judged" and pid in exported),
        "never_submitted": sorted(pid for pid in exported if pid not in records),
    }
    return index, docs, findings, report


def doc_validator(schema: dict, name: str) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": schema["$defs"]})


def run(args=None) -> None:
    from .judge import load_record
    from .steps import load_run
    from .paths import RUNS

    metas = [PairMeta.model_validate_json(line) for line in PAIRS.read_text(encoding="utf-8").splitlines()]
    alignments = {m.pair_id: Alignment.model_validate(read_json(ALIGNED / f"{m.pair_id}.json"))
                  for m in metas if (ALIGNED / f"{m.pair_id}.json").exists()}
    records = {m.pair_id: r for m in metas if (r := load_record(m.pair_id))}
    validation_ids = set(read_json(VALIDATION_IDS)) if VALIDATION_IDS.exists() else set()
    validation = Validation.model_validate(read_json(VALIDATION)) if VALIDATION.exists() else None

    def get_run(traj_id: str) -> Run | None:
        return load_run(traj_id) if (RUNS / f"{traj_id}.json").exists() else None

    index, docs, findings, report = build_site(metas, get_run, alignments, records, validation_ids, validation)

    write_schema(SCHEMA)
    schema = read_json(SCHEMA)
    pair_check, entry_check = doc_validator(schema, "PairDoc"), doc_validator(schema, "IndexEntry")
    for old in (WEB_DATA / "pairs").glob("*.json"):
        old.unlink()
    for pid, doc in docs.items():
        data = doc.model_dump()
        pair_check.validate(data)
        write_json(WEB_DATA / "pairs" / f"{pid}.json", data)
    index_data = [e.model_dump() for e in index]
    for entry in index_data:
        entry_check.validate(entry)
    write_json(WEB_DATA / "index.json", index_data)
    doc_validator(schema, "Findings").validate(findings.model_dump())
    write_json(WEB_DATA / "findings.json", findings.model_dump(), indent=2)
    write_json(WEB_DATA / "categories.json", [c.model_dump() for c in CATEGORIES], indent=2)
    write_json(EXPORT_REPORT, report, indent=2)

    size = sum(p.stat().st_size for p in WEB_DATA.rglob("*.json"))
    print(f"exported {len(docs)} pairs ({findings.n_judged} judged), {size / 1e6:.1f} MB; "
          f"{len(report['skipped'])} skipped, {len(report['not_judged'])} not judged, "
          f"{len(report['never_submitted'])} not yet submitted to the judge")
