// Tendência do motor (CAP-TEN-01, DA-15) e mudança (CAP-TMP-01) na apresentação. Nada aqui classifica,
// conta ou calcula: o código da classe vem de `metadata.tendencia.classes` (rótulo → código), as contagens
// vêm de `contagens`, `sem_classificacao_por_motivo`, `nao_avaliaveis_por_motivo` e `familias`, e as
// velocidades de `unidades[].velocidades`. As funções só traduzem e posicionam o que o motor entregou.

export type TrendFamily = "CRESCIMENTO" | "DECLINIO" | "NENHUMA" | "NAO_AVALIAVEL";
export type TrendClass = { codigo: string; rotulo: string; familia: Exclude<TrendFamily, "NAO_AVALIAVEL"> };
export type TrendWindow = { periodos: string[]; inicio: string; fim: string; intervalos: number[]; intervalo_constante: boolean;
  serie_anual: string | null; serie_anual_disponivel: boolean; competencias_serie_anual?: string[] };
export type TrendUnit = { territorio: string; categoria: string; velocidades: number[]; ausentes: string[] };
export type TrendMeta = {
  capacidade: string; versao_metodo: string; desfecho: "RES-VAL" | "RES-LIM" | "RES-SCL" | "BLQ-MET";
  bloqueio: { desfecho: string; motivo: string; periodos_distintos: number; texto: string; texto_minimo: string } | null;
  unidades_total: number; avaliaveis: number; nao_avaliaveis: number; indicador: string; unidade_valor: string | null; unidade_tempo: string;
  contagens: Record<string, number>; sem_classificacao_por_motivo: Record<string, number>;
  nao_avaliaveis_por_motivo: Record<string, number>; familias: Record<string, number>;
  classes: TrendClass[]; rotulos_familia: Record<string, string>; rotulos_nao_avaliavel: Record<string, string>;
  rotulos_motivo: Record<string, string>; janela: TrendWindow; unidades: TrendUnit[];
};

export const NOT_EVALUABLE_CLASS = "NAO_AVALIAVEL";

export function trendMeta(metadata: Record<string, unknown> | undefined): TrendMeta | null {
  const value = metadata?.tendencia as TrendMeta | undefined;
  return value && Array.isArray(value.classes) && value.contagens ? value : null;
}

/** Código da classe pelo rótulo da linha (rótulos do motor); rótulos de não avaliável viram NAO_AVALIAVEL. */
export function classOfLabel(label: unknown, meta: TrendMeta): string | null {
  if (typeof label !== "string" || !label) return null;
  const found = meta.classes.find(item => item.rotulo === label);
  if (found) return found.codigo;
  return Object.values(meta.rotulos_nao_avaliavel).includes(label) ? NOT_EVALUABLE_CLASS : null;
}

export function familyOfClass(code: string | null, meta: TrendMeta): TrendFamily | null {
  if (!code) return null;
  if (code === NOT_EVALUABLE_CLASS) return "NAO_AVALIAVEL";
  return meta.classes.find(item => item.codigo === code)?.familia ?? null;
}

/** Motivo de não avaliável pelo rótulo (SERIE_INSUFICIENTE ou INCOMPARABILIDADE). */
export function notEvaluableReason(label: unknown, meta: TrendMeta): string | null {
  const entry = Object.entries(meta.rotulos_nao_avaliavel).find(([, text]) => text === label);
  return entry ? entry[0] : null;
}

/** Texto da coluna "Motivo da tendência" na tabela. O motor só preenche o motivo de Sem classificação e de não avaliável;
 * com a classe atribuída, o campo vem vazio (null, vazio também no CSV): o motivo não se aplica, e a linha não é
 * "Não avaliável", o texto genérico da tabela para valor ausente. */
export function trendMotiveText(value: unknown): string {
  return value === null || value === undefined || value === "" ? "Não se aplica" : String(value);
}

export type CountEntry = { key: string; code: string; label: string; value: number; family: TrendFamily; motive?: string };
export type CountGroup = { family: TrendFamily; title: string; total: number; entries: CountEntry[] };

/** Grupos da contagem na ordem da SPEC (L415): família do crescimento, do declínio, sem classificação (por motivo)
 * e, à parte, os não avaliáveis por motivo (AT-18). Os números são os do motor, sem soma nesta camada. */
export function countGroups(meta: TrendMeta): CountGroup[] {
  const families: Exclude<TrendFamily, "NAO_AVALIAVEL">[] = ["CRESCIMENTO", "DECLINIO", "NENHUMA"];
  const groups: CountGroup[] = families.map(family => ({
    family, title: meta.rotulos_familia[family] || family, total: meta.familias[family] ?? 0,
    entries: meta.classes.filter(item => item.familia === family).flatMap((item): CountEntry[] => item.codigo === "SEM_CLASSIFICACAO"
      ? Object.entries(meta.sem_classificacao_por_motivo).map(([motive, value]) => ({ key: item.codigo + ":" + motive, code: item.codigo,
        label: item.rotulo + " (" + (meta.rotulos_motivo[motive] || motive).toLocaleLowerCase("pt-BR") + ")", value, family, motive }))
      : [{ key: item.codigo, code: item.codigo, label: item.rotulo, value: meta.contagens[item.codigo] ?? 0, family }]),
  }));
  const missing = Object.entries(meta.nao_avaliaveis_por_motivo).map(([motive, value]): CountEntry => ({
    key: NOT_EVALUABLE_CLASS + ":" + motive, code: NOT_EVALUABLE_CLASS, label: meta.rotulos_nao_avaliavel[motive] || motive, value,
    family: "NAO_AVALIAVEL", motive }));
  return [...groups, { family: "NAO_AVALIAVEL", title: "Não avaliáveis, listados à parte", total: meta.nao_avaliaveis, entries: missing }];
}

const count = (value: number | undefined) => (value ?? 0).toLocaleString("pt-BR");

/** Opções do filtro por família (L1776: o filtro por direção reúne as três classes da família), com os números do motor. */
export function familyFilterOptions(meta: TrendMeta): { key: TrendFamily; label: string }[] {
  return [
    { key: "CRESCIMENTO", label: (meta.rotulos_familia.CRESCIMENTO || "Família do crescimento") + " (" + count(meta.familias.CRESCIMENTO) + ")" },
    { key: "DECLINIO", label: (meta.rotulos_familia.DECLINIO || "Família do declínio") + " (" + count(meta.familias.DECLINIO) + ")" },
    { key: "NENHUMA", label: (meta.rotulos_familia.NENHUMA || "Sem classificação") + " (" + count(meta.familias.NENHUMA) + ")" },
    { key: "NAO_AVALIAVEL", label: "Não avaliável (" + count(meta.nao_avaliaveis) + ")" },
  ];
}

/** Aviso da etapa: bloqueio BLQ-MET com os textos do catálogo, ou RES-SCL (método executado, nenhuma classe). */
export function stageNote(meta: TrendMeta): string | null {
  if (meta.bloqueio) return meta.bloqueio.texto + " " + meta.bloqueio.texto_minimo +
    " A mudança entre o primeiro e o último período continua disponível.";
  if (meta.desfecho === "BLQ-MET") return "Nenhum território tem série avaliável para a tendência nesta seleção. " +
    "A mudança entre o primeiro e o último período continua disponível.";
  if (meta.desfecho === "RES-SCL") return "Método executado: nenhum território recebeu classe de tendência nesta série. " +
    "Sem classificação não é falta de dados.";
  return null;
}

/** Velocidades de um território (e categoria) entregues pelo motor, com as competências de cada intervalo. */
export function unitVelocities(meta: TrendMeta, territory: string, category?: string): { from: string; to: string; value: number }[] {
  const unit = meta.unidades.find(item => item.territorio === territory && (category === undefined || item.categoria === category));
  if (!unit || !unit.velocidades.length) return [];
  const observed = meta.janela.periodos.filter(period => !unit.ausentes.includes(period));
  return unit.velocidades.map((value, index) => ({ from: observed[index], to: observed[index + 1], value }));
}

export type VelocityBar = { x: number; y: number; width: number; height: number; sign: -1 | 0 | 1 };

/** Geometria das barras de velocidade a partir do zero (mapeamento visual, sem cálculo analítico): a escala é a maior
 * magnitude; velocidade zero vira um traço de 2 px na linha de base, diferente de ausência. */
export function velocityBars(values: number[], width: number, height: number, pad = 2): { baseline: number; bars: VelocityBar[] } {
  if (!values.length) return { baseline: height / 2, bars: [] };
  const max = Math.max(...values.map(Math.abs)) || 1;
  const positive = values.every(value => value >= 0), negative = values.every(value => value <= 0);
  const baseline = positive ? height - pad : negative ? pad : height / 2;
  const room = positive || negative ? height - pad * 2 : height / 2 - pad;
  const step = (width - pad * 2) / values.length, barWidth = Math.max(2, Math.min(18, step - 2));
  return { baseline, bars: values.map((value, index) => {
    const size = value === 0 ? 2 : Math.max(1, Math.abs(value) / max * room);
    const x = pad + index * step + (step - barWidth) / 2;
    const sign = value > 0 ? 1 : value < 0 ? -1 : 0;
    return { x, width: barWidth, sign, height: size, y: sign > 0 ? baseline - size : sign < 0 ? baseline : baseline - 1 };
  }) };
}
