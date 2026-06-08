"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Volume2, VolumeX, Radio } from "lucide-react";
import { useStore } from "@/store";
import { voiceAPI } from "@/lib/api";
import VoiceVisualizer from "@/components/hud/visualizer/VoiceVisualizer";
import JayOrb from "@/components/hud/orb/JayOrb";

export default function VoicePanel() {
  const {
    isListening, isSpeaking, isWakeWordActive, currentTranscript,
    setListening, setWakeWordActive, setSpeaking, setTranscript,
    setWaveformData,
  } = useStore();
  const [voiceStatus, setVoiceStatus] = useState<any>(null);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [audioCtx, setAudioCtx] = useState<AudioContext | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const [animFrame, setAnimFrame] = useState<number>(0);
  const [testText, setTestText] = useState("Hello, I am J.A.Y., your personal AI operating system. How can I assist you?");

  useEffect(() => {
    voiceAPI.getStatus().then(setVoiceStatus).catch(() => {});
  }, []);

  const startWakeWord = async () => {
    try {
      await voiceAPI.startWakeWord();
      setWakeWordActive(true);
    } catch (e) {
      console.error(e);
    }
  };

  const stopWakeWord = async () => {
    try {
      await voiceAPI.stopWakeWord();
      setWakeWordActive(false);
    } catch (e) {
      console.error(e);
    }
  };

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Set up audio analyser for waveform
      const ctx = new AudioContext();
      const src = ctx.createMediaStreamSource(stream);
      const asr = ctx.createAnalyser();
      asr.fftSize = 64;
      src.connect(asr);
      setAudioCtx(ctx);
      setAnalyser(asr);

      // Animate waveform
      const animate = () => {
        const data = new Uint8Array(asr.frequencyBinCount);
        asr.getByteFrequencyData(data);
        const normalized = Array.from(data).map((v) => v / 255);
        useStore.getState().setWaveformData(normalized);
        setAnimFrame(requestAnimationFrame(animate));
      };
      animate();

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      const chunks: BlobPart[] = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        cancelAnimationFrame(animFrame);
        stream.getTracks().forEach((t) => t.stop());
        ctx.close();
        setListening(false);
        setWaveformData(new Array(32).fill(0));

        const blob = new Blob(chunks, { type: "audio/webm" });
        const result = await voiceAPI.transcribe(blob);
        setTranscript(result.text || "");
      };

      recorder.start();
      setMediaRecorder(recorder);
      setListening(true);
    } catch (e: any) {
      console.error("Mic error:", e.message);
    }
  };

  const stopListening = () => {
    mediaRecorder?.stop();
  };

  const testTTS = async () => {
    setSpeaking(true);
    try {
      const resp = await voiceAPI.speak(testText, false);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => setSpeaking(false);
      audio.play();
    } catch (e) {
      setSpeaking(false);
    }
  };

  return (
    <div className="flex flex-col h-full items-center gap-8 py-8">
      {/* Main orb */}
      <JayOrb />

      {/* Voice visualizer */}
      <div className="w-full max-w-lg">
        <VoiceVisualizer height={64} />
      </div>

      {/* Transcript */}
      <AnimatePresence mode="wait">
        {currentTranscript && (
          <motion.div
            key={currentTranscript}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="max-w-lg w-full text-center px-4 py-3 bg-jay-surface/30 border border-jay-accent/20 rounded-xl"
          >
            <div className="text-[10px] font-mono text-jay-textDim mb-1 tracking-widest">TRANSCRIPT</div>
            <div className="text-sm text-jay-text">{currentTranscript}</div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Control buttons */}
      <div className="flex items-center gap-4">
        {/* Wake word */}
        <button
          onClick={isWakeWordActive ? stopWakeWord : startWakeWord}
          className={`flex flex-col items-center gap-2 p-5 rounded-2xl border transition-all ${
            isWakeWordActive
              ? "border-jay-accent/50 bg-jay-accent/10 text-jay-accent"
              : "border-jay-border/40 bg-jay-surface/20 text-jay-textDim hover:border-jay-border"
          }`}
        >
          <Radio size={22} />
          <span className="text-[10px] font-mono">{isWakeWordActive ? "WAKE WORD ON" : "WAKE WORD"}</span>
          {isWakeWordActive && (
            <span className="text-[9px] font-mono text-jay-textMuted">Say "Hey J.A.Y."</span>
          )}
        </button>

        {/* Listen */}
        <button
          onClick={isListening ? stopListening : startListening}
          className={`flex flex-col items-center gap-2 p-6 rounded-2xl border-2 transition-all ${
            isListening
              ? "border-jay-red/60 bg-jay-red/10 text-jay-red"
              : "border-jay-accent/40 bg-jay-accent/5 text-jay-accent hover:bg-jay-accent/10"
          }`}
        >
          <motion.div
            animate={isListening ? { scale: [1, 1.15, 1] } : {}}
            transition={{ duration: 0.8, repeat: Infinity }}
          >
            {isListening ? <MicOff size={28} /> : <Mic size={28} />}
          </motion.div>
          <span className="text-[11px] font-mono">{isListening ? "STOP" : "SPEAK"}</span>
        </button>

        {/* TTS test */}
        <button
          onClick={testTTS}
          disabled={isSpeaking}
          className={`flex flex-col items-center gap-2 p-5 rounded-2xl border transition-all ${
            isSpeaking
              ? "border-jay-green/50 bg-jay-green/10 text-jay-green"
              : "border-jay-border/40 bg-jay-surface/20 text-jay-textDim hover:border-jay-border"
          }`}
        >
          {isSpeaking ? <Volume2 size={22} /> : <VolumeX size={22} />}
          <span className="text-[10px] font-mono">{isSpeaking ? "SPEAKING" : "TEST TTS"}</span>
        </button>
      </div>

      {/* TTS test input */}
      <div className="w-full max-w-lg">
        <label className="text-[10px] font-mono text-jay-textDim mb-1 block">TTS TEST TEXT</label>
        <textarea
          value={testText}
          onChange={(e) => setTestText(e.target.value)}
          rows={2}
          className="w-full bg-jay-surface border border-jay-border/50 rounded-xl px-3 py-2 text-sm text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/50 resize-none"
        />
      </div>

      {/* Status info */}
      <div className="grid grid-cols-3 gap-3 w-full max-w-lg">
        {[
          { label: "Wake Word", value: isWakeWordActive ? "ACTIVE" : "INACTIVE", active: isWakeWordActive },
          { label: "Mic", value: isListening ? "LISTENING" : "IDLE", active: isListening },
          { label: "Speech", value: isSpeaking ? "SPEAKING" : "IDLE", active: isSpeaking },
        ].map(({ label, value, active }) => (
          <div key={label} className={`p-3 rounded-xl border text-center ${active ? "border-jay-accent/30 bg-jay-accent/5" : "border-jay-border/30"}`}>
            <div className="text-[9px] font-mono text-jay-textMuted mb-1">{label}</div>
            <div className={`text-xs font-mono ${active ? "text-jay-accent" : "text-jay-textDim"}`}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
