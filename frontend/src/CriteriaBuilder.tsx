import { useState, type ReactNode } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  ATTRIBUTE_LABELS, NUMERIC_OPERATORS, UNITS, addCondition, describe, isNegated, leaves, nextId, removeLeaf,
  toggleNegation, unitText, updateLeaf, uses, type Attribute, type BandsSpec, type CriteriaNode, type Leaf,
  type NumericAttribute, type RankingSpec,
} from "./criteriaTree";

const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];
const NUMERIC: NumericAttribute[] = ["densidade", "quantidade", "populacao", "distancia"];
const input = "min-w-0 rounded-lg border border-violet-200 bg-white px-2 py-1.5 text-sm";

type Props = {
  tree: CriteriaNode | null; onTree: (tree: CriteriaNode | null) => void;
  ranking: RankingSpec | null; onRanking: (ranking: RankingSpec | null) => void;
  bands: BandsSpec | null; onBands: (bands: BandsSpec | null) => void;
  distanceScope: string; onDistanceScope: (value: string) => void;
  eligibilityScope: string; onEligibilityScope: (value: string) => void;
  period: string; category: string; categories: string[]; countUnit: string; universe: string;
  selectionIds: string[]; ranges: Record<string, [number, number]>; references: ReactNode; disabled: boolean;
};

// Régua: posição e passo vêm da faixa observada no último resultado; o valor é sempre escolha do usuário.
function Ruler({ leaf, range, onValue, disabled }: { leaf: Leaf; range?: [number, number]; onValue: (v: string) => void; disabled: boolean }) {
  const current = Number(String(leaf.value).replace(",", "."));
  if (!range || !Number.isFinite(current) || range[1] <= range[0]) return null;
  const [low, high] = [Math.min(range[0], current), Math.max(range[1], current)];
  const step = Math.pow(10, Math.floor(Math.log10((high - low) / 100)));
  const decimals = Math.max(0, -Math.floor(Math.log10(step)));
  return <label className="flex w-full flex-col gap-1 text-[11px] text-slate-500">
    <input type="range" aria-label={"Régua de " + leaf.id} min={low} max={high} step={step} value={current} disabled={disabled}
      onChange={e => onValue(Number(e.target.value).toFixed(decimals))}/>
    Faixa observada no último resultado: {low.toLocaleString("pt-BR")} a {high.toLocaleString("pt-BR")} (não é ponto de corte)
  </label>;
}

export default function CriteriaBuilder(p: Props) {
  const [attribute, setAttribute] = useState<Attribute | "">("");
  const [operator, setOperator] = useState("");
  const [value, setValue] = useState("");
  const [logic, setLogic] = useState<"and" | "or">("and");
  const conditions = leaves(p.tree);
  const distance = uses(p.tree, "distancia", p.ranking, p.bands);
  const membership = attribute === "territorio" || attribute === "uf";
  const canAdd = !!attribute && !!operator && (attribute === "territorio" ? p.selectionIds.length > 0 : !!value.trim());
  const context = "competência " + (p.period || "a escolher") + (p.category ? " · categoria " + p.category : "") + " · universo: " + p.universe;
  function add() {
    if (!attribute || !canAdd) return;
    const leaf: Leaf = {id: nextId(p.tree), attribute, operator,
      value: attribute === "territorio" ? [...p.selectionIds] : attribute === "uf" ? [value] : value.trim()};
    p.onTree(addCondition(p.tree, leaf, logic));
    setAttribute(""); setOperator(""); setValue("");
  }
  const change = (leaf: Leaf, patch: Partial<Leaf>) => p.tree && p.onTree(updateLeaf(p.tree, leaf.id, patch));
  return <fieldset aria-label="Critérios combinados" className="min-w-0 space-y-3 rounded-xl border border-violet-300 bg-violet-50/30 p-3 text-sm leading-6">
    <legend className="px-1 text-xs font-semibold text-violet-900">Critérios do usuário</legend>
    <p className="text-xs leading-5 text-slate-600">Operadores e valores são escolhas suas: não há pontos de corte padrão nem
      caráter legal, sanitário ou científico. Indeterminação nunca é tratada como “não atende”.</p>
    {p.tree && <p aria-label="Combinação atual" className="break-words rounded-lg bg-white px-2 py-1 text-xs text-ink">
      Combinação: <strong>{describe(p.tree, p.countUnit)}</strong></p>}
    {!!conditions.length && <ol aria-label="Condições" className="space-y-2">
      {conditions.map(leaf => <li key={leaf.id} role="group" aria-label={"Condição " + leaf.id}
        className="space-y-2 rounded-lg border border-violet-200 bg-white p-2 text-xs">
        <p className="leading-5 text-slate-600"><strong className="text-ink">{leaf.id} · {ATTRIBUTE_LABELS[leaf.attribute]}</strong>
          {unitText(leaf, p.countUnit) && " · unidade: " + unitText(leaf, p.countUnit)} · {context} · origem: escolha do usuário</p>
        <div className="flex flex-wrap items-end gap-2">
          {NUMERIC.includes(leaf.attribute as NumericAttribute) && <>
            <label className="flex flex-col gap-0.5">Operador
              <select aria-label={"Operador de " + leaf.id} className={input} value={leaf.operator} disabled={p.disabled}
                onChange={e => change(leaf, {operator: e.target.value})}>
                {NUMERIC_OPERATORS.map(([key, symbol]) => <option key={key} value={key}>{symbol}</option>)}
              </select></label>
            <label className="flex flex-col gap-0.5">Valor
              <input aria-label={"Valor de " + leaf.id} inputMode="decimal" maxLength={32} className={input + " w-28"}
                value={String(leaf.value)} disabled={p.disabled} onChange={e => change(leaf, {value: e.target.value})}/></label>
            {UNITS[leaf.attribute] && <label className="flex flex-col gap-0.5">Unidade
              <select aria-label={"Unidade de " + leaf.id} className={input} value={leaf.unit || ""} disabled={p.disabled}
                onChange={e => change(leaf, {unit: e.target.value || undefined})}>
                <option value="">{unitText({...leaf, unit: undefined})} (contexto único)</option>
                {UNITS[leaf.attribute]!.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
              </select></label>}
            {(leaf.attribute === "densidade" || leaf.attribute === "quantidade") && p.categories.length > 1 &&
              <label className="flex flex-col gap-0.5">Categoria
                <select aria-label={"Categoria de " + leaf.id} className={input} value={leaf.category || ""} disabled={p.disabled}
                  onChange={e => change(leaf, {category: e.target.value || undefined})}>
                  <option value="">A da análise</option>{p.categories.map(item => <option key={item}>{item}</option>)}
                </select></label>}
          </>}
          {leaf.attribute === "uf" && <label className="flex flex-col gap-0.5">UF
            <select aria-label={"UF de " + leaf.id} className={input} value={(leaf.value as string[])[0]} disabled={p.disabled}
              onChange={e => change(leaf, {value: [e.target.value]})}>{UFS.map(uf => <option key={uf}>{uf}</option>)}</select></label>}
          {leaf.attribute === "territorio" && <span className="pb-1.5">{(leaf.value as string[]).length} território(s) na lista</span>}
          <label className="flex min-h-9 items-center gap-1.5"><input type="checkbox" checked={isNegated(p.tree, leaf.id)}
            disabled={p.disabled} onChange={() => p.tree && p.onTree(toggleNegation(p.tree, leaf.id))}/>NÃO (negar)</label>
          <button type="button" aria-label={"Remover " + leaf.id} disabled={p.disabled} onClick={() => p.onTree(removeLeaf(p.tree, leaf.id))}
            className="ml-auto rounded-md p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-40"><Trash2 size={15}/></button>
        </div>
        {NUMERIC.includes(leaf.attribute as NumericAttribute) &&
          <Ruler leaf={leaf} range={p.ranges[leaf.id]} disabled={p.disabled} onValue={v => change(leaf, {value: v})}/>}
      </li>)}
    </ol>}
    <div role="group" aria-label="Nova condição" className="flex flex-wrap items-end gap-2 text-xs">
      <label className="flex flex-col gap-0.5">Indicador
        <select aria-label="Indicador da nova condição" className={input} value={attribute} disabled={p.disabled}
          onChange={e => { const next = e.target.value as Attribute | ""; setAttribute(next); setOperator(""); setValue(next === "uf" ? "" : value); }}>
          <option value="">Escolher</option>
          {(Object.keys(ATTRIBUTE_LABELS) as Attribute[]).map(key => <option key={key} value={key}>
            {key === "territorio" ? "Território na seleção atual" : ATTRIBUTE_LABELS[key]}</option>)}
        </select></label>
      <label className="flex flex-col gap-0.5">Operador
        <select aria-label="Operador da nova condição" className={input} value={operator} disabled={p.disabled || !attribute}
          onChange={e => setOperator(e.target.value)}>
          <option value="">Escolher</option>
          {(attribute === "territorio" ? [["in", "pertence"], ["not_in", "não pertence"]] : attribute === "uf" ? [["=", "="], ["!=", "≠"]]
            : NUMERIC_OPERATORS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
      {attribute === "uf" ? <label className="flex flex-col gap-0.5">UF
        <select aria-label="Valor da nova condição" className={input} value={value} disabled={p.disabled} onChange={e => setValue(e.target.value)}>
          <option value="">Escolher</option>{UFS.map(uf => <option key={uf}>{uf}</option>)}</select></label>
      : attribute !== "territorio" && <label className="flex flex-col gap-0.5">Valor
        <input aria-label="Valor da nova condição" inputMode="decimal" maxLength={32} value={value} disabled={p.disabled || !attribute}
          onChange={e => setValue(e.target.value)} className={input + " w-28"}/></label>}
      {attribute === "territorio" && <span className="pb-1.5 text-slate-600">{p.selectionIds.length
        ? p.selectionIds.length + " território(s) da seleção atual" : "Selecione territórios na pesquisa territorial"}</span>}
      {!!p.tree && <div role="radiogroup" aria-label="Combinar a nova condição" className="flex items-center gap-2 pb-1.5">
        <label className="flex items-center gap-1"><input type="radio" name="criteria-logic" checked={logic === "and"}
          onChange={() => setLogic("and")}/>E</label>
        <label className="flex items-center gap-1"><input type="radio" name="criteria-logic" checked={logic === "or"}
          onChange={() => setLogic("or")}/>OU</label></div>}
      <button type="button" disabled={p.disabled || !canAdd} onClick={add}
        className="inline-flex items-center gap-1 rounded-lg border border-violet-300 bg-white px-3 py-1.5 font-semibold text-violet-900 disabled:opacity-40">
        <Plus size={14}/>Adicionar condição</button>
      {membership && <p className="w-full text-[11px] text-slate-500">{attribute === "uf"
        ? "UF pela regra governada do código IBGE (base Brasil); em bases importadas fica não avaliável."
        : "A lista usa a seleção territorial vigente no momento em que a condição é adicionada."}</p>}
    </div>
    <details className="rounded-lg border border-violet-100 bg-white px-2 py-1 text-xs">
      <summary className="cursor-pointer font-semibold text-violet-900">Ordenação e seleção dos primeiros</summary>
      <div className="flex flex-wrap items-end gap-2 py-2">
        <label className="flex flex-col gap-0.5">Ordenar por
          <select aria-label="Ordenar por" className={input} value={p.ranking?.attribute || ""} disabled={p.disabled}
            onChange={e => p.onRanking(e.target.value ? {...(p.ranking || {direction: ""}), attribute: e.target.value as NumericAttribute} : null)}>
            <option value="">Sem ordenação</option>{NUMERIC.map(key => <option key={key} value={key}>{ATTRIBUTE_LABELS[key]}</option>)}
          </select></label>
        {p.ranking && <>
          <label className="flex flex-col gap-0.5">Direção
            <select aria-label="Direção da ordenação" className={input} value={p.ranking.direction} disabled={p.disabled}
              onChange={e => p.onRanking({...p.ranking!, direction: e.target.value as "asc" | "desc" | ""})}>
              <option value="">Escolher</option><option value="desc">Do maior para o menor</option><option value="asc">Do menor para o maior</option>
            </select></label>
          <label className="flex flex-col gap-0.5">N primeiros
            <input aria-label="Mostrar os N primeiros" type="number" min={1} max={10000} className={input + " w-24"} disabled={p.disabled}
              value={p.ranking.top_n ?? ""} onChange={e => p.onRanking({...p.ranking!, top_n: e.target.value ? Number(e.target.value) : undefined})}/></label>
          <label className="flex min-h-9 items-center gap-1.5"><input type="checkbox" checked={!!p.ranking.exact_n} disabled={p.disabled || !p.ranking.top_n}
            onChange={e => p.onRanking({...p.ranking!, exact_n: e.target.checked})}/>Exigir exatamente N</label>
          {!!p.tree && <label className="flex flex-col gap-0.5">Conjunto ordenado
            <select aria-label="Conjunto ordenado" className={input} value={p.ranking.set || "atende"} disabled={p.disabled}
              onChange={e => p.onRanking({...p.ranking!, set: e.target.value as "atende" | "universo"})}>
              <option value="atende">Os que atendem aos critérios</option><option value="universo">Todo o universo</option>
            </select></label>}
        </>}
      </div>
      <p className="pb-1 text-[11px] text-slate-500">Valores iguais compartilham posição (1, 2, 2, 4); não avaliáveis ficam fora da ordenação.
        Os N primeiros incluem os empatados no corte; com N exato e empate, o sistema pergunta, pois não há regra de desempate.</p>
    </details>
    <details className="rounded-lg border border-violet-100 bg-white px-2 py-1 text-xs">
      <summary className="cursor-pointer font-semibold text-violet-900">Faixas</summary>
      <div className="flex flex-wrap items-end gap-2 py-2">
        <label className="flex flex-col gap-0.5">Faixas de
          <select aria-label="Atributo das faixas" className={input} value={p.bands?.attribute || ""} disabled={p.disabled}
            onChange={e => p.onBands(e.target.value ? {attribute: e.target.value as NumericAttribute, limits: p.bands?.limits || []} : null)}>
            <option value="">Sem faixas</option>{NUMERIC.map(key => <option key={key} value={key}>{ATTRIBUTE_LABELS[key]}</option>)}
          </select></label>
        {p.bands && <label className="flex min-w-[12rem] flex-1 flex-col gap-0.5">Limites escolhidos por você (separados por “;”)
          <input aria-label="Limites das faixas" className={input} disabled={p.disabled} value={p.bands.limits.join("; ")}
            onChange={e => p.onBands({...p.bands!, limits: e.target.value.split(";").map(item => item.trim()).filter(Boolean)})}/></label>}
      </div>
      <p className="pb-1 text-[11px] text-slate-500">Intervalos [a, b), com o último fechado; nenhum intervalo é criado pelo sistema.</p>
    </details>
    {distance && <div className="space-y-2">
      {p.references}
      <label className="flex items-start gap-2 text-xs leading-5"><input type="checkbox" className="mt-1"
        checked={p.distanceScope === "evaluable_references"} disabled={p.disabled}
        onChange={e => p.onDistanceScope(e.target.checked ? "evaluable_references" : "")}/>
        Aceito, quando alguma referência não tiver coordenada válida, usar a mais próxima entre as referências avaliáveis
        (cobertura parcial, sempre rotulada; não equivale ao mínimo do conjunto completo).</label>
      <label className="flex items-start gap-2 text-xs leading-5"><input type="checkbox" className="mt-1"
        checked={p.eligibilityScope === "confirmed_eligible"} disabled={p.disabled}
        onChange={e => p.onEligibilityScope(e.target.checked ? "confirmed_eligible" : "")}/>
        Aceito, quando houver candidatos a referência com elegibilidade desconhecida, restringir a afirmação às referências de
        elegibilidade confirmada (rotulado; esses candidatos não são tratados como inelegíveis).</label>
    </div>}
  </fieldset>;
}
