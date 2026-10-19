export interface UploadResponse {
  dataset_id: string;
  filename: string;
  row_count: number;
  column_check: Record<string, unknown>;
  equipment_discovered: string[];
  time_range: Record<string, string | null>;
  missing_values: Record<string, unknown>;
  temporal_gaps: Record<string, unknown>;
  ready_for_training: boolean;
  message: string;
}

export interface TrainStatus {
  dataset_id: string;
  status: "not_started" | "running" | "completed" | "failed";
  message?: string | null;
  metrics?: Record<string, unknown> | null;
  equipment?: string[] | null;
  anomaly_summary?: Record<string, unknown> | null;
}

export interface ContributingFactor {
  feature: string;
  direction: string;
  [key: string]: unknown;
}

export interface PeriodInsight {
  summary: string;
  evidence: string[];
  contributing_factors: ContributingFactor[];
  recommended_investigation: string[];
  disclaimer: string;
}

export interface ScoredObservation {
  timestamp: string;
  equipment_id: string;
  actual_energy: number;
  expected_energy: number;
  residual: number;
  unusualness_score: number;
  is_abnormal: boolean;
  [key: string]: unknown;
}

export interface AbnormalPeriod {
  period_id: string;
  equipment_id: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  n_abnormal_observations: number;
  n_observations_in_period: number;
  avg_unusualness: number;
  max_unusualness: number;
  avg_residual: number;
  avg_actual_energy: number;
  avg_expected_energy: number;
  severity_score: number;
  severity_label: "high" | "medium" | "low";
  recurrence_count_for_equipment: number;
  observation_rows: ScoredObservation[];
  insight?: PeriodInsight;
  operating_context?: Record<string, unknown>;
}

export interface OverviewResponse {
  dataset_id: string;
  equipment_discovered: string[];
  equipment_count: number;
  monitoring_status: string;
  metrics: Record<string, unknown> | null;
  anomaly_summary: Record<string, unknown> | null;
  priority_abnormal_periods: AbnormalPeriod[];
  recent_events: AbnormalPeriod[];
  energy_statistics: {
    avg_actual_energy_kwh: number | null;
    n_scored_observations: number;
  };
}

export interface EquipmentSummary {
  equipment_id: string;
  n_scored_observations: number;
  n_abnormal_observations: number;
  n_abnormal_periods: number;
  high_priority_periods: number;
  avg_actual_energy_kwh: number | null;
  status: "attention_needed" | "monitor" | "normal";
}

export interface EquipmentListResponse {
  equipment: EquipmentSummary[];
}

export interface EquipmentDetailResponse {
  equipment_id: string;
  energy_history: ScoredObservation[];
  abnormal_periods: AbnormalPeriod[];
  n_observations: number;
  n_abnormal_observations: number;
}

export interface TimelineResponse {
  abnormal_observations: ScoredObservation[];
  abnormal_periods: AbnormalPeriod[];
}

export interface AnomaliesResponse {
  count: number;
  abnormal_periods: AbnormalPeriod[];
}
