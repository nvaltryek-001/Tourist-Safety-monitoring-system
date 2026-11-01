import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        ink: { 950: "#0b141a", 900: "#101c24", 800: "#18272f", 700: "#24363f", 600: "#3a4f59" },
        brand: { 50: "#eefaf7", 100: "#d2f1e9", 500: "#14917c", 600: "#0f766a", 700: "#0d5f56" },
        safe: "#15803d",
        caution: "#b45309",
        danger: "#c2410c",
        sos: "#b91c1c",
      },
      borderRadius: { DEFAULT: "6px", md: "6px", lg: "8px" },
    },
  },
  plugins: [],
};

export default config;
