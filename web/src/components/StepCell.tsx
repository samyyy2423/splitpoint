"use client";

import { useState } from "react";
import type { Step } from "@/types/data";

export type Tone = "normal" | "matched" | "split" | "candidate";

const TONE: Record<Tone, string> = {
  normal: "border-line bg-surface",
  matched: "border-line bg-surface-2 text-muted",
  split: "border-fail-line bg-fail-bg ring-1 ring-fail-line",
  candidate: "border-dashed border-fail-line bg-surface",
};

const ACTION_COLOR: Record<string, string> = {
  edit: "text-cmd",
  create: "text-cmd",
  test: "text-think",
  run: "text-think",
  submit: "text-pass",
};

export function stepTarget(step: Step): string {
  if (step.files.length) return step.files.join(", ");
  if (step.tool === "str_replace_editor") return "repository root";
  const first = step.command.split("\n")[0].replace(/^cd \S+ && /, "");
  return first.length > 90 ? `${first.slice(0, 90)}…` : first;
}

function Section({ label, children, mono = true }: { label: string; children: string; mono?: boolean }) {
  if (!children.trim()) return null;
  return (
    <div className="space-y-1">
      <div className="text-[11px] uppercase tracking-wide text-faint">{label}</div>
      <pre
        className={`max-h-80 overflow-auto rounded bg-surface-2 p-2 text-xs leading-relaxed whitespace-pre-wrap break-words ${
          mono ? "font-mono" : "font-sans"
        }`}
      >
        {children}
      </pre>
    </div>
  );
}

export function StepCell({ step, tone = "normal" }: { step: Step | null; tone?: Tone }) {
  const [open, setOpen] = useState(false);
  if (!step) return <div aria-hidden className="min-h-9 rounded border border-dashed border-line/60" />;
  return (
    <div className={`rounded border text-sm ${TONE[tone]}`} data-step={step.index} data-tone={tone}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full min-w-0 items-baseline gap-2 px-2.5 py-1.5 text-left"
      >
        <span className="w-6 shrink-0 text-right text-xs text-faint tabular-nums">{step.index}</span>
        <span className={`shrink-0 text-xs ${ACTION_COLOR[step.action] ?? "text-muted"}`}>{step.action}</span>
        <span className="min-w-0 truncate font-mono text-xs">{stepTarget(step)}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-line px-2.5 py-2">
          <Section label="Reasoning" mono={false}>
            {step.thought}
          </Section>
          <Section label="Command">{step.command}</Section>
          <Section label={step.truncated ? "Output (trimmed)" : "Output"}>{step.output}</Section>
        </div>
      )}
    </div>
  );
}
