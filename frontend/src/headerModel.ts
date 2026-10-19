// Cabeçalho do resultado (decisão D7, 19/10/2026): frase-resumo, indicadores (KPIs) e procedência entregues pelo motor em
// metadata.representacao.resumo. Nada aqui calcula: a frase é a do motor, montada pelas partes; cada número vem de um caminho
// do resultado e só é formatado para leitura (RQ-REP-05: milhar, sinal e competência como mês/ano). O minigráfico só
// seleciona e posiciona os pontos de uma lista do próprio resultado. Sem importações de outros módulos (testes em Node): as
// funções de formatação chegam como parâmetro.

export type Path = (string | number)[];
export type SummaryPart = { texto: string; segmento?: number; tipo?: string; caminho?: Path };
export type KpiSeries = { caminho: Path; periodo: string; valor: string };
export type Kpi = { rotulo: string; caminho?: Path; valor?: unknown; texto?: string; tipo: "CONTAGEM" | "CONTINUO"; unidade?: string;
  nivel?: string; papel?: string; serie?: KpiSeries };
export type ProvenanceItem = { rotulo: string; valor: string; caminho?: Path };
export type Summary = { versao: number; modelo: string; texto: string; partes: SummaryPart[]; indicadores: Kpi[];
  procedencia: ProvenanceItem[]; nota?: string };
export type Formatters = { number: (value: number, kind?: "CONTINUO" | "CONTAGEM") => string; period: (value: string) => string };
type Bag = Record<string, unknown>;

/** Resumo do motor (versão 1), ou null em resultados antigos: a tela mostra então a grade de métricas de antes. */
export function summaryOf(metadata: Bag | undefined): Summary | null {
  const representation = metadata?.representacao as Bag | undefined;
  const value = representation?.resumo as Summary | undefined;
  return value && value.versao === 1 && Array.isArray(value.partes) && Array.isArray(value.indicadores) ? value : null;
}

/** Valor de um caminho do resultado (o mesmo endereço verificado pelo motor); ausente → undefined. */
export function resolvePath(root: unknown, path: Path | undefined): unknown {
  if (!path) return undefined;
  let value: unknown = root;
  for (const key of path) {
    if (value === null || value === undefined || typeof value !== "object") return undefined;
    value = (value as Record<string | number, unknown>)[key];
  }
  return value;
}

const PERIOD_KEYS = new Set(["periods", "competencia_valores", "inicio", "fim", "competencia", "Período", "Período inicial",
  "Período final"]);
const isPeriodPath = (path: Path) => path.some(key => typeof key === "string" && PERIOD_KEYS.has(key));
const AAAAMM = /^(\d{4})(0[1-9]|1[0-2])$/;

/** Separador de milhar na parte inteira de um número já escrito pelo motor ("212583750,5" → "212.583.750,5") e sinal
 * tipográfico (−), sem mudar casas decimais (o motor já acrescentou as casas que distinguem valores próximos). */
export function groupDigits(text: string): string {
  const match = /^(-?)(\d+)(,\d+)?$/.exec(text);
  if (!match) return text;
  return (match[1] ? "−" : "") + match[2].replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (match[3] || "");
}

/** Texto de leitura de uma parte da frase. Parte sem caminho é o texto fixo do modelo; com caminho, é o valor do motor:
 * competência AAAAMM como mês/ano, inteiro com milhar, decimal com as casas escritas pelo motor; relação, como está. */
export function partText(part: SummaryPart, result: unknown, fmt: Formatters): string {
  if (!part.caminho || part.tipo === "RELACAO") return part.texto;
  const value = resolvePath(result, part.caminho);
  if (typeof value === "string" && AAAAMM.test(value) && isPeriodPath(part.caminho)) return fmt.period(value);
  if (typeof value === "number") {
    if (Number.isInteger(value) && !part.texto.includes(",")) return fmt.number(value, "CONTAGEM");
    return groupDigits(part.texto);
  }
  return part.texto;
}

/** Frase de leitura: as partes do motor, na ordem, com cada valor formatado; `valor` marca as partes com caminho. */
export function summaryParts(summary: Summary, result: unknown, fmt: Formatters): { text: string; value: boolean; kind?: string }[] {
  return summary.partes.map(part => ({ text: partText(part, result, fmt), value: !!part.caminho, kind: part.tipo }));
}

/** Competências AAAAMM escritas em rótulos do motor (por exemplo, "Brasil (total nacional) em 202406"), como mês/ano. */
export function periodsInText(text: string, fmt: Formatters): string {
  return text.replace(/\b(\d{4})(0[1-9]|1[0-2])\b/g, (whole) => fmt.period(whole));
}

export type SparkPoint = { period: string; value: number | null };
export type KpiView = { label: string; value: string; full: number | null; unit: string; level: string; context: boolean;
  period: string | null; spark: SparkPoint[] | null; kind: "CONTAGEM" | "CONTINUO" };

const chronological = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });

/** Pontos do minigráfico: a lista do resultado apontada pelo motor (`serie.caminho`), uma categoria só (a do próprio KPI ou a
 * única do resultado), em ordem cronológica; competência sem valor fica como lacuna (null). Sem duas competências, null. */
export function kpiSeries(kpi: Kpi, result: unknown): SparkPoint[] | null {
  if (!kpi.serie) return null;
  const list = resolvePath(result, kpi.serie.caminho);
  if (!Array.isArray(list)) return null;
  const items = list.filter((item): item is Bag => !!item && typeof item === "object");
  const categoryKey = items.some(item => "categoria" in item) ? "categoria" : items.some(item => "Categoria" in item) ? "Categoria" : "";
  let category: unknown = undefined;
  if (categoryKey) {
    const own = kpi.caminho && kpi.caminho.length >= 2 ? resolvePath(result, kpi.caminho.slice(0, -1)) as Bag | undefined : undefined;
    const categories = (resolvePath(result, ["metadata", "categories"]) as unknown[] | undefined) || [];
    category = own && typeof own === "object" && categoryKey in own ? own[categoryKey] : categories.length === 1 ? categories[0] : undefined;
    if (category === undefined && new Set(items.map(item => String(item[categoryKey]))).size > 1) return null;  // sem misturar categorias
  }
  const points = items.filter(item => !categoryKey || category === undefined || item[categoryKey] === category)
    .map(item => ({ period: String(item[kpi.serie!.periodo] ?? ""), value: typeof item[kpi.serie!.valor] === "number"
      ? item[kpi.serie!.valor] as number : null }))
    .filter(item => item.period)
    .sort((a, b) => chronological(a.period, b.period));
  return points.length >= 2 ? points : null;
}

/** Cartão de um KPI: o valor do motor (ou, sem valor único, o último ponto avaliável da série: seleção, não cálculo). */
export function kpiView(kpi: Kpi, result: unknown, fmt: Formatters): KpiView {
  const spark = kpiSeries(kpi, result);
  let full: number | null = typeof kpi.valor === "number" ? kpi.valor : null;
  let period: string | null = null;
  if (full === null && spark) {
    const last = [...spark].reverse().find(item => item.value !== null);
    if (last) { full = last.value; period = last.period; }
  }
  const value = full !== null ? fmt.number(full, kpi.tipo) : typeof kpi.texto === "string" && kpi.texto ? groupDigits(kpi.texto) : "Não avaliável";
  return { label: periodsInText(kpi.rotulo, fmt), value, full, unit: kpi.unidade || "", level: kpi.nivel || "",
    context: kpi.papel === "REFERENCIA_DE_CONTEXTO", period, spark, kind: kpi.tipo === "CONTAGEM" ? "CONTAGEM" : "CONTINUO" };
}

export type SparkGeometry = { segments: [number, number][][]; dots: { x: number; y: number; period: string; value: number }[];
  domain: [number, number] };

/** Geometria do minigráfico (desenho): x pela posição na lista, y entre o menor e o maior valor; lacunas quebram a linha
 * (nada é interpolado). Valores iguais ficam no meio da altura. */
export function sparkGeometry(points: SparkPoint[], width: number, height: number, pad = 3): SparkGeometry {
  const values = points.map(item => item.value).filter((value): value is number => value !== null);
  const low = values.length ? Math.min(...values) : 0, high = values.length ? Math.max(...values) : 1;
  const step = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0;
  const y = (value: number) => high > low ? pad + (1 - (value - low) / (high - low)) * (height - pad * 2) : height / 2;
  const segments: [number, number][][] = [];
  let current: [number, number][] = [];
  const dots: SparkGeometry["dots"] = [];
  points.forEach((item, index) => {
    const x = pad + index * step;
    if (item.value === null) { if (current.length) segments.push(current); current = []; return; }
    current.push([x, y(item.value)]);
    dots.push({ x, y: y(item.value), period: item.period, value: item.value });
  });
  if (current.length) segments.push(current);
  return { segments, dots, domain: [low, high] };
}
