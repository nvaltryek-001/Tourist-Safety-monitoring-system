"use client";

import { humanize } from "@/lib/format";

export function LiveBadge({ status }: { status: string }) {
  const color = status === "live" ? "bg-emerald-500" : status === "reconnecting" || status === "connecting" ? "bg-amber-500" : "bg-slate-400";
  return (
    <span className="inline-flex items-center gap-2 rounded border hairline bg-[var(--panel)] px-3 py-1.5 text-xs">
      <span className={`h-2 w-2 rounded-full ${color} ${status === "live" ? "animate-pulse" : ""}`} />
      {status === "live" ? "Live updates on" : humanize(status)}
    </span>
  );
}
