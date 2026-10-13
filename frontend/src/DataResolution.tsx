export type ResolutionOptions = {
  number_format?: string; duplicate_policy?: string; component_columns?: string[];
  rows_additive_confirmed?: boolean; comparison_confirmed?: boolean;
  population_additive_confirmed?: boolean; component_sum_confirmed?: boolean;
  identity_union_confirmed?: boolean; cohort_coverage_confirmed?: boolean;
  initial_period?: string; final_period?: string; period_convention?: string;
};
export type Multiplicity = {
  affected_records: number; groups: number; exact_duplicate_excess: number;
  distinguishing_columns: string[]; key_columns: string[];
  examples: { dimensions: Record<string, string>; records: number }[];
};

type Props = {
  operation: string; columns: string[]; mapping: Record<string, string | undefined>;
  diagnostic?: Multiplicity; options: ResolutionOptions; periods: string[];
  setOptions: (options: ResolutionOptions) => void;
  selectIdentity: (column: string) => void; identityConfirmed: boolean; confirmIdentity: (value: boolean) => void;
  confirmCoordinates: () => void;
};

export default function DataResolution(p: Props) {
  const set = (value: Partial<ResolutionOptions>) => p.setOptions({...p.options, ...value});
  const check = (key: keyof ResolutionOptions, label: string) => <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
    <input type="checkbox" checked={p.options[key] === true} onChange={e => set({[key]: e.target.checked})}/>{label}
  </label>;
  return <div className="mt-5 space-y-4 rounded-xl border border-line bg-slate-50/50 p-4">
    <h4 className="text-sm font-bold text-ink">Conferir a estrutura dos dados</h4>
    {!!p.diagnostic?.affected_records && p.mapping.count && <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
      <p className="text-sm font-semibold">{p.diagnostic.affected_records.toLocaleString("pt-BR")} registros em {p.diagnostic.groups.toLocaleString("pt-BR")} grupos com mais de uma linha</p>
      <p className="text-xs">Cópias idênticas em todas as colunas: {p.diagnostic.exact_duplicate_excess}. Colunas que variam: {p.diagnostic.distinguishing_columns.join(", ") || "nenhuma"}.</p>
      <ul className="space-y-1 text-xs">{p.diagnostic.examples.map((example, i) => <li key={i}>{Object.entries(example.dimensions).map(([k, v]) => `${k}: ${v}`).join(" · ")} — {example.records} registros</li>)}</ul>
      {!!p.diagnostic.exact_duplicate_excess && <label className="flex items-start gap-2 text-xs leading-5">
        <input type="checkbox" checked={p.options.duplicate_policy === "remove_exact"} onChange={e => set({duplicate_policy: e.target.checked ? "remove_exact" : ""})}/>
        Verifiquei que as linhas integralmente iguais são cópias de importação e autorizo remover somente essas cópias nesta análise
      </label>}
      <details><summary className="cursor-pointer text-xs font-bold">As linhas representam partes diferentes da mesma contagem?</summary>
        <p className="my-2 text-xs leading-5">Indique dimensões adicionais, como setor ou estabelecimento. Não use este recurso para juntar municípios de mesmo nome ou para somar pessoas que possam aparecer em mais de uma parte.</p>
        <div className="flex flex-wrap gap-3">{p.columns.filter(c => !Object.values(p.mapping).includes(c)).map(c => <label className="flex gap-1 text-xs" key={c}>
          <input type="checkbox" checked={p.options.component_columns?.includes(c) || false} onChange={e => set({component_columns: e.target.checked ? [...(p.options.component_columns || []), c] : p.options.component_columns?.filter(x => x !== c), rows_additive_confirmed: false})}/>{c}
        </label>)}</div>
        <div className="mt-3">{check("rows_additive_confirmed", "Declaro que essas partes têm a mesma unidade de contagem e não se sobrepõem dentro de cada território, período e categoria; a população é o total territorial compartilhado.")}</div>
      </details>
    </div>}
    <label className="block text-xs font-semibold text-slate-700">Formato dos valores numéricos
      <select className="mt-2 block w-full min-w-0 rounded-lg border p-2 sm:ml-2 sm:inline sm:w-auto" value={p.options.number_format || "decimal_point"} onChange={e => set({number_format: e.target.value})}>
        <option value="decimal_point">Ponto decimal, sem separador de milhares</option>
        <option value="decimal_comma">Vírgula decimal, sem separador de milhares</option>
      </select>
    </label>
    {p.operation !== "spatial" && p.operation !== "rotation" && p.operation !== "nearest" && !p.mapping.count && <div className="space-y-3">
      <label className="block text-xs font-semibold">Identificador individual para contar pessoas distintas
        <select className="ml-2 rounded-lg border p-2" value={p.mapping.identity || ""} onChange={e => p.selectIdentity(e.target.value)}>
          <option value="">Selecione</option>{p.columns.map(c => <option key={c}>{c}</option>)}
        </select>
      </label>
      <label className="flex items-start gap-2 text-xs"><input type="checkbox" checked={p.identityConfirmed} onChange={e => p.confirmIdentity(e.target.checked)}/>Autorizo contar pessoas distintas: o identificador é completo e identifica a mesma pessoa no recorte.</label>
    </div>}
    {(p.operation === "spatial" || p.operation === "nearest") && <button type="button" className="rounded-lg border bg-white px-3 py-2 text-xs" onClick={p.confirmCoordinates}>Confirmar as colunas de latitude e longitude selecionadas</button>}
    {["comparisons", "ranking"].includes(p.operation) && check("comparison_confirmed", "Confirmo equivalência da medida, unidade de contagem e definição populacional entre os territórios comparados.")}
    {["temporal", "rotation"].includes(p.operation) && <label className="block text-xs font-semibold">Convenção temporal
      <select className="ml-2 rounded-lg border p-2" value={p.options.period_convention || "auto"} onChange={e => set({period_convention: e.target.value})}>
        <option value="auto">Reconhecer ano, AAAAMM ou data ISO</option><option value="yyyymm">Competência AAAAMM</option><option value="date">Data ISO (AAAA-MM-DD)</option><option value="numeric">Posição numérica declarada</option>
      </select>
    </label>}
    {p.operation === "rotation" && <>
      <div className="flex flex-wrap gap-3">{(["initial_period", "final_period"] as const).map((key, i) => <label key={key} className="text-xs font-semibold">{i === 0 ? "Período inicial" : "Período final"}
        <select className="ml-2 rounded-lg border p-2" value={p.options[key] || ""} onChange={e => set({[key]: e.target.value})}><option value="">{i === 0 ? "Primeiro período" : "Último período"}</option>{p.periods.map(v => <option key={v}>{v}</option>)}</select>
      </label>)}</div>
      {check("cohort_coverage_confirmed", "Confirmo cobertura integral do mesmo universo nos dois períodos; ausência de registro representa ausência na coorte.")}
    </>}
    {p.operation === "aggregate" && <>
      {check("population_additive_confirmed", "Declaro que as populações territoriais são partes sem sobreposição do conjunto agregado.")}
      {check("component_sum_confirmed", "Autorizo a soma das contagens dos componentes, ciente de que pode contar a mesma unidade mais de uma vez; o total não será apresentado como pessoas únicas.")}
      {!p.mapping.count && check("identity_union_confirmed", "O identificador individual reconhece a mesma pessoa em todos os territórios da união; autorizo deduplicar a união.")}
    </>}
  </div>;
}
