import { describe, expect, it } from "vitest";
import { filterPairs, facets } from "@/lib/filter";
import { modelName } from "@/lib/format";
import type { IndexEntry } from "@/types/data";

const entry = (over: Partial<IndexEntry>): IndexEntry => ({
  pair_id: "p", instance_id: "o__r.1.x", repo: "o/r", pass_model: "claude-3-7-sonnet-20250219",
  fail_model: "claude-3-5-sonnet-20241022", category: null, split_step: null, fail_steps: 10,
  validation: false, ...over,
});

const ENTRIES = [
  entry({ pair_id: "a", repo: "dask/dask", instance_id: "dask__dask.1.pr_1", category: "wrong_location", split_step: 3 }),
  entry({ pair_id: "b", repo: "pandas-dev/pandas", fail_model: "gpt-4o-2024-08-06", category: "incomplete_fix", split_step: 5 }),
  entry({ pair_id: "c", repo: "dask/dask", instance_id: "dask__dask.2.lm_rewrite" }),
];

describe("filterPairs", () => {
  it("returns everything with no filters", () => {
    expect(filterPairs(ENTRIES, {}).map((e) => e.pair_id)).toEqual(["a", "b", "c"]);
  });
  it("filters by failing model, category, repo and search text", () => {
    expect(filterPairs(ENTRIES, { failModel: "gpt-4o-2024-08-06" }).map((e) => e.pair_id)).toEqual(["b"]);
    expect(filterPairs(ENTRIES, { category: "wrong_location" }).map((e) => e.pair_id)).toEqual(["a"]);
    expect(filterPairs(ENTRIES, { category: "not_judged" }).map((e) => e.pair_id)).toEqual(["c"]);
    expect(filterPairs(ENTRIES, { repo: "dask/dask" }).map((e) => e.pair_id)).toEqual(["a", "c"]);
    expect(filterPairs(ENTRIES, { query: "LM_REWRITE" }).map((e) => e.pair_id)).toEqual(["c"]);
  });
  it("combines filters", () => {
    expect(filterPairs(ENTRIES, { repo: "dask/dask", category: "wrong_location" }).map((e) => e.pair_id)).toEqual(["a"]);
  });
});

describe("facets", () => {
  it("lists sorted unique values", () => {
    const f = facets(ENTRIES);
    expect(f.repos).toEqual(["dask/dask", "pandas-dev/pandas"]);
    expect(f.failModels).toEqual(["claude-3-5-sonnet-20241022", "gpt-4o-2024-08-06"]);
  });
});

describe("modelName", () => {
  it("turns model ids into readable names", () => {
    expect(modelName("claude-3-7-sonnet-20250219")).toBe("Claude 3.7 Sonnet");
    expect(modelName("claude-3-5-sonnet-20241022")).toBe("Claude 3.5 Sonnet");
    expect(modelName("gpt-4o-2024-08-06")).toBe("GPT-4o");
    expect(modelName("something-else")).toBe("something-else");
  });
});
