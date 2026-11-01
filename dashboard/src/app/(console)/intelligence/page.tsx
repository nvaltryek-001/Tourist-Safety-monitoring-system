"use client";

import Link from "next/link";
import { useState } from "react";
import { AdvisoryList } from "@/components/Advisories";
import { EmptyState, ErrorState, PageHeader, Panel, SkeletonRows, StatusBadge } from "@/components/ui";
import { humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { TouristAssessment } from "@/lib/types";

interface ZoneRisk {
  zone_id: number;
  zone_name: string;
  zone_type: string;
  entries: number;
  sos_within_zone: number;
  risk_index: number;
  explanation: string;
}

interface Report {
  summary: string;
  generated_at: string;
  limitations: string[];
}

export default function IntelligencePage() {
  const tourists = useApi<TouristAssessment[]>("/api/v1/intelligence/tourists", 60000);
  const zones = useApi<ZoneRisk[]>("/api/v1/intelligence/zones?limit=15");
  const report = useApi<Report>("/api/v1/intelligence/report");
  const [open, setOpen] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        title="AI safety intelligence"
        subtitle="Explainable, rule-based advisories computed from location history, geofence events and SOS records. Advisories prompt a human check — they are not confirmed emergencies."
      />
      {report.data && (
        <Panel className="mb-6" title="Hazard intelligence summary">
          <p className="text-sm">{report.data.summary}</p>
          <ul className="mt-3 list-disc space-y-0.5 pl-5 text-xs muted">
            {report.data.limitations.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </Panel>
      )}
      <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
        <Panel title="Tourist risk scores (last 24 h)" bodyClass="p-0">
          {tourists.loading ? <SkeletonRows /> : tourists.error ? <ErrorState message={tourists.error} onRetry={tourists.reload} /> : !tourists.data?.length ? <EmptyState title="No tourists registered" /> : (
            <ul className="divide-y hairline">
              {tourists.data.map((t) => (
                <li key={t.tourist_code}>
                  <button className="flex w-full items-center gap-4 px-4 py-3 text-left hover:bg-black/[.02]" onClick={() => setOpen(open === t.tourist_code ? null : t.tourist_code)}>
                    <div className="w-12 text-right text-lg font-semibold tabular-nums">{t.risk_score}</div>
                    <div className="h-2 flex-1 overflow-hidden rounded bg-black/[.06] dark:bg-white/10">
                      <div className="h-full rounded" style={{ width: `${t.risk_score}%`, background: t.risk_score >= 60 ? "#dc2626" : t.risk_score >= 35 ? "#ea580c" : t.risk_score >= 15 ? "#d97706" : "#15803d" }} />
                    </div>
                    <div className="w-44">
                      <p className="text-sm font-medium">{t.name}</p>
                      <p className="text-xs muted">{t.tourist_code} · {t.advisories.length} advisories</p>
                    </div>
                    <StatusBadge status={t.risk_level} />
                  </button>
                  {open === t.tourist_code && (
                    <div className="border-t hairline bg-black/[.015] px-4 py-4 dark:bg-white/[.02]">
                      <AdvisoryList advisories={t.advisories} />
                      <Link href={`/tourists/${encodeURIComponent(t.tourist_code)}`} className="mt-3 inline-block text-xs text-brand-600 hover:underline">Open tourist profile →</Link>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Zone risk ranking (last 30 days)" bodyClass="p-0">
          {zones.loading ? <SkeletonRows /> : zones.error ? <ErrorState message={zones.error} onRetry={zones.reload} /> : !zones.data?.length ? <EmptyState title="No active zones" /> : (
            <table className="w-full">
              <thead className="border-b hairline"><tr><th className="th">Zone</th><th className="th">Entries</th><th className="th">SOS</th><th className="th">Index</th></tr></thead>
              <tbody className="divide-y hairline">
                {zones.data.map((z) => (
                  <tr key={z.zone_id} title={z.explanation}>
                    <td className="td"><p className="text-sm">{z.zone_name}</p><p className="text-xs muted">{humanize(z.zone_type)}</p></td>
                    <td className="td tabular-nums">{z.entries}</td>
                    <td className="td tabular-nums">{z.sos_within_zone}</td>
                    <td className="td font-semibold tabular-nums">{z.risk_index}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="border-t hairline px-4 py-3 text-[11px] muted">Index = zone type/risk base + 5 per tourist entry + 15 per SOS raised inside the zone. Hover a row for its breakdown.</p>
        </Panel>
      </div>
    </>
  );
}
