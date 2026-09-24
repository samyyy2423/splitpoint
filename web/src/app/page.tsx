import { PairTable } from "@/components/PairTable";
import { readCategories, readIndex } from "@/lib/data";

export default async function Home() {
  const [index, categories] = await Promise.all([readIndex(), readCategories()]);
  const judged = index.filter((e) => e.category !== null).length;
  const cross = index.filter((e) => e.pass_model !== e.fail_model).length;
  return (
    <div className="space-y-8">
      <section className="max-w-3xl space-y-3">
        <h1 className="text-2xl font-medium tracking-tight">Where did the failing run go wrong?</h1>
        <p className="text-muted leading-relaxed">
          Each pair is one coding task attempted twice: one agent run passed the hidden tests, the other failed.
          Splitpoint lines the two runs up step by step and marks where the failing run split off, with a reason
          and a failure category from an LLM judge.
        </p>
        <p className="text-sm text-faint">
          {index.length} pairs · {cross} with the pass and fail from different models · {judged} judged
        </p>
      </section>
      <PairTable entries={index} categories={categories} />
    </div>
  );
}
