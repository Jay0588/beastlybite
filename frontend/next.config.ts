import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false, // Needed for Tauri + WebSocket stability
  output: "export",       // Static export for Tauri
  trailingSlash: true,
  images: {
    unoptimized: true,    // Required for static export
  },
  // Allow external backend API calls
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL:  process.env.NEXT_PUBLIC_WS_URL  || "ws://localhost:8000/ws",
  },
};

export default nextConfig;
