"use client";

import { DatabaseZap, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { MapLegend, SafetyMap } from "@/components/Map";
import { Badge, Button, EmptyState, ErrorState, Field, Modal, PageHeader, Panel, SkeletonRows, Stat, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { isAdminRole, useAuth } from "@/lib/auth";
import { coords, humanize } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { FACILITY_STYLE } from "@/lib/maps";
import type { Facility, FacilityType, Paged } from "@/lib/types";

const TYPES: FacilityType[] = ["POLICE", "HOSPITAL", "CLINIC", "FIRE_STATION", "PHARMACY"];

type Draft = Partial<Facility> & { facility_type: FacilityType; name: string; latitude: number; longitude: number };
const EMPTY: Draft = { facility_type: "POLICE", name: "", latitude: 13.1665, longitude: 77.5611, phone: "", address: "", district: "", active: true };

export default function FacilitiesPage() {
  const { session } = useAuth();
  const admin = isAdminRole(session?.user.role);
  const toast = useToast();
  const [type, setType] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [deleting, setDeleting] = useState<Facility | null>(null);
  const [busy, setBusy] = useState(false);
  const [focus, setFocus] = useState<[number, number] | null>(null);

  const params = new URLSearchParams({ page: String(page), page_size: "500" });
  if (type) params.set("type", type);
  if (query) params.set("search", query);
  const list = useApi<Paged<Facility>>(`/api/v1/facilities?${params}`);
  const stats = useApi<{ by_type: Record<string, number>; total: number }>("/api/v1/facilities/stats");
  const pages = list.data ? Math.max(1, Math.ceil(list.data.total / list.data.page_size)) : 1;
  const items = useMemo(() => list.data?.items ?? [], [list.data]);

  async function save() {
    if (!draft) return;
    setBusy(true);
    const body = {
      facility_type: draft.facility_type, name: draft.name.trim(), latitude: Number(draft.latitude), longitude: Number(draft.longitude),
      phone: draft.phone || null, address: draft.address || null, district: draft.district || null, active: draft.active ?? true,
    };
    try {
      if (draft.id) await api(`/api/v1/facilities/${draft.id}`, { method: "PATCH", body });
      else await api("/api/v1/facilities", { method: "POST", body });
      toast(draft.id ? "Facility updated" : "Facility added");
      setDraft(null);
      void list.reload();
      void stats.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!deleting) return;
    setBusy(true);
    try {
      await api(`/api/v1/facilities/${deleting.id}`, { method: "DELETE" });
      toast("Facility deleted");
      setDeleting(null);
      void list.reload();
      void stats.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Delete failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function importDataset() {
    setBusy(true);
    try {
      const r = await api<{ imported: number; updated: number; skipped: number }>("/api/v1/facilities/import-dataset", { method: "POST" });
      toast(`Imported ${r.imported}, refreshed ${r.updated}, skipped ${r.skipped} invalid`);
      void list.reload();
      void stats.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Import failed", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Emergency facilities"
        subtitle="Police stations, hospitals, clinics, fire stations and pharmacies — imported from OpenStreetMap (© OpenStreetMap contributors) and editable by admins."
        actions={
          admin && (
            <>
              <Button onClick={importDataset} loading={busy}><DatabaseZap className="h-4 w-4" /> Import / refresh OSM dataset</Button>
              <Button variant="primary" onClick={() => setDraft({ ...EMPTY })}><Plus className="h-4 w-4" /> Add facility</Button>
            </>
          )
        }
      />

      <div className="stagger mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="All facilities" value={stats.data?.total ?? 0} />
        {TYPES.map((t) => <Stat key={t} label={FACILITY_STYLE[t].label} value={stats.data?.by_type[t] ?? 0} />)}
      </div>

      <div className="grid gap-6 2xl:grid-cols-2">
        <Panel bodyClass="p-3">
          <SafetyMap
            facilities={items}
            focus={focus}
            height="560px"
            draft={draft ? { latitude: Number(draft.latitude), longitude: Number(draft.longitude), radius_meters: 60 } : null}
            onMapClick={(lat, lon) => draft && setDraft({ ...draft, latitude: Number(lat.toFixed(6)), longitude: Number(lon.toFixed(6)) })}
          />
          <div className="mt-3"><MapLegend facilities /></div>
        </Panel>

        <div className="space-y-6">
          {draft && (
            <Panel title={draft.id ? `Edit facility #${draft.id}` : "New facility"}>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="sm:col-span-2"><Field label="Name"><input className="field" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></Field></div>
                <Field label="Type">
                  <select className="field" value={draft.facility_type} onChange={(e) => setDraft({ ...draft, facility_type: e.target.value as FacilityType })}>
                    {TYPES.map((t) => <option key={t} value={t}>{FACILITY_STYLE[t].label}</option>)}
                  </select>
                </Field>
                <Field label="Phone"><input className="field" value={draft.phone ?? ""} onChange={(e) => setDraft({ ...draft, phone: e.target.value })} /></Field>
                <Field label="Latitude"><input className="field" type="number" step="0.000001" value={draft.latitude} onChange={(e) => setDraft({ ...draft, latitude: Number(e.target.value) })} /></Field>
                <Field label="Longitude"><input className="field" type="number" step="0.000001" value={draft.longitude} onChange={(e) => setDraft({ ...draft, longitude: Number(e.target.value) })} /></Field>
                <Field label="District"><input className="field" value={draft.district ?? ""} onChange={(e) => setDraft({ ...draft, district: e.target.value })} /></Field>
                <Field label="Status">
                  <select className="field" value={draft.active ? "1" : "0"} onChange={(e) => setDraft({ ...draft, active: e.target.value === "1" })}>
                    <option value="1">Active</option><option value="0">Inactive</option>
                  </select>
                </Field>
                <div className="sm:col-span-2"><Field label="Address"><input className="field" value={draft.address ?? ""} onChange={(e) => setDraft({ ...draft, address: e.target.value })} /></Field></div>
                <p className="text-xs muted sm:col-span-2">Click the map to place the facility.</p>
                <div className="flex justify-end gap-2 sm:col-span-2">
                  <Button onClick={() => setDraft(null)}>Cancel</Button>
                  <Button variant="primary" loading={busy} disabled={!draft.name.trim()} onClick={save}>Save facility</Button>
                </div>
              </div>
            </Panel>
          )}

          <Panel bodyClass="p-0">
            <form className="flex flex-wrap gap-2 border-b hairline p-3" onSubmit={(e) => { e.preventDefault(); setPage(1); setQuery(search.trim()); }}>
              <input className="field h-9 w-56" placeholder="Search name or address…" value={search} onChange={(e) => setSearch(e.target.value)} />
              <select className="field h-9 w-44" value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}>
                <option value="">All types</option>
                {TYPES.map((t) => <option key={t} value={t}>{FACILITY_STYLE[t].label}</option>)}
              </select>
              <Button size="sm" type="submit">Search</Button>
              <span className="self-center text-xs muted">{list.data?.total ?? 0} found</span>
            </form>
            {list.loading ? <SkeletonRows /> : list.error ? <ErrorState message={list.error} onRetry={list.reload} /> : !items.length ? (
              <EmptyState title="No facilities" hint={admin ? "Use “Import / refresh OSM dataset” to load the downloaded OpenStreetMap facilities." : undefined} />
            ) : (
              <div className="max-h-[520px] overflow-auto">
                <table className="w-full min-w-[620px]">
                  <thead className="sticky top-0 border-b hairline bg-[var(--panel)]">
                    <tr><th className="th">Facility</th><th className="th">Type</th><th className="th">Phone</th><th className="th">Source</th><th className="th" /></tr>
                  </thead>
                  <tbody className="divide-y hairline">
                    {items.map((f) => (
                      <tr key={f.id} className="hover:bg-black/[.02] dark:hover:bg-white/[.03]">
                        <td className="td">
                          <button className="text-left font-medium hover:text-brand-600" onClick={() => setFocus([f.latitude, f.longitude])}>{f.name}</button>
                          <p className="font-mono text-[11px] muted">{coords(f.latitude, f.longitude)}{f.district ? ` · ${f.district}` : ""}</p>
                        </td>
                        <td className="td"><span className="inline-flex items-center gap-1.5 text-xs"><span className="h-2.5 w-2.5 rounded-full" style={{ background: FACILITY_STYLE[f.facility_type].color }} />{FACILITY_STYLE[f.facility_type].label}</span></td>
                        <td className="td text-xs">{f.phone ? <a className="text-brand-600" href={`tel:${f.phone}`}>{f.phone}</a> : "—"}</td>
                        <td className="td">{f.source === "osm" ? <Badge tone="info">OSM {f.source_ref}</Badge> : <Badge tone="neutral">{humanize(f.source)}</Badge>}{!f.active && <Badge tone="neutral" className="ml-1">Inactive</Badge>}</td>
                        <td className="td whitespace-nowrap text-right">
                          {admin && (
                            <>
                              <Button size="sm" variant="ghost" onClick={() => { setFocus([f.latitude, f.longitude]); setDraft({ ...f }); }}>Edit</Button>
                              <Button size="sm" variant="ghost" className="text-red-700" onClick={() => setDeleting(f)}>Delete</Button>
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {pages > 1 && (
              <div className="flex items-center justify-between border-t hairline px-4 py-3 text-xs muted">
                <span>Page {page} of {pages}</span>
                <div className="flex gap-2">
                  <Button size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
                  <Button size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button>
                </div>
              </div>
            )}
          </Panel>
        </div>
      </div>

      <Modal
        open={!!deleting}
        title="Delete facility"
        onClose={() => setDeleting(null)}
        footer={<><Button onClick={() => setDeleting(null)}>Cancel</Button><Button variant="danger" loading={busy} onClick={remove}>Delete</Button></>}
      >
        <p className="text-sm">Delete <b>{deleting?.name}</b>? {deleting?.source === "osm" ? "It will come back if the OSM dataset is re-imported; set it inactive instead to hide it permanently." : "This cannot be undone."}</p>
      </Modal>
    </>
  );
}
