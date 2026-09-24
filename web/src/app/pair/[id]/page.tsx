import type { Metadata } from "next";
import Link from "next/link";
import { PairLoader } from "@/components/PairLoader";
import { readCategories, readIndex } from "@/lib/data";
import { taskName } from "@/lib/format";

export const dynamicParams = false;

export async function generateStaticParams() {
  return (await readIndex()).map((e) => ({ id: e.pair_id }));
}

export async function generateMetadata({ params }: PageProps<"/pair/[id]">): Promise<Metadata> {
  const { id } = await params;
  const entry = (await readIndex()).find((e) => e.pair_id === id);
  return { title: entry ? `${taskName(entry.instance_id)} (${entry.repo})` : "Pair" };
}

export default async function PairPage({ params }: PageProps<"/pair/[id]">) {
  const { id } = await params;
  const categories = await readCategories();
  return (
    <div className="space-y-4">
      <Link href="/" className="text-sm text-muted hover:text-ink">
        ← All pairs
      </Link>
      <PairLoader id={id} categories={categories} />
    </div>
  );
}
