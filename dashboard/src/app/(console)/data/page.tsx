"use client";

import { Upload } from "lucide-react";
import { useState } from "react";
import { OpenDatasets } from "@/components/OpenDatasets";
import { Badge, Button, ErrorState, Field, PageHeader, Panel, SkeletonRows, Stat, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";

interface ZoneAudit {
  total_zones: number;
  active_zones: number;
  by_type: Record<string, number>;
  synthetic_zones: number;
  college_demo_zones: number;
  college_demo_zone_rows: { id: number; name: string; radius_meters: number; zone_type: string; active: boolean }[];
  college_demo_radii_found: number[];
  college_demo_radius_note: string | null;
  college_demo_overlaps: { zone_a: { name: string }; zone_b: { name: string }; centre_distance_m: number; combined_radius_m: number }[];
  invalid_records: { id: number; name: string }[];
  duplicates: { id: number; duplicate_of: number; kind: string }[];
  overlap_pairs_sample: unknown[];
}

interface DataAudit {
  schema_version: number;
  table_counts: Record<string, number>;
  tourists: { total: number; with_login_access: number; access_rows_without_tourist: number; access_emails_gmail: number; invalid_coordinates: number };
  sos: { total: number; orphaned: number };
  zones: ZoneAudit;
}

interface ImportResult {
  dry_run: boolean;
  summary: { created: number; duplicates: number; invalid: number };
  created: { name: string; zone_type: string; radius_meters: number }[];
  duplicates: { name: string }[];
  invalid: { name: string; problems: string[] }[];
}

export default function DataPage() {
  const audit = useApi<DataAudit>("/api/v1/admin/data-audit");
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [activate, setActivate] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);

  async function upload(dryRun: boolean) {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    setBusy(true);
    try {
      const r = await api<ImportResult>(`/api/v1/zones/import?dry_run=${dryRun}&activate=${activate}`, { method: "POST", body: form });
      setResult(r);
      if (!dryRun) {
        toast(`Imported ${r.summary.created} zone(s)`);
        void audit.reload();
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "Import failed", "error");
    } finally {
      setBusy(false);
    }
  }

  const z = audit.data?.zones;
  return (
    <>
      <PageHeader title="Dataset management" subtitle="Open-data sources and analysis, a read-only audit of the live database, and validated GeoJSON/KML zone import. No personal data is shown." />
      <OpenDatasets />
      <h2 className="mb-3 mt-10 text-sm font-semibold uppercase tracking-wider muted">Live database audit</h2>
      {audit.loading ? <SkeletonRows rows={6} /> : audit.error || !audit.data || !z ? <Panel><ErrorState message={audit.error ?? "Unavailable"} onRetry={audit.reload} /></Panel> : (
        <>
          <div className="stagger grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
            <Stat label="Tourists" value={audit.data.tourists.total} hint={`${audit.data.tourists.with_login_access} with Gmail login`} />
            <Stat label="Safety zones" value={z.total_zones} hint={`${z.active_zones} active`} />
            <Stat label="Synthetic zones" value={z.synthetic_zones} hint="DEMO-KA test data" />
            <Stat label="College demo zones" value={z.college_demo_zones} hint={z.college_demo_radii_found.length ? `radius ${z.college_demo_radii_found.join(", ")} m` : undefined} />
            <Stat label="SOS records" value={audit.data.sos.total} hint={`${audit.data.sos.orphaned} orphaned`} />
            <Stat label="Schema version" value={`v${audit.data.schema_version}`} />
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <Panel title="Zone reconciliation">
              <dl className="space-y-2 text-sm">
                <Line k="Total zone records" v={z.total_zones} />
                <Line k="Synthetic DEMO-KA records (inside the total)" v={z.synthetic_zones} />
                <Line k="College demo zones (inside the total)" v={z.college_demo_zones} />
                <Line k="Other zones" v={z.total_zones - z.synthetic_zones - z.college_demo_zones} />
                <Line k="Invalid coordinates / radius" v={z.invalid_records.length} warn={z.invalid_records.length > 0} />
                <Line k="Duplicate name/coordinates" v={z.duplicates.length} warn={z.duplicates.length > 0} />
                {Object.entries(z.by_type).map(([t, n]) => <Line key={t} k={`Type: ${humanize(t)}`} v={n} />)}
              </dl>
              {z.college_demo_radius_note && <p className="mt-4 rounded bg-amber-50 px-3 py-2 text-xs text-amber-900">{z.college_demo_radius_note}</p>}
            </Panel>
            <Panel title="College demo zones" bodyClass="p-0">
              <table className="w-full">
                <thead className="border-b hairline"><tr><th className="th">ID</th><th className="th">Name</th><th className="th">Radius</th><th className="th">State</th></tr></thead>
                <tbody className="divide-y hairline">
                  {z.college_demo_zone_rows.map((r) => (
                    <tr key={r.id}><td className="td font-mono text-xs">{r.id}</td><td className="td">{r.name}</td><td className="td">{r.radius_meters} m</td><td className="td">{r.active ? <Badge tone="safe">Active</Badge> : <Badge tone="neutral">Inactive</Badge>}</td></tr>
                  ))}
                  {!z.college_demo_zone_rows.length && <tr><td className="td muted" colSpan={4}>No zones named “College Demo Zone …” in this database.</td></tr>}
                </tbody>
              </table>
              <div className="border-t hairline p-4 text-sm">
                <p className="font-medium">Overlaps between demo zones: {z.college_demo_overlaps.length}</p>
                <ul className="mt-1 space-y-0.5 text-xs muted">
                  {z.college_demo_overlaps.slice(0, 12).map((o, i) => (
                    <li key={i}>{o.zone_a.name} ↔ {o.zone_b.name}: centres {o.centre_distance_m} m apart (radii sum {o.combined_radius_m} m)</li>
                  ))}
                </ul>
              </div>
            </Panel>
          </div>
        </>
      )}

      <Panel title="Import zones (GeoJSON or KML)" className="mt-6">
        <div className="flex flex-wrap items-end gap-4">
          <Field label="File (.geojson, .json, .kml · max 5 MB)">
            <input type="file" accept=".geojson,.json,.kml" className="field" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setResult(null); }} />
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={activate} onChange={(e) => setActivate(e.target.checked)} /> Activate alerts for imported zones
          </label>
          <Button disabled={!file} loading={busy} onClick={() => upload(true)}>Validate (dry run)</Button>
          <Button variant="primary" disabled={!file || !result?.dry_run || !result.summary.created} loading={busy} onClick={() => upload(false)}>
            <Upload className="h-4 w-4" /> Import {result?.dry_run ? result.summary.created : ""} zone(s)
          </Button>
        </div>
        <p className="mt-3 text-xs muted">Imports never overwrite or delete existing zones. Duplicates (same name and coordinates) are skipped. Imported zones are marked “pending review”.</p>
        {result && (
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <ResultList title={`New (${result.summary.created})`} items={result.created.map((c) => `${c.name} · ${humanize(c.zone_type)} · ${Math.round(c.radius_meters)} m`)} />
            <ResultList title={`Duplicates skipped (${result.summary.duplicates})`} items={result.duplicates.map((d) => d.name)} />
            <ResultList title={`Invalid (${result.summary.invalid})`} items={result.invalid.map((d) => `${d.name}: ${d.problems.join("; ")}`)} />
          </div>
        )}
      </Panel>
    </>
  );
}

function Line({ k, v, warn }: { k: string; v: number; warn?: boolean }) {
  return <div className="flex justify-between gap-4"><dt className="muted">{k}</dt><dd className={warn ? "font-semibold text-orange-700" : "font-medium"}>{v}</dd></div>;
}

function ResultList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded border hairline p-3">
      <p className="text-xs font-semibold uppercase tracking-wide">{title}</p>
      <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto text-xs">{items.length ? items.map((i, n) => <li key={n}>{i}</li>) : <li className="muted">None</li>}</ul>
    </div>
  );
}
