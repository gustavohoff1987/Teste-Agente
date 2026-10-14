// Contrato de apresentação do backend (metadata.representacao) e transformações formais admitidas
// pela CFG-REP: vínculo por identificador, formatação e arredondamento de apresentação (RQ-REP-05),
// mapeamento visual contínuo e ordem neutra por código. Nada aqui calcula valores analíticos.

export type Row = Record<string, unknown>;
export type IndicatorKind = "CONTINUO" | "CONTAGEM" | "POSICAO" | "CLASSE" | "ESTADO";
export type Indicator = { coluna: string; rotulo: string; tipo: IndicatorKind; unidade?: string; origem?: string;
  classes?: string[]; nota?: string };
export type MissingPoint = { id: string; condicao: string; motivo?: string | null; texto?: string | null };
export type Geometry = {
  estado: "DISPONIVEL" | "INDISPONIVEL" | "NAO_APLICAVEL"; motivo?: string; pendencia?: string; desfecho?: string;
  competencia?: string | null; referencial?: string; fonte?: string; ids?: string[]; lat?: number[]; lon?: number[];
  complementados?: string[]; sem_geometria?: MissingPoint[];
  complemento_geografico?: { estado?: string; identificador?: string; versao?: string; sha256?: string; premissa?: string;
    proveniencia?: Record<string, unknown> } | null;
};
export type Series = { tabela: "rows" | "detail_rows"; periodo: string; territorio: string; categoria: string; valor: string;
  unidade: string; tipo: IndicatorKind };
export type Representation = { versao: number; tabela: "rows" | "detail_rows"; vinculo: { coluna: string; chave: "rotulo" | "codigo" | "nome" };
  indicadores: Indicator[]; serie: Series | null; geometria: Geometry; notas: string[] };
export type ResultLike = { result_id: string; title: string; rows: Row[]; detail_rows?: Row[]; metadata: Record<string, unknown> };
type Member = { id: string; name?: string; code?: string; label: string };

export function representationOf(result: ResultLike): Representation | null {
  const value = result.metadata.representacao as Representation | undefined;
  return value && value.versao === 1 && value.vinculo ? value : null;
}

export function tableOf(result: ResultLike, rep: Representation): Row[] {
  return (rep.tabela === "detail_rows" ? result.detail_rows : result.rows) || [];
}

/** Identificador estável de cada linha pela coluna e chave declaradas no contrato (código evita homônimos). */
export function rowLinker(result: ResultLike, rep: Representation): (row: Row) => string | null {
  const { coluna, chave } = rep.vinculo;
  if (chave === "rotulo") {
    const byLabel = new Map(membersOf(result).map(item => [item.label, item.id]));
    return row => byLabel.get(String(row[coluna] ?? "")) ?? null;
  }
  const prefix = chave === "codigo" ? "code:" : "name:";
  return row => row[coluna] === null || row[coluna] === undefined || row[coluna] === "" ? null : prefix + String(row[coluna]);
}

export function membersOf(result: ResultLike): Member[] {
  return ((result.metadata.universe as { members?: Member[] } | undefined)?.members) || [];
}

/** Rótulos por identificador: universo do resultado e referências declaradas nos metadados estruturados. */
export function labelIndex(result: ResultLike): Map<string, string> {
  const labels = new Map<string, string>();
  for (const item of membersOf(result)) labels.set(item.id, item.label);
  const nearest = result.metadata.nearest_reference as { conjunto_referencias?: { membros?: { id: string; territorio: string }[] } } | undefined;
  const criteria = result.metadata.criterios as { referencias?: { membros?: { id: string; territorio: string }[] } | null } | undefined;
  for (const item of [...(nearest?.conjunto_referencias?.membros || []), ...(criteria?.referencias?.membros || [])])
    if (!labels.has(item.id)) labels.set(item.id, item.territorio + (item.id.startsWith("code:") ? " [" + item.id.slice(5) + "]" : ""));
  return labels;
}

export const codeOf = (id: string) => id.startsWith("code:") ? id.slice(5) : "";

const decimal = (digits: number) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const integer = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/** RQ-REP-05: contínuas com duas casas (arredondamento convencional sobre o valor absoluto, sinal
 * preservado); contagens inteiras; valor não nulo nunca aparece como zero (casas aumentadas). */
export function formatNumber(value: number, kind: IndicatorKind | "CONTINUO" = "CONTINUO"): string {
  if (kind === "CONTAGEM" || kind === "POSICAO") return integer.format(value);
  let digits = 2;
  while (digits < 8 && value !== 0 && roundHalfUp(Math.abs(value), digits) === 0) digits += 1;
  return (value < 0 ? "−" : "") + decimal(digits).format(roundHalfUp(Math.abs(value), digits));
}

/** Casas suficientes para que valores exibidos juntos (ex.: mínimo e máximo da legenda) não pareçam iguais. */
export function formatPair(a: number, b: number, kind: IndicatorKind = "CONTINUO"): [string, string] {
  if (kind === "CONTAGEM" || kind === "POSICAO" || a === b) return [formatNumber(a, kind), formatNumber(b, kind)];
  for (let digits = 2; digits <= 8; digits++) {
    const fa = (a < 0 ? "−" : "") + decimal(digits).format(roundHalfUp(Math.abs(a), digits));
    const fb = (b < 0 ? "−" : "") + decimal(digits).format(roundHalfUp(Math.abs(b), digits));
    if (fa !== fb || digits === 8) return [fa, fb];
  }
  return [formatNumber(a, kind), formatNumber(b, kind)];
}

function roundHalfUp(value: number, digits: number): number {
  const factor = 10 ** digits;
  // Correção de representação binária (1,235 → 1,24) sem alterar valores exatos.
  return Math.round(value * factor + Number.EPSILON * factor * Math.max(1, value)) / factor;
}

export function formatValue(value: unknown, kind: IndicatorKind = "CONTINUO"): string {
  if (value === null || value === undefined || value === "") return "Não avaliável";
  return typeof value === "number" ? formatNumber(value, kind) : String(value);
}

export const fullPrecision = (value: unknown) => typeof value === "number" ? String(value).replace(".", ",") : "";

export const displayPeriod = (value: string | null | undefined): string => {
  if (!value) return "competência não declarada";
  if (/^\d{6}$/.test(value)) {
    const month = Number(value.slice(4));
    if (month >= 1 && month <= 12) return value.slice(4) + "/" + value.slice(0, 4);
  }
  return value;
};

// Paleta validada (skill de visualização): sequencial azul (passos 250→700), ordinal azul de cinco
// passos, categóricas nas três primeiras posições validadas para todos os pares (mapa).
export const SEQUENTIAL = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"];
export const ORDINAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"];
export const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
export const STATE_COLORS: Record<string, string> = {
  ATENDE: "#eb6834", NAO_ATENDE: "#2a78d6",
  "Conjunto completo de referências": "#2a78d6", "Entre as referências avaliáveis": "#eb6834",
};
export const NOT_EVALUABLE = "#898781";
export const INK = { primary: "#0b0b0b", secondary: "#52514e", muted: "#898781", grid: "#e1e0d9", surface: "#fcfcfb", faint: "#d9d8d1" };
export const STATE_LABELS: Record<string, string> = { ATENDE: "Atende", NAO_ATENDE: "Não atende", NAO_AVALIAVEL: "Não avaliável" };

function hexToRgb(hex: string): [number, number, number] {
  const value = parseInt(hex.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

/** Mapeamento visual contínuo (transformação formal; não é classificação): posição em [0, 1] ao longo da rampa. */
export function sequentialColor(t: number): string {
  const clamped = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0));
  const position = clamped * (SEQUENTIAL.length - 1);
  const index = Math.min(SEQUENTIAL.length - 2, Math.floor(position));
  const local = position - index;
  const [a, b] = [hexToRgb(SEQUENTIAL[index]), hexToRgb(SEQUENTIAL[index + 1])];
  const mix = a.map((channel, i) => Math.round(channel + (b[i] - channel) * local));
  return "#" + mix.map(channel => channel.toString(16).padStart(2, "0")).join("");
}
