import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-border bg-panel p-5 ${className}`}>
      {children}
    </div>
  );
}

export function StatPill({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-400">{label}</span>
      <span className="text-2xl font-semibold text-white">{value}</span>
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
    </Card>
  );
}

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-high/15 text-high border-high/40",
  medium: "bg-medium/15 text-medium border-medium/40",
  low: "bg-low/15 text-low border-low/40",
};

export function SeverityBadge({ severity }: { severity: string }) {
  const cls = SEVERITY_STYLES[severity] || "bg-white/10 text-slate-300 border-white/20";
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium uppercase ${cls}`}>
      {severity}
    </span>
  );
}

export function StatusDot({ status }: { status: string }) {
  const color =
    status === "attention_needed" ? "bg-high" : status === "monitor" ? "bg-medium" : "bg-low";
  const text =
    status === "attention_needed" ? "Attention needed" : status === "monitor" ? "Monitor" : "Normal";
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-slate-300">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {text}
    </span>
  );
}

export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <Card className="text-center py-12">
      <p className="text-slate-300 font-medium">{title}</p>
      {body && <p className="text-sm text-slate-500 mt-1">{body}</p>}
    </Card>
  );
}

export function Spinner() {
  return (
    <div className="flex items-center gap-2 text-slate-400 text-sm py-8 justify-center">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      Loading…
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-high/40 bg-high/10 px-4 py-3 text-sm text-red-200">
      {message}
    </div>
  );
}

export function fmtNum(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
