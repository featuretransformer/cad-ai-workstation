// ── Core types shared across frontend ──────────────────────────────

export interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Design {
  id: string;
  session_id: string;
  version: number;
  prompt: string;
  cad_code?: string;
  feature_tree: FeatureTree;
  geometry_valid: boolean;
  dfm_report: DFMReport;
  engineering_report: EngineeringReport;
  cost_estimate: CostEstimate;
  safety_report: SafetyReport;
  alternatives: Alternative[];
  confidence_scores: Record<string, number>;
  created_at: string;
}

export interface FeatureTree {
  root?: {
    id: string;
    name: string;
    type: string;
    children: Feature[];
  };
}

export interface Feature {
  id: string;
  name: string;
  type: "primitive" | "feature" | "modify" | "pattern";
  params: string;
  line: number;
  suppressed: boolean;
}

export interface AgentLog {
  id: string;
  design_id: string;
  agent_name: string;
  status: "running" | "done" | "error";
  message?: string;
  confidence: number;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface DFMReport {
  overall_score?: number;
  process?: string;
  issues?: DFMIssue[];
  recommendations?: string[];
  skipped?: boolean;
}

export interface DFMIssue {
  severity: "error" | "warning" | "info";
  rule: string;
  description: string;
  recommendation: string;
}

export interface EngineeringReport {
  material_properties?: {
    name: string;
    density_g_cm3: number;
    yield_strength_mpa: number;
    elastic_modulus_gpa: number;
  };
  mass_estimate_kg?: number;
  safety_factor_estimate?: number;
  recommended_surface_finish?: string;
  skipped?: boolean;
}

export interface CostEstimate {
  material_cost_usd?: number;
  machining_time_hours?: number;
  total_unit_cost_usd?: number;
  cost_drivers?: string[];
  skipped?: boolean;
}

export interface SafetyReport {
  overall_compliance?: "pass" | "warning" | "fail";
  issues?: SafetyIssue[];
  skipped?: boolean;
}

export interface SafetyIssue {
  standard: string;
  severity: "critical" | "major" | "minor";
  description: string;
}

export interface Alternative {
  id: number;
  name: string;
  description: string;
  tradeoffs: string;
  code: string;
}

export interface ExportArtifact {
  id: string;
  design_id: string;
  format: string;
  file_path: string;
  file_size_bytes: number;
}

export interface GenerateResponse {
  task_id: string;
  design_id: string;
  message: string;
}
// ── WebSocket Event types ───────────────────────────────────────────

export type WSEventType =
  | "pipeline_started"
  | "agent_update"
  | "pipeline_complete"
  | "pipeline_error";

export interface WSEvent {
  type: WSEventType;
  agent?: string;
  display_name?: string;
  status?: string;
  confidence?: number;
  payload?: Record<string, unknown>;
  design_id?: string;
  message?: string;
  error?: string;
  geometry_valid?: boolean;
  export_paths?: Record<string, string>;
  confidence_scores?: Record<string, number>;
}
