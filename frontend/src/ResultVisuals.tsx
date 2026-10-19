import { useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { CATEGORICAL, INK, NOT_EVALUABLE, ORDINAL, displayPeriod, formatNumber, formatPair, fullPrecision, type IndicatorKind,
  type Row } from "./representation";
import { TrendBadge } from "./TrendVisuals";
import { useNarrow } from "./useNarrow";
import type { TrendMeta } from "./trend";
import {
  LEVEL_TITLES, RELATION_TEXT, aggregateMembers, cohortBars, colorPosition, colorScaleFor, comparisonModel, distributionStrip,
  neighborTexts, position, scaleTicks, seriesSegments, smallMultiples, visibleRange, zeroExtent, type ComparisonGroup, type ComparisonObject,
  type Dumbbell, type LevelCode,
} from "./visualModels";

// Visuais próprios de cada análise (D7; pacote visual V3 a V9). Desenham só valores do motor: nenhuma soma, média, contagem,
// classe, diferença ou percentual é produzida aqui. Paleta neutra (sem verde = bom nem vermelho = ruim); "não avaliável"
// sempre em texto e em cinza, nunca como zero.

const signed = (value: number, kind: IndicatorKind = "CONTINUO") => (value > 0 ? "+" : "") + formatNumber(value, kind);
const DENSITY_UNIT = "por 1.000 habitantes";
// Textura da soma dos componentes (estados): listras a 45°, sempre com o rótulo "possível dupla contagem" (RQ-REP-14).
export const UF_TEXTURE = "repeating-linear-gradient(45deg, rgba(42,120,214,0.55) 0 3px, rgba(42,120,214,0.15) 3px 6px)";
export const UF_WARNING = "possível dupla contagem · não comparável com a contagem nacional";

/** Largura do contêiner em pixels, para desenhar SVG sem esticar o texto. */
function useWidth(ready: boolean, initial = 600): [RefObject<HTMLDivElement>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(initial);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const measure = () => { if (element.clientWidth > 0) setWidth(element.clientWidth); };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ready]);
  return [ref, width];
}

function LevelTag({ level }: { level: LevelCode | null }) {
  if (!level) return null;
  return <span data-testid="level-tag" data-level={level} className={"inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold " +
    (level === "UF" ? "border-blue-300 text-blue-900" : level === "BR" ? "border-slate-500 text-ink" : "border-line text-slate-700")}
    style={level === "UF" ? { backgroundImage: "repeating-linear-gradient(45deg, #eaf2fc 0 3px, #ffffff 3px 6px)" } : undefined}>
    {LEVEL_TITLES[level]}</span>;
}

/** Aviso fixo do nível estadual (soma dos municípios). */
export function StateWarning() {
  return <p data-testid="uf-warning" className="text-xs text-blue-900">Soma dos municípios: {UF_WARNING}.</p>;
}

// ------------------------------------------------------------------------------------------------ comparação
type ComparisonProps = { result: { rows: Row[]; detail_rows?: Row[]; metadata: Record<string, unknown> }; trend: TrendMeta | null;
  unit: string };

/** Comparação (V3): valores lado a lado por nível na competência dos valores, com a relação e a diferença do motor no par;
 * com janela, halteres do inicial ao final, com a variação e a classe de tendência do motor. */
export function ComparisonPanel({ result, trend, unit }: ComparisonProps) {
  const model = useMemo(() => comparisonModel(result), [result]);
  if (!model.groups.length) return null;
  const kind: IndicatorKind = model.indicator === "density" ? "CONTINUO" : "CONTAGEM";
  const valueUnit = model.indicator === "density" ? DENSITY_UNIT : unit;
  const period = model.valuesPeriod ? displayPeriod(model.valuesPeriod) : "";
  return <section aria-label="Comparação lado a lado" data-testid="comparison-panel" className="mt-6 space-y-4">
    {model.valuesPeriod && <p data-testid="comparison-values-caption" className="text-xs text-slate-700">Competência dos valores:{" "}
      <strong className="text-ink">{period}</strong>{model.window && model.window.count > 1 ? <> · janela de {displayPeriod(model.window.start)} a{" "}
      {displayPeriod(model.window.end)} ({model.window.count} competências): mudança e tendência de cada território</> : null}.
      {" "}Relações (maior, menor, diferença) só dentro do mesmo nível.</p>}
    <figure data-testid="comparison-side-by-side" aria-label={"Valores lado a lado" + (period ? " em " + period : "")}
      className="space-y-4 rounded-2xl border border-line bg-white p-4">
      {model.groups.map(group => <SideBySideGroup key={group.level || "todos"} group={group} kind={kind} unit={valueUnit}
        density={model.indicator === "density"} trend={trend} withChange={model.withChange} showValues={model.detailed}/>)}
      <figcaption className="text-xs leading-5 text-slate-600">Valores do motor{period ? " em " + period : ""}, cada nível no seu
        bloco e no seu eixo, a partir do zero; o Brasil fica lado a lado, sem relação. Sem razão nem diferença percentual automáticas.</figcaption>
    </figure>
    {model.withChange && <figure data-testid="comparison-dumbbell" aria-label="Mudança na janela por território"
      className="space-y-4 rounded-2xl border border-line bg-white p-4">
      <h4 className="text-sm font-bold text-ink">Do primeiro ao último período da janela{model.window ? " (" + displayPeriod(model.window.start) +
        " → " + displayPeriod(model.window.end) + ")" : ""}</h4>
      {model.groups.map(group => <div key={group.level || "todos"} data-testid={"comparison-dumbbell-group-" + (group.level || "todos").toLowerCase()}>
        <p className="mb-1 flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-700"><LevelTag level={group.level}/>
          {!group.level && group.title}</p>
        <DumbbellList items={group.objects.map((item, index) => ({ key: item.territory + "|" + index, territory: item.territory,
          category: item.category, level: item.level, start: item.window?.start || "", end: item.window?.end || "", initial: item.window?.initial ?? null,
          final: item.window?.final ?? null, delta: item.window?.delta ?? null, direction: item.window?.direction || "",
          condition: item.window?.changeCondition || "", trend: item.window?.trend, trendMotive: item.window?.trendMotive,
          observations: item.window?.observations ?? null }))} kind={kind} unit={valueUnit} trend={trend} title={group.title}/>
      </div>)}
      <figcaption className="text-xs leading-5 text-slate-600">Círculo vazado: primeiro período; cheio: último. A variação entre
        parênteses é a do motor (CAP-TMP-01). Classes de tendência lado a lado: entre territórios, só se lê se a classe é a mesma;
        as classes não têm ordem entre si.</figcaption>
    </figure>}
  </section>;
}

function SideBySideGroup({ group, kind, unit, trend, withChange, showValues, density }: { group: ComparisonGroup; kind: IndicatorKind;
  unit: string; density: boolean; trend: TrendMeta | null; withChange: boolean; showValues: boolean }) {
  const domain = zeroExtent(group.objects.map(item => item.value));
  const narrow = useNarrow();
  const pair = group.pair;
  const [left, right] = pair && pair.valueA !== null && pair.valueB !== null ? formatPair(pair.valueA, pair.valueB, kind) : ["", ""];
  const shown = (item: ComparisonObject) => pair && item.territory === pair.a && left ? left : pair && item.territory === pair.b && right
    ? right : item.value === null ? "Não avaliável" : formatNumber(item.value, kind);
  return <div data-testid={"comparison-group-" + (group.level || "todos").toLowerCase()} className="space-y-2">
    <div className="flex flex-wrap items-center gap-2 text-xs">
      {group.level ? <LevelTag level={group.level}/> : <span className="font-semibold text-slate-700">{group.title}</span>}
      {group.countType && <span className="text-slate-600">{group.countType}</span>}
    </div>
    {group.level === "UF" && <StateWarning/>}
    {group.level === "BR" && <p className="text-xs text-slate-600">Lado a lado, sem relação: o Brasil é outro nível e não entra em
      maior, menor nem diferença com estados ou municípios.</p>}
    {showValues && group.objects.length <= 6 && <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {group.objects.map(item => <div key={item.territory} data-testid="comparison-object" data-territory={item.territory}
        className="min-w-0 rounded-xl border border-line bg-slate-50 p-3 text-xs">
        <p className="truncate font-semibold text-ink" title={item.territory}>{item.territory}</p>
        <dl className="mt-1 grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-0.5 text-slate-700">
          {density && <><dt className="text-slate-500">Densidade</dt><dd className="font-semibold text-ink">{item.density === null ? "Não avaliável"
            : formatNumber(item.density) + " " + DENSITY_UNIT}</dd></>}
          <dt className="text-slate-500">Quantidade</dt><dd className={density ? "" : "font-semibold text-ink"}>{item.quantity === null ? "Não avaliável"
            : formatNumber(item.quantity, "CONTAGEM") + (density ? "" : " " + unit)}</dd>
          {density && <><dt className="text-slate-500">População</dt><dd>{item.population === null ? "Não avaliável"
            : formatNumber(item.population, "CONTAGEM") + " habitantes"}</dd></>}
        </dl>
        {item.condition && item.condition !== "Avaliável" && <p className="mt-1 text-slate-600">{item.condition}</p>}
        {withChange && item.window && <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {trend && item.window.trend ? <TrendBadge label={item.window.trend} meta={trend} motive={item.window.trendMotive}/> :
            <span className="text-slate-600">{item.window.trend || "Tendência não avaliável"}</span>}
          {item.window.trendMotive && <span className="text-slate-600">{item.window.trendMotive}</span>}
        </div>}
      </div>)}
    </div>}
    <p className="text-[10px] text-slate-500">Valores {density ? DENSITY_UNIT : "em " + unit}{group.level ? ", no eixo deste nível" : ""}, a partir do zero</p>
    {group.objects.length > 40 ? <ValueRows objects={group.objects} domain={domain} shown={shown} unit={unit} title={group.title}/> :
      <div className="space-y-1" role="list" aria-label={"Valores · " + group.title}>
        {group.objects.map(item => <ValueRow key={item.territory} item={item} domain={domain} text={shown(item)} unit={unit} stack={narrow}/>)}
      </div>}
    {pair && <div data-testid="comparison-pair-relation" className="flex flex-wrap items-center gap-1.5 text-xs">
      <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5">Relação A/B: <strong>{pair.a}</strong> {RELATION_TEXT[pair.relation] || pair.relation}{" "}
        <strong>{pair.b}</strong></span>
      {pair.difference !== null && <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5">Diferença A − B ={" "}
        <strong>{signed(pair.difference, kind)}</strong>{unit ? " " + unit : ""}</span>}
      <span className="text-slate-500">relação e diferença calculadas pelo motor</span>
    </div>}
  </div>;
}

function ValueRow({ item, domain, text, unit, stack = false }: { item: ComparisonObject; domain: [number, number]; text: string; unit: string;
  stack?: boolean }) {
  const zero = position(0, domain) * 100, end = item.value === null ? zero : position(item.value, domain) * 100;
  return <div role="listitem" className={"grid items-center gap-x-2 text-xs " + (stack ? "grid-cols-[minmax(0,1fr)_auto]"
    : "grid-cols-[minmax(0,38%)_minmax(0,1fr)_auto]")}
    aria-label={item.territory + ": " + text + (item.value !== null && unit ? " " + unit : "")}>
    <span className={(stack ? "col-span-2 break-words " : "truncate ") + "text-slate-700"} title={item.territory}>{item.territory}</span>
    <span className="relative h-4 min-w-0">
      <span aria-hidden className="absolute inset-y-0 border-l border-slate-300" style={{ left: zero + "%" }}/>
      {item.value !== null && <span aria-hidden className="absolute top-1 h-2 rounded-sm" style={{ left: Math.min(zero, end) + "%",
        width: Math.abs(end - zero) + "%", background: item.level === "UF" ? undefined : CATEGORICAL[0],
        backgroundImage: item.level === "UF" ? UF_TEXTURE : undefined }}/>}
      {item.value !== null && <span aria-hidden className="absolute top-0 h-4 w-4 -translate-x-1/2 rounded-full border-2 border-white"
        style={{ left: end + "%", background: item.level === "BR" ? INK.primary : CATEGORICAL[0] }}/>}
    </span>
    <span className={"whitespace-nowrap tabular-nums " + (item.value === null ? "text-slate-500" : "font-semibold text-ink")}>{text}</span>
  </div>;
}

function ValueRows({ objects, domain, shown, unit, title }: { objects: ComparisonObject[]; domain: [number, number];
  shown: (item: ComparisonObject) => string; unit: string; title: string }) {
  const [top, setTop] = useState(0);
  const height = 26, range = visibleRange(top, height, objects.length);
  return <div tabIndex={0} role="list" aria-label={"Valores · " + title + " (lista com rolagem)"} className="max-h-[360px] overflow-y-auto rounded-lg border border-line"
    onScroll={event => setTop(event.currentTarget.scrollTop)}>
    <div style={{ height: objects.length * height, position: "relative" }}>
      {objects.slice(range.start, range.end).map((item, index) => <div key={item.territory} className="absolute inset-x-0 px-2"
        style={{ top: (range.start + index) * height, height }}><ValueRow item={item} domain={domain} text={shown(item)} unit={unit}/></div>)}
    </div>
  </div>;
}

// ------------------------------------------------------------------------------------------------ halteres
/** Halteres do primeiro ao último período (vazado → cheio) num eixo comum, com a variação e a classe do motor. Muitos
 * territórios: lista com rolagem, só as linhas visíveis montadas. */
export function DumbbellList({ items, kind, unit, trend, title, testId }: { items: Dumbbell[]; kind: IndicatorKind; unit: string;
  trend: TrendMeta | null; title: string; testId?: string }) {
  // Eixo a partir do zero: a distância entre os dois círculos não é ampliada pelo enquadramento.
  const domain = useMemo(() => zeroExtent(items.flatMap(item => [item.initial, item.final])), [items]);
  const [top, setTop] = useState(0);
  const narrow = useNarrow();
  const height = narrow ? 76 : 58;
  const row = (item: Dumbbell) => <DumbbellRow key={item.key} item={item} domain={domain} kind={kind} unit={unit} trend={trend} stack={narrow}/>;
  const [low, high] = formatPair(domain[0], domain[1], kind);
  const axis = <p className={"flex justify-between text-[10px] text-slate-500 " + (narrow ? "" : "pl-[34%]")} aria-hidden><span>{low}</span><span>{high} {unit}</span></p>;
  if (items.length <= 40) return <div data-testid={testId} data-total={items.length} role="list" aria-label={title} className="space-y-1">
    {axis}{items.map(row)}</div>;
  const range = visibleRange(top, height, items.length, 16);
  return <div data-testid={testId} data-total={items.length}>
    {axis}
    <div role="list" aria-label={title + " (lista com rolagem)"} tabIndex={0} className="max-h-[440px] overflow-y-auto rounded-lg border border-line"
      onScroll={event => setTop(event.currentTarget.scrollTop)}>
      <div style={{ height: items.length * height, position: "relative" }}>
        {items.slice(range.start, range.end).map((item, index) => <div key={item.key} className="absolute inset-x-0 px-2"
          style={{ top: (range.start + index) * height, height }}>{row(item)}</div>)}
      </div>
    </div>
  </div>;
}

function DumbbellRow({ item, domain, kind, unit, trend, stack = false }: { item: Dumbbell; domain: [number, number]; kind: IndicatorKind;
  unit: string; trend: TrendMeta | null; stack?: boolean }) {
  const ok = item.initial !== null && item.final !== null;
  const [first, last] = ok ? formatPair(item.initial!, item.final!, kind) : ["", ""];
  const a = ok ? position(item.initial!, domain) * 100 : 0, b = ok ? position(item.final!, domain) * 100 : 0;
  const label = item.territory + (item.category ? " · " + item.category : "") + ": " + (ok ? first + " → " + last +
    (item.delta !== null ? " (" + signed(item.delta, kind) + ")" : "") + (unit ? " " + unit : "") : item.condition || "mudança não avaliável");
  return <div role="listitem" data-testid="dumbbell-row" data-territory={item.territory} aria-label={label}
    className={"grid items-center gap-x-2 border-b border-slate-100 py-1 text-xs " + (stack ? "grid-cols-1" : "grid-cols-[minmax(0,34%)_minmax(0,1fr)]")}>
    <span className={(stack ? "break-words " : "truncate ") + "font-semibold text-slate-800"} title={item.territory}>{item.territory}</span>
    <span className="relative h-4 min-w-0">
      <span aria-hidden className="absolute inset-x-0 top-1/2 border-t border-dashed border-slate-200"/>
      {ok && <>
        <span aria-hidden className="absolute top-1/2 h-0.5 -translate-y-1/2" style={{ left: Math.min(a, b) + "%", width: Math.abs(b - a) + "%",
          background: INK.secondary }}/>
        <span aria-hidden data-testid="dumbbell-initial" className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 bg-white"
          style={{ left: a + "%", borderColor: CATEGORICAL[0] }}/>
        <span aria-hidden data-testid="dumbbell-final" className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ left: b + "%", background: CATEGORICAL[0] }}/>
      </>}
    </span>
    <span className={(stack ? "" : "col-start-2 ") + "flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 text-slate-700"}>
      {ok ? <span className="tabular-nums" title={"Valores do motor: " + fullPrecision(item.initial) + " → " + fullPrecision(item.final)}>{first} → {last}
        {item.delta !== null && <> (<strong data-testid="dumbbell-delta" className="text-ink">{signed(item.delta, kind)}</strong>)</>}</span>
        : <span className="text-slate-600">{item.condition || "Mudança não avaliável"}</span>}
      {item.trend != null && (trend ? <TrendBadge label={item.trend} meta={trend} motive={item.trendMotive as string | null}/> :
        <span>{String(item.trend)}</span>)}
    </span>
  </div>;
}

// ------------------------------------------------------------------------------------------------ pequenos múltiplos
type MultiplesProps = { source: Row[]; spec: { periodo: string; territorio: string; categoria: string; valor: string };
  territories: string[]; category: string; kind: IndicatorKind; unit: string; trend: TrendMeta | null; rows: Row[];
  breaks: Set<string>; dashed: string | null; title: string; testId?: string };
const PER_PAGE = 12;

/** Pequenos múltiplos (V4): uma série por território, na mesma escala em todas as páginas; lacunas sem ligação; séries não
 * comparáveis só como pontos; o Brasil (quando marcado) tracejado. Selo da classe do motor em cada um. */
export function TrendSmallMultiples(p: MultiplesProps) {
  const [page, setPage] = useState(0);
  const model = useMemo(() => smallMultiples(p.source, p.spec, p.territories, p.category, page, PER_PAGE),
    [p.source, p.spec, p.territories, p.category, page]);
  if (model.periods.length < 2 || !model.items.length) return null;
  const [low, high] = formatPair(model.domain[0], model.domain[1], p.kind);
  const rowOf = (territory: string) => p.rows.find(row => String(row["Território"] ?? "") === territory && String(row["Categoria"] ?? "") === p.category);
  return <figure data-testid={p.testId || "trend-small-multiples"} data-domain={model.domain.join(";")} aria-label={p.title} className="w-full">
    <figcaption className="mb-2 text-xs text-slate-600">{p.title}: mesma escala em todos ({low} a {high} {p.unit}), de{" "}
      {displayPeriod(model.periods[0])} a {displayPeriod(model.periods[model.periods.length - 1])}. Sem interpolação nem reta ajustada.</figcaption>
    {model.pages > 1 && <nav aria-label="Páginas dos pequenos múltiplos" className="no-print mb-2 flex flex-wrap items-center gap-2 text-xs">
      <button type="button" className="rounded-lg border border-line bg-white px-3 py-1.5 font-semibold disabled:opacity-40" disabled={model.page === 0}
        onClick={() => setPage(model.page - 1)}>Anteriores</button>
      <span>Territórios {model.page * PER_PAGE + 1} a {Math.min((model.page + 1) * PER_PAGE, p.territories.length)} de {p.territories.length}</span>
      <button type="button" className="rounded-lg border border-line bg-white px-3 py-1.5 font-semibold disabled:opacity-40"
        disabled={model.page === model.pages - 1} onClick={() => setPage(model.page + 1)}>Próximos</button>
    </nav>}
    <div className="grid grid-cols-1 gap-2 min-[420px]:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
      {model.items.map(item => {
        const width = 160, height = 56;
        const { segments, dots } = seriesSegments(item.points, width, height, model.domain);
        const lastIndex = [...item.points].reverse().findIndex(point => point.value !== null);
        const last = lastIndex < 0 ? null : item.points[item.points.length - 1 - lastIndex];
        const row = rowOf(item.territory);
        const pointsOnly = p.breaks.has(item.territory), dashed = p.dashed === item.territory;
        const color = dashed ? INK.primary : CATEGORICAL[0];
        return <div key={item.territory} data-testid="trend-small-multiple" data-territory={item.territory}
          className="min-w-0 rounded-xl border border-line bg-white p-2">
          <p className="truncate text-xs font-semibold text-ink" title={item.territory}>{item.territory}{dashed ? " (tracejado)" : ""}</p>
          <svg role="img" aria-label={item.territory + ": " + item.points.map(point => displayPeriod(point.period) + " " +
            (point.value === null ? "sem valor" : formatNumber(point.value, p.kind))).join("; ")} viewBox={`0 0 ${width} ${height}`}
            className="block w-full">
            <line x1="0" x2={width} y1={height - 4} y2={height - 4} stroke={INK.grid}/>
            {!pointsOnly && segments.map((segment, index) => segment.length > 1 ? <polyline key={index} fill="none" stroke={color} strokeWidth="1.6"
              strokeDasharray={dashed ? "4 3" : undefined} points={segment.map(xy => xy.join(",")).join(" ")}/> : null)}
            {dots.map(([x, y], index) => <circle key={index} cx={x} cy={y} r={pointsOnly ? 2 : index === dots.length - 1 ? 2.4 : 1.2} fill={color}/>)}
          </svg>
          <p className="flex flex-wrap items-center justify-between gap-1 text-[11px] text-slate-600">
            <span className="tabular-nums">{last ? displayPeriod(last.period) + ": " + formatNumber(last.value!, p.kind) : "sem valor"}</span>
            {row?.["Tendência"] != null && (p.trend ? <TrendBadge label={row["Tendência"]} meta={p.trend} motive={row["Motivo da tendência"] as string | null}/>
              : <span>{String(row["Tendência"])}</span>)}
          </p>
        </div>;
      })}
    </div>
  </figure>;
}

// ------------------------------------------------------------------------------------------------ ranking
export type LollipopDatum = { id: string; label: string; value: number | null; rank: unknown; condition: string; highlighted: boolean };

/** Ranking em pirulito (V7): "Posição N" do motor, na ordem pedida (padrão: a do resultado); haste do zero ao valor. */
export function RankingLollipop({ data, kind, unit, title, onSelect }: { data: LollipopDatum[]; kind: IndicatorKind; unit: string; title: string;
  onSelect: (id: string) => void }) {
  const domain = useMemo(() => zeroExtent(data.map(item => item.value)), [data]);
  const texts = useMemo(() => neighborTexts(data.map(item => item.value), value => formatNumber(value, kind),
    (a, b) => formatPair(a, b, kind)), [data, kind]);
  const order = useMemo(() => new Map(data.map((item, place) => [item.id, place])), [data]);
  const [top, setTop] = useState(0);
  const narrow = useNarrow();
  const height = narrow ? 46 : 30, range = visibleRange(top, height, data.length, 22);
  const zero = position(0, domain) * 100;
  const row = (item: LollipopDatum) => {
    const end = item.value === null ? zero : position(item.value, domain) * 100;
    const rank = typeof item.rank === "number" ? "Posição " + item.rank : "Sem posição";
    const shown = item.value === null ? "" : texts[order.get(item.id) ?? 0] || formatNumber(item.value, kind);
    return <button type="button" data-testid="lollipop-row" data-rank={typeof item.rank === "number" ? item.rank : ""} onClick={() => onSelect(item.id)}
      aria-label={rank + " · " + item.label + ": " + (item.value === null ? "Não avaliável" : shown + " " + unit)}
      className={"grid w-full items-center gap-x-2 px-2 text-left text-xs hover:bg-blue-50 " + (narrow
        ? "grid-cols-[4.4rem_minmax(0,1fr)_auto] " : "grid-cols-[4.8rem_minmax(0,30%)_minmax(0,1fr)_auto] ") +
        (item.highlighted ? "" : "opacity-60")} style={{ height }}>
      <span className="whitespace-nowrap font-semibold text-slate-600">{rank}</span>
      <span className={(narrow ? "col-span-2 " : "") + "truncate text-slate-800"} title={item.label}>{item.label}</span>
      <span className={(narrow ? "col-span-2 " : "") + "relative h-4 min-w-0"}>
        <span aria-hidden className="absolute inset-y-0 border-l border-slate-300" style={{ left: zero + "%" }}/>
        {item.value !== null && <>
          <span aria-hidden className="absolute top-1/2 h-0.5 -translate-y-1/2" style={{ left: Math.min(zero, end) + "%", width: Math.abs(end - zero) + "%",
            background: INK.secondary }}/>
          <span aria-hidden className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ left: end + "%",
            background: CATEGORICAL[0] }}/></>}
      </span>
      <span className={"whitespace-nowrap tabular-nums " + (item.value === null ? "text-slate-500" : "text-ink")}>
        {item.value === null ? item.condition || "Não avaliável" : shown}</span>
    </button>;
  };
  return <figure data-testid="ranking-lollipop" data-total={data.length} aria-label={title} className="w-full">
    <figcaption className="mb-2 text-xs text-slate-600">A posição é a do motor (CAP-SUB-02); ordem descritiva, sem julgamento
      normativo. Território sem valor fica sem haste, nunca como zero.</figcaption>
    {data.length <= 40 ? <div role="list" aria-label="Territórios ordenados" className="divide-y divide-slate-100 rounded-lg border border-line">
      {data.map(item => <div role="listitem" key={item.id}>{row(item)}</div>)}</div> :
      <div role="region" aria-label="Territórios ordenados (lista com rolagem)" tabIndex={0} className="max-h-[440px] overflow-y-auto rounded-lg border border-line"
        onScroll={event => setTop(event.currentTarget.scrollTop)}>
        <div style={{ height: data.length * height, position: "relative" }}>
          {data.slice(range.start, range.end).map((item, index) => <div key={item.id} className="absolute inset-x-0"
            style={{ top: (range.start + index) * height }}>{row(item)}</div>)}
        </div>
      </div>}
    <p className={"mt-1 flex justify-between text-[10px] text-slate-500 " + (narrow ? "" : "pl-[45%]")} aria-hidden><span>{formatNumber(domain[0], kind)}</span>
      <span>{formatNumber(domain[1], kind)} {unit}</span></p>
  </figure>;
}

// ------------------------------------------------------------------------------------------------ distribuição
/** Faixa da distribuição (V6): um ponto por território na raia da sua classe (do motor), na posição do valor; cor ordinal
 * pela classe. Pontos de corte não são desenhados (o motor não os devolve). */
export function DistributionStrip({ summary, detail, column, unit, kind, highlight, idOf }: { summary: Row[]; detail: Row[]; column: string;
  unit: string; kind: IndicatorKind; highlight: Set<string>; idOf: (row: Row) => string | null }) {
  const model = useMemo(() => distributionStrip(summary, detail, column), [summary, detail, column]);
  const ids = useMemo(() => new Map(detail.map(row => [String(row["Território"] ?? ""), idOf(row)])), [detail, idOf]);
  const [box, measured] = useWidth(model.points.length > 0);
  // Eixo logarítmico quando todos os valores são positivos (a mesma transformação contínua da escala de cor do mapa),
  // para que as raias de valores baixos não fiquem espremidas junto ao mínimo; com zero ou negativos, linear.
  const scale = colorScaleFor(model.domain, "logaritmica");
  const width = Math.max(280, measured), lane = 22, height = model.lanes.length * lane + 8, left = 76;
  const at = (value: number) => colorPosition(value, model.domain, scale);
  const x = (value: number) => left + at(value) * (width - left - 10);
  const ticks = scaleTicks(model.domain, scale, 0.1, 0.06);
  if (!model.points.length) return null;
  const [low, high] = formatPair(model.domain[0], model.domain[1], kind);
  const axisText = scale === "logaritmica" ? "eixo logarítmico" : "eixo linear";
  return <figure data-testid="distribution-strip" data-total={model.points.length} data-scale={scale} aria-label={"Faixa da distribuição: " + column}
    className="w-full"><div ref={box} className="w-full">
    <svg role="img" aria-label={model.points.length + " territórios com valor, um ponto por território na raia da sua classe; de " + low + " a " +
      high + " " + unit + " (" + axisText + ")."} width={width} height={height + 30} viewBox={`0 0 ${width} ${height + 30}`} className="block max-w-full">
      {model.lanes.map((name, index) => <g key={name}>
        <line x1={left} x2={width - 10} y1={6 + index * lane + lane / 2} y2={6 + index * lane + lane / 2} stroke={INK.grid}/>
        <text x={0} y={6 + index * lane + lane / 2 + 4} fontSize="11" fill={INK.secondary}>{name}</text>
      </g>)}
      {model.points.map((point, index) => {
        const id = ids.get(point.territory);
        const chosen = !!id && highlight.has(id);
        return <circle key={index} cx={x(point.value)} cy={6 + point.lane * lane + lane / 2} r={chosen ? 4.5 : 2.6}
          fill={ORDINAL[Math.min(point.lane, ORDINAL.length - 1)]} fillOpacity={chosen ? 1 : 0.7} stroke={chosen ? INK.primary : "none"}
          strokeWidth={chosen ? 1.5 : 0}>{model.points.length <= 400 && <title>{point.territory}: {formatNumber(point.value, kind)} {unit} ({point.group})</title>}</circle>;
      })}
      {ticks.map(tick => <g key={tick.value} aria-hidden>
        <line x1={x(tick.value)} x2={x(tick.value)} y1={height} y2={height + 4} stroke={INK.muted}/>
        <text x={x(tick.value)} y={height + 14} fontSize="10" fill={INK.muted} textAnchor="middle">{tick.value.toLocaleString("pt-BR", { maximumFractionDigits: 8 })}</text>
      </g>)}
      <line x1={left} x2={left} y1={height} y2={height + 4} stroke={INK.primary}/>
      <line x1={width - 10} x2={width - 10} y1={height} y2={height + 4} stroke={INK.primary}/>
      <text x={left} y={height + 27} fontSize="10" fill={INK.secondary}>mín. {low}</text>
      <text x={width - 10} y={height + 27} fontSize="10" fill={INK.secondary} textAnchor="end">máx. {high} {unit}</text>
    </svg></div>
    <figcaption className="mt-1 text-xs text-slate-600">Cada ponto é um território, na raia da classe calculada pelo motor (CAP-DIS-02)
      e na posição do seu valor, num {axisText} entre o menor e o maior valor{scale === "logaritmica" ? " (as marcas 1, 2 e 5 × 10ⁿ são do eixo, não pontos de corte)" : ""};
      os territórios selecionados aparecem maiores. As raias não são limites desenhados pela tela.</figcaption>
  </figure>;
}

// ------------------------------------------------------------------------------------------------ agregação
/** Cartão da agregação (V8): quantidade, população e densidade do motor, com o tipo de contagem como selo obrigatório,
 * os membros e, quando o motor os declara, os ausentes por competência. Sem linha nacional (L1751). */
export function AggregateCard({ result, unit }: { result: { rows: Row[]; metrics: { label: string; value: string | number }[];
  metadata: Record<string, unknown> }; unit: string }) {
  const row = result.rows[0];
  const { members, expansions } = useMemo(() => aggregateMembers(result.metadata), [result]);
  if (!row) return null;
  const kind = String(row["Tipo"] ?? "");
  const partial = kind.includes("possível dupla contagem");
  const count = result.metrics.find(item => item.label === "Territórios agregados")?.value;
  const value = (key: string, type: IndicatorKind) => typeof row[key] === "number" ? formatNumber(row[key] as number, type) : "Não avaliável";
  return <section aria-label="Cartão da agregação" data-testid="aggregate-card" className="mt-6 rounded-2xl border border-line bg-white p-4 shadow-sm">
    <div className="flex flex-wrap items-center gap-2">
      <h4 className="text-sm font-bold text-ink">Agregação{typeof count === "number" ? " de " + formatNumber(count, "CONTAGEM") + " territórios" : ""}</h4>
      <span data-testid="aggregate-type" className="rounded-full border border-blue-300 px-2 py-0.5 text-[11px] font-semibold text-blue-900"
        style={partial ? { backgroundImage: "repeating-linear-gradient(45deg, #eaf2fc 0 3px, #ffffff 3px 6px)" } : undefined}>{kind || "Tipo não informado"}</span>
    </div>
    <dl className="mt-3 grid gap-3 sm:grid-cols-3">
      <div className="min-w-0"><dt className="text-xs text-slate-500">Quantidade</dt>
        <dd className="text-2xl font-bold text-ink" title={"Valor do motor: " + fullPrecision(row["Quantidade"])}>{value("Quantidade", "CONTAGEM")}</dd>
        <dd className="text-xs text-slate-600">{partial ? "soma das contagens dos componentes" : unit}</dd></div>
      <div className="min-w-0"><dt className="text-xs text-slate-500">População</dt>
        <dd className="text-2xl font-bold text-ink">{value("População", "CONTAGEM")}</dd><dd className="text-xs text-slate-600">habitantes</dd></div>
      <div className="min-w-0"><dt className="text-xs text-slate-500">Densidade</dt>
        <dd className="text-2xl font-bold text-ink">{value("Densidade por 1.000", "CONTINUO")}</dd><dd className="text-xs text-slate-600">{DENSITY_UNIT}</dd></div>
    </dl>
    {partial && <p className="mt-2 text-xs text-blue-900">Soma dos componentes: quem atua em mais de um território é contado em cada um
      (possível dupla contagem); não é o número de pessoas diferentes.</p>}
    {members.length > 0 && <details className="mt-3 text-xs">
      <summary className="cursor-pointer font-semibold text-teal">Membros da agregação{typeof count === "number" ? " (" + formatNumber(count, "CONTAGEM") + ")" : ""}</summary>
      <ul data-testid="aggregate-members" className="mt-2 max-h-40 columns-1 gap-4 overflow-auto sm:columns-2">
        {members.map(item => <li key={item.id} className="break-inside-avoid">{item.label}</li>)}</ul>
    </details>}
    {expansions.map(item => {
      const missing = Object.entries((item.ausentes_por_competencia || {}) as Record<string, string[]>);
      return missing.length ? <p key={String(item.id)} data-testid="aggregate-missing" className="mt-2 text-xs text-amber-900">
        {String(item.rotulo)}: {missing.map(([period, codes]) => displayPeriod(period) + ", sem registro: " + codes.join(", ")).join("; ")}.</p> : null;
    })}
  </section>;
}

// ------------------------------------------------------------------------------------------------ rotatividade
/** Rotatividade (V9): barra da coorte inicial dividida em "permanecem" e "saíram", com os percentuais do motor (% da coorte
 * inicial). Coorte sem registro em um dos períodos: barra cinza tracejada, com o motivo. */
export function RotationCohortBars({ rows }: { rows: Row[] }) {
  const bars = useMemo(() => cohortBars(rows), [rows]);
  if (!bars.length) return null;
  return <figure data-testid="rotation-cohort-bars" aria-label="Coorte inicial: permanecem e saíram" className="mt-6 space-y-2 rounded-2xl border border-line bg-white p-4">
    <h4 className="text-sm font-bold text-ink">Coorte inicial: permanecem e saíram (% da coorte inicial)</h4>
    {bars.map((bar, index) => {
      const ok = bar.stayShare !== null && bar.leftShare !== null;
      return <div key={index} data-testid="cohort-bar" data-territory={bar.territory} className="space-y-1 text-xs">
        <p className="flex flex-wrap items-baseline justify-between gap-2"><strong className="text-ink">{bar.territory}{bar.category ? " · " + bar.category : ""}</strong>
          <span className="text-slate-600">{displayPeriod(bar.start)} → {displayPeriod(bar.end)} · coorte inicial: {bar.cohort === null ? "não avaliável" :
            formatNumber(bar.cohort, "CONTAGEM") + " pessoas"}</span></p>
        {ok ? <div className="flex h-5 w-full overflow-hidden rounded" role="img" aria-label={formatNumber(bar.stay ?? 0, "CONTAGEM") + " permanecem (" +
          formatNumber(bar.stayShare!) + "% da coorte inicial) e " + formatNumber(bar.left ?? 0, "CONTAGEM") + " saíram (" + formatNumber(bar.leftShare!) + "%)"}>
          <span style={{ width: bar.stayShare + "%", background: CATEGORICAL[0] }}/>
          <span style={{ width: bar.leftShare + "%", background: CATEGORICAL[1] }}/>
        </div> : <div className="h-5 w-full rounded border border-dashed" style={{ borderColor: NOT_EVALUABLE }} aria-hidden/>}
        <p className="text-slate-700">{ok ? <><span className="mr-3"><span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-sm" style={{ background: CATEGORICAL[0] }}/>
          Permanecem: <strong>{formatNumber(bar.stay ?? 0, "CONTAGEM")}</strong> ({formatNumber(bar.stayShare!)}%)</span>
          <span><span aria-hidden className="mr-1 inline-block h-2 w-2 rounded-sm" style={{ background: CATEGORICAL[1] }}/>
            Saíram: <strong>{formatNumber(bar.left ?? 0, "CONTAGEM")}</strong> ({formatNumber(bar.leftShare!)}%)</span></> : bar.condition}</p>
      </div>;
    })}
    <figcaption className="text-xs text-slate-600">Percentuais da coorte inicial calculados pelo motor (CAP-ROT-01); as cores só separam
      os dois grupos, sem juízo.</figcaption>
  </figure>;
}

/** Bloco de um nível no painel de níveis (V5). */
export function LevelBlock({ level, children, testId }: { level: LevelCode; children: ReactNode; testId?: string }) {
  return <div data-testid={testId || "level-panel-" + level.toLowerCase()} data-level={level}
    className={"min-w-0 rounded-xl border p-3 " + (level === "UF" ? "border-blue-200" : "border-line")}>
    {children}
  </div>;
}
