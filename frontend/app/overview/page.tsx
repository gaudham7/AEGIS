"use client";

export const dynamic = "force-dynamic";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getOverview, ApiError } from "@/lib/api";
import type { OverviewResponse } from "@/lib/types";
import { useDataset, withDataset } from "@/lib/useDataset";
import { useToast } from "@/components/Toast";
import {
  Card,
  StatPill,
  SeverityBadge,
  EmptyState,
  Spinner,
  ErrorBanner,
  fmtDate,
  fmtNum,
} from "@/components/ui";

export default function OverviewPage() {
  const [datasetId] = useDataset();
  const toast = useToast();
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getOverview(datasetId)
      .then(setData)
      .catch((e) => {
        const msg = e instanceof ApiError ? e.message : "Could not load overview.";
        setError(msg);
        toast.show(msg, "error");
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  if (!datasetId) {
    return (
      <EmptyState
        title="No dataset selected"
        body="Upload and train a dataset first."
      />
    );
  }
  if (loading) return <Spinner />;
  if (error)
    return (
      <div className="flex flex-col gap-3">
        <ErrorBanner message={error} />
        <Link href="/upload" className="text-sm text-accent underline">
          Go upload / train a dataset
        </Link>
      </div>
    );
  if (!data) return null;

  const metrics = (data.metrics || {}) as Record<string, any>;
  const anomalySummary = (data.anomaly_summary || {}) as Record<string, any>;
  // R² lives nested at metrics.xgboost.{test,validation}.r2 — it was never
  // actually at a flat metrics.xgboost_r2 / metrics.r2 key, which is why
  // this stat always rendered as "—" before.
  const modelR2 = metrics?.xgboost?.test?.r2 ?? metrics?.xgboost?.validation?.r2;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Overview</h1>
        <p className="text-sm text-slate-400 mt-1">
          Monitoring {data.equipment_count} equipment unit
          {data.equipment_count === 1 ? "" : "s"} · dataset {data.dataset_id}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatPill label="Equipment monitored" value={data.equipment_count} />
        <StatPill
          label="Abnormal observations"
          value={anomalySummary.total_abnormal_observations ?? "—"}
          hint={
            anomalySummary.total_scored_observations
              ? `of ${fmtNum(anomalySummary.total_scored_observations, 0)} scored`
              : undefined
          }
        />
        <StatPill
          label="Avg energy (kWh)"
          value={fmtNum(data.energy_statistics.avg_actual_energy_kwh)}
        />
        <StatPill
          label="Model accuracy (R²)"
          value={fmtNum(modelR2, 3)}
          hint="1.0 = perfect fit to held-out data; closer to 1 is better"
        />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <h2 className="font-medium text-white mb-4">Priority abnormal periods</h2>
          {data.priority_abnormal_periods.length === 0 ? (
            <p className="text-sm text-slate-500">No abnormal periods detected.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {data.priority_abnormal_periods.map((p) => (
                <li key={p.period_id}>
                  <Link
                    href={withDataset(`/investigation/${p.period_id}`, datasetId)}
                    className="flex items-center justify-between rounded-lg border border-border px-3 py-2 hover:bg-white/5 transition"
                  >
                    <div className="flex flex-col">
                      <span className="text-sm text-slate-200">{p.equipment_id}</span>
                      <span className="text-xs text-slate-500">
                        {fmtDate(p.start_time)} – {fmtDate(p.end_time)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">
                        score {fmtNum(p.severity_score, 0)}
                      </span>
                      <SeverityBadge severity={p.severity_label} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="font-medium text-white mb-4">Recent events</h2>
          {data.recent_events.length === 0 ? (
            <p className="text-sm text-slate-500">No events recorded.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {data.recent_events.map((p) => (
                <li key={p.period_id}>
                  <Link
                    href={withDataset(`/investigation/${p.period_id}`, datasetId)}
                    className="flex items-center justify-between rounded-lg border border-border px-3 py-2 hover:bg-white/5 transition"
                  >
                    <div className="flex flex-col">
                      <span className="text-sm text-slate-200">{p.equipment_id}</span>
                      <span className="text-xs text-slate-500">
                        started {fmtDate(p.start_time)}
                      </span>
                    </div>
                    <SeverityBadge severity={p.severity_label} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="flex gap-3">
        <Link
          href={withDataset("/equipment", datasetId)}
          className="rounded-md border border-border px-4 py-2 text-sm hover:bg-white/5"
        >
          View equipment
        </Link>
        <Link
          href={withDataset("/timeline", datasetId)}
          className="rounded-md border border-border px-4 py-2 text-sm hover:bg-white/5"
        >
          Explore timeline
        </Link>
      </div>
    </div>
  );
}
