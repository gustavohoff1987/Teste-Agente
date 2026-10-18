import {useState} from "react";
import {Check, ChevronDown} from "lucide-react";
import {chronological, describePeriods, periodRange, readablePeriod} from "./periods";

type Props = {
  periods: string[];
  value: string;
  selected: string[];
  multiple: boolean;
  onSingle: (period: string) => void;
  onMultiple: (periods: string[]) => void;
  allowMultiple: boolean;
};
export default function PeriodSelection(p: Props) {
  const [expanded, setExpanded] = useState(false);
  const multiple = p.multiple;
  const periods = chronological(p.periods);
  const ordered = chronological(p.selected.filter(item => periods.includes(item)));
  const chooseRange = (first: string, last: string) => {
    const range = periodRange(periods, first, last);
    if (range.length) p.onMultiple(range);
  };
  const toggleMode = () => {
    if (!p.allowMultiple) return;
    if (multiple) {
      p.onSingle(p.selected[0] || p.value || "");
    } else {
      // onMultiple é a transição atômica; o componente pai já limpa o período único.
      p.onMultiple(p.value ? [p.value] : periods);
    }
    setExpanded(true);
  };
  const values = multiple ? p.selected : p.value ? [p.value] : [];
  const description = !values.length
    ? multiple ? "Escolher períodos" : "Escolher período"
    : multiple ? (values.length === periods.length ? "Todos os períodos (" + periods.length + ")"
      : values.length + " de " + periods.length + " períodos") : readablePeriod(values[0]);
  const select = "min-w-0 rounded-md border border-line bg-white px-2 py-1 text-xs";
  return <div className="mt-2 space-y-2">
    <div className="flex flex-wrap items-center gap-2">
      <details className="relative max-w-full" open={expanded} onToggle={e=>setExpanded(e.currentTarget.open)}>
        <summary aria-label="Escolher períodos da análise"
          className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-semibold text-teal">
          {description} <ChevronDown size={14}/>
        </summary>
        <div className="mt-2 max-h-80 min-w-[230px] max-w-full overflow-y-auto rounded-lg border border-line bg-white p-3 shadow-sm">
          {multiple && <div className="mb-3 flex flex-wrap items-center gap-2 text-xs" role="group" aria-label="Intervalo de períodos">
            <span className="font-semibold text-ink">Intervalo:</span>
            <label className="flex items-center gap-1">de
              <select aria-label="Início do intervalo" className={select} value={ordered[0] || ""}
                onChange={e => chooseRange(e.target.value, ordered[ordered.length - 1] || periods[periods.length - 1])}>
                {!ordered.length && <option value="">escolher</option>}
                {periods.map(item => <option key={item} value={item}>{readablePeriod(item)}</option>)}
              </select></label>
            <label className="flex items-center gap-1">até
              <select aria-label="Fim do intervalo" className={select} value={ordered[ordered.length - 1] || ""}
                onChange={e => chooseRange(ordered[0] || periods[0], e.target.value)}>
                {!ordered.length && <option value="">escolher</option>}
                {periods.map(item => <option key={item} value={item}>{readablePeriod(item)}</option>)}
              </select></label>
            <button type="button" className="font-semibold text-teal underline" onClick={()=>p.onMultiple(periods)}>Todos os períodos disponíveis</button>
            <button type="button" className="font-semibold text-teal underline" disabled={!p.selected.length} onClick={()=>p.onMultiple([])}>Limpar</button>
          </div>}
          {multiple && <p className="mb-2 text-xs text-slate-600">Ou clique em cada competência para incluí-la ou retirá-la:</p>}
          <div className="flex flex-wrap gap-1.5">
            {periods.map(period => {
              const chosen = values.includes(period);
              return <button key={period} type="button" aria-pressed={chosen}
                onClick={() => {
                  if (multiple) p.onMultiple(chosen ? p.selected.filter(x=>x!==period) : [...p.selected,period]);
                  else {p.onSingle(period);setExpanded(false);}
                }}
                className={"inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition " +
                  (chosen ? "border-blue-700 bg-blue-700 font-semibold text-white" : "border-dashed border-slate-300 bg-white text-slate-700 hover:bg-slate-50")}>
                {multiple && chosen && <Check size={12} aria-hidden="true"/>}{readablePeriod(period)}
              </button>;
            })}
          </div>
          {multiple && <p data-testid="period-range-summary" className="mt-2 text-xs text-slate-700">
            Selecionadas: {describePeriods(p.selected, periods)}.</p>}
        </div>
      </details>
      {p.allowMultiple && <button type="button" className="text-xs text-teal underline"
        onClick={toggleMode}>{multiple ? "Escolher apenas um" : "Selecionar vários períodos"}</button>}
    </div>
    {multiple && <p className="text-xs text-slate-600">Os períodos escolhidos serão analisados separadamente;
      não somarei pessoas de competências diferentes como se fossem indivíduos únicos.</p>}
  </div>;
}
