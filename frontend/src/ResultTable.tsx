import { useEffect, useMemo, type ReactNode } from "react";
import { useInvestigationState } from "./InvestigationViewState";
import type { Row } from "./representation";

// display: texto de apresentação (ex.: competência 201406 como 06/2014); a busca aceita o texto e o valor original.
type Column = { key: string; label?: string; render?: (value: unknown) => ReactNode; display?: (value: unknown) => string };
export type TablePresentation = { filtros: Record<string, string>; ordenacao: { key: string; ascending: boolean } | null;
  pagina: number; tamanho_pagina: number; total_filtrado: number };
type Props = { stateKey?: string; rows: Row[]; columns: Column[]; idOf?: (row: Row) => string | null; selected?: Set<string>;
  onToggle?: (id: string) => void; onExport?: (rows: Row[]) => void; exportLabel?: string;
  onPresentation?: (state: TablePresentation) => void; stacked?: boolean };
const PAGE_SIZE = 150;
const plain = (value: unknown) => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
const show = (value: unknown) => value == null ? "Não avaliável" : typeof value === "number"
  ? new Intl.NumberFormat("pt-BR", value !== 0 && Math.abs(value) < 1e-6
    ? { notation: "scientific", maximumSignificantDigits: 8 } : { maximumFractionDigits: 6 }).format(value) : String(value);

// Filtros são apenas de apresentação: não alteram indicadores, classes nem a seleção territorial.
function matches(value: unknown, query: string, display?: (value: unknown) => string): boolean {
  if (!query.trim()) return true;
  if (display && plain(display(value)).includes(plain(query.trim()))) return true;
  const comparison = query.trim().match(/^(>=|<=|>|<|=)\s*(-?\d+(?:[.,]\d+)?)$/);
  if (comparison) {
    if (typeof value !== "number") return false;
    const target = Number(comparison[2].replace(",", "."));
    return comparison[1] === ">=" ? value >= target : comparison[1] === "<=" ? value <= target :
      comparison[1] === ">" ? value > target : comparison[1] === "<" ? value < target : value === target;
  }
  const search = plain(query.trim());
  return plain(value == null ? "Não avaliável" : value).includes(search) || plain(show(value)).includes(search);
}

export default function ResultTable({ rows, columns, idOf, selected, onToggle, onExport,
  exportLabel = "Exportar tabela filtrada (CSV)", onPresentation, stateKey = "main", stacked = false }: Props) {
  const [filters, setFilters] = useInvestigationState<Record<string, string>>(stateKey + ".filters", {});
  const [sort, setSort] = useInvestigationState<{ key: string; ascending: boolean } | null>(stateKey + ".sort", null);
  const [page, setPage] = useInvestigationState(stateKey + ".page", 0);
  const displayOf = (key: string) => columns.find(column => column.key === key)?.display;
  const text = (key: string, value: unknown) => displayOf(key)?.(value) ?? show(value);
  const filtered = useMemo(() => {
    const chosen = rows.filter(row => Object.entries(filters).every(([key, query]) => matches(row[key], query, displayOf(key))));
    if (sort) chosen.sort((a, b) => {
      const left = a[sort.key], right = b[sort.key];
      if (left == null) return right == null ? 0 : 1;
      if (right == null) return -1;
      return (typeof left === "number" && typeof right === "number" ? left - right :
        String(left).localeCompare(String(right), "pt-BR", { numeric: true })) * (sort.ascending ? 1 : -1);
    });
    return chosen;
  }, [rows, filters, sort]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages - 1);
  const visible = filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);
  const hasFilters = Object.values(filters).some(value => value.trim());
  useEffect(() => { onPresentation?.({ filtros: filters, ordenacao: sort, pagina: current + 1,
    tamanho_pagina: PAGE_SIZE, total_filtrado: filtered.length }); }, [filters, sort, current, filtered.length, onPresentation]);
  return <div data-testid="result-table">
    <div className="no-print flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3 text-xs">
      <p>{filtered.length.toLocaleString("pt-BR")} de {rows.length.toLocaleString("pt-BR")} registros
        {hasFilters ? " · filtros da tabela aplicados" : " · filtre pelas colunas abaixo"}</p>
      <div className="flex flex-wrap gap-2">
        {hasFilters && <button type="button" className="text-teal underline" onClick={() => { setFilters({}); setPage(0); }}>Limpar filtros da tabela</button>}
        {onExport && <button type="button" disabled={!filtered.length} onClick={() => onExport(filtered)}
          className="rounded-lg border border-line px-3 py-2 font-semibold text-teal disabled:opacity-40">{exportLabel}</button>}
      </div>
    </div>
    {sort && <p className="no-print px-4 py-2 text-xs text-slate-600">Ordenação da tabela apenas para consulta; as posições calculadas na análise são preservadas.</p>}
    {stacked && <details className="no-print px-4 py-3 text-xs">
      <summary className="cursor-pointer font-semibold text-teal">Filtrar e ordenar a comparação</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{columns.map(column => <div key={column.key} className="min-w-0">
        <button type="button" aria-label={"Ordenar tabela por " + (column.label || column.key)}
          onClick={() => {setSort({key: column.key, ascending: sort?.key === column.key ? !sort.ascending : true});setPage(0);}}
          className="mb-1 font-semibold">{column.label || column.key}{sort?.key === column.key ? sort.ascending ? " ↑" : " ↓" : ""}</button>
        <input aria-label={"Filtrar " + (column.label || column.key)} value={filters[column.key] || ""}
          placeholder={rows.some(row => typeof row[column.key] === "number") ? "Ex.: >= 2" : "Buscar..."}
          onChange={event => {setFilters(previous => ({...previous, [column.key]: event.target.value}));setPage(0);}}
          className="w-full rounded-md border border-line px-2 py-2"/>
      </div>)}</div>
    </details>}
    {stacked && <div className="space-y-3 p-4" aria-label="Comparação em registros separados">
      {visible.map((row, index) => {
        const id = idOf?.(row), chosen = !!id && !!selected?.has(id);
        if (row["Objeto A"] != null && row["Objeto B"] != null) return <div key={index} className="space-y-3 rounded-xl border border-line p-3">
          {(["A", "B"] as const).map(side => <article key={side} data-testid="comparison-territory-row" className="rounded-lg border border-line bg-white p-4">
            <h5 className="font-semibold text-ink">{show(row["Objeto " + side])}</h5>
            <dl className="mt-2 grid gap-2 sm:grid-cols-2">
              {["Período", "Categoria", "Indicador", "Unidade de contagem", "Valor " + side].map(key => <div key={key} className="min-w-0">
                <dt className="text-xs text-slate-500">{key.startsWith("Valor ") ? "Valor" : key}</dt>
                <dd className="break-words text-sm" title={typeof row[key] === "number" ? "Valor integral: " + String(row[key]) : undefined}>{text(key, row[key])}</dd>
              </div>)}
            </dl>
          </article>)}
          <dl data-testid="comparison-pair-summary" className="grid gap-2 px-1 sm:grid-cols-2">
            {columns.filter(column => !["Objeto A", "Objeto B", "Valor A", "Valor B", "Período", "Categoria", "Indicador", "Unidade de contagem"].includes(column.key)).map(column =>
              <div key={column.key}><dt className="text-xs text-slate-500">{column.label || column.key}</dt>
                <dd className="break-words text-sm" title={typeof row[column.key] === "number" ? "Valor integral: " + String(row[column.key]) : undefined}>{text(column.key, row[column.key])}</dd></div>)}
          </dl>
        </div>;
        return <article data-testid="comparison-territory-row" key={id ? id + ":" + index : index}
          className={"rounded-xl border p-4 " + (chosen ? "border-blue-400 bg-blue-50" : "border-line bg-white")}>
          <div className="mb-3 flex items-center justify-between gap-3">
            <strong className="text-sm text-ink">{show(row["Território"] || "Território " + (current * PAGE_SIZE + index + 1))}</strong>
            {id && onToggle && <button type="button" onClick={()=>onToggle(id)}
              aria-pressed={chosen} className="text-xs font-semibold text-teal underline">{chosen ? "Retirar da seleção" : "Selecionar território"}</button>}
          </div>
          <dl className="grid gap-2 sm:grid-cols-2">
            {columns.map(column=><div key={column.key} className="min-w-0 border-b border-slate-100 pb-2">
              <dt className="text-xs font-medium text-slate-500">{column.label || column.key}</dt>
              <dd className="break-words text-sm text-ink" title={typeof row[column.key] === "number" ? "Valor integral: " + String(row[column.key]) : undefined}>
                {column.render ? column.render(row[column.key]) : text(column.key, row[column.key])}
              </dd>
            </div>)}
          </dl>
        </article>;
      })}
    </div>}
    {!stacked && <div className="max-h-[520px] overflow-auto"><table className="data-table w-full">
      <thead className="sticky top-0 z-10 bg-slate-50"><tr>{columns.map(column => <th key={column.key}
        aria-sort={sort?.key === column.key ? sort.ascending ? "ascending" : "descending" : "none"}>
        <button type="button" className="text-left" aria-label={"Ordenar tabela por " + (column.label || column.key)} onClick={() => {
          setSort({ key: column.key, ascending: sort?.key === column.key ? !sort.ascending : true }); setPage(0);
        }}>{column.label || column.key}{sort?.key === column.key ? sort.ascending ? " ↑" : " ↓" : ""}</button>
      </th>)}</tr>
        <tr className="no-print">{columns.map(column => <th key={column.key} className="p-2">
          <input aria-label={"Filtrar " + (column.label || column.key)} value={filters[column.key] || ""}
            placeholder={rows.some(row => typeof row[column.key] === "number") ? "Ex.: >= 2" : "Buscar..."}
            onChange={event => { setFilters(previous => ({ ...previous, [column.key]: event.target.value })); setPage(0); }}
            className="w-full min-w-24 rounded-md border border-line bg-white px-2 py-2 text-xs font-normal normal-case tracking-normal"/>
        </th>)}</tr>
      </thead>
      <tbody>{visible.map((row, index) => {
        const id = idOf?.(row), chosen = !!id && !!selected?.has(id);
        return <tr key={id ? id + ":" + index : index} aria-selected={id && onToggle ? chosen : undefined}
          tabIndex={id && onToggle ? 0 : undefined} onClick={id && onToggle ? () => onToggle(id) : undefined}
          onKeyDown={id && onToggle ? event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onToggle(id); } } : undefined}
          className={(id && onToggle ? "cursor-pointer " : "") + (chosen ? "bg-blue-50 outline outline-1 outline-blue-300" : "")}>
          {columns.map(column => <td key={column.key} title={typeof row[column.key] === "number" ? "Valor integral: " + String(row[column.key]) : undefined}>
            {column.render ? column.render(row[column.key]) : text(column.key, row[column.key])}</td>)}
        </tr>;
      })}</tbody>
    </table></div>}
    {!filtered.length && <p role="status" className="px-4 py-5 text-xs text-slate-600">Nenhum registro corresponde aos filtros da tabela.</p>}
    {pages > 1 && <nav aria-label="Páginas da tabela" className="no-print flex flex-wrap items-center justify-between gap-2 border-t border-line p-3 text-xs">
      <button type="button" disabled={current === 0} onClick={() => setPage(current - 1)} className="rounded-lg border px-3 py-2 disabled:opacity-40">Página anterior</button>
      <span>Página {current + 1} de {pages} · até {PAGE_SIZE} registros por página</span>
      <button type="button" disabled={current === pages - 1} onClick={() => setPage(current + 1)} className="rounded-lg border px-3 py-2 disabled:opacity-40">Próxima página</button>
    </nav>}
  </div>;
}
