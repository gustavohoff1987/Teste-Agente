import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";

export type ChatFeature<T extends string> = {
  id: T; title: string; detail: string; icon: LucideIcon; tone: string;
};

type Props<T extends string> = {
  features: ChatFeature<T>[];
  selected: T | null;
  disabled: boolean;
  onSelect: (id: T) => void;
};

/** Carrossel compacto de uma análise por vez, integrado à primeira mensagem. */
export default function ChatAnalysisCarousel<T extends string>({
  features, selected, disabled, onSelect,
}: Props<T>) {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const found = features.findIndex(feature => feature.id === selected);
    if (found !== -1) setIndex(found);
  }, [selected, features]);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  if (!features.length) return null;
  const feature = features[Math.min(index, features.length - 1)];
  const Icon = feature.icon;
  const isSelected = selected === feature.id;
  const move = (delta: number) =>
    setIndex(current => Math.max(0, Math.min(features.length - 1, current + delta)));
  return <div id="analises" aria-label="Tipos de análise" className="section-anchor mt-3 w-full max-w-[520px] rounded-xl border border-blue-100 bg-white p-3 shadow-sm">
    <div className="mb-3 flex items-center justify-between gap-3">
      <span className="text-[11px] font-semibold text-slate-600">Escolha uma análise</span>
      <span className="text-[11px] font-semibold tabular-nums text-slate-500">{index + 1} de {features.length}</span>
    </div>
    <div role="group" aria-label="Carrossel de tipos de análise" className="flex items-center gap-2"
      onTouchStart={event => setTouchStart(event.touches[0]?.clientX ?? null)}
      onTouchEnd={event => {
        if (touchStart === null) return;
        const delta = (event.changedTouches[0]?.clientX ?? touchStart) - touchStart;
        if (Math.abs(delta) >= 45) move(delta < 0 ? 1 : -1);
        setTouchStart(null);
      }}>
      <button type="button" onClick={() => move(-1)} disabled={index === 0}
        aria-label="Análise anterior" className="shrink-0 rounded-lg border border-line bg-white p-2 text-teal hover:bg-blue-50 disabled:opacity-30">
        <ChevronLeft size={19}/>
      </button>
      <button type="button" onClick={() => onSelect(feature.id)} disabled={disabled}
        aria-label={"Selecionar análise: " + feature.title} aria-pressed={isSelected}
        className={"flex min-h-[88px] min-w-0 flex-1 items-center gap-3 rounded-xl border p-3 text-left transition hover:border-cyan-500 disabled:opacity-50 " +
          (isSelected ? "border-cyan-500 bg-cyan-50" : "border-line bg-slate-50/70")}>
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white text-teal shadow-sm"><Icon size={24}/></span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-bold text-ink">{feature.title}</span>
          <span className="mt-1 block text-[11px] leading-4 text-slate-600">{feature.detail}</span>
          <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-teal">
            {isSelected ? "Análise selecionada · ver preparação" : "Selecionar e preparar"} <ArrowRight size={12}/>
          </span>
        </span>
      </button>
      <button type="button" onClick={() => move(1)} disabled={index >= features.length - 1}
        aria-label="Próxima análise" className="shrink-0 rounded-lg border border-line bg-white p-2 text-teal hover:bg-blue-50 disabled:opacity-30">
        <ChevronRight size={19}/>
      </button>
    </div>
  </div>;
}
