import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { EvaluationResponse, HealthResponse } from "./types";

const healthPayload: HealthResponse = {
  status: "ok",
  service: "Seekphony Backend",
  api_prefix: "/api/v1",
  database: { kind: "sqlite", postgres_configured: false },
  providers: { gemini_configured: false },
  limits: {
    max_upload_bytes: 15 * 1024 * 1024,
    min_clip_seconds: 5,
    max_clip_seconds: 60,
  },
};

const evaluationPayload: EvaluationResponse = {
  status: "completed",
  evaluation_id: 1,
  created_at: "2026-07-08T00:00:00Z",
  reference_filename: "reference.wav",
  performance_filename: "performance.wav",
  clip_start_seconds: 0,
  clip_duration_seconds: 5,
  performance_start_seconds: 0,
  scores: {
    overall: 88,
    pitch: 91,
    rhythm: 84,
    stability: 90,
    coverage: 86,
    audio_quality: 87,
  },
  metrics: {
    key_shift_semitones: 0,
    pitch_error_cents: 22,
    timing_offset_ms: 40,
    voiced_coverage: 0.86,
    reference_voiced_ratio: 0.9,
    performance_voiced_ratio: 0.88,
    confidence: 0.87,
    reference_duration_seconds: 5,
    performance_duration_seconds: 5,
  },
  segments: [],
  warnings: [],
  explanation: {
    status: "unavailable",
    provider: "gemini",
    error: "Gemini API key is not configured.",
    content: null,
  },
};

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.__SEEKPHONY_CONFIG__ = { apiBaseUrl: "http://localhost:8000" };
  });

  it("renders the singing evaluator shell", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      return jsonResponse({ status: "ok", evaluations: [evaluationPayload] });
    });

    render(<App />);

    expect(screen.getByRole("heading", { name: "Seekphony" })).toBeInTheDocument();
    expect(await screen.findByText("Upload, clip, sing, evaluate")).toBeInTheDocument();
    expect(screen.getByText("Recent saved evaluations")).toBeInTheDocument();
    expect(screen.getByText("88%")).toBeInTheDocument();
  });

  it("keeps the UI available when the backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));

    render(<App />);

    expect(screen.getByRole("heading", { name: "Seekphony" })).toBeInTheDocument();
    expect(await screen.findByText("Backend is unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Backend response unavailable")).toBeInTheDocument();
  });

  it("submits uploaded reference and performance audio", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      if (url.includes("/api/v1/evaluations?")) {
        return jsonResponse({ status: "ok", evaluations: [] });
      }
      if (url.endsWith("/api/v1/evaluations") && init?.method === "POST") {
        return jsonResponse(evaluationPayload);
      }
      return jsonResponse({ status: "ok", evaluations: [] });
    });

    render(<App />);

    await screen.findByText("Upload, clip, sing, evaluate");
    const referenceInput = screen.getByLabelText(/Reference song audio/i);
    const performanceInput = screen.getByLabelText(/Performance audio/i);
    await userEvent.upload(referenceInput, new File(["wav"], "reference.wav", { type: "audio/wav" }));
    await userEvent.upload(performanceInput, new File(["wav"], "performance.wav", { type: "audio/wav" }));
    await userEvent.click(screen.getByRole("button", { name: /Evaluate Singing/i }));

    await waitFor(() => expect(screen.getByText("Evaluation complete")).toBeInTheDocument());
    expect(screen.getByText("AI explanation unavailable")).toBeInTheDocument();
    expect(screen.getByText("Gemini API key is not configured.")).toBeInTheDocument();
  });
});

function jsonResponse(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}
