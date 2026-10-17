import { useEffect, useMemo, useState } from "react";
import { identity, parameterLabels, parameterValue, selectionCompatibility, type InvestigationEntry } from "./investigation";
import { displayPeriod } from "./representation";
import { ANALYSIS_LABELS, type Operation } from "./analysisCatalog";

type Props = { items: InvestigationEntry[]; currentId: string | null; selected: string[]; busy: boolean;
  onOpen: (id: string) => void; onTransfer: (id: string) => void; onPrepare: () => void };
const button = "rounded-lg border border-line bg-white px-3 py-2 text-xs font-semibold text-teal disabled:opacity-40";
const PAGE = 6;

export function ResultIdentity({ entry }: { entry: InvestigationEntry }) {
  const info = useMemo(() => identity(entry), [entry]);
  return <section aria-label="Identidade do resultado" className="my-4 rounded-xl border border-line bg-slate-50 p-4 text-xs leading-5">
    <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-[auto_minmax(0,1fr)]">
      <dt className="font-semibold">Fonte</dt><dd className="break-words">{info.source}</dd>
      <dt className="font-semibold">Indicadores e unidades</dt><dd>{info.indicators.join("; ") || "Consulte as colunas e as notas deste resultado."}</dd>
      <dt className="font-semibold">Períodos e categorias</dt><dd>{info.periods.map(displayPeriod).join(", ")} · {info.categories.join(", ")}</dd>
      <dt className="font-semibold">Recorte territorial</dt><dd>{info.scope}</dd>
      <dt className="font-semibold">Situação informada pelo motor</dt><dd>{info.status}</dd>
    </dl>
    <details className="mt-3"><summary className="cursor-pointer font-semibold text-teal">Origem e parâmetros desta execução</summary>
      <p className="mt-2 break-all">Resultado: {entry.result.result_id} · Versão da base: {info.version}</p>
      <p>Método: {info.method}{info.createdAt ? " · " + new Date(info.createdAt).toLocaleString("pt-BR") : ""}</p>
      <p className="mt-2">Territórios: {info.members.map(m => m.label).join("; ") || "Consulte o recorte no resultado."}</p>
      <dl className="mt-2 space-y-1">{Object.entries(parameterLabels).filter(([key]) => info.options[key] !== undefined && info.options[key] !== "")
        .map(([key, label]) => <div key={key}><dt className="inline font-semibold">{label}: </dt><dd className="inline">{parameterValue(info.options[key])}</dd></div>)}</dl>
      <p className="mt-2">Referências, critérios e demais condições completos estão em “Método e parâmetros” e nas notas do resultado.</p>
    </details>
  </section>;
}

export default function InvestigationOverview(p: Props) {
  const [page, setPage] = useState(0);
  const current = p.items.find(i => i.result.result_id === p.currentId);
  const pages = Math.max(1, Math.ceil(p.items.length / PAGE));
  useEffect(() => { const index = p.items.findIndex(i => i.result.result_id === p.currentId); if (index >= 0) setPage(Math.floor(index / PAGE)); }, [p.currentId, p.items.length]);
  // Descreve apenas a página visível; não retém listas territoriais de todas as etapas.
  const entries = useMemo(() => p.items.slice(page * PAGE, (page + 1) * PAGE)
    .map((entry, offset) => ({entry, info: identity(entry), index: page * PAGE + offset})), [p.items, page]);
  const dimensions = useMemo(() => new Set(p.items.map(e => e.result.metadata.operation)).size, [p.items]);
  return <section id="investigacao" aria-label="Investigação territorial" data-testid="investigation-overview" className="no-print my-4 rounded-2xl border border-blue-100 bg-blue-50/40 p-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 className="font-semibold text-ink">Sua investigação territorial</h2>
        <p className="mt-1 text-xs text-slate-600">{p.items.length} {p.items.length === 1 ? "resultado disponível" : "resultados disponíveis"} · {dimensions} dimensões analíticas</p></div>
      <button type="button" className={button} onClick={p.onPrepare}>Acrescentar uma análise</button>
    </div>
    <p className="my-3 text-xs leading-5 text-slate-600">Cada análise conserva sua fonte, recorte e parâmetros. Abrir resultados ou destacar territórios não executa cálculos.
      {p.selected.length > 0 && ` Seleção visual ativa: ${p.selected.length} território(s).`}</p>
    {p.busy && <p role="status" className="my-2 text-xs font-semibold text-teal">Preparando a próxima análise. Os resultados concluídos permanecem disponíveis abaixo.</p>}
    {!p.items.length && <p className="text-xs text-slate-600">Execute a primeira análise para iniciar esta investigação.</p>}
    <ol className="grid gap-3 sm:grid-cols-2">{entries.map(({entry, info, index}) => {
      const active = entry.result.result_id === p.currentId;
      const link = current && !active ? selectionCompatibility(current, entry) : null;
      return <li key={entry.result.result_id} data-testid="investigation-card" className={"min-w-0 rounded-xl border p-3 " + (active ? "border-blue-400 bg-white" : "border-line bg-white/80")}>
        <div className="flex flex-wrap justify-between gap-2 text-xs"><strong>Etapa {index + 1} · {ANALYSIS_LABELS[info.operation as Operation] || info.operation}</strong>
          <span>{active ? "Em exibição" : "Resultado anterior"}</span></div>
        <p className="mt-2 text-sm font-semibold text-ink">{entry.result.title}</p>
        <p className="mt-1 text-xs text-slate-600">{info.periods.map(displayPeriod).join(", ")} · {info.categories.join(", ")}</p>
        <p className="mt-1 text-xs text-slate-600">{info.members.length} territórios · {info.status}</p>
        <details className="mt-2 text-xs"><summary className="cursor-pointer text-teal">Ver contexto da etapa {index + 1}</summary>
          <p className="mt-2 break-words">{info.source} · {info.scope}</p><p>{info.indicators.join("; ")}</p><p>{entry.request}</p>
          <p>{info.createdAt && new Date(info.createdAt).toLocaleString("pt-BR")}</p>
        </details>
        {link && <p data-testid="selection-compatibility" className="mt-2 text-xs leading-5 text-slate-600">{link.allowed
          ? "Destaque territorial compatível. " + (link.differences.length ? link.differences.join("; ") + ". " : "") + "Isso não autoriza comparar valores ou transferir classes."
          : "Somente consulta independente: " + link.reasons.join(" ")}</p>}
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className={button} disabled={active || p.busy} aria-current={active ? "step" : undefined}
            data-testid={"open-investigation-" + index} onClick={() => p.onOpen(entry.result.result_id)}>Abrir etapa {index + 1}</button>
          {link && p.selected.length > 0 && <button type="button" className={button} disabled={!link.allowed || p.busy}
            data-testid={"transfer-selection-" + index} onClick={() => p.onTransfer(entry.result.result_id)}>Destacar seleção nesta análise</button>}
        </div>
      </li>;
    })}</ol>
    {pages > 1 && <nav aria-label="Etapas da investigação" className="mt-3 flex items-center justify-between gap-2 text-xs">
      <button type="button" className={button} disabled={page === 0} onClick={() => setPage(page - 1)}>Etapas anteriores</button>
      <span>Página {page + 1} de {pages}</span>
      <button type="button" className={button} disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Etapas seguintes</button>
    </nav>}
    <p className="mt-3 text-xs text-slate-500">Investigação temporária nesta aba. Recarregar, encerrar ou expirar a sessão descarta os resultados; exporte o que deseja conservar.</p>
  </section>;
}
