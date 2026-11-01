"use client";

import { Download, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { MapLegend, SafetyMap } from "@/components/Map";
import { Badge, Button, EmptyState, ErrorState, Field, Modal, PageHeader, Panel, SkeletonRows, StatusBadge, useToast } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { coords, humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Zone } from "@/lib/types";

const TYPES = ["RESTRICTED", "HIGH_RISK", "CAUTION", "SAFE"];
const RISKS = ["", "LOW", "MEDIUM", "HIGH"];

interface Draft {
  id?: number;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  zone_type: string;
  risk_level: string;
  description: string;
  active: boolean;
}

const EMPTY: Draft = { name: "", latitude: 13.1665, longitude: 77.5611, radius_meters: 50, zone_type: "RESTRICTED", risk_level: "", description: "", active: true };

export default function ZonesPage() {
  const toast = useToast();
  const { session } = useAuth();
  const zones = useApi<Zone[]>("/api/v1/zones");
  const [search, setSearch] = useState("");
  const [type, setType] = useState("");
  const [kind, setKind] = useState<"all" | "real" | "synthetic" | "college">("all");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const [deleting, setDeleting] = useState<Zone | null>(null);
  const [confirmName, setConfirmName] = useState("");
  const [busy, setBusy] = useState(false);

  const filtered = useMemo(
    () =>
      (zones.data ?? []).filter((z) => {
        if (search && !`${z.name} ${z.description ?? ""}`.toLowerCase().includes(search.toLowerCase())) return false;
        if (type && z.zone_type !== type) return false;
        if (kind === "real" && (z.synthetic || z.college_demo)) return false;
        if (kind === "synthetic" && !z.synthetic) return false;
        if (kind === "college" && !z.college_demo) return false;
        return true;
      }),
    [zones.data, search, type, kind],
  );

  async function save() {
    if (!draft) return;
    setBusy(true);
    const body = { ...draft, risk_level: draft.risk_level || null, description: draft.description || null };
    try {
      if (draft.id) await api(`/api/v1/zones/${draft.id}`, { method: "PATCH", body });
      else await api("/api/v1/zones", { method: "POST", body });
      toast(draft.id ? "Zone updated" : "Zone created");
      setDraft(null);
      void zones.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function remove(permanent: boolean) {
    if (!deleting) return;
    setBusy(true);
    try {
      await api(`/api/v1/zones/${deleting.id}?confirm_name=${encodeURIComponent(confirmName)}&permanent=${permanent}`, { method: "DELETE" });
      toast(permanent ? "Zone permanently deleted" : "Zone deactivated");
      setDeleting(null);
      setConfirmName("");
      void zones.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Delete failed", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Safety zones"
        subtitle={`${zones.data?.length ?? "…"} zones. Purple zones are synthetic test data and must not be treated as real hazards.`}
        actions={
          <>
            <a href={`${API_URL}/api/v1/zones/export?format=geojson`}><Button><Download className="h-4 w-4" /> GeoJSON</Button></a>
            <a href={`${API_URL}/api/v1/zones/export?format=kml`}><Button><Download className="h-4 w-4" /> KML</Button></a>
            <Button variant="primary" onClick={() => setDraft({ ...EMPTY })}><Plus className="h-4 w-4" /> New zone</Button>
          </>
        }
      />
      <div className="grid gap-6 2xl:grid-cols-[1fr_1fr]">
        <Panel bodyClass="p-3">
          <SafetyMap
            zones={filtered}
            focus={focus}
            draft={draft}
            height="560px"
            onMapClick={(lat, lon) => draft && setDraft({ ...draft, latitude: Number(lat.toFixed(6)), longitude: Number(lon.toFixed(6)) })}
          />
          <div className="mt-3"><MapLegend /></div>
          {draft && <p className="mt-2 text-xs text-brand-700">Editing: click the map to move the zone centre.</p>}
        </Panel>

        <div className="space-y-6">
        {draft && (
          <Panel title={draft.id ? `Edit zone #${draft.id}` : "New safety zone"}>
            {draft && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2"><Field label="Name"><input className="field" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></Field></div>
            <Field label="Latitude"><input className="field" type="number" step="0.000001" value={draft.latitude} onChange={(e) => setDraft({ ...draft, latitude: Number(e.target.value) })} /></Field>
            <Field label="Longitude"><input className="field" type="number" step="0.000001" value={draft.longitude} onChange={(e) => setDraft({ ...draft, longitude: Number(e.target.value) })} /></Field>
            <Field label="Radius (metres)"><input className="field" type="number" min={1} value={draft.radius_meters} onChange={(e) => setDraft({ ...draft, radius_meters: Number(e.target.value) })} /></Field>
            <Field label="Type"><select className="field" value={draft.zone_type} onChange={(e) => setDraft({ ...draft, zone_type: e.target.value })}>{TYPES.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}</select></Field>
            <Field label="Risk level"><select className="field" value={draft.risk_level} onChange={(e) => setDraft({ ...draft, risk_level: e.target.value })}>{RISKS.map((r) => <option key={r} value={r}>{r ? humanize(r) : "Not set"}</option>)}</select></Field>
            <Field label="Status"><select className="field" value={draft.active ? "1" : "0"} onChange={(e) => setDraft({ ...draft, active: e.target.value === "1" })}><option value="1">Active (alerts on)</option><option value="0">Inactive</option></select></Field>
            <div className="sm:col-span-2"><Field label="Description"><textarea className="field" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} /></Field></div>
            <p className="text-xs muted sm:col-span-2">Click the map to move the centre. Polygon zones can be imported on the Dataset page.</p>
            <div className="flex justify-end gap-2 sm:col-span-2"><Button onClick={() => setDraft(null)}>Cancel</Button><Button variant="primary" loading={busy} onClick={save}>Save zone</Button></div>
          </div>
        )}
          </Panel>
        )}
        <Panel bodyClass="p-0">
          <div className="flex flex-wrap gap-2 border-b hairline p-3">
            <input className="field h-9 w-56" placeholder="Search zones…" value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="field h-9 w-40" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">All types</option>
              {TYPES.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
            </select>
            <select className="field h-9 w-44" value={kind} onChange={(e) => setKind(e.target.value as typeof kind)}>
              <option value="all">All sources</option>
              <option value="real">Non-demo zones</option>
              <option value="college">College demo zones</option>
              <option value="synthetic">Synthetic (DEMO-KA)</option>
            </select>
            <span className="self-center text-xs muted">{filtered.length} shown</span>
          </div>
          {zones.loading ? <SkeletonRows /> : zones.error ? <ErrorState message={zones.error} onRetry={zones.reload} /> : !filtered.length ? <EmptyState title="No zones match" /> : (
            <div className="max-h-[560px] overflow-auto">
              <table className="w-full min-w-[640px]">
                <thead className="sticky top-0 border-b hairline bg-[var(--panel)]">
                  <tr><th className="th">Zone</th><th className="th">Type</th><th className="th">Radius</th><th className="th">State</th><th className="th" /></tr>
                </thead>
                <tbody className="divide-y hairline">
                  {filtered.map((z) => (
                    <tr key={z.id}>
                      <td className="td">
                        <button className="text-left font-medium hover:text-brand-600" onClick={() => setFocus([z.latitude, z.longitude])}>{z.name}</button>
                        <p className="font-mono text-[11px] muted">#{z.id} · {coords(z.latitude, z.longitude)}{z.geometry ? " · polygon" : ""}</p>
                        <div className="mt-1 flex gap-1">
                          {z.synthetic && <Badge tone="info" className="!bg-violet-50 !text-violet-800">Synthetic</Badge>}
                          {z.college_demo && <Badge tone="neutral">College demo</Badge>}
                          {z.verification_status === "PENDING_REVIEW" && <Badge tone="caution">Pending review</Badge>}
                        </div>
                      </td>
                      <td className="td"><StatusBadge status={z.zone_type} />{z.risk_level && <p className="mt-1 text-xs muted">{humanize(z.risk_level)} risk</p>}</td>
                      <td className="td text-xs">{Math.round(z.radius_meters)} m</td>
                      <td className="td">{z.active ? <Badge tone="safe">Active</Badge> : <Badge tone="neutral">Inactive</Badge>}</td>
                      <td className="td whitespace-nowrap text-right">
                        <Button size="sm" variant="ghost" onClick={() => { setFocus([z.latitude, z.longitude]); setDraft({ id: z.id, name: z.name, latitude: z.latitude, longitude: z.longitude, radius_meters: z.radius_meters, zone_type: z.zone_type, risk_level: z.risk_level ?? "", description: z.description ?? "", active: z.active }); }}>Edit</Button>
                        <Button size="sm" variant="ghost" className="text-red-700" onClick={() => setDeleting(z)}>Remove</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
        </div>
      </div>

      <Modal
        open={!!deleting}
        title="Remove zone"
        onClose={() => { setDeleting(null); setConfirmName(""); }}
        footer={
          <>
            <Button onClick={() => setDeleting(null)}>Cancel</Button>
            {session?.user.role === "SUPER_ADMIN" && <Button variant="danger" disabled={confirmName !== deleting?.name} loading={busy} onClick={() => remove(true)}>Delete permanently</Button>}
            <Button variant="primary" disabled={confirmName !== deleting?.name} loading={busy} onClick={() => remove(false)}>Deactivate</Button>
          </>
        }
      >
        <p className="text-sm">Deactivating keeps the record but stops alerts. Permanent deletion is limited to super admins and is audit-logged.</p>
        <Field label={`Type the zone name to confirm: ${deleting?.name ?? ""}`}>
          <input className="field mt-2" value={confirmName} onChange={(e) => setConfirmName(e.target.value)} />
        </Field>
      </Modal>
    </>
  );
}
