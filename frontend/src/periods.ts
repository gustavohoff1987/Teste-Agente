const months = ["janeiro","fevereiro","março","abril","maio","junho","julho",
  "agosto","setembro","outubro","novembro","dezembro"];

export function readablePeriod(value: string): string {
  const match = /^(\d{4})(\d{2})$/.exec(value);
  if (match) {
    const month = Number(match[2]);
    if (month >= 1 && month <= 12) return months[month - 1] + " de " + match[1];
  }
  return value;
}

export const chronological = (values: string[]) => [...new Set(values)].sort((a, b) => a.localeCompare(b, "pt-BR", {numeric: true}));

/** Série anual: as competências AAAAMM de um mesmo mês (padrão: junho, o mês da população estimada da base Brasil),
 * em ordem cronológica. É uma seleção de competências existentes; nada é agregado. */
export const ANNUAL_MONTH = "06";
export function annualSeries(periods: string[], month = ANNUAL_MONTH): string[] {
  return chronological(periods).filter(period => /^\d{6}$/.test(period) && period.slice(4) === month);
}

/** A seleção é exatamente a série anual das competências disponíveis, e ela difere de "todas" (há outros meses). */
export function isAnnualSeries(selected: string[], periods: string[], month = ANNUAL_MONTH): boolean {
  const annual = annualSeries(periods, month), chosen = chronological(selected);
  return annual.length >= 2 && annual.length < chronological(periods).length && chosen.length === annual.length &&
    annual.every((period, index) => period === chosen[index]);
}

const monthName = (month: string) => months[Number(month) - 1] || month;

/** Resumo em ordem cronológica: período único, intervalo contínuo, série anual, até três competências fora de sequência
 * pelo nome ou intervalo com as lacunas nomeadas. */
export function describePeriods(values: string[], all: string[]): string {
  const chosen = chronological(values), universe = chronological(all);
  if (!chosen.length) return "nenhum período selecionado";
  if (chosen.length === 1) return readablePeriod(chosen[0]);
  const start = universe.indexOf(chosen[0]), end = universe.indexOf(chosen[chosen.length - 1]);
  const missing = start < 0 || end < 0 ? [] : universe.slice(start, end + 1).filter(item => !chosen.includes(item));
  const range = chosen.length + " competências, de " + readablePeriod(chosen[0]) + " a " + readablePeriod(chosen[chosen.length - 1]);
  if (chosen.length === universe.length) return "todas as " + range;
  if (isAnnualSeries(chosen, universe)) return "série anual de " + monthName(ANNUAL_MONTH) + ": " + range;
  if (!missing.length) return range;
  if (chosen.length <= 3) return chosen.slice(0, -1).map(readablePeriod).join(", ") + " e " + readablePeriod(chosen[chosen.length - 1]);
  return range + (missing.length <= 3 ? ", exceto " + missing.map(readablePeriod).join(", ")
    : " (" + missing.length + " competências do intervalo não incluídas)");
}

/** Competências de um resultado: até três por extenso; acima disso, quantidade e extremos (a lista completa
 * fica no título do elemento e nas exportações). */
export function compactPeriods(values: string[], format: (value: string) => string): string {
  const ordered = chronological(values);
  if (ordered.length <= 3) return ordered.map(format).join(", ");
  return ordered.length + " competências, de " + format(ordered[0]) + " a " + format(ordered[ordered.length - 1]);
}

/** Clique numa competência na escolha de vários períodos. Com todos os períodos incluídos por padrão
 * (nenhuma escolha feita ainda), o clique escolhe só a clicada; depois, cada clique inclui ou retira. */
export function clickPeriod(selected: string[], period: string, allByDefault: boolean): string[] {
  if (allByDefault) return [period];
  return selected.includes(period) ? selected.filter(item => item !== period) : [...selected, period];
}

/** Intervalo contínuo e inclusivo entre duas competências, na ordem cronológica das disponíveis. */
export function periodRange(all: string[], first: string, last: string): string[] {
  const periods = chronological(all);
  const [a, b] = [periods.indexOf(first), periods.indexOf(last)].sort((x, y) => x - y);
  return a < 0 ? [] : periods.slice(a, b + 1);
}

/** Coorte da rotatividade: competências inicial e final; sem escolha, valem a primeira e a última disponíveis. */
export function rotationPeriods(all: string[], initial: string, final: string): string {
  const periods = chronological(all);
  const first = initial || periods[0] || "", last = final || periods[periods.length - 1] || "";
  if (!first || !last) return "Escolher períodos";
  return first === last ? readablePeriod(first) : "de " + readablePeriod(first) + " a " + readablePeriod(last);
}

/** Comparação com janela (D6): competência dos valores. Com uma competência só, é ela; com a janela, a escolhida (se estiver
 * na janela) ou a última em ordem cronológica. Sem competência escolhida, vazia: a comparação segue o caminho anterior
 * (relações em cada competência). É uma seleção entre as competências escolhidas; nada é calculado. */
export function valuesPeriodOf(single: string, window: string[], chosen: string): string {
  if (single) return single;
  const ordered = chronological(window);
  if (!ordered.length) return "";
  return chosen && ordered.includes(chosen) ? chosen : ordered[ordered.length - 1];
}

/** Janela padrão da comparação: a série anual de junho (12 meses entre as competências, o mês da população do Brasil),
 * quando há ao menos duas competências de junho; sem ela, nenhuma janela padrão. */
export function comparisonWindow(periods: string[]): string[] {
  const annual = annualSeries(periods);
  return annual.length >= 2 ? annual : [];
}
