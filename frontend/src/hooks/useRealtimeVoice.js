import { useRef, useEffect, useCallback } from "react";

const BACKEND_URL = "http://127.0.0.1:8000";

// Tuned values
const SILENCE_THRESHOLD = 10;
const SPEECH_THRESHOLD = 22;
const SILENCE_DELAY_MS = 2800;
const MIN_SPEECH_MS = 800;
const VAD_INTERVAL_MS = 80;

export const useRealtimeVoice = (sessionId, onCoachText, onUserText) => {
  // ✅ CLEAN STATES
  const isListeningRef = useRef(false);
  const isRecordingRef = useRef(false);
  const isSpeakingRef  = useRef(false);
  const isProcessingRef = useRef(false);

  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const vadTimerRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const speechStartRef = useRef(null);
  const silenceTimerRef = useRef(null);

  const onCoachTextRef = useRef(onCoachText);
  const onUserTextRef = useRef(onUserText);

  useEffect(() => { onCoachTextRef.current = onCoachText; }, [onCoachText]);
  useEffect(() => { onUserTextRef.current = onUserText; }, [onUserText]);

  // ================= RMS =================
  const getRMS = (analyser) => {
    const buf = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) {
      const v = buf[i] - 128;
      sum += v * v;
    }
    return Math.sqrt(sum / buf.length);
  };

  // ================= TTS =================
  const speakReply = useCallback((text, audioB64) => {
    isSpeakingRef.current = true;

    if (!audioB64) {
      console.error("❌ No TTS audio");
      isSpeakingRef.current = false;
      return;
    }

    const bytes = Uint8Array.from(atob(audioB64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    audio.onended = () => {
      isSpeakingRef.current = false;
      URL.revokeObjectURL(url);
    };

    audio.onerror = () => {
      isSpeakingRef.current = false;
    };

    audio.play();
  }, []);

  // ================= SEND =================
  const sendAudio = useCallback(async (blob) => {
    if (isProcessingRef.current) return;

    isProcessingRef.current = true;

    const formData = new FormData();
    formData.append("audio", blob, "voice.webm");
    formData.append("session_id", String(sessionId));

    try {
      const res = await fetch(`${BACKEND_URL}/voice/transcribe-and-respond`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (data?.transcript) {
        onUserTextRef.current?.(data.transcript);
      }

      if (data?.coach_message) {
        onCoachTextRef.current?.(data.coach_message);
        speakReply(data.coach_message, data.audio_b64);
      }

    } catch (err) {
      console.error("❌ Send error:", err);
    } finally {
      isProcessingRef.current = false;
    }
  }, [sessionId, speakReply]);

  // ================= RECORD =================
  const stopRecording = () => {
    if (!isRecordingRef.current) return;

    isRecordingRef.current = false;
    mediaRecorderRef.current?.stop();
  };

  const createRecorder = (stream) => {
    const mimeType = "audio/webm";

    const mr = new MediaRecorder(stream, { mimeType });

    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mr.onstop = () => {
      const elapsed = Date.now() - (speechStartRef.current || 0);

      if (elapsed >= MIN_SPEECH_MS && chunksRef.current.length) {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        sendAudio(blob);
      }

      chunksRef.current = [];
    };

    return mr;
  };

  // ================= VAD =================
  const startVAD = useCallback(() => {
    clearInterval(vadTimerRef.current);

    vadTimerRef.current = setInterval(() => {
      if (!isListeningRef.current) return;
      if (isSpeakingRef.current) return;
      if (isProcessingRef.current) return;

      const rms = getRMS(analyserRef.current);

      if (!isRecordingRef.current && rms > SPEECH_THRESHOLD) {
        if (rms < 28) return;

        isRecordingRef.current = true;
        speechStartRef.current = Date.now();
        chunksRef.current = [];

        mediaRecorderRef.current.start();
      }

      else if (isRecordingRef.current) {
        if (rms < SILENCE_THRESHOLD) {
          if (!silenceTimerRef.current) {
            silenceTimerRef.current = setTimeout(() => {
              silenceTimerRef.current = null;
              stopRecording();
            }, SILENCE_DELAY_MS);
          }
        } else {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
      }

    }, VAD_INTERVAL_MS);

  }, []);

  // ================= START =================
  const startVoice = useCallback(async () => {
    if (isListeningRef.current) return;

    isListeningRef.current = true;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const audioCtx = new AudioContext();
    audioCtxRef.current = audioCtx;

    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;

    source.connect(analyser);
    analyserRef.current = analyser;

    mediaRecorderRef.current = createRecorder(stream);

    startVAD();

  }, [startVAD]);

  // ================= STOP =================
  const stopVoice = useCallback(() => {
    isListeningRef.current = false;

    clearInterval(vadTimerRef.current);
    clearTimeout(silenceTimerRef.current);

    streamRef.current?.getTracks().forEach(t => t.stop());
    audioCtxRef.current?.close();

    isRecordingRef.current = false;
    isSpeakingRef.current = false;
    isProcessingRef.current = false;

  }, []);

  useEffect(() => {
    return () => stopVoice();
  }, [stopVoice]);

  return { startVoice, stopVoice };
};