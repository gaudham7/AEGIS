"use client";

export const dynamic = "force-dynamic";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDataset, trainDataset, getTrainingStatus, ApiError } from "@/lib/api";
import type { UploadResponse, TrainStatus } from "@/lib/types";
import { useDataset, withDataset } from "@/lib/useDataset";
import { Card, ErrorBanner, Spinner } from "@/components/ui";

export default function UploadPage() {
  const router = useRouter();
  const [, setDatasetId] = useDataset();
  const fileInput = useRef<HTMLInputElement>(null);

  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [training, setTraining] = useState(false);
  const [trainStatus, setTrainStatus] = useState<TrainStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }
    setError(null);
    setUploading(true);
    setUploadResult(null);
    setTrainStatus(null);
    try {
      const result = await uploadDataset(file);
      setUploadResult(result);
      setDatasetId(result.dataset_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleTrain() {
    if (!uploadResult) return;
    setError(null);
    setTraining(true);
    try {
      await trainDataset(uploadResult.dataset_id);
      // poll status until completed/failed
      let status = await getTrainingStatus(uploadResult.dataset_id);
      let attempts = 0;
      while (status.status === "running" && attempts < 120) {
        await new Promise((r) => setTimeout(r, 1500));
        status = await getTrainingStatus(uploadResult.dataset_id);
        attempts += 1;
      }
      setTrainStatus(status);
      if (status.status === "completed") {
        setTimeout(() => {
          router.push(withDataset("/overview", uploadResult.dataset_id));
        }, 800);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Training failed.");
    } finally {
      setTraining(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-semibold text-white">Upload dataset</h1>
        <p className="text-sm text-slate-400 mt-1">
          CSV must conform to the Data Specification: timestamp, equipment_id, and
          the operational/environmental measurement columns.
        </p>
      </div>

      {error && <ErrorBanner message={error} />}

      <Card className="flex flex-col gap-4">
        <input
          ref={fileInput}
          type="file"
          accept=".csv"
          className="text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-white/10 file:px-3 file:py-2 file:text-slate-200 hover:file:bg-white/20"
        />
        <div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-black hover:opacity-90 disabled:opacity-50"
          >
            {uploading ? "Validating…" : "Upload & validate"}
          </button>
        </div>
      </Card>

      {uploading && <Spinner />}

      {uploadResult && (
        <Card className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-white">Validation report</h2>
            <span
              className={`text-xs rounded-full px-2 py-0.5 border ${
                uploadResult.ready_for_training
                  ? "border-low/40 text-low bg-low/10"
                  : "border-medium/40 text-medium bg-medium/10"
              }`}
            >
              {uploadResult.ready_for_training ? "Ready for training" : "Check data"}
            </span>
          </div>
          <p className="text-sm text-slate-400">{uploadResult.message}</p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <Info label="Dataset ID" value={uploadResult.dataset_id} />
            <Info label="Rows" value={uploadResult.row_count.toLocaleString()} />
            <Info
              label="Equipment discovered"
              value={uploadResult.equipment_discovered.join(", ") || "—"}
            />
            <Info
              label="Time range"
              value={`${uploadResult.time_range?.start ?? "—"} → ${
                uploadResult.time_range?.end ?? "—"
              }`}
            />
          </div>

          <details className="text-xs text-slate-400">
            <summary className="cursor-pointer text-slate-300">Missing values &amp; gaps</summary>
            <pre className="mt-2 overflow-x-auto rounded-md bg-black/30 p-3">
              {JSON.stringify(
                { missing_values: uploadResult.missing_values, temporal_gaps: uploadResult.temporal_gaps },
                null,
                2
              )}
            </pre>
          </details>

          <div className="pt-2">
            <button
              onClick={handleTrain}
              disabled={training}
              className="rounded-md bg-white text-black px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
              {training ? "Training…" : "Train model"}
            </button>
          </div>

          {training && <Spinner />}

          {trainStatus && (
            <div className="text-sm">
              {trainStatus.status === "completed" ? (
                <p className="text-low">
                  Training complete. Redirecting to overview…
                </p>
              ) : trainStatus.status === "failed" ? (
                <ErrorBanner message={trainStatus.message || "Training failed."} />
              ) : (
                <p className="text-slate-400">{trainStatus.message}</p>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <span className="text-slate-200 break-words">{value}</span>
    </div>
  );
}
