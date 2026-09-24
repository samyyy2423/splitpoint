"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { CategoryBadge } from "@/components/CategoryBadge";
import { facets, filterPairs, type Filters } from "@/lib/filter";
import { modelName, taskName } from "@/lib/format";
import type { Category, IndexEntry } from "@/types/data";

const selectClass = "rounded border border-line bg-surface px-2 py-1.5 text-sm text-ink";

export function PairTable({ entries, categories }: { entries: IndexEntry[]; categories: Category[] }) {
  const [filters, setFilters] = useState<Filters>({});
  const { repos, failModels } = useMemo(() => facets(entries), [entries]);
  const shown = useMemo(() => filterPairs(entries, filters), [entries, filters]);
  const set = (key: keyof Filters) => (value: string) => setFilters((f) => ({ ...f, [key]: value || undefined }));

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label="Search tasks"
          placeholder="Search task or repo"
          className={`${selectClass} w-56`}
          onChange={(e) => set("query")(e.target.value)}
        />
        <select aria-label="Failing model" className={selectClass} onChange={(e) => set("failModel")(e.target.value)}>
          <option value="">Any failing model</option>
          {failModels.map((m) => (
            <option key={m} value={m}>
              {modelName(m)}
            </option>
          ))}
        </select>
        <select aria-label="Failure category" className={selectClass} onChange={(e) => set("category")(e.target.value)}>
          <option value="">Any category</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
          <option value="not_judged">Not judged</option>
        </select>
        <select aria-label="Repository" className={selectClass} onChange={(e) => set("repo")(e.target.value)}>
          <option value="">Any repo</option>
          {repos.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <span className="text-sm text-faint">
          {shown.length} of {entries.length}
        </span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-line bg-surface">
        <table className="w-full text-sm">
          <thead className="border-b border-line text-left text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-normal">Task</th>
              <th className="px-3 py-2 font-normal">Repo</th>
              <th className="px-3 py-2 font-normal">Passed</th>
              <th className="px-3 py-2 font-normal">Failed</th>
              <th className="px-3 py-2 font-normal">Why it failed</th>
              <th className="px-3 py-2 text-right font-normal">Split</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.pair_id} className="border-b border-line last:border-0 hover:bg-surface-2">
                <td className="px-3 py-2">
                  <Link href={`/pair/${e.pair_id}/`} className="font-mono text-xs text-ink hover:underline">
                    {taskName(e.instance_id)}
                  </Link>
                </td>
                <td className="px-3 py-2 text-muted">{e.repo}</td>
                <td className="px-3 py-2 whitespace-nowrap text-pass">{modelName(e.pass_model)}</td>
                <td className="px-3 py-2 whitespace-nowrap text-fail">{modelName(e.fail_model)}</td>
                <td className="px-3 py-2">
                  <CategoryBadge id={e.category} categories={categories} />
                </td>
                <td className="px-3 py-2 text-right whitespace-nowrap text-muted tabular-nums">
                  {e.split_step === null ? "—" : `step ${e.split_step} of ${e.fail_steps}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
