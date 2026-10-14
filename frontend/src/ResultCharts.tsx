import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CATEGORICAL, INK, NOT_EVALUABLE, displayPeriod, formatNumber, fullPrecision, type IndicatorKind } from "./representation";

// Gráficos de barras e de linhas (CAP-REP-02) sobre valores já calculados pelo motor. A ordem padrão
// é a do código territorial ou a do resultado de ordenação (RQ-REP-03); reordenar pelo valor é estado
// visual e não exibe posições. Ausências ficam como lacunas, sem interpolação nem linhas de tendência.

export type BarDatum = { id: string; label: string; value: number | null; highlighted: boolean };
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

export function TerritoryBars({ data, unit, kind, title, onSelect }: { data: BarDatum[]; unit: string; kind: IndicatorKind; title: string;
  onSelect: (id: string) => void }) {
  const height = Math.max(220, 46 + data.length * 26);
  return <figure aria-label={title} className="w-full">
    <div style={{ height }} className="w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 18, bottom: 4, left: 4 }} barCategoryGap={4}>
        <CartesianGrid horizontal={false} stroke={INK.grid}/>
        <XAxis type="number" tick={axis} tickFormatter={(value: number) => formatNumber(value, kind)} stroke={INK.grid}/>
        <YAxis type="category" dataKey="label" width={170} tick={{ ...axis, fill: INK.secondary }} interval={0} stroke={INK.grid}
          tickFormatter={(value: string) => value.length > 26 ? value.slice(0, 25) + "…" : value}/>
        <Tooltip cursor={{ fill: "rgba(42,120,214,0.06)" }} wrapperStyle={{ maxWidth: "calc(100% - 40px)" }} content={({ active, payload }) => {
          const item = active && payload?.[0]?.payload as BarDatum | undefined;
          return item ? <TooltipBox title={item.label} lines={[item.value === null ? { text: "Não avaliável (sem valor no resultado)" } :
            { strong: formatNumber(item.value, kind), text: " " + unit + " · valor integral " + fullPrecision(item.value) }]}/> : null;
        }}/>
        <Bar dataKey="value" name={title} radius={[0, 4, 4, 0]} maxBarSize={18} onClick={(entry: BarDatum) => onSelect(entry.id)} cursor="pointer">
          {data.map(item => <Cell key={item.id} fill={item.highlighted ? CATEGORICAL[0] : "#9ec5f4"}/>)}
        </Bar>
      </BarChart>
    </ResponsiveContainer></div>
    {data.some(item => item.value === null) && <figcaption className="mt-1 text-xs text-slate-600">
      Sem barra por não avaliabilidade (nunca convertida em zero): {data.filter(item => item.value === null).map(item => item.label).join("; ")}.
    </figcaption>}
  </figure>;
}

export function CountBars({ data, title, note }: { data: CountDatum[]; title: string; note: string }) {
  return <figure aria-label={title} className="w-full">
    <div className="h-[200px] w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }} barCategoryGap={8}>
        <CartesianGrid vertical={false} stroke={INK.grid}/>
        <XAxis dataKey="label" tick={{ ...axis, fill: INK.secondary }} interval={0} stroke={INK.grid}/>
        <YAxis allowDecimals={false} tick={axis} width={52} stroke={INK.grid} tickFormatter={(value: number) => formatNumber(value, "CONTAGEM")}/>
        <Tooltip cursor={{ fill: "rgba(42,120,214,0.06)" }} content={({ active, payload }) => {
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

export function SeriesLines({ points, series, unit, kind, title }: { points: LinePoint[]; series: { key: string; label: string; color: string }[];
  unit: string; kind: IndicatorKind; title: string }) {
  return <figure aria-label={title} className="w-full">
    <div className="h-[300px] w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
      <LineChart data={points} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} stroke={INK.grid}/>
        <XAxis dataKey="periodo" tick={axis} tickFormatter={(value: string) => displayPeriod(value)} stroke={INK.grid} minTickGap={12}/>
        <YAxis tick={axis} width={64} stroke={INK.grid} tickFormatter={(value: number) => formatNumber(value, kind)}
          label={{ value: unit, angle: -90, position: "insideLeft", style: { fontSize: 11, fill: INK.muted } }}/>
        <Tooltip wrapperStyle={{ maxWidth: "calc(100% - 40px)" }} content={({ active, payload, label }) => active && payload?.length ?
          <TooltipBox title={displayPeriod(String(label))} lines={series.map(item => {
            const value = payload.find(entry => entry.dataKey === item.key)?.value as number | null | undefined;
            return { color: item.color, strong: value === null || value === undefined ? "sem valor" : formatNumber(value, kind), text: " " + item.label };
          })}/> : null}/>
        <Legend wrapperStyle={{ fontSize: 11, color: INK.secondary }} iconType="plainline"/>
        {series.map(item => <Line key={item.key} type="linear" dataKey={item.key} name={item.label} stroke={item.color} strokeWidth={2}
          dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={false}/>)}
      </LineChart>
    </ResponsiveContainer></div>
    <figcaption className="mt-1 text-xs text-slate-600">Competências sem valor aparecem como lacunas; não há interpolação, linha de
      tendência ou taxa calculada pela representação.</figcaption>
  </figure>;
}

export const stateColor = (state: string) => state === "NAO_AVALIAVEL" || state === "Não avaliável" ? NOT_EVALUABLE : undefined;
