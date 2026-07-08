from __future__ import annotations

import io
import math
import shutil
import statistics
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from seekphony_backend.core.errors import AppError

SUPPORTED_EXTENSIONS = {".wav", ".wave", ".mp3", ".m4a", ".webm", ".ogg", ".flac"}
TARGET_ANALYSIS_RATE = 8000


@dataclass(slots=True)
class AudioData:
    sample_rate: int
    samples: list[float]

    @property
    def duration_seconds(self) -> float:
        return len(self.samples) / self.sample_rate if self.sample_rate else 0


@dataclass(slots=True)
class FrameFeature:
    time_seconds: float
    rms: float
    zcr: float
    f0_hz: float | None
    pitch_confidence: float
    voiced: bool


@dataclass(slots=True)
class ClipFeatures:
    sample_rate: int
    duration_seconds: float
    global_rms: float
    clipping_ratio: float
    frames: list[FrameFeature]

    @property
    def voiced_frames(self) -> list[FrameFeature]:
        return [frame for frame in self.frames if frame.voiced and frame.f0_hz]

    @property
    def voiced_ratio(self) -> float:
        if not self.frames:
            return 0.0
        return len(self.voiced_frames) / len(self.frames)


class AudioEvaluator:
    def __init__(self, decode_timeout_seconds: float) -> None:
        self.decode_timeout_seconds = decode_timeout_seconds

    def evaluate(
        self,
        reference_bytes: bytes,
        reference_filename: str,
        performance_bytes: bytes,
        performance_filename: str,
        clip_start_seconds: float,
        clip_duration_seconds: float,
        performance_start_seconds: float,
    ) -> dict[str, object]:
        reference_audio = self.decode(reference_bytes, reference_filename)
        performance_audio = self.decode(performance_bytes, performance_filename)
        reference_clip = _reference_window(
            reference_audio,
            clip_start_seconds,
            clip_duration_seconds,
        )
        performance_clip = _performance_window(
            performance_audio,
            performance_start_seconds,
            clip_duration_seconds,
        )
        reference_features = _extract_features(reference_clip)
        performance_features = _extract_features(performance_clip)
        return _score_features(reference_features, performance_features)

    def decode(self, content: bytes, filename: str) -> AudioData:
        extension = Path(filename or "").suffix.lower()
        if extension and extension not in SUPPORTED_EXTENSIONS:
            raise AppError(
                415,
                "unsupported_audio",
                "Unsupported audio file type.",
                {"filename": filename, "supported_extensions": sorted(SUPPORTED_EXTENSIONS)},
            )

        try:
            return _decode_wav(content)
        except AppError:
            if extension in {"", ".wav", ".wave"}:
                raise

        if not shutil.which("ffmpeg"):
            raise AppError(
                415,
                "unsupported_audio",
                "This audio format needs ffmpeg, but ffmpeg is not available in this runtime.",
                {"filename": filename},
            )
        return _decode_with_ffmpeg(content, self.decode_timeout_seconds, filename)


def _decode_wav(content: bytes) -> AudioData:
    try:
        with wave.open(io.BytesIO(content), "rb") as reader:
            channels = reader.getnchannels()
            sample_rate = reader.getframerate()
            sample_width = reader.getsampwidth()
            frame_count = reader.getnframes()
            raw = reader.readframes(frame_count)
    except (EOFError, wave.Error) as exc:
        raise AppError(422, "audio_decode_failed", "Audio could not be decoded as WAV.") from exc

    if channels < 1 or sample_rate <= 0 or sample_width not in {1, 2, 3, 4}:
        raise AppError(
            422,
            "audio_decode_failed",
            "WAV file has unsupported channel, sample-rate, or bit-depth metadata.",
        )
    samples = _pcm_to_float(raw, sample_width, channels)
    if not samples:
        raise AppError(422, "audio_decode_failed", "Audio file does not contain samples.")
    return AudioData(sample_rate=sample_rate, samples=samples)


def _decode_with_ffmpeg(content: bytes, timeout_seconds: float, filename: str) -> AudioData:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "wav",
        "-ac",
        "1",
        "-ar",
        "16000",
        "pipe:1",
    ]
    try:
        completed = subprocess.run(
            command,
            input=content,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError(
            422,
            "audio_decode_failed",
            "Audio decoding timed out.",
            {"filename": filename},
        ) from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AppError(
            422,
            "audio_decode_failed",
            "Audio could not be decoded by ffmpeg.",
            {"filename": filename, "ffmpeg_error": stderr[:500]},
        )
    return _decode_wav(completed.stdout)


def _pcm_to_float(raw: bytes, sample_width: int, channels: int) -> list[float]:
    if sample_width == 1:
        channel_values = [(value - 128) / 128 for value in raw]
    elif sample_width in {2, 4}:
        max_value = float(2 ** (8 * sample_width - 1))
        channel_values = [
            int.from_bytes(raw[index : index + sample_width], "little", signed=True) / max_value
            for index in range(0, len(raw), sample_width)
        ]
    else:
        channel_values = [
            int.from_bytes(raw[index : index + sample_width], "little", signed=True) / float(2**23)
            for index in range(0, len(raw), sample_width)
        ]

    samples: list[float] = []
    for index in range(0, len(channel_values), channels):
        frame = channel_values[index : index + channels]
        if frame:
            samples.append(sum(frame) / len(frame))
    return samples


def _reference_window(audio: AudioData, start_seconds: float, duration_seconds: float) -> AudioData:
    if start_seconds < 0:
        raise AppError(422, "validation_error", "Clip start must be zero or greater.")
    if start_seconds + duration_seconds > audio.duration_seconds + 0.05:
        raise AppError(
            422,
            "validation_error",
            "Reference clip exceeds the uploaded audio duration.",
            {
                "audio_duration_seconds": round(audio.duration_seconds, 3),
                "clip_start_seconds": start_seconds,
                "clip_duration_seconds": duration_seconds,
            },
        )
    return _slice_audio(audio, start_seconds, duration_seconds, pad=False)


def _performance_window(
    audio: AudioData,
    start_seconds: float,
    duration_seconds: float,
) -> AudioData:
    if start_seconds < 0 or start_seconds >= audio.duration_seconds:
        raise AppError(
            422,
            "validation_error",
            "Performance start must be inside the uploaded performance audio.",
            {"audio_duration_seconds": round(audio.duration_seconds, 3)},
        )
    return _slice_audio(audio, start_seconds, duration_seconds, pad=True)


def _slice_audio(
    audio: AudioData,
    start_seconds: float,
    duration_seconds: float,
    *,
    pad: bool,
) -> AudioData:
    start = int(start_seconds * audio.sample_rate)
    end = start + int(duration_seconds * audio.sample_rate)
    samples = audio.samples[start:end]
    if pad and len(samples) < end - start:
        samples = [*samples, *([0.0] * (end - start - len(samples)))]
    return AudioData(sample_rate=audio.sample_rate, samples=samples)


def _extract_features(audio: AudioData) -> ClipFeatures:
    analysis_audio = _downsample(audio)
    samples = analysis_audio.samples
    sample_rate = analysis_audio.sample_rate
    frame_size = max(160, int(sample_rate * 0.04))
    hop_size = max(80, int(sample_rate * 0.02))
    global_rms = _rms(samples)
    silence_threshold = max(0.006, global_rms * 0.2)
    frames: list[FrameFeature] = []
    for start in range(0, max(1, len(samples) - frame_size + 1), hop_size):
        frame = samples[start : start + frame_size]
        if len(frame) < frame_size:
            break
        rms = _rms(frame)
        zcr = _zero_crossing_rate(frame)
        f0_hz: float | None = None
        confidence = 0.0
        voiced = False
        if rms >= silence_threshold:
            f0_hz, confidence = _estimate_pitch(frame, sample_rate)
            voiced = f0_hz is not None and confidence >= 0.32
        frames.append(
            FrameFeature(
                time_seconds=start / sample_rate,
                rms=rms,
                zcr=zcr,
                f0_hz=f0_hz,
                pitch_confidence=confidence,
                voiced=voiced,
            )
        )
    return ClipFeatures(
        sample_rate=sample_rate,
        duration_seconds=analysis_audio.duration_seconds,
        global_rms=global_rms,
        clipping_ratio=_clipping_ratio(samples),
        frames=frames,
    )


def _downsample(audio: AudioData) -> AudioData:
    if audio.sample_rate <= TARGET_ANALYSIS_RATE:
        return audio
    step = max(1, round(audio.sample_rate / TARGET_ANALYSIS_RATE))
    samples = audio.samples[::step]
    return AudioData(sample_rate=round(audio.sample_rate / step), samples=samples)


def _estimate_pitch(frame: list[float], sample_rate: int) -> tuple[float | None, float]:
    centered = _remove_dc(frame)
    energy = sum(sample * sample for sample in centered)
    if energy <= 1e-9:
        return None, 0.0
    min_lag = max(1, int(sample_rate / 800))
    max_lag = min(len(centered) - 2, int(sample_rate / 80))
    best_lag = 0
    best_score = 0.0
    for lag in range(min_lag, max_lag + 1):
        numerator = 0.0
        left_energy = 0.0
        right_energy = 0.0
        limit = len(centered) - lag
        for index in range(limit):
            left = centered[index]
            right = centered[index + lag]
            numerator += left * right
            left_energy += left * left
            right_energy += right * right
        denominator = math.sqrt(left_energy * right_energy)
        score = numerator / denominator if denominator else 0.0
        if score > best_score:
            best_score = score
            best_lag = lag
    if not best_lag or best_score < 0.2:
        return None, max(0.0, best_score)
    return sample_rate / best_lag, min(1.0, best_score)


def _score_features(reference: ClipFeatures, performance: ClipFeatures) -> dict[str, object]:
    warnings: list[str] = []
    if reference.voiced_ratio < 0.12:
        warnings.append("Reference clip has low detectable vocal/melodic content.")
    if performance.voiced_ratio < 0.12:
        warnings.append(
            "Performance has low detectable voice coverage; "
            "noise or backing audio may affect score."
        )
    if performance.global_rms < 0.006:
        warnings.append("Performance audio is very quiet.")
    if performance.clipping_ratio > 0.01:
        warnings.append("Performance audio appears clipped or overloaded.")

    offset_frames, rhythm_similarity = _best_timing_offset(reference.frames, performance.frames)
    hop_seconds = _hop_seconds(reference.frames)
    timing_offset_ms = offset_frames * hop_seconds * 1000
    pairs, missing_count = _aligned_pitch_pairs(reference.frames, performance.frames, offset_frames)
    reference_voiced_count = max(1, len(reference.voiced_frames))
    voiced_coverage = min(1.0, len(pairs) / reference_voiced_count)

    key_shift: int | None = None
    pitch_error_cents: float | None = None
    corrected_errors: list[tuple[float, float]] = []
    if pairs:
        semitone_diffs = [
            12 * math.log2(performance_pitch / reference_pitch)
            for _, reference_pitch, performance_pitch in pairs
            if reference_pitch > 0 and performance_pitch > 0
        ]
        if semitone_diffs:
            key_shift = round(statistics.median(semitone_diffs))
            corrected_errors = [
                (time_seconds, (diff - key_shift) * 100)
                for (time_seconds, _, _), diff in zip(pairs, semitone_diffs, strict=False)
            ]
            pitch_error_cents = statistics.fmean(abs(error) for _, error in corrected_errors)

    pitch_score = _score_pitch(pitch_error_cents, voiced_coverage)
    rhythm_score = _score_rhythm(rhythm_similarity, timing_offset_ms)
    stability_score = _score_stability(performance.voiced_frames)
    coverage_score = 100 * voiced_coverage
    audio_quality_score = _score_audio_quality(performance)
    overall = _clamp(
        pitch_score * 0.35
        + rhythm_score * 0.2
        + stability_score * 0.15
        + coverage_score * 0.2
        + audio_quality_score * 0.1
    )
    confidence = _clamp01((voiced_coverage * 0.55) + (audio_quality_score / 100 * 0.45))

    segments = _problem_segments(
        corrected_errors=corrected_errors,
        reference_frames=reference.frames,
        performance_frames=performance.frames,
        offset_frames=offset_frames,
        missing_count=missing_count,
        timing_offset_ms=timing_offset_ms,
    )
    return {
        "scores": {
            "overall": round(overall, 1),
            "pitch": round(pitch_score, 1),
            "rhythm": round(rhythm_score, 1),
            "stability": round(stability_score, 1),
            "coverage": round(coverage_score, 1),
            "audio_quality": round(audio_quality_score, 1),
        },
        "metrics": {
            "key_shift_semitones": key_shift,
            "pitch_error_cents": (
                round(pitch_error_cents, 1) if pitch_error_cents is not None else None
            ),
            "timing_offset_ms": round(timing_offset_ms, 1),
            "voiced_coverage": round(voiced_coverage, 3),
            "reference_voiced_ratio": round(reference.voiced_ratio, 3),
            "performance_voiced_ratio": round(performance.voiced_ratio, 3),
            "confidence": round(confidence, 3),
            "reference_duration_seconds": round(reference.duration_seconds, 3),
            "performance_duration_seconds": round(performance.duration_seconds, 3),
        },
        "segments": segments,
        "warnings": warnings,
    }


def _best_timing_offset(
    reference_frames: list[FrameFeature],
    performance_frames: list[FrameFeature],
) -> tuple[int, float]:
    if not reference_frames or not performance_frames:
        return 0, 0.0
    max_offset = min(50, max(len(reference_frames), len(performance_frames)) // 3)
    best_offset = 0
    best_score = -1.0
    for offset in range(-max_offset, max_offset + 1):
        ref_values: list[float] = []
        perf_values: list[float] = []
        for ref_index, ref_frame in enumerate(reference_frames):
            perf_index = ref_index + offset
            if 0 <= perf_index < len(performance_frames):
                ref_values.append(ref_frame.rms)
                perf_values.append(performance_frames[perf_index].rms)
        if len(ref_values) < 5:
            continue
        score = _correlation(ref_values, perf_values)
        if score > best_score:
            best_score = score
            best_offset = offset
    return best_offset, max(0.0, best_score)


def _aligned_pitch_pairs(
    reference_frames: list[FrameFeature],
    performance_frames: list[FrameFeature],
    offset_frames: int,
) -> tuple[list[tuple[float, float, float]], int]:
    pairs: list[tuple[float, float, float]] = []
    missing_count = 0
    for ref_index, ref_frame in enumerate(reference_frames):
        if not ref_frame.voiced or not ref_frame.f0_hz:
            continue
        perf_index = ref_index + offset_frames
        if not 0 <= perf_index < len(performance_frames):
            missing_count += 1
            continue
        perf_frame = performance_frames[perf_index]
        if not perf_frame.voiced or not perf_frame.f0_hz:
            missing_count += 1
            continue
        pairs.append((ref_frame.time_seconds, ref_frame.f0_hz, perf_frame.f0_hz))
    return pairs, missing_count


def _problem_segments(
    *,
    corrected_errors: list[tuple[float, float]],
    reference_frames: list[FrameFeature],
    performance_frames: list[FrameFeature],
    offset_frames: int,
    missing_count: int,
    timing_offset_ms: float,
) -> list[dict[str, object]]:
    points: list[tuple[float, str, str, str]] = []
    for time_seconds, error_cents in corrected_errors:
        if abs(error_cents) >= 180:
            points.append(
                (
                    time_seconds,
                    "pitch",
                    "high",
                    "Pitch was off by about "
                    f"{abs(error_cents):.0f} cents after key-shift correction.",
                )
            )
        elif abs(error_cents) >= 100:
            points.append(
                (
                    time_seconds,
                    "pitch",
                    "medium",
                    f"Pitch drifted by about {abs(error_cents):.0f} cents.",
                )
            )

    if missing_count:
        for ref_index, ref_frame in enumerate(reference_frames):
            perf_index = ref_index + offset_frames
            if not ref_frame.voiced:
                continue
            if 0 <= perf_index < len(performance_frames) and performance_frames[perf_index].voiced:
                continue
            points.append(
                (
                    ref_frame.time_seconds,
                    "missing_voice",
                    "high" if missing_count > 10 else "medium",
                    "Reference had detectable melody here, but the performance did not.",
                )
            )

    segments = _group_problem_points(points)
    if abs(timing_offset_ms) >= 350:
        segments.insert(
            0,
            {
                "start_seconds": 0.0,
                "end_seconds": min(2.0, _last_frame_time(reference_frames)),
                "issue": "timing",
                "severity": "medium" if abs(timing_offset_ms) < 700 else "high",
                "detail": f"Performance timing was offset by about {abs(timing_offset_ms):.0f} ms.",
            },
        )
    return segments[:5]


def _group_problem_points(points: list[tuple[float, str, str, str]]) -> list[dict[str, object]]:
    if not points:
        return []
    ordered = sorted(points, key=lambda point: point[0])
    segments: list[dict[str, object]] = []
    start, issue, severity, detail = ordered[0]
    end = start + 0.2
    for time_seconds, current_issue, current_severity, current_detail in ordered[1:]:
        if current_issue == issue and time_seconds <= end + 0.25:
            end = time_seconds + 0.2
            if current_severity == "high":
                severity = "high"
            continue
        segments.append(
            {
                "start_seconds": round(start, 2),
                "end_seconds": round(end, 2),
                "issue": issue,
                "severity": severity,
                "detail": detail,
            }
        )
        start, issue, severity, detail = (
            time_seconds,
            current_issue,
            current_severity,
            current_detail,
        )
        end = time_seconds + 0.2
    segments.append(
        {
            "start_seconds": round(start, 2),
            "end_seconds": round(end, 2),
            "issue": issue,
            "severity": severity,
            "detail": detail,
        }
    )
    return segments


def _score_pitch(pitch_error_cents: float | None, voiced_coverage: float) -> float:
    if pitch_error_cents is None:
        return 0.0
    return _clamp((100 - pitch_error_cents * 0.65) * (0.35 + voiced_coverage * 0.65))


def _score_rhythm(rhythm_similarity: float, timing_offset_ms: float) -> float:
    offset_penalty = min(35.0, abs(timing_offset_ms) / 20)
    return _clamp((rhythm_similarity * 100) - offset_penalty)


def _score_stability(frames: list[FrameFeature]) -> float:
    pitches = [frame.f0_hz for frame in frames if frame.f0_hz]
    if len(pitches) < 3:
        return 0.0
    cents = [
        1200 * math.log2(pitches[index] / pitches[index - 1]) for index in range(1, len(pitches))
    ]
    jitter = statistics.median(abs(value) for value in cents)
    return _clamp(100 - max(0.0, jitter - 35) * 0.8)


def _score_audio_quality(features: ClipFeatures) -> float:
    score = 100.0
    if features.global_rms < 0.006:
        score -= 35
    elif features.global_rms < 0.02:
        score -= 15
    if features.clipping_ratio > 0.03:
        score -= 35
    elif features.clipping_ratio > 0.01:
        score -= 20
    if features.voiced_ratio < 0.12:
        score -= 30
    elif features.voiced_ratio < 0.25:
        score -= 15
    zcr_values = [frame.zcr for frame in features.frames if frame.rms > 0.01]
    if zcr_values and statistics.median(zcr_values) > 0.35:
        score -= 15
    return _clamp(score)


def _rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def _zero_crossing_rate(samples: list[float]) -> float:
    if len(samples) < 2:
        return 0.0
    crossings = 0
    previous = samples[0]
    for sample in samples[1:]:
        if (previous <= 0 < sample) or (previous >= 0 > sample):
            crossings += 1
        previous = sample
    return crossings / (len(samples) - 1)


def _clipping_ratio(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return sum(1 for sample in samples if abs(sample) >= 0.98) / len(samples)


def _remove_dc(samples: list[float]) -> list[float]:
    mean = statistics.fmean(samples) if samples else 0.0
    return [sample - mean for sample in samples]


def _correlation(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = 0.0
    left_energy = 0.0
    right_energy = 0.0
    for left_value, right_value in zip(left, right, strict=False):
        left_delta = left_value - left_mean
        right_delta = right_value - right_mean
        numerator += left_delta * right_delta
        left_energy += left_delta * left_delta
        right_energy += right_delta * right_delta
    denominator = math.sqrt(left_energy * right_energy)
    return numerator / denominator if denominator else 0.0


def _hop_seconds(frames: list[FrameFeature]) -> float:
    if len(frames) >= 2:
        return frames[1].time_seconds - frames[0].time_seconds
    return 0.02


def _last_frame_time(frames: list[FrameFeature]) -> float:
    if not frames:
        return 0.0
    return frames[-1].time_seconds


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, value))


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))
