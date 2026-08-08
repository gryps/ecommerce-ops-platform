export type View = "flow" | "materials" | "copy" | "music" | "production";
export type ImageView = "overview" | "batches" | "products" | "plans" | "review" | "delivery";
export type PlatformModule = "video" | "images" | "models";

export type User = {
  id: string;
  username: string;
  is_active: boolean;
};

export type ModelProfile = {
  stage: string;
  label: string;
  base_url: string;
  model: string;
  temperature: number;
  proxy_url: string;
  api_key: string;
  has_api_key: boolean;
  api_key_mask: string;
};

export type ModelProfilesResponse = {
  profiles: ModelProfile[];
};

export type Product = {
  id: number;
  system_code: string;
  name: string;
  status: string;
  asset_count: number;
};

export type SourceVideo = { name: string; relative_path: string; path: string };
export type SourceImage = { name: string; relative_path: string; path: string };

export type ImageReference = {
  type: string;
  label: string;
  expected_file_name: string;
  purpose: string;
  uploaded: boolean;
  id?: string | null;
  file_name: string;
  url: string;
  updated_at?: string | null;
};

export type ImageProduct = {
  id: string;
  product_code: string;
  name: string;
  status: string;
  reference_count: number;
  reference_total: number;
  missing_reference_types: string[];
  references: ImageReference[];
  source_images: SourceImage[];
  created_at: string;
  updated_at: string;
};

export type ImageTemplate = {
  id: string;
  name: string;
  image_type: string;
  aspect_ratio: string;
  scene: string;
  negative: string;
  recommended_models: string[];
  input_image_types: string[];
};

export type ImagePrompt = {
  template_id: string;
  template_name: string;
  recommended_models: string[];
  input_image_types: string[];
  prompt_zh: string;
  negative_prompt_zh: string;
  fidelity_rules: string[];
  checkpoints: string[];
};

export type ImageTask = {
  id: string;
  product_id: string;
  template_id: string;
  template_name: string;
  model: string;
  prompt: string;
  negative_prompt: string;
  input_image_types: string[];
  output_plan: Record<string, number>;
  status: string;
  output_images: Array<{ name: string; path: string; image_type: string; url: string }>;
  review_status: string;
  review_issues: string[];
  review_comment: string;
  created_at: string;
  updated_at: string;
};

export type BrowserSession = { id: string; platform_url: string; status: "running" | "stopped" };
export type PlatformField = {
  key: string;
  label: string;
  type: "text" | "number" | "select" | "textarea" | "rich_text" | "sku_matrix";
  required: boolean;
  default: unknown;
  options: string[];
  selector: string;
};
export type PlatformImageSlot = { key: string; label: string; required: boolean; max_count: number; selector: string };
export type PlatformTemplate = {
  id: string;
  name: string;
  platform: string;
  entry_url: string;
  fields: PlatformField[];
  image_slots: PlatformImageSlot[];
  status: string;
  created_at: string;
  updated_at: string;
};
export type PlatformProfile = {
  id: string;
  product_id: string;
  template_id: string;
  values: Record<string, unknown>;
  image_selections: Record<string, Array<{ task_id: string; output_index: number; name: string; url: string }>>;
  status: string;
  draft_url: string;
  process_log: Array<{ at: string; detail: string }>;
  created_at: string;
  updated_at: string;
};

export type Tag = { id: string; name: string; category: string; category_id: string; product_id?: number };
export type TagCategory = { id: string; name: string };
export type ImageSourceAsset = { id: string; name: string; status: string; url: string; created_at: string; updated_at: string };
export type SourceImageGroup = { id: string; name: string; images: SourceImage[]; basis: string; status: string };
export type ClassifiedMaterial = {
  id: string;
  product_id: number;
  product_name: string;
  filename: string;
  source_path: string;
  status: string;
  duration_seconds: number;
  width: number;
  height: number;
  tags: Tag[];
};

export type CopyItem = {
  id: string;
  content: string;
  product_id: number | null;
  product_name?: string;
  source: string;
};
export type CopyCandidate = { id: string; content: string; status: string; rejection_reason?: string; library_content_id?: string | null };
export type CopyBatch = { id: string; sequence_number: number; created_at: string; copies: CopyCandidate[] };
export type CopyAnalysis = {
  id: string;
  source_mode: "input" | "adopted_history";
  source_text: string;
  language_analysis: Record<string, string>;
  audience_analysis: Record<string, string>;
  expert_role: string;
  created_at: string;
  batches: CopyBatch[];
};
export type VoiceCatalogItem = {
  sequence: number;
  name: string;
  voice: string;
  gender: string;
  age: string;
  trait: string;
  scenario: string;
  language: string;
  preview_filename: string;
  preview_ready?: boolean;
};
export type Narration = {
  id: string;
  approved_text: string;
  recognized_text: string;
  voice_source: "human" | "model";
  text_source: "human" | "model";
  subtitle_cues: Array<Record<string, unknown>>;
  status: string;
};
export type MusicResource = {
  id: string;
  name: string;
  status: string;
  duration_seconds: number;
  source_type: string;
  custom_tags: string[];
  error?: string;
};
export type JianyingDraft = {
  id: string;
  name: string;
  draft_path: string;
  status: string;
  created_at: string;
  error: string;
  copy_content_id?: string | null;
  narration_asset_id?: string | null;
  music_resource_id?: string | null;
  snapshot?: Record<string, unknown>;
};
export type DraftDirectory = { path: string; windows_path: string; source: string; exists: boolean };

export type DeleteConfirmation = {
  title: string;
  message: string;
  onConfirm: (optionSelected?: boolean) => Promise<boolean | void>;
  optionLabel?: string;
  confirmLabel?: string;
};

export type TrackedOperationStatus = {
  operation_id: string;
  kind: string;
  status: "unknown" | "processing" | "completed" | "failed";
  detail: string;
};
