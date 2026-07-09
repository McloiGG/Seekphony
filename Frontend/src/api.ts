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
  reference: Blob;
  referenceFilename: string;
  performance: Blob;
  performanceFilename: string;
  clipStartSeconds: number;
  clipDurationSeconds: number;
  performanceStartSeconds: number;
}

export interface ImportedReferenceAudio {
  blob: Blob;
  filename: string;
  sourceType: string;
  title: string;
  byteSize: number;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/v1/health");
}

export async function fetchEvaluations(limit = 5): Promise<EvaluationListResponse> {
  return requestJson<EvaluationListResponse>(`/api/v1/evaluations?limit=${limit}`);
}

export async function createEvaluation(payload: EvaluationPayload): Promise<EvaluationResponse> {
  const body = new FormData();
  body.append("reference", payload.reference, payload.referenceFilename);
  body.append("performance", payload.performance, payload.performanceFilename);
  body.append("clip_start_seconds", String(payload.clipStartSeconds));
  body.append("clip_duration_seconds", String(payload.clipDurationSeconds));
  body.append("performance_start_seconds", String(payload.performanceStartSeconds));
  return requestJson<EvaluationResponse>("/api/v1/evaluations", {
    method: "POST",
    body,
  });
}

export async function importReferenceAudio(url: string): Promise<ImportedReferenceAudio> {
  const response = await requestBlob("/api/v1/reference-audio/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return {
    blob: response.blob,
    filename: decodeHeader(response.headers.get("X-Seekphony-Filename")) || "reference-audio",
    sourceType: response.headers.get("X-Seekphony-Source-Type") || "direct_url",
    title: decodeHeader(response.headers.get("X-Seekphony-Title")) || "Imported reference",
    byteSize: Number(response.headers.get("X-Seekphony-Byte-Size") || response.blob.size),
  };
}

export async function deleteEvaluationRecord(evaluationId: number): Promise<void> {
  await requestJson(`/api/v1/evaluations/${evaluationId}`, { method: "DELETE" });
}

export async function clearEvaluationRecords(): Promise<void> {
  await requestJson("/api/v1/evaluations", { method: "DELETE" });
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

async function requestBlob(
  path: string,
  init: RequestInit = {},
): Promise<{ blob: Blob; headers: Headers }> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      signal: controller.signal,
    });
    if (!response.ok) {
      const payload = await parseJson(response);
      throw errorFromPayload(response.status, payload);
    }
    return { blob: await response.blob(), headers: response.headers };
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

function decodeHeader(value: string | null): string {
  if (!value) {
    return "";
  }
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
