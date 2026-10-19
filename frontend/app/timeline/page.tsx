"use client";

export const dynamic = "force-dynamic";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getTimeline, getEquipmentList, ApiError } from "@/lib/api";
import type { TimelineResponse } from "@/lib/types";
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

export default function TimelinePage() {
  const [datasetId] = useDataset();
  const searchParams = useSearchParams();
  const initialEquipment = searchParams?.get("equipment") || "";
  const [equipmentFilter, setEquipmentFilter] = useState(initialEquipment);
  const [equipmentOptions, setEquipmentOptions] = useState<string[]>([]);
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) return;
    getEquipmentList(datasetId)
      .then((r) => setEquipmentOptions(r.equipment.map((e) => e.equipment_id)))
      .catch(() => {});
  }, [datasetId]);

  useEffect(() => {
    if (!datasetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getTimeline(datasetId, equipmentFilter || undefined)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load timeline."))
      .finally(() => setLoading(false));
  }, [datasetId, equipmentFilter]);

  if (!datasetId)
    return <EmptyState title="No dataset selected" body="Upload and train a dataset first." />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-semibold text-white">Timeline</h1>
        <select
          value={equipmentFilter}
          onChange={(e) => setEquipmentFilter(e.target.value)}
          className="rounded-md border border-border bg-panel px-3 py-1.5 text-sm text-slate-200"
        >
          <option value="">All equipment</option>
          {equipmentOptions.map((eq) => (
            <option key={eq} value={eq}>
              {eq}
            </option>
          ))}
        </select>
      </div>

      {loading && <Spinner />}
      {error && <ErrorBanner message={error} />}

      {data && (
        <>
          <Card>
            <h2 className="font-medium text-white mb-4">Abnormal periods</h2>
            {data.abnormal_periods.length === 0 ? (
              <p className="text-sm text-slate-500">No abnormal periods found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>Equipment</th>
                      <th>Start</th>
                      <th>End</th>
                      <th>Duration (min)</th>
                      <th>Severity</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.abnormal_periods.map((p) => (
                      <tr key={p.period_id}>
                        <td>{p.equipment_id}</td>
                        <td>{fmtDate(p.start_time)}</td>
                        <td>{fmtDate(p.end_time)}</td>
                        <td>
                          {p.duration_minutes === 0
                            ? "Single observation"
                            : `${fmtNum(p.duration_minutes, 0)} min`}
                        </td>
                        <td>
                          <SeverityBadge severity={p.severity_label} />
                        </td>
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

          <Card>
            <h2 className="font-medium text-white mb-4">
              Flagged abnormal observations ({data.abnormal_observations.length})
            </h2>
            {data.abnormal_observations.length === 0 ? (
              <p className="text-sm text-slate-500">No individual observations flagged.</p>
            ) : (
              <div className="max-h-96 overflow-y-auto overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Equipment</th>
                      <th>Actual (kWh)</th>
                      <th>Expected (kWh)</th>
                      <th>Unusualness</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.abnormal_observations.slice(0, 300).map((r, i) => (
                      <tr key={`${r.equipment_id}-${r.timestamp}-${i}`}>
                        <td>{fmtDate(r.timestamp)}</td>
                        <td>{r.equipment_id}</td>
                        <td>{fmtNum(r.actual_energy)}</td>
                        <td>{fmtNum(r.expected_energy)}</td>
                        <td>{fmtNum(r.unusualness_score, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
