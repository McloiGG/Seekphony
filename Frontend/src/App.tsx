import {
  AlertTriangle,
  Clock3,
  Database,
  Gauge,
  Headphones,
  Link2,
  Loader2,
  Mic,
  Music2,
  PlayCircle,
  RotateCcw,
  Scissors,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, DragEvent, ReactNode } from "react";

import {
  clearEvaluationRecords,
  createEvaluation,
  deleteEvaluationRecord,
  fetchEvaluations,
  fetchHealth,
  importReferenceAudio,
  SeekphonyApiError,
} from "./api";
import type { EvaluationResponse, HealthResponse, Metrics, ProblemSegment, Scores } from "./types";

const DEFAULT_MAX_AUDIO_BYTES = 30 * 1024 * 1024;
const DEFAULT_MIN_CLIP_SECONDS = 5;
const DEFAULT_MAX_CLIP_SECONDS = 60;

type BusyState = "idle" | "loading" | "recording" | "importing";
type NoticeKind = "info" | "success" | "warning" | "danger";
type ReferenceMode = "upload" | "url";
type PerformanceMode = "upload" | "record";

interface Notice {
  kind: NoticeKind;
  title: string;
  detail: string;
}

interface SelectedAudio {
  blob: Blob;
  filename: string;
  objectUrl: string | null;
  duration: number | null;
  title: string;
  sourceLabel: string;
}

interface WavRecorder {
  stop: () => Promise<Blob>;
}

interface SourceTab<T extends string> {
  value: T;
  label: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null);
  const [history, setHistory] = useState<EvaluationResponse[]>([]);
  const [referenceMode, setReferenceMode] = useState<ReferenceMode>("upload");
  const [performanceMode, setPerformanceMode] = useState<PerformanceMode>("record");
  const [referenceAudio, setReferenceAudio] = useState<SelectedAudio | null>(null);
  const [performanceAudio, setPerformanceAudio] = useState<SelectedAudio | null>(null);
  const [referenceUrl, setReferenceUrl] = useState("");
  const [referenceStart, setReferenceStart] = useState(0);
  const [performanceStart, setPerformanceStart] = useState(0);
  const [performanceEnd, setPerformanceEnd] = useState(DEFAULT_MAX_CLIP_SECONDS);
  const [recordDuration, setRecordDuration] = useState(DEFAULT_MAX_CLIP_SECONDS);
  const [recordDurationDraft, setRecordDurationDraft] = useState(
    formatNumberInput(DEFAULT_MAX_CLIP_SECONDS),
  );
  const [recordElapsedSeconds, setRecordElapsedSeconds] = useState<number | null>(null);
  const [recordRemainingSeconds, setRecordRemainingSeconds] = useState<number | null>(null);
  const [busy, setBusy] = useState<BusyState>("idle");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [result, setResult] = useState<EvaluationResponse | null>(null);
  const [selectedHistory, setSelectedHistory] = useState<EvaluationResponse | null>(null);
  const recorderRef = useRef<WavRecorder | null>(null);
  const recordingDurationRef = useRef(DEFAULT_MAX_CLIP_SECONDS);
  const timerRef = useRef<number | null>(null);
  const referenceRef = useRef<SelectedAudio | null>(null);
  const performanceRef = useRef<SelectedAudio | null>(null);

  const limits = {
    maxUploadBytes: health?.limits.max_upload_bytes ?? DEFAULT_MAX_AUDIO_BYTES,
    minClipSeconds: health?.limits.min_clip_seconds ?? DEFAULT_MIN_CLIP_SECONDS,
    maxClipSeconds: health?.limits.max_clip_seconds ?? DEFAULT_MAX_CLIP_SECONDS,
  };

  const evaluationDuration = Math.max(0, performanceEnd - performanceStart);
  const maxReferenceStart = Math.max(0, (referenceAudio?.duration ?? referenceStart) - evaluationDuration);
  const performanceDuration = performanceAudio?.duration ?? null;
  const maxPerformanceStart =
    performanceDuration == null ? undefined : Math.max(0, performanceDuration - limits.minClipSeconds);
  const maxPerformanceEnd = performanceDuration ?? undefined;
  const performanceLimitMessage =
    performanceDuration != null &&
    (performanceStart > (maxPerformanceStart ?? performanceDuration) + 0.05 ||
      performanceEnd > performanceDuration + 0.05)
      ? `Performance trim must stay within ${formatSeconds(performanceDuration)}.`
      : null;
  const loadRuntime = useCallback(async () => {
    try {
      const [healthResponse, evaluationsResponse] = await Promise.all([
        fetchHealth(),
        fetchEvaluations(5),
      ]);
      setHealth(healthResponse);
      setHistory(evaluationsResponse.evaluations);
      setRecordDuration(healthResponse.limits.max_clip_seconds);
      setRecordDurationDraft(formatNumberInput(healthResponse.limits.max_clip_seconds));
      setPerformanceEnd((current) =>
        clamp(current, healthResponse.limits.min_clip_seconds, healthResponse.limits.max_clip_seconds),
      );
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
      setRecordElapsedSeconds(null);
      setRecordRemainingSeconds(null);
      void stopRecorder();
      revokeAudio(referenceRef.current);
      revokeAudio(performanceRef.current);
    };
  }, [loadRuntime]);

  useEffect(() => {
    referenceRef.current = referenceAudio;
  }, [referenceAudio]);

  useEffect(() => {
    performanceRef.current = performanceAudio;
  }, [performanceAudio]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!referenceAudio) {
      setNotice({
        kind: "warning",
        title: "Reference audio needed",
        detail: "Upload a reference file or load a direct audio URL or YouTube link.",
      });
      return;
    }
    if (!performanceAudio) {
      setNotice({
        kind: "warning",
        title: "Performance audio needed",
        detail: "Upload your singing or record a take before evaluating.",
      });
      return;
    }
    const validation = validateWorkspace();
    if (validation) {
      setNotice(validation);
      return;
    }

    setBusy("loading");
    setNotice({ kind: "info", title: "Evaluating performance", detail: "Backend is analyzing audio." });
    try {
      const response = await createEvaluation({
        reference: referenceAudio.blob,
        referenceFilename: referenceAudio.filename,
        performance: performanceAudio.blob,
        performanceFilename: performanceAudio.filename,
        clipStartSeconds: referenceStart,
        clipDurationSeconds: evaluationDuration,
        performanceStartSeconds: performanceStart,
      });
      setResult(response);
      setServiceOnline(true);
      setNotice({
        kind: "success",
        title: "Evaluation complete",
        detail: `Overall score: ${Math.round(response.scores.overall)}%.`,
      });
      await refreshHistory();
    } catch (error) {
      setServiceOnline(false);
      setNotice(toNotice(error, "Evaluation failed."));
    } finally {
      setBusy("idle");
    }
  }

  function validateWorkspace(): Notice | null {
    if (referenceAudio && referenceAudio.blob.size > limits.maxUploadBytes) {
      return {
        kind: "danger",
        title: "Reference audio is too large",
        detail: `Reference audio must be under ${formatBytes(limits.maxUploadBytes)}.`,
      };
    }
    if (performanceAudio && performanceAudio.blob.size > limits.maxUploadBytes) {
      return {
        kind: "danger",
        title: "Performance audio is too large",
        detail: `Performance audio must be under ${formatBytes(limits.maxUploadBytes)}.`,
      };
    }
    if (evaluationDuration < limits.minClipSeconds || evaluationDuration > limits.maxClipSeconds) {
      return {
        kind: "warning",
        title: "Clip duration outside limits",
        detail: `Evaluation clips must be between ${formatSeconds(limits.minClipSeconds)} and ${formatSeconds(limits.maxClipSeconds)}.`,
      };
    }
    if (performanceStart < 0 || performanceEnd <= performanceStart) {
      return {
        kind: "warning",
        title: "Performance trim is invalid",
        detail: "Performance end must be later than performance start.",
      };
    }
    if (performanceAudio?.duration && performanceEnd > performanceAudio.duration + 0.05) {
      return {
        kind: "warning",
        title: "Performance trim exceeds audio",
        detail: "Move the performance end earlier or upload a longer take.",
      };
    }
    if (referenceStart < 0) {
      return {
        kind: "warning",
        title: "Reference start is invalid",
        detail: "Reference start must be zero or greater.",
      };
    }
    if (referenceAudio?.duration && referenceStart + evaluationDuration > referenceAudio.duration + 0.05) {
      return {
        kind: "warning",
        title: "Reference clip exceeds audio",
        detail: "Move the reference start earlier or choose a shorter performance duration.",
      };
    }
    return null;
  }

  async function refreshHistory() {
    const evaluationsResponse = await fetchEvaluations(5);
    setHistory(evaluationsResponse.evaluations);
  }

  function replaceReferenceAudio(blob: Blob, filename: string, title: string, sourceLabel: string) {
    const objectUrl = createObjectUrl(blob);
    const audio: SelectedAudio = {
      blob,
      filename,
      objectUrl,
      duration: null,
      title,
      sourceLabel,
    };
    setReferenceStart(0);
    setReferenceAudio((current) => {
      revokeAudio(current);
      return audio;
    });
    loadAudioDuration(objectUrl, (duration) => {
      setReferenceAudio((current) =>
        current?.objectUrl === objectUrl ? { ...current, duration } : current,
      );
    });
  }

  function replacePerformanceAudio(blob: Blob, filename: string, title: string, sourceLabel: string) {
    const objectUrl = createObjectUrl(blob);
    const audio: SelectedAudio = {
      blob,
      filename,
      objectUrl,
      duration: null,
      title,
      sourceLabel,
    };
    const fallbackDuration = clamp(recordDuration, limits.minClipSeconds, limits.maxClipSeconds);
    setPerformanceStart(0);
    setPerformanceEnd(fallbackDuration);
    setPerformanceAudio((current) => {
      revokeAudio(current);
      return audio;
    });
    loadAudioDuration(objectUrl, (duration) => {
      const defaultEnd = clamp(duration, limits.minClipSeconds, limits.maxClipSeconds);
      setPerformanceEnd(defaultEnd);
      setPerformanceAudio((current) =>
        current?.objectUrl === objectUrl ? { ...current, duration } : current,
      );
    });
  }

  async function handleReferenceImport() {
    if (!referenceUrl.trim()) {
      setNotice({
        kind: "warning",
        title: "Reference URL needed",
        detail: "Paste a direct audio URL or YouTube link first.",
      });
      return;
    }
    setBusy("importing");
    setNotice({
      kind: "info",
      title: "Loading reference URL",
      detail: "Backend is importing the audio so you can confirm it before evaluation.",
    });
    try {
      const imported = await importReferenceAudio(referenceUrl);
      replaceReferenceAudio(
        imported.blob,
        imported.filename,
        imported.title,
        imported.sourceType === "youtube" ? "YouTube import" : "URL import",
      );
      setNotice({
        kind: "success",
        title: "Reference loaded",
        detail: `${imported.title} is ready for playback.`,
      });
    } catch (error) {
      setNotice(toNotice(error, "Reference import failed."));
    } finally {
      setBusy("idle");
    }
  }

  async function toggleRecording() {
    if (busy === "recording") {
      await finishRecording();
      return;
    }
    const duration = commitRecordDuration();
    if (performanceAudio && !window.confirm("Recording again will replace the current performance audio.")) {
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
      recordingDurationRef.current = duration;
      setBusy("recording");
      setPerformanceMode("record");
      setNotice({
        kind: "info",
        title: "Recording",
        detail: "Watch the elapsed and remaining timers below.",
      });
      startRecordingTimer(duration);
    } catch {
      setBusy("idle");
      setNotice({
        kind: "danger",
        title: "Microphone access blocked",
        detail: "Allow microphone access or upload a singing file instead.",
      });
    }
  }

  function startRecordingTimer(seconds: number) {
    const startAt = Date.now();
    const stopAt = startAt + seconds * 1000;
    setRecordElapsedSeconds(0);
    setRecordRemainingSeconds(Math.ceil(seconds));
    timerRef.current = window.setInterval(() => {
      const elapsed = Math.min(seconds, Math.floor((Date.now() - startAt) / 1000));
      const remaining = Math.max(0, Math.ceil((stopAt - Date.now()) / 1000));
      setRecordElapsedSeconds(elapsed);
      setRecordRemainingSeconds(remaining);
      if (remaining <= 0) {
        void finishRecording();
      }
    }, 1000);
  }

  async function finishRecording() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRecordElapsedSeconds(null);
    setRecordRemainingSeconds(null);
    const blob = await stopRecorder();
    if (blob) {
      replacePerformanceAudio(blob, "seekphony-performance.wav", "Recorded WAV take", "Recording");
      setPerformanceEnd(clamp(recordingDurationRef.current, limits.minClipSeconds, limits.maxClipSeconds));
      setNotice({
        kind: "success",
        title: "Recording ready",
        detail: "The WAV recording is ready for playback and evaluation.",
      });
    }
    setBusy("idle");
  }

  function updateRecordDurationDraft(value: string) {
    setRecordDurationDraft(value);
    const parsed = parseOptionalNumber(value);
    if (
      parsed != null &&
      parsed >= limits.minClipSeconds &&
      parsed <= limits.maxClipSeconds
    ) {
      setRecordDuration(parsed);
    }
  }

  function commitRecordDuration(): number {
    const parsed = parseOptionalNumber(recordDurationDraft);
    const next = clamp(parsed ?? recordDuration, limits.minClipSeconds, limits.maxClipSeconds);
    setRecordDuration(next);
    setRecordDurationDraft(formatNumberInput(next));
    return next;
  }

  async function stopRecorder(): Promise<Blob | null> {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    if (!recorder) {
      return null;
    }
    return recorder.stop();
  }

  async function handleDeleteEvaluation(evaluationId: number) {
    if (!window.confirm("Delete this saved evaluation?")) {
      return;
    }
    try {
      await deleteEvaluationRecord(evaluationId);
      setHistory((current) => current.filter((evaluation) => evaluation.evaluation_id !== evaluationId));
      setSelectedHistory((current) => (current?.evaluation_id === evaluationId ? null : current));
      setNotice({ kind: "success", title: "Evaluation deleted", detail: "Saved result was removed." });
    } catch (error) {
      setNotice(toNotice(error, "Delete failed."));
    }
  }

  async function handleClearEvaluations() {
    if (!history.length || !window.confirm("Clear all saved evaluations?")) {
      return;
    }
    try {
      await clearEvaluationRecords();
      setHistory([]);
      setSelectedHistory(null);
      setNotice({ kind: "success", title: "History cleared", detail: "All saved results were removed." });
    } catch (error) {
      setNotice(toNotice(error, "Clear history failed."));
    }
  }

  function resetWorkspace() {
    setReferenceAudio((current) => {
      revokeAudio(current);
      return null;
    });
    setPerformanceAudio((current) => {
      revokeAudio(current);
      return null;
    });
    setReferenceUrl("");
    setReferenceStart(0);
    setPerformanceStart(0);
    setPerformanceEnd(limits.maxClipSeconds);
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
        </nav>

        <div className="hero-copy">
          <p className="eyebrow">Explainable singing evaluator</p>
          <h1 id="hero-title">Seekphony</h1>
          <p className="hero-subtitle">
            Compare your singing against a chosen song clip, then review pitch, rhythm,
            stability, coverage, audio quality, and AI explanation signals.
          </p>
          <div className="hero-actions">
            <a className="primary-link" href="#evaluate">
              <Mic aria-hidden="true" size={18} />
              Start Evaluation
            </a>
          </div>
        </div>
      </section>

      <section className="workspace-band" id="evaluate" aria-labelledby="evaluate-title">
        <div className="workspace-grid">
          <form className="evaluate-panel" onSubmit={handleSubmit}>
            <div className="section-heading">
              <p className="eyebrow">Evaluation workspace</p>
              <h2 id="evaluate-title">Choose audio, trim, evaluate</h2>
              <p className="helper-copy">
                Evaluation clips must be between {formatSeconds(limits.minClipSeconds)} and{" "}
                {formatSeconds(limits.maxClipSeconds)}. Max file/import size:{" "}
                {formatBytes(limits.maxUploadBytes)}.
              </p>
            </div>

            <div className="source-grid">
              <SourcePanel
                description="Use the original song, backing track, or reference clip."
                icon={<Music2 aria-hidden="true" size={20} />}
                title="Reference audio"
              >
                <Tabs
                  active={referenceMode}
                  ariaLabel="Reference source"
                  onChange={setReferenceMode}
                  tabs={[
                    { value: "upload", label: "Upload" },
                    { value: "url", label: "URL" },
                  ]}
                />
                <div className={`source-body ${referenceMode === "upload" ? "upload-mode" : "url-mode"}`}>
                  {referenceMode === "upload" ? (
                    <FilePicker
                      id="reference-upload"
                      label="Reference upload"
                      onChange={(file) => {
                        if (file) {
                          replaceReferenceAudio(file, file.name, file.name, "Upload");
                        }
                      }}
                    />
                  ) : (
                    <div className="url-import">
                      <p>Paste a direct audio URL or YouTube link. YouTube import is best effort.</p>
                      <label>
                        <span>Reference URL</span>
                        <input
                          placeholder="https://..."
                          type="url"
                          value={referenceUrl}
                          onChange={(event) => setReferenceUrl(event.target.value)}
                        />
                      </label>
                      <button
                        className="ghost-button compact"
                        disabled={busy !== "idle"}
                        type="button"
                        onClick={() => void handleReferenceImport()}
                      >
                        {busy === "importing" ? (
                          <Loader2 aria-hidden="true" size={16} />
                        ) : (
                          <Link2 aria-hidden="true" size={16} />
                        )}
                        Load URL
                      </button>
                    </div>
                  )}
                </div>
                <AudioPreview audio={referenceAudio} label="Reference playback" />
              </SourcePanel>

              <SourcePanel
                description="Upload or record the singing you want scored."
                icon={<Headphones aria-hidden="true" size={20} />}
                title="Performance audio"
              >
                <Tabs
                  active={performanceMode}
                  ariaLabel="Performance source"
                  onChange={setPerformanceMode}
                  tabs={[
                    { value: "record", label: "Record" },
                    { value: "upload", label: "Upload" },
                  ]}
                />
                <div
                  className={`source-body ${
                    performanceMode === "record" ? "record-mode" : "upload-mode"
                  }`}
                >
                  {performanceMode === "record" ? (
                    <div className="record-controls">
                      <label>
                        <span>Record duration</span>
                        <input
                          max={limits.maxClipSeconds}
                          min={limits.minClipSeconds}
                          step={1}
                          type="number"
                          value={recordDurationDraft}
                          onBlur={() => commitRecordDuration()}
                          onChange={(event) => updateRecordDurationDraft(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              commitRecordDuration();
                            }
                          }}
                        />
                      </label>
                      <button
                        className={busy === "recording" ? "record-button active" : "record-button"}
                        disabled={busy === "loading" || busy === "importing"}
                        type="button"
                        onClick={() => void toggleRecording()}
                      >
                        <Mic aria-hidden="true" size={18} />
                        {busy === "recording" ? "Stop recording" : "Record WAV take"}
                      </button>
                      {busy === "recording" &&
                      recordElapsedSeconds != null &&
                      recordRemainingSeconds != null ? (
                        <div className="record-status" role="status">
                          <div className="record-status-header">
                            <span>Recording in progress</span>
                            <small>Auto-stops when remaining hits 00:00</small>
                          </div>
                          <div className="record-timers">
                            <div className="timer-card elapsed">
                              <span>Elapsed</span>
                              <strong>{formatTimer(recordElapsedSeconds)}</strong>
                            </div>
                            <div className="timer-card remaining">
                              <span>Remaining</span>
                              <strong>{formatTimer(recordRemainingSeconds)}</strong>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <FilePicker
                      id="performance-upload"
                      label="Performance upload"
                      onChange={(file) => {
                        if (file) {
                          replacePerformanceAudio(file, file.name, file.name, "Upload");
                        }
                      }}
                    />
                  )}
                </div>
                <AudioPreview audio={performanceAudio} label="Performance playback" />
              </SourcePanel>
            </div>

            <div className="clip-panel" aria-label="Audio trim settings">
              <div className="clip-title">
                <Scissors aria-hidden="true" size={20} />
                <div>
                  <strong>Edit audio</strong>
                  <span>Reference duration follows the selected performance window.</span>
                </div>
              </div>

              <div className="trim-grid">
                <section className="trim-card">
                  <h3>Reference</h3>
                  <AudioScrub audio={referenceAudio} current={referenceStart} duration={evaluationDuration} />
                  <label>
                    <span>Start at</span>
                    <input
                      min={0}
                      max={maxReferenceStart || undefined}
                      step={0.5}
                      type="number"
                      value={referenceStart}
                      onChange={(event) => setReferenceStart(Number(event.target.value))}
                    />
                  </label>
                </section>

                <section className="trim-card">
                  <h3>Performance</h3>
                  <AudioScrub
                    audio={performanceAudio}
                    current={performanceStart}
                    duration={evaluationDuration}
                  />
                  <div className="clip-row">
                    <label>
                      <span>Start at</span>
                      <input
                        min={0}
                        max={maxPerformanceStart}
                        step={0.5}
                        type="number"
                        value={performanceStart}
                        onChange={(event) => setPerformanceStart(Number(event.target.value))}
                      />
                    </label>
                    <label>
                      <span>End at</span>
                      <input
                        min={limits.minClipSeconds}
                        max={maxPerformanceEnd}
                        step={0.5}
                        type="number"
                        value={performanceEnd}
                        onChange={(event) => setPerformanceEnd(Number(event.target.value))}
                      />
                    </label>
                  </div>
                  {performanceLimitMessage ? (
                    <p className="field-tip warning" role="status">
                      {performanceLimitMessage}
                    </p>
                  ) : null}
                  <p className="duration-note">Selected duration: {formatSeconds(evaluationDuration)}</p>
                </section>
              </div>
            </div>

            {notice ? <NoticeBanner notice={notice} /> : null}

            <div className="panel-actions">
              <button className="primary-action" disabled={busy !== "idle"} type="submit">
                {busy === "loading" ? (
                  <Loader2 aria-hidden="true" size={18} />
                ) : (
                  <Gauge aria-hidden="true" size={18} />
                )}
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
        <div className="history-heading">
          <div className="section-heading">
            <p className="eyebrow">Evaluation data</p>
            <h2 id="history-title">Recent saved evaluations</h2>
          </div>
          <button
            className="ghost-button compact danger"
            disabled={!history.length}
            type="button"
            onClick={() => void handleClearEvaluations()}
          >
            <Trash2 aria-hidden="true" size={16} />
            Clear all
          </button>
        </div>
        <div className="history-grid">
          {history.length ? (
            history.map((evaluation) => (
              <HistoryCard
                evaluation={evaluation}
                key={evaluation.evaluation_id}
                onDelete={() => void handleDeleteEvaluation(evaluation.evaluation_id)}
                onOpen={() => setSelectedHistory(evaluation)}
              />
            ))
          ) : (
            <div className="empty-history">
              <Database aria-hidden="true" size={24} />
              <span>No evaluation records loaded yet.</span>
            </div>
          )}
        </div>
      </section>

      {selectedHistory ? (
        <EvaluationDialog
          evaluation={selectedHistory}
          onClose={() => setSelectedHistory(null)}
          onDelete={() => void handleDeleteEvaluation(selectedHistory.evaluation_id)}
        />
      ) : null}
    </main>
  );
}

function SourcePanel({
  children,
  description,
  icon,
  title,
}: {
  children: ReactNode;
  description: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <section className="source-panel">
      <div className="source-title">
        {icon}
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function Tabs<T extends string>({
  active,
  ariaLabel,
  onChange,
  tabs,
}: {
  active: T;
  ariaLabel: string;
  onChange: (value: T) => void;
  tabs: SourceTab<T>[];
}) {
  return (
    <div className="tab-list" aria-label={ariaLabel} role="tablist">
      {tabs.map((tab) => (
        <button
          aria-selected={active === tab.value}
          className={active === tab.value ? "active" : ""}
          key={tab.value}
          role="tab"
          type="button"
          onClick={() => onChange(tab.value)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function FilePicker({
  id,
  label,
  onChange,
}: {
  id: string;
  label: string;
  onChange: (file: File | null) => void;
}) {
  const [isDragging, setIsDragging] = useState(false);

  function handleDrag(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "copy";
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    event.stopPropagation();
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
      return;
    }
    setIsDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
    onChange(event.dataTransfer.files?.[0] ?? null);
  }

  return (
    <label
      className={isDragging ? "file-picker dragging" : "file-picker"}
      htmlFor={id}
      onDragEnter={handleDrag}
      onDragLeave={handleDragLeave}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <Upload aria-hidden="true" size={18} />
      <span>
        <strong>{label}</strong>
        <small>Drag and drop or browse audio/video files.</small>
      </span>
      <input
        accept="audio/*,video/mp4,video/webm"
        id={id}
        type="file"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}

function AudioPreview({ audio, label }: { audio: SelectedAudio | null; label: string }) {
  return (
    <div className={audio ? "audio-preview ready" : "audio-preview empty"}>
      <PlayCircle aria-hidden="true" size={18} />
      <div>
        <strong>{audio ? `${label} ready` : `${label} unavailable`}</strong>
        <span>
          {audio
            ? `${audio.title} (${audio.sourceLabel}${audio.duration ? `, ${formatSeconds(audio.duration)}` : ""})`
            : "Load audio to enable playback."}
        </span>
      </div>
      <audio aria-label={label} controls src={audio?.objectUrl ?? undefined} />
    </div>
  );
}

function AudioScrub({
  audio,
  current,
  duration,
}: {
  audio: SelectedAudio | null;
  current: number;
  duration: number;
}) {
  const total = audio?.duration ?? Math.max(duration, current + duration);
  const startPercent = total > 0 ? Math.min(100, (current / total) * 100) : 0;
  const widthPercent = total > 0 ? Math.min(100 - startPercent, (duration / total) * 100) : 0;
  return (
    <div className="audio-scrub">
      <span>{formatSeconds(current)}</span>
      <div className="scrub-track">
        <i
          style={
            {
              "--start": `${startPercent}%`,
              "--width": `${widthPercent}%`,
            } as CSSProperties
          }
        />
      </div>
      <span>{audio?.duration ? formatSeconds(audio.duration) : "duration unknown"}</span>
    </div>
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
      <Sparkles aria-hidden="true" size={30} />
      <strong>{serviceOnline === false ? "Backend response unavailable" : "No evaluation yet"}</strong>
      <p>
        {serviceOnline === false
          ? "The interface still works. Reconnect the backend and retry."
          : "Load reference and performance audio to generate metrics."}
      </p>
    </div>
  );
}

function HistoryCard({
  evaluation,
  onDelete,
  onOpen,
}: {
  evaluation: EvaluationResponse;
  onDelete: () => void;
  onOpen: () => void;
}) {
  return (
    <article className="history-card">
      <button className="history-open" type="button" onClick={onOpen}>
        <Clock3 aria-hidden="true" size={18} />
        <span>
          <strong>{Math.round(evaluation.scores.overall)}%</strong>
          <small>{new Date(evaluation.created_at).toLocaleString()}</small>
          <em>{evaluation.reference_filename}</em>
        </span>
      </button>
      <button className="icon-button danger" aria-label="Delete saved evaluation" type="button" onClick={onDelete}>
        <Trash2 aria-hidden="true" size={16} />
      </button>
    </article>
  );
}

function EvaluationDialog({
  evaluation,
  onClose,
  onDelete,
}: {
  evaluation: EvaluationResponse;
  onClose: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="modal-backdrop">
      <section className="modal-panel" aria-labelledby="evaluation-detail-title" aria-modal="true" role="dialog">
        <div className="modal-header">
          <div>
            <p className="eyebrow">Saved evaluation</p>
            <h2 id="evaluation-detail-title">{Math.round(evaluation.scores.overall)}% overall</h2>
          </div>
          <button className="icon-button" aria-label="Close details" type="button" onClick={onClose}>
            <X aria-hidden="true" size={18} />
          </button>
        </div>
        <div className="detail-grid">
          <div>
            <span>Reference</span>
            <strong>{evaluation.reference_filename}</strong>
          </div>
          <div>
            <span>Performance</span>
            <strong>{evaluation.performance_filename}</strong>
          </div>
          <div>
            <span>Reference start</span>
            <strong>{formatSeconds(evaluation.clip_start_seconds)}</strong>
          </div>
          <div>
            <span>Duration</span>
            <strong>{formatSeconds(evaluation.clip_duration_seconds)}</strong>
          </div>
        </div>
        <EvaluationResult result={evaluation} />
        <div className="modal-actions">
          <button className="ghost-button compact danger" type="button" onClick={onDelete}>
            <Trash2 aria-hidden="true" size={16} />
            Delete
          </button>
          <button className="primary-action compact" type="button" onClick={onClose}>
            Close
          </button>
        </div>
      </section>
    </div>
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

function createObjectUrl(blob: Blob): string | null {
  if (typeof URL.createObjectURL !== "function") {
    return null;
  }
  try {
    return URL.createObjectURL(blob);
  } catch {
    return null;
  }
}

function revokeAudio(audio: SelectedAudio | null) {
  if (audio?.objectUrl && typeof URL.revokeObjectURL === "function") {
    URL.revokeObjectURL(audio.objectUrl);
  }
}

function loadAudioDuration(objectUrl: string | null, onDuration: (duration: number) => void) {
  if (!objectUrl) {
    return;
  }
  try {
    const audio = new Audio(objectUrl);
    audio.onloadedmetadata = () => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        onDuration(audio.duration);
      }
    };
  } catch {
    // Metadata probing is best-effort; backend validation remains authoritative.
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

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
}

function parseOptionalNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumberInput(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)));
}

function formatSeconds(value: number): string {
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(value)}s`;
}

function formatTimer(seconds: number): string {
  const safeSeconds = Math.max(0, Math.ceil(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function formatBytes(value: number): string {
  const megabytes = value / (1024 * 1024);
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(megabytes)} MB`;
}
