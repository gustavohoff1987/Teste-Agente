import { useMemo } from "react";
import { INK, displayPeriod, formatNumber, fullPrecision } from "./representation";
import { kpiView, sparkGeometry, summaryOf, summaryParts, type Formatters, type KpiView } from "./headerModel";

// Cabeçalho do resultado (D7): frase-resumo, indicadores (KPIs) e procedência, todos do motor
// (metadata.representacao.resumo). Substitui a grade genérica de métricas; resultados antigos sem resumo mantêm a grade.

type Metric = { label: string; value: string | number };
type Props = { result: { metadata: Record<string, unknown>; metrics: Metric[] } & Record<string, unknown> };

const FORMAT: Formatters = { number: (value, kind) => formatNumber(value, kind || "CONTINUO"), period: displayPeriod };
// Grade de antes (resultados sem resumo): o mesmo formato de então.
const pretty = (value: unknown) => value === null || value === undefined ? "Não avaliável" : typeof value === "number"
  ? new Intl.NumberFormat("pt-BR", value !== 0 && Math.abs(value) < 1e-6 ? { notation: "scientific", maximumSignificantDigits: 8 }
    : { maximumFractionDigits: 6 }).format(value) : String(value);

export default function ResultHeader({ result }: Props) {
  const summary = useMemo(() => summaryOf(result.metadata), [result]);
  const parts = useMemo(() => summary ? summaryParts(summary, result, FORMAT) : [], [summary, result]);
  const kpis = useMemo(() => summary ? summary.indicadores.map(item => kpiView(item, result, FORMAT)) : [], [summary, result]);
  if (!summary) return result.metrics.length > 0 ? <div data-testid="result-metrics" className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    {result.metrics.map(metric => <div key={metric.label} className="rounded-2xl border border-line bg-slate-50 px-5 py-5">
      <p className="text-xs font-medium text-slate-500">{metric.label}</p>
      <p className="mt-2 text-2xl font-bold text-ink">{pretty(metric.value)}</p></div>)}
  </div> : null;
  return <section aria-label="Resumo do resultado" data-testid="result-header" className="mt-4 space-y-3">
    <p data-testid="result-summary" className="rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3 text-sm leading-6 text-slate-800">
      {parts.map((part, index) => part.value && part.kind !== "RELACAO"
        ? <strong key={index} className="font-semibold text-ink">{part.text}</strong> : <span key={index}>{part.text}</span>)}
    </p>
    {kpis.length > 0 && <div data-testid="result-kpis" role="list" aria-label="Indicadores do resultado"
      className="grid items-start gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {kpis.map((item, index) => <KpiCard key={index} item={item}/>)}
    </div>}
    {summary.procedencia.length > 0 && <ul data-testid="result-provenance" aria-label="Procedência do resultado"
      className="flex flex-wrap gap-1.5 text-[11px] leading-4 text-slate-600">
      {summary.procedencia.map(item => <li key={item.rotulo} className="max-w-full break-words rounded-full border border-line bg-white px-2.5 py-1">
        <span className="font-semibold text-slate-700">{item.rotulo}:</span> {item.valor}</li>)}
    </ul>}
  </section>;
}

function KpiCard({ item }: { item: KpiView }) {
  return <div role="listitem" data-testid="result-kpi" data-nivel={item.level || undefined} data-papel={item.context ? "REFERENCIA_DE_CONTEXTO" : undefined}
    className={"min-w-0 rounded-2xl border px-4 py-3 " + (item.context ? "border-dashed border-slate-400 bg-white" : "border-line bg-slate-50")}>
    <p className="flex flex-wrap items-center gap-1.5 text-xs font-medium text-slate-600">
      <span className="min-w-0 break-words">{item.label}</span>
      {item.context && <span className="rounded-full border border-slate-300 px-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">contexto</span>}
    </p>
    <p className="mt-1 flex flex-wrap items-baseline gap-x-1.5 text-2xl font-bold text-ink">
      <span title={item.full !== null ? "Valor do motor em precisão integral: " + fullPrecision(item.full) : undefined}>{item.value}</span>
      {item.unit && <span className="text-xs font-normal text-slate-600">{item.unit}</span>}
    </p>
    {item.period && <p className="text-[11px] text-slate-500">em {displayPeriod(item.period)} (última competência avaliável da série)</p>}
    {item.context && <p className="text-[11px] leading-4 text-slate-500">Referência de contexto: não classifica nem colore os territórios.</p>}
    {item.spark && <Sparkline item={item}/>}
  </div>;
}

function Sparkline({ item }: { item: KpiView }) {
  const points = item.spark!;
  const width = 200, height = 40;
  const { segments, dots, domain } = sparkGeometry(points, width, height);
  const last = dots[dots.length - 1];
  const gaps = points.filter(point => point.value === null).map(point => displayPeriod(point.period));
  const text = item.label + ": " + points.length + " competências, de " + displayPeriod(points[0].period) + " a " +
    displayPeriod(points[points.length - 1].period) + "; de " + formatNumber(domain[0], item.kind) + " a " + formatNumber(domain[1], item.kind) +
    (item.unit ? " " + item.unit : "") + (gaps.length ? "; sem valor em " + gaps.join(", ") : "") + ".";
  return <figure data-testid="kpi-sparkline" data-points={points.length} className="mt-2">
    <svg role="img" aria-label={text} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="block h-10 w-full overflow-visible">
      {segments.map((segment, index) => segment.length > 1
        ? <polyline key={index} points={segment.map(point => point.join(",")).join(" ")} fill="none" stroke={INK.secondary} strokeWidth="1.5"
          strokeDasharray={item.context ? "4 2" : undefined} vectorEffect="non-scaling-stroke"/> : null)}
      {dots.map((dot, index) => <circle key={index} cx={dot.x} cy={dot.y} r={dot === last ? 2.8 : 1.6}
        fill={dot === last ? INK.primary : INK.secondary}><title>{displayPeriod(dot.period)}: {formatNumber(dot.value, item.kind)}{item.unit ? " " + item.unit : ""}</title></circle>)}
    </svg>
    <figcaption className="text-[10px] text-slate-500">{displayPeriod(points[0].period)} a {displayPeriod(points[points.length - 1].period)}
      {gaps.length ? " · lacuna sem valor em " + gaps.join(", ") : ""}</figcaption>
  </figure>;
}
