import { beforeEach, describe, expect, it, vi } from "vitest";

import { createEvaluation, fetchHealth } from "./api";

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
});

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
