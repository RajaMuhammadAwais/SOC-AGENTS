// Shared SOC console presentation helpers (empty states, page headers, badges).
// Console work-in-progress: these are lightweight building blocks until the
// full console component library lands.
import type { ReactNode } from "react";

const SEVERITY_CLASSES: Record<string, string> = {
  critical: "border-red-500/40 bg-red-500/10 text-red-300",
  high: "border-orange-500/40 bg-orange-500/10 text-orange-300",
  medium: "border-yellow-500/40 bg-yellow-500/10 text-yellow-300",
  low: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  informational: "border-slate-500/40 bg-slate-500/10 text-slate-300",
  active: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  inactive: "border-slate-500/40 bg-slate-500/10 text-slate-400"
};

/**
 * StatusBadge — severity/state chip with a fixed style vocabulary so that
 * incident and alert surfaces stay visually consistent.
 */
export function StatusBadge({ status }: { status: string }) {
  const label = status.toUpperCase();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide ${
        SEVERITY_CLASSES[status.toLowerCase()] ?? SEVERITY_CLASSES.informational
      }`}
    >
      {label}
    </span>
  );
}

/**
 * PageHeader — title + optional subtitle for console pages.
 */
export function PageHeader({
  title,
  description,
  actions
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-4 border-b border-slate-800 px-6 py-4 lg:px-10">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">{title}</h1>
        {description ? (
          <p className="mt-1 text-sm text-slate-400">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </header>
  );
}

/**
 * EmptyState — friendly placeholder when a list has no records yet.
 */
export function EmptyState({
  title,
  message,
  children
}: {
  title?: string;
  message?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center border border-dashed border-slate-700 px-6 py-12 text-center">
      {title ? (
        <p className="text-sm font-medium text-slate-300">{title}</p>
      ) : null}
      <div className="mt-3 text-sm text-slate-400">
        {message ? <p>{message}</p> : null}
        {children}
      </div>
    </div>
  );
}

/**
 * formatRelativeTime — renders ISO timestamps as short relative descriptions
 * ("3m ago", "2h ago") so event surfaces read naturally.
 */
export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diff = Date.now() - then;
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
