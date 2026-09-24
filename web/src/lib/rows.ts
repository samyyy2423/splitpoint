import type { Row } from "@/types/data";

export type DisplayItem =
  | { kind: "row"; key: string; row: Row; isSplit: boolean }
  | { kind: "strip"; key: string; rows: Row[] };

/** Fold runs of `minRun`+ matching rows into one strip, except around the split step. */
export function groupRows(rows: Row[], splitStep: number | null, minRun = 3): DisplayItem[] {
  const items: DisplayItem[] = [];
  let run: { start: number; rows: Row[] } | null = null;

  const flush = () => {
    if (!run) return;
    if (run.rows.length >= minRun) {
      items.push({ kind: "strip", key: `strip-${run.start}`, rows: run.rows });
    } else {
      run.rows.forEach((row, k) => items.push({ kind: "row", key: `row-${run!.start + k}`, row, isSplit: false }));
    }
    run = null;
  };

  rows.forEach((row, i) => {
    const isSplit = splitStep !== null && row.f === splitStep;
    if (row.match && !isSplit) {
      run ??= { start: i, rows: [] };
      run.rows.push(row);
      return;
    }
    flush();
    items.push({ kind: "row", key: `row-${i}`, row, isSplit });
  });
  flush();
  return items;
}
