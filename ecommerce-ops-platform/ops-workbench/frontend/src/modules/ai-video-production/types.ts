export type AssetKind = "product" | "character" | "environment" | "prop" | "keyframe" | "reference" | "output";

export interface ProductProject {
  id: string;
  name: string;
  product_name: string;
  selling_points: string;
  audience: string;
  tone: string;
  status: string;
}

export interface Asset {
  id: string;
  project_id: string;
  kind: AssetKind;
  name: string;
  file_path: string;
  preview_url: string;
  source: string;
  notes: string;
}

export interface Shot {
  id: string;
  project_id: string;
  order: number;
  title: string;
  duration_seconds: number;
  visual_goal: string;
  camera: string;
  prompt: string;
  negative_prompt: string;
  status: string;
}

export interface GenerationTask {
  id: string;
  project_id: string;
  engine: string;
  workflow_name: string;
  status: string;
  prompt: string;
  input_asset_ids: string[];
  provider_task_id: string;
  output_paths: string[];
  error: string;
}

export interface TaskEvent {
  id: string;
  task_id: string;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface WorkflowTemplate {
  name: string;
  label: string;
  description: string;
  default_engine: "comfyui" | "vendor_video";
  mode: "t2v" | "i2v" | "first_last_frame" | "workflow";
  required_asset_kinds: AssetKind[];
  available: boolean;
  availability_note: string;
}

export interface WorkbenchStore {
  projects: ProductProject[];
  assets: Asset[];
  shots: Shot[];
  tasks: GenerationTask[];
}

export type WorkbenchView = "overview" | "canvas" | "assets" | "director" | "shots" | "review" | "export";
