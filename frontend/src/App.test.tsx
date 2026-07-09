import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    max_upload_bytes: 30 * 1024 * 1024,
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
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("renders the redesigned evaluator shell", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      return jsonResponse({ status: "ok", evaluations: [evaluationPayload] });
    });

    render(<App />);

    expect(screen.getByRole("heading", { name: "Seekphony" })).toBeInTheDocument();
    expect(await screen.findByText("Choose audio, trim, evaluate")).toBeInTheDocument();
    expect(screen.getByText(/Evaluation clips must be between 5s and 60s/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Reference audio" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Performance audio" })).toBeInTheDocument();
    expect(screen.getByLabelText("Record duration")).toBeInTheDocument();
    expect(screen.queryByText("Checking")).not.toBeInTheDocument();
    expect(screen.queryByText("Connected")).not.toBeInTheDocument();
    expect(screen.queryByText("Refresh Backend")).not.toBeInTheDocument();
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

    await screen.findByText("Choose audio, trim, evaluate");
    await userEvent.upload(
      screen.getByLabelText(/Reference upload/i),
      new File(["wav"], "reference.wav", { type: "audio/wav" }),
    );
    await userEvent.click(screen.getAllByRole("tab", { name: "Upload" })[1]);
    await userEvent.upload(
      screen.getByLabelText(/Performance upload/i),
      new File(["wav"], "performance.wav", { type: "audio/wav" }),
    );
    await userEvent.click(screen.getByRole("button", { name: /Evaluate Singing/i }));

    await waitFor(() => expect(screen.getByText("Evaluation complete")).toBeInTheDocument());
    expect(screen.getByText("Reference playback ready")).toBeInTheDocument();
    expect(screen.getByText("Performance playback ready")).toBeInTheDocument();
    expect(screen.getByText("AI explanation unavailable")).toBeInTheDocument();
    expect(screen.getByText("Gemini API key is not configured.")).toBeInTheDocument();
  });

  it("accepts dropped reference audio", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      return jsonResponse({ status: "ok", evaluations: [] });
    });

    render(<App />);

    await screen.findByText("Choose audio, trim, evaluate");
    const dropZone = screen.getByText("Reference upload").closest("label");
    expect(dropZone).not.toBeNull();
    const file = new File(["wav"], "reference-drop.wav", { type: "audio/wav" });

    fireEvent.dragEnter(dropZone!, { dataTransfer: { files: [file] } });
    expect(dropZone).toHaveClass("dragging");
    fireEvent.drop(dropZone!, { dataTransfer: { files: [file] } });

    expect(screen.getByText("Reference playback ready")).toBeInTheDocument();
    expect(screen.getByText(/reference-drop.wav/)).toBeInTheDocument();
  });

  it("accepts dropped performance audio after switching to upload", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      return jsonResponse({ status: "ok", evaluations: [] });
    });

    render(<App />);

    await screen.findByText("Choose audio, trim, evaluate");
    await userEvent.click(screen.getAllByRole("tab", { name: "Upload" })[1]);
    const dropZone = screen.getByText("Performance upload").closest("label");
    expect(dropZone).not.toBeNull();
    const file = new File(["wav"], "performance-drop.wav", { type: "audio/wav" });

    fireEvent.drop(dropZone!, { dataTransfer: { files: [file] } });

    expect(screen.getByText("Performance playback ready")).toBeInTheDocument();
    expect(screen.getByText(/performance-drop.wav/)).toBeInTheDocument();
  });

  it("loads reference audio from the URL tab and enables playback", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      if (url.includes("/api/v1/evaluations?")) {
        return jsonResponse({ status: "ok", evaluations: [] });
      }
      if (url.endsWith("/api/v1/reference-audio/import")) {
        return blobResponse(new Blob(["RIFF"], { type: "audio/wav" }));
      }
      return jsonResponse({ status: "ok", evaluations: [] });
    });

    render(<App />);

    await userEvent.click(await screen.findByRole("tab", { name: "URL" }));
    expect(screen.getByText(/direct audio URL or YouTube link/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Reference URL"), "https://example.com/reference.wav");
    await userEvent.click(screen.getByRole("button", { name: /Load URL/i }));

    await waitFor(() => expect(screen.getByText("Reference loaded")).toBeInTheDocument());
    expect(screen.getByText("Reference playback ready")).toBeInTheDocument();
    expect(screen.getAllByText(/Imported Reference/).length).toBeGreaterThan(0);
  });

  it("allows record duration to be cleared while editing", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      return jsonResponse({ status: "ok", evaluations: [] });
    });

    render(<App />);

    await screen.findByText("Choose audio, trim, evaluate");
    await userEvent.click(screen.getByRole("tab", { name: "Record" }));
    const recordDuration = screen.getByLabelText("Record duration") as HTMLInputElement;

    await userEvent.clear(recordDuration);
    expect(recordDuration.value).toBe("");

    await userEvent.type(recordDuration, "12");
    expect(recordDuration.value).toBe("12");
  });

  it("opens saved evaluation details and deletes history", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      if (url.includes("/api/v1/evaluations?")) {
        return jsonResponse({ status: "ok", evaluations: [evaluationPayload] });
      }
      if (url.endsWith("/api/v1/evaluations/1") && init?.method === "DELETE") {
        return jsonResponse({ status: "ok", deleted_count: 1 });
      }
      if (url.endsWith("/api/v1/evaluations") && init?.method === "DELETE") {
        return jsonResponse({ status: "ok", deleted_count: 1 });
      }
      return jsonResponse(evaluationPayload);
    });

    render(<App />);

    const historyButton = await screen.findByRole("button", { name: /88%/i });
    await userEvent.click(historyButton);
    const dialog = screen.getByRole("dialog", { name: /88% overall/i });
    expect(within(dialog).getByText("reference.wav")).toBeInTheDocument();
    expect(within(dialog).getByText("performance.wav")).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("Evaluation deleted")).toBeInTheDocument();
  });

  it("clears all saved evaluations", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.endsWith("/api/v1/health")) {
        return jsonResponse(healthPayload);
      }
      if (url.endsWith("/api/v1/evaluations") && init?.method === "DELETE") {
        return jsonResponse({ status: "ok", deleted_count: 1 });
      }
      return jsonResponse({ status: "ok", evaluations: [evaluationPayload] });
    });

    render(<App />);

    await screen.findByText("88%");
    await userEvent.click(screen.getByRole("button", { name: /Clear all/i }));

    await waitFor(() => expect(screen.getByText("History cleared")).toBeInTheDocument());
    expect(screen.getByText("No evaluation records loaded yet.")).toBeInTheDocument();
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

function blobResponse(blob: Blob): Promise<Response> {
  return Promise.resolve(
    new Response(new Uint8Array([82, 73, 70, 70]), {
      status: 200,
      headers: {
        "Content-Type": "audio/wav",
        "X-Seekphony-Filename": "imported-reference.wav",
        "X-Seekphony-Source-Type": "direct_url",
        "X-Seekphony-Title": "Imported Reference",
        "X-Seekphony-Byte-Size": String(blob.size),
      },
    }),
  );
}
