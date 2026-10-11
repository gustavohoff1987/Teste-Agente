export const ANALYSIS_LABELS = {
  density: "Densidade", counts: "Quantitativos", distribution: "Distribuição",
  comparisons: "Comparações", temporal: "Evolução temporal", aggregate: "Agregações",
  spatial: "Análise espacial", ranking: "Recortes e rankings",
  rotation: "Rotatividade", report: "Relatórios",
} as const;
export type Operation = keyof typeof ANALYSIS_LABELS;
