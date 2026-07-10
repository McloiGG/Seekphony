import { beforeEach, describe, expect, it, vi } from "vitest";

import { createEvaluation, fetchHealth, importReferenceAudio } from "./api";

describe("api client timeouts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    window.__SEEKPHONY_CONFIG__ = { apiBaseUrl: "http://localhost:8000" };
  });

  it("keeps health checks on the default request timeout", async () => {
    const timeoutSpy = vi.spyOn(window, "setTimeout");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ status: "ok" }));

    await fetchHealth();

    expect(timeoutSpy).toHaveBeenCalledWith(expect.any(Function), 60000);
  });

  it("uses a longer timeout for evaluation creation", async () => {
    const timeoutSpy = vi.spyOn(window, "setTimeout");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ status: "completed" }));

    await createEvaluation({
      reference: new Blob(["RIFF"], { type: "audio/wav" }),
      referenceFilename: "reference.wav",
      performance: new Blob(["RIFF"], { type: "audio/wav" }),
      performanceFilename: "performance.wav",
      clipStartSeconds: 0,
      clipDurationSeconds: 20,
      performanceStartSeconds: 0,
    });

    expect(timeoutSpy).toHaveBeenCalledWith(expect.any(Function), 240000);
  });

  it("uses a longer timeout for reference URL import", async () => {
    const timeoutSpy = vi.spyOn(window, "setTimeout");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("audio", {
        status: 200,
        headers: {
          "Content-Type": "audio/ogg",
          "X-Seekphony-Filename": "reference.ogg",
          "X-Seekphony-Source-Type": "direct_url",
          "X-Seekphony-Title": "Reference",
        },
      }),
    );

    await importReferenceAudio("https://example.com/reference.ogg");

    expect(timeoutSpy).toHaveBeenCalledWith(expect.any(Function), 240000);
  });

  it("regenerates a corrupt browser history id before creating an evaluation", async () => {
    window.localStorage.setItem("seekphony_device_id", "not-a-valid-device-id");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ status: "completed" }),
    );

    await createEvaluation(evaluationPayload());

    const headers = new Headers(fetchSpy.mock.calls[0]?.[1]?.headers);
    const deviceId = headers.get("X-Seekphony-Device-ID");
    expect(deviceId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    expect(deviceId).toBe(window.localStorage.getItem("seekphony_device_id"));
  });

  it("does not expose the internal device header name to users", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          status: "validation_error",
          message: "X-Seekphony-Device-ID is required for evaluation history.",
          retryable: false,
          fallback_used: false,
        },
        422,
      ),
    );

    await expect(createEvaluation(evaluationPayload())).rejects.toMatchObject({
      message: "Browser session could not be identified. Refresh the page and retry.",
      code: "validation_error",
      statusCode: 422,
    });
  });
});

function evaluationPayload() {
  return {
    reference: new Blob(["RIFF"], { type: "audio/wav" }),
    referenceFilename: "reference.wav",
    performance: new Blob(["RIFF"], { type: "audio/wav" }),
    performanceFilename: "performance.wav",
    clipStartSeconds: 0,
    clipDurationSeconds: 20,
    performanceStartSeconds: 0,
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
