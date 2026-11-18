// As fichas metodológicas em PDF (comando de ajustes pré-publicação, AJ-03, 18/11/2026): a Ficha A, do Detector de Sinais, e a
// Ficha B, do Simulador de Cenários. São documentos de leitura sobre o método e a técnica — como os resultados são produzidos —,
// gerados por scripts/gerar_fichas.py a partir das fontes em Docs/fichas/ e servidos com os arquivos estáticos da interface
// (frontend/public/fichas/). Não alteram nem substituem as "fichas de método" de backend/definicoes.py, usadas pela conversa.
// Os links respeitam a base da página (ADT_BASE_DA_PAGINA, pelo BASE_URL do build) e abrem numa nova aba; "Ver explicação
// completa" leva à seção certa, pelo destino nomeado do PDF (#nameddest=…, o id da seção na fonte). Sem importações em tempo de
// execução, para os testes Node lerem só este arquivo.

export type FerramentaDaFicha = "detector" | "simulador";

/** O arquivo de cada ficha, relativo à base da página. */
export const ARQUIVOS_DAS_FICHAS: Record<FerramentaDaFicha, string> = {
  detector: "fichas/ficha-detector.pdf",
  simulador: "fichas/ficha-simulador.pdf",
};

/** As seções de cada ficha que a página abre direto ("Ver explicação completa"): o id da seção na fonte, que vira o destino
 * nomeado do PDF. O teste das fichas confere que cada uma existe no PDF. */
export const SECOES_DAS_FICHAS = {
  detector: { ferramenta: "o-que-e", sinal: "sinais", alerta: "niveis", porQue: "sinais", ultimo: "dados" },
  simulador: { ferramenta: "o-que-e", forma: "forma-escolhida", faixa: "faixa" },
} as const;

/** O endereço de uma ficha (e, com a seção, do ponto dela), na base da página: "/fichas/ficha-detector.pdf#nameddest=niveis";
 * publicada em "/Teste-Agente/", "/Teste-Agente/fichas/…". */
export function linkDaFicha(base: string, ferramenta: FerramentaDaFicha, secao?: string): string {
  const raiz = !base ? "/" : base.endsWith("/") ? base : base + "/";
  return raiz + ARQUIVOS_DAS_FICHAS[ferramenta] + (secao ? "#nameddest=" + encodeURIComponent(secao) : "");
}
