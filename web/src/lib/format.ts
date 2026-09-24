const MODEL_NAMES: Record<string, string> = {
  "claude-3-7-sonnet-20250219": "Claude 3.7 Sonnet",
  "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
  "gpt-4o-2024-08-06": "GPT-4o",
};

export function modelName(id: string): string {
  return MODEL_NAMES[id] ?? id;
}

/** "dask__dask.5f61e423.pr_8685" -> "pr_8685" (the bug id within the repo). */
export function taskName(instanceId: string): string {
  const parts = instanceId.split(".");
  return parts.length > 2 ? parts.slice(2).join(".") : instanceId;
}

export function percent(x: number | null | undefined, digits = 0): string {
  return x === null || x === undefined ? "—" : `${(x * 100).toFixed(digits)}%`;
}
