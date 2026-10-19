"use client";

export const dynamic = "force-dynamic";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDataset, trainDataset, getTrainingStatus, ApiError } from "@/lib/api";
import type { UploadResponse, TrainStatus } from "@/lib/types";
import { useDataset, withDataset } from "@/lib/useDataset";
import { useToast } from "@/components/Toast";
import { Card, ErrorBanner, ProgressStages, DataQualitySummary } from "@/components/ui";

export default function UploadPage() {
  const router = useRouter();
  const [, setDatasetId] = useDataset();
  const fileInput = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const [busy, setBusy] = useState<"idle" | "uploading" | "training">("idle");
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [trainStatus, setTrainStatus] = useState<TrainStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      const msg = "Please choose a .csv file.";
      setError(msg);
      toast.show(msg, "error");
      return;
    }

    setError(null);
    setUploadResult(null);
    setTrainStatus(null);
    setBusy("uploading");

    let result: UploadResponse;
    try {
      result = await uploadDataset(file);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Upload failed.";
      setError(msg);
      toast.show(msg, "error");
      setBusy("idle");
      return;
    }

    setUploadResult(result);
    setDatasetId(result.dataset_id);
    toast.show(
      result.ready_for_training
        ? "Dataset uploaded and validated."
        : "Dataset uploaded, but it may be too small or incomplete for reliable training.",
      result.ready_for_training ? "success" : "info"
    );

    if (result.ready_for_training) {
      await startTraining(result.dataset_id);
    } else {
      setBusy("idle");
    }
  }

  async function startTraining(datasetId: string) {
    setBusy("training");
    setError(null);
    try {
      await trainDataset(datasetId);
      let status = await getTrainingStatus(datasetId);
      let attempts = 0;
      while (status.status === "running" && attempts < 240) {
        setTrainStatus(status);
        await new Promise((r) => setTimeout(r, 1200));
        status = await getTrainingStatus(datasetId);
        attempts += 1;
      }
      setTrainStatus(status);

      if (status.status === "completed") {
        toast.show("Analysis ready.", "success");
        setTimeout(() => {
          router.push(withDataset("/overview", datasetId));
        }, 700);
      } else if (status.status === "failed") {
        toast.show(status.message || "Training failed.", "error");
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Training failed.";
      setError(msg);
      toast.show(msg, "error");
    } finally {
      setBusy("idle");
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-semibold text-white">Upload dataset</h1>
        <p className="text-sm text-slate-400 mt-1">
          Drop in a CSV of chiller readings. We&apos;ll check it, then automatically learn
          what normal behaviour looks like and flag anything unusual — no extra steps.
        </p>
      </div>

      {error && <ErrorBanner message={error} />}

      <Card>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFile(e.dataTransfer.files?.[0]);
          }}
          onClick={() => fileInput.current?.click()}
          className={`flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center cursor-pointer transition ${
            dragOver ? "border-accent bg-accent/5" : "border-border hover:border-slate-500"
          }`}
        >
          <span className="text-sm text-slate-300">
            Drag and drop a CSV here, or click to choose a file
          </span>
          <span className="text-xs text-slate-500">.csv only</span>
          <input
            ref={fileInput}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
        </div>
      </Card>

      {busy === "uploading" && (
        <Card>
          <ProgressStages stage="ingesting" message="Uploading and validating your file…" />
        </Card>
      )}

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

          <div className="border-t border-border pt-3">
            <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
              Data quality
            </h3>
            <DataQualitySummary
              missingValues={uploadResult.missing_values as any}
              temporalGaps={uploadResult.temporal_gaps as any}
            />
          </div>

          {!uploadResult.ready_for_training && busy === "idle" && !trainStatus && (
            <div className="pt-2">
              <button
                onClick={() => startTraining(uploadResult.dataset_id)}
                className="rounded-md bg-white text-black px-4 py-2 text-sm font-medium hover:opacity-90"
              >
                Train anyway
              </button>
            </div>
          )}

          {busy === "training" && (
            <ProgressStages stage={trainStatus?.stage} message={trainStatus?.message} />
          )}

          {trainStatus?.status === "failed" && (
            <ErrorBanner message={trainStatus.message || "Training failed."} />
          )}
          {trainStatus?.status === "completed" && (
            <p className="text-sm text-low">Analysis ready. Taking you to the overview…</p>
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
