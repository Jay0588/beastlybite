import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // J.A.Y. HUD color palette
        jay: {
          bg:         "#050a14",
          surface:    "#0a1628",
          panel:      "#0d1f35",
          border:     "#1a3a5c",
          borderGlow: "#0ea5e9",
          accent:     "#00d4ff",
          accentDim:  "#0284c7",
          gold:       "#fbbf24",
          green:      "#22c55e",
          red:        "#ef4444",
          orange:     "#f97316",
          purple:     "#a855f7",
          text:       "#e2f0ff",
          textDim:    "#7ea8cc",
          textMuted:  "#3d6080",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "'Fira Code'", "monospace"],
        display: ["'Rajdhani'", "'Orbitron'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      animation: {
        "orb-pulse":   "orbPulse 3s ease-in-out infinite",
        "orb-rotate":  "orbRotate 8s linear infinite",
        "scan-line":   "scanLine 4s linear infinite",
        "grid-fade":   "gridFade 6s ease-in-out infinite",
        "flicker":     "flicker 8s linear infinite",
        "glow-pulse":  "glowPulse 2s ease-in-out infinite",
        "slide-in-right": "slideInRight 0.3s ease-out",
        "slide-in-left":  "slideInLeft 0.3s ease-out",
        "fade-up":     "fadeUp 0.4s ease-out",
        "data-stream": "dataStream 20s linear infinite",
        "border-glow": "borderGlow 2s ease-in-out infinite",
        "typing":      "typing 1.5s steps(3) infinite",
        "ring-expand": "ringExpand 2s ease-out infinite",
      },
      keyframes: {
        orbPulse: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.9" },
          "50%":      { transform: "scale(1.08)", opacity: "1" },
        },
        orbRotate: {
          "0%":   { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
        scanLine: {
          "0%":   { top: "-2px", opacity: "0" },
          "10%":  { opacity: "1" },
          "90%":  { opacity: "1" },
          "100%": { top: "100%", opacity: "0" },
        },
        gridFade: {
          "0%, 100%": { opacity: "0.03" },
          "50%":      { opacity: "0.06" },
        },
        flicker: {
          "0%, 95%, 100%":  { opacity: "1" },
          "96%, 98%": { opacity: "0.92" },
          "97%": { opacity: "0.85" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 10px #00d4ff33, 0 0 20px #00d4ff22" },
          "50%":      { boxShadow: "0 0 20px #00d4ff55, 0 0 40px #00d4ff33" },
        },
        slideInRight: {
          "0%":   { transform: "translateX(100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        slideInLeft: {
          "0%":   { transform: "translateX(-100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        fadeUp: {
          "0%":   { transform: "translateY(12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        dataStream: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        borderGlow: {
          "0%, 100%": { borderColor: "#0ea5e9" },
          "50%":      { borderColor: "#00d4ff" },
        },
        typing: {
          "0%": { content: "''" },
          "33%": { content: "'.'" },
          "66%": { content: "'..'" },
          "100%": { content: "'...'" },
        },
        ringExpand: {
          "0%":   { transform: "scale(1)", opacity: "0.8" },
          "100%": { transform: "scale(2)", opacity: "0" },
        },
      },
      backgroundImage: {
        "hud-grid": "linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px)",
        "panel-gradient": "linear-gradient(180deg, #0d1f35 0%, #050a14 100%)",
        "accent-gradient": "linear-gradient(135deg, #00d4ff 0%, #0284c7 100%)",
        "glow-radial": "radial-gradient(circle at center, #00d4ff22 0%, transparent 70%)",
      },
      backgroundSize: {
        "hud-grid": "40px 40px",
      },
      boxShadow: {
        "panel":  "0 0 0 1px #1a3a5c, 0 4px 24px #00000088",
        "accent": "0 0 20px #00d4ff44, 0 0 40px #00d4ff22",
        "glow-sm": "0 0 8px #00d4ff66",
        "glow":    "0 0 16px #00d4ff55, 0 0 32px #00d4ff33",
        "glow-lg": "0 0 24px #00d4ff77, 0 0 48px #00d4ff44",
        "inner-glow": "inset 0 0 30px #00d4ff11",
      },
    },
  },
  plugins: [],
};

export default config;
