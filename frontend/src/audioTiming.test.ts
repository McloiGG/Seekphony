import { describe, expect, it } from "vitest";

import {
  alignedClipEndSeconds,
  resolveRecordedDuration,
  sampleCountForDuration,
  shouldUseTargetRecordingDuration,
} from "./audioTiming";

const limits = {
  minClipSeconds: 5,
  maxClipSeconds: 60,
};

describe("audio timing helpers", () => {
  it("aligns default trim ends to the nearest lower half-second", () => {
    expect(alignedClipEndSeconds(9.865, limits)).toBe(9.5);
    expect(alignedClipEndSeconds(10, limits)).toBe(10);
    expect(alignedClipEndSeconds(72.4, limits)).toBe(60);
  });

  it("uses the requested recording duration when metadata is only slightly short", () => {
    expect(resolveRecordedDuration(9.865, 10)).toBe(10);
    expect(resolveRecordedDuration(8.9, 10)).toBe(8.9);
  });

  it("detects manual stops that are close enough to the requested duration", () => {
    expect(shouldUseTargetRecordingDuration(9.8, 10)).toBe(true);
    expect(shouldUseTargetRecordingDuration(8.5, 10)).toBe(false);
  });

  it("converts target recording durations to exact sample counts", () => {
    expect(sampleCountForDuration(10, 48_000)).toBe(480_000);
    expect(sampleCountForDuration(0, 48_000)).toBe(0);
  });
});
