import type { Metadata } from "next";
import { Columns, HBars, StatTile, type Datum } from "@/components/charts";
import { readCategories, readFindings } from "@/lib/data";
import { modelName, percent } from "@/lib/format";
import type { Category, Findings } from "@/types/data";

export const metadata: Metadata = { title: "Findings" };

function categoryData(counts: Record<string, number>, categories: Category[], asShare: boolean): Datum[] {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  return categories
    .map((c) => {
      const n = counts[c.id] ?? 0;
      const share = total ? n / total : 0;
      return {
        label: c.label,
        value: asShare ? share : n,
        display: asShare ? percent(share) : String(n),
        hint: `${c.label}: ${n} of ${total} (${percent(share)}). ${c.definition}`,
      };
    })
    .sort((a, b) => b.value - a.value);
}

function Headline({ findings, categories }: { findings: Findings; categories: Category[] }) {
  const [topId, topN] = Object.entries(findings.categories).sort((a, b) => b[1] - a[1])[0] ?? [];
  const top = categories.find((c) => c.id === topId);
  return (
    <p className="max-w-3xl text-lg leading-relaxed">
      Across {findings.n_judged} judged pairs, the most common reason a run failed was{" "}
      <span className="font-medium">{top?.label.toLowerCase()}</span> ({topN} of {findings.n_judged},{" "}
      {percent((topN ?? 0) / Math.max(findings.n_judged, 1))}). Failing runs typically went wrong{" "}
      {percent(findings.median_split_fraction)} of the way through.
    </p>
  );
}

export default async function FindingsPage() {
  const [findings, categories] = await Promise.all([readFindings(), readCategories()]);
  if (findings.n_judged === 0) {
    return (
      <div className="max-w-3xl space-y-3">
        <h1 className="text-2xl font-medium tracking-tight">Findings</h1>
        <p className="text-muted">The judge hasn&apos;t run yet, so there&apos;s nothing to report.</p>
      </div>
    );
  }
  const v = findings.validation;
  const models = Object.entries(findings.by_model).sort((a, b) => a[0].localeCompare(b[0]));
  const sharedMax = Math.max(
    0.01,
    ...models.flatMap(([, counts]) => categoryData(counts, categories, true).map((d) => d.value)),
  );
  const hist: Datum[] = findings.split_fraction_hist.map((n, i) => ({
    label: `${i * 10}%`,
    value: n,
    hint: `Split ${i * 10}–${i * 10 + 10}% of the way through: ${n} pairs`,
  }));

  return (
    <div className="space-y-12">
      <section className="space-y-3">
        <h1 className="text-2xl font-medium tracking-tight">Findings</h1>
        <Headline findings={findings} categories={categories} />
      </section>

      <section className="space-y-4">
        <h2 className="text-base font-medium">Can the judge be trusted?</h2>
        {v && v.n > 0 ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <StatTile
                label="Same failure category as my label"
                value={percent(v.category_agreement)}
                note={`Cohen's κ ${v.category_kappa?.toFixed(2) ?? "—"} over ${v.n} pairs`}
              />
              <StatTile label="Split step within 2 of mine" value={percent(v.split_within_2)} note={`exact: ${percent(v.split_exact)}`} />
              <StatTile
                label="Alignment alone, within 2"
                value={percent(v.baseline_split_within_2)}
                note={`exact: ${percent(v.baseline_split_exact)}; no LLM`}
              />
              <StatTile
                label="Judge cost"
                value={`$${findings.judge_cost_usd.toFixed(2)}`}
                note={`${findings.n_judged} pairs, Claude Haiku 4.5`}
              />
            </div>
            <p className="max-w-3xl text-sm text-muted">
              I labelled {v.n} pairs myself without seeing the judge&apos;s answer. &ldquo;Alignment alone&rdquo; takes the
              alignment&apos;s first candidate step with no LLM involved, which shows what the judge adds.
            </p>
          </>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Validation" value="Pending" note="Human labels not scored yet" />
            <StatTile
              label="Judge cost"
              value={`$${findings.judge_cost_usd.toFixed(2)}`}
              note={`${findings.n_judged} pairs, Claude Haiku 4.5`}
            />
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-medium">Why the failing runs failed</h2>
        <p className="text-sm text-muted">Pairs per failure category, all models.</p>
        <HBars data={categoryData(findings.categories, categories, false)} valueHeader="Pairs" />
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-medium">By the model that failed</h2>
        <p className="text-sm text-muted">Share of each model&apos;s failed runs, on one shared scale.</p>
        <div className="grid gap-8 lg:grid-cols-3">
          {models.map(([model, counts]) => {
            const n = Object.values(counts).reduce((a, b) => a + b, 0);
            return (
              <div key={model} className="space-y-2">
                <h3 className="text-sm">
                  {modelName(model)} <span className="text-faint">· {n} failed runs</span>
                </h3>
                <HBars data={categoryData(counts, categories, true)} max={sharedMax} valueHeader="Share" />
              </div>
            );
          })}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-medium">Where runs split</h2>
        <p className="text-sm text-muted">
          How far through the failing run the split step falls, as a share of its steps.
        </p>
        <div className="max-w-2xl">
          <Columns data={hist} labelHeader="Split position" valueHeader="Pairs" />
        </div>
      </section>
    </div>
  );
}
