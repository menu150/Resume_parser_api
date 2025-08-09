/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./styles/**/*.{css}",
  ],
  theme: {
    extend: {
      colors: {
        purple: { 700: "#6B21A8", 800: "#5B21B6" },
        gold:   { 400: "#FFD700", 500: "#E6BE00" },
      },
    },
  },
  plugins: [],
};
