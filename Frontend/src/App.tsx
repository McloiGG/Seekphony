import {
  AlertTriangle,
  Clock3,
  Database,
  FileAudio,
  Gauge,
  Loader2,
  Mic,
  Music2,
  RefreshCw,
  RotateCcw,
  Scissors,
  ShieldCheck,
  Signal,
  Sparkles,
  Upload,
  Waves,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import {
  createEvaluation,
  fetchEvaluations,
  fetchHealth,
  SeekphonyApiError,
} from "./api";
import type { EvaluationResponse, HealthResponse, Metrics, ProblemSegment, Scores } from "./types";

const DEFAULT_MAX_AUDIO_BYTES = 15 * 1024 * 1024;
const DEFAULT_MIN_CLIP_SECONDS = 5;
const DEFAULT_MAX_CLIP_SECONDS = 60;
const DEFAULT_RECORD_SECONDS = 20;

type BusyState = "idle" | "loading" | "recording";
type NoticeKind = "info" | "success" | "warning" | "danger";

interface Notice {
  kind: NoticeKind;
  title: string;
  detail: string;
}

interface RecordedAudio {
  blob: Blob;
  filename: string;
}

interface WavRecorder {
  stop: () => Promise<Blob>;
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null);
  const [history, setHistory] = useState<EvaluationResponse[]>([]);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [performanceFile, setPerformanceFile] = useState<File | null>(null);
  const [recordedAudio, setRecordedAudio] = useState<RecordedAudio | null>(null);
  const [referenceDuration, setReferenceDuration] = useState<number | null>(null);
  const [clipStart, setClipStart] = useState(0);
  const [clipDuration, setClipDuration] = useState(15);
  const [performanceStart, setPerformanceStart] = useState(0);
  const [busy, setBusy] = useState<BusyState>("idle");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [result, setResult] = useState<EvaluationResponse | null>(null);
  const [recordingSeconds, setRecordingSeconds] = useState(DEFAULT_RECORD_SECONDS);
  const recorderRef = useRef<WavRecorder | null>(null);
  const timerRef = useRef<number | null>(null);

  const limits = {
    maxUploadBytes: health?.limits.max_upload_bytes ?? DEFAULT_MAX_AUDIO_BYTES,
    minClipSeconds: health?.limits.min_clip_seconds ?? DEFAULT_MIN_CLIP_SECONDS,
    maxClipSeconds: health?.limits.max_clip_seconds ?? DEFAULT_MAX_CLIP_SECONDS,
  };

  const loadRuntime = useCallback(async () => {
    try {
      const [healthResponse, evaluationsResponse] = await Promise.all([
        fetchHealth(),
        fetchEvaluations(5),
      ]);
      setHealth(healthResponse);
      setHistory(evaluationsResponse.evaluations);
      setServiceOnline(true);
    } catch (error) {
      setServiceOnline(false);
      setNotice(toNotice(error, "Backend is unavailable."));
    }
  }, []);

  useEffect(() => {
    void loadRuntime();
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
      void stopRecorder();
    };
  }, [loadRuntime]);

  useEffect(() => {
    if (!referenceFile || typeof URL.createObjectURL !== "function") {
      setReferenceDuration(null);
      return undefined;
    }
    const objectUrl = URL.createObjectURL(referenceFile);
    const audio = new Audio(objectUrl);
    audio.onloadedmetadata = () => {
      if (Number.isFinite(audio.duration)) {
        setReferenceDuration(audio.duration);
      }
    };
    audio.onerror = () => setReferenceDuration(null);
    return () => URL.revokeObjectURL(objectUrl);
  }, [referenceFile]);

  const maxClipStart = Math.max(0, (referenceDuration ?? clipDuration) - clipDuration);
  const performanceLabel = performanceFile?.name ?? recordedAudio?.filename ?? "Upload or record singing";
  const serviceLabel = serviceOnline === null ? "Checking" : serviceOnline ? "Connected" : "Offline";
  const serviceTone = serviceOnline === null ? "neutral" : serviceOnline ? "good" : "bad";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!referenceFile) {
      setNotice({
        kind: "warning",
        title: "Reference audio needed",
        detail: "Upload the song or backing clip you want to compare against.",
      });
      return;
    }
    const performance = performanceFile ?? recordedAudio?.blob;
    const performanceFilename = performanceFile?.name ?? recordedAudio?.filename;
    if (!performance || !performanceFilename) {
      setNotice({
        kind: "warning",
        title: "Performance audio needed",
        detail: "Upload your singing or record a take before evaluating.",
      });
      return;
    }
    if (referenceFile.size > limits.maxUploadBytes || performance.size > limits.maxUploadBytes) {
      setNotice({
        kind: "danger",
        title: "Audio file too large",
        detail: `Each upload must be under ${formatBytes(limits.maxUploadBytes)}.`,
      });
      return;
    }
    if (referenceDuration && clipStart + clipDuration > referenceDuration + 0.05) {
      setNotice({
        kind: "warning",
        title: "Clip exceeds reference",
        detail: "Move the clip start earlier or shorten the selected duration.",
      });
      return;
    }

    setBusy("loading");
    setNotice({ kind: "info", title: "Evaluating performance", detail: "Backend is analyzing audio." });
    try {
      const response = await createEvaluation({
        reference: referenceFile,
        performance,
        performanceFilename,
        clipStartSeconds: clipStart,
        clipDurationSeconds: clipDuration,
        performanceStartSeconds: performanceStart,
      });
      setResult(response);
      setServiceOnline(true);
      setNotice({
        kind: "success",
        title: "Evaluation complete",
        detail: `Overall score: ${Math.round(response.scores.overall)}%.`,
      });
      const evaluationsResponse = await fetchEvaluations(5);
      setHistory(evaluationsResponse.evaluations);
    } catch (error) {
      setServiceOnline(false);
      setNotice(toNotice(error, "Evaluation failed."));
    } finally {
      setBusy("idle");
    }
  }

  async function toggleRecording() {
    if (busy === "recording") {
      await finishRecording();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setNotice({
        kind: "danger",
        title: "Microphone unavailable",
        detail: "This browser does not expose microphone recording.",
      });
      return;
    }
    try {
      recorderRef.current = await startWavRecorder();
      setPerformanceFile(null);
      setRecordedAudio(null);
      setBusy("recording");
      setNotice({ kind: "info", title: "Recording", detail: "Sing the selected clip." });
      startRecordingTimer();
    } catch {
      setBusy("idle");
      setNotice({
        kind: "danger",
        title: "Microphone access blocked",
        detail: "Allow microphone access or upload a singing file instead.",
      });
    }
  }

  function startRecordingTimer() {
    setRecordingSeconds(DEFAULT_RECORD_SECONDS);
    timerRef.current = window.setInterval(() => {
      setRecordingSeconds((seconds) => {
        if (seconds <= 1) {
          void finishRecording();
          return DEFAULT_RECORD_SECONDS;
        }
        return seconds - 1;
      });
    }, 1000);
  }

  async function finishRecording() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    const blob = await stopRecorder();
    if (blob) {
      setRecordedAudio({ blob, filename: "seekphony-performance.wav" });
      setNotice({
        kind: "success",
        title: "Recording ready",
        detail: "The WAV recording is ready for evaluation.",
      });
    }
    setBusy("idle");
    setRecordingSeconds(DEFAULT_RECORD_SECONDS);
  }

  async function stopRecorder(): Promise<Blob | null> {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    if (!recorder) {
      return null;
    }
    return recorder.stop();
  }

  function resetWorkspace() {
    setReferenceFile(null);
    setPerformanceFile(null);
    setRecordedAudio(null);
    setReferenceDuration(null);
    setClipStart(0);
    setClipDuration(15);
    setPerformanceStart(0);
    setResult(null);
    setNotice(null);
  }

  return (
    <main>
      <section className="hero-section" aria-labelledby="hero-title">
        <nav className="top-nav" aria-label="Primary">
          <div className="brand-mark">
            <Music2 aria-hidden="true" size={28} />
            <span>Seekphony</span>
          </div>
          <div className={`service-pill ${serviceTone}`}>
            <Signal aria-hidden="true" size={16} />
            <span>{serviceLabel}</span>
          </div>
        </nav>

        <div className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Explainable singing evaluator</p>
            <h1 id="hero-title">Seekphony</h1>
            <p className="hero-subtitle">
              Compare your singing against a chosen song clip and get pitch, rhythm, stability,
              coverage, audio-quality, and AI explanation signals in one workflow.
            </p>
            <div className="hero-actions">
              <a className="primary-link" href="#evaluate">
                <Mic aria-hidden="true" size={18} />
                Start Evaluation
              </a>
              <button className="ghost-button" type="button" onClick={() => void loadRuntime()}>
                <RefreshCw aria-hidden="true" size={18} />
                Refresh Backend
              </button>
            </div>
          </div>
          <div className="wave-hero" aria-hidden="true">
            {Array.from({ length: 32 }, (_, index) => (
              <span key={index} style={{ "--i": index } as CSSProperties} />
            ))}
          </div>
        </div>
      </section>

      <section className="workspace-band" id="evaluate" aria-labelledby="evaluate-title">
        <div className="workspace-grid">
          <form className="evaluate-panel" onSubmit={handleSubmit}>
            <div className="section-heading">
              <p className="eyebrow">Evaluation workspace</p>
              <h2 id="evaluate-title">Upload, clip, sing, evaluate</h2>
            </div>

            <div className="step-grid">
              <FilePicker
                id="reference-audio"
                icon={<Music2 aria-hidden="true" size={20} />}
                label="Reference song audio"
                detail={referenceFile?.name ?? "Upload a song or backing clip"}
                onChange={(file) => {
                  setReferenceFile(file);
                  setClipStart(0);
                }}
              />
              <FilePicker
                id="performance-audio"
                icon={<FileAudio aria-hidden="true" size={20} />}
                label="Performance audio"
                detail={performanceLabel}
                onChange={(file) => {
                  setPerformanceFile(file);
                  setRecordedAudio(null);
                }}
              />
            </div>

            <div className="clip-panel" aria-label="Clip settings">
              <div className="clip-title">
                <Scissors aria-hidden="true" size={20} />
                <div>
                  <strong>Reference clip</strong>
                  <span>
                    {referenceDuration
                      ? `Reference length: ${formatSeconds(referenceDuration)}`
                      : "Backend will validate the selected window."}
                  </span>
                </div>
              </div>
              <label>
                <span>Clip start seconds</span>
                <input
                  min={0}
                  max={maxClipStart || undefined}
                  step={0.5}
                  type="number"
                  value={clipStart}
                  onChange={(event) => setClipStart(Number(event.target.value))}
                />
              </label>
              <input
                aria-label="Clip start slider"
                disabled={!referenceDuration}
                min={0}
                max={maxClipStart}
                step={0.5}
                type="range"
                value={Math.min(clipStart, maxClipStart)}
                onChange={(event) => setClipStart(Number(event.target.value))}
              />
              <div className="clip-row">
                <label>
                  <span>Clip duration</span>
                  <input
                    min={limits.minClipSeconds}
                    max={limits.maxClipSeconds}
                    step={1}
                    type="number"
                    value={clipDuration}
                    onChange={(event) => setClipDuration(Number(event.target.value))}
                  />
                </label>
                <label>
                  <span>Performance start</span>
                  <input
                    min={0}
                    step={0.5}
                    type="number"
                    value={performanceStart}
                    onChange={(event) => setPerformanceStart(Number(event.target.value))}
                  />
                </label>
              </div>
            </div>

            <div className="record-panel">
              <button
                className={busy === "recording" ? "record-button active" : "record-button"}
                disabled={busy === "loading"}
                type="button"
                onClick={() => void toggleRecording()}
              >
                <Mic aria-hidden="true" size={18} />
                {busy === "recording" ? `Stop ${recordingSeconds}s` : "Record WAV Take"}
              </button>
              <span>
                {recordedAudio ? "Recorded take ready." : "Use headphones for cleaner metrics."}
              </span>
            </div>

            {notice ? <NoticeBanner notice={notice} /> : null}

            <div className="panel-actions">
              <button className="primary-action" disabled={busy !== "idle"} type="submit">
                {busy === "loading" ? <Loader2 aria-hidden="true" size={18} /> : <Gauge aria-hidden="true" size={18} />}
                Evaluate Singing
              </button>
              <button className="ghost-button compact" type="button" onClick={resetWorkspace}>
                <RotateCcw aria-hidden="true" size={16} />
                Reset
              </button>
            </div>
          </form>

          <aside className="results-panel" aria-labelledby="results-title">
            <div className="section-heading">
              <p className="eyebrow">Structured result</p>
              <h2 id="results-title">Score and explanation</h2>
            </div>
            {result ? <EvaluationResult result={result} /> : <EmptyResult serviceOnline={serviceOnline} />}
          </aside>
        </div>
      </section>

      <section className="history-band" aria-labelledby="history-title">
        <div className="section-heading">
          <p className="eyebrow">Evaluation data</p>
          <h2 id="history-title">Recent saved evaluations</h2>
        </div>
        <div className="history-grid">
          {history.length ? (
            history.map((evaluation) => <HistoryCard evaluation={evaluation} key={evaluation.evaluation_id} />)
          ) : (
            <div className="empty-history">
              <Database aria-hidden="true" size={24} />
              <span>No evaluation records loaded yet.</span>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function FilePicker({
  id,
  icon,
  label,
  detail,
  onChange,
}: {
  id: string;
  icon: ReactNode;
  label: string;
  detail: string;
  onChange: (file: File | null) => void;
}) {
  return (
    <label className="file-picker" htmlFor={id}>
      {icon}
      <span>
        <strong>{label}</strong>
        <small>{detail}</small>
      </span>
      <Upload aria-hidden="true" size={18} />
      <input
        accept="audio/*,video/mp4,video/webm"
        id={id}
        type="file"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}

function EvaluationResult({ result }: { result: EvaluationResponse }) {
  return (
    <div className="result-stack">
      <ScoreSummary scores={result.scores} />
      <MetricGrid metrics={result.metrics} />
      {result.warnings.length ? <WarningList warnings={result.warnings} /> : null}
      <SegmentList segments={result.segments} />
      <ExplanationPanel result={result} />
    </div>
  );
}

function ScoreSummary({ scores }: { scores: Scores }) {
  const scoreItems = [
    ["Pitch", scores.pitch],
    ["Rhythm", scores.rhythm],
    ["Stability", scores.stability],
    ["Coverage", scores.coverage],
    ["Audio quality", scores.audio_quality],
  ];
  return (
    <section className="score-box">
      <div className="score-ring" style={{ "--score": `${scores.overall}%` } as CSSProperties}>
        <span>{Math.round(scores.overall)}%</span>
      </div>
      <div className="score-bars">
        {scoreItems.map(([label, value]) => (
          <div className="score-bar" key={label}>
            <div>
              <span>{label}</span>
              <strong>{Math.round(Number(value))}%</strong>
            </div>
            <div className="bar-track">
              <span style={{ width: `${Number(value)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MetricGrid({ metrics }: { metrics: Metrics }) {
  const items = [
    ["Key shift", metrics.key_shift_semitones == null ? "n/a" : `${metrics.key_shift_semitones} st`],
    [
      "Pitch error",
      metrics.pitch_error_cents == null ? "n/a" : `${Math.round(metrics.pitch_error_cents)} cents`,
    ],
    [
      "Timing offset",
      metrics.timing_offset_ms == null ? "n/a" : `${Math.round(metrics.timing_offset_ms)} ms`,
    ],
    ["Voiced coverage", `${Math.round(metrics.voiced_coverage * 100)}%`],
    ["Confidence", `${Math.round(metrics.confidence * 100)}%`],
  ];
  return (
    <section className="metric-grid" aria-label="Evaluation metrics">
      {items.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function WarningList({ warnings }: { warnings: string[] }) {
  return (
    <section className="warning-box">
      <AlertTriangle aria-hidden="true" size={20} />
      <div>
        <strong>Warnings</strong>
        {warnings.map((warning) => (
          <p key={warning}>{warning}</p>
        ))}
      </div>
    </section>
  );
}

function SegmentList({ segments }: { segments: ProblemSegment[] }) {
  if (!segments.length) {
    return (
      <section className="segment-box">
        <ShieldCheck aria-hidden="true" size={20} />
        <span>No major weak segments detected.</span>
      </section>
    );
  }
  return (
    <section className="segment-box vertical">
      <strong>Weak segments</strong>
      {segments.map((segment) => (
        <div className="segment-row" key={`${segment.start_seconds}-${segment.issue}`}>
          <span>
            {formatSeconds(segment.start_seconds)} - {formatSeconds(segment.end_seconds)}
          </span>
          <b>{segment.severity}</b>
          <p>{segment.detail}</p>
        </div>
      ))}
    </section>
  );
}

function ExplanationPanel({ result }: { result: EvaluationResponse }) {
  const explanation = result.explanation;
  if (explanation.status !== "available" || !explanation.content) {
    return (
      <section className={`explanation-box ${explanation.status}`}>
        <Sparkles aria-hidden="true" size={20} />
        <div>
          <strong>AI explanation {explanation.status}</strong>
          <p>{explanation.error ?? "Gemini did not return an explanation."}</p>
        </div>
      </section>
    );
  }
  return (
    <section className="explanation-box available">
      <Sparkles aria-hidden="true" size={20} />
      <div>
        <strong>AI explanation</strong>
        <p>{explanation.content.summary}</p>
        <List label="Strengths" items={explanation.content.strengths} />
        <List label="Focus" items={explanation.content.focus_areas} />
        <List label="Practice" items={explanation.content.practice_steps} />
      </div>
    </section>
  );
}

function List({ label, items }: { label: string; items: string[] }) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="mini-list">
      <span>{label}</span>
      {items.slice(0, 3).map((item) => (
        <p key={item}>{item}</p>
      ))}
    </div>
  );
}

function EmptyResult({ serviceOnline }: { serviceOnline: boolean | null }) {
  return (
    <div className="empty-result">
      <Waves aria-hidden="true" size={30} />
      <strong>{serviceOnline === false ? "Backend response unavailable" : "No evaluation yet"}</strong>
      <p>
        {serviceOnline === false
          ? "The interface still works. Reconnect the backend and retry."
          : "Upload a reference clip and your singing to generate metrics."}
      </p>
    </div>
  );
}

function HistoryCard({ evaluation }: { evaluation: EvaluationResponse }) {
  return (
    <article className="history-card">
      <Clock3 aria-hidden="true" size={18} />
      <div>
        <strong>{Math.round(evaluation.scores.overall)}%</strong>
        <span>{new Date(evaluation.created_at).toLocaleString()}</span>
        <small>{evaluation.reference_filename}</small>
      </div>
    </article>
  );
}

function NoticeBanner({ notice }: { notice: Notice }) {
  const Icon = notice.kind === "danger" ? AlertTriangle : notice.kind === "success" ? ShieldCheck : Sparkles;
  return (
    <div className={`notice ${notice.kind}`} role="status">
      <Icon aria-hidden="true" size={20} />
      <div>
        <strong>{notice.title}</strong>
        <p>{notice.detail}</p>
      </div>
    </div>
  );
}

async function startWavRecorder(): Promise<WavRecorder> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
  const context = new AudioContextCtor();
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const gain = context.createGain();
  gain.gain.value = 0;
  const chunks: Float32Array[] = [];
  let sampleCount = 0;

  processor.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    const copy = new Float32Array(input.length);
    copy.set(input);
    chunks.push(copy);
    sampleCount += copy.length;
  };

  source.connect(processor);
  processor.connect(gain);
  gain.connect(context.destination);

  return {
    stop: async () => {
      processor.disconnect();
      source.disconnect();
      gain.disconnect();
      stream.getTracks().forEach((track) => track.stop());
      await context.close();
      return encodeWav(chunks, sampleCount, context.sampleRate);
    },
  };
}

function encodeWav(chunks: Float32Array[], sampleCount: number, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + sampleCount * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, sampleCount * 2, true);

  let offset = 44;
  for (const chunk of chunks) {
    for (const sample of chunk) {
      const clamped = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
      offset += 2;
    }
  }
  return new Blob([view], { type: "audio/wav" });
}

function writeString(view: DataView, offset: number, value: string) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

function toNotice(error: unknown, fallbackTitle: string): Notice {
  if (error instanceof SeekphonyApiError) {
    return {
      kind: error.retryable ? "warning" : "danger",
      title: fallbackTitle,
      detail: error.message,
    };
  }
  return {
    kind: "danger",
    title: fallbackTitle,
    detail: "Unexpected UI error while handling the backend response.",
  };
}

function formatSeconds(value: number): string {
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(value)}s`;
}

function formatBytes(value: number): string {
  const megabytes = value / (1024 * 1024);
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(megabytes)} MB`;
}
