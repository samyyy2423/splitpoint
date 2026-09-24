"""Stage 1: download SWE-smith's tool split and choose one passing and one failing run per task."""

import hashlib
import json
import random
from collections import defaultdict
from itertools import product

from . import SEED
from .models import PairMeta
from .paths import PAIRS, PARQUET_GLOB, RAW, VALIDATION_IDS

DATASET = "SWE-bench/SWE-smith-trajectories"


def repo_of(instance_id: str) -> str:
    return instance_id.split(".", 1)[0].replace("__", "/")


def pair_id(pass_traj: str, fail_traj: str) -> str:
    return hashlib.sha1(f"{pass_traj}|{fail_traj}".encode()).hexdigest()[:10]


def select_pairs(rows: list[dict], n: int = 300, seed: int = SEED) -> list[PairMeta]:
    """Keep tasks with at least one pass and one fail. Prefer a pass and a fail from different
    models; take every cross-model pair first, then fill with same-model pairs."""
    rng = random.Random(seed)
    by_task: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_task[r["instance_id"]].append(r)

    cross, same = [], []
    for task in sorted(by_task):
        runs = by_task[task]
        passes = sorted((r for r in runs if r["resolved"]), key=lambda r: r["traj_id"])
        fails = sorted((r for r in runs if not r["resolved"]), key=lambda r: r["traj_id"])
        if not passes or not fails:
            continue
        combos = list(product(passes, fails))
        cross_combos = [(p, f) for p, f in combos if p["model"] != f["model"]]
        p, f = rng.choice(cross_combos or combos)
        meta = PairMeta(
            pair_id=pair_id(p["traj_id"], f["traj_id"]), instance_id=task, repo=repo_of(task),
            pass_traj=p["traj_id"], pass_model=p["model"], fail_traj=f["traj_id"],
            fail_model=f["model"], cross_model=bool(cross_combos),
        )
        (cross if cross_combos else same).append(meta)

    if len(cross) >= n:
        return sorted(rng.sample(cross, n), key=lambda m: m.instance_id)
    fill = sorted(rng.sample(same, min(n - len(cross), len(same))), key=lambda m: m.instance_id)
    return cross + fill


def pick_validation(pairs: list[PairMeta], k: int = 50, seed: int = SEED) -> list[str]:
    ids = sorted(p.pair_id for p in pairs)
    return sorted(random.Random(seed).sample(ids, min(k, len(ids))))


def download() -> None:
    from huggingface_hub import snapshot_download
    snapshot_download(DATASET, repo_type="dataset", revision="refs/convert/parquet",
                      allow_patterns="default/tool/*.parquet", local_dir=RAW)


def load_meta() -> list[dict]:
    import duckdb
    query = f"""SELECT traj_id, instance_id, model, CAST(resolved AS BOOLEAN) AS resolved
                FROM read_parquet('{PARQUET_GLOB.as_posix()}')"""
    cur = duckdb.sql(query)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def run(args=None) -> None:
    download()
    rows = load_meta()
    pairs = select_pairs(rows)
    PAIRS.parent.mkdir(parents=True, exist_ok=True)
    PAIRS.write_text("".join(p.model_dump_json() + "\n" for p in pairs), encoding="utf-8")
    ids = pick_validation(pairs)
    VALIDATION_IDS.write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")
    n_cross = sum(p.cross_model for p in pairs)
    print(f"{len(rows)} runs -> {len(pairs)} pairs ({n_cross} cross-model), {len(ids)} for validation")
