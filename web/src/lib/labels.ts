export const STORAGE_KEY = "splitpoint.labels.v1";

export type Label = { pair_id: string; split_step: number; category: string };
export type LabelMap = Record<string, Label>;

export const LABELS_EVENT = "splitpoint-labels";

export function parseLabels(raw: string | null): LabelMap {
  try {
    const parsed = JSON.parse(raw ?? "{}");
    return parsed && typeof parsed === "object" ? (parsed as LabelMap) : {};
  } catch {
    return {};
  }
}

export function loadLabels(storage: Storage = localStorage): LabelMap {
  return parseLabels(storage.getItem(STORAGE_KEY));
}

export function saveLabel(label: Label, storage: Storage = localStorage): LabelMap {
  const next = { ...loadLabels(storage), [label.pair_id]: label };
  storage.setItem(STORAGE_KEY, JSON.stringify(next));
  if (typeof window !== "undefined") window.dispatchEvent(new Event(LABELS_EVENT));
  return next;
}

/** For useSyncExternalStore: re-read when this tab saves or another tab changes storage. */
export function subscribeLabels(onChange: () => void): () => void {
  window.addEventListener(LABELS_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(LABELS_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
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
