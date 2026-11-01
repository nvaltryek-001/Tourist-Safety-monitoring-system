import { humanize } from "@/lib/format";
import type { Advisory } from "@/lib/types";
import { StatusBadge } from "./ui";

export function AdvisoryList({ advisories }: { advisories: Advisory[] }) {
  if (!advisories.length) {
    return <p className="text-sm muted">No advisories. This only means no rule fired — it is not a guarantee of safety.</p>;
  }
  return (
    <ul className="space-y-3">
      {advisories.map((a, i) => (
        <li key={`${a.code}-${i}`} className="rounded border hairline p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide">{humanize(a.code)}</p>
            <StatusBadge status={a.risk_level} />
          </div>
          <p className="mt-1.5 text-sm">{a.reason}</p>
          <p className="mt-1 text-xs muted">Recommended: {a.recommended_action}</p>
          {Object.keys(a.evidence).length > 0 && (
            <details className="mt-1.5">
              <summary className="cursor-pointer text-xs text-brand-600">Evidence</summary>
              <pre className="mt-1 overflow-x-auto rounded bg-black/[.04] p-2 font-mono text-[11px] dark:bg-white/[.05]">
                {JSON.stringify(a.evidence, null, 2)}
              </pre>
            </details>
          )}
          <p className="mt-1.5 text-[10px] uppercase tracking-wider muted">{a.kind === "AI_ADVISORY" ? "AI advisory — not a confirmed emergency" : a.kind}</p>
        </li>
      ))}
    </ul>
  );
}
