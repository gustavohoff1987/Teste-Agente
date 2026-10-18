import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { BarChart3, Map as MapIcon, Search, Table2, X } from "lucide-react";
import { useInvestigationState } from "./InvestigationViewState";
import TerritoryMap, { type MapHandle } from "./TerritoryMap";
import CriteriaResults, { type CriteriaMetadata } from "./CriteriaResults";
import DistributionResults from "./DistributionResults";
import ResultTable, { type TablePresentation } from "./ResultTable";
import { CountBars, SeriesLines, TerritoryBars, type BarDatum, type CountDatum, type LinePoint } from "./ResultCharts";
import {
  CATEGORICAL, INK, NOT_EVALUABLE, ORDINAL, STATE_COLORS, STATE_LABELS, codeOf, displayPeriod, formatNumber, formatPair, formatValue,
  fullPrecision, labelIndex, representationOf, rowLinker, sequentialColor, tableOf, type Indicator, type ResultLike, type Row,
} from "./representation";

// Painel único do resultado (CAP-REP-04: justaposição de tabela, gráficos e mapa dos mesmos
// resultados, sem cálculo entre eles). Seleção, filtro, indicador e enquadramento são estado visual
// (RQ-REP-06): nada aqui inicia análise; reutilizar a seleção só prepara a próxima solicitação.

type View = "mapa" | "graficos" | "tabela";
export type Sibling = { id: string; period: string; current: boolean };
export type RepresentationRecord = Record<string, unknown>;
type Props = {
  result: ResultLike & { total_rows: number; notes: string[] };
  operation: string;
  reusable: boolean;
  disabled: boolean;
  status: string;
  siblings: Sibling[];
  onOpenSibling: (id: string) => void;
  onExport: (rows: Row[]) => void;
  onReuseSelection: (ids: string[]) => void;
  onReferences: (ids: string[]) => void;
  onRepresentation: (record: RepresentationRecord) => void;
};
type StateFilter = "TODOS" | "MINHA_SELECAO" | string;

const pretty = (value: unknown) => value === null || value === undefined ? "Não avaliável" :
  typeof value === "number" ? new Intl.NumberFormat("pt-BR", value !== 0 && Math.abs(value) < 1e-6
    ? { notation: "scientific", maximumSignificantDigits: 8 } : { maximumFractionDigits: 6 }).format(value) : String(value);
const MAX_LINES = 8;
const MAX_LINKS = 30;
const chip = (active: boolean) => "flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg border px-3 text-xs " +
  (active ? "border-violet-500 bg-violet-50" : "border-line bg-white");
const button = "inline-flex items-center gap-1.5 rounded-lg border border-line bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40";

export default function ResultWorkspace(p: Props) {
  const { result, operation } = p;
  const rep = useMemo(() => representationOf(result), [result]);
  const rows = useMemo(() => rep ? tableOf(result, rep) : result.rows, [result, rep]);
  const linker = useMemo(() => rep ? rowLinker(result, rep) : () => null, [result, rep]);
  const rowIds = useMemo(() => rows.map(row => linker(row)), [rows, linker]);
  const rowsById = useMemo(() => {
    const byId = new Map<string, Row>();
    rows.forEach((row, index) => { const id = rowIds[index]; if (id && !byId.has(id)) byId.set(id, row); });
    return byId;
  }, [rows, rowIds]);
  const labels = useMemo(() => labelIndex(result), [result]);
  const labelOf = (id: string) => labels.get(id) || (id.startsWith("name:") ? id.slice(5) : codeOf(id) || id);
  const geometry = rep?.geometria;
  const points = useMemo(() => geometry?.estado === "DISPONIVEL" && geometry.ids ? { ids: geometry.ids, lat: geometry.lat!, lon: geometry.lon! } : null,
    [geometry]);
  const mappable = useMemo(() => (rep?.indicadores || []).filter(item => item.tipo !== "POSICAO"), [rep]);
  const numeric = useMemo(() => (rep?.indicadores || []).filter(item => item.tipo === "CONTINUO" || item.tipo === "CONTAGEM"), [rep]);
  const [indicatorColumn, setIndicatorColumn] = useInvestigationState("indicatorColumn", () => mappable[0]?.coluna || "");
  const indicator = mappable.find(item => item.coluna === indicatorColumn) || mappable[0];
  const [barColumn, setBarColumn] = useInvestigationState("barColumn", () => numeric[0]?.coluna || "");
  const barIndicator = numeric.find(item => item.coluna === barColumn) || numeric[0];
  // Indicador compartilhado: o escolhido no mapa vale para as barras (e vice-versa) quando ambos o representam.
  const chooseIndicator = (column: string) => {
    setIndicatorColumn(column);
    if (numeric.some(item => item.coluna === column)) setBarColumn(column);
  };
  const chooseBar = (column: string) => {
    setBarColumn(column);
    if (mappable.some(item => item.coluna === column)) setIndicatorColumn(column);
  };
  const [view, setView] = useInvestigationState<View>("view", () => points ? "mapa" : (rep?.serie || numeric.length) ? "graficos" : "tabela");
  const [selected, setSelected] = useInvestigationState<string[]>("selected", []);
  const [focusId, setFocusId] = useInvestigationState<string | null>("focusId", null);
  const [multi, setMulti] = useInvestigationState("multi", false);
  const [notice, setNotice] = useState("");
  const [barOrder, setBarOrder] = useInvestigationState<"codigo" | "resultado" | "valor">("barOrder", operation === "ranking" ||
    (operation === "criteria" && !!(result.metadata.criterios as CriteriaMetadata | undefined)?.ordenacao) ? "resultado" : "codigo");
  const [lineCategory, setLineCategory] = useInvestigationState("lineCategory", "");
  const [linePage, setLinePage] = useInvestigationState("linePage", 0);
  const previousSeriesFilter = useRef({selected, lineCategory});
  useEffect(() => {
    if (previousSeriesFilter.current.selected !== selected || previousSeriesFilter.current.lineCategory !== lineCategory) setLinePage(0);
    previousSeriesFilter.current = {selected, lineCategory};
  }, [selected, lineCategory]);
  const [tablePresentation, setTablePresentation] = useState<TablePresentation | null>(null);
  const mapRef = useRef<MapHandle>(null);
  const selectedSet = useMemo(() => new Set(selected), [selected]);
  const criteriaMeta = result.metadata.criterios as (CriteriaMetadata & { avaliacoes?: CriteriaEvaluation[] }) | undefined;
  const criteriaHasTree = !!criteriaMeta?.contagens;
  const [filter, setFilter] = useInvestigationState<StateFilter>("filter", operation === "criteria" && criteriaHasTree ? "ATENDE" : "TODOS");

  // Estados produzidos pelo motor que os filtros visuais usam (nunca recalculados aqui).
  const stateOf = useMemo(() => {
    if (operation === "criteria") return (id: string) => String(rowsById.get(id)?.["Resultado"] ?? "");
    if (operation === "nearest") return (id: string) => String(rowsById.get(id)?.["Alcance"] ?? "");
    return () => "";
  }, [operation, rowsById]);
  const engineSelected = useMemo(() => new Set((criteriaMeta?.selecao?.membros || []).map(item => item.id)), [criteriaMeta]);
  const passesFilter = (id: string) => filter === "TODOS" ? true : filter === "MINHA_SELECAO" ? selectedSet.has(id) :
    filter === "SELECIONADOS" ? engineSelected.has(id) : stateOf(id) === filter;

  const references = useMemo(() => {
    const nearest = result.metadata.nearest_reference as { conjunto_referencias?: { membros?: { id: string }[] } } | undefined;
    const ids = [...(nearest?.conjunto_referencias?.membros || []), ...(criteriaMeta?.referencias?.membros || [])].map(item => item.id);
    if (operation === "spatial") {
      const label = String((result.metadata.options as Record<string, unknown> | undefined)?.reference_territory || "");
      const member = [...labels.entries()].find(([, value]) => value === label);
      if (member) ids.push(member[0]);
    }
    return new Set(ids);
  }, [result, criteriaMeta, operation, labels]);

  // Vínculos já calculados: referência(s) mais próxima(s) e distância do motor por alvo.
  const nearestRecords = useMemo(() => {
    const records = new Map<string, NearestLink>();
    const nearest = result.metadata.nearest_reference as { cobertura_referencias?: NearestRecord[] } | undefined;
    for (const record of nearest?.cobertura_referencias || []) {
      const scope = record.minimo_completo.avaliabilidade === "AVALIAVEL" ? record.minimo_completo :
        record.minimo_avaliaveis.avaliabilidade === "AVALIAVEL" ? record.minimo_avaliaveis : null;
      records.set(record.unidade, { refs: scope?.referencias || [], distance: scope?.distancia_km ?? null, reach: scope?.alcance || "não avaliável",
        partial: scope === record.minimo_avaliaveis, accepted: false, alsoReference: record.alvo_e_referencia, origin: record.coordenada });
    }
    for (const item of criteriaMeta?.avaliacoes || []) {
      const node = Object.values(item.nos).find(entry => "referencias" in entry && entry.referencias !== undefined);
      if (node) records.set(item.elemento, { refs: node.referencias || [], distance: typeof node.valor === "number" ? node.valor : null,
        reach: node.alcance || "não avaliável", partial: String(node.alcance || "").startsWith("entre"), accepted: true,
        alsoReference: (node.referencias || []).includes(item.elemento) });
    }
    if (operation === "spatial") {
      const target = [...references][0];
      for (const [id, row] of rowsById) records.set(id, { refs: target ? [target] : [], distance: typeof row["Distância (km)"] === "number" ? row["Distância (km)"] as number : null,
        reach: "distância ao território de referência", partial: false, accepted: false, alsoReference: id === target });
    }
    return records;
  }, [result, criteriaMeta, operation, references, rowsById]);

  // Valores e cores por ponto do mapa (mapeamento visual; domínio fixo em todo o resultado).
  const encoding = useMemo(() => {
    if (!points || !indicator) return null;
    const universe = points.ids.map(id => rowsById.has(id));
    const raw = points.ids.map(id => rowsById.get(id)?.[indicator.coluna]);
    if (indicator.tipo === "CONTINUO" || indicator.tipo === "CONTAGEM") {
      const values = raw.map(value => typeof value === "number" ? value : null);
      let min = Infinity, max = -Infinity;
      values.forEach((value, i) => { if (value !== null && universe[i]) { min = Math.min(min, value); max = Math.max(max, value); } });
      const span = max - min;
      const fills = values.map((value, i) => !universe[i] ? INK.surface : value === null ? null :
        sequentialColor(span > 0 ? (value - min) / span : 0.5));
      return { fills, domain: Number.isFinite(min) ? [min, max] as [number, number] : null, classes: null as string[] | null };
    }
    const classes = indicator.classes || [];
    const palette = indicator.tipo === "CLASSE" && indicator.origem === "CAP-DIS-02" ? ORDINAL : CATEGORICAL;
    const colorOfClass = (value: string) => STATE_COLORS[value] || (value === "NAO_AVALIAVEL" || value === "Não avaliável" ? null :
      palette[Math.max(0, classes.indexOf(value)) % palette.length]);
    const fills = raw.map((value, i) => !universe[i] ? INK.surface : value === null || value === undefined || value === "" ? null :
      colorOfClass(String(value)));
    return { fills, domain: null, classes };
  }, [points, indicator, rowsById]);
  const passes = useMemo(() => points ? points.ids.map(id => passesFilter(id)) : [], [points, filter, selectedSet, stateOf, engineSelected]);
  const connections = useMemo(() => selected.slice(0, MAX_LINKS).map(id => ({ from: id, to: nearestRecords.get(id)?.refs || [] }))
    .filter(item => item.to.length), [selected, nearestRecords]);

  const valueLine = (id: string) => {
    if (!indicator) return "";
    const row = rowsById.get(id);
    if (!row) return references.has(id) ? "Referência (fora do universo-alvo)" : "Sem linha no resultado";
    const value = row[indicator.coluna];
    const unit = indicator.unidade ? " " + indicator.unidade : "";
    return indicator.rotulo + ": " + (typeof value === "number" ? formatNumber(value, indicator.tipo) + unit : formatValue(value, indicator.tipo));
  };

  function select(id: string, additive: boolean) {
    setFocusId(id);
    setSelected(current => additive || multi ? (current.includes(id) ? current.filter(item => item !== id) : [...current, id]) :
      current.length === 1 && current[0] === id ? current : [id]);
  }
  function toggle(id: string) {
    setFocusId(id);
    setSelected(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id]);
  }

  // Registro das transformações desta representação (exportado com “Método e parâmetros”).
  useEffect(() => {
    p.onRepresentation({
      resultado: result.result_id, visao: view, indicador: indicator ? { coluna: indicator.coluna, unidade: indicator.unidade, tipo: indicator.tipo,
        origem: indicator.origem } : null,
      escala: indicator && (indicator.tipo === "CONTINUO" || indicator.tipo === "CONTAGEM") ? { tipo: "mapeamento visual contínuo linear",
        dominio: encoding?.domain, rampa: "azul sequencial (passos 250 a 700)", classificacao: false } :
        indicator ? { tipo: "classes ou estados produzidos por " + (indicator.origem || "capacidade"), classes: indicator.classes } : null,
      filtro_visual: filter, selecao_visual: selected, arredondamento: "RQ-REP-05: duas casas para medidas contínuas, inteiros para contagens",
      projecao: points ? "equirretangular (longitude × cos da latitude média), somente para desenho" : null,
      geometria: geometry ? { estado: geometry.estado, competencia: geometry.competencia, referencial: geometry.referencial,
        complemento_geografico: geometry.complemento_geografico ?? null } : null,
      ordem_barras: barOrder,
      tabela: tablePresentation,
      series: rep?.serie ? { pagina_territorios: linePage + 1, limite_por_pagina: MAX_LINES, categoria: lineCategory || null } : null,
    });
  }, [view, indicator, filter, selected, barOrder, encoding, tablePresentation, linePage, lineCategory]);

  // Gancho de teste (só com window.__ADT_TEST__): o modelo desenhado, para conferência com o resultado.
  useEffect(() => {
    const scope = window as unknown as { __ADT_TEST__?: boolean; __adtMapModel?: unknown };
    if (!scope.__ADT_TEST__) return;
    scope.__adtMapModel = points && encoding ? { resultId: result.result_id, ids: points.ids, lat: points.lat, lon: points.lon,
      fills: encoding.fills, passes, references: [...references], selected, focusId, indicator: indicator?.coluna, domain: encoding.domain,
      connections } : { resultId: result.result_id, geometry: geometry?.estado || null };
  }, [points, encoding, passes, references, selected, focusId, connections]);

  const missing = geometry?.sem_geometria || [];
  const filterOptions: { key: string; label: string }[] = operation === "nearest"
    ? [{ key: "TODOS", label: "Todos" }, { key: "Conjunto completo de referências", label: "Mínimo do conjunto completo" },
      { key: "Entre as referências avaliáveis", label: "Somente entre avaliáveis" }, { key: "Não avaliável", label: "Não avaliáveis" }]
    : [{ key: "TODOS", label: "Todos" }];
  const sharedFilter = operation !== "criteria" && <div role="radiogroup" aria-label="Filtro visual dos territórios" className="no-print flex flex-wrap gap-2">
    {[...filterOptions, { key: "MINHA_SELECAO", label: "Minha seleção (" + selected.length + ")" }].map(item =>
      <label key={item.key} className={chip(filter === item.key)}>
        <input type="radio" className="sr-only" name={"filtro-visual-" + result.result_id} checked={filter === item.key} onChange={() => setFilter(item.key)}/>
        {item.label}</label>)}
  </div>;

  const visual = <section aria-label="Exploração visual" className="mt-5 space-y-3">
    <div className="no-print flex flex-wrap items-center justify-between gap-2">
      <div role="tablist" aria-label="Forma de visualização" className="flex w-full min-w-0 flex-wrap rounded-xl border border-line bg-slate-50 p-1 sm:inline-flex sm:w-auto">
        {([["mapa", "Mapa", MapIcon], ["graficos", "Gráficos", BarChart3], ["tabela", "Tabela", Table2]] as const).map(([key, label, Icon]) =>
          <button key={key} type="button" role="tab" aria-selected={view === key} onClick={() => setView(key)}
            className={"inline-flex min-h-9 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold " + (view === key ? "bg-white text-ink shadow-sm" : "text-slate-600")}>
            <Icon size={15}/>{label}{key === "mapa" && !points && geometry && <span className="font-normal text-slate-500">
              ({geometry.estado === "NAO_APLICAVEL" ? "não aplicável" : "indisponível"})</span>}</button>)}
      </div>
      {p.siblings.length > 1 && <nav aria-label="Competências deste pedido" className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
        Competências calculadas:{p.siblings.map(item => <button key={item.id} type="button" aria-current={item.current}
          onClick={() => p.onOpenSibling(item.id)} className={"rounded-lg border px-2 py-1 " + (item.current ? "border-blue-500 bg-blue-50 font-semibold" : "border-line bg-white")}>
          {displayPeriod(item.period)}</button>)}
      </nav>}
    </div>
    {p.status !== "VIGENTE" && <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
      {p.status === "INVALIDADO" ? "Resultado invalidado: disponível apenas para consulta." :
        "Você está consultando uma análise anterior, com as opções usadas naquele cálculo. Para atualizar, revise a preparação e calcule novamente."}</p>}
    {view === "mapa" && renderMap()}
    {view === "graficos" && renderCharts()}
    {view === "tabela" && <p className="text-xs text-slate-600">Visualização em tabela: os valores, estados e motivos estão na tabela abaixo,
      a mesma usada pelo mapa e pelos gráficos.</p>}
    {renderSelection()}
  </section>;

  function renderMap() {
    if (!geometry || !rep) return <Unavailable reason="O resultado não traz o contrato de apresentação; consulte a tabela."/>;
    if (!points || !encoding || !indicator) return <Unavailable reason={geometry.motivo || "Mapa indisponível."} pending={geometry.pendencia}/>;
    const period = displayPeriod(geometry.competencia);
    return <div className="space-y-3">
      <div className="no-print flex flex-wrap items-end gap-3">
        {mappable.length > 1 && <label className="flex w-full min-w-0 flex-col gap-1 text-xs font-semibold text-slate-700 sm:w-auto sm:max-w-xs">Indicador representado
          <select aria-label="Indicador representado" value={indicator.coluna} onChange={event => chooseIndicator(event.target.value)}
            className="w-full min-w-0 rounded-lg border border-line bg-white px-2 py-2 text-sm font-normal">
            {mappable.map(item => <option key={item.coluna} value={item.coluna}>{item.rotulo}{item.unidade ? " (" + item.unidade + ")" : ""}</option>)}
          </select></label>}
        <TerritorySearch ids={[...new Set([...points.ids, ...missing.map(item => item.id)])]} labelOf={labelOf}
          onPick={id => { select(id, false); mapRef.current?.center(id); }}/>
        <label className="flex min-h-9 items-center gap-2 text-xs"><input type="checkbox" checked={multi} onChange={event => setMulti(event.target.checked)}/>
          Seleção múltipla (ou Shift + clique)</label>
      </div>
      <div className="result-map-layout grid gap-3">
        <TerritoryMap ref={mapRef} ids={points.ids} lat={points.lat} lon={points.lon} fills={encoding.fills} passes={passes}
          references={references} selected={selectedSet} focusId={focusId} connections={connections} labelOf={labelOf}
          detailOf={valueLine} onSelect={select}
          ariaLabel={"Mapa de pontos: " + points.ids.length + " territórios com coordenada válida em " + period + ", " + indicator.rotulo +
            ". Com o mapa em foco, as setas deslocam a vista, + e − ampliam ou reduzem e 0 volta à extensão completa. " +
            "Os mesmos valores estão na tabela abaixo; use a busca para selecionar um território pelo teclado."}/>
        <Legend indicator={indicator} domain={encoding.domain} counts={classCounts()} referencesShown={references.size > 0}
          linksShown={connections.length > 0}/>
      </div>
      <p className="text-xs leading-5 text-slate-600">
        {period}. Cada ponto representa a localização de um território (sede municipal na base Brasil).
        O conjunto dos pontos permite reconhecer a distribuição geográfica; não representa os limites territoriais.
        {geometry.configuracao_apresentacao && " Localização ilustrativa; a fonte original não informa o referencial das coordenadas. A premissa de apresentação está registrada em Método e parâmetros."}
        {connections.length > 0 && " Linhas tracejadas são ligações ilustrativas entre alvo e referência: a distância informada é a geodésica direta calculada pelo motor, não um trajeto viário."}
      </p>
      {rep.notas.length > 0 && <details className="text-xs text-slate-600"><summary className="cursor-pointer">Sobre a localização dos pontos</summary>
        {rep.notas.map(note => <p key={note} className="mt-2 leading-5">{note}</p>)}</details>}
      {missing.length > 0 && <details className="text-xs">
        <summary className="cursor-pointer font-semibold text-slate-700">Sem coordenada válida na competência ({missing.length}): no resultado e na tabela, fora do mapa</summary>
        <ul className="mt-2 max-h-40 space-y-1 overflow-auto">{missing.map(item => <li key={item.id}>
          <button type="button" className="text-left text-teal underline" onClick={() => select(item.id, false)}>{labelOf(item.id)}</button>
          {" — "}{item.texto || item.condicao}{item.motivo ? " (" + item.motivo + ")" : ""}</li>)}</ul>
      </details>}
    </div>;
  }

  function classCounts(): Record<string, number> | null {
    if (operation === "criteria" && criteriaMeta?.contagens) return { ATENDE: criteriaMeta.contagens.ATENDE,
      NAO_ATENDE: criteriaMeta.contagens.NAO_ATENDE, NAO_AVALIAVEL: criteriaMeta.contagens.NAO_AVALIAVEL };
    if (operation === "distribution") return Object.fromEntries(result.rows.map(row => [String(row["Classe"] ?? row["Quintil"] ?? "").split(" — ")[0], Number(row["Unidades"])]));
    return null;
  }

  function renderCharts() {
    const counts = countBars();
    const bars = territoryBars();
    const line = lineChart();
    return <div className="space-y-5">
      <div className="no-print flex flex-wrap items-end gap-3">
        {bars && numeric.length > 1 && <label className="flex w-full min-w-0 flex-col gap-1 text-xs font-semibold text-slate-700 sm:w-auto sm:max-w-xs">Indicador das barras
          <select aria-label="Indicador das barras" value={barIndicator?.coluna} onChange={event => chooseBar(event.target.value)}
            className="w-full min-w-0 rounded-lg border border-line bg-white px-2 py-2 text-sm font-normal">
            {numeric.map(item => <option key={item.coluna} value={item.coluna}>{item.rotulo}{item.unidade ? " (" + item.unidade + ")" : ""}</option>)}
          </select></label>}
        {bars && <label className="flex w-full min-w-0 flex-col gap-1 text-xs font-semibold text-slate-700 sm:w-auto sm:max-w-xs">Ordem das barras
          <select aria-label="Ordem das barras" value={barOrder} onChange={event => setBarOrder(event.target.value as typeof barOrder)}
            className="w-full min-w-0 rounded-lg border border-line bg-white px-2 py-2 text-sm font-normal">
            <option value="codigo">Código territorial (padrão)</option>
            {(operation === "ranking" || criteriaMeta?.ordenacao) && <option value="resultado">Ordem do resultado (ordenação do motor)</option>}
            <option value="valor">Valor, decrescente (apenas visual)</option>
          </select></label>}
      </div>
      {counts}
      {bars ? <div><h4 className="mb-1 text-sm font-bold text-ink">{bars.title}</h4>
        {barOrder === "valor" && <p className="mb-1 text-xs text-amber-900">Ordenação apenas visual: não constitui posição de ranking nem resultado.</p>}
        <TerritoryBars data={bars.data} unit={barIndicator?.unidade || ""} kind={barIndicator?.tipo || "CONTINUO"} title={bars.title}
          onSelect={id => select(id, true)}/></div> : null}
      {line}
      {!counts && !bars && !line && numeric.length === 0 && <p className="text-xs text-slate-600">Este resultado não tem valores compatíveis
        com gráficos de barras ou de linhas; consulte a tabela.</p>}
    </div>;
  }

  function countBars() {
    let data: CountDatum[] = [], title = "", note = "";
    if (operation === "criteria" && criteriaMeta?.contagens) {
      data = ["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"].map(key => ({ label: STATE_LABELS[key], value: (criteriaMeta.contagens as Record<string, number>)[key],
        color: key === "NAO_AVALIAVEL" ? NOT_EVALUABLE : STATE_COLORS[key] }));
      title = "Territórios por resultado dos critérios"; note = "Não avaliável é apresentado separadamente de não atende.";
    } else if (operation === "nearest") {
      const coverage = (result.metadata.nearest_reference as { cobertura?: { n_minimo_completo: number; n_somente_entre_avaliaveis: number;
        n_nao_avaliaveis_por_motivo: Record<string, number> } } | undefined)?.cobertura;
      if (coverage) {
        data = [{ label: "Mínimo do conjunto completo", value: coverage.n_minimo_completo, color: STATE_COLORS["Conjunto completo de referências"] },
          { label: "Somente entre avaliáveis", value: coverage.n_somente_entre_avaliaveis, color: STATE_COLORS["Entre as referências avaliáveis"] },
          ...Object.entries(coverage.n_nao_avaliaveis_por_motivo).map(([motive, n]) => ({ label: "Não avaliável: " + motive, value: n, color: NOT_EVALUABLE }))];
        title = "Alcance da distância por alvo"; note = "O mínimo entre as referências avaliáveis pode diferir do mínimo do conjunto completo.";
      }
    }
    if (operation === "distribution") {
      data = result.rows.map((row, index) => ({label: String(row.Classe ?? row.Quintil ?? ""), value: Number(row.Unidades), color: ORDINAL[index % ORDINAL.length]}));
      title = "Territórios por grupo da distribuição"; note = "Grupos e quantidades calculados na análise.";
    }
    const bands = criteriaMeta?.faixas;
    if (!data.length && !bands) return null;
    return <>
      {data.length > 0 && <div><h4 className="mb-1 text-sm font-bold text-ink">{title}</h4><CountBars data={data} title={title} note={note}/></div>}
      {bands && <div><h4 className="mb-1 text-sm font-bold text-ink">Faixas ({bands.convencao})</h4>
        <CountBars data={bands.faixas.map((item, index) => ({ label: item.faixa, value: item.n, color: ORDINAL[Math.min(index, ORDINAL.length - 1)] }))}
          title="Faixas" note="Limites escolhidos pelo usuário e contagens do motor; fora das faixas e não avaliáveis estão na tabela."/></div>}
    </>;
  }

  function territoryBars(): { data: BarDatum[]; title: string } | null {
    if (!barIndicator || rep?.serie) return null;
    const universe = [...rowsById.keys()];
    const ids = (selected.length ? selected.filter(id => rowsById.has(id)) : universe).filter(passesFilter);
    if (!ids.length) return null;
    const order = barOrder === "resultado" ? rowIds.filter((id): id is string => !!id && ids.includes(id))
      : barOrder === "valor" ? [...ids].sort((a, b) => (Number(rowsById.get(b)?.[barIndicator.coluna] ?? -Infinity)) - (Number(rowsById.get(a)?.[barIndicator.coluna] ?? -Infinity)))
      : [...ids].sort((a, b) => (codeOf(a) || a).localeCompare(codeOf(b) || b, "pt-BR", { numeric: true }));
    const data = [...new Set(order)].map(id => {
      const value = rowsById.get(id)?.[barIndicator.coluna];
      return { id, label: labelOf(id), value: typeof value === "number" ? value : null, highlighted: !selected.length || selectedSet.has(id) };
    });
    return { data, title: barIndicator.rotulo + (barIndicator.unidade ? " (" + barIndicator.unidade + ")" : "") +
      (selected.length ? " · territórios selecionados" : " · todos os territórios do resultado") };
  }

  function lineChart() {
    const serie = rep?.serie;
    if (!serie) return null;
    const source = (serie.tabela === "detail_rows" ? result.detail_rows : result.rows) || [];
    const categories = [...new Set(source.map(row => String(row[serie.categoria] ?? "")))];
    const category = lineCategory && categories.includes(lineCategory) ? lineCategory : categories[0];
    const territories = [...new Set(source.map(row => String(row[serie.territorio] ?? "")))];
    const labelToId = new Map([...labels.entries()].map(([id, label]) => [label, id]));
    const chosen = territories.filter(name => {
      const id = labelToId.get(name) || "";
      return (!selected.length || selectedSet.has(id)) && passesFilter(id);
    });
    const periods = [...new Set(source.map(row => String(row[serie.periodo])))].sort((a, b) => a.localeCompare(b, "pt-BR", { numeric: true }));
    if (periods.length < 2) return <p className="text-xs text-slate-600">Uma única competência não forma série temporal.</p>;
    if (!chosen.length) return <p className="text-xs text-slate-600">Nenhum território selecionado possui série temporal neste resultado.</p>;
    const pages = Math.ceil(chosen.length / MAX_LINES), page = Math.min(linePage, pages - 1);
    const series = chosen.slice(page * MAX_LINES, (page + 1) * MAX_LINES).map((name, index) => ({ key: "s" + index, label: name, color: CATEGORICAL[index] }));
    const points: LinePoint[] = periods.map(period => {
      const point: LinePoint = { periodo: period };
      for (const item of series) {
        const row = source.find(entry => String(entry[serie.periodo]) === period && String(entry[serie.territorio] ?? "") === item.label &&
          String(entry[serie.categoria] ?? "") === category);
        const value = row?.[serie.valor];
        point[item.key] = typeof value === "number" ? value : null;
      }
      return point;
    });
    const title = (serie.valor.startsWith("Densidade") ? "Densidade" : "Quantitativo") + " (" + serie.unidade + ") por competência" +
      (category ? " · " + category : "");
    return <div>
      <h4 className="mb-1 text-sm font-bold text-ink">{title}</h4>
      {pages > 1 && <nav aria-label="Territórios das séries" className="no-print mb-3 flex flex-wrap items-center gap-3 text-xs">
        <button type="button" className={button} disabled={page === 0} onClick={() => setLinePage(page - 1)}>Territórios anteriores</button>
        <span>Territórios {page * MAX_LINES + 1} a {Math.min((page + 1) * MAX_LINES, chosen.length)} de {chosen.length}, na ordem dos dados</span>
        <button type="button" className={button} disabled={page === pages - 1} onClick={() => setLinePage(page + 1)}>Próximos territórios</button>
      </nav>}
      {categories.length > 1 && <label className="no-print mb-2 flex items-center gap-2 text-xs">Categoria
        <select aria-label="Categoria da série" value={category} onChange={event => setLineCategory(event.target.value)} className="rounded-lg border border-line px-2 py-1">
          {categories.map(item => <option key={item} value={item}>{item}</option>)}</select></label>}
      <SeriesLines points={points} series={series} unit={serie.unidade} kind={serie.tipo} title={title}/>
    </div>;
  }

  function renderSelection() {
    if (!selected.length && !focusId) return <p className="no-print text-xs text-slate-500">Clique em um ponto do mapa, em uma barra ou em uma linha da
      tabela (ou use a busca) para consultar o território; a seleção é apenas visual e não altera o resultado.</p>;
    const focus = focusId && (selectedSet.has(focusId) || !selected.length) ? focusId : selected[selected.length - 1];
    return <div aria-label="Territórios selecionados" className="rounded-xl border border-line bg-white p-3 text-xs" role="region">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold text-ink">Seleção visual: {selected.map(labelOf).join("; ") || "—"}</p>
        <div className="no-print flex flex-wrap gap-2">
          <button type="button" className={button} disabled={!selected.length || !p.reusable || p.disabled}
            onClick={() => { p.onReuseSelection(selected); setNotice("Seleção levada à preparação da próxima análise (" + selected.length +
              " território(s)). Revise e execute pela preparação; nada foi calculado."); }}>Usar seleção na próxima análise</button>
          {(operation === "nearest" || operation === "criteria") && <button type="button" className={button + " text-amber-900"}
            disabled={!selected.length || !p.reusable || p.disabled} onClick={() => { p.onReferences(selected);
              setNotice("Seleção definida como lista de referências na preparação; execute novamente para calcular."); }}>Usar seleção como referências</button>}
          <button type="button" className={button} onClick={() => { setSelected([]); setFocusId(null); }}><X size={13}/> Limpar seleção</button>
        </div>
      </div>
      {!p.reusable && <p className="mt-1 text-slate-500">Reutilização indisponível: resultado invalidado ou de outra fonte, versão ou camada geográfica.</p>}
      {notice && <p role="status" className="mt-2 text-teal">{notice}</p>}
      {focus && renderDetail(focus)}
    </div>;
  }

  function renderDetail(id: string) {
    const row = rowsById.get(id);
    const index = points ? points.ids.indexOf(id) : -1;
    const lost = missing.find(item => item.id === id);
    const link = nearestRecords.get(id);
    const complemented = geometry?.complementados?.includes(id);
    return <dl className="mt-3 grid gap-x-4 gap-y-1.5 sm:grid-cols-[auto_minmax(0,1fr)]">
      <dt className="text-slate-500">Território</dt><dd className="font-semibold text-ink">{labelOf(id)}{codeOf(id) ? " · código " + codeOf(id) : ""}</dd>
      <dt className="text-slate-500">Competência</dt><dd>{displayPeriod(geometry?.competencia ?? (row?.["Período"] as string | undefined))}</dd>
      <dt className="text-slate-500">Coordenada</dt><dd>{index >= 0 ? <>lat. {fullPrecision(points!.lat[index])}, long. {fullPrecision(points!.lon[index])} ·
        {complemented ? " complementada pela camada oficial (coordenada fixa 2014–2024, premissa do usuário)" : " original da base"}</> :
        lost ? "sem coordenada válida: " + (lost.texto || lost.condicao) : geometry?.estado === "DISPONIVEL" ? "fora do conjunto representado" : "mapa indisponível"}</dd>
      {row ? (rep?.indicadores || []).map(item => <Pair key={item.coluna} label={item.rotulo + (item.unidade ? " (" + item.unidade + ")" : "")}
        value={row[item.coluna]} kind={item} />) : <><dt className="text-slate-500">Resultado</dt><dd>{references.has(id) ?
          "Referência fora do universo-alvo (sem valores de alvo)" : "Sem linha neste resultado"}</dd></>}
      {row && typeof row["Motivos"] === "string" && <><dt className="text-slate-500">Motivos</dt><dd>{row["Motivos"] as string}</dd></>}
      {Object.entries(criteriaMeta?.avaliacoes?.find(item => item.elemento === id)?.nos || {}).filter(([, node]) => node.causas?.length)
        .map(([key, node]) => <Fragment key={key}><dt className="text-slate-500">{key} não avaliável</dt>
          <dd>{node.causas!.map(causeText).join("; ")}</dd></Fragment>)}
      {references.has(id) && <><dt className="text-slate-500">Papel</dt><dd>Referência{rowsById.has(id) ? " e alvo" : ""}</dd></>}
      {link && <><dt className="text-slate-500">Referência mais próxima</dt>
        <dd>{link.refs.length ? link.refs.map(ref => labelOf(ref)).join("; ") + (link.refs.length > 1 ? " (empate: todas apresentadas)" : "") : "não avaliável"}
          {link.distance !== null && <> · <strong>{formatNumber(link.distance)} km</strong> <span className="text-slate-500">(geodésica direta do motor; valor integral {fullPrecision(link.distance)})</span></>}
          {link.alsoReference && " · o próprio alvo é referência (distância zero)"}
          <span className="block text-slate-600">Alcance: {link.reach}{!link.partial ? "" : link.accepted
            ? " — cobertura parcial aceita explicitamente; não equivale ao mínimo do conjunto completo"
            : " — cobertura parcial: o mínimo do conjunto completo não é avaliável para este alvo (referência sem coordenada válida); não equivale a ele"}</span></dd></>}
      <dd className="no-print sm:col-start-2">{index >= 0 && <button type="button" className="mr-2 text-teal underline" onClick={() => { setView("mapa"); setTimeout(() => mapRef.current?.center(id)); }}>
        Centralizar no mapa</button>}
        <button type="button" className="text-teal underline" onClick={() => { setFilter("MINHA_SELECAO"); if (!selectedSet.has(id)) toggle(id);
          setTimeout(() => document.getElementById("tabela-resultado")?.scrollIntoView({ behavior: "smooth", block: "start" })); }}>Ver na tabela</button></dd>
    </dl>;
  }

  const tables = operation === "criteria" && criteriaMeta ? null : operation === "distribution" && result.detail_rows ?
    <DistributionResults summary={result.rows} detail={result.detail_rows} onExport={p.onExport} highlight={selectedSet}
      idOf={linker} onToggle={toggle} onlyHighlighted={filter === "MINHA_SELECAO"} onTablePresentation={setTablePresentation}/> :
    result.rows.length > 0 ? renderTable() : null;

  function renderTable() {
    const columns = Object.keys(result.rows[0]);
    const visible = result.rows.map((row, index) => ({ row, id: rep?.tabela === "rows" ? rowIds[index] : linker(row) }))
      .filter(item => filter === "TODOS" || (item.id !== null && passesFilter(item.id)));
    return <div id="tabela-resultado" className="mt-7 overflow-hidden rounded-2xl border border-line">
      <div className="flex items-center justify-between border-b border-line px-5 py-4"><h4 className="text-sm font-bold text-ink">Tabela detalhada</h4>
        <span className="text-xs text-slate-400">{result.total_rows} registros{filter !== "TODOS" ? " · filtro visual aplicado" : ""}</span></div>
      <ResultTable rows={visible.map(item => item.row)} columns={columns.map(key => ({key}))} stacked={operation === "comparisons"} idOf={linker}
        selected={selectedSet} onToggle={toggle} onExport={p.onExport} onPresentation={setTablePresentation}/>
      {filter !== "TODOS" && !visible.length && <p className="px-5 py-3 text-xs text-slate-500">Nenhum território neste filtro visual.</p>}
    </div>;
  }

  if (operation === "criteria" && criteriaMeta) return <CriteriaResults key={result.result_id} rows={result.rows} meta={criteriaMeta}
    onExport={p.onExport} onSelection={p.onReuseSelection} onReferences={p.onReferences} reusable={p.reusable} disabled={p.disabled}
    filter={filter} onFilter={setFilter} mySelection={selectedSet} onToggle={toggle} explorer={visual} onTablePresentation={setTablePresentation}/>;
  return <>{sharedFilter && <div className="mt-6">{sharedFilter}</div>}{visual}{tables}</>;
}

type CriteriaCause = { origem: string; motivo?: string; detalhe?: string; candidatos_elegibilidade_desconhecida?: number;
  referencias_sem_coordenadas_avaliaveis?: number };
type CriteriaEvaluation = { elemento: string; estado: string; nos: Record<string, { estado: string; valor?: unknown; referencias?: string[] | null;
  alcance?: string | null; motivos?: string[]; causas?: CriteriaCause[] }> };

// Causas estruturadas do motor (critérios com distância), apenas reescritas em texto.
function causeText(cause: CriteriaCause): string {
  if (cause.candidatos_elegibilidade_desconhecida !== undefined) return "elegibilidade desconhecida em " +
    cause.candidatos_elegibilidade_desconhecida + " candidato(s) a referência (sem aceitar só as confirmadas)";
  if (cause.referencias_sem_coordenadas_avaliaveis !== undefined) return cause.referencias_sem_coordenadas_avaliaveis +
    " referência(s) sem coordenada avaliável e cobertura parcial não aceita";
  if (cause.detalhe === "CONJUNTO_REFERENCIAS_VAZIO") return "conjunto de referências vazio";
  return cause.origem + (cause.motivo ? ": " + cause.motivo : cause.detalhe ? ": " + cause.detalhe : "");
}
type NearestScope = { avaliabilidade: string; referencias: string[]; distancia_km: number | null; alcance: string };
type NearestRecord = { unidade: string; coordenada: string; alvo_e_referencia: boolean; minimo_completo: NearestScope; minimo_avaliaveis: NearestScope };
type NearestLink = { refs: string[]; distance: number | null; reach: string; partial: boolean; accepted: boolean; alsoReference: boolean;
  origin?: string };

function Pair({ label, value, kind }: { label: string; value: unknown; kind: Indicator }) {
  return <><dt className="text-slate-500">{label}</dt>
    <dd title={typeof value === "number" ? "Valor integral: " + fullPrecision(value) : undefined}>
      {kind.tipo === "ESTADO" ? (STATE_LABELS[String(value)] || formatValue(value, kind.tipo)) : formatValue(value, kind.tipo)}</dd></>;
}

function Unavailable({ reason, pending }: { reason: string; pending?: string }) {
  const needsLocation = ["REFERENCIAL_GEODESICO", "SEPARADOR_DECIMAL", "PAPEIS_COORDENADAS", "COORDENADAS_NAO_ASSOCIADAS"].includes(pending || "");
  return <div role="status" className="rounded-xl border border-line bg-slate-50 p-4 text-xs leading-5 text-slate-700">
    <p className="font-semibold text-ink">Mapa indisponível para este resultado</p>
    <p className="mt-1">{needsLocation ? "A fonte importada não tem informações de localização completas e confirmadas. A configuração de origem pode ser revisada nas opções avançadas da preparação." : reason}</p>
    {pending === "COMPETENCIA_UNICA" && <p className="mt-1">Escolha um período para visualizar os pontos no mapa. Para acompanhar vários períodos, use o gráfico de linhas.</p>}
    <p className="mt-1">Você pode continuar explorando a tabela e os gráficos.</p>
  </div>;
}

function Legend({ indicator, domain, counts, referencesShown, linksShown }: { indicator: Indicator; domain: [number, number] | null;
  counts: Record<string, number> | null; referencesShown: boolean; linksShown: boolean }) {
  const symbol = (shape: ReactNode, text: string) => <li className="flex items-center gap-2"><svg aria-hidden width="18" height="14">{shape}</svg>{text}</li>;
  const [low, high] = domain ? formatPair(domain[0], domain[1], indicator.tipo) : ["", ""];
  const palette = indicator.tipo === "CLASSE" && indicator.origem === "CAP-DIS-02" ? ORDINAL : CATEGORICAL;
  return <aside aria-label="Legenda do mapa" className="rounded-xl border border-line bg-white p-3 text-xs leading-5 text-slate-700">
    <p className="font-semibold text-ink">{indicator.rotulo}{indicator.unidade ? " (" + indicator.unidade + ")" : ""}</p>
    {domain ? <div className="mt-2">
      <div aria-hidden className="h-2.5 w-full rounded" style={{ background: "linear-gradient(90deg," + Array.from({ length: 10 }, (_, i) => sequentialColor(i / 9)).join(",") + ")" }}/>
      <div className="mt-1 flex justify-between"><span>{low}</span><span>{high}</span></div>
      <p className="text-slate-500">Escala contínua linear entre o menor e o maior valor do resultado; a cor não é classe nem limiar.</p>
    </div> : <ul className="mt-2 space-y-1">
      {(indicator.classes || []).filter(item => item !== "NAO_AVALIAVEL" && item !== "Não avaliável").map((item, index) =>
        symbol(<circle cx="9" cy="7" r="5" fill={STATE_COLORS[item] || palette[index % palette.length]}/>,
          (STATE_LABELS[item] || item) + (counts && counts[item] !== undefined ? " (" + formatNumber(counts[item], "CONTAGEM") + ")" : "")))}
      <li className="text-slate-500">Grupos calculados na análise.</li>
    </ul>}
    <ul className="mt-2 space-y-1 border-t border-line pt-2">
      {symbol(<circle cx="9" cy="7" r="4.5" fill={INK.surface} stroke={NOT_EVALUABLE} strokeWidth="1.5"/>, "Não avaliável (sem valor; nunca zero)" +
        (counts?.NAO_AVALIAVEL !== undefined ? " (" + formatNumber(counts.NAO_AVALIAVEL, "CONTAGEM") + ")" : ""))}
      {referencesShown && symbol(<path d="M9 1 L15 7 L9 13 L3 7 Z" fill={INK.surface} stroke={INK.primary} strokeWidth="1.3"/>, "Referência")}
      {symbol(<circle cx="9" cy="7" r="5.5" fill="none" stroke={INK.primary} strokeWidth="2"/>, "Selecionado (estado visual)")}
      {symbol(<circle cx="9" cy="7" r="3" fill={INK.faint}/>, "Fora do filtro visual")}
      {linksShown && symbol(<line x1="1" y1="7" x2="17" y2="7" stroke={INK.secondary} strokeWidth="1.5" strokeDasharray="4 3"/>, "Ligação ilustrativa (não é trajeto)")}
    </ul>
  </aside>;
}

function TerritorySearch({ ids, labelOf, onPick }: { ids: string[]; labelOf: (id: string) => string; onPick: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const normalized = (text: string) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLocaleLowerCase("pt-BR");
  const matches = useMemo(() => {
    const q = normalized(query.trim());
    if (q.length < 2) return [];
    return ids.filter(id => normalized(labelOf(id)).includes(q) || codeOf(id).startsWith(q)).slice(0, 8);
  }, [query, ids]);
  const choose = (id: string) => { onPick(id); setQuery(""); };
  return <div className="relative flex min-w-[220px] flex-1 flex-col gap-1 text-xs font-semibold text-slate-700 sm:max-w-xs">
    <label htmlFor="busca-territorio">Buscar território (nome ou código)</label>
    <span className="relative"><Search size={14} className="absolute left-2.5 top-3 text-slate-400"/>
      <input id="busca-territorio" role="combobox" aria-expanded={matches.length > 0} aria-controls="busca-territorio-lista" aria-autocomplete="list"
        value={query} onChange={event => { setQuery(event.target.value); setActive(0); }}
        onKeyDown={event => {
          if (event.key === "ArrowDown") { setActive(index => Math.min(index + 1, matches.length - 1)); event.preventDefault(); }
          if (event.key === "ArrowUp") { setActive(index => Math.max(index - 1, 0)); event.preventDefault(); }
          if (event.key === "Enter" && matches[active]) { choose(matches[active]); event.preventDefault(); }
          if (event.key === "Escape") setQuery("");
        }}
        className="w-full rounded-lg border border-line bg-white py-2 pl-8 pr-2 text-sm font-normal"/></span>
    {matches.length > 0 && <ul id="busca-territorio-lista" role="listbox" className="absolute top-full z-20 mt-1 w-full overflow-hidden rounded-lg border border-line bg-white font-normal shadow-card">
      {matches.map((id, index) => <li key={id} role="option" aria-selected={index === active} onMouseDown={event => { event.preventDefault(); choose(id); }}
        className={"cursor-pointer px-3 py-2 " + (index === active ? "bg-blue-50" : "")}>{labelOf(id)}</li>)}
    </ul>}
  </div>;
}
