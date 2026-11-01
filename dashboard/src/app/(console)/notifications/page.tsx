"use client";

import Link from "next/link";
import { Badge, Button, EmptyState, ErrorState, PageHeader, Panel, SkeletonRows, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { isAdminRole, useAuth } from "@/lib/auth";
import { dateTime, humanize, timeAgo } from "@/lib/format";
import { useApi, useLiveEvents } from "@/lib/hooks";
import type { AppNotification } from "@/lib/types";

interface Delivery {
  providers: Record<string, string>;
  items: { id: number; recipient_type: string; channel: string; category: string; title: string; status: string; attempts: number; last_error: string | null; created_at: string }[];
}

export default function NotificationsPage() {
  const { session } = useAuth();
  const admin = isAdminRole(session?.user.role);
  const inbox = useApi<AppNotification[]>("/api/v1/notifications");
  const delivery = useApi<Delivery>(admin ? "/api/v1/notifications/delivery-log" : null);
  useLiveEvents((e) => {
    if (e.type.startsWith("sos.")) void inbox.reload();
  });

  async function readAll() {
    await api("/api/v1/notifications/read-all", { method: "POST" });
    void inbox.reload();
  }

  return (
    <>
      <PageHeader title="Notification centre" subtitle="In-app alerts for your account, and (for admins) the delivery log of every email and push attempt." actions={<Button onClick={readAll}>Mark all read</Button>} />
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="My inbox" bodyClass="p-0">
          {inbox.loading ? <SkeletonRows /> : inbox.error ? <ErrorState message={inbox.error} onRetry={inbox.reload} /> : !inbox.data?.length ? <EmptyState title="No notifications" /> : (
            <ul className="divide-y hairline">
              {inbox.data.map((n) => (
                <li key={n.id} className={`px-4 py-3 ${n.read_at ? "" : "bg-brand-50/50 dark:bg-brand-600/5"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium">{n.title}</p>
                    <span className="text-[11px] muted">{timeAgo(n.created_at)}</span>
                  </div>
                  <p className="mt-0.5 text-sm muted">{n.body}</p>
                  <div className="mt-1.5 flex gap-2">
                    <Badge tone="info">{humanize(n.category)}</Badge>
                    {n.related_sos_id && <Link className="text-xs text-brand-600 hover:underline" href={`/incidents/${n.related_sos_id}`}>Open SOS #{n.related_sos_id}</Link>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        {admin && (
          <Panel
            title="Delivery log"
            bodyClass="p-0"
            action={delivery.data && <span className="text-xs muted">Email: {delivery.data.providers.email} · Push: {delivery.data.providers.push} · SMS: {delivery.data.providers.sms}</span>}
          >
            {delivery.loading ? <SkeletonRows /> : delivery.error ? <ErrorState message={delivery.error} onRetry={delivery.reload} /> : !delivery.data?.items.length ? <EmptyState title="No deliveries yet" /> : (
              <ul className="max-h-[640px] divide-y hairline overflow-y-auto">
                {delivery.data.items.map((d) => (
                  <li key={d.id} className="px-4 py-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm">{d.title}</p>
                      <StatusBadge status={d.status} />
                    </div>
                    <p className="text-xs muted">
                      {d.channel} → {humanize(d.recipient_type)} · {humanize(d.category)} · {d.attempts} attempt(s) · {dateTime(d.created_at)}
                    </p>
                    {d.last_error && <p className="mt-0.5 text-xs text-orange-700">{d.last_error}</p>}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        )}
      </div>
      <p className="mt-4 text-xs muted">“Accepted by provider” means the email/push service accepted the message. It is not proof the recipient read it.</p>
    </>
  );
}
