import {useMemo, useState} from "react";

export type Territory = {id: string; name: string; code: string; label: string;
  state: string; state_name: string; parents: string[]; selection_reason?: string;
  /** Base oficial: prefixo IBGE do estado (regra brasil-cod-uf-prefix-1) e nota quando a UF declarada na fonte diverge. */
  state_code?: string; hierarchy_note?: string};
const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

// Alvos e referências usam o mesmo controle com rótulos e cores distintos (azul e âmbar).
const TONES = {
  blue: {box: "border-blue-100 bg-blue-50/40", hover: "hover:bg-blue-50", chip: "border-blue-200"},
  amber: {box: "border-amber-300 bg-amber-50/60", hover: "hover:bg-amber-50", chip: "border-amber-300"},
};

export default function TerritorialSelection({items, selected, onChange, disabled, reason,
  label = "Seleção territorial compartilhada", title = "Municípios e territórios selecionados",
  description = "Use este conjunto nas próximas análises. Cada resultado preserva seu próprio recorte.", tone = "blue",
  listLabel = "Seleção atual", embedded = false}: {
  items: Territory[]; selected: string[]; onChange: (ids: string[]) => void; disabled: boolean; reason?: string;
  label?: string; title?: string; description?: string; tone?: keyof typeof TONES; listLabel?: string;
  /** Dentro de outro quadro (caixa "Abrangência territorial" das configurações): sem moldura própria. */
  embedded?: boolean;
}) {
  const colors = TONES[tone];
  const [query, setQuery] = useState("");
  const [state, setState] = useState("");
  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const states = useMemo(() => [...new Set(items.map(item => item.state_name).filter(Boolean))].sort(), [items]);
  const matches = useMemo(() => items.filter(item => (!state || item.state_name === state) &&
    normalize([item.label, item.state, item.state_name, ...item.parents].join(" ")).includes(normalize(query))), [items, query, state]);
  const toggle = (id: string) => onChange(selectedSet.has(id) ? selected.filter(value => value !== id) : [...selected, id]);
  return <section aria-label={label} className={"no-print min-w-0 " + (embedded ? "" : "my-4 rounded-2xl border " + colors.box + " p-4")}>
    <h3 className="text-sm font-semibold text-ink">{title}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{description}</p>
    <div className="mt-3 flex flex-wrap gap-2">
      <label className="min-w-[min(12rem,100%)] flex-1 text-xs">Pesquisar por nome ou código
        <input type="search" value={query} onChange={e=>setQuery(e.target.value)} disabled={disabled}
          className="mt-1 block w-full rounded-lg border border-line bg-white px-3 py-2 text-sm"/>
      </label>
      {!!states.length && <label className="max-w-full text-xs">Estado derivado do código
        <select value={state} onChange={e=>setState(e.target.value)} disabled={disabled}
          className="mt-1 block max-w-full rounded-lg border border-line bg-white px-3 py-2 text-sm">
          <option value="">Todos os estados</option>{states.map(value=><option key={value}>{value}</option>)}
        </select>
      </label>}
    </div>
    {!items.length && <p role="status" className="mt-3 text-xs">{reason || "Escolha a coluna territorial (e o código, se houver) para habilitar a seleção."}</p>}
    {(query || state) && <div className="mt-3 space-y-2">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span role="status">{matches.length} correspondências · até 40 exibidas</span>
        {!!matches.length && <button type="button" disabled={disabled} className="rounded-md border bg-white px-2 py-2 font-semibold text-teal disabled:opacity-40"
          onClick={()=>onChange([...new Set([...selected, ...matches.filter(item=>!item.selection_reason).map(item=>item.id)])])}>Adicionar todas as correspondências válidas</button>}
      </div>
      <div className="max-h-52 overflow-y-auto rounded-lg border border-line bg-white p-2">
        {matches.slice(0,40).map(item=><label key={item.id} className={"flex min-h-10 cursor-pointer items-center gap-2 rounded px-2 py-2 text-xs " + colors.hover}>
          <input type="checkbox" checked={selectedSet.has(item.id)} disabled={disabled || !!item.selection_reason} onChange={()=>toggle(item.id)}/>
          <span>{item.label}{item.state ? " · " + item.state : item.parents.length ? " · " + item.parents.join(" / ") : ""}
            {item.selection_reason && <span className="block text-amber-800">{item.selection_reason}</span>}</span>
        </label>)}
      </div>
    </div>}
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
      <strong aria-live="polite">{selected.length} selecionados</strong>
      {!!selected.length && <button type="button" disabled={disabled} onClick={()=>onChange([])}
        className="min-h-9 rounded-lg border bg-white px-3 text-teal disabled:opacity-40">Limpar seleção</button>}
    </div>
    {!!selected.length && <ul aria-label={listLabel} className="mt-2 flex max-h-44 flex-wrap gap-2 overflow-y-auto">
      {selected.map(id=>{
        const item = items.find(value=>value.id===id);
        return <li key={id} className={"flex max-w-full items-center gap-1 rounded-lg border " + colors.chip + " bg-white pl-2 text-xs"}>
          <span className="break-words">{item?.label || id}</span>
          <button type="button" disabled={disabled} onClick={()=>toggle(id)} aria-label={"Remover " + (item?.label || id)}
            className={"min-h-10 min-w-10 rounded-r-lg text-lg text-slate-500 " + colors.hover}>×</button>
        </li>;
      })}
    </ul>}
  </section>;
}
