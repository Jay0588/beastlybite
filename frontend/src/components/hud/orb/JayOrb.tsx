"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useStore } from "@/store";

export default function JayOrb() {
  const { isStreaming, isSpeaking, isListening, isWakeWordActive, activeAgents } = useStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  const isActive = isStreaming || isSpeaking || isListening || activeAgents.length > 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    const W = canvas.width;
    const H = canvas.height;
    const cx = W / 2;
    const cy = H / 2;

    function draw(t: number) {
      ctx.clearRect(0, 0, W, H);

      // Outer glow rings
      for (let i = 3; i >= 1; i--) {
        const alpha = isActive ? 0.06 * i : 0.03 * i;
        const radius = 90 + i * 12 + (isActive ? Math.sin(t / 800 + i) * 4 : 0);
        const grad = ctx.createRadialGradient(cx, cy, radius - 4, cx, cy, radius + 4);
        grad.addColorStop(0, `rgba(0,212,255,0)`);
        grad.addColorStop(0.5, `rgba(0,212,255,${alpha})`);
        grad.addColorStop(1, `rgba(0,212,255,0)`);
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 8;
        ctx.stroke();
      }

      // Rotating arc segments (HUD rings)
      const numArcs = isActive ? 6 : 4;
      for (let i = 0; i < numArcs; i++) {
        const offset = (t / (1200 + i * 300)) * (i % 2 === 0 ? 1 : -1);
        const r = 72 + i * 3;
        const arcLen = (Math.PI * 2 * (0.3 + Math.random() * 0.2));
        ctx.beginPath();
        ctx.arc(cx, cy, r, offset, offset + arcLen);
        const brightness = isActive ? 0.6 + 0.4 * Math.sin(t / 500 + i) : 0.3;
        ctx.strokeStyle = `rgba(0,212,255,${brightness * 0.7})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Core sphere
      const coreR = 52;
      const coreGrad = ctx.createRadialGradient(cx - 10, cy - 10, 5, cx, cy, coreR);
      if (isListening) {
        coreGrad.addColorStop(0, "rgba(255,255,255,0.95)");
        coreGrad.addColorStop(0.3, "rgba(100,220,255,0.9)");
        coreGrad.addColorStop(1, "rgba(0,100,200,0.3)");
      } else if (isSpeaking) {
        coreGrad.addColorStop(0, "rgba(255,255,255,0.95)");
        coreGrad.addColorStop(0.3, "rgba(120,255,200,0.9)");
        coreGrad.addColorStop(1, "rgba(0,150,100,0.3)");
      } else if (isStreaming) {
        coreGrad.addColorStop(0, "rgba(255,255,255,0.9)");
        coreGrad.addColorStop(0.3, "rgba(180,140,255,0.85)");
        coreGrad.addColorStop(1, "rgba(80,0,200,0.3)");
      } else {
        coreGrad.addColorStop(0, "rgba(255,255,255,0.7)");
        coreGrad.addColorStop(0.3, "rgba(0,212,255,0.5)");
        coreGrad.addColorStop(1, "rgba(0,60,120,0.2)");
      }

      const pulse = isActive ? Math.sin(t / 400) * 3 : 0;
      ctx.beginPath();
      ctx.arc(cx, cy, coreR + pulse, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();

      // Inner shimmer
      ctx.beginPath();
      ctx.arc(cx - 14, cy - 14, 18, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255,255,255,0.12)";
      ctx.fill();

      // Particle ring
      if (isActive) {
        const particles = 20;
        for (let i = 0; i < particles; i++) {
          const angle = (i / particles) * Math.PI * 2 + t / 2000;
          const dist = 80 + Math.sin(t / 600 + i * 0.8) * 8;
          const px = cx + Math.cos(angle) * dist;
          const py = cy + Math.sin(angle) * dist;
          const size = 1.5 + Math.sin(t / 300 + i) * 1;
          ctx.beginPath();
          ctx.arc(px, py, size, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(0,212,255,${0.4 + Math.sin(t / 400 + i) * 0.3})`;
          ctx.fill();
        }
      }

      // Scanning line (when listening)
      if (isListening) {
        const scanAngle = (t / 1200) % (Math.PI * 2);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, 80, scanAngle - 0.3, scanAngle);
        ctx.closePath();
        const scanGrad = ctx.createLinearGradient(cx, cy,
          cx + Math.cos(scanAngle) * 80, cy + Math.sin(scanAngle) * 80);
        scanGrad.addColorStop(0, "rgba(0,212,255,0)");
        scanGrad.addColorStop(1, "rgba(0,212,255,0.6)");
        ctx.fillStyle = scanGrad;
        ctx.fill();
      }

      timeRef.current = t;
    }

    let start = 0;
    function animate(ts: number) {
      if (!start) start = ts;
      draw(ts - start);
      animRef.current = requestAnimationFrame(animate);
    }

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [isActive, isListening, isSpeaking, isStreaming]);

  const stateLabel = isListening ? "LISTENING"
    : isSpeaking ? "SPEAKING"
    : isStreaming ? "PROCESSING"
    : activeAgents.length > 0 ? `${activeAgents[0].toUpperCase()}`
    : "STANDBY";

  const stateColor = isListening ? "#00ff88"
    : isSpeaking ? "#00d4ff"
    : isStreaming ? "#a855f7"
    : "#0ea5e9";

  return (
    <div className="flex flex-col items-center gap-3 select-none">
      {/* Main orb */}
      <motion.div
        className="relative cursor-pointer"
        animate={{ scale: isActive ? [1, 1.02, 1] : 1 }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        {/* Outer glow */}
        <div
          className="absolute inset-0 rounded-full blur-xl opacity-30 transition-all duration-500"
          style={{
            background: `radial-gradient(circle, ${stateColor}88 0%, transparent 70%)`,
            transform: "scale(1.4)",
          }}
        />

        <canvas
          ref={canvasRef}
          width={200}
          height={200}
          className="relative z-10"
        />

        {/* State ring — expanding pulse */}
        {isActive && (
          <motion.div
            className="absolute inset-0 rounded-full border border-jay-accent/30"
            animate={{ scale: [1, 1.8], opacity: [0.6, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}
      </motion.div>

      {/* J.A.Y. Label */}
      <div className="flex flex-col items-center gap-1">
        <div className="font-display font-bold text-lg tracking-[0.25em] text-jay-text">
          J.A.Y.
        </div>
        <motion.div
          key={stateLabel}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-[10px] font-mono tracking-[0.3em] font-semibold"
          style={{ color: stateColor }}
        >
          {stateLabel}
        </motion.div>

        {/* Active agents */}
        {activeAgents.length > 0 && (
          <div className="flex gap-1 mt-1">
            {activeAgents.map((a) => (
              <span
                key={a}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-jay-accent/30 text-jay-accent bg-jay-accent/5"
              >
                {a}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
