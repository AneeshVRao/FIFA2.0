/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkbg: "#050505",
        panelbg: "rgba(10, 12, 22, 0.7)",
        fifagold: "hsl(45, 100%, 50%)",
        fifagreen: "hsl(140, 100%, 50%)",
        borderglow: "rgba(255, 255, 255, 0.08)",
        cardbg: "rgba(13, 16, 31, 0.6)",
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "sans-serif"],
        display: ["Satoshi", "sans-serif"],
        mono: ["Geist Mono", "monospace"],
      },
    },
  },
  plugins: [],
}
