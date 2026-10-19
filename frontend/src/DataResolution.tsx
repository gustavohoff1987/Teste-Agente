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
  selectIdentity: (column: string) => void;
  /** Premissas aplicadas pelo backend nesta preparação (perfil oficial e verificadas nos dados): a tela não as pede. */
  applied: ReadonlySet<string>;
  /** O backend não conseguiu verificar o separador das coordenadas (formato misto): só então ele é uma escolha. */
  separatorChoice: boolean;
};

/** Escolhas reais sobre a estrutura dos dados (D1): nenhuma declaração ou confirmação de coluna. */
export default function DataResolution(p: Props) {
  const set = (value: Partial<ResolutionOptions>) => p.setOptions({...p.options, ...value});
  const spatial = p.operation === "spatial" || p.operation === "nearest" || p.operation === "criteria";
  return <div className="mt-5 space-y-4 rounded-xl border border-line bg-slate-50/50 p-4">
    <h4 className="text-sm font-bold text-ink">Conferir a estrutura dos dados</h4>
    {!!p.diagnostic?.affected_records && p.mapping.count && <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
      <p className="text-sm font-semibold">{p.diagnostic.affected_records.toLocaleString("pt-BR")} registros em {p.diagnostic.groups.toLocaleString("pt-BR")} grupos com mais de uma linha</p>
      <p className="text-xs">Cópias idênticas em todas as colunas: {p.diagnostic.exact_duplicate_excess}. Colunas que variam: {p.diagnostic.distinguishing_columns.join(", ") || "nenhuma"}.</p>
      <ul className="space-y-1 text-xs">{p.diagnostic.examples.map((example, i) => <li key={i}>{Object.entries(example.dimensions).map(([k, v]) => `${k}: ${v}`).join(" · ")} — {example.records} registros</li>)}</ul>
      {!!p.diagnostic.exact_duplicate_excess && <label className="block text-xs font-semibold">Linhas idênticas
        <select aria-label="Linhas idênticas" data-testid="duplicate-policy" className="ml-2 rounded-lg border p-2"
          value={p.options.duplicate_policy === "remove_exact" ? "remove_exact" : ""}
          onChange={e => set({duplicate_policy: e.target.value || undefined})}>
          <option value="">Escolher</option>
          <option value="remove_exact">Remover as cópias nesta análise</option>
        </select>
      </label>}
      <details><summary className="cursor-pointer text-xs font-bold">As linhas representam partes diferentes da mesma contagem?</summary>
        <p className="my-2 text-xs leading-5">Escolha as dimensões adicionais, como setor ou estabelecimento. As partes são somadas como componentes da mesma
          unidade, com a população territorial usada uma vez; a premissa aparece em “Método e limitações”. Não use este recurso para juntar
          municípios de mesmo nome.</p>
        <div className="flex flex-wrap gap-3">{p.columns.filter(c => !Object.values(p.mapping).includes(c)).map(c => <label className="flex gap-1 text-xs" key={c}>
          <input type="checkbox" checked={p.options.component_columns?.includes(c) || false} onChange={e => set({component_columns: e.target.checked ? [...(p.options.component_columns || []), c] : p.options.component_columns?.filter(x => x !== c)})}/>{c}
        </label>)}</div>
      </details>
    </div>}
    {spatial && (p.separatorChoice ? <label className="block text-xs font-semibold text-slate-700">Separador decimal das coordenadas
      <select aria-label="Separador decimal das coordenadas" className="mt-2 block w-full min-w-0 rounded-lg border p-2 sm:ml-2 sm:inline sm:w-auto"
        value={p.options.number_format || ""} onChange={e => set({number_format: e.target.value || undefined})}>
        <option value="">Escolher</option>
        <option value="decimal_point">Ponto decimal, sem separador de milhares</option>
        <option value="decimal_comma">Vírgula decimal, sem separador de milhares</option>
      </select>
    </label> : p.applied.has("number_format") ? <p data-testid="governed-number-format" className="text-xs text-slate-700">
      <span className="font-semibold">Formato dos valores numéricos:</span> vírgula decimal nas coordenadas, verificada nos dados.</p> : null)}
    {p.operation !== "spatial" && p.operation !== "rotation" && p.operation !== "nearest" && !p.mapping.count && <div className="space-y-3">
      <label className="block text-xs font-semibold">Identificador individual para contar pessoas distintas
        <select className="ml-2 rounded-lg border p-2" value={p.mapping.identity || ""} onChange={e => p.selectIdentity(e.target.value)}>
          <option value="">Escolher coluna</option>{p.columns.map(c => <option key={c}>{c}</option>)}
        </select>
      </label>
    </div>}
    {["temporal", "rotation"].includes(p.operation) && <label className="block text-xs font-semibold">Convenção temporal
      <select className="ml-2 rounded-lg border p-2" value={p.options.period_convention || "auto"} onChange={e => set({period_convention: e.target.value})}>
        <option value="auto">Reconhecer ano, AAAAMM ou data ISO</option><option value="yyyymm">Competência AAAAMM</option><option value="date">Data ISO (AAAA-MM-DD)</option><option value="numeric">Posição numérica</option>
      </select>
    </label>}
    {p.operation === "rotation" && <div className="flex flex-wrap gap-3">{(["initial_period", "final_period"] as const).map((key, i) => <label key={key} className="text-xs font-semibold">{i === 0 ? "Período inicial" : "Período final"}
      <select className="ml-2 rounded-lg border p-2" value={p.options[key] || ""} onChange={e => set({[key]: e.target.value})}><option value="">{i === 0 ? "Primeiro período" : "Último período"}</option>{p.periods.map(v => <option key={v}>{v}</option>)}</select>
    </label>)}</div>}
    {p.operation === "aggregate" && p.mapping.identity && !p.mapping.count && <label className="block text-xs font-semibold">Total da agregação
      <select aria-label="Total da agregação" className="ml-2 rounded-lg border p-2" value={p.options.identity_union_confirmed ? "identity" : ""}
        onChange={e => set({identity_union_confirmed: e.target.value === "identity" ? true : undefined})}>
        <option value="">Soma dos componentes (possível dupla contagem)</option>
        <option value="identity">Pessoas distintas pelo identificador</option>
      </select>
    </label>}
  </div>;
}
