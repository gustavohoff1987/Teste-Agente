import type { LucideIcon } from "lucide-react";

type Props<T extends string> = { features: { id: T; title: string; description?: string; detail: string; icon: LucideIcon }[];
  active: T | null; onSelect: (operation: T) => void; disabled: boolean };

export default function AnalysisList<T extends string>({ features, active, onSelect, disabled }: Props<T>) {
  return <aside className="analysis-list-panel" aria-label="Seleção de análises">
    <h2 className="border-b border-line p-4 text-sm font-bold text-ink">Escolha a análise</h2>
    <div className="analysis-list-scroll p-2">
      {features.map(feature => <button key={feature.id} type="button" disabled={disabled}
        aria-label={"Selecionar análise: " + feature.title} aria-pressed={active === feature.id}
        onClick={() => onSelect(feature.id)} className={"mb-1 flex w-full items-start gap-3 rounded-xl border p-3 text-left disabled:opacity-50 " +
          (active === feature.id ? "border-teal bg-teal-50 text-teal" : "border-transparent text-slate-600 hover:bg-slate-50")}>
        <feature.icon size={20} className="mt-0.5 shrink-0"/>
        <span><strong className="block text-sm">{feature.title}</strong><span className="mt-1 block text-xs leading-4">{feature.detail}</span></span>
      </button>)}
    </div>
  </aside>;
}
