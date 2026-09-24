"""The data contract between pipeline stages and the site. The site's types are generated from
SiteData's JSON Schema, so change a model here and both sides move together."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .categories import Category
from .io import write_json

CategoryId = Literal[
    "wrong_location", "incomplete_fix", "broke_other_behaviour", "misread_issue",
    "never_verified", "gave_up_or_ran_out", "tool_or_syntax_trouble", "other",
]
Action = Literal["view", "create", "edit", "search", "test", "run", "submit", "other"]
Rule = Literal["foreign_edit", "lost_thread", "unfixed_test_failure", "fallback"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TestResult(Model):
    __test__ = False  # not a pytest class

    passed: int
    failed: int
    errors: int


class Step(Model):
    index: int
    thought: str
    tool: str
    command: str
    action: Action
    files: list[str]
    output: str
    truncated: bool
    test_result: TestResult | None


class Run(Model):
    traj_id: str
    model: str
    resolved: bool
    issue: str
    steps: list[Step]
    patch: str


class PairMeta(Model):
    pair_id: str
    instance_id: str
    repo: str
    pass_traj: str
    pass_model: str
    fail_traj: str
    fail_model: str
    cross_model: bool


class Row(Model):
    p: int | None
    f: int | None
    match: bool


class Candidate(Model):
    step: int
    rule: Rule


class Alignment(Model):
    pair_id: str
    rows: list[Row]
    candidates: list[Candidate]


class Verdict(Model):
    split_step: int = Field(ge=0)
    reason: str = Field(min_length=1)
    category: CategoryId
    confidence: float = Field(ge=0, le=1)


class JudgeRecord(Model):
    pair_id: str
    status: Literal["judged", "not_judged"]
    verdict: Verdict | None
    attempts: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    errors: list[str]


class PairDoc(Model):
    pair_id: str
    instance_id: str
    repo: str
    issue: str
    pass_run: Run
    fail_run: Run
    rows: list[Row]
    candidates: list[Candidate]
    verdict: Verdict | None
    validation: bool


class IndexEntry(Model):
    pair_id: str
    instance_id: str
    repo: str
    pass_model: str
    fail_model: str
    category: CategoryId | None
    split_step: int | None
    fail_steps: int
    validation: bool


class Validation(Model):
    n: int
    category_kappa: float | None
    category_agreement: float | None
    split_exact: float | None
    split_within_2: float | None
    baseline_split_exact: float | None
    baseline_split_within_2: float | None


class Findings(Model):
    n_pairs: int
    n_judged: int
    categories: dict[str, int]
    by_model: dict[str, dict[str, int]]
    split_fraction_hist: list[int]
    median_split_fraction: float | None
    validation: Validation | None
    judge_input_tokens: int
    judge_output_tokens: int
    judge_cost_usd: float


class SiteData(Model):
    """Schema wrapper only: one of each file the site reads."""
    index: list[IndexEntry]
    pair: PairDoc
    findings: Findings
    category_defs: list[Category]


def write_schema(path: Path) -> None:
    write_json(path, SiteData.model_json_schema(), indent=2)
