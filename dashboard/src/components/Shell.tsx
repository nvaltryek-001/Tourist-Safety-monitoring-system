"use client";

import {
  Activity,
  Bell,
  BrainCircuit,
  ClipboardList,
  Database,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Hospital,
  Map,
  Menu,
  Moon,
  Settings,
  ShieldAlert,
  Siren,
  Sun,
  Users,
  UserCog,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { isAdminRole, useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { AppNotification, Role } from "@/lib/types";
import { cx } from "./ui";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: Role[];
}

const ALL: Role[] = ["SUPER_ADMIN", "ADMIN", "POLICE"];
const ADMINS: Role[] = ["SUPER_ADMIN", "ADMIN"];

const NAV: { section: string; items: NavItem[] }[] = [
  {
    section: "Operations",
    items: [
      { href: "/", label: "Overview", icon: LayoutDashboard, roles: ADMINS },
      { href: "/police", label: "My workspace", icon: ShieldAlert, roles: ["POLICE"] },
      { href: "/map", label: "Live map", icon: Map, roles: ALL },
      { href: "/incidents", label: "SOS command centre", icon: Siren, roles: ALL },
      { href: "/tourists", label: "Tourists", icon: Users, roles: ALL },
      { href: "/facilities", label: "Emergency facilities", icon: Hospital, roles: ALL },
      { href: "/notifications", label: "Notifications", icon: Bell, roles: ALL },
    ],
  },
  {
    section: "Intelligence",
    items: [
      { href: "/intelligence", label: "AI safety intelligence", icon: BrainCircuit, roles: ALL },
      { href: "/analytics", label: "Analytics", icon: Activity, roles: ALL },
    ],
  },
  {
    section: "Administration",
    items: [
      { href: "/zones", label: "Safety zones", icon: ShieldAlert, roles: ADMINS },
      { href: "/data", label: "Dataset management", icon: Database, roles: ADMINS },
      { href: "/access", label: "Tourist login access", icon: KeyRound, roles: ADMINS },
      { href: "/officers", label: "Officers & staff", icon: UserCog, roles: ADMINS },
      { href: "/audit", label: "Audit log", icon: ClipboardList, roles: ADMINS },
      { href: "/settings", label: "Settings", icon: Settings, roles: ALL },
    ],
  },
];

function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem("tsm.theme");
    } catch {
      /* ignore */
    }
    const initial = stored ? stored === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(initial);
    document.documentElement.classList.toggle("dark", initial);
  }, []);
  const toggle = () => {
    setDark((d) => {
      const next = !d;
      document.documentElement.classList.toggle("dark", next);
      try {
        window.localStorage.setItem("tsm.theme", next ? "dark" : "light");
      } catch {
        /* ignore */
      }
      return next;
    });
  };
  return [dark, toggle];
}

export function Shell({ children }: { children: React.ReactNode }) {
  const { session, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [dark, toggleTheme] = useTheme();
  const unread = useApi<AppNotification[]>(session ? "/api/v1/notifications?unread_only=true" : null, 30000);

  useEffect(() => {
    if (ready && !session) router.replace("/login");
  }, [ready, session, router]);

  useEffect(() => setOpen(false), [pathname]);

  if (!ready || !session) {
    return <div className="flex min-h-screen items-center justify-center text-sm muted">Checking session…</div>;
  }
  const role = session.user.role;
  const unreadCount = unread.data?.length ?? 0;

  const nav = (
    <nav className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="relative flex h-8 w-8 items-center justify-center overflow-hidden rounded bg-brand-600 text-white">
          <span className="radar" />
          <ShieldAlert className="relative h-4 w-4" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-white">SafeTrail</p>
          <p className="text-[11px] text-slate-400">Tourist Safety Command</p>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {NAV.map((group) => {
          const items = group.items.filter((i) => i.roles.includes(role));
          if (!items.length) return null;
          return (
            <div key={group.section} className="mt-4">
              <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">{group.section}</p>
              {items.map((item) => {
                const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cx(
                      "relative flex items-center gap-2.5 rounded px-2.5 py-2 text-[13px] transition-all duration-200",
                      active ? "bg-white/10 text-white shadow-[inset_3px_0_0_#14917c]" : "text-slate-300 hover:translate-x-0.5 hover:bg-white/5 hover:text-white",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1">{item.label}</span>
                    {item.href === "/notifications" && unreadCount > 0 && (
                      <span className="rounded bg-red-600 px-1.5 text-[10px] font-semibold text-white">{unreadCount}</span>
                    )}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </div>
      <div className="border-t border-white/10 p-4">
        <p className="truncate text-sm font-medium text-white">{session.user.name}</p>
        <p className="truncate text-xs text-slate-400">
          {role.replace("_", " ").toLowerCase()} · {session.user.email}
        </p>
        <div className="mt-3 flex gap-2">
          <button
            onClick={toggleTheme}
            className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded border border-white/10 text-xs text-slate-300 hover:bg-white/5"
            aria-label="Toggle colour theme"
          >
            {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            {dark ? "Light" : "Dark"}
          </button>
          <button
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
            className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded border border-white/10 text-xs text-slate-300 hover:bg-white/5"
          >
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </button>
        </div>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen lg:pl-64">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 bg-ink-950 lg:block">{nav}</aside>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 bg-ink-950">
            <button className="absolute right-3 top-4 text-slate-300" onClick={() => setOpen(false)} aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
            {nav}
          </aside>
        </div>
      )}
      <div className="sticky top-0 z-30 flex items-center gap-3 border-b hairline bg-[var(--panel)] px-4 py-3 lg:hidden">
        <button onClick={() => setOpen(true)} aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </button>
        <span className="text-sm font-semibold">SafeTrail</span>
        {isAdminRole(role) ? null : <span className="ml-auto text-xs muted">Officer</span>}
      </div>
      <main key={pathname} className="animate-fade mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}
