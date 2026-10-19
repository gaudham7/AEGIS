"use client";

export const dynamic = "force-dynamic";

import Link from "next/link";
import { useDataset, withDataset } from "@/lib/useDataset";
import { Card } from "@/components/ui";

export default function HomePage() {
  const [datasetId] = useDataset();

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto text-center pt-10">
      <div>
        <h1 className="text-3xl font-semibold text-white mb-2">AEGIS</h1>
        <p className="text-slate-400">
          Contextual anomaly detection for chiller equipment. Upload historical
          operational data, train the model, and investigate flagged behaviour.
        </p>
      </div>
      <Card className="flex flex-col gap-3 items-center">
        <p className="text-sm text-slate-400">
          {datasetId
            ? "You have a dataset in progress."
            : "Start by uploading a dataset that conforms to the Data Specification."}
        </p>
        <div className="flex gap-3">
          <Link
            href="/upload"
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-black hover:opacity-90"
          >
            Upload dataset
          </Link>
          {datasetId && (
            <Link
              href={withDataset("/overview", datasetId)}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium text-slate-200 hover:bg-white/5"
            >
              Go to overview
            </Link>
          )}
        </div>
      </Card>
    </div>
  );
}
