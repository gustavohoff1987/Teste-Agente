import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Caminho da página (01/11/2026): "/" no desenvolvimento, nos testes e no GitHub Pages do destino (desde 04/11/2026); outro
// caminho só por ADT_BASE_DA_PAGINA, como no build do CI em "/Teste-Agente/" (a publicação antiga, retirada na D-3 em
// 07/11/2026). O endereço do serviço de análise vem de VITE_API_BASE_URL, lido pela própria interface.
const ambiente = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const base = ambiente.ADT_BASE_DA_PAGINA || "/";
if (!/^\/(?:[A-Za-z0-9._-]+\/)*$/.test(base)) throw new Error("ADT_BASE_DA_PAGINA precisa começar e terminar com /: " + base);

export default defineConfig({
  base,
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } }
});
