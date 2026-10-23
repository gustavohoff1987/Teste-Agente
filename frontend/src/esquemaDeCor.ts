// Modo escuro (decisão do responsável pelo produto, 23/10/2026): a página segue o esquema de cor do aparelho, sem botão. A
// estrutura e os painéis trocam de cor pelas variáveis de styles.css; o gráfico (SVG) e o mapa (canvas) escolhem a paleta em
// JavaScript, pelo esquema que esta loja informa. A impressão é sempre clara: o escuro vale só na tela, a mesma condição das
// variáveis de styles.css, e, durante a impressão (beforeprint até afterprint), a loja informa o claro. Sem importações em tempo
// de execução (os testes em Node transpilam este arquivo sozinho): o React fica em useEsquemaDeCor.ts.

export type EsquemaDeCor = "claro" | "escuro";

/** Consulta do escuro: só na tela (na impressão, nunca), como o bloco escuro de styles.css. */
export const CONSULTA_ESCURO = "screen and (prefers-color-scheme: dark)";

/** O esquema que vale: escuro só com o aparelho no escuro e fora da impressão. */
export const esquemaDe = (escuroNaTela: boolean, imprimindo: boolean): EsquemaDeCor => escuroNaTela && !imprimindo ? "escuro" : "claro";

export type MidiaDoEsquema = {
  matches: boolean;
  addEventListener?: (tipo: "change", ouvinte: () => void) => void;
  removeEventListener?: (tipo: "change", ouvinte: () => void) => void;
};
export type JanelaDoEsquema = {
  matchMedia?: (consulta: string) => MidiaDoEsquema;
  addEventListener: (tipo: "beforeprint" | "afterprint", ouvinte: () => void) => void;
  removeEventListener: (tipo: "beforeprint" | "afterprint", ouvinte: () => void) => void;
};
export type LojaDoEsquema = { atual: () => EsquemaDeCor; assinar: (aviso: () => void) => () => void };

/** Loja do esquema de cor (para o useSyncExternalStore): `atual` lê a consulta do escuro; `assinar` avisa quando o aparelho
 * troca de esquema e quando a impressão começa ou termina. No começo da impressão, o aviso passa por `sincrono` (o flushSync do
 * React), para o gráfico e o mapa já irem claros para a página impressa. Os ouvintes da janela existem só enquanto houver quem
 * assine. Sem janela (fora do navegador), vale o claro. */
export function criarLojaDoEsquema(janela: JanelaDoEsquema | null, sincrono: (acao: () => void) => void = acao => acao()): LojaDoEsquema {
  const avisos = new Set<() => void>();
  let midia: MidiaDoEsquema | null = null;
  let imprimindo = false, ligada = false;
  const consulta = () => midia ?? (midia = typeof janela?.matchMedia === "function" ? janela.matchMedia(CONSULTA_ESCURO) : null);
  const avisar = () => { for (const aviso of [...avisos]) aviso(); };
  const mudou = () => avisar();
  const antes = () => { imprimindo = true; sincrono(avisar); };
  const depois = () => { imprimindo = false; avisar(); };
  return {
    atual: () => esquemaDe(!!consulta()?.matches, imprimindo),
    assinar(aviso) {
      avisos.add(aviso);
      if (!ligada && janela) {
        ligada = true;
        consulta()?.addEventListener?.("change", mudou);
        janela.addEventListener("beforeprint", antes);
        janela.addEventListener("afterprint", depois);
      }
      return () => {
        avisos.delete(aviso);
        if (avisos.size || !ligada || !janela) return;
        ligada = false;
        consulta()?.removeEventListener?.("change", mudou);
        janela.removeEventListener("beforeprint", antes);
        janela.removeEventListener("afterprint", depois);
      };
    },
  };
}
