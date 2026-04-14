import { useRef, useEffect, useCallback } from "react";

const BACKEND_URL = "http://127.0.0.1:8000";

// -- tuneable constants --------------------------------------------------------
const SILENCE_THRESHOLD  = 10;
const SPEECH_THRESHOLD   = 22;
const SILENCE_DELAY_MS   = 3000;
const MIN_SPEECH_MS      = 900;
const VAD_INTERVAL_MS    = 80;
// -----------------------------------------------------------------------------

export const useRealtimeVoice = (sessionId, onCoachText, onUserText) => {
  const inVoiceModeRef   = useRef(false);
  const streamRef        = useRef(null);
  const audioCtxRef      = useRef(null);
  const analyserRef      = useRef(null);
  const vadTimerRef      = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef        = useRef([]);
  const isRecordingRef   = useRef(false);
  const speechStartRef   = useRef(null);
  const silenceTimerRef  = useRef(null);
  const playingAudioRef  = useRef(null);  // keep ref so audio element isn't GC'd

  // -- keep all callbacks in refs so closures never go stale ----------------
  const onCoachTextRef = useRef(onCoachText);
  const onUserTextRef  = useRef(onUserText);
  const startVADRef    = useRef(null);
  useEffect(() => { onCoachTextRef.current = onCoachText; }, [onCoachText]);
  useEffect(() => { onUserTextRef.current  = onUserText;  }, [onUserText]);

  // -- helpers ---------------------------------------------------------------

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

  const resumeListening = useCallback(() => {
    if (inVoiceModeRef.current) startVADRef.current?.();
  }, []);

  const speakReply = useCallback((text, audioB64) => {
    window.speechSynthesis.cancel();
    clearInterval(vadTimerRef.current);
    inVoiceModeRef.current = false;  //STOP listening while coach speaks

    if (audioB64) {
      const bytes = Uint8Array.from(atob(audioB64), (c) => c.charCodeAt(0));
      const blob  = new Blob([bytes], { type: "audio/wav" });
      const url   = URL.createObjectURL(blob);
      const audio = new Audio(url);
      playingAudioRef.current = audio;  // prevent GC

      let done = false;
      let safetyClock;
      const onDone = () => {
        if (done) return;
        done = true;

        clearTimeout(safetyClock);
        URL.revokeObjectURL(url);
        playingAudioRef.current = null;

        inVoiceModeRef.current = true;   //ADD THIS
        resumeListening();
      };
      safetyClock = setTimeout(onDone, 30_000); // hard fallback in case events never fire
      audio.onended = onDone;
      audio.onerror = onDone;
      audio.play().catch(onDone);
    } else {
      console.error("No TTS audio received");
      resumeListening();
    }
  }, [resumeListening]);

  const sendAudio = useCallback(async (blob) => {
    if (!inVoiceModeRef.current) {
    console.log("Ignored audio (voice mode off)");
    return;
  }
    const formData = new FormData();
    formData.append("audio", blob, "voice.webm");
    formData.append("session_id", String(sessionId));

    try {
      const res = await fetch(`${BACKEND_URL}/voice/transcribe-and-respond`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        console.error("Voice endpoint error:", res.status);
        resumeListening();
        return;
      }

      const data = await res.json();

      if (data?.transcript) {
        onUserTextRef.current?.(data.transcript);
      }

      if (data?.coach_message) {
        onCoachTextRef.current?.(data.coach_message);
        speakReply(data.coach_message, data.audio_b64 || null);
      } else {
        resumeListening();
      }
    } catch (err) {
      console.error("Voice send error:", err);
      resumeListening();
    }
  }, [sessionId, speakReply, resumeListening]);

  const stopCurrentRecording = useCallback(() => {
    if (!isRecordingRef.current) return;
    isRecordingRef.current = false;
    clearTimeout(silenceTimerRef.current);
    silenceTimerRef.current = null;
    mediaRecorderRef.current?.stop();
  }, []);

  // -- VAD loop --------------------------------------------------------------

  const startVAD = useCallback(() => {
    if (!inVoiceModeRef.current) return;
    // Chrome may suspend the AudioContext between interactions
    if (audioCtxRef.current?.state === "suspended") {
      audioCtxRef.current.resume().catch(() => {});
    }
    clearInterval(vadTimerRef.current);
    isRecordingRef.current = false;
    clearTimeout(silenceTimerRef.current);
    silenceTimerRef.current = null;

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    const createFreshRecorder = () => {
      const mr = new MediaRecorder(streamRef.current, { mimeType });
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        if (!inVoiceModeRef.current) return;
  const elapsed = Date.now() - (speechStartRef.current || 0);

  if (elapsed >= MIN_SPEECH_MS && chunksRef.current.length) {
    const blob = new Blob(chunksRef.current, { type: mimeType });

    clearInterval(vadTimerRef.current);

    // 🔥 IMPORTANT: recreate recorder AFTER sending
    sendAudio(blob).finally(() => {
      if (inVoiceModeRef.current) {
        mediaRecorderRef.current = createFreshRecorder();  // ✅ FIX
        resumeListening();
      }
    });

  } else {
    mediaRecorderRef.current = createFreshRecorder(); // ✅ FIX
    resumeListening();
  }
};
      return mr;
    };

    mediaRecorderRef.current = createFreshRecorder();

    vadTimerRef.current = setInterval(() => {
      if (!inVoiceModeRef.current) { clearInterval(vadTimerRef.current); return; }

      const rms = getRMS(analyserRef.current);

      if (!isRecordingRef.current && rms > SPEECH_THRESHOLD) {
        if (rms < 28) return; //ignore weak noise
        if (mediaRecorderRef.current?.state !== "inactive") return; // guard against race
        isRecordingRef.current = true;
        speechStartRef.current = Date.now();
        try { mediaRecorderRef.current.start(); }
        catch (e) { console.error("MediaRecorder.start failed:", e); isRecordingRef.current = false; }
      } else if (isRecordingRef.current) {
        if (rms < SILENCE_THRESHOLD) {
          if (!silenceTimerRef.current) {
            silenceTimerRef.current = setTimeout(() => {
              silenceTimerRef.current = null;
              stopCurrentRecording();
            }, SILENCE_DELAY_MS);
          }
        } else {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
      }
    }, VAD_INTERVAL_MS);
  }, [sendAudio, stopCurrentRecording, resumeListening]);

  useEffect(() => { startVADRef.current = startVAD; }, [startVAD]);

  // -- public API ------------------------------------------------------------

  const startVoice = useCallback(async () => {
    if (inVoiceModeRef.current) return;
    inVoiceModeRef.current = true;

    const stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const audioCtx = new AudioContext();
    audioCtxRef.current = audioCtx;
    const source   = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);
    analyserRef.current = analyser;

    startVAD();
  }, [startVAD]);

  const stopVoice = useCallback(() => {
    inVoiceModeRef.current = false;

    clearInterval(vadTimerRef.current);
    vadTimerRef.current = null;
    clearTimeout(silenceTimerRef.current);
    silenceTimerRef.current = null;

    if (isRecordingRef.current) {
      isRecordingRef.current = false;
      mediaRecorderRef.current?.stop();
    }
    mediaRecorderRef.current = null;

    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;

    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    analyserRef.current = null;

    window.speechSynthesis.cancel();
  }, []);

  useEffect(() => {
    return () => stopVoice();
  }, [stopVoice]);

  return { startVoice, stopVoice };
};
