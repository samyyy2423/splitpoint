/* Generated from pipeline/src/splitpoint/models.py via src/types/schema.json. Do not edit; run pnpm gen:types. */

/**
 * Schema wrapper only: one of each file the site reads.
 */
export interface SiteData {
  index: IndexEntry[];
  pair: PairDoc;
  findings: Findings;
  category_defs: Category[];
}
export interface IndexEntry {
  pair_id: string;
  instance_id: string;
  repo: string;
  pass_model: string;
  fail_model: string;
  category:
    | (
        | "wrong_location"
        | "incomplete_fix"
        | "broke_other_behaviour"
        | "misread_issue"
        | "never_verified"
        | "gave_up_or_ran_out"
        | "tool_or_syntax_trouble"
        | "other"
      )
    | null;
  split_step: number | null;
  fail_steps: number;
  validation: boolean;
}
export interface PairDoc {
  pair_id: string;
  instance_id: string;
  repo: string;
  issue: string;
  pass_run: Run;
  fail_run: Run;
  rows: Row[];
  candidates: Candidate[];
  verdict: Verdict | null;
  validation: boolean;
}
export interface Run {
  traj_id: string;
  model: string;
  resolved: boolean;
  issue: string;
  steps: Step[];
  patch: string;
}
export interface Step {
  index: number;
  thought: string;
  tool: string;
  command: string;
  action: "view" | "create" | "edit" | "search" | "test" | "run" | "submit" | "other";
  files: string[];
  output: string;
  truncated: boolean;
  test_result: TestResult | null;
}
export interface TestResult {
  passed: number;
  failed: number;
  errors: number;
}
export interface Row {
  p: number | null;
  f: number | null;
  match: boolean;
}
export interface Candidate {
  step: number;
  rule: "foreign_edit" | "lost_thread" | "unfixed_test_failure" | "fallback";
}
export interface Verdict {
  split_step: number;
  reason: string;
  category:
    | "wrong_location"
    | "incomplete_fix"
    | "broke_other_behaviour"
    | "misread_issue"
    | "never_verified"
    | "gave_up_or_ran_out"
    | "tool_or_syntax_trouble"
    | "other";
  confidence: number;
}
export interface Findings {
  n_pairs: number;
  n_judged: number;
  categories: {
    [k: string]: number;
  };
  by_model: {
    [k: string]: {
      [k: string]: number;
    };
  };
  split_fraction_hist: number[];
  median_split_fraction: number | null;
  validation: Validation | null;
  judge_input_tokens: number;
  judge_output_tokens: number;
  judge_cost_usd: number;
}
export interface Validation {
  n: number;
  category_kappa: number | null;
  category_agreement: number | null;
  split_exact: number | null;
  split_within_2: number | null;
  baseline_split_exact: number | null;
  baseline_split_within_2: number | null;
}
export interface Category {
  id: string;
  label: string;
  definition: string;
  [k: string]: unknown;
}
