export const STORAGE_KEY = "splitpoint.labels.v1";

export type Label = { pair_id: string; split_step: number; category: string };
export type LabelMap = Record<string, Label>;

export function loadLabels(storage: Storage = localStorage): LabelMap {
  try {
    const parsed = JSON.parse(storage.getItem(STORAGE_KEY) ?? "{}");
    return parsed && typeof parsed === "object" ? (parsed as LabelMap) : {};
  } catch {
    return {};
  }
}

export function saveLabel(label: Label, storage: Storage = localStorage): LabelMap {
  const next = { ...loadLabels(storage), [label.pair_id]: label };
  storage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

/** The file `python -m splitpoint validate --labels labels.json` reads. */
export function exportLabels(labels: LabelMap) {
  return {
    version: 1,
    labels: Object.values(labels)
      .sort((a, b) => a.pair_id.localeCompare(b.pair_id))
      .map(({ pair_id, split_step, category }) => ({ pair_id, split_step, category })),
  };
}

export function downloadJson(data: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}
