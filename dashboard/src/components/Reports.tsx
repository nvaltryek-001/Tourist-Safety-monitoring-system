"use client";

import { Download } from "lucide-react";
import { useState } from "react";
import { API_URL, readSession } from "@/lib/api";
import { Button, Panel, useToast } from "./ui";

const REPORTS: [string, string, string][] = [
  ["incidents.csv", "SOS incidents", "Type, status, officer, minutes to acknowledge and resolve, outcome"],
  ["zones.csv", "Safety zones", "Every zone with type, verification status and entries/dwell time"],
  ["tourists.csv", "Tourist summary", "Status, consent, last update and SOS count (no contact details)"],
];

/** Authenticated CSV downloads (the token is sent as a header, never in the URL). */
export function Reports({ days }: { days: number }) {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);

  async function download(file: string) {
    setBusy(file);
    try {
      const token = readSession()?.token;
      const q = file === "tourists.csv" ? "" : `?days=${days}`;
      const res = await fetch(`${API_URL}/api/v1/reports/${file}${q}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `safetrail_${file}`;
      a.click();
      URL.revokeObjectURL(url);
      toast("Report downloaded (export recorded in the audit log)");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Export failed", "error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Panel title="Reports (CSV)">
      <div className="grid gap-3 md:grid-cols-3">
        {REPORTS.map(([file, title, desc]) => (
          <div key={file} className="lift rounded border hairline p-4">
            <p className="text-sm font-semibold">{title}</p>
            <p className="mt-1 text-xs muted">{desc}</p>
            <Button size="sm" className="mt-3" loading={busy === file} onClick={() => download(file)}>
              <Download className="h-3.5 w-3.5" /> Download
            </Button>
          </div>
        ))}
      </div>
    </Panel>
  );
}
