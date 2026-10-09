/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        ink: "#0e2840",
        teal: "#0c8792",
        canvas: "#f5f8fb",
        line: "#dfebf0"
      },
      boxShadow: { card: "0 14px 45px rgba(9, 37, 60, 0.06)", lift: "0 24px 55px rgba(9,37,60,.12)" }
    }
  },
  plugins: []
};
