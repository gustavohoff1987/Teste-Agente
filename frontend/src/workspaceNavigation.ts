export type WorkspaceStage = "preparation" | "results";
/** Destinos de navegação: "territories" abre a preparação com a seleção territorial expandida. */
export type NavigationTarget = WorkspaceStage | "territories";

/** Abre a etapa antes de localizar o alvo, inclusive quando ele ainda não foi montado. */
export function scrollAnalysisTo(id: string): boolean {
  const stage: NavigationTarget | undefined = id === "preparacao-conversacional" ? "preparation"
    : id === "territorios" ? "territories"
    : ["resultados", "selected-result-content"].includes(id) ? "results" : undefined;
  if (stage) window.dispatchEvent(new CustomEvent("adt:stage", {detail: stage}));
  requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({block: "start",
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"}));
  return !!stage || !!document.getElementById(id);
}

export function normalizeCommand(message: string): string {
  return message.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[.,!?]/g, " ").replace(/\s+/g, " ").trim();
}

/** Abas do resultado apresentado (Mapa, Gráficos, Tabela). */
export type ResultView = "mapa" | "graficos" | "tabela";
const VIEW_WORDS = new Map<string, ResultView>([["mapa", "mapa"], ["grafico", "graficos"], ["graficos", "graficos"], ["tabela", "tabela"]]);
// Palavras que acompanham o pedido sem mudar o sentido; qualquer outra (inclusive "não") deixa a mensagem para a
// interpretação, que também conhece esses pedidos.
const VIEW_FILLER = new Set(("me mostre mostra mostrar ver veja abra abre abrir exiba exibe exibir quero queria gostaria " +
  "pode poderia de do da no na em num numa um uma o a os as isso isto esse essa resultado resultados aba agora entao " +
  "tambem por favor la ai e pra para").split(" "));
const PREVIOUS_FILLER = new Set(("volta volte voltar retorna retorne retornar reabra reabre reabrir abra abre abrir mostra " +
  "mostre mostrar ver quero queria me de do da para pra pro ao a o as os no na por favor aquele aquela e agora").split(" "));

/** "Mostre no gráfico", "agora a tabela": a aba pedida, ou null quando a mensagem diz mais do que isso. */
export function viewCommand(message: string): ResultView | null {
  const words = normalizeCommand(message).split(" ").filter(Boolean);
  const views = words.filter(word => VIEW_WORDS.has(word));
  if (views.length !== 1 || words.some(word => !VIEW_WORDS.has(word) && !VIEW_FILLER.has(word))) return null;
  return VIEW_WORDS.get(views[0]) ?? null;
}

/** "Volte para o resultado anterior", "volta pra análise de antes": reabrir o resultado anterior, sem recalcular. */
export function previousResultCommand(message: string): boolean {
  const words = normalizeCommand(message).split(" ").filter(Boolean);
  const target = words.filter(word => ["resultado", "analise", "selecao", "recorte"].includes(word));
  const marker: string[] = words.filter(word => word === "anterior" || word === "antes");
  return target.length === 1 && marker.length === 1 &&
    words.every(word => target.includes(word) || marker.includes(word) || PREVIOUS_FILLER.has(word));
}

export function navigationCommand(message: string, current: WorkspaceStage, hasResult: boolean): NavigationTarget | null {
  const value = normalizeCommand(message);
  const target = /^(?:(?:ver|mostrar|mostre|ir para|voltar para|volte para|voltar a|volte a) )?(?:a |os |as )?(?:territorios|municipios|selecao de territorios)$/.test(value) ? "territories"
    : /^(?:(?:ver|mostrar|mostre|ir para|voltar para|volte para|voltar a|volte a) )?(?:a |os |as )?(?:preparacao|parametros|configuracao)$/.test(value) ? "preparation"
    : /^(?:(?:ver|mostrar|mostre|ir para|voltar para|volte para) )?(?:os |o )?(?:resultados|resultado)$/.test(value) ? "results"
    : value === "voltar" ? current === "results" ? "preparation" : "territories"
    : /^(?:avancar|proxima etapa|continuar)$/.test(value) ? hasResult ? "results" : null : null;
  return target === "results" && !hasResult ? null : target;
}
