"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const STORAGE_KEY = "aegis_dataset_id";

/** Resolves the active dataset id from ?dataset=<id> in the URL, falling
 * back to the last one stored in this browser. Also persists whichever
 * id is resolved so other pages pick it up without re-specifying it. */
export function useDataset(): [string | null, (id: string) => void] {
  const searchParams = useSearchParams();
  const fromUrl = searchParams?.get("dataset") || null;
  const [datasetId, setDatasetIdState] = useState<string | null>(fromUrl);

  useEffect(() => {
    if (fromUrl) {
      setDatasetIdState(fromUrl);
      window.localStorage.setItem(STORAGE_KEY, fromUrl);
    } else {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored) setDatasetIdState(stored);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fromUrl]);

  const setDatasetId = (id: string) => {
    window.localStorage.setItem(STORAGE_KEY, id);
    setDatasetIdState(id);
  };

  return [datasetId, setDatasetId];
}

export function withDataset(path: string, datasetId: string | null): string {
  if (!datasetId) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}dataset=${encodeURIComponent(datasetId)}`;
}
