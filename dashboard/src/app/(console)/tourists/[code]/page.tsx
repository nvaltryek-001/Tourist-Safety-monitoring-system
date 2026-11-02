"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { AdvisoryList } from "@/components/Advisories";
import { SafetyMap } from "@/components/Map";
import { Badge, Button, EmptyState, ErrorState, Field, Modal, PageHeader, Panel, SkeletonRows, StatusBadge, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { isAdminRole, useAuth } from "@/lib/auth";
import { coords, dateTime, humanize, metres, timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Advisory, SOSAlert, Tourist } from "@/lib/types";

interface Detail {
  tourist: Tourist;
  contact_visible: boolean;
  alerts: SOSAlert[];
  trips: { id: number; title: string; destination: string | null; status: string; started_at: string; ended_at: string | null }[];
  geofence_events: { event_type: string; zone_id: number; zone_name: string | null; zone_type: string | null; created_at: string }[];
  assessment: { risk_score: number; risk_level: string; advisories: Advisory[]; confidence_note: string };
}

interface Point {
  latitude: number;
  longitude: number;
  accuracy: number | null;
  recorded_at: string;
}

export default function TouristDetailPage() {
  const { code } = useParams<{ code: string }>();
  const detail = useApi<Detail>(`/api/v1/admin/tourists/${encodeURIComponent(code)}`);
  const [hours, setHours] = useState<number | null>(null);
  const history = useApi<Point[]>(hours ? `/api/v1/admin/tourists/${encodeURIComponent(code)}/locations?hours=${hours}` : null);
  const { session } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [editing, setEditing] = useState<Record<string, string> | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const admin = isAdminRole(session?.user.role);
  const superAdmin = session?.user.role === "SUPER_ADMIN";

  async function saveEdit() {
    if (!editing) return;
    setBusy(true);
    try {
      await api(`/api/v1/admin/tourists/${encodeURIComponent(code)}`, { method: "PATCH", body: editing });
      toast("Tourist updated");
      setEditing(null);
      void detail.reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Update failed", "error");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api(`/api/v1/admin/tourists/${encodeURIComponent(code)}?confirm=${encodeURIComponent(confirm)}`, { method: "DELETE" });
      toast("Tourist record deleted");
      router.replace("/tourists");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Delete failed", "error");
      setBusy(false);
    }
  }

  if (detail.loading) return <SkeletonRows rows={8} />;
  if (detail.error || !detail.data) return <Panel><ErrorState message={detail.error ?? "Not found"} onRetry={detail.reload} /></Panel>;
  const { tourist: t, alerts, trips, geofence_events: events, assessment } = detail.data;
  const activeTrip = trips.find((tr) => tr.status === "ACTIVE");
  const track: [number, number][] = (history.data ?? []).map((p) => [p.latitude, p.longitude]);

  return (
    <>
      <PageHeader
        title={t.name}
        subtitle={`${t.tourist_code} · registered ${dateTime(t.created_at)}`}
        actions={
          <>
            {admin && (
              <Button size="sm" onClick={() => setEditing({
                name: t.name, phone: t.phone ?? "", college_email: t.college_email ?? "", enrollment_number: t.enrollment_number ?? "",
                emergency_contact_name: t.emergency_contact_name ?? "", emergency_contact_phone: t.emergency_contact_phone ?? "",
                emergency_contact_email: t.emergency_contact_email ?? "",
              })}>Edit</Button>
            )}
            {superAdmin && <Button size="sm" variant="danger" onClick={() => setDeleting(true)}>Delete</Button>}
            <Link href="/tourists"><Button size="sm">← All tourists</Button></Link>
          </>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          <Panel
            title="Location"
            action={
              <div className="flex items-center gap-2">
                <span className="text-xs muted">History:</span>
                {[6, 24, 72].map((h) => (
                  <Button key={h} size="sm" variant={hours === h ? "primary" : "secondary"} onClick={() => setHours(h)}>
                    {h} h
                  </Button>
                ))}
              </div>
            }
          >
            <SafetyMap
              tourists={t.latitude != null ? [t] : []}
              track={track}
              center={t.latitude != null && t.longitude != null ? [t.latitude, t.longitude] : undefined}
              zoom={15}
              height="360px"
            />
            {history.error && <p className="mt-2 text-sm text-orange-700">{history.error}</p>}
            {hours && history.data && <p className="mt-2 text-xs muted">{history.data.length} points in the last {hours} hours (access is audit-logged).</p>}
          </Panel>

          <Panel title="SOS history" bodyClass="p-0">
            {!alerts.length ? (
              <EmptyState title="No SOS alerts" />
            ) : (
              <ul className="divide-y hairline">
                {alerts.map((a) => (
                  <li key={a.id}>
                    <Link href={`/incidents/${a.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-black/[.02]">
                      <span className="text-sm">
                        SOS #{a.id} · {humanize(a.alert_type)} <span className="muted">· {dateTime(a.created_at)}</span>
                      </span>
                      <StatusBadge status={a.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Geofence events" bodyClass="p-0">
            {!events.length ? (
              <EmptyState title="No zone entries or exits recorded" />
            ) : (
              <ul className="divide-y hairline">
                {events.map((e, i) => (
                  <li key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
                    <span>
                      <Badge tone={e.event_type === "ENTER" ? "danger" : "safe"}>{e.event_type === "ENTER" ? "Entered" : "Exited"}</Badge>{" "}
                      {e.zone_name ?? `Zone ${e.zone_id}`} <span className="muted">· {humanize(e.zone_type)}</span>
                    </span>
                    <span className="text-xs muted">{dateTime(e.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Current state">
            <dl className="space-y-2.5 text-sm">
              <Item label="Safety status" value={<StatusBadge status={t.safety_status} />} />
              <Item label="Last update" value={`${timeAgo(t.last_location_update)}${t.location_stale ? " (stale)" : ""}`} />
              <Item label="Position" value={<span className="font-mono text-xs">{coords(t.latitude, t.longitude)}</span>} />
              <Item label="GPS accuracy" value={metres(t.location_accuracy)} />
              <Item label="Location consent" value={t.consent_given ? "Given" : "Not given"} />
              <Item label="Active trip" value={activeTrip ? `${activeTrip.title}${activeTrip.destination ? ` → ${activeTrip.destination}` : ""}` : "None"} />
            </dl>
          </Panel>

          <Panel title="Contact details">
            {!detail.data.contact_visible && <p className="mb-3 rounded bg-amber-50 px-3 py-2 text-xs text-amber-900">Masked: visible to officers only while handling an active SOS.</p>}
            <dl className="space-y-2.5 text-sm">
              <Item label="Phone" value={t.phone ?? "—"} />
              <Item label="College email" value={t.college_email ?? "—"} />
              <Item label="Emergency contact" value={t.emergency_contact_name ?? "—"} />
              <Item label="Contact phone" value={t.emergency_contact_phone ?? "—"} />
              <Item label="Contact email" value={t.emergency_contact_email ?? "—"} />
            </dl>
          </Panel>

          <Panel title={`AI risk assessment · ${assessment.risk_score}/100`} action={<StatusBadge status={assessment.risk_level} />}>
            <AdvisoryList advisories={assessment.advisories} />
            <p className="mt-3 text-[11px] muted">{assessment.confidence_note}</p>
          </Panel>
        </div>
      </div>
      <Modal open={!!editing} title={`Edit ${t.name}`} onClose={() => setEditing(null)}
        footer={<><Button onClick={() => setEditing(null)}>Cancel</Button><Button variant="primary" loading={busy} onClick={saveEdit}>Save</Button></>}>
        {editing && (
          <div className="grid gap-3 sm:grid-cols-2">
            {Object.keys(editing).map((k) => (
              <Field key={k} label={k.replace(/_/g, " ")}>
                <input className="field" value={editing[k]} onChange={(e) => setEditing({ ...editing, [k]: e.target.value })} />
              </Field>
            ))}
          </div>
        )}
      </Modal>
      <Modal open={deleting} title="Delete tourist record" onClose={() => setDeleting(false)}
        footer={<><Button onClick={() => setDeleting(false)}>Cancel</Button><Button variant="danger" disabled={confirm !== t.tourist_code} loading={busy} onClick={remove}>Delete permanently</Button></>}>
        <p className="text-sm">This removes the profile, Gmail login access, location history, trips and geofence events. SOS records are kept for the incident audit trail. It cannot be undone.</p>
        <Field label={`Type ${t.tourist_code} to confirm`}><input className="field mt-2" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></Field>
      </Modal>
    </>
  );
}

function Item({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-xs muted">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}
