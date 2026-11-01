"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { LiveBadge } from "@/components/LiveBadge";
import { MapLegend, SafetyMap } from "@/components/Map";
import { Badge, Button, PageHeader, Panel, StatusBadge } from "@/components/ui";
import { coords, humanize, metres, timeAgo } from "@/lib/format";
import { useApi, useLiveEvents } from "@/lib/hooks";
import type { Paged, SOSAlert, Tourist, Zone } from "@/lib/types";

const FILTERS = ["ALL", "ACTIVE", "ATTENTION", "SOS"] as const;

export default function LiveMapPage() {
  const tourists = useApi<Paged<Tourist>>("/api/v1/admin/tourists?page_size=200");
  const zones = useApi<Zone[]>("/api/v1/zones");
  const alerts = useApi<SOSAlert[]>("/api/v1/sos?scope=active");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const [zoneLayer, setZoneLayer] = useState<"active" | "all" | "none">("active");
  const [selected, setSelected] = useState<Tourist | null>(null);
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const [search, setSearch] = useState("");

  const live = useLiveEvents((event) => {
    if (event.type === "location.updated") {
      const d = event.data as unknown as Tourist;
      tourists.setData((prev) =>
        prev ? { ...prev, items: prev.items.map((t) => (t.tourist_code === d.tourist_code ? { ...t, ...d, location_stale: false } : t)) } : prev,
      );
      setSelected((s) => (s && s.tourist_code === d.tourist_code ? { ...s, ...d, location_stale: false } : s));
    }
    if (event.type.startsWith("sos.")) {
      void alerts.reload();
      void tourists.reload();
    }
  });

  const visibleTourists = useMemo(() => {
    const items = tourists.data?.items ?? [];
    return items.filter((t) => {
      if (search && !`${t.name} ${t.tourist_code}`.toLowerCase().includes(search.toLowerCase())) return false;
      if (filter === "ACTIVE") return t.last_location_update && !t.location_stale;
      if (filter === "ATTENTION") return ["CAUTION", "DANGER", "SOS"].includes(t.safety_status);
      if (filter === "SOS") return t.safety_status === "SOS";
      return true;
    });
  }, [tourists.data, filter, search]);

  const visibleZones = useMemo(
    () => (zoneLayer === "none" ? [] : (zones.data ?? []).filter((z) => zoneLayer === "all" || z.active)),
    [zones.data, zoneLayer],
  );

  return (
    <>
      <PageHeader
        title="Live monitoring map"
        subtitle="Positions come only from tourists who consented to location sharing. Grey markers are stale."
        actions={<LiveBadge status={live} />}
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <Panel bodyClass="p-3">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {FILTERS.map((f) => (
              <Button key={f} size="sm" variant={filter === f ? "primary" : "secondary"} onClick={() => setFilter(f)}>
                {f === "ALL" ? "All tourists" : humanize(f)}
              </Button>
            ))}
            <span className="mx-1 h-5 w-px bg-[var(--line)]" />
            <select className="field h-8 w-auto py-0 text-xs" value={zoneLayer} onChange={(e) => setZoneLayer(e.target.value as typeof zoneLayer)}>
              <option value="active">Active zones</option>
              <option value="all">All zones (incl. inactive)</option>
              <option value="none">Hide zones</option>
            </select>
            <input className="field h-8 w-48 py-0 text-xs" placeholder="Search tourist…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <SafetyMap
            zones={visibleZones}
            tourists={visibleTourists}
            alerts={alerts.data ?? []}
            height="calc(100vh - 260px)"
            focus={focus}
            onTouristClick={(t) => setSelected(t)}
          />
          <div className="mt-3">
            <MapLegend />
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel title={selected ? selected.name : "Tourist details"}>
            {!selected ? (
              <p className="text-sm muted">Select a marker or a tourist below to see details.</p>
            ) : (
              <dl className="space-y-2 text-sm">
                <Row label="Code" value={selected.tourist_code} />
                <Row label="Status" value={<StatusBadge status={selected.safety_status} />} />
                <Row label="Position" value={<span className="font-mono text-xs">{coords(selected.latitude, selected.longitude)}</span>} />
                <Row label="Accuracy" value={metres(selected.location_accuracy)} />
                <Row label="Last update" value={`${timeAgo(selected.last_location_update)}${selected.location_stale ? " · stale" : ""}`} />
                <Link href={`/tourists/${encodeURIComponent(selected.tourist_code)}`} className="block pt-2 text-xs text-brand-600 hover:underline">
                  Open tourist profile →
                </Link>
              </dl>
            )}
          </Panel>
          <Panel title={`Tourists (${visibleTourists.length})`} bodyClass="p-0">
            <ul className="max-h-[420px] divide-y hairline overflow-y-auto">
              {visibleTourists.map((t) => (
                <li key={t.tourist_code}>
                  <button
                    className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left hover:bg-black/[.02] dark:hover:bg-white/[.03]"
                    onClick={() => {
                      setSelected(t);
                      if (t.latitude != null && t.longitude != null) setFocus([t.latitude, t.longitude]);
                    }}
                  >
                    <span>
                      <span className="block text-sm font-medium">{t.name}</span>
                      <span className="text-xs muted">
                        {t.tourist_code} · {timeAgo(t.last_location_update)}
                      </span>
                    </span>
                    {t.location_stale ? <Badge tone="neutral">Stale</Badge> : <StatusBadge status={t.safety_status} />}
                  </button>
                </li>
              ))}
              {!visibleTourists.length && <li className="px-4 py-6 text-center text-sm muted">No tourists match.</li>}
            </ul>
          </Panel>
        </div>
      </div>
    </>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-xs muted">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}
