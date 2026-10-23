import type { AnimarTransicao, PosicaoNaTela, Posicoes, PosicoesDoGrafico } from "./mapaContrato";
import { LIMITE_TRANSICAO, MAPA_CORES, quadroDaTransicao, suavizar } from "./mapaModel";

// Transição entre o gráfico e o mapa (23/10/2026): as bolhas se deslocam do lugar no gráfico até o lugar de cada unidade no
// mapa (ou o contrário), numa camada de canvas por cima da área do desenho. É só estado visual: não pede nada ao motor nem
// muda valor (RQ-REP-06). Com movimento reduzido, ou com milhares de pontos, a troca é direta.

/** Posições das bolhas do gráfico na janela (centro e raio de getBoundingClientRect, cor do preenchimento), a partir do elemento
 * que contém o gráfico. Bolhas ocultas (fora da régua no modo leve, sem valor na vista inicial) ficam de fora. A bolha vazada
 * (não avaliável) leva a cor do anel tracejado. */
export const posicoesDoGrafico: PosicoesDoGrafico = raiz => {
  const saida: Posicoes = new Map();
  raiz.querySelectorAll<SVGElement>('[data-testid="analise-bolha"]').forEach(elemento => {
    const id = elemento.getAttribute("data-id");
    if (!id || saida.has(id) || elemento.getAttribute("data-visivel") === "false") return;
    const circulo = elemento.tagName.toLowerCase() === "circle" ? elemento : elemento.querySelector<SVGElement>("circle.analise-marca");
    if (!circulo) return;
    const caixa = circulo.getBoundingClientRect();
    if (!(caixa.width > 0 && caixa.height > 0)) return;
    const tracejada = circulo.hasAttribute("stroke-dasharray");
    const cor = (tracejada ? circulo.getAttribute("stroke") : circulo.getAttribute("fill")) || MAPA_CORES.neutro;
    const posicao: PosicaoNaTela = { x: caixa.left + caixa.width / 2, y: caixa.top + caixa.height / 2, r: caixa.width / 2, cor };
    saida.set(id, posicao);
  });
  return saida;
};

/** Prefere menos movimento? (preferência do sistema). */
export const movimentoReduzido = () => typeof window !== "undefined" && typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Anima, numa camada fixa por cima de `raiz`, cada id de `origem` até a mesma id em `destino`, com suavização, em cerca de
 * `duracaoMs`: os ids só da origem somem aos poucos e os só do destino aparecem. A camada cobre a área com a superfície (a vista
 * nova fica por baixo) e se desfaz no fim, revelando a vista nova no mesmo lugar dos pontos. Com movimento reduzido, sem
 * pontos, com mais de LIMITE_TRANSICAO pontos num dos lados ou com a área oculta, resolve na hora. Remove a camada ao terminar. */
export const animarTransicao: AnimarTransicao = (raiz, origem, destino, duracaoMs) => new Promise<void>(resolver => {
  if (movimentoReduzido() || !(duracaoMs > 0) || (!origem.size && !destino.size) ||
    origem.size > LIMITE_TRANSICAO || destino.size > LIMITE_TRANSICAO || typeof document === "undefined") { resolver(); return; }
  const caixa = raiz.getBoundingClientRect();
  if (!(caixa.width > 0 && caixa.height > 0)) { resolver(); return; }
  const largura = caixa.width, altura = caixa.height, dpr = Math.min(window.devicePixelRatio || 1, 2);
  const camada = document.createElement("canvas");
  camada.width = Math.round(largura * dpr); camada.height = Math.round(altura * dpr);
  camada.setAttribute("aria-hidden", "true");
  camada.setAttribute("data-testid", "transicao-vistas");
  Object.assign(camada.style, { position: "fixed", left: caixa.left + "px", top: caixa.top + "px", width: largura + "px", height: altura + "px",
    pointerEvents: "none", zIndex: "40" });
  const ctx = camada.getContext("2d");
  if (!ctx) { resolver(); return; }
  document.body.appendChild(camada);
  const inicio = performance.now();
  let encerrado = false, quadro = 0;
  const encerrar = () => {
    if (encerrado) return;
    encerrado = true;
    if (quadro) cancelAnimationFrame(quadro);
    camada.remove();
    resolver();
  };
  const passo = (agora: number) => {
    if (encerrado) return;
    const bruto = Math.min(1, Math.max(0, (agora - inicio) / duracaoMs));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, largura, altura);
    // A superfície cobre a vista nova durante o deslocamento e se desfaz no último quinto.
    ctx.globalAlpha = bruto < 0.8 ? 1 : Math.max(0, 1 - (bruto - 0.8) / 0.2);
    ctx.fillStyle = MAPA_CORES.superficie;
    ctx.fillRect(0, 0, largura, altura);
    // Pontos em lotes pela cor e pela opacidade, com o anel fino da superfície.
    const lotes = new Map<string, { cor: string; alfa: number; pontos: { x: number; y: number; r: number }[] }>();
    for (const ponto of quadroDaTransicao(origem, destino, suavizar(bruto))) {
      if (ponto.alfa <= 0.01) continue;
      const alfa = Math.round(ponto.alfa * 20) / 20, chave = ponto.cor + "|" + alfa;
      let lote = lotes.get(chave);
      if (!lote) { lote = { cor: ponto.cor, alfa, pontos: [] }; lotes.set(chave, lote); }
      lote.pontos.push({ x: ponto.x - caixa.left, y: ponto.y - caixa.top, r: ponto.r });
    }
    ctx.lineWidth = 1;
    ctx.strokeStyle = MAPA_CORES.superficie;
    for (const lote of lotes.values()) {
      ctx.globalAlpha = lote.alfa;
      ctx.fillStyle = lote.cor;
      ctx.beginPath();
      for (const p of lote.pontos) {
        if (p.x < -p.r || p.y < -p.r || p.x > largura + p.r || p.y > altura + p.r) continue;
        ctx.moveTo(p.x + p.r, p.y);
        ctx.arc(p.x, p.y, p.r, 0, 2 * Math.PI);
      }
      ctx.fill();
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    if (bruto >= 1) encerrar();
    else quadro = requestAnimationFrame(passo);
  };
  quadro = requestAnimationFrame(passo);
  // Sem quadros (aba oculta), o tempo-limite encerra e remove a camada.
  window.setTimeout(encerrar, duracaoMs + 600);
});
