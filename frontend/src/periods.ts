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

/** Resumo em ordem cronológica: período único, intervalo contínuo ou intervalo com as lacunas nomeadas. */
export function describePeriods(values: string[], all: string[]): string {
  const chosen = chronological(values), universe = chronological(all);
  if (!chosen.length) return "nenhum período selecionado";
  if (chosen.length === 1) return readablePeriod(chosen[0]);
  const start = universe.indexOf(chosen[0]), end = universe.indexOf(chosen[chosen.length - 1]);
  const missing = start < 0 || end < 0 ? [] : universe.slice(start, end + 1).filter(item => !chosen.includes(item));
  const range = chosen.length + " competências, de " + readablePeriod(chosen[0]) + " a " + readablePeriod(chosen[chosen.length - 1]);
  if (chosen.length === universe.length) return "todas as " + range;
  if (!missing.length) return range;
  return range + (missing.length <= 3 ? ", exceto " + missing.map(readablePeriod).join(", ")
    : " (" + missing.length + " competências do intervalo não incluídas)");
}

/** Intervalo contínuo e inclusivo entre duas competências, na ordem cronológica das disponíveis. */
export function periodRange(all: string[], first: string, last: string): string[] {
  const periods = chronological(all);
  const [a, b] = [periods.indexOf(first), periods.indexOf(last)].sort((x, y) => x - y);
  return a < 0 ? [] : periods.slice(a, b + 1);
}
