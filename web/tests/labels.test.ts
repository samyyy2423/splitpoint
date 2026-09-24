import { beforeEach, describe, expect, it } from "vitest";
import { exportLabels, loadLabels, saveLabel, STORAGE_KEY } from "@/lib/labels";

describe("labels", () => {
  beforeEach(() => localStorage.clear());

  it("round-trips through localStorage and overwrites per pair", () => {
    saveLabel({ pair_id: "b", split_step: 4, category: "wrong_location" });
    saveLabel({ pair_id: "a", split_step: 2, category: "other" });
    saveLabel({ pair_id: "b", split_step: 5, category: "incomplete_fix" });
    expect(loadLabels()).toEqual({
      a: { pair_id: "a", split_step: 2, category: "other" },
      b: { pair_id: "b", split_step: 5, category: "incomplete_fix" },
    });
  });

  it("exports the format the pipeline's validate stage reads", () => {
    saveLabel({ pair_id: "b", split_step: 4, category: "wrong_location" });
    saveLabel({ pair_id: "a", split_step: 2, category: "other" });
    expect(exportLabels(loadLabels())).toEqual({
      version: 1,
      labels: [
        { pair_id: "a", split_step: 2, category: "other" },
        { pair_id: "b", split_step: 4, category: "wrong_location" },
      ],
    });
  });

  it("ignores corrupt storage", () => {
    localStorage.setItem(STORAGE_KEY, "{not json");
    expect(loadLabels()).toEqual({});
  });
});
