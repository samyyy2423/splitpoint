# Splitpoint

**Where did the failing agent run go wrong?** Splitpoint takes coding tasks that one agent run solved
and another failed, lines the two runs up step by step, and marks the step where the failing run split
off, with a one-line reason and a failure category from an LLM judge. The judge is scored against my
own blind labels, and the site reports how often it agrees.

<!-- RESULTS -->
_Results are published after the judge run; see the Findings page._
<!-- /RESULTS -->

## What's in it

- **300 pass/fail pairs** from [SWE-smith trajectories](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories)
  (MIT): the same task, one run passed the hidden tests, one failed. 292 pairs have the pass and fail
  from different models (Claude 3.7 Sonnet, Claude 3.5 Sonnet, GPT-4o).
- **Compare page:** both runs side by side, aligned step by step. Matching stretches fold away; the split
  step is highlighted with the judge's reason, category and confidence. Every step expands to the
  agent's reasoning, command and output, and both final patches are shown.
- **Findings page:** failure categories overall and per model, where runs split, judge-vs-human
  agreement, and what the judge run cost.
- **Label mode** (`/label/`): walks 50 held-out pairs with the judge's answer hidden, so the agreement
  numbers come from blind labels.

## How it works

```
SWE-smith (HF parquet) → pick → steps → align → judge → validate → export → Next.js static site
```

1. **pick** chooses one passing and one failing run for each of the 843 tasks that have both, preferring
   different models, with a fixed seed.
2. **steps** turns each run into one step per tool call (reasoning, command, output), handling both the
   native tool-call and the inline `<function=…>` formats in the dataset, and classifies each step
   (view, edit, test, run, …).
3. **align** runs Needleman–Wunsch over action tokens like `edit:src/crop.py`, then proposes candidate
   split steps from three rules: first edit to a file the passing run never touched, the point after
   which the runs stop matching, and the first failing test run that is never fixed.
4. **judge** sends each pair to Claude Haiku 4.5 through the Message Batches API with a forced
   `record_verdict` tool: the issue, one-line summaries of both runs, full detail around each candidate,
   and both patches. Answers are schema-checked (step in range, known category, ≤ 40-word reason) with one
   retry. The CLI prints a cost estimate and spends nothing without `--yes`.
5. **validate** scores the judge against the blind labels: Cohen's κ on the category, split step exact
   and within ±2 steps, and the same split metrics for the alignment alone (no LLM) as a baseline.
6. **export** writes the site's JSON and checks every file against a JSON Schema generated from the
   Pydantic models. The site's TypeScript types are generated from that same schema.

## Reproduce

Requirements: Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 20+ with pnpm, an Anthropic API key
for the judge step.

```bash
cd pipeline
uv run python -m splitpoint pick      # downloads the tool split once (~1.1 GB) into data/raw
uv run python -m splitpoint steps
uv run python -m splitpoint align
uv run python -m splitpoint judge     # prints the estimate; add --yes to submit the batch
uv run python -m splitpoint export
```

Label the validation pairs at `/label/`, export `labels.json`, then:

```bash
uv run python -m splitpoint validate --labels labels.json
uv run python -m splitpoint export
```

Put the key in `pipeline/.env` as `ANTHROPIC_API_KEY=…`; the file is git-ignored.

Site:

```bash
cd web
pnpm install
pnpm dev          # http://localhost:3000
pnpm build        # static export in out/
```

## Tests

```bash
cd pipeline && uv run pytest          # parsing, alignment rules, judge checks, κ, export schema
cd web && pnpm test && pnpm e2e       # components and label export; Playwright smoke test on the build
```

The pipeline tests never call the API; the judge is tested with saved good and bad answers.

## Stack

Python (DuckDB, Pydantic, Anthropic SDK, pytest) · Next.js static export, TypeScript, Tailwind, Vitest,
Playwright.
