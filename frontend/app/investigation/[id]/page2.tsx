"use client";

export const dynamic = "force-dynamic";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { getAnomalyDetail, ApiError } from "@/lib/api";
import type { AbnormalPeriod } from "@/lib/types";
import { useDataset, withDataset } from "@/lib/useDataset";
import {
  Card,
  SeverityBadge,
  EmptyState,
  Spinner,
  ErrorBanner,
  fmtDate,
  fmtNum,
} from "@/components/ui";

export default function InvestigationPage({ params }: { params: { id: string } }) {
  const periodId = params.id;
  const [datasetId] = useDataset();
  const [period, setPeriod] = useState<AbnormalPeriod | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getAnomalyDetail(datasetId, periodId)
      .then(setPeriod)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load this period."))
      .finally(() => setLoading(false));
  }, [datasetId, periodId]);

  if (!datasetId)
    return <EmptyState title="No dataset selected" body="Upload and train a dataset first." />;
  if (loading) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!period) return null;

  const insight = period.insight;
  const factorData = (insight?.contributing_factors || []).slice(0, 8).map((f: any) => ({
    feature: f.feature,
    magnitude: Math.abs(f.shap_value ?? f.magnitude ?? f.value ?? 0),
    direction: f.direction,
  }));

  const obsData = (period.observation_rows || []).map((r) => ({
    timestamp: fmtDate(r.timestamp),
    actual: r.actual_energy,
    expected: r.expected_energy,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-semibold text-white">{period.equipment_id}</h1>
            <SeverityBadge severity={period.severity_label} />
          </div>
          <p className="text-sm text-slate-400">
            {fmtDate(period.start_time)} → {fmtDate(period.end_time)} ·{" "}
            {period.duration_minutes === 0 || period.n_observations_in_period === 1
              ? "Single observation"
              : `${fmtNum(period.duration_minutes, 0)} minutes`}{" "}
            · severity score {fmtNum(period.severity_score, 0)}/100
          </p>
        </div>
        <Link
          href={withDataset(`/equipment/${encodeURIComponent(period.equipment_id)}`, datasetId)}
          className="text-sm text-accent underline"
        >
          View equipment
        </Link>
      </div>

      {insight && (
        <Card>
          <h2 className="font-medium text-white mb-2">{insight.summary}</h2>
          <ul className="list-disc list-inside text-sm text-slate-300 flex flex-col gap-1 mt-2">
            {insight.evidence.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
          <p className="text-xs text-slate-500 mt-4 border-t border-border pt-3">
            {insight.disclaimer}
          </p>
        </Card>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <h2 className="font-medium text-white mb-4">Actual vs. expected during period</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={obsData}>
                <CartesianGrid stroke="#232c38" strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tick={{ fontSize: 9, fill: "#94a3b8" }} minTickGap={30} />
                <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <Tooltip contentStyle={{ background: "#121821", border: "1px solid #232c38", fontSize: 12 }} />
                <Bar dataKey="expected" fill="#334155" name="Expected" />
                <Bar dataKey="actual" fill="#ef4444" name="Actual" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm mt-4">
            <Metric label="Avg actual (kWh)" value={fmtNum(period.avg_actual_energy)} />
            <Metric label="Avg expected (kWh)" value={fmtNum(period.avg_expected_energy)} />
            <Metric label="Avg residual (kWh)" value={fmtNum(period.avg_residual)} />
            <Metric label="Max unusualness" value={fmtNum(period.max_unusualness, 2)} />
            <Metric
              label="Recurrence for equipment"
              value={String(period.recurrence_count_for_equipment)}
            />
            <Metric
              label="Abnormal / total obs."
              value={`${period.n_abnormal_observations} / ${period.n_observations_in_period}`}
            />
          </div>
        </Card>

        <Card>
          <h2 className="font-medium text-white mb-4">Model-associated contributing factors</h2>
          {factorData.length === 0 ? (
            <p className="text-sm text-slate-500">
              No contributing-factor breakdown available for this period.
            </p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={factorData} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid stroke="#232c38" strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                  <YAxis
                    dataKey="feature"
                    type="category"
                    width={140}
                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                  />
                  <Tooltip contentStyle={{ background: "#121821", border: "1px solid #232c38", fontSize: 12 }} />
                  <Bar dataKey="magnitude" fill="#3ba7ff" name="Influence" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="text-xs text-slate-500 mt-2">
            Relative influence on the model&apos;s expected-energy prediction for this
            period, not a confirmed physical cause.
          </p>
        </Card>
      </div>

      {insight && insight.recommended_investigation.length > 0 && (
        <Card>
          <h2 className="font-medium text-white mb-3">Recommended investigation</h2>
          <ol className="list-decimal list-inside text-sm text-slate-300 flex flex-col gap-1.5">
            {insight.recommended_investigation.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-slate-200">{value}</span>
    </div>
  );
}
