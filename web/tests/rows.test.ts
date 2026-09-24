import { describe, expect, it } from "vitest";
import { groupRows } from "@/lib/rows";
import type { Row } from "@/types/data";

const m = (i: number): Row => ({ p: i, f: i, match: true });
const gapF = (f: number): Row => ({ p: null, f, match: false });
const kinds = (items: ReturnType<typeof groupRows>) =>
  items.map((it) => (it.kind === "strip" ? `strip${it.rows.length}` : it.isSplit ? "SPLIT" : "row"));

describe("groupRows", () => {
  it("collapses runs of three or more matching rows", () => {
    const rows = [m(0), m(1), m(2), m(3), gapF(4), m(5), m(6)];
    expect(kinds(groupRows(rows, 4))).toEqual(["strip4", "SPLIT", "row", "row"]);
  });

  it("never hides the split step inside a strip", () => {
    const rows = [m(0), m(1), m(2), m(3), m(4)];
    expect(kinds(groupRows(rows, 2))).toEqual(["row", "row", "SPLIT", "row", "row"]);
  });

  it("keeps short matching runs as rows", () => {
    expect(kinds(groupRows([m(0), m(1), gapF(2)], null))).toEqual(["row", "row", "row"]);
  });

  it("gives strips stable keys", () => {
    const items = groupRows([m(0), m(1), m(2)], null);
    expect(items[0].kind === "strip" && items[0].key).toBe("strip-0");
  });
});
