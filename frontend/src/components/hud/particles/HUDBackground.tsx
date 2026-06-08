"use client";

import { useEffect, useRef } from "react";

export default function HUDBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    // Particles
    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.4 + 0.1,
      pulse: Math.random() * Math.PI * 2,
    }));

    // Data stream lines
    const streams = Array.from({ length: 8 }, () => ({
      x: Math.random() * window.innerWidth,
      y: -50,
      speed: Math.random() * 1.5 + 0.5,
      length: Math.random() * 80 + 40,
      alpha: Math.random() * 0.3 + 0.05,
      chars: Array.from({ length: 12 }, () =>
        String.fromCharCode(0x30A0 + Math.floor(Math.random() * 96))
      ),
      charTimer: 0,
    }));

    function draw(t: number) {
      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      // Grid
      ctx.strokeStyle = "rgba(0,212,255,0.03)";
      ctx.lineWidth = 1;
      const gridSize = 60;
      for (let x = 0; x < W; x += gridSize) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
      }
      for (let y = 0; y < H; y += gridSize) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      }

      // HUD corner decorations
      const corners = [
        { x: 0, y: 0, rx: 1, ry: 1 },
        { x: W, y: 0, rx: -1, ry: 1 },
        { x: 0, y: H, rx: 1, ry: -1 },
        { x: W, y: H, rx: -1, ry: -1 },
      ];
      ctx.strokeStyle = "rgba(0,212,255,0.2)";
      ctx.lineWidth = 1.5;
      corners.forEach(({ x, y, rx, ry }) => {
        ctx.beginPath();
        ctx.moveTo(x + rx * 40, y);
        ctx.lineTo(x, y);
        ctx.lineTo(x, y + ry * 40);
        ctx.stroke();
      });

      // Particles
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.pulse += 0.02;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;

        const a = p.alpha * (0.7 + 0.3 * Math.sin(p.pulse));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0,212,255,${a})`;
        ctx.fill();
      });

      // Data streams (matrix rain)
      ctx.font = "10px monospace";
      streams.forEach((s) => {
        s.y += s.speed;
        s.charTimer++;
        if (s.charTimer % 8 === 0) {
          s.chars.shift();
          s.chars.push(String.fromCharCode(0x30A0 + Math.floor(Math.random() * 96)));
        }
        if (s.y > H + s.length) {
          s.y = -s.length;
          s.x = Math.random() * W;
        }
        s.chars.forEach((c, i) => {
          const cy = s.y - i * 12;
          const fadeAlpha = (1 - i / s.chars.length) * s.alpha;
          ctx.fillStyle = `rgba(0,212,255,${fadeAlpha})`;
          ctx.fillText(c, s.x, cy);
        });
      });

      // Scan line
      const scanY = ((t / 6000) % 1) * H;
      const scanGrad = ctx.createLinearGradient(0, scanY - 60, 0, scanY + 2);
      scanGrad.addColorStop(0, "rgba(0,212,255,0)");
      scanGrad.addColorStop(1, "rgba(0,212,255,0.04)");
      ctx.fillStyle = scanGrad;
      ctx.fillRect(0, scanY - 60, W, 62);
      ctx.fillStyle = "rgba(0,212,255,0.06)";
      ctx.fillRect(0, scanY, W, 1);
    }

    let start = 0;
    function animate(ts: number) {
      if (!start) start = ts;
      draw(ts - start);
      animRef.current = requestAnimationFrame(animate);
    }
    animRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ opacity: 0.7 }}
    />
  );
}
