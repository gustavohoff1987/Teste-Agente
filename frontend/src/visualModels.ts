// Modelos de desenho dos visuais por análise (D7, pacote visual V3 a V9). Só organizam e posicionam o que o motor entregou:
// valores, diferenças, relações, classes, variações, posições, percentuais e contagens vêm das linhas e dos metadados. Nada
// aqui soma, conta, classifica, ordena por valor ou compara níveis. Sem importações de outros módulos (testes em Node).

type Row = Record<string, unknown>;
type Bag = Record<string, unknown>;
export type LevelCode = "BR" | "UF" | "MUN";

export const LEVEL_OF_LABEL: Record<string, LevelCode> = {
  "Brasil (total nacional)": "BR", "Estado (soma dos municípios)": "UF", "Município": "MUN",
};
export const LEVEL_TITLES: Record<LevelCode, string> = {
  BR: "Brasil (total nacional)", UF: "Estados (soma dos municípios)", MUN: "Municípios",
};
const LEVEL_ORDER: LevelCode[] = ["BR", "UF", "MUN"];
const num = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null;
const text = (value: unknown): string => value === null || value === undefined ? "" : String(value);

// ------------------------------------------------------------------------------------------------ escalas de desenho
/** Intervalo do eixo de um gráfico de valores a partir do zero (barras, pontos, pirulitos): [min(0, menor), max(0, maior)].
 * Só enquadra o desenho. */
export function zeroExtent(values: (number | null)[]): [number, number] {
  let low = 0, high = 0;
  for (const value of values) if (value !== null && Number.isFinite(value)) { low = Math.min(low, value); high = Math.max(high, value); }
  return high > low ? [low, high] : [low, low + 1];
}

/** Intervalo do eixo entre o menor e o maior valor (halteres, pequenos múltiplos), com folga quando são iguais. */
export function valueExtent(values: (number | null)[]): [number, number] {
  const valid = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (!valid.length) return [0, 1];
  const low = Math.min(...valid), high = Math.max(...valid);
  if (high > low) return [low, high];
  const pad = Math.abs(low) * 0.1 || 1;
  return [low - pad, high + pad];
}

/** Posição (0 a 1) de um valor num intervalo do eixo; fora dele, presa às pontas. */
export function position(value: number, domain: [number, number]): number {
  const span = domain[1] - domain[0];
  if (!(span > 0)) return 0.5;
  return Math.min(1, Math.max(0, (value - domain[0]) / span));
}

// ------------------------------------------------------------------------------------------------ escala de cor do mapa
export type ColorScale = "logaritmica" | "linear";

/** Escala de cor do mapa: logarítmica (padrão) quando todos os valores são positivos; com zero ou negativos, só a linear é
 * definida. É mapeamento visual contínuo (RQ-REP-02): nenhuma classe, quebra ou quantil; o domínio continua [mínimo, máximo]. */
export function colorScaleFor(domain: [number, number] | null, chosen: ColorScale): ColorScale {
  return chosen === "logaritmica" && !!domain && domain[0] > 0 ? "logaritmica" : "linear";
}

/** Posição de cor (0 a 1) de um valor: linear, (v − mín) ÷ (máx − mín); logarítmica, ln(v ÷ mín) ÷ ln(máx ÷ mín). Domínio de um
 * valor só: meio da rampa. */
export function colorPosition(value: number, domain: [number, number], scale: ColorScale): number {
  const [low, high] = domain;
  if (!(high > low)) return 0.5;
  if (scale === "logaritmica" && low > 0 && value > 0) return Math.min(1, Math.max(0, Math.log(value / low) / Math.log(high / low)));
  return Math.min(1, Math.max(0, (value - low) / (high - low)));
}

/** Marcas de leitura da legenda na escala logarítmica: 1, 2 e 5 × 10ⁿ dentro do domínio, longe das pontas e umas das outras
 * (são marcas do eixo, não limites de classe). Na linear, só as pontas. */
export function scaleTicks(domain: [number, number], scale: ColorScale, minGap = 0.14, edgeGap = 0.08): { value: number; at: number }[] {
  if (scale !== "logaritmica" || !(domain[0] > 0) || !(domain[1] > domain[0])) return [];
  const out: { value: number; at: number }[] = [];
  for (let power = Math.floor(Math.log10(domain[0])); power <= Math.ceil(Math.log10(domain[1])); power++) {
    for (const factor of [1, 2, 5]) {
      const value = Number((factor * 10 ** power).toPrecision(12));
      if (value <= domain[0] || value >= domain[1]) continue;
      const at = colorPosition(value, domain, scale);
      if (at < edgeGap || at > 1 - edgeGap || (out.length && at - out[out.length - 1].at < minGap)) continue;
      out.push({ value, at });
    }
  }
  return out;
}

// ------------------------------------------------------------------------------------------------ comparação
export type WindowColumns = { start: string; end: string; initial: number | null; final: number | null; delta: number | null;
  direction: string; changeCondition: string; trend: string | null; trendMotive: string | null; observations: number | null };
export type ComparisonObject = { territory: string; category: string; level: LevelCode | null; quantity: number | null;
  population: number | null; density: number | null; value: number | null; condition: string; countType: string;
  coverage: string; window: WindowColumns | null };
export type ComparisonPair = { a: string; b: string; valueA: number | null; valueB: number | null; relation: string;
  difference: number | null; condition: string };
export type ComparisonGroup = { level: LevelCode | null; title: string; countType: string; relations: boolean;
  objects: ComparisonObject[]; pair: ComparisonPair | null };
export type ComparisonModel = { valuesPeriod: string | null; window: { start: string; end: string; count: number } | null;
  indicator: "density" | "quantity"; column: string; withChange: boolean; groups: ComparisonGroup[]; detailed: boolean };

function windowOf(row: Row): WindowColumns | null {
  if (!("Período inicial" in row)) return null;
  return { start: text(row["Período inicial"]), end: text(row["Período final"]), initial: num(row["Inicial"]), final: num(row["Final"]),
    delta: num(row["Variação absoluta"]), direction: text(row["Direção da mudança"]), changeCondition: text(row["Condição da mudança"]),
    trend: row["Tendência"] == null ? null : text(row["Tendência"]), trendMotive: row["Motivo da tendência"] == null ? null : text(row["Motivo da tendência"]),
    observations: num(row["Observações da tendência"]) };
}

/** Comparação por grupo de nível (Brasil, estados, municípios; sem níveis, um grupo só), na ordem do motor. Com `detail_rows`
 * (competência dos valores), um objeto por território com quantidade, população, densidade, mudança e tendência; sem eles,
 * os valores das relações. O par de cada grupo é a linha A/B do motor, com a relação e a diferença dele. */
export function comparisonModel(result: { rows: Row[]; detail_rows?: Row[]; metadata: Bag }): ComparisonModel {
  const meta = (result.metadata.comparacao || null) as Bag | null;
  const indicator = (meta?.indicador || result.metadata.indicator || (result.metadata.options as Bag | undefined)?.comparison_indicator) === "quantity"
    ? "quantity" : "density";
  const column = indicator === "density" ? "Densidade por 1.000" : "Quantidade";
  const levelOfRow = (row: Row): LevelCode | null => LEVEL_OF_LABEL[text(row["Nível"])] || null;
  const pairs = result.rows.filter(row => row["Objeto A"] != null && row["Objeto B"] != null);
  const groupsMeta = (Array.isArray(meta?.grupos) ? meta!.grupos : []) as Bag[];
  const relationsOf = (level: LevelCode | null) => {
    const found = groupsMeta.find(item => (item.nivel ?? null) === level);
    return found ? !!found.relacoes : level !== "BR";
  };
  const objects: ComparisonObject[] = [];
  const detailed = Array.isArray(result.detail_rows) && result.detail_rows.length > 0 && !!meta;
  if (detailed) {
    for (const row of result.detail_rows!) objects.push({ territory: text(row["Território"]), category: text(row["Categoria"]),
      level: levelOfRow(row), quantity: num(row["Quantidade"]), population: num(row["População"]), density: num(row["Densidade por 1.000"]),
      value: num(row[column]), condition: text(row["Condição"]), countType: text(row["Tipo de contagem"] ?? row["Unidade de contagem"]),
      coverage: text(row["Cobertura"]), window: windowOf(row) });
  } else if (new Set(result.rows.map(row => text(row["Período"]) + "|" + text(row["Categoria"]))).size <= 1) {
    // Sem competência dos valores, só um recorte (uma competência e uma categoria) vira painel; vários ficam na tabela.
    for (const row of result.rows) {
      const common = { category: text(row["Categoria"]), level: levelOfRow(row), quantity: null, population: null, density: null,
        countType: text(row["Unidade de contagem"]), coverage: "", window: null };
      if (row["Objeto A"] != null && row["Objeto B"] != null) {
        for (const side of ["A", "B"]) objects.push({ ...common, territory: text(row["Objeto " + side]), value: num(row["Valor " + side]),
          condition: text(row["Condição"]) });
      } else if (row["Território"] != null) objects.push({ ...common, territory: text(row["Território"]), value: num(row[column]),
        condition: text(row["Condição"]) });
    }
  }
  const groups: ComparisonGroup[] = [];
  const levels = [...new Set(objects.map(item => item.level))].sort((a, b) =>
    (a ? LEVEL_ORDER.indexOf(a) : -1) - (b ? LEVEL_ORDER.indexOf(b) : -1));
  for (const level of levels) {
    const members = objects.filter(item => item.level === level);
    const pairRow = pairs.find(row => levelOfRow(row) === level);
    groups.push({ level, title: level ? LEVEL_TITLES[level] : "Territórios comparados", countType: members[0]?.countType || "",
      relations: relationsOf(level) && members.length >= 2, objects: members,
      pair: pairRow ? { a: text(pairRow["Objeto A"]), b: text(pairRow["Objeto B"]), valueA: num(pairRow["Valor A"]), valueB: num(pairRow["Valor B"]),
        relation: text(pairRow["Relação A/B"]), difference: num(pairRow["Diferença A − B"]), condition: text(pairRow["Condição"]) } : null });
  }
  const window = meta?.janela as Bag | undefined;
  return { valuesPeriod: meta ? text(meta.competencia_valores) || null : null,
    window: window && num(window.competencias) !== null ? { start: text(window.inicio), end: text(window.fim), count: num(window.competencias)! } : null,
    indicator, column, withChange: !!meta?.mudanca_e_tendencia, groups, detailed };
}

export const RELATION_TEXT: Record<string, string> = { MAIOR: "maior que", MENOR: "menor que", IGUALDADE: "igual a", IGUAL: "igual a" };

// ------------------------------------------------------------------------------------------------ halteres e pequenos múltiplos
export type Dumbbell = { key: string; territory: string; category: string; level: LevelCode | null; start: string; end: string;
  initial: number | null; final: number | null; delta: number | null; direction: string; condition: string; trend: unknown;
  trendMotive: unknown; observations: number | null };

/** Halteres da evolução temporal: um por linha do motor (território e categoria), na ordem do resultado. */
export function temporalDumbbells(rows: Row[], category?: string): Dumbbell[] {
  return rows.filter(row => category === undefined || text(row["Categoria"]) === category).map((row, index) => ({
    key: text(row["Território"]) + "|" + text(row["Categoria"]) + "|" + index, territory: text(row["Território"]),
    category: text(row["Categoria"]), level: LEVEL_OF_LABEL[text(row["Nível"])] || null, start: text(row["Período inicial"]),
    end: text(row["Período final"]), initial: num(row["Inicial"]), final: num(row["Final"]), delta: num(row["Variação absoluta"]),
    direction: text(row["Direção da mudança"]), condition: text(row["Condição da mudança"]), trend: row["Tendência"],
    trendMotive: row["Motivo da tendência"], observations: num(row["Observações da tendência"]) }));
}

export type SmallMultiple = { territory: string; points: { period: string; value: number | null }[] };

/** Pequenos múltiplos: uma série por território (na ordem dos dados), todas nas mesmas competências e na mesma escala
 * (o intervalo de todas as séries mostradas em todas as páginas). Ausência fica como lacuna. */
export function smallMultiples(source: Row[], spec: { periodo: string; territorio: string; categoria: string; valor: string },
  territories: string[], category: string, page: number, perPage: number):
  { periods: string[]; items: SmallMultiple[]; domain: [number, number]; pages: number; page: number } {
  const rows = source.filter(row => text(row[spec.categoria]) === category && territories.includes(text(row[spec.territorio])));
  const periods = [...new Set(rows.map(row => text(row[spec.periodo])))].sort((a, b) => a.localeCompare(b, "pt-BR", { numeric: true }));
  const lookup = new Map(rows.map(row => [text(row[spec.territorio]) + "|" + text(row[spec.periodo]), num(row[spec.valor])]));
  const domain = valueExtent(rows.map(row => num(row[spec.valor])));
  const pages = Math.max(1, Math.ceil(territories.length / perPage)), current = Math.min(Math.max(0, page), pages - 1);
  const items = territories.slice(current * perPage, (current + 1) * perPage).map(territory => ({ territory,
    points: periods.map(period => ({ period, value: lookup.get(territory + "|" + period) ?? null })) }));
  return { periods, items, domain, pages, page: current };
}

/** Caminho de uma série no pequeno múltiplo: segmentos sem atravessar lacunas (desenho, sem interpolação). */
export function seriesSegments(points: { value: number | null }[], width: number, height: number, domain: [number, number], pad = 4):
  { segments: [number, number][][]; dots: [number, number][] } {
  const step = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0;
  const segments: [number, number][][] = [], dots: [number, number][] = [];
  let current: [number, number][] = [];
  points.forEach((point, index) => {
    if (point.value === null) { if (current.length) segments.push(current); current = []; return; }
    const xy: [number, number] = [pad + index * step, pad + (1 - position(point.value, domain)) * (height - pad * 2)];
    current.push(xy); dots.push(xy);
  });
  if (current.length) segments.push(current);
  return { segments, dots };
}

// ------------------------------------------------------------------------------------------------ listas longas
/** Janela de linhas montadas numa lista com rolagem (as demais continuam acessíveis rolando). */
export function visibleRange(scrollTop: number, rowHeight: number, total: number, size = 24): { start: number; end: number } {
  const start = Math.max(0, Math.min(Math.floor(scrollTop / rowHeight) - 2, Math.max(0, total - size)));
  return { start, end: Math.min(total, start + size) };
}

// ------------------------------------------------------------------------------------------------ texto dos valores
/** Texto do valor de cada item de uma lista na ordem dada (ex.: o pirulito do ranking): quando o arredondamento igualaria um
 * vizinho de valor diferente, as casas que os distinguem (RQ-REP-05, `pair`). Só apresentação: não reordena nem compara. */
export function neighborTexts(values: (number | null)[], format: (value: number) => string,
  pair: (a: number, b: number) => [string, string]): string[] {
  const texts = values.map(value => value === null ? "" : format(value));
  values.forEach((value, index) => {
    if (value === null) return;
    for (const other of [index - 1, index + 1]) {
      const near = values[other];
      if (near === null || near === undefined || near === value || format(near) !== format(value)) continue;
      const [mine] = pair(value, near);
      if (mine.length > texts[index].length) texts[index] = mine;
    }
  });
  return texts;
}

// ------------------------------------------------------------------------------------------------ distribuição
export type StripPoint = { territory: string; value: number; lane: number; group: string };

/** Faixa da distribuição: um ponto por território, na raia da classe do motor (ordem das classes do resumo), na posição do
 * seu valor. Classes e contagens não são criadas aqui; território sem valor fica fora da faixa (está na tabela). */
export function distributionStrip(summary: Row[], detail: Row[], column: string): { lanes: string[]; points: StripPoint[]; domain: [number, number] } {
  const lanes = summary.map(row => text(row["Quintil"] ?? row["Classe"]).split(" — ")[0]);
  const points: StripPoint[] = [];
  for (const row of detail) {
    const value = num(row[column]);
    const group = text(row["Quintil"]);
    const lane = lanes.indexOf(group);
    if (value === null || lane < 0) continue;
    points.push({ territory: text(row["Território"]), value, lane, group });
  }
  return { lanes, points, domain: valueExtent(points.map(point => point.value)) };
}

// ------------------------------------------------------------------------------------------------ rotatividade
export type CohortBar = { territory: string; category: string; start: string; end: string; cohort: number | null; stay: number | null;
  left: number | null; stayShare: number | null; leftShare: number | null; condition: string };

/** Barras da coorte: permanecem e saíram, com os percentuais do motor (% da coorte inicial); sem cálculo. */
export function cohortBars(rows: Row[]): CohortBar[] {
  return rows.map(row => ({ territory: text(row["Território"]), category: text(row["Categoria"]), start: text(row["Período inicial"]),
    end: text(row["Período final"]), cohort: num(row["Coorte inicial"]), stay: num(row["Permanecem"]), left: num(row["Saíram"]),
    stayShare: num(row["Permanência (%)"]), leftShare: num(row["Rotatividade (%)"]), condition: text(row["Condição"]) }));
}

// ------------------------------------------------------------------------------------------------ agregação
export type AggregateMember = { id: string; label: string; state: string };

/** Membros da agregação (universo do resultado) e expansões declaradas pelo motor (por exemplo, municípios de um estado). */
export function aggregateMembers(metadata: Bag): { members: AggregateMember[]; expansions: Bag[] } {
  const universe = (metadata.universe || {}) as Bag;
  const members = ((universe.members || []) as Bag[]).map(item => ({ id: text(item.id), label: text(item.label || item.name || item.id),
    state: text(item.state) }));
  const selection = (metadata.selecao_territorial || {}) as Bag;
  return { members, expansions: (Array.isArray(selection.expansoes) ? selection.expansoes : []) as Bag[] };
}
