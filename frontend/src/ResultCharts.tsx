import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CATEGORICAL, INK, NOT_EVALUABLE, displayPeriod, formatNumber, fullPrecision, niceDomain, type IndicatorKind } from "./representation";

// Gráficos de barras e de linhas (CAP-REP-02) sobre valores já calculados pelo motor. A ordem padrão
// é a do código territorial ou a do resultado de ordenação (RQ-REP-03); reordenar pelo valor é estado
// visual e não exibe posições. Ausências ficam como lacunas, sem interpolação nem linhas de tendência.

/** `group`: estado do município (members[].state), só para separadores visuais na ordem do código; nada é reordenado. */
export type BarDatum = { id: string; label: string; value: number | null; highlighted: boolean; group?: string };
/** Taxa nacional de contexto (D5) desenhada como linha tracejada sobre as barras dos municípios; não colore as barras. */
export type BarReference = { value: number; label: string; text: string };
export type CountDatum = { label: string; value: number; color: string };
export type LinePoint = Record<string, string | number | null>;
const axis = { fontSize: 11, fill: INK.muted };

function TooltipBox({ title, lines }: { title: string; lines: { color?: string; text: string; strong?: string }[] }) {
  return <div className="max-w-[260px] rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-card">
    <p className="mb-1 font-semibold text-ink">{title}</p>
    {lines.map((line, index) => <p key={index} className="flex items-center gap-1.5 text-slate-600">
      {line.color && <span aria-hidden className="inline-block h-0.5 w-3" style={{ background: line.color }}/>}
      {line.strong && <strong className="text-ink">{line.strong}</strong>}<span>{line.text}</span></p>)}
  </div>;
}

function ReferenceCaption({ reference }: { reference?: BarReference }) {
  return reference ? <figcaption data-testid="bars-reference-line" className="mt-1 flex items-center gap-2 text-xs text-slate-600">
    <svg aria-hidden width="22" height="10"><line x1="1" y1="5" x2="21" y2="5" stroke={INK.primary} strokeWidth="1.5" strokeDasharray="4 3"/></svg>
    <span>{reference.text}</span></figcaption> : null;
}

/** Começo de um novo grupo (estado) na sequência das barras: separador visual, sem contagem por grupo. */
const groupStarts = (data: BarDatum[]) => {
  const groups = new Set(data.map(item => item.group || ""));
  return groups.size > 1 ? data.map((item, index) => index > 0 && item.group !== data[index - 1].group) : data.map(() => false);
};

export function TerritoryBars({ data, unit, kind, title, onSelect, reference, texture = false }: { data: BarDatum[]; unit: string; kind: IndicatorKind;
  title: string; onSelect: (id: string) => void; reference?: BarReference; texture?: boolean }) {
  if (data.length > 40) return <ScrollableBars key={title} data={data} unit={unit} kind={kind} title={title} onSelect={onSelect} reference={reference}/>;
  const height = Math.max(220, 46 + data.length * 26) + (reference ? 16 : 0);
  const starts = groupStarts(data);
  // Soma dos componentes (estados): textura própria, além do rótulo "possível dupla contagem" (RQ-REP-14).
  const fill = (item: BarDatum) => texture ? (item.highlighted ? "url(#adt-uf-hatch)" : "url(#adt-uf-hatch-light)") : item.highlighted ? CATEGORICAL[0] : "#9ec5f4";
  return <figure aria-label={title} className="w-full">
    <div style={{ height }} className="w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: reference ? 20 : 4, right: 52, bottom: 4, left: 4 }} barCategoryGap={4}>
        {texture && <defs>
          <pattern id="adt-uf-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#cfe1f7"/><rect width="3" height="6" fill={CATEGORICAL[0]}/></pattern>
          <pattern id="adt-uf-hatch-light" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#eef4fc"/><rect width="3" height="6" fill="#9ec5f4"/></pattern>
        </defs>}
        <CartesianGrid horizontal={false} stroke={INK.grid}/>
        <XAxis type="number" tick={axis} tickFormatter={(value: number) => formatNumber(value, kind)} stroke={INK.grid}/>
        <YAxis type="category" dataKey="label" width={170} interval={0} stroke={INK.grid}
          tick={(props: { x: number; y: number; index?: number; payload: { value: string; index?: number } }) => {
            const value = props.payload.value, index = props.index ?? props.payload.index ?? 0;
            const step = (height - (reference ? 40 : 24)) / Math.max(1, data.length);
            return <g>
              {starts[index] && <g data-testid="bar-group-separator"><line x1={4} x2={2000} y1={props.y - step / 2} y2={props.y - step / 2}
                stroke={INK.muted} strokeDasharray="2 3"/><text x={6} y={props.y - step / 2 + 9} fontSize={9} fill={INK.muted}>{data[index].group}</text></g>}
              <text x={props.x} y={props.y} dy={4} textAnchor="end" fontSize={11} fill={INK.secondary}>
                {value.length > 26 ? value.slice(0, 25) + "…" : value}</text>
            </g>;
          }}/>
        <Tooltip cursor={{ fill: "rgba(42,120,214,0.06)" }} wrapperStyle={{ maxWidth: "calc(100% - 40px)" }} content={({ active, payload }) => {
          const item = active && payload?.[0]?.payload as BarDatum | undefined;
          return item ? <TooltipBox title={item.label} lines={[item.value === null ? { text: "Não avaliável (sem valor no resultado)" } :
            { strong: formatNumber(item.value, kind), text: " " + unit + " · valor integral " + fullPrecision(item.value) }]}/> : null;
        }}/>
        <Bar dataKey="value" name={title} radius={[0, 4, 4, 0]} maxBarSize={18} onClick={(entry: BarDatum) => onSelect(entry.id)} cursor="pointer">
          {data.map(item => <Cell key={item.id} fill={fill(item)}/>)}
          {/* Valor do motor no fim de cada barra (RQ-REP-05); sem valor, nada (a ausência é dita abaixo do gráfico). */}
          <LabelList dataKey="value" position="right" fontSize={10} fill={INK.secondary}
            formatter={(value: unknown) => typeof value === "number" ? formatNumber(value, kind) : ""}/>
        </Bar>
        {/* A referência entra no eixo (ifOverflow), mas nunca na cor das barras. */}
        {reference && <ReferenceLine x={reference.value} stroke={INK.primary} strokeWidth={1.5} strokeDasharray="4 3" ifOverflow="extendDomain"
          label={{ value: reference.label, position: "top", fontSize: 11, fontWeight: 600, fill: INK.primary }}/>}
      </BarChart>
    </ResponsiveContainer></div>
    <ReferenceCaption reference={reference}/>
    {data.some(item => item.value === null) && <figcaption className="mt-1 text-xs text-slate-600">
      Sem barra por não avaliabilidade (nunca convertida em zero): {data.filter(item => item.value === null).map(item => item.label).join("; ")}.
    </figcaption>}
  </figure>;
}

// Todos os territórios permanecem acessíveis. Só as linhas próximas à área visível
// são montadas, para evitar milhares de elementos SVG no resultado Brasil.
function ScrollableBars({ data, unit, kind, title, onSelect, reference }: { data: BarDatum[]; unit: string; kind: IndicatorKind; title: string;
  onSelect: (id: string) => void; reference?: BarReference }) {
  const [start, setStart] = useState(0);
  const narrow = useNarrow();
  const rowHeight = narrow ? 46 : 34, windowSize = 20;
  const [min, max] = useMemo(() => {
    let low = 0, high = 0;
    for (const item of data) if (item.value !== null) { low = Math.min(low, item.value); high = Math.max(high, item.value); }
    if (reference) { low = Math.min(low, reference.value); high = Math.max(high, reference.value); }  // a referência entra no eixo
    return [low, high];
  }, [data, reference]);
  const span = max - min || 1, zero = -min / span * 100;
  const mark = reference ? (reference.value - min) / span * 100 : null;
  const offset = Math.min(start, Math.max(0, data.length - 1));
  const starts = useMemo(() => groupStarts(data), [data]);
  return <figure aria-label={title} className="w-full" data-testid="scrollable-bars" data-total={data.length}>
    <figcaption className="mb-2 text-xs text-slate-600">{data.length.toLocaleString("pt-BR")} territórios.
      Role o gráfico para percorrer todos ou selecione territórios na tabela para comparar.</figcaption>
    <div className={"mb-1 flex justify-between text-[11px] text-slate-500 " + (narrow ? "" : "pl-[42%]")}><span>{formatNumber(min, kind)}</span>
      <span>{formatNumber(max, kind)} {unit}</span></div>
    {mark !== null && <div aria-hidden className={"relative mb-1 h-4 text-[11px] font-semibold text-ink " + (narrow ? "" : "pl-[42%]")}>
      <span className="relative block h-full"><span className="absolute -translate-x-1/2 whitespace-nowrap" style={{left: mark + "%"}}>
        {reference!.label}</span></span></div>}
    <div role="region" aria-label="Barras por território" tabIndex={0} className="max-h-[440px] overflow-y-auto rounded-lg border border-line"
      onScroll={event => setStart(Math.max(0, Math.floor(event.currentTarget.scrollTop / rowHeight) - 2))}>
      <div style={{height: data.length * rowHeight, position: "relative"}}>
        {data.slice(offset, offset + windowSize).map((item, index) => {
          const value = item.value, end = value === null ? zero : (value - min) / span * 100;
          // O valor fica logo depois do fim da barra (perto da borda direita, dentro dela), num fundo claro que passa
          // por cima da linha tracejada da referência: nem a barra nem a linha cobrem o número.
          const tip = Math.max(zero, end), inside = value !== null && tip > 82;
          return <button key={item.id} type="button" onClick={() => onSelect(item.id)}
            aria-label={item.label + ": " + (value === null ? "Não avaliável" : formatNumber(value, kind) + " " + unit)}
            title={item.label + ": " + (value === null ? "Não avaliável" : fullPrecision(value) + " " + unit)}
            style={{position:"absolute", top: (offset + index) * rowHeight, height: rowHeight}}
            className={"grid w-full items-center gap-x-2 border-b border-slate-100 px-2 text-left text-xs hover:bg-blue-50 focus-visible:bg-blue-50 " +
              (narrow ? "grid-cols-1 content-center" : "grid-cols-[42%_minmax(0,1fr)]")}>
            <span className="relative truncate">{starts[offset + index] && <span data-testid="bar-group-separator" aria-hidden
              className="absolute -top-1.5 left-0 rounded bg-slate-100 px-1 text-[9px] font-semibold leading-3 text-slate-600">{item.group}</span>}
              {item.label}</span>
            <span className="relative h-6 min-w-0">
              <span aria-hidden className="absolute inset-y-0 border-l border-slate-300" style={{left: zero + "%"}}/>
              {mark !== null && <span aria-hidden data-testid="bar-reference-mark" className="absolute inset-y-0 border-l-[1.5px] border-dashed border-ink"
                style={{left: mark + "%"}}/>}
              {value !== null && <span aria-hidden data-testid="bar-fill" className="absolute top-1 h-4 rounded-sm"
                style={{left: Math.min(zero, end) + "%", width: Math.abs(end - zero) + "%", background: item.highlighted ? CATEGORICAL[0] : "#9ec5f4"}}/>}
              <span data-testid="bar-value" className={"absolute top-1 z-[1] whitespace-nowrap rounded-sm px-1 text-[10px] leading-4 " +
                (inside ? (item.highlighted ? "text-white" : "text-ink") : "bg-white text-slate-800")}
                style={inside ? { right: (100 - tip) + "%" } : { left: "calc(" + tip + "% + 2px)" }}>
                {value === null ? "Não avaliável" : formatNumber(value, kind)}</span>
            </span>
          </button>;
        })}
      </div>
    </div>
    <ReferenceCaption reference={reference}/>
  </figure>;
}

export function CountBars({ data, title, note }: { data: CountDatum[]; title: string; note: string }) {
  return <figure aria-label={title} className="w-full">
    <div className="h-[200px] w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }} barCategoryGap={8}>
        <CartesianGrid vertical={false} stroke={INK.grid}/>
        <XAxis dataKey="label" tick={{ ...axis, fill: INK.secondary }} interval={0} stroke={INK.grid}/>
        <YAxis allowDecimals={false} tick={axis} width={52} stroke={INK.grid} tickFormatter={(value: number) => formatNumber(value, "CONTAGEM")}/>
        <Tooltip cursor={{ fill: "rgba(42,120,214,0.06)" }} wrapperStyle={{ maxWidth: "calc(100% - 40px)" }} content={({ active, payload }) => {
          const item = active && payload?.[0]?.payload as CountDatum | undefined;
          return item ? <TooltipBox title={item.label} lines={[{ strong: formatNumber(item.value, "CONTAGEM"), text: " territórios" }]}/> : null;
        }}/>
        <Bar dataKey="value" name={title} radius={[4, 4, 0, 0]} maxBarSize={56}>
          {data.map(item => <Cell key={item.label} fill={item.color}/>)}
        </Bar>
      </BarChart>
    </ResponsiveContainer></div>
    <figcaption className="mt-1 text-xs text-slate-600">{note}</figcaption>
  </figure>;
}

export function SeriesLines({ points, series, unit, kind, title }: { points: LinePoint[];
  series: { key: string; label: string; color: string; pointsOnly?: boolean; dashed?: boolean }[]; unit: string; kind: IndicatorKind; title: string }) {
  // Eixo em números redondos ao redor dos valores: uma série de densidade entre 1,6 e 1,9 deixa de virar uma
  // linha achatada sobre o zero. O começo do eixo é informado na legenda quando não é zero.
  const domain = niceDomain(points.flatMap(point => series.map(item => point[item.key])).filter((value): value is number => typeof value === "number"));
  const last = Object.fromEntries(series.map(item => [item.key,
    points.reduce((found, point, index) => typeof point[item.key] === "number" ? index : found, -1)]));
  const labeled = series.length <= 4;  // rótulo direto só no último valor de cada série (seletivo)
  return <figure aria-label={title} className="w-full">
    <div className="h-[300px] w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
      <LineChart data={points} margin={{ top: 12, right: labeled ? 52 : 16, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} stroke={INK.grid}/>
        <XAxis dataKey="periodo" tick={axis} tickFormatter={(value: string) => displayPeriod(value)} stroke={INK.grid} minTickGap={12}/>
        <YAxis tick={axis} width={64} stroke={INK.grid} domain={domain} tickCount={5} allowDecimals={kind !== "CONTAGEM"}
          tickFormatter={(value: number) => formatNumber(value, kind)}
          label={{ value: unit, angle: -90, position: "insideLeft", style: { fontSize: 11, fill: INK.muted } }}/>
        <Tooltip wrapperStyle={{ maxWidth: "calc(100% - 40px)" }} content={({ active, payload, label }) => active && payload?.length ?
          <TooltipBox title={displayPeriod(String(label))} lines={series.map(item => {
            const value = payload.find(entry => entry.dataKey === item.key)?.value as number | null | undefined;
            return { color: item.color, strong: value === null || value === undefined ? "sem valor" : formatNumber(value, kind), text: " " + item.label };
          })}/> : null}/>
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11, color: INK.secondary }} iconType="plainline"/>}
        {/* Sem trajetória (tendência não comparável, `serie.quebras`): só os pontos de cada competência, sem linha entre eles. */}
        {series.map(item => <Line key={item.key} type="linear" dataKey={item.key} name={item.label} stroke={item.pointsOnly ? "none" : item.color}
          strokeWidth={item.pointsOnly ? 0 : 2} strokeDasharray={item.dashed ? "6 4" : undefined}
          dot={{ r: 4, fill: item.color, stroke: INK.surface, strokeWidth: 2 }} activeDot={{ r: 6, stroke: INK.surface, strokeWidth: 2 }}
          connectNulls={false} isAnimationActive={false}
          label={labeled ? (props: { x?: number; y?: number; index?: number; value?: number }) =>
            props.index === last[item.key] && typeof props.value === "number"
              ? <text x={(props.x ?? 0) + 9} y={(props.y ?? 0) + 4} fontSize={11} fontWeight={600} fill={INK.primary}>{formatNumber(props.value, kind)}</text>
              : <g/> : undefined}/>)}
      </LineChart>
    </ResponsiveContainer></div>
    <figcaption className="mt-1 text-xs text-slate-600">{series.length === 1 ? series[0].label + ". " : ""}Competências sem valor aparecem
      como lacunas; não há interpolação, linha de tendência ou taxa calculada pela representação.
      {series.some(item => item.pointsOnly) ? " Territórios com série não comparável aparecem só como pontos, sem linha de trajetória." : ""}
      {series.some(item => item.dashed) ? " Linha tracejada: " + series.filter(item => item.dashed).map(item => item.label).join(", ") +
        " (Brasil, total nacional): contexto lado a lado; não classifica os territórios nem entra em relação com eles." : ""}
      {domain[0] > 0 ? " O eixo vertical começa em " + formatNumber(domain[0], kind) + " para mostrar a variação; os valores são os do motor." : ""}</figcaption>
  </figure>;
}

export const stateColor = (state: string) => state === "NAO_AVALIAVEL" || state === "Não avaliável" ? NOT_EVALUABLE : undefined;
import { useMemo, useState } from "react";
import { useNarrow } from "./useNarrow";
