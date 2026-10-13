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
