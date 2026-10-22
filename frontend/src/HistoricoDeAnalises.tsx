import { useEffect, useRef } from "react";
import { ChevronDown, Clock3 } from "lucide-react";

// Histórico da página única (22/10/2026): as análises desta sessão, cada uma no último estado guardado pela área de análise.
// Reabrir uma análise devolve o gráfico como estava, sem recalcular. Uma análise feita com outra fonte de dados fica na lista,
// mas só reabre com aquela fonte. Fecha com clique fora ou Escape. Nada fica salvo quando a página é recarregada.

export type ItemDoHistorico = { id: number; titulo: string; quando: string; fonte: string; mesmaFonte: boolean; emExibicao: boolean };
type Props = { itens: ItemDoHistorico[]; desabilitado: boolean; onAbrir: (id: number) => void };

export default function HistoricoDeAnalises({ itens, desabilitado, onAbrir }: Props) {
  const menu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    function fora(event: PointerEvent) {
      if (menu.current?.open && !menu.current.contains(event.target as Node)) menu.current.open = false;
    }
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape" && menu.current?.open) {
        menu.current.open = false;
        menu.current.querySelector("summary")?.focus();
      }
    }
    document.addEventListener("pointerdown", fora);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", fora); document.removeEventListener("keydown", escape); };
  }, []);
  const total = itens.length;
  return <section aria-label="Histórico de análises" className="no-print">
    <details data-testid="analysis-history-menu" ref={menu} className="history-menu group">
      <summary data-testid="nav-history">
        <Clock3 size={18} aria-hidden="true"/>
        <span>Histórico</span>
        {total > 0 && <span className="historico-contagem" aria-hidden="true">{total}</span>}
        <span className="sr-only">{total} {total === 1 ? "análise" : "análises"} nesta sessão</span>
        <ChevronDown size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-180" aria-hidden="true"/>
      </summary>
      <div className="history-list bg-white px-4 py-3">
        <p className="mb-3 text-xs leading-5 text-slate-600" data-testid="historico-orientacao">
          {total ? "Reabra uma análise desta sessão como estava, sem refazer os cálculos."
            : "O Histórico guarda as análises desta sessão. Ele começa quando o gráfico mostra os primeiros valores."}
          {" "}Nada fica salvo quando a página é recarregada.</p>
        {total > 0 && <nav aria-label="Abrir análises desta sessão">
          <ol className="max-h-72 space-y-2 overflow-y-auto">
            {[...itens].reverse().map(item => <li key={item.id}>
              <button type="button" data-testid="historico-item" data-id={item.id}
                disabled={desabilitado || item.emExibicao || !item.mesmaFonte} aria-current={item.emExibicao ? "true" : undefined}
                aria-label={"Abrir análise: " + item.titulo}
                onClick={() => { onAbrir(item.id); if (menu.current) menu.current.open = false; }}
                className={"w-full rounded-lg border px-3 py-2.5 text-left transition-colors disabled:cursor-default " +
                  (item.emExibicao ? "border-blue-200 bg-blue-50" : "border-line bg-white hover:border-blue-200 hover:bg-slate-50")}>
                <span className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-ink">{item.titulo}</span>
                  {item.emExibicao && <span className="text-xs font-semibold text-teal">Em exibição</span>}
                </span>
                <span className="mt-1 block text-xs text-slate-500">{[item.quando, item.fonte].filter(Boolean).join(" · ")}</span>
                {!item.mesmaFonte && <span className="mt-1 block text-xs text-slate-500" data-testid="historico-outra-fonte">
                  Calculada com outra fonte de dados: troque a fonte para reabrir.</span>}
              </button>
            </li>)}
          </ol>
        </nav>}
      </div>
    </details>
  </section>;
}
