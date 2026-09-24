import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Category, Findings, IndexEntry } from "@/types/data";

const DATA = path.join(process.cwd(), "public", "data");

async function readJson<T>(name: string): Promise<T> {
  return JSON.parse(await readFile(path.join(DATA, name), "utf8")) as T;
}

export const readIndex = () => readJson<IndexEntry[]>("index.json");
export const readFindings = () => readJson<Findings>("findings.json");
export const readCategories = () => readJson<Category[]>("categories.json");
