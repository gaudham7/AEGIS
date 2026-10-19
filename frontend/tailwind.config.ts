import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f14",
        panel: "#121821",
        border: "#232c38",
        accent: "#3ba7ff",
        high: "#ef4444",
        medium: "#f59e0b",
        low: "#22c55e",
      },
    },
  },
  plugins: [],
};
export default config;
