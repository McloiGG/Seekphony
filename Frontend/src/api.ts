import { apiBaseUrl } from "./config";
import type {
  ApiErrorDetail,
  EvaluationListResponse,
  EvaluationResponse,
  HealthResponse,
} from "./types";

const REQUEST_TIMEOUT_MS = 60000;

export class SeekphonyApiError extends Error {
  readonly statusCode?: number;
  readonly retryable: boolean;
  readonly code: string;

  constructor(
    message: string,
    options: { statusCode?: number; retryable?: boolean; code?: string } = {},
  ) {
    super(message);
    this.name = "SeekphonyApiError";
    this.statusCode = options.statusCode;
    this.retryable = options.retryable ?? false;
    this.code = options.code ?? "request_failed";
  }
}

export interface EvaluationPayload {
  reference: File;
  performance: Blob;
  performanceFilename: string;
  clipStartSeconds: number;
  clipDurationSeconds: number;
  performanceStartSeconds: number;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/v1/health");
}

export async function fetchEvaluations(limit = 5): Promise<EvaluationListResponse> {
  return requestJson<EvaluationListResponse>(`/api/v1/evaluations?limit=${limit}`);
}

export async function createEvaluation(payload: EvaluationPayload): Promise<EvaluationResponse> {
  const body = new FormData();
  body.append("reference", payload.reference, payload.reference.name);
  body.append("performance", payload.performance, payload.performanceFilename);
  body.append("clip_start_seconds", String(payload.clipStartSeconds));
  body.append("clip_duration_seconds", String(payload.clipDurationSeconds));
  body.append("performance_start_seconds", String(payload.performanceStartSeconds));
  return requestJson<EvaluationResponse>("/api/v1/evaluations", {
    method: "POST",
    body,
  });
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      signal: controller.signal,
    });
    const payload = await parseJson(response);
    if (!response.ok) {
      throw errorFromPayload(response.status, payload);
    }
    return payload as T;
  } catch (error) {
    if (error instanceof SeekphonyApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new SeekphonyApiError("Backend request timed out.", {
        code: "timeout",
        retryable: true,
      });
    }
    throw new SeekphonyApiError("Backend service is unreachable.", {
      code: "network_error",
      retryable: true,
    });
  } finally {
    window.clearTimeout(timer);
  }
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new SeekphonyApiError("Backend returned a malformed response.", {
      statusCode: response.status,
      retryable: response.status >= 500,
      code: "malformed_response",
    });
  }
}

function errorFromPayload(statusCode: number, payload: unknown): SeekphonyApiError {
  if (isApiError(payload)) {
    return new SeekphonyApiError(payload.message, {
      statusCode,
      retryable: payload.retryable ?? statusCode >= 500,
      code: payload.status,
    });
  }
  return new SeekphonyApiError(`Backend returned HTTP ${statusCode}.`, {
    statusCode,
    retryable: statusCode >= 500,
  });
}

function isApiError(value: unknown): value is ApiErrorDetail {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ApiErrorDetail>;
  return typeof candidate.status === "string" && typeof candidate.message === "string";
}
