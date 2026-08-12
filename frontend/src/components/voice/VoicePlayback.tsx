import { useEffect, useRef, useState } from "react";
import { base64ToAudioUrl } from "../../services/voiceService";

interface VoicePlaybackProps {
  audioBase64: string;
  label?: string;
}

export default function VoicePlayback({ audioBase64, label = "Play response" }: VoicePlaybackProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!audioBase64) return;
    const url = base64ToAudioUrl(audioBase64);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audioBase64]);

  function handleToggle() {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;

    if (isPlaying) {
      audio.pause();
      audio.currentTime = 0;
      setIsPlaying(false);
    } else {
      audio.src = audioUrl;
      audio.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  }

  if (!audioBase64) return null;

  return (
    <div className="flex items-center gap-2">
      {audioUrl && (
        <audio
          ref={audioRef}
          onEnded={() => setIsPlaying(false)}
          onError={() => setIsPlaying(false)}
          aria-label="Assistant audio response"
        />
      )}
      <button
        type="button"
        onClick={handleToggle}
        className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-emerald-600 hover:text-emerald-700"
        aria-label={isPlaying ? "Stop audio" : label}
      >
        <span>{isPlaying ? "⏹" : "▶"}</span>
        <span>{isPlaying ? "Stop" : label}</span>
      </button>
    </div>
  );
}
