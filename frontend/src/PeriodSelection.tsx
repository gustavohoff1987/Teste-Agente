import {useState} from "react";
import {Check, ChevronDown} from "lucide-react";
import {chronological, clickPeriod, describePeriods, periodRange, readablePeriod} from "./periods";

type ChoicesProps = {
  periods: string[];
  value: string;
  selected: string[];
  multiple: boolean;
  onSingle: (period: string) => void;
  onMultiple: (periods: string[]) => void;
  allowMultiple: boolean;
  /** Enquanto outro recorte carrega, a escolha seria descartada ao chegar; a lista fica bloqueada. */
  disabled?: boolean;
  /** Chamado depois de escolher a competência no modo único (por exemplo, para recolher a lista). */
  onChosen?: () => void;
  /** Troca entre um e vários períodos dentro da própria lista (caixa "Período" das configurações). */
  modeToggle?: boolean;
  /** Aviso de que as competências são analisadas separadamente; a lista recolhível o mostra do lado de fora. */
  note?: boolean;
};

/** Texto da escolha atual, usado no gatilho da lista. */
export function periodChoiceLabel(periods: string[], value: string, selected: string[], multiple: boolean): string {
  const values = multiple ? selected : value ? [value] : [];
  if (!values.length) return multiple ? "Escolher períodos" : "Escolher período";
  return multiple ? (values.length === periods.length ? "Todos os períodos (" + periods.length + ")"
    : values.length + " de " + periods.length + " períodos") : readablePeriod(values[0]);
}

/** Lista de competências: intervalo, todos, limpar e um botão por competência. */
export function PeriodChoices(p: ChoicesProps) {
  // Todos os períodos incluídos é o padrão da análise, não uma escolha do usuário: até a primeira escolha
  // nesta lista, as competências aparecem sem marca e o clique escolhe só a clicada (orientação de 18/10/2026).
  // A escolha vale enquanto a seleção for a escolhida aqui; se ela mudar por fora (ex.: nova inspeção
  // que restaura todas as competências), o padrão volta.
  const [picked, setPicked] = useState<string[] | null>(null);
  const multiple = p.multiple;
  const periods = chronological(p.periods);
  const ordered = chronological(p.selected.filter(item => periods.includes(item)));
  const customized = !!picked && picked.length === p.selected.length && picked.every(item => p.selected.includes(item));
  const allByDefault = multiple && !customized && periods.length > 1 && ordered.length === periods.length;
  const pick = (next: string[]) => { setPicked(next); p.onMultiple(next); };
  const chooseRange = (first: string, last: string) => {
    const range = periodRange(periods, first, last);
    if (range.length) pick(range);
  };
  const toggleMode = () => {
    if (multiple) p.onSingle(p.selected[0] || p.value || "");
    else {
      // onMultiple é a transição atômica; o componente pai já limpa o período único.
      setPicked(null);
      p.onMultiple(p.value ? [p.value] : periods);
    }
  };
  const values = multiple ? p.selected : p.value ? [p.value] : [];
  const select = "min-w-0 rounded-md border border-line bg-white px-2 py-1 text-xs";
  return <div className="space-y-2">
    {p.modeToggle && p.allowMultiple && <button type="button" className="text-xs font-semibold text-teal underline disabled:opacity-50"
      disabled={p.disabled} onClick={toggleMode}>{multiple ? "Escolher apenas um" : "Selecionar vários períodos"}</button>}
    {multiple && <div className="flex flex-wrap items-center gap-2 text-xs" role="group" aria-label="Intervalo de períodos">
      <span className="font-semibold text-ink">Intervalo:</span>
      <label className="flex items-center gap-1">de
        <select aria-label="Início do intervalo" className={select} value={ordered[0] || ""} disabled={p.disabled}
          onChange={e => chooseRange(e.target.value, ordered[ordered.length - 1] || periods[periods.length - 1])}>
          {!ordered.length && <option value="">escolher</option>}
          {periods.map(item => <option key={item} value={item}>{readablePeriod(item)}</option>)}
        </select></label>
      <label className="flex items-center gap-1">até
        <select aria-label="Fim do intervalo" className={select} value={ordered[ordered.length - 1] || ""} disabled={p.disabled}
          onChange={e => chooseRange(ordered[0] || periods[0], e.target.value)}>
          {!ordered.length && <option value="">escolher</option>}
          {periods.map(item => <option key={item} value={item}>{readablePeriod(item)}</option>)}
        </select></label>
      <button type="button" className="font-semibold text-teal underline disabled:opacity-50" disabled={p.disabled} onClick={()=>pick(periods)}>Todos os períodos disponíveis</button>
      <button type="button" className="font-semibold text-teal underline disabled:opacity-50" disabled={p.disabled || !p.selected.length} onClick={()=>pick([])}>Limpar</button>
    </div>}
    {multiple && <p className="text-xs text-slate-600">{allByDefault
      ? "Todos os períodos estão incluídos. Para analisar só alguns, clique neles:"
      : "Ou clique em cada competência para incluí-la ou retirá-la:"}</p>}
    <div className="flex flex-wrap gap-1.5">
      {periods.map(period => {
        const chosen = !allByDefault && values.includes(period);
        return <button key={period} type="button" aria-pressed={chosen} disabled={p.disabled}
          onClick={() => {
            if (multiple) pick(clickPeriod(p.selected, period, allByDefault));
            else {p.onSingle(period); p.onChosen?.();}
          }}
          className={"inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition disabled:opacity-50 " +
            (chosen ? "border-blue-700 bg-blue-700 font-semibold text-white"
              : (allByDefault ? "" : "border-dashed ") + "border-slate-300 bg-white text-slate-700 hover:bg-slate-50")}>
          {multiple && chosen && <Check size={12} aria-hidden="true"/>}{readablePeriod(period)}
        </button>;
      })}
    </div>
    {multiple && <p data-testid="period-range-summary" className="text-xs text-slate-700">
      Selecionadas: {describePeriods(p.selected, periods)}.</p>}
    {multiple && p.note !== false && <SeparateNote/>}
  </div>;
}

function SeparateNote() {
  return <p className="text-xs text-slate-600">Os períodos escolhidos serão analisados separadamente;
    não somarei pessoas de competências diferentes como se fossem indivíduos únicos.</p>;
}

type Props = Omit<ChoicesProps, "onChosen" | "modeToggle" | "note">;
/** Lista recolhível usada nas bases importadas: o resumo abre as competências, e a troca de modo fica ao lado. */
export default function PeriodSelection(p: Props) {
  const [expanded, setExpanded] = useState(false);
  const toggleMode = () => {
    if (!p.allowMultiple) return;
    if (p.multiple) p.onSingle(p.selected[0] || p.value || "");
    else p.onMultiple(p.value ? [p.value] : chronological(p.periods));
    setExpanded(true);
  };
  return <div className="mt-2 space-y-2">
    <div className="flex flex-wrap items-center gap-2">
      <details className="relative max-w-full" open={expanded} onToggle={e=>setExpanded(e.currentTarget.open)}>
        <summary aria-label="Escolher períodos da análise"
          className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-semibold text-teal">
          {periodChoiceLabel(p.periods, p.value, p.selected, p.multiple)} <ChevronDown size={14}/>
        </summary>
        <div className="mt-2 max-h-80 min-w-[230px] max-w-full overflow-y-auto rounded-lg border border-line bg-white p-3 shadow-sm">
          {/* A troca de modo recomeça a lista: todos os períodos voltam a ser o padrão, ainda sem escolha. */}
          <PeriodChoices key={String(p.multiple)} {...p} note={false} onChosen={() => setExpanded(false)}/>
        </div>
      </details>
      {p.allowMultiple && <button type="button" className="text-xs text-teal underline disabled:opacity-50" disabled={p.disabled}
        onClick={toggleMode}>{p.multiple ? "Escolher apenas um" : "Selecionar vários períodos"}</button>}
    </div>
    {p.multiple && <SeparateNote/>}
  </div>;
}
