"use client";

import { useEffect, useMemo, useState } from "react";
import { CompareView } from "@/components/CompareView";
import { fetchPair } from "@/components/PairLoader";
import { stepTarget } from "@/components/StepCell";
import { downloadJson, exportLabels, loadLabels, saveLabel, type LabelMap } from "@/lib/labels";
import type { Category, IndexEntry, PairDoc } from "@/types/data";

export function LabelApp({ pairs, categories }: { pairs: IndexEntry[]; categories: Category[] }) {
  const [labels, setLabels] = useState<LabelMap>({});
  const [i, setI] = useState(0);
  const [doc, setDoc] = useState<PairDoc | null>(null);
  const [step, setStep] = useState<number | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const current = pairs[i];

  useEffect(() => {
    const stored = loadLabels();
    setLabels(stored);
    const firstOpen = pairs.findIndex((p) => !stored[p.pair_id]);
    setI(firstOpen === -1 ? 0 : firstOpen);
  }, [pairs]);

  useEffect(() => {
    if (!current) return;
    let live = true;
    setDoc(null);
    setError(null);
    const saved = loadLabels()[current.pair_id];
    setStep(saved?.split_step ?? null);
    setCategory(saved?.category ?? null);
    fetchPair(current.pair_id).then(
      (d) => live && setDoc(d),
      (e: Error) => live && setError(e.message),
    );
    return () => {
      live = false;
    };
  }, [current]);

  const done = useMemo(() => pairs.filter((p) => labels[p.pair_id]).length, [pairs, labels]);

  if (!current) return <p className="text-muted">No validation pairs in this export.</p>;

  const save = () => {
    if (step === null || category === null) {
      setError("Pick a split step and a category first.");
      return;
    }
    setLabels(saveLabel({ pair_id: current.pair_id, split_step: step, category }));
    setError(null);
    if (i < pairs.length - 1) setI(i + 1);
  };

  return (
    <div className="space-y-6">
      <div className="sticky top-0 z-20 -mx-5 space-y-3 border-b border-line bg-bg px-5 py-3">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-medium">
            Pair {i + 1} of {pairs.length}
          </span>
          <span className="text-muted">
            {done} of {pairs.length} labelled
          </span>
          <button type="button" className="rounded border border-line px-2 py-1" onClick={() => setI(Math.max(0, i - 1))}>
            Previous
          </button>
          <button
            type="button"
            className="rounded border border-line px-2 py-1"
            onClick={() => setI(Math.min(pairs.length - 1, i + 1))}
          >
            Next
          </button>
          <button
            type="button"
            className="ml-auto rounded border border-line px-2 py-1"
            onClick={() => downloadJson(exportLabels(loadLabels()), "labels.json")}
          >
            Export labels ({done})
          </button>
        </div>

        {doc && (
          <div className="grid gap-3 lg:grid-cols-[1fr_2fr]">
            <label className="space-y-1 text-sm">
              <span className="text-muted">Where did the failing run go wrong?</span>
              <select
                aria-label="Split step"
                className="w-full rounded border border-line bg-surface px-2 py-1.5"
                value={step ?? ""}
                onChange={(e) => setStep(e.target.value === "" ? null : Number(e.target.value))}
              >
                <option value="">Pick a step</option>
                {doc.fail_run.steps.map((s) => (
                  <option key={s.index} value={s.index}>
                    {s.index} {s.action} {stepTarget(s)}
                  </option>
                ))}
              </select>
            </label>
            <fieldset className="space-y-1 text-sm">
              <legend className="text-muted">Why?</legend>
              <div className="flex flex-wrap gap-1.5">
                {categories.map((c) => (
                  <label
                    key={c.id}
                    title={c.definition}
                    className={`cursor-pointer rounded border px-2 py-1 ${
                      category === c.id ? "border-accent bg-accent-bg text-accent" : "border-line"
                    }`}
                  >
                    <input
                      type="radio"
                      name="category"
                      value={c.id}
                      checked={category === c.id}
                      onChange={() => setCategory(c.id)}
                      className="sr-only"
                    />
                    {c.label}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
        )}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={save}
            className="rounded bg-ink px-3 py-1.5 text-sm text-bg disabled:opacity-50"
            disabled={!doc}
          >
            Save and next
          </button>
          {labels[current.pair_id] && <span className="text-xs text-pass">Saved</span>}
          {error && <span className="text-xs text-fail">{error}</span>}
        </div>
      </div>

      {doc ? (
        <CompareView key={doc.pair_id} doc={doc} categories={categories} blind />
      ) : (
        !error && <p className="text-muted">Loading both runs…</p>
      )}
    </div>
  );
}
