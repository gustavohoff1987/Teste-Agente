export const ANALYSIS_LABELS = {
  density: "Densidade", counts: "Quantitativos", distribution: "Distribuição",
  comparisons: "Comparações", temporal: "Evolução temporal", aggregate: "Agregações",
  spatial: "Análise espacial", ranking: "Recortes e rankings",
  rotation: "Rotatividade", report: "Relatórios",
  nearest: "Referência mais próxima", criteria: "Critérios combinados",
} as const;
export type Operation = keyof typeof ANALYSIS_LABELS;
// Base Brasil oficial: o que cada análise aceita entre Brasil, estados e municípios vem do backend (bloco "niveis" da
// inspeção); a interface não decide a fonte nem troca de recorte ao trocar de análise.
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
