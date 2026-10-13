import { useMemo, useState } from "react";

type Row = Record<string, unknown>;
type Item = { id: string; territorio: string };
export type CriteriaMetadata = {
  contagens?: { ATENDE: number; NAO_ATENDE: number; NAO_AVALIAVEL: number; universo: number } | null;
  conjuntos?: { ATENDE: string[]; NAO_ATENDE: string[]; NAO_AVALIAVEL: { id: string }[] } | null;
  desfecho?: string;
  referencias?: { alcance_afirmacao: string; forma: string; n: number; n_coordenadas_avaliaveis: number;
    cobertura_avaliacao_elegibilidade: { candidatos: number; ATENDE: number; NAO_ATENDE: number; NAO_AVALIAVEL: number } | null;
    aceitacoes_disponiveis: { cobertura_parcial: number; elegibilidade_confirmada: number }; membros: { id: string }[] } | null;
  selecao?: { n_solicitado: number; n_efetivo?: number; membros: (Item & { posicao: number })[] | null } | null;
  ordenacao?: { atributo: string; direcao: string; nao_avaliaveis: Item[] } | null;
  faixas?: { faixas: { faixa: string; n: number }[]; fora_de_todas: Item[]; nao_avaliaveis: Item[]; convencao: string } | null;
  comparacao?: { em_ambos: Item[]; somente_atual: Item[]; somente_anterior: Item[]; indeterminados: (Item & { anterior: string; atual: string })[];
    definicao_anterior: { descricao: string; rotulo: string } } | null;
  pendencias?: { tipo: string; pergunta: string }[];
  limitacoes?: { tipo: string; dados_estruturados?: Record<string, unknown>; elementos_afetados?: number }[];
};
type Filter = "ATENDE" | "NAO_ATENDE" | "NAO_AVALIAVEL" | "TODOS" | "SELECIONADOS";
const LABEL: Record<Filter, string> = {ATENDE: "Atendem", NAO_ATENDE: "Não atendem", NAO_AVALIAVEL: "Não avaliáveis",
  TODOS: "Todos", SELECIONADOS: "Selecionados"};
const shortNum = (n: number) => new Intl.NumberFormat("pt-BR", {maximumFractionDigits: 6}).format(n);
const show = (value: unknown) => value === null || value === undefined ? "—" : typeof value === "number" ? shortNum(value) : String(value);
const button = "rounded-lg border px-3 py-2 text-xs disabled:opacity-40";

function List({ title, items }: { title: string; items: Item[] }) {
  return <details className="text-xs"><summary className="cursor-pointer">{title}: {items.length}</summary>
    <p className="mt-1 max-h-32 overflow-auto break-words text-slate-600">{items.map(item => item.territorio).join("; ") || "—"}</p></details>;
}

export default function CriteriaResults({ rows, meta, onExport, onSelection, onReferences, reusable, disabled }: {
  rows: Row[]; meta: CriteriaMetadata; onExport: (rows: Row[]) => void; onSelection: (ids: string[]) => void;
  onReferences: (ids: string[]) => void; reusable: boolean; disabled: boolean;
}) {
  const hasTree = !!meta.contagens;
  const selected = useMemo(() => new Set((meta.selecao?.membros || []).map(item => item.id)), [meta]);
  const [filter, setFilter] = useState<Filter>(hasTree ? "ATENDE" : "TODOS");
  const codeOf = (id: string) => id.startsWith("code:") ? id.slice(5) : null;
  const selectedCodes = useMemo(() => new Set([...selected].map(codeOf)), [selected]);
  const visible = useMemo(() => rows.filter(row => filter === "TODOS" ? true : filter === "SELECIONADOS"
    ? row["Selecionado"] === "Sim" || selectedCodes.has(String(row["Código"])) : row["Resultado"] === filter), [rows, filter, selectedCodes]);
  const counts: Partial<Record<Filter, number>> = hasTree ? {ATENDE: meta.contagens!.ATENDE, NAO_ATENDE: meta.contagens!.NAO_ATENDE,
    NAO_AVALIAVEL: meta.contagens!.NAO_AVALIAVEL, TODOS: rows.length} : {TODOS: rows.length};
  if (meta.selecao?.membros) counts.SELECIONADOS = meta.selecao.membros.length;
  const reasons = meta.limitacoes?.find(item => item.tipo === "UNIDADES_NAO_AVALIAVEIS")?.dados_estruturados;
  const columns = rows.length ? Object.keys(rows[0]) : [];
  const meets = meta.conjuntos?.ATENDE || [];
  const chosen = meta.selecao?.membros?.map(item => item.id) || [];
  return <section aria-label="Territórios classificados" className="mt-6 space-y-4">
    {!!meta.pendencias?.length && <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
      {meta.pendencias.map(item => <p key={item.tipo}>{item.pergunta}</p>)}</div>}
    {meta.referencias && <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-3 text-xs leading-5">
      <p><strong>Distância:</strong> {meta.referencias.alcance_afirmacao}.</p>
      <p>Referências: {meta.referencias.n} ({meta.referencias.forma === "CRITERIO" ? "por critério" : "lista explícita"}), {meta.referencias.n_coordenadas_avaliaveis} com
        coordenadas avaliáveis{meta.referencias.cobertura_avaliacao_elegibilidade && <> · critério de elegibilidade avaliado em {meta.referencias.cobertura_avaliacao_elegibilidade.candidatos - meta.referencias.cobertura_avaliacao_elegibilidade.NAO_AVALIAVEL} de {meta.referencias.cobertura_avaliacao_elegibilidade.candidatos} candidatos</>}.</p>
      {(meta.referencias.aceitacoes_disponiveis.cobertura_parcial > 0 || meta.referencias.aceitacoes_disponiveis.elegibilidade_confirmada > 0) &&
        <p className="text-amber-900">A distância só é afirmada com o alcance completo. Para usar o alcance restrito, marque explicitamente a
          aceitação correspondente nos critérios ({meta.referencias.aceitacoes_disponiveis.cobertura_parcial > 0 ? "cobertura parcial" : "elegibilidade confirmada"}).</p>}
    </div>}
    {reasons && Object.keys(reasons).length > 0 && <p className="text-xs text-slate-600">Motivos de não avaliabilidade (causas por território):{" "}
      {Object.entries(reasons).map(([motive, n]) => motive + " " + n).join(" · ")}</p>}
    <div role="radiogroup" aria-label="Mostrar territórios" className="flex flex-wrap gap-2">
      {(Object.keys(counts) as Filter[]).map(key => <label key={key} className={"flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg border px-3 text-xs " +
        (filter === key ? "border-violet-500 bg-violet-50" : "border-line bg-white")}>
        <input type="radio" className="sr-only" name="criteria-filter" checked={filter === key} onChange={() => setFilter(key)}/>
        {LABEL[key]} ({counts[key]})</label>)}
    </div>
    <div className="overflow-hidden rounded-2xl border border-line">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
        <h4 className="text-sm font-bold text-ink">{LABEL[filter]}</h4>
        <span className="text-xs text-slate-400">{visible.length} linhas · até 150 exibidas</span>
        <button type="button" disabled={!visible.length} onClick={() => onExport(visible)} className={button}>Exportar este recorte (CSV)</button>
      </div>
      {visible.length ? <div className="max-h-[520px] overflow-auto"><table className="data-table w-full">
        <thead className="sticky top-0 bg-slate-50"><tr>{columns.map(key => <th key={key}>{key}</th>)}</tr></thead>
        <tbody>{visible.slice(0, 150).map((row, index) => <tr key={index}>{columns.map(key => <td key={key}>{show(row[key])}</td>)}</tr>)}</tbody>
      </table></div> : <p className="px-4 py-6 text-xs text-slate-500">Nenhum território nesta condição.</p>}
    </div>
    {meta.faixas && <div className="rounded-xl border border-line p-3 text-xs">
      <h4 className="font-bold text-ink">Faixas ({meta.faixas.convencao})</h4>
      <table className="data-table mt-2 w-full"><thead><tr><th>Faixa</th><th>Territórios</th></tr></thead>
        <tbody>{meta.faixas.faixas.map(item => <tr key={item.faixa}><td>{item.faixa}</td><td>{item.n}</td></tr>)}</tbody></table>
      <List title="Fora de todas as faixas" items={meta.faixas.fora_de_todas}/>
      <List title="Não avaliáveis (à parte)" items={meta.faixas.nao_avaliaveis}/>
    </div>}
    {meta.comparacao && <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-3 text-xs leading-5">
      <h4 className="font-bold text-ink">Comparação com {meta.comparacao.definicao_anterior.rotulo || "o conjunto anterior"}</h4>
      <p className="break-words text-slate-600">Definição anterior: {meta.comparacao.definicao_anterior.descricao}</p>
      <List title="Em ambos" items={meta.comparacao.em_ambos}/>
      <List title="Somente no atual" items={meta.comparacao.somente_atual}/>
      <List title="Somente no anterior" items={meta.comparacao.somente_anterior}/>
      <List title="Indeterminados (não avaliáveis em algum dos dois, nunca tratados como fora)" items={meta.comparacao.indeterminados}/>
    </div>}
    {reusable && <div aria-label="Reutilizar conjunto" className="no-print flex flex-wrap gap-2">
      {hasTree && <button type="button" disabled={disabled || !meets.length} onClick={() => onSelection(meets)} className={button + " text-teal"}>
        Usar os que atendem como seleção territorial ({meets.length})</button>}
      {!!chosen.length && <button type="button" disabled={disabled} onClick={() => onSelection(chosen)} className={button + " text-teal"}>
        Usar os selecionados como seleção territorial ({chosen.length})</button>}
      {hasTree && <button type="button" disabled={disabled || !meets.length} onClick={() => onReferences(meets)} className={button + " text-amber-900"}>
        Usar os que atendem como referências</button>}
    </div>}
  </section>;
}
