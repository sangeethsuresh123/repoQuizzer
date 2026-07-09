import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0D1117",
        elevated: "#161B22",
        border: "#30363D",
        ink: "#E6EDF3",
        dim: "#8B949E",
        accent: "#39D2C0",
        amber: "#E3B341",
        good: "#3FB950",
        goodBg: "#0F2A1B",
        bad: "#F85149",
        badBg: "#2D1214",
      },
      fontFamily: {
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
