import { ArrowDownUp, ChevronsDown, ChevronsUp, CircleDashed, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { displayPeriod, formatNumber, INK, TREND_COLORS } from "./representation";
import {
  classOfLabel, countGroups, familyOfClass, NOT_EVALUABLE_CLASS, stageNote, velocityBars, type TrendFamily, type TrendMeta,
} from "./trend";

// Componentes da tendência do motor (CAP-TEN-01). Selos, contagens e velocidades só apresentam o que o motor
// entregou: sem classificação, contagem ou cálculo nesta camada. Cor pela família (sem juízo), sempre com texto e ícone.

const TONE: Record<TrendFamily, { text: string; background: string; border: string }> = {
  CRESCIMENTO: { text: "#1c5cab", background: "#eaf2fc", border: TREND_COLORS.CRESCIMENTO },
  DECLINIO: { text: "#a8431b", background: "#fdefe8", border: TREND_COLORS.DECLINIO },
  NENHUMA: { text: "#0b6b4a", background: "#e5f6ef", border: TREND_COLORS.NENHUMA },
  NAO_AVALIAVEL: { text: INK.secondary, background: "transparent", border: TREND_COLORS.NAO_AVALIAVEL },
};

function TrendIcon({ code, motive }: { code: string; motive?: string | null }) {
  const props = { size: 14, "aria-hidden": true, className: "shrink-0" } as const;
  if (code === NOT_EVALUABLE_CLASS) return <CircleDashed {...props}/>;
  if (code === "SEM_CLASSIFICACAO") return motive === "Série estável" || motive === "SERIE_ESTAVEL" ? <Minus {...props}/> : <ArrowDownUp {...props}/>;
  const growth = code.startsWith("CRESCIMENTO");
  return <>{growth ? <TrendingUp {...props}/> : <TrendingDown {...props}/>}
    {code.endsWith("_ACELERADO") ? <ChevronsUp {...props}/> : code.endsWith("_DESACELERADO") ? <ChevronsDown {...props}/> : null}</>;
}

/** Selo da classe de tendência: o texto é o rótulo do motor; o código vem de `metadata.tendencia.classes`. */
export function TrendBadge({ label, meta, motive, text, wrap = false }: { label: unknown; meta: TrendMeta; motive?: string | null; text?: string;
  /** Texto inteiro em mais de uma linha (contagem por classe); sem isso, uma linha com reticências e o texto no title. */
  wrap?: boolean }) {
  const code = classOfLabel(label, meta);
  if (!code) return <span>{label == null ? "Não avaliável" : String(label)}</span>;
  const family = familyOfClass(code, meta) || "NAO_AVALIAVEL";
  const tone = TONE[family];
  return <span data-testid="trend-badge" data-class={code} data-family={family}
    className={"inline-flex max-w-full items-center gap-1 border px-2 py-0.5 text-xs font-semibold " + (wrap ? "rounded-xl" : "rounded-full")}
    style={{ color: tone.text, background: tone.background, borderColor: tone.border, borderStyle: family === "NAO_AVALIAVEL" ? "dashed" : "solid" }}>
    <TrendIcon code={code} motive={motive}/><span className={wrap ? "min-w-0 break-words" : "truncate"} title={text ?? String(label)}>{text ?? String(label)}</span>
  </span>;
}

/** Contagem por classe na ordem da SPEC, agrupada por família; não avaliáveis à parte (AT-18). Números do motor. */
export function TrendCounts({ meta }: { meta: TrendMeta }) {
  const groups = countGroups(meta);
  const largest = Math.max(1, ...groups.flatMap(group => group.entries.map(entry => entry.value)));
  return <figure data-testid="trend-counts" aria-label="Territórios por classe de tendência" className="w-full">
    <div className="grid gap-x-8 gap-y-4 md:grid-cols-2">
      {groups.map(group => <div key={group.family} className="min-w-0">
        <p className="mb-1 text-xs font-semibold text-slate-600">{group.title}: {formatNumber(group.total, "CONTAGEM")}</p>
        {group.entries.map(entry => <div key={entry.key} data-testid="trend-count" data-key={entry.key} data-value={entry.value}
          className="my-1 grid grid-cols-[minmax(0,1fr)_3.5rem] items-center gap-x-2 gap-y-1 sm:grid-cols-[minmax(0,17rem)_minmax(0,1fr)_3.5rem]">
          <span className="min-w-0"><TrendBadge label={entry.code === NOT_EVALUABLE_CLASS ? entry.label : meta.classes.find(item => item.codigo === entry.code)?.rotulo}
            meta={meta} motive={entry.motive} text={entry.label} wrap/></span>
          <span aria-hidden className="order-3 col-span-2 h-2.5 overflow-hidden rounded bg-slate-100 sm:order-none sm:col-span-1">
            <span className="block h-full rounded-r" style={{ width: (entry.value ? Math.max(0.8, entry.value / largest * 100) : 0) + "%",
              background: TREND_COLORS[entry.family] }}/></span>
          <span className="text-right text-xs tabular-nums text-ink">{formatNumber(entry.value, "CONTAGEM")}</span>
        </div>)}
      </div>)}
    </div>
    <figcaption className="mt-2 text-xs text-slate-600">Contagens do motor ({meta.versao_metodo}; desfecho {meta.desfecho}). A ordem é a da
      SPEC, não um ranking. Sem classificação é resultado do método, não falta de dados; os não avaliáveis aparecem à parte.</figcaption>
  </figure>;
}

/** Minigráfico das velocidades do motor entre observações consecutivas: barras a partir do zero, sem linha ajustada. */
export function VelocityBars({ items, family, unit, timeUnit }: { items: { from: string; to: string; value: number }[];
  family: TrendFamily | null; unit: string; timeUnit: string }) {
  if (!items.length) return null;
  const width = 240, height = 48;
  const { baseline, bars } = velocityBars(items.map(item => item.value), width, height);
  const color = TREND_COLORS[family || "NAO_AVALIAVEL"];
  const describe = (item: { from: string; to: string; value: number }) => displayPeriod(item.from) + " → " + displayPeriod(item.to) + ": " +
    (item.value > 0 ? "+" : "") + formatNumber(item.value) + (unit ? " " + unit : "") + " por " + timeUnit;
  return <figure data-testid="trend-velocities" data-count={items.length} className="mt-2"
    aria-label={"Velocidades por " + timeUnit + " entre observações consecutivas"}>
    <svg role="img" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="block h-12 w-full overflow-visible">
      <line x1="0" x2={width} y1={baseline} y2={baseline} stroke={INK.grid}/>
      {bars.map((bar, index) => <rect key={index} x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx={bar.sign ? 1.5 : 0}
        fill={bar.sign ? color : INK.secondary} aria-label={describe(items[index])}><title>{describe(items[index])}</title></rect>)}
    </svg>
    <figcaption className="text-[11px] text-slate-500">Velocidade por {timeUnit} em cada intervalo, de {displayPeriod(items[0].from)} a{" "}
      {displayPeriod(items[items.length - 1].to)}; barras do motor, sem linha ajustada.</figcaption>
  </figure>;
}

/** Aviso da etapa (BLQ-MET com os textos do catálogo, ou RES-SCL). */
export function TrendStageNote({ meta }: { meta: TrendMeta }) {
  const text = stageNote(meta);
  if (!text) return null;
  return <p data-testid="trend-stage-note" role="status" data-outcome={meta.desfecho}
    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-700">{text}</p>;
}
