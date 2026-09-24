"""Stage 2: turn raw SWE-smith messages into steps, one per tool call."""

import ast
import json
import re
import shlex

from .io import read_json, write_json
from .models import Run, Step, TestResult
from .paths import PAIRS, PARQUET_GLOB, RUNS

OUTPUT_LIMIT = 4000
HEAD, TAIL = 2500, 1500

TEST_RUNNER = re.compile(r"\b(pytest|py\.test|tox|nox)\b|-m\s+unittest\b")
SEARCH_CMDS = {"grep", "rg", "find", "ls", "ag"}
VIEW_CMDS = {"cat", "head", "tail", "nl", "less", "sed"}
PATH_TOKEN = re.compile(r"[\w./-]+\.(?:py|pyx|pyi|cfg|toml|ini|txt|md|rst|json|ya?ml|c|h|cpp|js|ts)\b")
EDITOR_ACTIONS = {"view": "view", "create": "create", "str_replace": "edit", "insert": "edit", "undo_edit": "edit"}


def loads_loose(s):
    """JSON, or a Python repr (some fields arrive as repr strings)."""
    if not isinstance(s, str):
        return s
    try:
        return json.loads(s)
    except ValueError:
        return ast.literal_eval(s)


def text_of(content) -> str:
    content = loads_loose(content) if isinstance(content, str) and content[:1] == "[" else content
    if isinstance(content, list):
        return "\n".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
    return content or ""


def issue_of(text: str) -> str:
    m = re.search(r"<pr_description>\s*(.*?)\s*</pr_description>", text, re.S)
    return m.group(1) if m else text.strip()


def strip_testbed(path: str) -> str:
    return re.sub(r"^/testbed/?", "", path)


def main_command(command: str) -> str:
    """Drop leading `cd … &&` segments."""
    parts = [p.strip() for p in command.split("&&")]
    while len(parts) > 1 and parts[0].startswith("cd "):
        parts.pop(0)
    return " && ".join(parts)


def bash_files(command: str) -> list[str]:
    seen = []
    for token in PATH_TOKEN.findall(command):
        path = strip_testbed(token)
        if path and path not in seen:
            seen.append(path)
    return seen


def classify(tool: str, args: dict) -> tuple[str, list[str]]:
    if tool == "str_replace_editor":
        path = strip_testbed(args.get("path", ""))
        return EDITOR_ACTIONS.get(args.get("command"), "other"), [path] if path else []
    if tool == "submit":
        return "submit", []
    if tool != "bash":
        return "other", []
    command = main_command(args.get("command", ""))
    files = bash_files(command)
    if TEST_RUNNER.search(command):
        return "test", files
    try:
        first = shlex.split(command)[0] if command else ""
    except ValueError:
        first = command.split()[0] if command.split() else ""
    if first in SEARCH_CMDS:
        return "search", []
    if first in VIEW_CMDS:
        return "view", files
    return "run", files


def render_command(tool: str, args: dict) -> str:
    if tool == "bash":
        return args.get("command", "")
    if tool == "submit":
        return "submit"
    if tool == "str_replace_editor":
        head = f"{args.get('command', '')} {strip_testbed(args.get('path', ''))}".strip()
        blocks = []
        if args.get("view_range"):
            head += f" {args['view_range']}"
        if "insert_line" in args:
            head += f" at line {args['insert_line']}"
        for key, label in (("old_str", "old"), ("new_str", "new"), ("file_text", "file")):
            if args.get(key) is not None:
                blocks.append(f"--- {label}\n{args[key]}")
        return "\n".join([head, *blocks])
    return f"{tool} {json.dumps(args)}"


def parse_test_summary(output: str) -> TestResult | None:
    counts = {k: 0 for k in ("passed", "failed", "errors")}
    found = False
    for n, word in re.findall(r"(\d+) (passed|failed|errors?)\b", output):
        counts["errors" if word.startswith("error") else word] = int(n)
        found = True
    if found:
        return TestResult(**counts)
    ran = re.search(r"Ran (\d+) tests?", output)
    if ran:
        total = int(ran.group(1))
        failures = int(m.group(1)) if (m := re.search(r"failures=(\d+)", output)) else 0
        errors = int(m.group(1)) if (m := re.search(r"errors=(\d+)", output)) else 0
        return TestResult(passed=total - failures - errors, failed=failures, errors=errors)
    return None


def trim(text: str, limit: int = OUTPUT_LIMIT) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    cut = len(text) - HEAD - TAIL
    return f"{text[:HEAD]}\n… [{cut} characters trimmed] …\n{text[-TAIL:]}", True


XML_CALL = re.compile(r"<function=([\w-]+)>(.*?)</function>", re.S)
XML_PARAM = re.compile(r"<parameter=([\w-]+)>(.*?)</parameter>", re.S)


def xml_calls(text: str) -> tuple[str, list[tuple[str, dict]]]:
    """Some runs write calls inline: <function=bash><parameter=command>ls</parameter></function>."""
    calls = [(name, {k: v.strip("\n") for k, v in XML_PARAM.findall(body)}) for name, body in XML_CALL.findall(text)]
    return XML_CALL.sub("", text).strip(), calls


def native_calls(msg: dict) -> list[tuple[str, dict, str | None]]:
    calls = []
    for call in loads_loose(msg.get("tool_calls")) or []:
        fn = call.get("function", {})
        calls.append((fn.get("name", ""), loads_loose(fn.get("arguments") or "{}") or {}, call.get("id")))
    return calls


def parse_run(messages, patch: str, traj_id: str, model: str, resolved: bool) -> Run:
    messages = loads_loose(messages)
    issue = ""
    steps: list[dict] = []
    by_call_id: dict[str, dict] = {}
    pending_thought: list[str] = []
    last_calls: list[dict] = []

    def attach_output(target: dict, raw_text: str) -> None:
        output = re.sub(r"^OBSERVATION:\s*\n?", "", raw_text)
        if target["action"] == "test":
            result = parse_test_summary(output)
            target["test_result"] = result.model_dump() if result else None
        target["output"], target["truncated"] = trim(output)

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue
        if role == "user" and not issue:
            issue = issue_of(text_of(msg.get("content")))
            continue
        if role == "user":  # inline-format runs return observations as user messages
            if last_calls:
                attach_output(last_calls.pop(0), text_of(msg.get("content")))
            continue
        if role == "assistant":
            content = text_of(msg.get("content"))
            calls = native_calls(msg)
            if calls:
                thought = (msg.get("thought") or content or "").strip()
            else:
                thought, parsed = xml_calls(content)
                calls = [(name, args, None) for name, args in parsed]
            if not calls:
                if thought:
                    pending_thought.append(thought)
                continue
            last_calls = []
            for i, (tool, args, call_id) in enumerate(calls):
                action, files = classify(tool, args)
                step = {
                    "index": len(steps), "thought": "\n\n".join([*pending_thought, thought]) if i == 0 else "",
                    "tool": tool, "command": render_command(tool, args), "action": action, "files": files,
                    "output": "", "truncated": False, "test_result": None,
                }
                pending_thought = []
                steps.append(step)
                last_calls.append(step)
                if call_id:
                    by_call_id[call_id] = step
        elif role == "tool":
            ids = loads_loose(msg.get("tool_call_ids")) or []
            target = next((by_call_id[i] for i in ids if i in by_call_id), None)
            if target is None and last_calls:
                target = last_calls[0]
            if target is None:
                continue
            if target in last_calls:
                last_calls.remove(target)
            attach_output(target, text_of(msg.get("content")))

    return Run(traj_id=traj_id, model=model, resolved=resolved, issue=issue,
               steps=[Step(**s) for s in steps], patch=patch or "")


def run(args=None) -> None:
    import duckdb
    pairs = [json.loads(line) for line in PAIRS.read_text(encoding="utf-8").splitlines()]
    wanted = {t for p in pairs for t in (p["pass_traj"], p["fail_traj"])}
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE wanted(t VARCHAR)")
    con.executemany("INSERT INTO wanted VALUES (?)", [(t,) for t in sorted(wanted)])
    rows = con.execute(f"""SELECT traj_id, model, CAST(resolved AS BOOLEAN), messages, patch
                           FROM read_parquet('{PARQUET_GLOB.as_posix()}')
                           WHERE traj_id IN (SELECT t FROM wanted)""").fetchall()
    failures = []
    for traj_id, model, resolved, messages, patch in rows:
        try:
            parsed = parse_run(messages, patch, traj_id, model, resolved)
            if not parsed.steps:
                raise ValueError("no steps")
            write_json(RUNS / f"{traj_id}.json", parsed.model_dump())
        except Exception as exc:  # counted and reported, never silently dropped
            failures.append({"traj_id": traj_id, "error": f"{type(exc).__name__}: {exc}"})
    write_json(RUNS / "_failures.json", failures, indent=2)
    missing = wanted - {r[0] for r in rows}
    print(f"parsed {len(rows) - len(failures)} of {len(wanted)} runs; "
          f"{len(failures)} failed to parse, {len(missing)} missing from the dataset")


def load_run(traj_id: str) -> Run:
    return Run.model_validate(read_json(RUNS / f"{traj_id}.json"))
