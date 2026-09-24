/* Single-series charts in plain HTML: one validated hue (--chart), bars <= 24px thick with a 4px rounded
   data end, square at the baseline, hover tooltips via title, and a table view under every chart. */

export type Datum = { label: string; value: number; display?: string; hint?: string };

export function StatTile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-lg bg-surface-2 p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {note && <div className="mt-1 text-xs text-faint">{note}</div>}
    </div>
  );
}

function TableView({ data, labelHeader, valueHeader }: { data: Datum[]; labelHeader: string; valueHeader: string }) {
  return (
    <details className="text-xs text-muted">
      <summary className="cursor-pointer">Show as table</summary>
      <table className="mt-2 w-full max-w-md">
        <thead>
          <tr className="text-left">
            <th className="py-1 font-normal">{labelHeader}</th>
            <th className="py-1 text-right font-normal">{valueHeader}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.label} className="border-t border-line">
              <td className="py-1 text-ink">{d.label}</td>
              <td className="py-1 text-right tabular-nums text-ink">{d.display ?? d.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

/** Horizontal bars, sorted by the caller. `max` lets small multiples share one scale. */
export function HBars({
  data,
  max,
  labelHeader = "Category",
  valueHeader = "Value",
}: {
  data: Datum[];
  max?: number;
  labelHeader?: string;
  valueHeader?: string;
}) {
  const top = max ?? Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="space-y-2">
      <ul className="space-y-1.5">
        {data.map((d) => (
          <li
            key={d.label}
            title={d.hint ?? `${d.label}: ${d.display ?? d.value}`}
            className="group grid grid-cols-[11rem_1fr] items-center gap-3 text-sm"
          >
            <span className="truncate text-muted group-hover:text-ink">{d.label}</span>
            <span className="flex items-center gap-2">
              <span
                className="h-3.5 rounded-r bg-chart opacity-90 group-hover:opacity-100"
                style={{ width: `${(d.value / top) * 85}%`, minWidth: d.value > 0 ? 2 : 0 }}
              />
              <span className="text-xs tabular-nums text-muted">{d.display ?? d.value}</span>
            </span>
          </li>
        ))}
      </ul>
      <TableView data={data} labelHeader={labelHeader} valueHeader={valueHeader} />
    </div>
  );
}

/** Vertical columns on one baseline with a 2px gap; only the tallest column is labelled. */
export function Columns({
  data,
  labelHeader = "Bin",
  valueHeader = "Value",
  height = 140,
}: {
  data: Datum[];
  labelHeader?: string;
  valueHeader?: string;
  height?: number;
}) {
  const top = Math.max(1, ...data.map((d) => d.value));
  const peak = data.findIndex((d) => d.value === top);
  return (
    <div className="space-y-2">
      <div className="flex items-end gap-[2px] border-b border-grid" style={{ height }}>
        {data.map((d, i) => (
          <div
            key={d.label}
            title={d.hint ?? `${d.label}: ${d.display ?? d.value}`}
            className="group flex h-full flex-1 flex-col items-center justify-end"
          >
            {i === peak && d.value > 0 && (
              <span className="mb-1 text-xs tabular-nums text-muted">{d.display ?? d.value}</span>
            )}
            <div
              className="w-full max-w-6 rounded-t bg-chart opacity-90 group-hover:opacity-100"
              style={{ height: `${(d.value / top) * (height - 22)}px` }}
            />
          </div>
        ))}
      </div>
      <div className="flex gap-[2px] text-[11px] text-faint">
        {data.map((d, i) => (
          <span key={d.label} className="flex-1 text-center">
            {i === 0 || i === data.length - 1 || i === Math.floor(data.length / 2) ? d.label : ""}
          </span>
        ))}
      </div>
      <TableView data={data} labelHeader={labelHeader} valueHeader={valueHeader} />
    </div>
  );
}
