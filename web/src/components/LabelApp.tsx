"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { CompareView } from "@/components/CompareView";
import { fetchPair } from "@/components/PairLoader";
import { stepTarget } from "@/components/StepCell";
import {
  downloadJson,
  exportLabels,
  type Label,
  loadLabels,
  parseLabels,
  saveLabel,
  STORAGE_KEY,
  subscribeLabels,
} from "@/lib/labels";
import type { Category, IndexEntry, PairDoc } from "@/types/data";

const button = "rounded border border-line px-2 py-1";

export function LabelApp({ pairs, categories }: { pairs: IndexEntry[]; categories: Category[] }) {
  // null during the static prerender and hydration; the stored JSON once running in the browser.
  const raw = useSyncExternalStore(subscribeLabels, () => localStorage.getItem(STORAGE_KEY) ?? "{}", () => null);
  const labels = useMemo(() => parseLabels(raw), [raw]);
  const [chosen, setChosen] = useState<number | null>(null);

  const firstOpen = Math.max(0, pairs.findIndex((p) => !labels[p.pair_id]));
  const i = chosen ?? firstOpen;
  const current = pairs[i];
  const done = pairs.filter((p) => labels[p.pair_id]).length;

  if (!current) return <p className="text-muted">No validation pairs in this export.</p>;
  if (raw === null) return <p className="text-muted">Loading your labels…</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="font-medium">
          Pair {i + 1} of {pairs.length}
        </span>
        <span className="text-muted">
          {done} of {pairs.length} labelled
        </span>
        <button type="button" className={button} onClick={() => setChosen(Math.max(0, i - 1))}>
          Previous
        </button>
        <button type="button" className={button} onClick={() => setChosen(Math.min(pairs.length - 1, i + 1))}>
          Next
        </button>
        <button
          type="button"
          className={`${button} ml-auto`}
          onClick={() => downloadJson(exportLabels(loadLabels()), "labels.json")}
        >
          Export labels ({done})
        </button>
      </div>
      <PairLabeler
        key={current.pair_id}
        entry={current}
        categories={categories}
        saved={labels[current.pair_id]}
        onSaved={() => setChosen(Math.min(pairs.length - 1, i + 1))}
      />
    </div>
  );
}

function PairLabeler({
  entry,
  categories,
  saved,
  onSaved,
}: {
  entry: IndexEntry;
  categories: Category[];
  saved: Label | undefined;
  onSaved: () => void;
}) {
  const [doc, setDoc] = useState<PairDoc | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [step, setStep] = useState<number | null>(saved?.split_step ?? null);
  const [category, setCategory] = useState<string | null>(saved?.category ?? null);

  useEffect(() => {
    let live = true;
    fetchPair(entry.pair_id).then(
      (d) => live && setDoc(d),
      (e: Error) => live && setLoadError(e.message),
    );
    return () => {
      live = false;
    };
  }, [entry.pair_id]);

  const save = () => {
    if (step === null || category === null) {
      setFormError("Pick a split step and a category first.");
      return;
    }
    saveLabel({ pair_id: entry.pair_id, split_step: step, category });
    onSaved();
  };

  if (loadError) return <p className="text-fail">{loadError}. Try reloading the page.</p>;
  if (!doc) return <p className="text-muted">Loading both runs…</p>;

  return (
    <div className="space-y-6">
      <div className="sticky top-0 z-20 -mx-5 space-y-3 border-b border-line bg-bg px-5 py-3">
        <div className="grid gap-3 lg:grid-cols-[1fr_2fr]">
          <label className="space-y-1 text-sm">
            <span className="text-muted">Where did the failing run go wrong?</span>
            <select
              aria-label="Split step"
              className="w-full rounded border border-line bg-surface px-2 py-1.5"
              value={step ?? ""}
              onChange={(e) => {
                setStep(e.target.value === "" ? null : Number(e.target.value));
                setFormError(null);
              }}
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
                    onChange={() => {
                      setCategory(c.id);
                      setFormError(null);
                    }}
                    className="sr-only"
                  />
                  {c.label}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
        <div className="flex items-center gap-3">
          <button type="button" onClick={save} className="rounded bg-ink px-3 py-1.5 text-sm text-bg">
            Save and next
          </button>
          {saved && <span className="text-xs text-pass">Saved</span>}
          {formError && <span className="text-xs text-fail">{formError}</span>}
        </div>
      </div>
      <CompareView doc={doc} categories={categories} blind />
    </div>
  );
}
