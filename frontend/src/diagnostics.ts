/** Organização de apresentação; nunca modifica ou combina resultados analíticos. */
export type Diagnostic = { id: number; resultIds: string[] };
export type Placement = "independent" | "append";

export function attachResult(groups: Diagnostic[], id: number, resultId: string): Diagnostic[] {
  const group = groups.find(item => item.id === id);
  if (!group) return [...groups, { id, resultIds: [resultId] }];
  if (group.resultIds.includes(resultId)) return groups;
  return groups.map(item => item.id === id ? {...item, resultIds: [...item.resultIds, resultId]} : item);
}

export function diagnosticLabel(group: Diagnostic): string {
  return group.resultIds.length > 1 ? `Diagnóstico ${group.id} · ${group.resultIds.length} componentes`
    : `Análise independente ${group.id}`;
}

/** Somente intenção explícita de apresentação, sem inferir operações ou parâmetros. */
export function presentationIntent(message: string): Placement | null {
  const text = message.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  // Perguntas conceituais e negações não autorizam mudar a organização do diagnóstico.
  if (/\b(?:nao|nunca)\b|^(?:o que|como|qual|explique|o significado)\b/.test(text.trim())) return null;
  const independent = /\b(?:analise independente|analise separada|novo diagnostico)\b/.test(text);
  const append = /\b(?:acrescent\w*|adicion\w*|inclu\w*|compo\w*)\b.*\bdiagnostico\b/.test(text);
  return independent === append ? null : independent ? "independent" : "append";
}

/** Separa comandos da interface; o restante continua sujeito à gramática analítica existente. */
export function analyticalRequest(message: string): string {
  const intent = presentationIntent(message);
  if (!intent) return message;
  if (intent === "independent") {
    return message.replace(/^(?:faça|faca|inicie|crie)\s+uma\s+an[áa]lise\s+(?:independente|separada)(?:\s+(?:de|da|do))?\s+/iu, "");
  }
  return message.replace(/^(?:acrescente|adicione|inclua)\s+ao\s+diagn[óo]stico(?:\s+atual)?\s+/iu, "")
    .replace(/\s+ao\s+diagn[óo]stico(?:\s+atual)?(?=[.!?]?$)/iu, "");
}
