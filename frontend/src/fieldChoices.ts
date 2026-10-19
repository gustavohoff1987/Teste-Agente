/** Opções dos seletores de campo (D1: só escolhas, nenhuma confirmação).
 *
 * Uma sugestão do backend (suggested_columns) aparece no topo, com "(sugerida)", mas nunca é selecionada em silêncio:
 * o seletor fica vazio ("Escolher campo") até o usuário escolher. Escolher a coluna estabelece o papel.
 */
export type FieldChoice = { value: string; label: string };

/** Valor da opção "A base tem um único período" no seletor de período (enviado como single_period_confirmed). */
export const SINGLE_PERIOD = "__periodo_unico__";
export const SINGLE_PERIOD_LABEL = "A base tem um único período";

export function fieldOptions(columns: string[], suggestions: Partial<Record<string, string[]>> | undefined, role: string,
  {optional = false, singlePeriod = false, current = ""}: {optional?: boolean; singlePeriod?: boolean; current?: string} = {}): FieldChoice[] {
  const suggested = (suggestions?.[role] || []).filter(column => columns.includes(column));
  const rest = columns.filter(column => !suggested.includes(column));
  const options: FieldChoice[] = [
    // Coluna escolhida (ou reconhecida) que não é sugestão continua listada na ordem da base.
    ...suggested.map(column => ({value: column, label: column === current ? column : column + " (sugerida)"})),
    ...rest.map(column => ({value: column, label: column})),
  ];
  if (role === "period" && singlePeriod) options.push({value: SINGLE_PERIOD, label: SINGLE_PERIOD_LABEL});
  if (optional) options.unshift({value: "", label: role === "territory_id" ? "Sem código" : "Não usar"});
  return options;
}

/** Valor mostrado no seletor de período: a coluna escolhida ou a opção de período único. */
export function periodValue(column: string | undefined, singlePeriod: boolean): string {
  return column || (singlePeriod ? SINGLE_PERIOD : "");
}
