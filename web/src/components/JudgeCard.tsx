import { CategoryBadge } from "@/components/CategoryBadge";
import type { Candidate, Category, Verdict } from "@/types/data";

export const RULE_LABEL: Record<string, string> = {
  foreign_edit: "first edit to a file the passing run never touched",
  lost_thread: "first step after the runs stopped matching",
  unfixed_test_failure: "first failing test run that was never fixed",
  fallback: "first step that differs",
};

export function JudgeCard({
  verdict,
  candidates,
  categories,
  failSteps,
}: {
  verdict: Verdict | null;
  candidates: Candidate[];
  categories: Category[];
  failSteps: number;
}) {
  const others = candidates.filter((c) => c.step !== verdict?.split_step);
  return (
    <div className="rounded-lg border border-fail-line bg-surface p-3 text-sm" data-testid="judge-card">
      {verdict ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-fail">
              Split at step {verdict.split_step} of {failSteps}
            </span>
            <CategoryBadge id={verdict.category} categories={categories} />
            <span className="text-xs text-faint">judge confidence {Math.round(verdict.confidence * 100)}%</span>
          </div>
          <p className="leading-relaxed">{verdict.reason}</p>
        </div>
      ) : (
        <p className="text-muted">
          Not judged yet. The dashed steps are where the alignment thinks the runs split.
        </p>
      )}
      {others.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-muted">
          {others.map((c) => (
            <li key={c.step}>
              Alignment candidate: step {c.step}, {RULE_LABEL[c.rule]}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
