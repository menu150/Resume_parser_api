/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}"
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
