"use client";

import { AlertTriangle, Inbox, Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { humanize, statusTone, type Tone } from "@/lib/format";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

const TONES: Record<Tone, string> = {
  safe: "bg-emerald-50 text-emerald-800 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300",
  caution: "bg-amber-50 text-amber-800 ring-amber-600/25 dark:bg-amber-500/10 dark:text-amber-300",
  danger: "bg-orange-50 text-orange-800 ring-orange-600/25 dark:bg-orange-500/10 dark:text-orange-300",
  sos: "bg-red-50 text-red-800 ring-red-600/30 dark:bg-red-500/15 dark:text-red-300",
  neutral: "bg-slate-100 text-slate-700 ring-slate-500/20 dark:bg-slate-500/15 dark:text-slate-300",
  info: "bg-sky-50 text-sky-800 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-300",
};

export const TONE_HEX: Record<Tone, string> = {
  safe: "#15803d",
  caution: "#d97706",
  danger: "#ea580c",
  sos: "#dc2626",
  neutral: "#64748b",
  info: "#0284c7",
};

export function Badge({ tone = "info", children, className }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset", TONES[tone], className)}>
      {children}
    </span>
  );
}

export function StatusBadge({ status, label }: { status: string | null | undefined; label?: string }) {
  const tone = statusTone(status);
  return (
    <Badge tone={tone}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: TONE_HEX[tone] }} />
      {label ?? humanize(status)}
    </Badge>
  );
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
  loading?: boolean;
};

export function Button({ variant = "secondary", size = "md", loading, className, children, disabled, ...rest }: ButtonProps) {
  const styles = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 border-transparent",
    secondary: "bg-[var(--panel)] hairline border hover:bg-black/[.03] dark:hover:bg-white/[.04]",
    danger: "bg-red-700 text-white hover:bg-red-800 border-transparent",
    ghost: "border-transparent hover:bg-black/[.04] dark:hover:bg-white/[.06]",
  }[variant];
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded border font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "h-8 px-3 text-xs" : "h-10 px-4 text-sm",
        styles,
        className,
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Panel({ title, action, children, className, bodyClass }: {
  title?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClass?: string;
}) {
  return (
    <section className={cx("panel", className)}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b hairline px-4 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          {action}
        </header>
      )}
      <div className={bodyClass ?? "p-4"}>{children}</div>
    </section>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded bg-black/[.06] dark:bg-white/[.07]", className)} />;
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <Inbox className="h-8 w-8 muted" strokeWidth={1.5} />
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="max-w-sm text-xs muted">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-10 text-center" role="alert">
      <AlertTriangle className="h-7 w-7 text-orange-600" strokeWidth={1.75} />
      <p className="max-w-md text-sm">{message}</p>
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: React.ReactNode; hint?: string; tone?: Tone }) {
  return (
    <div className="panel px-4 py-3.5">
      <p className="text-[11px] font-semibold uppercase tracking-wider muted">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums" style={tone ? { color: TONE_HEX[tone] } : undefined}>
        {value}
      </p>
      {hint && <p className="mt-0.5 text-xs muted">{hint}</p>}
    </div>
  );
}

export function Modal({ open, title, onClose, children, footer }: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[1000] flex items-end justify-center bg-black/40 p-4 sm:items-center" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} className="panel w-full max-w-lg shadow-xl" onMouseDown={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b hairline px-5 py-3.5">
          <h3 className="text-sm font-semibold">{title}</h3>
          <button aria-label="Close" onClick={onClose} className="rounded p-1 hover:bg-black/5 dark:hover:bg-white/10">
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <footer className="flex justify-end gap-2 border-t hairline px-5 py-3">{footer}</footer>}
      </div>
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs muted">{hint}</span>}
    </label>
  );
}

/* ---------------------------------------------------------------- toasts */
interface Toast {
  id: number;
  message: string;
  tone: "success" | "error" | "info";
}
const ToastContext = createContext<(message: string, tone?: Toast["tone"]) => void>(() => {});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, tone: Toast["tone"] = "success") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, tone }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[1100] flex w-80 flex-col gap-2" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cx(
              "pointer-events-auto rounded border px-4 py-3 text-sm shadow-lg",
              t.tone === "error" ? "border-red-200 bg-red-50 text-red-900" : t.tone === "info" ? "border-sky-200 bg-sky-50 text-sky-900" : "border-emerald-200 bg-emerald-50 text-emerald-900",
            )}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
