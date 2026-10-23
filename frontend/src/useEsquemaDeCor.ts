import { useSyncExternalStore } from "react";
import { flushSync } from "react-dom";
import { criarLojaDoEsquema, type EsquemaDeCor } from "./esquemaDeCor";

/** Uma loja só para a página: os ouvintes da janela ficam num lugar, e todos os desenhos trocam de paleta juntos. No começo da
 * impressão, o aviso passa pelo flushSync: o gráfico (SVG) e o mapa (canvas) são redesenhados no claro antes de a página ir
 * para a impressão. */
const loja = criarLojaDoEsquema(typeof window !== "undefined" ? window : null, acao => flushSync(acao));

/** O esquema em uso agora, fora do React (por exemplo, na camada da transição entre o gráfico e o mapa). */
export const esquemaAtual = (): EsquemaDeCor => loja.atual();

/** Esquema de cor do aparelho ("claro" ou "escuro"), acompanhado: o componente redesenha quando o aparelho troca de esquema e na
 * impressão (sempre clara). Sem janela, o claro. */
export function useEsquemaDeCor(): EsquemaDeCor {
  return useSyncExternalStore(loja.assinar, loja.atual, () => "claro");
}
