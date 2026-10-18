import {useState} from "react";
import {ChevronDown} from "lucide-react";

const months = ["janeiro","fevereiro","março","abril","maio","junho","julho",
  "agosto","setembro","outubro","novembro","dezembro"];

export function readablePeriod(value: string): string {
  const match = /^(\d{4})(\d{2})$/.exec(value);
  if (match) {
    const month = Number(match[2]);
    if (month >= 1 && month <= 12) return months[month - 1] + " de " + match[1];
  }
  return value;
}

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
  const [multiple, setMultiple] = useState(p.multiple);
  const periods = [...p.periods].sort((a,b) => a.localeCompare(b, "pt-BR", {numeric:true}));
  const toggleMode = () => {
    if (!p.allowMultiple) return;
    if (multiple) {
      setMultiple(false);
      p.onMultiple([]);
      p.onSingle("");
    } else {
      setMultiple(true);
      // onMultiple é a transição atômica; o componente pai já limpa o período único.
      p.onMultiple(periods);
    }
    setExpanded(true);
  };
  const values = multiple ? p.selected : p.value ? [p.value] : [];
  const description = !values.length
    ? multiple ? "Todos os períodos" : "Escolher período"
    : multiple ? (values.length === periods.length ? "Todos os períodos" : values.length + (values.length === 1 ? " período" : " períodos")) :
      readablePeriod(values[0]);
  return <div className="mt-2 space-y-2">
    <div className="flex flex-wrap items-center gap-2">
      <details className="relative max-w-full" open={expanded} onToggle={e=>setExpanded(e.currentTarget.open)}>
        <summary aria-label="Escolher períodos da análise"
          className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-semibold text-teal">
          {description} <ChevronDown size={14}/>
        </summary>
        <div className="mt-2 max-h-64 min-w-[230px] max-w-full overflow-y-auto rounded-lg border border-line bg-white p-2 shadow-sm">
          {multiple && <button type="button" className="mb-2 text-xs font-semibold text-teal underline"
            onClick={()=>p.onMultiple(periods)}>Todos os períodos disponíveis</button>}
          <div className="flex flex-wrap gap-1.5">
            {periods.map(period => {
              const chosen = values.includes(period);
              return <button key={period} type="button" aria-pressed={chosen}
                onClick={() => {
                  if (multiple) p.onMultiple(chosen ? p.selected.filter(x=>x!==period) : [...p.selected,period]);
                  else {p.onSingle(period);setExpanded(false);}
                }}
                className={"rounded-md border px-2 py-1 text-xs transition " +
                  (chosen ? "border-blue-500 bg-blue-100 font-semibold text-blue-900" : "border-slate-200 bg-white hover:bg-slate-50")}>
                {readablePeriod(period)}
              </button>;
            })}
          </div>
        </div>
      </details>
      {p.allowMultiple && <button type="button" className="text-xs text-teal underline"
        onClick={toggleMode}>{multiple ? "Escolher apenas um" : "Selecionar vários períodos"}</button>}
    </div>
    {multiple && <p className="text-xs text-slate-600">Os períodos escolhidos serão analisados separadamente;
      não somarei pessoas de competências diferentes como se fossem indivíduos únicos.</p>}
  </div>;
}
