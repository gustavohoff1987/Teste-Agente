import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Caminho da página (01/11/2026): "/" no desenvolvimento e nos testes; no GitHub Pages, "/Teste-Agente/" (ADT_BASE_DA_PAGINA,
// definido pelo workflow pages.yml). O endereço do serviço de análise vem de VITE_API_BASE_URL, lido pela própria interface.
const ambiente = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const base = ambiente.ADT_BASE_DA_PAGINA || "/";
if (!/^\/(?:[A-Za-z0-9._-]+\/)*$/.test(base)) throw new Error("ADT_BASE_DA_PAGINA precisa começar e terminar com /: " + base);

export default defineConfig({
  base,
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } }
});
