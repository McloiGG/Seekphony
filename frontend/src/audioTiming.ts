export const CLIP_STEP_SECONDS = 0.5;
export const RECORDING_TARGET_TOLERANCE_SECONDS = 0.35;

interface ClipLimits {
  minClipSeconds: number;
  maxClipSeconds: number;
}

export function alignedClipEndSeconds(durationSeconds: number, limits: ClipLimits): number {
  return clampSeconds(
    snapDownToStep(durationSeconds, CLIP_STEP_SECONDS),
    limits.minClipSeconds,
    limits.maxClipSeconds,
  );
}

export function resolveRecordedDuration(
  measuredSeconds: number,
  targetSeconds: number | null,
): number {
  if (
    targetSeconds != null &&
    Number.isFinite(targetSeconds) &&
    Math.abs(measuredSeconds - targetSeconds) <= RECORDING_TARGET_TOLERANCE_SECONDS
  ) {
    return roundSeconds(targetSeconds);
  }
  return roundSeconds(measuredSeconds);
}

export function shouldUseTargetRecordingDuration(
  elapsedSeconds: number,
  targetSeconds: number,
): boolean {
  return elapsedSeconds >= targetSeconds - RECORDING_TARGET_TOLERANCE_SECONDS;
}

export function sampleCountForDuration(durationSeconds: number, sampleRate: number): number {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0 || sampleRate <= 0) {
    return 0;
  }
  return Math.round(durationSeconds * sampleRate);
}

function snapDownToStep(value: number, step: number): number {
  if (!Number.isFinite(value) || step <= 0) {
    return 0;
  }
  return roundSeconds(Math.floor((value + Number.EPSILON) / step) * step);
}

function clampSeconds(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
}

function roundSeconds(value: number): number {
  return Number(value.toFixed(3));
}
