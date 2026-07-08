import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
  value: vi.fn(() => ({
    arc: vi.fn(),
    beginPath: vi.fn(),
    clearRect: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    lineTo: vi.fn(),
    moveTo: vi.fn(),
    setTransform: vi.fn(),
    stroke: vi.fn(),
  })),
});

window.requestAnimationFrame = vi.fn((callback: FrameRequestCallback) =>
  window.setTimeout(() => callback(0), 16),
) as unknown as typeof window.requestAnimationFrame;

window.cancelAnimationFrame = vi.fn((handle: number) => window.clearTimeout(handle));
