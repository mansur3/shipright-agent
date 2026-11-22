import type { Config } from "tailwindcss";

/**
 * Tailwind CSS 4 theme tokens — mirrors the dark palette used across the app.
 *
 * NOTE: Tailwind v4 reads tokens from the `@theme` block in `src/app/globals.css`
 * at build time. This file is kept for tooling/editor IntelliSense and is also a
 * valid v3-style config (use `@config` to opt-in). The colour names below map
 * 1:1 to the CSS custom properties in globals.css.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx,js,jsx,mdx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0a0d14",
        panel: "#111520",
        raised: "#181d2b",
        line: "#1e2535",
        brand: "#2563eb",
        cyan: "#0ea5e9",
        ok: "#10b981",
        warn: "#f59e0b",
        danger: "#ef4444",
        ink: "#e2e8f0",
        ink2: "#94a3b8",
        ink3: "#475569",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 12px #2563eb44",
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "10px",
        lg: "14px",
      },
    },
  },
  plugins: [],
};

export default config;
