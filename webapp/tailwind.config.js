/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--c-bg)",
        surface: "var(--c-surface)",
        text: "var(--c-text)",
        hint: "var(--c-hint)",
        link: "var(--c-link)",
        accent: "var(--c-accent)",
        "accent-text": "var(--c-accent-text)",
        line: "var(--c-line)",
        danger: "var(--c-danger)",
        ok: "var(--c-ok)",
      },
    },
  },
  plugins: [],
};
