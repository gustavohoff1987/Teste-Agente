/** Base oficial: o cálculo só fica retido por escolhas da análise, nunca por definições ou confirmações sobre a base.
 * As escolhas que faltam são nomeadas pelos títulos das caixas das configurações, na ordem em que aparecem. */
export type Readiness = {
  category: string;
  /** Escolha de categoria ainda exigida (categoria pedida na conversa sem correspondência escolhida). */
  categoryChoiceRequired?: boolean;
  periodReady: boolean;
  territoryPending: boolean;
  /** Indicador escolhido pelo usuário, nas análises em que ele escolhe entre quantidade e densidade. */
  indicator: string;
  requiresIndicator: boolean;
  /** Análise espacial: território de referência. */
  reference?: string;
  requiresReference?: boolean;
  /** Fora da versão governada, as análises de distância pedem o referencial. */
  crs?: string;
  requiresCrs?: boolean;
};

export function missingChoices(r: Readiness): string[] {
  return [
    (!r.category || r.categoryChoiceRequired) && "Categoria",
    !r.periodReady && "Período",
    r.territoryPending && "Abrangência territorial",
    r.requiresIndicator && !r.indicator && "Indicador",
    r.requiresReference && !r.reference && "Território de referência",
    r.requiresCrs && !r.crs && "Referencial geodésico",
  ].filter((item): item is string => !!item);
}

/** "Falta escolher: Período." / "Falta escolher: Período e Indicador." / "Falta escolher: A, B e C." */
export function missingMessage(missing: string[]): string {
  if (!missing.length) return "";
  const list = missing.length === 1 ? missing[0] : missing.slice(0, -1).join(", ") + " e " + missing[missing.length - 1];
  return "Falta escolher: " + list + ".";
}
