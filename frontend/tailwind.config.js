/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'IBM Plex Mono'", "monospace"],
        sans: ["'DM Sans'", "sans-serif"],
      },
      colors: {
        ink: "#0f0f0f",
        paper: "#f5f0e8",
        tab: "#1a1a2e",
        accent: "#e8a020",
        muted: "#8a8070",
        danger: "#c0392b",
      },
    },
  },
  plugins: [],
};
