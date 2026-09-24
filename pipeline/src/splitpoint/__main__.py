"""CLI: python -m splitpoint <stage>. Each stage reads the previous stage's files under data/."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="splitpoint")
    sub = parser.add_subparsers(dest="stage", required=True)

    sub.add_parser("pick", help="download SWE-smith and choose pass/fail pairs")
    sub.add_parser("steps", help="turn the chosen runs into steps")
    sub.add_parser("align", help="align each pair and propose split candidates")
    judge = sub.add_parser("judge", help="ask Claude Haiku where each failing run went wrong")
    judge.add_argument("--yes", action="store_true", help="submit the batch after printing the estimate")
    judge.add_argument("--resume", metavar="BATCH_ID", help="collect results of an earlier batch")
    validate = sub.add_parser("validate", help="score the judge against your labels")
    validate.add_argument("--labels", required=True, help="labels.json exported from /label")
    sub.add_parser("export", help="write the site's JSON")
    sub.add_parser("schema", help="write the JSON Schema the site's types are generated from")

    args = parser.parse_args(argv)
    if args.stage == "schema":
        from .models import write_schema
        from .paths import SCHEMA
        write_schema(SCHEMA)
        print(f"wrote {SCHEMA}")
        return 0
    import importlib
    module = importlib.import_module(f"splitpoint.{args.stage}")
    return module.run(args) or 0


if __name__ == "__main__":
    sys.exit(main())
