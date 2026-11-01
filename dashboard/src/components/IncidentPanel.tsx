"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { isAdminRole, useAuth } from "@/lib/auth";
import { coords, dateTime, humanize, metres, timeAgo } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { Officer, SOSAlert } from "@/lib/types";
import { Button, Field, Modal, Panel, StatusBadge, useToast } from "./ui";

const OUTCOMES = ["ASSISTED", "FALSE_ALARM", "REFERRED", "UNREACHABLE", "OTHER"];

export function IncidentActions({ alert, onChange }: { alert: SOSAlert; onChange: (a: SOSAlert) => void }) {
  const { session } = useAuth();
  const toast = useToast();
  const admin = isAdminRole(session?.user.role);
  const police = session?.user.role === "POLICE";
  const officers = useApi<Officer[]>(admin ? "/api/v1/admin/officers" : null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [resolving, setResolving] = useState(false);
  const [outcome, setOutcome] = useState("ASSISTED");
  const [notes, setNotes] = useState("");
  const active = ["OPEN", "ACKNOWLEDGED", "RESPONDING"].includes(alert.status);

  async function run(label: string, path: string, body?: unknown) {
    setBusy(label);
    try {
      const updated = await api<SOSAlert>(`/api/v1/sos/${alert.id}/${path}`, { method: "POST", body });
      onChange(updated);
      toast(`${label} recorded`);
      return true;
    } catch (e) {
      toast(e instanceof Error ? e.message : "Action failed", "error");
      return false;
    } finally {
      setBusy(null);
    }
  }

  if (!active) {
    return <p className="text-sm muted">This incident is {humanize(alert.status).toLowerCase()}; no further actions.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {alert.status === "OPEN" && (
          <Button variant="primary" loading={busy === "Acknowledgement"} onClick={() => run("Acknowledgement", "acknowledge", note ? { note } : undefined)}>
            Acknowledge
          </Button>
        )}
        {police && (
          <Button variant="primary" loading={busy === "Acceptance"} onClick={() => run("Acceptance", "accept")}>
            {alert.assigned_officer_id ? "I'm responding" : "Accept & respond"}
          </Button>
        )}
        {admin && alert.status !== "RESPONDING" && alert.assigned_officer_id && (
          <Button loading={busy === "Status"} onClick={() => run("Status", "status", { status: "RESPONDING", note: note || undefined })}>
            Mark responding
          </Button>
        )}
        <Button variant="danger" onClick={() => setResolving(true)}>
          Resolve…
        </Button>
      </div>

      {admin && (
        <Field label="Assign officer">
          <div className="flex gap-2">
            <select
              className="field"
              defaultValue=""
              onChange={async (e) => {
                const id = Number(e.target.value);
                if (id) await run("Assignment", "assign", { officer_id: id });
                e.target.value = "";
              }}
            >
              <option value="" disabled>
                {officers.data?.length ? "Choose an officer…" : "No active officers — create one under Officers & staff"}
              </option>
              {officers.data?.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name} {o.badge_number ? `(${o.badge_number})` : ""} · {o.active_incidents} active
                </option>
              ))}
            </select>
          </div>
        </Field>
      )}

      <Field label="Incident note">
        <textarea className="field min-h-[72px]" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Called tourist; patrol dispatched…" />
      </Field>
      <Button
        size="sm"
        disabled={!note.trim()}
        loading={busy === "Note"}
        onClick={async () => {
          if (await run("Note", "notes", { note: note.trim() })) setNote("");
        }}
      >
        Add note to timeline
      </Button>

      <Modal
        open={resolving}
        title={`Resolve SOS #${alert.id}`}
        onClose={() => setResolving(false)}
        footer={
          <>
            <Button onClick={() => setResolving(false)}>Cancel</Button>
            <Button
              variant="danger"
              disabled={notes.trim().length < 3}
              loading={busy === "Resolution"}
              onClick={async () => {
                if (await run("Resolution", "resolve", { outcome, notes: notes.trim() })) setResolving(false);
              }}
            >
              Resolve incident
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm muted">Only resolve once the tourist is confirmed safe or the case is handed over. This cannot be undone.</p>
          <Field label="Outcome">
            <select className="field" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
              {OUTCOMES.map((o) => (
                <option key={o} value={o}>
                  {humanize(o)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Resolution notes (required)">
            <textarea className="field min-h-[96px]" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

export function IncidentSummary({ alert }: { alert: SOSAlert }) {
  return (
    <Panel title={`SOS #${alert.id} · ${alert.tourist_name ?? alert.tourist_code}`} action={<StatusBadge status={alert.status} />}>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
        <Cell label="Type" value={humanize(alert.alert_type)} />
        <Cell label="Raised" value={`${dateTime(alert.created_at)} (${timeAgo(alert.created_at)})`} />
        <Cell label="GPS position" value={<span className="font-mono text-xs">{coords(alert.latitude, alert.longitude)}</span>} />
        <Cell label="Accuracy" value={metres(alert.accuracy)} />
        <Cell label="Assigned officer" value={alert.assigned_officer ? `${alert.assigned_officer.name}${alert.assigned_officer.badge_number ? ` · ${alert.assigned_officer.badge_number}` : ""}` : "Unassigned"} />
        <Cell label="Acknowledged" value={dateTime(alert.acknowledged_at)} />
        <div className="col-span-2">
          <dt className="text-xs muted">Tourist message</dt>
          <dd className="mt-0.5">{alert.message || "—"}</dd>
        </div>
        {alert.resolution_outcome && (
          <div className="col-span-2">
            <dt className="text-xs muted">Resolution</dt>
            <dd className="mt-0.5">
              {humanize(alert.resolution_outcome)} — {alert.resolution_notes}
            </dd>
          </div>
        )}
        {alert.latitude != null && alert.longitude != null && (
          <div className="col-span-2">
            <a
              className="text-xs text-brand-600 hover:underline"
              href={`https://www.google.com/maps/dir/?api=1&destination=${alert.latitude},${alert.longitude}`}
              target="_blank"
              rel="noreferrer"
            >
              Navigate in Google Maps →
            </a>
          </div>
        )}
      </dl>
    </Panel>
  );
}

function Cell({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs muted">{label}</dt>
      <dd className="mt-0.5">{value}</dd>
    </div>
  );
}

export function Timeline({ alert }: { alert: SOSAlert }) {
  return (
    <Panel title="Incident timeline">
      <ol className="relative space-y-4 border-l hairline pl-5">
        {(alert.timeline ?? []).map((e) => (
          <li key={e.id} className="relative">
            <span className="absolute -left-[25px] top-1 h-2.5 w-2.5 rounded-full border-2 border-[var(--panel)] bg-brand-600" />
            <p className="text-sm font-medium">
              {humanize(e.action)}
              {e.to_status && e.from_status ? <span className="font-normal muted"> · {humanize(e.from_status)} → {humanize(e.to_status)}</span> : null}
            </p>
            <p className="text-xs muted">
              {e.actor_name ?? e.actor_type} · {dateTime(e.created_at)}
            </p>
            {e.note && <p className="mt-1 text-sm">{e.note}</p>}
          </li>
        ))}
      </ol>
    </Panel>
  );
}
