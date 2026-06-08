"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useStore } from "@/store";

export default function VoiceVisualizer({ height = 48 }: { height?: number }) {
  const { isListening, isSpeaking, voiceLevel, waveformData } = useStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const dataRef = useRef<number[]>(new Array(64).fill(0));

  const isActive = isListening || isSpeaking;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const W = canvas.width;
    const H = canvas.height;

    function draw(t: number) {
      ctx.clearRect(0, 0, W, H);

      const bars = 48;
      const barW = W / bars - 1;

      for (let i = 0; i < bars; i++) {
        const x = i * (barW + 1);

        let amp: number;
        if (isActive) {
          const base = waveformData[i % waveformData.length] || 0;
          amp = (base + Math.sin(t / 200 + i * 0.4) * 0.3 + Math.random() * 0.1) * (H * 0.8);
          amp = Math.max(2, Math.min(amp, H - 2));
        } else {
          amp = 2 + Math.sin(t / 2000 + i * 0.3) * 1.5;
        }

        const y = (H - amp) / 2;

        // Gradient bar
        const grad = ctx.createLinearGradient(x, H, x, 0);
        if (isListening) {
          grad.addColorStop(0, "rgba(0,255,136,0.2)");
          grad.addColorStop(0.5, "rgba(0,255,136,0.8)");
          grad.addColorStop(1, "rgba(0,212,255,0.9)");
        } else if (isSpeaking) {
          grad.addColorStop(0, "rgba(0,212,255,0.2)");
          grad.addColorStop(0.5, "rgba(0,212,255,0.8)");
          grad.addColorStop(1, "rgba(168,85,247,0.9)");
        } else {
          grad.addColorStop(0, "rgba(0,212,255,0.05)");
          grad.addColorStop(1, "rgba(0,212,255,0.15)");
        }

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, barW, amp);

        // Reflection
        const refGrad = ctx.createLinearGradient(x, H, x, H + amp * 0.3);
        refGrad.addColorStop(0, isActive ? "rgba(0,212,255,0.3)" : "rgba(0,212,255,0.05)");
        refGrad.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = refGrad;
        ctx.fillRect(x, H, barW, amp * 0.3);
      }

      // Center line
      ctx.beginPath();
      ctx.moveTo(0, H / 2);
      ctx.lineTo(W, H / 2);
      ctx.strokeStyle = "rgba(0,212,255,0.1)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    let start = 0;
    function animate(ts: number) {
      if (!start) start = ts;
      draw(ts - start);
      animRef.current = requestAnimationFrame(animate);
    }
    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [isActive, isListening, isSpeaking, waveformData]);

  return (
    <div className="w-full relative" style={{ height }}>
      <canvas
        ref={canvasRef}
        width={400}
        height={height}
        className="w-full h-full"
      />
      {/* Status overlay */}
      {isActive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5"
        >
          <motion.div
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
            className="w-2 h-2 rounded-full"
            style={{ background: isListening ? "#00ff88" : "#00d4ff" }}
          />
          <span className="text-[10px] font-mono" style={{ color: isListening ? "#00ff88" : "#00d4ff" }}>
            {isListening ? "LISTENING" : "SPEAKING"}
          </span>
        </motion.div>
      )}
    </div>
  );
}
