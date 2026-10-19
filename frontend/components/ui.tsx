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

/** Horizontal 0–100 gauge, used instead of a bare number so severity reads
 * visually rather than requiring the person to interpret a raw score. */
export function SeverityMeter({ score, label }: { score: number; label?: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = clamped >= 70 ? "bg-high" : clamped >= 40 ? "bg-medium" : "bg-low";
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && <span className="text-xs text-slate-500">{label}</span>}
      <div className="h-2.5 w-full rounded-full bg-white/10 overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs text-slate-400">{Math.round(clamped)} / 100</span>
    </div>
  );
}

// Ordered stage keys mirroring backend/app/services/training.py STAGE_ORDER.
// Kept here (not fetched) since it only drives a progress-bar fraction; the
// actual label shown to the user always comes from the backend's message.
const TRAIN_STAGE_ORDER = [
  "queued",
  "ingesting",
  "preprocessing",
  "feature_engineering",
  "training_baseline",
  "training_xgboost",
  "calibrating",
  "detecting_anomalies",
  "generating_insights",
  "finalizing",
  "completed",
];

/** Named-stage progress bar for training, replacing an indeterminate spinner. */
export function ProgressStages({
  stage,
  message,
}: {
  stage?: string | null;
  message?: string | null;
}) {
  const idx = stage ? TRAIN_STAGE_ORDER.indexOf(stage) : 0;
  const total = TRAIN_STAGE_ORDER.length - 1; // exclude "queued" from the denominator
  const fraction = idx <= 0 ? 0.03 : Math.min(1, idx / total);

  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full bg-accent transition-all duration-500"
          style={{ width: `${fraction * 100}%` }}
        />
      </div>
      <span className="text-sm text-slate-300">{message || "Working…"}</span>
    </div>
  );
}

/** Plain-language stand-in for a raw JSON dump of missing-value / gap reports. */
export function DataQualitySummary({
  missingValues,
  temporalGaps,
}: {
  missingValues: {
    per_column?: Record<string, { missing: number; pct: number }>;
    total_rows?: number;
  };
  temporalGaps: {
    total_gaps?: number;
    gaps_by_equipment?: Record<
      string,
      { gap_start: string; gap_end: string; gap_minutes: number }[]
    >;
  };
}) {
  const perColumn = missingValues?.per_column || {};
  const missingEntries = Object.entries(perColumn).filter(([, v]) => v && v.missing > 0);

  const gapsByEquipment = temporalGaps?.gaps_by_equipment || {};
  const totalGaps = temporalGaps?.total_gaps ?? 0;
  const equipmentWithGaps = Object.keys(gapsByEquipment).length;
  const worstGap = Object.values(gapsByEquipment)
    .flat()
    .sort((a, b) => b.gap_minutes - a.gap_minutes)[0];

  if (missingEntries.length === 0 && totalGaps === 0) {
    return (
      <p className="text-sm text-slate-400">
        No missing values or timing gaps found — the data looks complete.
      </p>
    );
  }

  return (
    <ul className="text-sm text-slate-300 flex flex-col gap-1.5">
      {missingEntries.map(([field, info]) => (
        <li key={`missing-${field}`}>
          <span className="text-slate-400">Missing values:</span> {field} was missing{" "}
          <span className="text-slate-100">{info.missing}</span> reading
          {info.missing === 1 ? "" : "s"} ({info.pct}% of rows) — filled in automatically
          where it could be done safely, left blank where it couldn't be guessed reliably.
        </li>
      ))}
      {totalGaps > 0 && (
        <li>
          <span className="text-slate-400">Timing gaps:</span> found{" "}
          <span className="text-slate-100">{totalGaps}</span> period
          {totalGaps === 1 ? "" : "s"} across {equipmentWithGaps} equipment unit
          {equipmentWithGaps === 1 ? "" : "s"} where readings stopped for longer than
          expected
          {worstGap ? ` (longest: ~${Math.round(worstGap.gap_minutes / 60)} hours)` : ""} —
          kept as real gaps rather than guessed at.
        </li>
      )}
    </ul>
  );
}
