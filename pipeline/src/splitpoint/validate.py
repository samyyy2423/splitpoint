"""Stage 5: score the judge (and the alignment on its own) against the owner's blind labels."""

from collections import Counter
from pathlib import Path

from .io import read_json, write_json
from .models import Alignment, Validation, Verdict
from .paths import ALIGNED, VALIDATION

TOLERANCE = 2


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def _share(hits: list[bool]) -> float | None:
    return sum(hits) / len(hits) if hits else None


def score(labels: list[dict], verdicts: dict[str, Verdict], alignments: dict[str, Alignment]) -> Validation:
    both = [lab for lab in labels if lab["pair_id"] in verdicts]
    human_cat = [lab["category"] for lab in both]
    judge_cat = [verdicts[lab["pair_id"]].category for lab in both]
    judge_d = [abs(verdicts[lab["pair_id"]].split_step - lab["split_step"]) for lab in both]
    base_d = [abs(alignments[lab["pair_id"]].candidates[0].step - lab["split_step"])
              for lab in both if lab["pair_id"] in alignments]
    return Validation(
        n=len(both),
        category_kappa=cohen_kappa(human_cat, judge_cat),
        category_agreement=_share([h == j for h, j in zip(human_cat, judge_cat)]),
        split_exact=_share([d == 0 for d in judge_d]),
        split_within_2=_share([d <= TOLERANCE for d in judge_d]),
        baseline_split_exact=_share([d == 0 for d in base_d]),
        baseline_split_within_2=_share([d <= TOLERANCE for d in base_d]),
    )


def run(args) -> None:
    from .judge import load_record
    labels = read_json(Path(args.labels))["labels"]
    verdicts, alignments = {}, {}
    for lab in labels:
        pid = lab["pair_id"]
        record = load_record(pid)
        if record and record.verdict:
            verdicts[pid] = record.verdict
        path = ALIGNED / f"{pid}.json"
        if path.exists():
            alignments[pid] = Alignment.model_validate(read_json(path))
    result = score(labels, verdicts, alignments)
    write_json(VALIDATION, result.model_dump(), indent=2)
    print(result.model_dump_json(indent=2))
