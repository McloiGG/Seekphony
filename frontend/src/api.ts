import { apiBaseUrl } from "./config";
import type {
  ApiErrorDetail,
  EvaluationListResponse,
  EvaluationResponse,
  HealthResponse,
} from "./types";

const REQUEST_TIMEOUT_MS = 60000;
const EVALUATION_TIMEOUT_MS = 240000;
const REFERENCE_IMPORT_TIMEOUT_MS = 240000;
const DEVICE_ID_STORAGE_KEY = "seekphony_device_id";
const DEVICE_ID_HEADER = "X-Seekphony-Device-ID";
const DEVICE_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

let memoryDeviceId: string | null = null;

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
  return requestJson<EvaluationListResponse>(
    `/api/v1/evaluations?limit=${limit}`,
    withDeviceHeader(),
  );
}

export async function createEvaluation(payload: EvaluationPayload): Promise<EvaluationResponse> {
  const body = new FormData();
  body.append("reference", payload.reference, payload.referenceFilename);
  body.append("performance", payload.performance, payload.performanceFilename);
  body.append("clip_start_seconds", String(payload.clipStartSeconds));
  body.append("clip_duration_seconds", String(payload.clipDurationSeconds));
  body.append("performance_start_seconds", String(payload.performanceStartSeconds));
  return requestJson<EvaluationResponse>(
    "/api/v1/evaluations",
    {
      method: "POST",
      headers: deviceHeaders(),
      body,
    },
    EVALUATION_TIMEOUT_MS,
  );
}

export async function importReferenceAudio(url: string): Promise<ImportedReferenceAudio> {
  const response = await requestBlob(
    "/api/v1/reference-audio/import",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    },
    REFERENCE_IMPORT_TIMEOUT_MS,
  );
  return {
    blob: response.blob,
    filename: decodeHeader(response.headers.get("X-Seekphony-Filename")) || "reference-audio",
    sourceType: response.headers.get("X-Seekphony-Source-Type") || "direct_url",
    title: decodeHeader(response.headers.get("X-Seekphony-Title")) || "Imported reference",
    byteSize: Number(response.headers.get("X-Seekphony-Byte-Size") || response.blob.size),
  };
}

export async function deleteEvaluationRecord(evaluationId: number): Promise<void> {
  await requestJson(`/api/v1/evaluations/${evaluationId}`, withDeviceHeader({ method: "DELETE" }));
}

export async function clearEvaluationRecords(): Promise<void> {
  await requestJson("/api/v1/evaluations", withDeviceHeader({ method: "DELETE" }));
}

async function requestJson<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
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
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<{ blob: Blob; headers: Headers }> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
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
    return new SeekphonyApiError(userFacingErrorMessage(payload.message), {
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

function withDeviceHeader(init: RequestInit = {}): RequestInit {
  return {
    ...init,
    headers: deviceHeaders(init.headers),
  };
}

function deviceHeaders(headers?: HeadersInit): Headers {
  const next = new Headers(headers);
  next.set(DEVICE_ID_HEADER, anonymousDeviceId());
  return next;
}

function anonymousDeviceId(): string {
  try {
    const stored = normalizeDeviceId(window.localStorage.getItem(DEVICE_ID_STORAGE_KEY));
    if (stored) {
      return stored;
    }
    const generated = randomUuid();
    window.localStorage.setItem(DEVICE_ID_STORAGE_KEY, generated);
    return generated;
  } catch {
    memoryDeviceId = normalizeDeviceId(memoryDeviceId) ?? randomUuid();
    return memoryDeviceId;
  }
}

function normalizeDeviceId(value: string | null): string | null {
  const trimmed = value?.trim() ?? "";
  if (!DEVICE_ID_PATTERN.test(trimmed)) {
    return null;
  }
  return trimmed.toLowerCase();
}

function userFacingErrorMessage(message: string): string {
  if (message.includes(DEVICE_ID_HEADER)) {
    return "Browser session could not be identified. Refresh the page and retry.";
  }
  return message;
}

function randomUuid(): string {
  if (typeof window.crypto?.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  if (typeof window.crypto?.getRandomValues === "function") {
    window.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join(""),
  ].join("-");
}
