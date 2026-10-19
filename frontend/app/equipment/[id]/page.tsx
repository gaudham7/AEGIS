"use client";

export const dynamic = "force-dynamic";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { getEquipmentDetail, ApiError } from "@/lib/api";
import type { EquipmentDetailResponse } from "@/lib/types";
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

export default function EquipmentDetailPage({ params }: { params: { id: string } }) {
  const equipmentId = decodeURIComponent(params.id);
  const [datasetId] = useDataset();
  const [data, setData] = useState<EquipmentDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getEquipmentDetail(datasetId, equipmentId)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load equipment."))
      .finally(() => setLoading(false));
  }, [datasetId, equipmentId]);

  if (!datasetId)
    return <EmptyState title="No dataset selected" body="Upload and train a dataset first." />;
  if (loading) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  const chartData = data.energy_history
    .filter((_, i) => i % Math.max(1, Math.floor(data.energy_history.length / 400)) === 0)
    .map((r) => ({
      timestamp: fmtDate(r.timestamp),
      actual: r.actual_energy,
      expected: r.expected_energy,
      abnormal: r.is_abnormal ? r.actual_energy : null,
    }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">{data.equipment_id}</h1>
          <p className="text-sm text-slate-400 mt-1">
            {data.n_observations.toLocaleString()} observations ·{" "}
            {data.n_abnormal_observations.toLocaleString()} flagged abnormal
          </p>
        </div>
        <Link
          href={withDataset(`/timeline?equipment=${encodeURIComponent(data.equipment_id)}`, datasetId)}
          className="text-sm text-accent underline"
        >
          View on timeline
        </Link>
      </div>

      <Card>
        <h2 className="font-medium text-white mb-4">
          Actual vs. expected energy consumption (kWh)
        </h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid stroke="#232c38" strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: "#94a3b8" }} minTickGap={40} />
              <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} />
              <Tooltip
                contentStyle={{ background: "#121821", border: "1px solid #232c38", fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="actual" stroke="#3ba7ff" dot={false} name="Actual" strokeWidth={1.5} />
              <Line
                type="monotone"
                dataKey="expected"
                stroke="#94a3b8"
                dot={false}
                strokeDasharray="4 3"
                name="Expected"
                strokeWidth={1.5}
              />
              <Line
                type="monotone"
                dataKey="abnormal"
                stroke="#ef4444"
                dot={{ r: 2 }}
                name="Flagged abnormal"
                strokeWidth={0}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Chart sampled for readability; investigate individual periods below for full detail.
        </p>
      </Card>

      <Card>
        <h2 className="font-medium text-white mb-4">Abnormal periods for this equipment</h2>
        {data.abnormal_periods.length === 0 ? (
          <p className="text-sm text-slate-500">No abnormal periods detected for this equipment.</p>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Start</th>
                  <th>End</th>
                  <th>Duration (min)</th>
                  <th>Severity</th>
                  <th>Score</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.abnormal_periods.map((p) => (
                  <tr key={p.period_id}>
                    <td>{fmtDate(p.start_time)}</td>
                    <td>{fmtDate(p.end_time)}</td>
                    <td>{fmtNum(p.duration_minutes, 0)}</td>
                    <td>
                      <SeverityBadge severity={p.severity_label} />
                    </td>
                    <td>{fmtNum(p.severity_score, 0)}</td>
                    <td>
                      <Link
                        href={withDataset(`/investigation/${p.period_id}`, datasetId)}
                        className="text-accent underline"
                      >
                        Investigate
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
