import { useEffect, useRef } from "react";
import { Clock3, ChevronDown } from "lucide-react";
import { displayPeriod } from "./DistributionResults";

// Resultados existentes na memória desta sessão: navegação apenas visual.
// Não altera a fonte, os parâmetros nem dispara outra análise.
export type PreviousAnalysis = {
  id: string;
  title: string;
  request: string;
  periods: string[];
  availableForReuse: boolean;
  context?: string;
};

type Props = {
  items: PreviousAnalysis[];
  currentId: string | null;
  disabled: boolean;
  onOpen: (id: string) => void;
};

export default function PreviousAnalyses({ items, currentId, disabled, onOpen }: Props) {
  const menuRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    function outside(event: PointerEvent) {
      if (menuRef.current?.open && !menuRef.current.contains(event.target as Node)) menuRef.current.open = false;
    }
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape" && menuRef.current?.open) {
        menuRef.current.open = false;
        menuRef.current.querySelector("summary")?.focus();
      }
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, []);
  return <section aria-label="Histórico de análises" className="no-print">
    <details data-testid="analysis-history-menu" ref={menuRef} className="history-menu group overflow-hidden rounded-xl border border-line bg-white">
      <summary className="flex cursor-pointer list-none items-center gap-2.5 px-4 py-3 text-sm font-semibold text-ink marker:hidden hover:bg-slate-50 [&::-webkit-details-marker]:hidden">
        <Clock3 size={17} className="shrink-0 text-teal" aria-hidden="true"/>
        <span>Histórico de análises</span>
        <span className="ml-auto text-xs font-normal text-slate-500">{items.length} {items.length === 1 ? "análise" : "análises"} nesta sessão</span>
        <ChevronDown size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-180" aria-hidden="true"/>
      </summary>
      <div className="history-list border-t border-line bg-white px-4 py-3 shadow-lg">
        {!items.length && <p className="mb-2 text-xs text-slate-600">O histórico será preenchido após o primeiro cálculo.</p>}
        <p className="mb-3 text-xs text-slate-500">
          Reabra uma análise desta sessão sem refazer os cálculos. Os resultados não ficam salvos quando a página é recarregada.
        </p>
        <nav aria-label="Abrir análises desta sessão">
          <ol className="max-h-72 space-y-2 overflow-y-auto">
            {[...items].reverse().map(item => {
              const current = item.id === currentId;
              const period = item.periods.length === 1 ? displayPeriod(item.periods[0])
                : item.periods.length > 1 ? item.periods.length + " períodos" : "";
              return <li key={item.id}>
                <button type="button" disabled={disabled || current} aria-current={current ? "true" : undefined}
                  aria-label={"Abrir análise: " + item.title} onClick={() => { onOpen(item.id); if (menuRef.current) menuRef.current.open = false; }}
                  className={"w-full rounded-lg border px-3 py-2.5 text-left transition-colors disabled:cursor-default " +
                    (current ? "border-blue-200 bg-blue-50" : "border-line bg-white hover:border-blue-200 hover:bg-slate-50")}>
                  <span className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-ink">{item.title}</span>
                    {current && <span className="text-xs font-semibold text-teal">Em exibição</span>}
                  </span>
                  <span className="mt-1 block truncate text-xs text-slate-600">{item.request}</span>
                  {item.context && <span className="mt-1 block text-xs text-slate-500">{item.context}</span>}
                  {(period || !item.availableForReuse) && <span className="mt-1 block text-xs text-slate-500">
                    {period}{period && !item.availableForReuse ? " · " : ""}
                    {!item.availableForReuse ? "Outra fonte de dados — somente consulta" : ""}
                  </span>}
                </button>
              </li>;
            })}
          </ol>
        </nav>
      </div>
    </details>
  </section>;
}
