export const ANALYSIS_LABELS = {
  density: "Densidade", counts: "Quantitativos", distribution: "Distribuição",
  comparisons: "Comparações", temporal: "Evolução temporal", aggregate: "Agregações",
  spatial: "Análise espacial", ranking: "Recortes e rankings",
  rotation: "Rotatividade", report: "Relatórios",
  nearest: "Referência mais próxima", criteria: "Critérios combinados",
} as const;
export type Operation = keyof typeof ANALYSIS_LABELS;
// Capacidades só do motor determinístico, fora do contrato do LLM e de default_scopes da base
// Brasil: existem apenas no recorte municipal, o único com coordenadas.
export const ENGINE_ONLY_SCOPES: Partial<Record<Operation, "national" | "municipal">> = { nearest: "municipal", criteria: "municipal" };
// Análises com resultado válido nas duas fontes da base Brasil. A fonte nacional tem um único
// território e nenhuma população: nas demais, só o recorte municipal é executável.
export const NATIONAL_SCOPE_OPERATIONS: Operation[] = ["counts", "temporal", "report"];
// Indicador das análises sem escolha entre quantidade e densidade, mostrado na caixa "Indicador" das configurações
// (uma opção, como a categoria): o mesmo que o motor calcula para cada análise.
const OWN_INDICATORS: Partial<Record<Operation, string>> = {
  density: "Densidade por 1.000 habitantes", counts: "Quantidade",
  aggregate: "Quantidade e densidade por 1.000 habitantes", ranking: "Densidade por 1.000 habitantes",
  spatial: "Distância geodésica (km)", rotation: "Permanência e rotatividade da coorte (%)",
  nearest: "Distância à referência mais próxima (km)",
};
/** Nos critérios combinados, o indicador são os atributos usados nas condições, na ordenação e nas faixas. */
export function ownIndicator(operation: Operation, criteriaAttributes: string[] = []): string {
  if (operation !== "criteria") return OWN_INDICATORS[operation] || "";
  if (!criteriaAttributes.length) return "Definido nos critérios";
  return criteriaAttributes.length === 1 ? criteriaAttributes[0]
    : criteriaAttributes.slice(0, -1).join(", ") + " e " + criteriaAttributes[criteriaAttributes.length - 1];
}
