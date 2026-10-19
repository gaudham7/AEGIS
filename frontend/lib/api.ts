import type {
  UploadResponse,
  TrainStatus,
  OverviewResponse,
  EquipmentListResponse,
  EquipmentDetailResponse,
  TimelineResponse,
  AnomaliesResponse,
  AbnormalPeriod,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function uploadDataset(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/api/upload", { method: "POST", body: form });
}

export async function trainDataset(datasetId: string): Promise<TrainStatus> {
  return request<TrainStatus>(`/api/train/${datasetId}`, { method: "POST" });
}

export async function getTrainingStatus(datasetId: string): Promise<TrainStatus> {
  return request<TrainStatus>(`/api/train/status/${datasetId}`);
}

export async function getOverview(datasetId: string): Promise<OverviewResponse> {
  return request<OverviewResponse>(`/api/overview/${datasetId}`);
}

export async function getEquipmentList(datasetId: string): Promise<EquipmentListResponse> {
  return request<EquipmentListResponse>(`/api/equipment/${datasetId}`);
}

export async function getEquipmentDetail(
  datasetId: string,
  equipmentId: string
): Promise<EquipmentDetailResponse> {
  return request<EquipmentDetailResponse>(
    `/api/equipment/${datasetId}/${encodeURIComponent(equipmentId)}`
  );
}

export async function getTimeline(
  datasetId: string,
  equipmentId?: string
): Promise<TimelineResponse> {
  const qs = equipmentId ? `?equipment_id=${encodeURIComponent(equipmentId)}` : "";
  return request<TimelineResponse>(`/api/timeline/${datasetId}${qs}`);
}

export async function getAnomalies(
  datasetId: string,
  params?: { equipment_id?: string; severity?: string }
): Promise<AnomaliesResponse> {
  const search = new URLSearchParams();
  if (params?.equipment_id) search.set("equipment_id", params.equipment_id);
  if (params?.severity) search.set("severity", params.severity);
  const qs = search.toString() ? `?${search.toString()}` : "";
  return request<AnomaliesResponse>(`/api/anomalies/${datasetId}${qs}`);
}

export async function getAnomalyDetail(
  datasetId: string,
  periodId: string
): Promise<AbnormalPeriod> {
  return request<AbnormalPeriod>(`/api/anomalies/${datasetId}/${periodId}`);
}

export { ApiError };
