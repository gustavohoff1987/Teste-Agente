export type WorkspaceStage = "territories" | "preparation" | "results";

/** Abre a etapa antes de localizar o alvo, inclusive quando ele ainda não foi montado. */
export function scrollAnalysisTo(id: string): boolean {
  const stage: WorkspaceStage | undefined = id === "preparacao-conversacional" ? "preparation"
    : id === "territorios" ? "preparation"
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

export function navigationCommand(message: string, current: WorkspaceStage, hasResult: boolean): WorkspaceStage | null {
  const value = normalizeCommand(message);
  const target = /^(?:(?:ver|mostrar|mostre|ir para|voltar para|volte para|voltar a|volte a) )?(?:a |os |as )?(?:territorios|municipios|selecao de territorios)$/.test(value) ? "territories"
    : /^(?:(?:ver|mostrar|mostre|ir para|voltar para|volte para|voltar a|volte a) )?(?:a |os |as )?(?:preparacao|parametros|configuracao)$/.test(value) ? "preparation"
    : /^(?:(?:ver|mostrar|mostre|ir para|voltar para|volte para) )?(?:os |o )?(?:resultados|resultado)$/.test(value) ? "results"
    : value === "voltar" ? current === "results" ? "preparation" : "territories"
    : /^(?:avancar|proxima etapa|continuar)$/.test(value) ? current === "territories" ? "preparation" : hasResult ? "results" : null : null;
  return target === "results" && !hasResult ? null : target === "territories" ? "preparation" : target;
}
