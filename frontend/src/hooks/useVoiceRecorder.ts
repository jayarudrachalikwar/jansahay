import { useCallback, useRef, useState } from "react";

export type RecorderState = "idle" | "recording" | "error";

interface UseVoiceRecorderReturn {
  state: RecorderState;
  errorMessage: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
}

export function useVoiceRecorder(): UseVoiceRecorderReturn {
  const [state, setState] = useState<RecorderState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    setErrorMessage(null);
    chunksRef.current = [];

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setErrorMessage(
        "Microphone access denied. Please allow microphone permissions and try again.",
      );
      setState("error");
      return;
    }

    try {
      const mimeType = getSupportedMimeType();
      console.log("[VOICE] Recording started — MIME type:", mimeType ?? "(browser default)");
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(100); // collect data every 100ms
      setState("recording");
    } catch {
      stream.getTracks().forEach((t) => t.stop());
      setErrorMessage("Unable to start recording. Please try again.");
      setState("error");
    }
  }, []);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        setState("idle");
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });
        // Stop all tracks to release the microphone
        recorder.stream.getTracks().forEach((t) => t.stop());
        mediaRecorderRef.current = null;
        chunksRef.current = [];
        setState("idle");
        console.log("[VOICE] Recording stopped — Blob MIME type:", blob.type, "size:", blob.size);
        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  return { state, errorMessage, startRecording, stopRecording };
}

function getSupportedMimeType(): string | null {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
    "audio/mp4",
  ];
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return null;
}
