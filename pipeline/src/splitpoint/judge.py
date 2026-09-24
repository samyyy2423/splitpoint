"""Stage 4: ask Claude Haiku where each failing run went wrong, via the Message Batches API.

Nothing is spent without --yes. Results are cached per pair, so reruns only submit what is missing.
"""

import json
import time

from pydantic import ValidationError

from .categories import CATEGORIES, CATEGORY_IDS
from .io import read_json, write_json
from .models import Alignment, JudgeRecord, PairMeta, Run, Verdict
from .paths import ALIGNED, JUDGE, PAIRS

MODEL = "claude-haiku-4-5"
# USD per million tokens for claude-haiku-4-5 (Anthropic model table, checked 2026-09-24).
PRICE_IN, PRICE_OUT = 1.00, 5.00
BATCH_DISCOUNT = 0.5
MAX_TOKENS = 1024
OUTPUT_TOKENS_GUESS = 200
TOOL_TOKENS = 250
REASON_WORDS_PROMPT, REASON_WORDS_MAX = 30, 40

ISSUE_CHARS, THOUGHT_CHARS, COMMAND_CHARS, OUTPUT_CHARS, PATCH_CHARS = 3000, 600, 600, 800, 3000
WINDOW = 3

RULE_TEXT = {
    "foreign_edit": "first edit to a file the passing run never edited",
    "lost_thread": "first step after the runs stopped matching",
    "unfixed_test_failure": "first failing test run that was never fixed",
    "fallback": "first step that differs from the passing run",
}

TOOL = {
    "name": "record_verdict",
    "description": "Record where the failing run went wrong and why.",
    "input_schema": {
        "type": "object",
        "properties": {
            "split_step": {"type": "integer", "description": "Step number in the FAILING run where it went wrong."},
            "reason": {"type": "string", "description": f"At most {REASON_WORDS_PROMPT} words: what the failing run did wrong and why it mattered."},
            "category": {"type": "string", "enum": CATEGORY_IDS},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["split_step", "reason", "category", "confidence"],
        "additionalProperties": False,
    },
}


def clip(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + f"… [{len(text) - limit} more characters]"


def one_line(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def summary_line(step) -> str:
    target = " ".join(step.files) if step.files else one_line(step.command.splitlines()[0] if step.command else "", 60)
    line = f"{step.index} {step.action} {target}".rstrip()
    return f"{line} — {one_line(step.thought, 80)}" if step.thought.strip() else line


def system_prompt() -> str:
    categories = "\n".join(f"- {c.id}: {c.definition}" for c in CATEGORIES)
    return (
        "You review coding-agent runs. Two runs attempted the same task in the same repository: one passed "
        "the hidden tests and one failed. Find the step in the FAILING run where it went wrong: the earliest "
        "step after which it could not succeed without undoing that step. Then classify the failure.\n\n"
        "The passing run is a reference, not the only correct path; doing things differently is not a mistake "
        "by itself. The candidate steps come from an automatic alignment and can be wrong; treat them as hints.\n\n"
        f"Failure categories:\n{categories}\n\n"
        f"Answer only by calling record_verdict. The reason must be plain English, at most {REASON_WORDS_PROMPT} words."
    )


def detail(step) -> str:
    return (f"Step {step.index} [{step.action}]\nThought: {clip(step.thought, THOUGHT_CHARS)}\n"
            f"Command: {clip(step.command, COMMAND_CHARS)}\nOutput: {clip(step.output, OUTPUT_CHARS)}")


def build_prompt(meta: PairMeta, passing: Run, failing: Run, alignment: Alignment) -> str:
    window = sorted({i for c in alignment.candidates
                     for i in range(c.step - WINDOW, c.step + WINDOW + 1) if 0 <= i < len(failing.steps)})
    candidates = "\n".join(f"- step {c.step}: {RULE_TEXT[c.rule]}" for c in alignment.candidates)
    return "\n\n".join([
        f"<issue repo=\"{meta.repo}\">\n{clip(failing.issue or passing.issue, ISSUE_CHARS)}\n</issue>",
        f"<passing_run model=\"{passing.model}\">\n" + "\n".join(summary_line(s) for s in passing.steps) + "\n</passing_run>",
        f"<failing_run model=\"{failing.model}\">\n" + "\n".join(summary_line(s) for s in failing.steps) + "\n</failing_run>",
        f"<candidates>\n{candidates}\n</candidates>",
        "<failing_run_detail>\n" + "\n\n".join(detail(failing.steps[i]) for i in window) + "\n</failing_run_detail>",
        f"<passing_patch>\n{clip(passing.patch, PATCH_CHARS)}\n</passing_patch>",
        f"<failing_patch>\n{clip(failing.patch, PATCH_CHARS)}\n</failing_patch>",
    ])


def request_params(prompt: str) -> dict:
    return {
        "model": MODEL, "max_tokens": MAX_TOKENS, "system": system_prompt(), "tools": [TOOL],
        "tool_choice": {"type": "tool", "name": TOOL["name"]},
        "messages": [{"role": "user", "content": prompt}],
    }


def check_answer(raw: dict, n_steps: int) -> tuple[Verdict | None, list[str]]:
    try:
        verdict = Verdict.model_validate(raw)
    except ValidationError as exc:
        return None, [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
    errors = []
    if verdict.split_step >= n_steps:
        errors.append(f"split_step {verdict.split_step} out of range (failing run has {n_steps} steps)")
    if len(verdict.reason.split()) > REASON_WORDS_MAX:
        errors.append(f"reason has {len(verdict.reason.split())} words")
    return (None, errors) if errors else (verdict, [])


def cost(tokens_in: int, tokens_out: int, discount: float = 1.0) -> float:
    return (tokens_in * PRICE_IN + tokens_out * PRICE_OUT) / 1e6 * discount


def estimate(prompts: list[str], system: str) -> tuple[int, int, float]:
    tokens_in = sum((len(system) + len(p)) // 4 + TOOL_TOKENS for p in prompts)
    tokens_out = OUTPUT_TOKENS_GUESS * len(prompts)
    return tokens_in, tokens_out, cost(tokens_in, tokens_out, BATCH_DISCOUNT)


def save_record(record: JudgeRecord) -> None:
    write_json(JUDGE / f"{record.pair_id}.json", record.model_dump())


def load_record(pair_id: str) -> JudgeRecord | None:
    path = JUDGE / f"{pair_id}.json"
    return JudgeRecord.model_validate(read_json(path)) if path.exists() else None


def pending(requests: dict[str, dict]) -> dict[str, dict]:
    done = {pid for pid in requests if (r := load_record(pid)) and r.status == "judged"}
    return {pid: p for pid, p in requests.items() if pid not in done}


def submit(client, requests: dict[str, dict], yes: bool) -> str | None:
    prompts = [p["messages"][0]["content"] if "messages" in p else "" for p in requests.values()]
    tokens_in, tokens_out, usd = estimate(prompts, system_prompt())
    print(f"{len(requests)} requests to {MODEL}; estimated {tokens_in:,} input + {tokens_out:,} output tokens "
          f"= ${usd:.2f} at batch prices")
    if not requests or not yes:
        if requests:
            print("Nothing submitted. Re-run with --yes to spend it.")
        return None
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    batch = client.messages.batches.create(requests=[
        Request(custom_id=pid, params=MessageCreateParamsNonStreaming(**params)) for pid, params in requests.items()
    ])
    write_json(JUDGE / "batch.json", {"id": batch.id, "pair_ids": list(requests)}, indent=2)
    print(f"submitted batch {batch.id}")
    return batch.id


def wait(client, batch_id: str, every: int = 30) -> None:
    while (batch := client.messages.batches.retrieve(batch_id)).processing_status != "ended":
        counts = getattr(batch, "request_counts", None)
        print(f"batch {batch_id}: {batch.processing_status}"
              + (f", {counts.processing} still processing" if counts else ""))
        time.sleep(every)


def tool_input(message) -> dict | None:
    return next((b.input for b in message.content if b.type == "tool_use" and b.name == TOOL["name"]), None)


def collect(client, batch_id: str, requests: dict[str, dict], n_steps: dict[str, int]) -> dict[str, JudgeRecord]:
    records = {}
    for item in client.messages.batches.results(batch_id):
        pid = item.custom_id
        tokens_in = tokens_out = 0
        usd = 0.0
        errors: list[str] = []
        verdict = None
        if item.result.type == "succeeded":
            msg = item.result.message
            tokens_in, tokens_out = msg.usage.input_tokens, msg.usage.output_tokens
            usd = cost(tokens_in, tokens_out, BATCH_DISCOUNT)
            raw = tool_input(msg)
            verdict, errors = check_answer(raw, n_steps[pid]) if raw is not None else (None, ["no tool call"])
        else:
            errors = [f"batch result {item.result.type}"]
        attempts = 1
        if verdict is None:  # one retry through the standard Messages API
            attempts = 2
            try:
                msg = client.messages.create(**requests[pid])
                tokens_in += msg.usage.input_tokens
                tokens_out += msg.usage.output_tokens
                usd += cost(msg.usage.input_tokens, msg.usage.output_tokens)
                raw = tool_input(msg)
                verdict, retry_errors = check_answer(raw, n_steps[pid]) if raw is not None else (None, ["no tool call"])
                errors += [f"retry: {e}" for e in retry_errors]
            except Exception as exc:  # recorded on the pair, never raised past one pair
                errors.append(f"retry: {type(exc).__name__}: {exc}")
        record = JudgeRecord(pair_id=pid, status="judged" if verdict else "not_judged", verdict=verdict,
                             attempts=attempts, input_tokens=tokens_in, output_tokens=tokens_out,
                             cost_usd=usd, errors=[] if verdict else errors)
        save_record(record)
        records[pid] = record
    return records


def all_requests() -> tuple[dict[str, dict], dict[str, int]]:
    from .steps import load_run
    requests, n_steps = {}, {}
    for line in PAIRS.read_text(encoding="utf-8").splitlines():
        meta = PairMeta.model_validate_json(line)
        passing, failing = load_run(meta.pass_traj), load_run(meta.fail_traj)
        alignment = Alignment.model_validate(read_json(ALIGNED / f"{meta.pair_id}.json"))
        requests[meta.pair_id] = request_params(build_prompt(meta, passing, failing, alignment))
        n_steps[meta.pair_id] = len(failing.steps)
    return requests, n_steps


def run(args) -> None:
    from dotenv import load_dotenv
    from .paths import ROOT
    load_dotenv(ROOT / "pipeline" / ".env")
    requests, n_steps = all_requests()
    if args.resume:
        import anthropic
        client = anthropic.Anthropic()
        batch_id = args.resume
    else:
        todo = pending(requests)
        client = None
        if args.yes and todo:
            import anthropic
            client = anthropic.Anthropic()
        batch_id = submit(client, todo, yes=args.yes)
        if batch_id is None:
            return
    wait(client, batch_id)
    records = collect(client, batch_id, requests, n_steps)
    judged = sum(r.status == "judged" for r in records.values())
    spent = sum(r.cost_usd for r in records.values())
    print(f"{judged} of {len(records)} judged; {len(records) - judged} not judged; spent ${spent:.2f}")
    print(json.dumps({pid: r.errors for pid, r in records.items() if r.errors}, indent=2)[:2000])
