"use client";

import { Fragment, useMemo, useState } from "react";
import { JudgeCard } from "@/components/JudgeCard";
import { PatchView } from "@/components/PatchView";
import { StepCell, type Tone } from "@/components/StepCell";
import { modelName, taskName } from "@/lib/format";
import { groupRows } from "@/lib/rows";
import type { Category, PairDoc, Row } from "@/types/data";

export function CompareView({
  doc,
  categories,
  blind = false,
}: {
  doc: PairDoc;
  categories: Category[];
  /** Label mode: hide the judge's verdict and the alignment's candidates. */
  blind?: boolean;
}) {
  const split = blind ? null : (doc.verdict?.split_step ?? null);
  const candidateSteps = useMemo(() => new Set(doc.candidates.map((c) => c.step)), [doc.candidates]);
  const items = useMemo(() => groupRows(doc.rows, split), [doc.rows, split]);
  const [openStrips, setOpenStrips] = useState<Set<string>>(new Set());
  const failSteps = doc.fail_run.steps.length;

  const toggle = (key: string) =>
    setOpenStrips((s) => {
      const next = new Set(s);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const failTone = (row: Row, isSplit: boolean): Tone => {
    if (isSplit) return "split";
    if (row.match) return "matched";
    if (!blind && split === null && row.f !== null && candidateSteps.has(row.f)) return "candidate";
    return "normal";
  };

  const renderRow = (row: Row, isSplit: boolean) => (
    <>
      <StepCell step={row.p === null ? null : doc.pass_run.steps[row.p]} tone={row.match ? "matched" : "normal"} />
      <StepCell step={row.f === null ? null : doc.fail_run.steps[row.f]} tone={failTone(row, isSplit)} />
    </>
  );

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <div>
          <h1 className="font-mono text-xl tracking-tight">{taskName(doc.instance_id)}</h1>
          <p className="text-sm text-muted">
            {doc.repo} · <span className="font-mono text-xs">{doc.instance_id}</span>
          </p>
        </div>
        {blind ? null : doc.verdict ? (
          <a href="#split" className="block rounded-lg border border-fail-line bg-fail-bg px-3 py-2 text-sm">
            <span className="font-medium text-fail">
              Split at step {doc.verdict.split_step} of {failSteps}:
            </span>{" "}
            {doc.verdict.reason}
          </a>
        ) : (
          <JudgeCard verdict={null} candidates={doc.candidates} categories={categories} failSteps={failSteps} />
        )}
        <details className="rounded-lg border border-line bg-surface text-sm">
          <summary className="cursor-pointer px-3 py-2 text-muted">The task (issue text)</summary>
          <pre className="max-h-96 overflow-auto border-t border-line px-3 py-2 font-sans leading-relaxed whitespace-pre-wrap">
            {doc.issue}
          </pre>
        </details>
      </header>

      <section className="space-y-1.5" aria-label="Aligned runs">
        <div className="sticky top-0 z-10 grid grid-cols-2 gap-3 bg-bg py-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="rounded bg-pass-bg px-2 py-0.5 text-xs text-pass">passed</span>
            {modelName(doc.pass_run.model)}
            <span className="text-xs text-faint">{doc.pass_run.steps.length} steps</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-fail-bg px-2 py-0.5 text-xs text-fail">failed</span>
            {modelName(doc.fail_run.model)}
            <span className="text-xs text-faint">{failSteps} steps</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
          {items.map((item) => {
            if (item.kind === "strip") {
              const open = openStrips.has(item.key);
              const first = item.rows[0].f;
              const last = item.rows[item.rows.length - 1].f;
              return (
                <Fragment key={item.key}>
                  <button
                    type="button"
                    onClick={() => toggle(item.key)}
                    aria-expanded={open}
                    className="col-span-2 rounded border border-line bg-surface-2 px-3 py-1 text-left text-xs text-muted hover:text-ink"
                  >
                    {open ? "Hide" : "Show"} {item.rows.length} matching steps
                    <span className="text-faint">
                      {" "}
                      (failing run steps {first}–{last})
                    </span>
                  </button>
                  {open && item.rows.map((row, k) => <Fragment key={`${item.key}-${k}`}>{renderRow(row, false)}</Fragment>)}
                </Fragment>
              );
            }
            return (
              <Fragment key={item.key}>
                {renderRow(item.row, item.isSplit)}
                {item.isSplit && (
                  <div id="split" className="col-span-2 scroll-mt-16 py-1">
                    <JudgeCard
                      verdict={doc.verdict}
                      candidates={doc.candidates}
                      categories={categories}
                      failSteps={failSteps}
                    />
                  </div>
                )}
              </Fragment>
            );
          })}
        </div>
      </section>

      <PatchView pass={doc.pass_run.patch} fail={doc.fail_run.patch} />
    </div>
  );
}
