"""Where every stage reads and writes. Override the data dir with SPLITPOINT_DATA."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(os.environ.get("SPLITPOINT_DATA", ROOT / "data"))

RAW = DATA / "raw"
PARQUET_GLOB = RAW / "default" / "tool" / "*.parquet"
PAIRS = DATA / "pairs.jsonl"
VALIDATION_IDS = DATA / "validation_ids.json"
RUNS = DATA / "runs"
ALIGNED = DATA / "aligned"
JUDGE = DATA / "judge"
VALIDATION = DATA / "validation.json"
EXPORT_REPORT = DATA / "export_report.json"

WEB_DATA = ROOT / "web" / "public" / "data"
SCHEMA = ROOT / "web" / "src" / "types" / "schema.json"
