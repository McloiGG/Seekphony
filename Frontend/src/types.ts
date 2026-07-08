export interface Scores {
  overall: number;
  pitch: number;
  rhythm: number;
  stability: number;
  coverage: number;
  audio_quality: number;
}

export interface Metrics {
  key_shift_semitones?: number | null;
  pitch_error_cents?: number | null;
  timing_offset_ms?: number | null;
  voiced_coverage: number;
  reference_voiced_ratio: number;
  performance_voiced_ratio: number;
  confidence: number;
  reference_duration_seconds: number;
  performance_duration_seconds: number;
}

export interface ProblemSegment {
  start_seconds: number;
  end_seconds: number;
  issue: "missing_voice" | "pitch" | "timing" | "low_confidence";
  severity: "low" | "medium" | "high";
  detail: string;
}

export interface ExplanationContent {
  summary: string;
  strengths: string[];
  focus_areas: string[];
  practice_steps: string[];
}

export interface Explanation {
  status: "available" | "unavailable" | "error";
  provider: string;
  error?: string | null;
  content?: ExplanationContent | null;
}

export interface EvaluationResponse {
  status: "completed";
  evaluation_id: number;
  created_at: string;
  reference_filename: string;
  performance_filename: string;
  clip_start_seconds: number;
  clip_duration_seconds: number;
  performance_start_seconds: number;
  scores: Scores;
  metrics: Metrics;
  segments: ProblemSegment[];
  warnings: string[];
  explanation: Explanation;
}

export interface EvaluationListResponse {
  status: "ok";
  evaluations: EvaluationResponse[];
}

export interface HealthResponse {
  status: "ok";
  service: string;
  api_prefix: string;
  database: {
    kind: string;
    postgres_configured: boolean;
  };
  providers: {
    gemini_configured: boolean;
  };
  limits: {
    max_upload_bytes: number;
    min_clip_seconds: number;
    max_clip_seconds: number;
  };
}

export interface ApiErrorDetail {
  status: string;
  message: string;
  details?: unknown;
  retryable?: boolean;
  fallback_used?: boolean;
}
