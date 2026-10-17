// Identidade e coordenação de apresentação. Nunca produz relações, classes ou valores analíticos.
import type { ResultLike } from "./representation";

export type InvestigationEntry = { result: ResultLike; sourceKey: string; request: string; invalidReason: string };
type Bag = Record<string, unknown>;
const object = (value: unknown): Bag => value && typeof value === "object" && !Array.isArray(value) ? value as Bag : {};
const strings = (value: unknown): string[] => Array.isArray(value) ? value.map(String) : [];
const canonical = (value: unknown): string => JSON.stringify(normalize(value));
function normalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, normalize(v)]));
  return value ?? null;
}
const sameSet = (a: unknown, b: unknown) => canonical([...strings(a)].sort()) === canonical([...strings(b)].sort());

// O histórico resumido não precisa materializar os membros de cada universo.
export function resultSummary(entry: InvestigationEntry) {
  return {
    scope: String(object(entry.result.metadata.universe).classification_scope || "Recorte não informado"),
    status: entry.invalidReason ? "Invalidado" : String(object(entry.result.metadata.evaluability).status || "Situação não informada")
      .replaceAll("_", " ").toLocaleLowerCase("pt-BR"),
  };
}

export function identity(entry: InvestigationEntry) {
  const m = entry.result.metadata, source = object(m.source), universe = object(m.universe), options = object(m.options);
  const members = Array.isArray(universe.members) ? universe.members as Bag[] : [];
  const rep = object(m.representacao);
  const indicators = Array.isArray(rep.indicadores) ? rep.indicadores as Bag[] : [];
  return {
    operation: String(m.operation || "Operação não informada"),
    source: String(source.label || m.input_file || "Fonte não identificada"),
    version: String(source.version || m.data_sha256 || "Versão não informada"),
    periods: strings(m.periods), categories: strings(m.categories),
    indicators: indicators.map(i => String(i.rotulo) + (i.unidade ? " (" + i.unidade + ")" : "")),
    members: members.map(i => ({ id: String(i.id), label: String(i.label || i.name || i.id) })),
    ...resultSummary(entry),
    method: String(m.method_version || "Método não informado"),
    createdAt: typeof m.created_at === "string" ? m.created_at : "",
    options,
  };
}

/** Somente a identificação visual pode circular. Mesmo contexto não certifica comparabilidade.
 * Universo completo é exigido: interseções, harmonização e seleção por nomes semelhantes são vedadas.
 * Diferentes indicadores/operações permanecem dimensões separadas e explicitamente qualificadas.
 */
export function selectionCompatibility(a: InvestigationEntry, b: InvestigationEntry): { allowed: boolean; reasons: string[]; differences: string[] } {
  const x = a.result.metadata, y = b.result.metadata, left = identity(a), right = identity(b);
  const reasons: string[] = [], differences: string[] = [];
  if (a.invalidReason || b.invalidReason || x.validity !== "VALIDO" || y.validity !== "VALIDO") reasons.push("Validade não confirmada.");
  if (a.sourceKey !== b.sourceKey || !x.data_sha256 || x.data_sha256 !== y.data_sha256 || canonical(x.source) !== canonical(y.source)) reasons.push("Fonte ou versão da base diferente.");
  if (!x.method_version || x.method_version !== y.method_version) reasons.push("Versão do método diferente ou ausente.");
  if (!x.mapping || canonical(x.mapping) !== canonical(y.mapping)) reasons.push("Associação dos campos diferente ou ausente.");
  if (!left.periods.length || !sameSet(x.periods, y.periods)) reasons.push("Períodos diferentes ou não identificados.");
  if (!left.categories.length || !sameSet(x.categories, y.categories)) reasons.push("Categorias diferentes ou não identificadas.");
  const ids = left.members.map(i => i.id), otherIds = right.members.map(i => i.id);
  if (!ids.length || new Set(ids).size !== ids.length || new Set(otherIds).size !== otherIds.length || !sameSet(ids, otherIds)) reasons.push("Recortes territoriais diferentes ou sem identidade inequívoca.");
  for (const m of [x, y]) {
    const rep = object(m.representacao);
    if (rep.versao !== 1 || !object(rep.vinculo).coluna || ["aggregate", "rotation", "temporal"].includes(String(m.operation))) {
      reasons.push("Esta representação não permite coordenar territórios individuais nesta competência."); break;
    }
  }
  // Condições que mudam o significado das unidades, a resolução de dados ou a agregação.
  const baseKeys = ["count_unit", "custom_count_unit", "fts_scope_confirmed", "category_constant", "duplicate_policy",
    "rows_additive_confirmed", "no_overlap_confirmed", "population_additive_confirmed", "identity_union_confirmed",
    "identity_count_confirmed", "hierarchy_columns", "population_denominator_confirmed"];
  if (baseKeys.some(key => canonical(left.options[key]) !== canonical(right.options[key]))) reasons.push("Unidades, condições de agregação ou tratamento dos dados diferentes.");
  if (canonical(x.complemento_geografico) !== canonical(y.complemento_geografico) && x.complemento_geografico && y.complemento_geografico) reasons.push("Camadas geográficas diferentes.");
  if (x.operation !== y.operation) differences.push("Operações distintas");
  if (x.indicator !== y.indicator || canonical(left.indicators) !== canonical(right.indicators)) differences.push("Indicadores ou unidades de apresentação distintos");
  if (canonical(x.options) !== canonical(y.options)) differences.push("Parâmetros próprios de cada execução");
  return { allowed: !reasons.length, reasons, differences };
}

// Rótulos de parâmetros de uso corrente; o JSON existente mantém o contrato completo.
export const parameterLabels: Record<string, string> = {
  count_unit: "Unidade de contagem", custom_count_unit: "Unidade declarada", quantile_count: "Número de grupos",
  comparison_indicator: "Indicador da comparação", distribution_indicator: "Indicador da distribuição",
  temporal_indicator: "Indicador temporal", report_indicator: "Indicador do relatório", reference_territory: "Território de referência",
  crs: "Referencial geodésico", reference_mode: "Forma das referências", duplicate_policy: "Tratamento de duplicatas",
  no_overlap_confirmed: "Ausência de sobreposição confirmada", rows_additive_confirmed: "Soma de componentes confirmada",
  population_additive_confirmed: "População aditiva confirmada", comparison_confirmed: "Comparabilidade confirmada",
};
export function parameterValue(value: unknown): string {
  return value === true ? "Sim" : value === false ? "Não" : ({quantity: "Quantidade", density: "Densidade", list: "Lista explícita", criterion: "Critério"}[String(value)] || String(value));
}
