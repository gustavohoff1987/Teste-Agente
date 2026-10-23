/** Cores das classes por variáveis CSS (modo escuro, 23/10/2026): cada tom usado nas classes (bg-white, text-slate-600,
 * border-line, text-ink…) lê os canais RGB de uma variável --tom-*, definida em src/styles.css para o claro (:root) e para o
 * escuro (bloco "screen and (prefers-color-scheme: dark)"). Assim, as classes existentes mudam sozinhas com o esquema do aparelho,
 * e a impressão continua clara. Os valores do claro são os de antes (os do Tailwind e os da identidade). Só os tons usados nas
 * classes passam por variável: um tom novo precisa das duas definições em styles.css (o teste modoEscuro.test.mjs confere). */
const tom = nome => `rgb(var(--tom-${nome}) / <alpha-value>)`;
const tons = (familia, passos) => Object.fromEntries(passos.map(passo => [passo, tom(familia + "-" + passo)]));

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        white: tom("white"),
        ink: { DEFAULT: tom("ink"), realce: tom("ink-realce") },
        teal: tom("teal"),
        canvas: tom("canvas"),
        line: tom("line"),
        slate: tons("slate", [50, 100, 400, 500, 600, 700]),
        amber: tons("amber", [50, 200, 300, 800, 900]),
        rose: tons("rose", [50, 200, 600, 800]),
        blue: tons("blue", [50, 100, 200, 600, 700]),
        cyan: tons("cyan", [50, 100])
      },
      /** Borda sem cor na classe (a do preflight): o gray-200 do Tailwind no claro. */
      borderColor: { DEFAULT: "rgb(var(--tom-borda-padrao))" },
      boxShadow: { card: "0 14px 45px rgba(9, 37, 60, 0.06)", lift: "0 24px 55px rgba(9,37,60,.12)" }
    }
  },
  plugins: []
};
