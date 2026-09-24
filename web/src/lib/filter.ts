import type { IndexEntry } from "@/types/data";

export type Filters = {
  failModel?: string;
  category?: string; // a category id, or "not_judged"
  repo?: string;
  query?: string;
};

export function filterPairs(entries: IndexEntry[], f: Filters): IndexEntry[] {
  const q = f.query?.trim().toLowerCase();
  return entries.filter(
    (e) =>
      (!f.failModel || e.fail_model === f.failModel) &&
      (!f.category || (f.category === "not_judged" ? e.category === null : e.category === f.category)) &&
      (!f.repo || e.repo === f.repo) &&
      (!q || e.instance_id.toLowerCase().includes(q) || e.repo.toLowerCase().includes(q)),
  );
}

export function facets(entries: IndexEntry[]) {
  const uniq = (xs: string[]) => [...new Set(xs)].sort();
  return {
    repos: uniq(entries.map((e) => e.repo)),
    failModels: uniq(entries.map((e) => e.fail_model)),
  };
}
