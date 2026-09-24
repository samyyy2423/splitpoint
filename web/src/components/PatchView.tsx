function lineClass(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("diff --git")) return "text-muted";
  if (line.startsWith("+")) return "text-pass";
  if (line.startsWith("-")) return "text-fail";
  if (line.startsWith("@@")) return "text-accent";
  return "";
}

function Patch({ title, patch }: { title: string; patch: string }) {
  return (
    <div className="min-w-0 space-y-1">
      <div className="text-xs text-muted">{title}</div>
      {patch.trim() ? (
        <pre className="max-h-[32rem] overflow-auto rounded-lg border border-line bg-surface p-3 font-mono text-xs leading-relaxed">
          {patch.split("\n").map((line, i) => (
            <div key={i} className={lineClass(line)}>
              {line || " "}
            </div>
          ))}
        </pre>
      ) : (
        <p className="rounded-lg border border-line bg-surface p-3 text-xs text-faint">No changes submitted.</p>
      )}
    </div>
  );
}

export function PatchView({ pass, fail }: { pass: string; fail: string }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-medium">Final changes</h2>
      <div className="grid gap-3 md:grid-cols-2">
        <Patch title="Passing run" patch={pass} />
        <Patch title="Failing run" patch={fail} />
      </div>
    </section>
  );
}
