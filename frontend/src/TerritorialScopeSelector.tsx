import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { Territory } from "./TerritorialSelection";
import {
  breakdown, countSelected, groupState, type Effective, type LevelRule, type Levels, type ScopeSelection, type Toggle, toggle,
} from "./territorialScope";

// Lista vertical da abrangência territorial da base oficial (D3): Brasil, estados e municípios agrupados por estado,
// com caixas de marcar nativas (Tab entre os controles, Espaço marca, botão abre cada grupo). Só organiza a escolha:
// o que cada análise aceita, o padrão e os motivos vêm do backend (bloco "niveis" da inspeção), que confere o pedido.

type Props = {
  levels: Levels;
  rule: LevelRule | undefined;
  /** Municípios da inspeção da base oficial (fonte municipal inteira). */
  items: Territory[];
  scope: ScopeSelection;
  ids: string[];
  effective: Effective | null;
  /** Resumo da caixa "Abrangência territorial" (o mesmo texto de scope-summary). */
  summary: string;
  onChange: (next: { scope: ScopeSelection; ids: string[] }) => void;
  onClear: () => void;
  disabled: boolean;
  loading: boolean;
  title: string;
  /** Escolha pendente informada pelo pré-exame (mistura de níveis ou mínimo de territórios). */
  pending?: string;
};

const ROW = "flex min-h-10 items-start gap-2 px-3 py-2";
const CHECK = "mt-0.5 h-4 w-4 shrink-0 accent-teal";
const REASON = "px-3 pb-2 text-xs leading-5 text-amber-900";
const LEGEND = "w-full border-b border-line bg-slate-50 px-3 py-1.5 text-xs font-bold text-ink";

function Badge() {
  return <span data-testid="territory-badge-padrao" className="ml-1 shrink-0 rounded-full bg-cyan-100 px-2 text-[11px] font-semibold text-cyan-900">
    padrão desta análise</span>;
}

export default function TerritorialScopeSelector(p: Props) {
  const [open, setOpen] = useState<string[]>([]);
  const [announcement, setAnnouncement] = useState("");
  const accepts = (level: "brasil" | "estado" | "municipio") => !!p.rule?.disponivel && !!p.rule?.aceita.includes(level);
  const groups = useMemo(() => {
    const byState = new Map<string, Territory[]>();
    const loose: Territory[] = [];
    const known = new Set(p.levels.estados.map(item => item.prefixo));
    for (const item of p.items) {
      const prefix = item.state_code || "";
      if (prefix && known.has(prefix)) byState.set(prefix, [...(byState.get(prefix) || []), item]);
      else loose.push(item);
    }
    return { byState, loose };
  }, [p.items, p.levels]);
  const members = (prefix: string) => (groups.byState.get(prefix) || []).map(item => item.id);
  const idSet = useMemo(() => new Set(p.ids), [p.ids]);
  const padrao = !!p.effective?.padrao;
  const applied = p.effective?.abrangencia;
  const n = countSelected(p.effective, p.levels);
  const stored = p.scope.brasil || p.scope.estados.length > 0 || p.scope.todos || p.scope.grupos.length > 0 || p.ids.length > 0;

  function change(item: Toggle, message: string) {
    if (p.disabled) return;
    p.onChange(toggle(p.scope, p.ids, item));
    setAnnouncement(message);
  }
  const allStates = p.levels.estados.map(item => item.prefixo);
  const statesMarked = allStates.filter(prefix => p.scope.estados.includes(prefix)).length;

  function municipality(item: Territory, group?: string) {
    const checked = p.scope.todos || (!!group && p.scope.grupos.includes(group)) || idSet.has(item.id);
    const testId = "territory-option-" + (item.code ? "code-" + item.code : "name-" + item.name);
    const input = "territorio-" + item.id.replace(/[^a-zA-Z0-9_-]/g, "_");
    return <li key={item.id} className={ROW + " pl-9"} style={{contentVisibility: "auto", containIntrinsicSize: "auto 40px"}}>
      <input id={input} type="checkbox" data-testid={testId} className={CHECK} checked={checked}
        disabled={p.disabled || p.scope.todos || !!item.selection_reason}
        aria-describedby={item.hierarchy_note || item.selection_reason ? input + "-nota" : undefined}
        onChange={() => change({ kind: "municipio", id: item.id, members: group ? members(group) : undefined },
          item.label + (checked ? " desmarcado." : " marcado."))}/>
      <span className="min-w-0 text-xs leading-5">
        <label htmlFor={input} className="cursor-pointer text-ink">{item.label}</label>
        {(item.hierarchy_note || item.selection_reason) && <span id={input + "-nota"} className="block text-[11px] text-slate-600">
          {item.hierarchy_note || item.selection_reason}</span>}
      </span>
    </li>;
  }

  return <section aria-label="Seleção territorial compartilhada" data-testid="territory-selector" className="no-print min-w-0 space-y-3">
    <h3 className="text-sm font-semibold text-ink">{p.title}</h3>
    <p data-testid="scope-info" className="text-xs leading-5 text-slate-600">{p.rule?.texto ||
      "Marque o Brasil, estados e municípios; cada nível aparece em um bloco separado no resultado."}</p>
    {p.loading && <p role="status" data-testid="scope-loading" className="text-xs text-teal">Carregando a lista de estados e municípios…</p>}
    <div className="territory-scope-layout grid gap-3">
      <div data-testid="territory-list" className="territory-list min-w-0 overflow-y-auto rounded-lg border border-line bg-white">
        <fieldset data-testid="territory-section-brasil" disabled={p.disabled || !accepts("brasil")} className="min-w-0">
          <legend className={LEGEND}>Brasil</legend>
          {!accepts("brasil") && p.rule?.motivos.brasil && <p className={REASON + " pt-2"}>{p.rule.motivos.brasil}</p>}
          <div className={ROW}>
            <input id="territorio-brasil" type="checkbox" data-testid="territory-option-brasil" className={CHECK} aria-describedby="territorio-brasil-ajuda"
              checked={accepts("brasil") && p.scope.brasil}
              onChange={() => change({ kind: "brasil" }, "Brasil (total nacional) " + (p.scope.brasil ? "desmarcado." : "marcado."))}/>
            <span className="min-w-0 text-xs leading-5">
              <span className="flex flex-wrap items-center gap-1"><label htmlFor="territorio-brasil" className="cursor-pointer font-semibold text-ink">
                Brasil (total nacional)</label>{padrao && applied?.brasil && <Badge/>}</span>
              <span id="territorio-brasil-ajuda" className="block text-[11px] text-slate-600">Total da fonte nacional; não é a soma dos municípios.</span>
            </span>
          </div>
        </fieldset>
        <fieldset data-testid="territory-section-estados" disabled={p.disabled || !accepts("estado")} className="min-w-0 border-t border-line">
          <legend className={LEGEND}>Estados <span className="ml-1 rounded-full bg-amber-100 px-2 text-[11px] font-semibold text-amber-900">soma dos municípios</span></legend>
          {!accepts("estado") && p.rule?.motivos.estado && <p className={REASON + " pt-2"}>{p.rule.motivos.estado}</p>}
          {allStates.length > 0 && <p data-testid="territory-double-count-help" className="mx-3 mt-2 rounded-md bg-amber-50 px-2 py-1.5 text-[11px] leading-4 text-amber-900">
            Cada estado é a soma dos seus municípios: o mesmo médico pode ser contado em mais de um município. Por isso, o
            valor do estado não é o número de médicos diferentes e a soma dos estados não é o total do Brasil.</p>}
          {allStates.length ? <ul>
            <li className={ROW}>
              <input id="territorio-todos-estados" type="checkbox" data-testid="territory-all-states" className={CHECK}
                checked={accepts("estado") && statesMarked === allStates.length}
                ref={element => { if (element) element.indeterminate = accepts("estado") && statesMarked > 0 && statesMarked < allStates.length; }}
                onChange={() => change({ kind: "todos_estados", prefixes: allStates }, statesMarked === allStates.length
                  ? "Todos os estados desmarcados." : "Todos os estados marcados.")}/>
              <label htmlFor="territorio-todos-estados" className="cursor-pointer text-xs font-semibold leading-5 text-ink">
                Todos os estados ({allStates.length})</label>
            </li>
            {p.levels.estados.map(state => <li key={state.prefixo} className={ROW}>
              <input id={"territorio-uf-" + state.prefixo} type="checkbox" data-testid={"territory-option-uf-" + state.prefixo} className={CHECK}
                aria-describedby={"territorio-uf-" + state.prefixo + "-ajuda"} checked={accepts("estado") && p.scope.estados.includes(state.prefixo)}
                onChange={() => change({ kind: "estado", prefix: state.prefixo }, state.rotulo +
                  (p.scope.estados.includes(state.prefixo) ? " desmarcado." : " marcado."))}/>
              <span className="flex min-w-0 flex-1 flex-wrap justify-between gap-x-2 text-xs leading-5">
                <label htmlFor={"territorio-uf-" + state.prefixo} className="cursor-pointer text-ink">{state.rotulo}</label>
                <span id={"territorio-uf-" + state.prefixo + "-ajuda"} className="text-[11px] text-slate-600">
                  soma de {state.municipios.toLocaleString("pt-BR")} {state.municipios === 1 ? "município" : "municípios"}</span>
              </span>
            </li>)}
          </ul> : accepts("estado") && <p className="px-3 py-2 text-xs text-slate-600">Nenhum estado identificado pelos códigos desta base.</p>}
        </fieldset>
        <fieldset data-testid="territory-section-municipios" disabled={p.disabled || !accepts("municipio")} className="min-w-0 border-t border-line">
          <legend className={LEGEND}>Municípios</legend>
          {!accepts("municipio") && p.rule?.motivos.municipio && <p className={REASON + " pt-2"}>{p.rule.motivos.municipio}</p>}
          <div className={ROW}>
            <input id="territorio-todos-municipios" type="checkbox" data-testid="territory-option-todos-municipios" className={CHECK}
              aria-describedby="territorio-todos-municipios-ajuda" checked={accepts("municipio") && p.scope.todos}
              onChange={() => change({ kind: "todos" }, p.scope.todos ? "Todos os municípios desmarcado."
                : "Todos os municípios marcado; os municípios marcados antes já estão incluídos nele.")}/>
            <span className="min-w-0 text-xs leading-5">
              <span className="flex flex-wrap items-center gap-1"><label htmlFor="territorio-todos-municipios" className="cursor-pointer font-semibold text-ink">
                Todos os municípios</label>{padrao && applied?.municipios.todos && <Badge/>}</span>
              <span id="territorio-todos-municipios-ajuda" className="block text-[11px] text-slate-600">
                Um valor para cada um dos {p.levels.municipios.total.toLocaleString("pt-BR")} municípios.</span>
            </span>
          </div>
          {p.scope.todos && accepts("municipio") && <p className="px-3 pb-2 text-[11px] leading-4 text-slate-600">
            Todos os municípios estão incluídos. Para escolher municípios, desmarque “Todos os municípios”.</p>}
          {p.levels.estados.length > 0 && <ul aria-label="Municípios por estado">
            {p.levels.estados.map(state => {
              const ids = members(state.prefixo);
              const status = groupState(state.prefixo, p.scope, p.ids, ids);
              const marked = status === "checked" ? ids.length : ids.filter(id => idSet.has(id)).length;
              const expanded = open.includes(state.prefixo);
              return <li key={state.prefixo} data-testid={"territory-group-" + state.prefixo} className="border-t border-slate-100">
                <div className={ROW}>
                  <input type="checkbox" data-testid={"territory-group-check-" + state.prefixo} className={CHECK}
                    aria-label={state.rotulo_grupo + " (" + state.municipios.toLocaleString("pt-BR") + ")"}
                    checked={status === "checked"} disabled={p.disabled || p.scope.todos || !ids.length}
                    ref={element => { if (element) element.indeterminate = status === "mixed"; }}
                    onChange={() => change({ kind: "grupo", prefix: state.prefixo, members: ids }, state.rotulo_grupo +
                      (status === "checked" ? " desmarcados." : " marcados (" + state.municipios.toLocaleString("pt-BR") + ")."))}/>
                  <button type="button" data-testid={"territory-group-toggle-" + state.prefixo} aria-expanded={expanded}
                    aria-controls={"territorio-grupo-" + state.prefixo}
                    onClick={() => setOpen(current => current.includes(state.prefixo) ? current.filter(item => item !== state.prefixo)
                      : [...current, state.prefixo])}
                    className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-x-2 text-left text-xs leading-5 text-ink">
                    <span>{state.nome} ({state.sigla})</span>
                    <span className="flex items-center gap-1 text-[11px] text-slate-600">{marked.toLocaleString("pt-BR")} de {
                      state.municipios.toLocaleString("pt-BR")} municípios
                      <ChevronDown size={13} aria-hidden="true" className={"text-teal transition " + (expanded ? "rotate-180" : "")}/></span>
                  </button>
                </div>
                {expanded && <ul id={"territorio-grupo-" + state.prefixo} aria-label={state.rotulo_grupo}>
                  {(groups.byState.get(state.prefixo) || []).map(item => municipality(item, state.prefixo))}</ul>}
              </li>;
            })}
          </ul>}
          {groups.loose.length > 0 && <>
            {p.levels.estados.length > 0 && <p className="border-t border-slate-100 px-3 pt-2 text-[11px] font-semibold text-slate-600">
              Sem estado identificado pelo código</p>}
            <ul aria-label="Municípios">{groups.loose.map(item => municipality(item))}</ul>
          </>}
        </fieldset>
      </div>
      <div className="min-w-0 space-y-2 text-xs leading-5">
        <p data-testid="territory-count" className="font-semibold text-ink">{n.toLocaleString("pt-BR")} selecionados</p>
        {padrao ? <p data-testid="territory-default" className="text-slate-600">Padrão desta análise: {p.summary}</p>
          : <p data-testid="territory-breakdown" className="text-slate-600">{breakdown(p.effective, p.levels)}</p>}
        {p.pending && <p role="status" data-testid="territory-rule-message" className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1.5 text-amber-900">
          {p.pending}</p>}
        <button type="button" data-testid="territory-clear" disabled={p.disabled || !stored}
          onClick={() => { p.onClear(); setAnnouncement("Seleção limpa. Vale o padrão da análise."); }}
          className="min-h-9 rounded-lg border border-line bg-white px-3 font-semibold text-teal disabled:opacity-40">Limpar seleção</button>
      </div>
    </div>
    <p aria-live="polite" className="sr-only">{announcement}</p>
  </section>;
}
