"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { API_URL, api } from "@/lib/api";
import { humanize } from "@/lib/format";
import { useApi, useLayer } from "@/lib/hooks";
import { SafetyMap } from "./Map";
import { Badge, Button, EmptyState, Panel, SkeletonRows, Stat, StatusBadge, useToast } from "./ui";

interface ManifestRow {
  dataset_id: string;
  kind: string;
  title: string;
  publisher: string;
  source_url: string;
  download_date: string;
  status: string;
  licence: string;
  records: string;
  file: string;
  notes: string;
}

interface RiskRow {
  name: string;
  risk_index: number | null;
  risk_level: string | null;
  crime_total: number | null;
  heavy_rain_days: number | null;
  police_stations: number | null;
}

interface Analysis {
  generated_at: string;
  facilities?: {
    facility_counts?: Record<string, number>;
    attractions?: number;
    attraction_to_police_km?: { median: number | null; p90: number | null };
    attraction_to_hospital_km?: { median: number | null };
    attractions_over_15km_from_police?: number;
    top_gaps?: { attraction: string; district: string | null; nearest_police_km: number }[];
  };
  crime?: { years?: number[]; state_totals?: Record<string, number>; top_districts?: { district: string; total: number; year: number }[]; narrative?: string };
  weather?: { state_mean_monthly_rain_mm?: Record<string, number> };
  district_risk?: RiskRow[];
  limitations?: string[];
  ml_evaluation?: string;
}

const LEVEL_COLOR: Record<string, string> = { HIGH: "#dc2626", MEDIUM: "#d97706", LOW: "#15803d" };

export function OpenDatasets() {
  const info = useApi<{ available: boolean; layers: Record<string, boolean>; manifest: ManifestRow[] }>("/api/v1/datasets");
  const analysis = useApi<Analysis>("/api/v1/datasets/analysis");
  const [showRisk, setShowRisk] = useState(false);
  const riskLayer = useLayer(showRisk ? "district_risk" : null);
  const toast = useToast();
  const [importing, setImporting] = useState<string | null>(null);

  async function importLayer(layer: "natural_hazards" | "protected_areas") {
    setImporting(layer);
    try {
      const dry = await api<{ created: number; duplicates: number; invalid: number }>(`/api/v1/zones/import-dataset?layer=${layer}`, { method: "POST" });
      if (!dry.created) {
        toast(`Nothing new to import (${dry.duplicates} already present, ${dry.invalid} invalid)`, "info");
        return;
      }
      if (!window.confirm(`Create ${dry.created} inactive "pending review" zones from ${humanize(layer)}? They will not alert tourists until you activate them.`)) return;
      const r = await api<{ created: number }>(`/api/v1/zones/import-dataset?layer=${layer}&dry_run=false`, { method: "POST" });
      toast(`Created ${r.created} pending-review zones — review them on the Safety zones page`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Import failed", "error");
    } finally {
      setImporting(null);
    }
  }

  if (info.loading) return <Panel title="Open datasets"><SkeletonRows rows={4} /></Panel>;
  if (!info.data?.available) {
    return (
      <Panel title="Open datasets">
        <EmptyState title="No processed datasets found" hint="Pull the latest code: datasets/application_data/ is produced by the Datasets GitHub workflow." />
      </Panel>
    );
  }
  const a = analysis.data;
  const raw = info.data.manifest.filter((m) => m.kind === "raw");
  const rain = Object.entries(a?.weather?.state_mean_monthly_rain_mm ?? {}).map(([month, mm]) => ({ month, mm }));
  const topCrime = (a?.crime?.top_districts ?? []).slice(0, 12).map((r) => ({ name: r.district, total: r.total }));

  return (
    <div className="mt-6 space-y-6">
      <div className="stagger grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="Sources downloaded" value={raw.filter((r) => r.status === "DOWNLOADED").length} hint={`${raw.filter((r) => r.status !== "DOWNLOADED").length} unavailable`} />
        <Stat label="Police stations (OSM)" value={a?.facilities?.facility_counts?.POLICE ?? 0} />
        <Stat label="Hospitals (OSM)" value={a?.facilities?.facility_counts?.HOSPITAL ?? 0} />
        <Stat label="Tourist attractions" value={a?.facilities?.attractions ?? 0} />
        <Stat label="Median attraction → police" value={a?.facilities?.attraction_to_police_km?.median != null ? `${a.facilities.attraction_to_police_km.median} km` : "—"} />
        <Stat label="Attractions > 15 km from police" value={a?.facilities?.attractions_over_15km_from_police ?? 0} tone="caution" />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="District crime totals (Karnataka State Police)">
          {!topCrime.length ? <EmptyState title="Crime tables not processed yet" /> : (
            <>
              <div className="h-72">
                <ResponsiveContainer>
                  <BarChart data={topCrime} layout="vertical" margin={{ left: 12, right: 16 }}>
                    <CartesianGrid horizontal={false} strokeOpacity={0.15} />
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="total" fill="#dc2626" radius={[0, 3, 3, 0]} barSize={14} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              {a?.crime?.narrative && <p className="mt-2 text-xs muted">{a.crime.narrative}</p>}
            </>
          )}
        </Panel>
        <Panel title="Mean monthly rainfall, Karnataka (ERA5 via Open-Meteo)">
          {!rain.length ? <EmptyState title="Weather data not processed yet" /> : (
            <div className="h-72">
              <ResponsiveContainer>
                <BarChart data={rain} margin={{ left: -12 }}>
                  <CartesianGrid vertical={false} strokeOpacity={0.15} />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={2} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="mm" fill="#0f766a" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Explainable district risk index"
        action={<label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={showRisk} onChange={(e) => setShowRisk(e.target.checked)} /> Show on map</label>}
      >
        {showRisk && (
          <div className="mb-4">
            <SafetyMap height="420px" zoom={7} center={[14.6, 76.1]}
              layers={[{ id: "risk", label: "District risk index", color: "#dc2626", data: riskLayer }]} />
          </div>
        )}
        {!a?.district_risk?.length ? <EmptyState title="Risk index not generated yet" /> : (
          <div className="max-h-96 overflow-auto">
            <table className="w-full min-w-[620px]">
              <thead className="sticky top-0 border-b hairline bg-[var(--panel)]"><tr><th className="th">District</th><th className="th">Index</th><th className="th">Crime total</th><th className="th">Heavy-rain days</th><th className="th">Police (OSM)</th></tr></thead>
              <tbody className="divide-y hairline">
                {a.district_risk.map((r) => (
                  <tr key={r.name}>
                    <td className="td">{r.name}</td>
                    <td className="td">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 overflow-hidden rounded bg-black/[.06] dark:bg-white/10">
                          <div className="h-full rounded" style={{ width: `${r.risk_index ?? 0}%`, background: LEVEL_COLOR[r.risk_level ?? ""] ?? "#64748b" }} />
                        </div>
                        <span className="text-xs tabular-nums">{r.risk_index ?? "—"}</span>
                        {r.risk_level && <StatusBadge status={r.risk_level} />}
                      </div>
                    </td>
                    <td className="td tabular-nums">{r.crime_total ?? "—"}</td>
                    <td className="td tabular-nums">{r.heavy_rain_days ?? "—"}</td>
                    <td className="td tabular-nums">{r.police_stations ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-[11px] muted">Registered crimes 55 % · heavy-rain days 30 % · heat days 15 %. OSM police counts are shown for coverage only. An analysis aid, not a crime prediction.</p>
      </Panel>

      <Panel title="Use open data as safety zones">
        <p className="text-sm muted">Turn OpenStreetMap features into zones for review. They are created <b>inactive</b> with status <b>pending review</b> and never alert tourists until an admin verifies and activates each one.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button disabled={!info.data.layers.natural_hazards} loading={importing === "natural_hazards"} onClick={() => importLayer("natural_hazards")}>Waterfalls & cliffs → review zones</Button>
          <Button disabled={!info.data.layers.protected_areas} loading={importing === "protected_areas"} onClick={() => importLayer("protected_areas")}>Protected areas → review zones</Button>
        </div>
      </Panel>

      <Panel title="Dataset manifest" bodyClass="p-0">
        <div className="max-h-[480px] overflow-auto">
          <table className="w-full min-w-[860px]">
            <thead className="sticky top-0 border-b hairline bg-[var(--panel)]"><tr><th className="th">Dataset</th><th className="th">Publisher</th><th className="th">Status</th><th className="th">Licence</th><th className="th">Records</th><th className="th">Downloaded</th></tr></thead>
            <tbody className="divide-y hairline">
              {raw.map((m) => (
                <tr key={m.dataset_id}>
                  <td className="td"><p className="text-sm font-medium">{m.title}</p><p className="font-mono text-[11px] muted">{m.file || m.source_url}</p></td>
                  <td className="td text-xs">{m.publisher}</td>
                  <td className="td">{m.status === "DOWNLOADED" ? <Badge tone="safe">Downloaded</Badge> : <Badge tone="caution" className="max-w-[220px] whitespace-normal">{humanize(m.status)}</Badge>}{m.notes && m.status !== "DOWNLOADED" && <p className="mt-1 text-[11px] muted">{m.notes.slice(0, 160)}</p>}</td>
                  <td className="td text-xs">{m.licence}</td>
                  <td className="td text-xs tabular-nums">{m.records}</td>
                  <td className="td text-xs">{m.download_date?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap gap-3 border-t hairline px-4 py-3 text-xs">
          {Object.entries(info.data.layers).filter(([, ok]) => ok).map(([name]) => (
            <a key={name} className="text-brand-600 hover:underline" href={`${API_URL}/api/v1/datasets/layers/${name}`} target="_blank" rel="noreferrer">⬇ {humanize(name)}.geojson</a>
          ))}
        </div>
      </Panel>

      {a?.limitations && (
        <Panel title="Limitations">
          <ul className="list-disc space-y-1 pl-5 text-sm muted">{a.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
          {a.ml_evaluation && <p className="mt-3 text-sm"><b>Machine learning:</b> {a.ml_evaluation}</p>}
        </Panel>
      )}
    </div>
  );
}
