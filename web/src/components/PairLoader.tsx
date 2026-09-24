"use client";

import { useEffect, useState } from "react";
import { CompareView } from "@/components/CompareView";
import type { Category, PairDoc } from "@/types/data";

export async function fetchPair(id: string): Promise<PairDoc> {
  const res = await fetch(`/data/pairs/${id}.json`);
  if (!res.ok) throw new Error(`Couldn't load pair ${id} (${res.status})`);
  return (await res.json()) as PairDoc;
}

export function PairLoader({ id, categories }: { id: string; categories: Category[] }) {
  const [doc, setDoc] = useState<PairDoc | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    fetchPair(id).then(
      (d) => live && setDoc(d),
      (e: Error) => live && setError(e.message),
    );
    return () => {
      live = false;
    };
  }, [id]);

  if (error) return <p className="text-fail">{error}. Try reloading the page.</p>;
  if (!doc) return <p className="text-muted">Loading both runs…</p>;
  return <CompareView doc={doc} categories={categories} />;
}
