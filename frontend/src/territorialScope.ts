/** Valor da caixa "Abrangência territorial": total nacional, todos os municípios ou os municípios marcados. */
export function describeScope(national: boolean, names: string[]): string {
  if (national) return "Brasil (total nacional)";
  if (!names.length) return "Todos os municípios";
  if (names.length <= 2) return names.join(" e ");
  return names.length + " municípios: " + names.slice(0, 2).join(", ") + " e mais " + (names.length - 2);
}

/** No recorte nacional, só marcar municípios leva a análise ao recorte municipal; desmarcar altera apenas a seleção guardada. */
export function addsMunicipalities(next: string[], current: string[]): boolean {
  return next.some(id => !current.includes(id));
}
