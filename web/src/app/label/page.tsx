import type { Metadata } from "next";
import { LabelApp } from "@/components/LabelApp";
import { readCategories, readIndex } from "@/lib/data";

export const metadata: Metadata = {
  title: "Label mode",
  robots: { index: false, follow: false },
};

export default async function LabelPage() {
  const [index, categories] = await Promise.all([readIndex(), readCategories()]);
  const pairs = index.filter((e) => e.validation).sort((a, b) => a.pair_id.localeCompare(b.pair_id));
  return <LabelApp pairs={pairs} categories={categories} />;
}
