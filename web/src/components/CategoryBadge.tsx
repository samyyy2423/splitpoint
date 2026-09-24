import type { Category } from "@/types/data";

export function CategoryBadge({ id, categories }: { id: string | null; categories: Category[] }) {
  if (!id) {
    return <span className="rounded border border-line px-2 py-0.5 text-xs text-faint">not judged</span>;
  }
  const cat = categories.find((c) => c.id === id);
  return (
    <span
      title={cat?.definition}
      className="rounded bg-accent-bg px-2 py-0.5 text-xs whitespace-nowrap text-accent"
    >
      {cat?.label ?? id}
    </span>
  );
}
