"use client";

export const dynamic = "force-dynamic";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getEquipmentList, ApiError } from "@/lib/api";
import type { EquipmentListResponse } from "@/lib/types";
import { useDataset, withDataset } from "@/lib/useDataset";
import { Card, StatusDot, EmptyState, Spinner, ErrorBanner, fmtNum } from "@/components/ui";

export default function EquipmentPage() {
  const [datasetId] = useDataset();
  const [data, setData] = useState<EquipmentListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!datasetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getEquipmentList(datasetId)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load equipment."))
      .finally(() => setLoading(false));
  }, [datasetId]);

  if (!datasetId)
    return <EmptyState title="No dataset selected" body="Upload and train a dataset first." />;
  if (loading) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;
  if (!data || data.equipment.length === 0)
    return <EmptyState title="No equipment found" body="Train the dataset to generate results." />;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-white">Equipment</h1>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.equipment.map((eq) => (
          <Link key={eq.equipment_id} href={withDataset(`/equipment/${encodeURIComponent(eq.equipment_id)}`, datasetId)}>
            <Card className="flex flex-col gap-3 h-full hover:border-accent/50 transition">
              <div className="flex items-center justify-between">
                <span className="font-medium text-white">{eq.equipment_id}</span>
                <StatusDot status={eq.status} />
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <Metric label="Observations" value={eq.n_scored_observations.toLocaleString()} />
                <Metric label="Abnormal obs." value={eq.n_abnormal_observations.toLocaleString()} />
                <Metric label="Abnormal periods" value={eq.n_abnormal_periods.toLocaleString()} />
                <Metric label="High priority" value={eq.high_priority_periods.toLocaleString()} />
              </div>
              <div className="text-xs text-slate-500">
                Avg energy: {fmtNum(eq.avg_actual_energy_kwh)} kWh
              </div>
            </Card>
          </Link>
        ))}
      </div>
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
