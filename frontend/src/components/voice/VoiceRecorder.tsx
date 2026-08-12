import { useVoiceRecorder } from "../../hooks/useVoiceRecorder";

interface VoiceRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  isDisabled?: boolean;
}

export default function VoiceRecorder({
  onRecordingComplete,
  isDisabled = false,
}: VoiceRecorderProps) {
  const { state, errorMessage, startRecording, stopRecording } =
    useVoiceRecorder();

  async function handleToggle() {
    if (state === "recording") {
      const blob = await stopRecording();
      if (blob && blob.size > 0) {
        onRecordingComplete(blob);
      }
    } else {
      await startRecording();
    }
  }

  const isRecording = state === "recording";

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={handleToggle}
        disabled={isDisabled || state === "error"}
        aria-label={isRecording ? "Stop recording" : "Start voice recording"}
        className={`flex h-10 w-10 items-center justify-center rounded-lg border text-lg transition
          ${
            isRecording
              ? "animate-pulse border-rose-500 bg-rose-50 text-rose-600"
              : "border-slate-300 bg-white text-slate-700 hover:border-emerald-600 hover:text-emerald-700"
          }
          disabled:cursor-not-allowed disabled:opacity-60`}
      >
        {isRecording ? "⏹" : "🎤"}
      </button>
      {isRecording && (
        <span className="text-xs font-medium text-rose-600">Recording…</span>
      )}
      {errorMessage && (
        <p className="max-w-xs text-xs text-rose-600">{errorMessage}</p>
      )}
    </div>
  );
}
