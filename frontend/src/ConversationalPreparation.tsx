import { useEffect, useState, type ReactNode } from "react";
import { ChevronDown, Play, SlidersHorizontal } from "lucide-react";
import BrandAvatar from "./BrandAvatar";
import PeriodSelection, {PeriodChoices} from "./PeriodSelection";
import {chronological, describePeriods, readablePeriod, rotationPeriods} from "./periods";
import {ownIndicator} from "./analysisCatalog";
import {fieldOptions, periodValue, SINGLE_PERIOD, type FieldChoice} from "./fieldChoices";
import type {ObjectState} from "./ContextConfig";

export type AnalysisKind = "density" | "counts" | "distribution" | "comparisons" |
  "temporal" | "aggregate" | "spatial" | "ranking" | "rotation" | "report" | "nearest" | "criteria";
export type FieldRole = "territory" | "territory_id" | "period" | "category" |
  "count" | "population" | "latitude" | "longitude" | "identity";
type Mapping = Partial<Record<FieldRole, string>>;
type SourceScope = "national" | "municipal";
type Capability = { status: "available" | "needs_confirmation" | "unavailable"; reasons: string[] };
type Props = {
  operation: AnalysisKind;
  sourceBrazil: boolean;
  curated: boolean;
  quantiles: number;
  onQuantiles: (value: number) => void;
  selectedPeriods: string[];
  multiplePeriods: boolean;
  periodEditor: number;
  onSelectedPeriods: (periods: string[]) => void;
  /** Fonte da base Brasil sem o perfil oficial (fluxo das bases importadas): escolha entre o total nacional e os municípios. */
  scope: SourceScope;
  onScope: (scope: SourceScope) => void;
  /** Base oficial: escolha pendente na abrangência territorial (mistura de níveis ou mínimo de territórios). */
  territoryPending?: boolean;
  /** Base oficial: a caixa "Abrangência territorial" reúne o Brasil (total nacional), os estados e os municípios. */
  territoriesOpen: boolean;
  onTerritoriesOpen: (open: boolean) => void;
  territorySelection?: ReactNode;
  territorySummary: string;
  /** Rotatividade: competências inicial e final da coorte (vazias = primeira e última disponíveis). */
  rotationPeriods: {initial: string; final: string};
  onRotationPeriod: (which: "initial" | "final", period: string) => void;
  /** Critérios combinados: atributos numéricos usados nas condições, na ordenação e nas faixas. */
  criteriaAttributes: string[];
  columns: string[];
  mapping: Mapping;
  onField: (role: FieldRole, column: string) => void;
  countUnit: string;
  onCountUnit: (unit: string) => void;
  customCountUnit: string;
  onCustomCountUnit: (value: string) => void;
  indicator: string;
  onIndicator: (value: "quantity" | "density" | "") => void;
  periodFilter: string;
  /** Comparação (D6): competência dos valores (a única escolhida ou uma da janela) e a escolha na caixa própria. */
  valuesPeriod?: string;
  onValuesPeriod?: (period: string) => void;
  periods: string[];
  onPeriod: (period: string) => void;
  categoryFilter: string;
  requestedCategory: string;
  categories: string[];
  onCategory: (category: string) => void;
  /** Colunas sugeridas pelo backend por papel: aparecem no topo dos seletores, nunca selecionadas em silêncio. */
  suggestions?: Partial<Record<string, string[]>>;
  /** Opção "A base tem um único período" do seletor de período. */
  singlePeriod: boolean;
  onSinglePeriod: (value: boolean) => void;
  /** Objeto de análise do pré-exame (reconhecido, informado ou ausente) e o texto informado pelo usuário. */
  objectState?: ObjectState;
  objectDraft: string;
  onObjectDraft: (value: string) => void;
  suggestedObject: string;
  reference: string;
  territories: string[];
  onReference: (territory: string) => void;
  crs: string;
  onCrs: (crs: string) => void;
  /** Base oficial: o referencial é premissa interna (SIRGAS 2000) e não é pedido ao usuário. */
  governedCrs: boolean;
  preparing: boolean;
  capability?: Capability;
  onExecute: () => void;
  executing: boolean;
  advanced: ReactNode;
  extra?: ReactNode;
  referenceMode?: string;
  criteriaNeeds?: { count: boolean; population: boolean; spatial: boolean };
};
type Choice = { label: string; value: string; disabled?: boolean };
export const GOVERNED_CRS = "SIRGAS 2000 (premissa da base oficial)";
function InlineChoice({ label, value, options, onChange, testId, placeholder = "Escolher campo" }: {
  label: string; value: string; options: Choice[] | FieldChoice[]; onChange: (value: string) => void; testId?: string;
  placeholder?: string;
}) {
  const current = options.find(o => o.value === value)?.label || (value ? "escolher" : placeholder);
  const width = Math.max(8, Math.min(28, current.length + 3)) + "ch";
  return <span className={"relative mx-0.5 inline-flex max-w-full align-baseline rounded-md text-teal hover:bg-blue-100 focus-within:outline focus-within:outline-2 focus-within:outline-offset-1 focus-within:outline-teal " +
    (value || placeholder !== "Escolher campo" ? "bg-blue-50/60" : "bg-amber-50")}>
    <select aria-label={label} title={"Alterar " + label} value={value} data-testid={testId}
      onChange={e => onChange(e.target.value)}
      style={{width, maxWidth: "min(80vw, 28ch)"}}
      className="min-w-0 cursor-pointer appearance-none overflow-hidden text-ellipsis border-0 bg-transparent py-0.5 pl-1.5 pr-5 text-sm font-semibold underline decoration-teal/40 underline-offset-2 focus:outline-none">
      <option value="">{placeholder}</option>
      {options.filter(o => o.value).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
    <ChevronDown size={12} aria-hidden="true" className="pointer-events-none absolute right-1 top-1/2 -translate-y-1/2"/>
  </span>;
}
// Caixas seletoras das configurações (base oficial): título curto, valor atual e o controle da escolha.
const BOX = "flex h-full w-full min-w-0 flex-col rounded-lg border px-3 py-2 text-left transition";
const boxTone = (open: boolean, pending: boolean) => open ? "border-teal bg-cyan-50"
  : pending ? "border-amber-300 bg-amber-50" : "border-line bg-white hover:border-teal";
const BOX_LABEL = "text-[11px] font-semibold uppercase tracking-wide text-slate-500";
const PANEL = "space-y-3 rounded-xl border border-teal/40 bg-white p-3 sm:p-4";
const DONE = "rounded-lg bg-teal px-3 py-2 text-xs font-semibold text-white";
function ConfigSelect({label, ariaLabel = label, value, options, onChange, placeholder = "Escolher", pending = false, testId}: {
  label: string; ariaLabel?: string; value: string; options: Choice[]; onChange: (value: string) => void;
  placeholder?: string; pending?: boolean; testId?: string;
}) {
  // O valor aparece por inteiro, com quebra de linha; o seletor nativo, transparente, cobre a caixa e recebe o clique e o teclado.
  const shown = options.find(o => o.value === value)?.label || placeholder;
  return <label data-testid={testId} className={BOX + " relative cursor-pointer focus-within:outline focus-within:outline-[3px] focus-within:outline-offset-2 " +
    "focus-within:outline-[#3bb5be] " + boxTone(false, pending)}>
    <span className={BOX_LABEL}>{label}</span>
    <span aria-hidden="true" className="mt-0.5 flex w-full items-start justify-between gap-2">
      <span className="min-w-0 text-sm font-semibold leading-5 text-ink">{shown}</span>
      <ChevronDown size={14} className="mt-0.5 shrink-0 text-teal"/>
    </span>
    <select aria-label={ariaLabel} value={value} onChange={e => onChange(e.target.value)}
      className="absolute inset-0 h-full w-full cursor-pointer appearance-none opacity-0">
      {!value && <option value="" disabled>{placeholder}</option>}
      {options.map(o => <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>)}
    </select>
  </label>;
}
/** Caixa que abre uma lista abaixo das configurações (período e abrangência territorial). */
function ConfigToggle({id, testId, toggleTestId, label, ariaLabel, value, valueTestId, open, pending = false, controls, onToggle}: {
  id?: string; testId?: string; toggleTestId?: string; label: string; ariaLabel: string; value: string; valueTestId: string;
  open: boolean; pending?: boolean; controls: string; onToggle: () => void;
}) {
  return <div id={id} data-testid={testId} className="section-anchor min-w-0">
    <button type="button" data-testid={toggleTestId} aria-label={ariaLabel} aria-expanded={open} aria-controls={controls}
      aria-describedby={controls + "-valor"} onClick={onToggle} className={BOX + " " + boxTone(open, pending)}>
      <span className={BOX_LABEL}>{label}</span>
      <span className="mt-0.5 flex w-full items-start justify-between gap-2">
        <span id={controls + "-valor"} data-testid={valueTestId} className="min-w-0 text-sm font-semibold leading-5 text-ink">{value}</span>
        <ChevronDown size={14} aria-hidden="true" className={"mt-0.5 shrink-0 text-teal transition " + (open ? "rotate-180" : "")}/>
      </span>
    </button>
  </div>;
}
const named = (values: string[]): Choice[] => values.map(value => ({value, label:value}));
const sourceOptions: Choice[] = [{label:"municípios",value:"municipal"},{label:"Brasil",value:"national"}];
const indicatorOptions: Choice[] = [{label:"quantidade",value:"quantity"},{label:"densidade por 1.000",value:"density"}];
const indicatorChoices: Choice[] = [{label:"Quantidade",value:"quantity"},{label:"Densidade por 1.000 habitantes",value:"density"}];
const groupChoices: Choice[] = [
  {label:"Quartis (4 grupos)",value:"4"}, {label:"Quintis (5 grupos)",value:"5"},
  {label:"Decis (10 grupos)",value:"10"}
];
const crsChoices: Choice[] = [{label:"SIRGAS2000",value:"SIRGAS2000"}];
const countUnits: Choice[] = [{label:"pessoas",value:"pessoas"},{label:"vínculos",value:"vinculos"},
  {label:"postos de trabalho",value:"postos"},{label:"outra unidade",value:"outro"}];

export default function ConversationalPreparation(p: Props) {
  // Lista de competências da caixa "Período" (base oficial); a da abrangência é controlada pelo App.
  const [periodOpen, setPeriodOpen] = useState(false);
  useEffect(() => { setPeriodOpen(false); }, [p.operation]);
  useEffect(() => { setPeriodOpen(p.periodEditor > 0); }, [p.periodEditor]);
  // Critérios combinados: os papéis seguem as condições, a ordenação e as referências definidas.
  const needs = p.operation === "criteria" ? p.criteriaNeeds || {count: false, population: false, spatial: false} : null;
  const criterion = (p.operation === "nearest" && p.referenceMode === "criterion") || !!needs?.count;
  const spatial = p.operation === "spatial" || p.operation === "nearest" || !!needs?.spatial;
  const requiresCount = p.operation !== "spatial" && p.operation !== "rotation" && (!["nearest", "criteria"].includes(p.operation) || criterion);
  const requiresPopulation = ["density", "ranking", "aggregate"].includes(p.operation) || (needs ? needs.population : criterion) ||
    p.operation === "comparisons" && p.indicator !== "quantity" ||
    (["distribution","temporal","report"].includes(p.operation) && p.indicator === "density");
  const requiresIndicator = ["comparisons", "distribution", "temporal", "report"].includes(p.operation);
  // Seletores de campo (D1): sugestões no topo, com "(sugerida)"; vazio até o usuário escolher. Escolher estabelece o papel.
  const field = (label: string, role: FieldRole, optional = false) => <InlineChoice label={label} testId={"field-choice-" + role}
    value={role === "period" ? periodValue(p.mapping.period, p.singlePeriod) : p.mapping[role] || ""}
    placeholder={optional ? "Sem código" : "Escolher campo"}
    options={fieldOptions(p.columns, p.suggestions, role, {singlePeriod: role === "period", current: p.mapping[role] || ""})}
    onChange={v => {
      if (role === "period" && v === SINGLE_PERIOD) { p.onField(role, ""); p.onSinglePeriod(true); return; }
      if (role === "period") p.onSinglePeriod(false);
      p.onField(role, v);
    }}/>;
  const status = p.capability?.status;
  const categoryChoiceRequired = !!p.requestedCategory && !!p.mapping.category && !p.categoryFilter;
  // Comparação (D6): uma competência ou uma janela de competências, com os valores numa delas.
  const allowMultiple = ["counts", "report", "temporal", "comparisons"].includes(p.operation);
  const comparing = p.operation === "comparisons";
  const windowPeriods = chronological(p.multiplePeriods ? p.selectedPeriods : p.periodFilter ? [p.periodFilter] : []);
  const valuesChoices: Choice[] = windowPeriods.map(value => ({value, label: readablePeriod(value)}));
  const emptyMultiple = allowMultiple && p.multiplePeriods && !p.selectedPeriods.length && p.periods.length > 1;
  const periodChoiceRequired = emptyMultiple || p.operation === "counts" && p.periods.length > 1 && !p.periodFilter && p.selectedPeriods.length === 0;
  const ready = status === "available" && !p.preparing && !p.executing && !categoryChoiceRequired && !periodChoiceRequired;
  // Objeto de análise: o texto informado é o objeto (sem confirmação); a sugestão do cabeçalho nunca é aplicada sozinha.
  const usesObject = p.operation !== "spatial" && (!["nearest", "criteria"].includes(p.operation) || criterion);
  if (p.sourceBrazil && p.curated) {
    const isTemporal = p.operation === "temporal";
    // Na análise espacial, uma competência: as coordenadas de um mesmo município podem mudar entre competências.
    const usesPeriods = p.operation !== "rotation";
    const multiple = allowMultiple && p.multiplePeriods;
    const periodReady = !usesPeriods || p.periods.length <= 1 || (multiple ? p.selectedPeriods.length > 0 : !!p.periodFilter);
    const analysisReady = ready && periodReady;
    // Períodos em ordem cronológica e resumidos por intervalo; sem escolha, a caixa pede a escolha.
    const periodValue = periodReady ? describePeriods(multiple ? p.selectedPeriods : p.periodFilter ? [p.periodFilter] : p.periods, p.periods)
      : multiple ? "Escolher períodos" : "Escolher período";
    // As quatro caixas aparecem em todas as análises. Sem escolha entre quantidade e densidade, a caixa Indicador mostra
    // o indicador próprio da análise, numa opção só. A densidade vale também para o Brasil (população de junho, regra
    // governada do backend).
    const own = ownIndicator(p.operation, p.criteriaAttributes);
    // Motivos do pré-exame da análise espacial (coordenadas, competência, referência): os mesmos textos do backend.
    const spatialReasons = p.operation === "spatial" && periodReady && status && status !== "available" && !p.preparing
      ? (p.capability?.reasons || []).slice(0, 2) : [];
    return <section aria-label="Preparação na conversa" className="mt-2 space-y-3 text-sm leading-7 text-slate-700">
      <h3 className="text-base font-bold text-ink">Configurações</h3>
      <div data-testid="analysis-summary" className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <ConfigSelect label="Categoria" value={p.categoryFilter} options={named(p.categories)} onChange={p.onCategory}
          placeholder="Escolher categoria" pending={!p.categoryFilter}/>
        {usesPeriods ? <ConfigToggle label="Período" ariaLabel="Escolher períodos da análise" value={periodValue} valueTestId="period-summary"
            open={periodOpen} pending={!periodReady} controls="configuracao-periodo" onToggle={() => setPeriodOpen(!periodOpen)}/>
          : <ConfigToggle label="Período" ariaLabel="Escolher os períodos da coorte" valueTestId="period-summary"
            value={rotationPeriods(p.periods, p.rotationPeriods.initial, p.rotationPeriods.final)}
            open={periodOpen} controls="configuracao-periodo" onToggle={() => setPeriodOpen(!periodOpen)}/>}
        <ConfigToggle id="territorios" testId="territory-card" toggleTestId="territory-toggle" label="Abrangência territorial"
          ariaLabel="Escolher a abrangência territorial" value={p.territorySummary} valueTestId="scope-summary"
          open={p.territoriesOpen} pending={!!p.territoryPending} controls="territorios-painel"
          onToggle={() => p.onTerritoriesOpen(!p.territoriesOpen)}/>
        {requiresIndicator ? <ConfigSelect label="Indicador" value={p.indicator} options={indicatorChoices}
            onChange={value => p.onIndicator(value as "quantity" | "density")} placeholder="Escolher indicador" pending={!p.indicator}/>
          : <ConfigSelect label="Indicador" value={own} options={[{label: own, value: own}]} onChange={() => {}}/>}
        {comparing && <ConfigSelect label="Competência dos valores" ariaLabel="Competência dos valores da comparação"
          testId="comparison-values-period" value={p.valuesPeriod || ""} options={valuesChoices}
          onChange={value => p.onValuesPeriod?.(value)} placeholder="Escolha o período" pending={!p.valuesPeriod}/>}
        {p.operation === "distribution" && <ConfigSelect label="Agrupamento" ariaLabel="Agrupamento da distribuição" value={String(p.quantiles)}
          options={groupChoices} onChange={value => p.onQuantiles(Number(value))}/>}
        {p.operation === "spatial" && <ConfigSelect label="Território de referência" value={p.reference} options={named(p.territories)}
          onChange={p.onReference} placeholder="Escolher território" pending={!p.reference}/>}
        {spatial && !p.governedCrs && <ConfigSelect label="Referencial geodésico" value={p.crs} options={crsChoices}
          onChange={p.onCrs} placeholder="Escolher referencial" pending={!p.crs}/>}
      </div>
      {spatial && p.governedCrs && <p className="text-xs text-slate-600">Referencial das distâncias: <strong data-testid="crs-summary"
        className="font-semibold text-ink">{GOVERNED_CRS}</strong></p>}
      {usesPeriods && periodOpen && <div id="configuracao-periodo" role="group" aria-label="Período da análise" className={PANEL}>
        <p className="font-medium text-ink">{isTemporal ? "Quais períodos você deseja comparar?" : comparing
          ? "Qual período (ou janela de períodos) você deseja usar na comparação?" : "Qual período você deseja analisar?"}</p>
        <PeriodChoices key={p.operation} periods={p.periods} value={p.periodFilter} selected={p.selectedPeriods}
          multiple={multiple} allowMultiple={allowMultiple} modeToggle disabled={p.executing} trendNote={isTemporal || comparing}
          onSingle={p.onPeriod} onChosen={() => setPeriodOpen(false)} onMultiple={p.onSelectedPeriods}/>
        {comparing && <p data-testid="comparison-window-note" className="text-xs leading-5 text-slate-600">
          Os valores lado a lado e as relações (maior, menor, diferença) usam só a competência da caixa “Competência dos valores”.
          Com dois ou mais períodos, cada território ganha também a mudança entre o primeiro e o último e a classe de tendência
          na janela; sem variação percentual nem razão automáticas.</p>}
        {p.operation === "distribution" && <p className="text-xs leading-5 text-slate-600">
          Para comparar territórios nesta distribuição, escolha um período. Para comparar períodos, utilize Evolução temporal.</p>}
        {p.operation === "spatial" && <p data-testid="spatial-period-note" className="text-xs leading-5 text-slate-600">
          As distâncias usam as coordenadas da competência escolhida; em algumas competências, a fonte traz coordenadas diferentes
          para o mesmo município.</p>}
        {p.operation === "aggregate" && <p className="text-xs leading-5 text-slate-600">
          Para agregar territórios, selecione uma competência por vez.
          A soma entre diferentes meses não representa pessoas únicas.</p>}
        {periodReady && <button type="button" data-testid="period-done" aria-label="Concluir a escolha do período"
          onClick={() => setPeriodOpen(false)} className={DONE}>Concluir</button>}
      </div>}
      {p.operation === "rotation" && periodOpen && <div id="configuracao-periodo" role="group" aria-label="Períodos da coorte" className={PANEL}>
        <p className="font-medium text-ink">Quais períodos delimitam a coorte?</p>
        <div className="flex flex-wrap gap-3 text-xs">
          {(["initial", "final"] as const).map(which => <label key={which} className="flex items-center gap-2">
            {which === "initial" ? "Período inicial" : "Período final"}
            <select aria-label={which === "initial" ? "Período inicial" : "Período final"} value={p.rotationPeriods[which]}
              onChange={e => p.onRotationPeriod(which, e.target.value)} className="min-w-0 rounded-md border border-line bg-white px-2 py-1">
              <option value="">{which === "initial" ? "Primeira competência disponível" : "Última competência disponível"}</option>
              {chronological(p.periods).map(value => <option key={value} value={value}>{readablePeriod(value)}</option>)}
            </select>
          </label>)}
        </div>
        <p className="text-xs leading-5 text-slate-600">A coorte reúne as pessoas do período inicial; a permanência é conferida no período final.</p>
        <button type="button" data-testid="period-done" aria-label="Concluir a escolha do período"
          onClick={() => setPeriodOpen(false)} className={DONE}>Concluir</button>
      </div>}
      {p.territoriesOpen && <div id="territorios-painel" role="group" aria-label="Abrangência territorial" className={PANEL}>
        {p.territorySelection}
        <button type="button" data-testid="scope-done" aria-label="Concluir a abrangência territorial"
          onClick={() => p.onTerritoriesOpen(false)} className={DONE}>Concluir</button>
      </div>}
      {p.extra}
      {!periodReady && <p className="text-xs text-slate-600">Escolha o período para continuar.</p>}
      {p.territoryPending && <p data-testid="territory-pending" className="text-xs text-amber-900">Ajuste a abrangência territorial para continuar.</p>}
      {spatialReasons.length > 0 && <p role="status" data-testid="spatial-reasons" className="text-xs leading-5 text-amber-900">
        {spatialReasons.join(" ")}</p>}
      {p.preparing && <p role="status" className="text-xs text-slate-500">Preparando a análise...</p>}
      {status !== "available" && !p.preparing &&
        <p role="status" className="text-xs text-slate-600">Ainda faltam condições específicas para esta análise.
          Você pode ajustá-las acima ou consultar as opções adicionais.</p>}
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={!analysisReady} onClick={p.onExecute}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">
          <Play size={14}/>{p.executing ? "Calculando..." : "Calcular e mostrar resultado"}
        </button>
      </div>
      {p.advanced && <details className="text-xs text-teal">
        <summary className="cursor-pointer">Ver outras condições da análise</summary>
        <div className="mt-2">{p.advanced}</div>
      </details>}
    </section>;
  }
  return <section aria-label="Preparação na conversa" className="mt-4 space-y-3 text-sm leading-7 text-slate-700">
    <div className="flex items-start gap-2">
      <BrandAvatar size={28} className="mt-1 shrink-0"/>
      <div className="min-w-0 flex-1 space-y-3">
        <p>Vamos organizar esta análise com os dados disponíveis. Preenchi os campos reconhecidos com segurança; escolha os demais nos termos destacados.</p>
        <p className="leading-8">
          {p.sourceBrazil
            ? <>Para esta consulta, vou considerar os dados {p.scope === "national" ? "do " : "dos "}
                <InlineChoice label="Abrangência territorial" value={p.scope}
                  options={sourceOptions} onChange={v=>p.onScope(v as SourceScope)}/>. </>
            : <>Nos dados que você importou, </>}
          {p.sourceBrazil ? <>A referência territorial é </> : <>a referência territorial é </>}
          {field("Território", "territory")}
          {p.mapping.territory || p.mapping.territory_id || p.suggestions?.territory_id?.length
            ? <>, e cada unidade pode ser identificada pelo código {field("Identificador territorial", "territory_id", true)} (opcional)</> : null}.
          {p.operation !== "spatial" && <> As profissões estão organizadas em {field("Categoria profissional", "category")},
            enquanto os períodos aparecem em {field("Período", "period")}.</>}
          {requiresCount && <> Os quantitativos são registrados em {field("Quantitativo", "count")}.</>}
          {requiresPopulation && <> Para calcular a densidade, usarei a população informada em {field("População", "population")}.</>}
          {p.operation === "rotation" && <> Para acompanhar pessoas entre períodos, considerarei {field("Identificador individual", "identity")} como identificador.</>}
          {spatial && <> As coordenadas constam de {field("Latitude", "latitude")} e {field("Longitude", "longitude")}.</>}
        </p>
        <p className="leading-8">
          {requiresIndicator && <>O indicador escolhido é <InlineChoice label="Indicador" value={p.indicator}
            options={indicatorOptions} onChange={v => p.onIndicator(v as "quantity" | "density" | "")}/>. </>}
          {requiresCount && <>Antes do cálculo, preciso saber se esses quantitativos representam <InlineChoice label="Unidade de contagem"
            value={p.countUnit} options={countUnits} onChange={p.onCountUnit}/>. </>}
          {p.operation !== "spatial" && p.operation !== "temporal" && <>
            {p.periods.length > 1 && !(allowMultiple && p.multiplePeriods) && <>Podemos considerar o período <InlineChoice label="Filtrar por período"
              value={p.periodFilter} options={named(p.periods)} onChange={p.onPeriod}/>. </>}
            {p.requestedCategory && p.mapping.category &&
              <>Você mencionou “{p.requestedCategory}”; selecione como essa profissão aparece nos dados: <InlineChoice
                label="Filtrar por categoria" value={p.categoryFilter} options={named(p.categories)} onChange={p.onCategory}/>. </>}
            {!p.requestedCategory && p.categories.length > 1 && <>Se desejar, escolha uma categoria específica em <InlineChoice
                label="Filtrar por categoria" value={p.categoryFilter} options={named(p.categories)} onChange={p.onCategory}/>. </>}
          </>}
          {p.operation === "spatial" && <>Para as distâncias, o referencial será <InlineChoice label="Referencial geodésico"
            value={p.crs} options={[{label:"SIRGAS2000",value:"SIRGAS2000"}]} onChange={p.onCrs}/>,
            tendo como ponto de referência <InlineChoice label="Território de referência" value={p.reference}
              options={named(p.territories)} onChange={p.onReference}/>. </>}
          {(p.operation === "nearest" || needs?.spatial) && <>Para as distâncias, o referencial das coordenadas é <InlineChoice label="Referencial geodésico"
            value={p.crs} options={[{label:"SIRGAS2000",value:"SIRGAS2000"}]} onChange={p.onCrs}/>; nenhum referencial é presumido. </>}
        </p>
        {allowMultiple && p.periods.length > 1 && <div>
          {p.multiplePeriods ? <PeriodSelection periods={p.periods} value={p.periodFilter} selected={p.selectedPeriods}
            multiple={true} allowMultiple={true} onSingle={p.onPeriod} onMultiple={p.onSelectedPeriods}/> :
            <button type="button" onClick={()=>p.onSelectedPeriods(p.periodFilter ? [p.periodFilter] : p.periods)}
              className="text-xs text-teal underline">Selecionar vários períodos</button>}
        </div>}
        {comparing && p.multiplePeriods && windowPeriods.length > 1 && <p className="leading-8">Os valores comparados são os da
          competência <InlineChoice label="Competência dos valores da comparação" testId="comparison-values-period" value={p.valuesPeriod || ""}
            options={valuesChoices} onChange={value => p.onValuesPeriod?.(value)} placeholder="escolher"/>; nas demais
          competências da janela, cada território ganha a mudança e a classe de tendência.</p>}
        {categoryChoiceRequired && <p className="text-xs text-slate-600">A categoria escolhida define a correspondência desejada; não vou presumir que nomes diferentes tenham o mesmo significado.</p>}
        {usesObject && p.objectState?.status === "ausente" && <p className="flex flex-wrap items-center gap-2 text-sm">
          O objeto da análise é <input aria-label="Objeto de análise" data-testid="object-draft" value={p.objectDraft}
            onChange={e => p.onObjectDraft(e.target.value)} placeholder="profissão ou conjunto de trabalhadores"
            className="max-w-[260px] rounded-md border border-amber-300 bg-amber-50 px-2 py-1"/>
          {!p.objectDraft && p.suggestedObject && <button type="button" data-testid="object-suggestion"
            onClick={() => p.onObjectDraft(p.suggestedObject)} className="rounded-md border border-blue-200 bg-white px-2 py-1 text-xs font-semibold text-teal">
            Usar sugestão: {p.suggestedObject}</button>}
        </p>}
        {usesObject && p.objectState?.status === "informado" && p.objectDraft && <p className="text-xs text-slate-600">
          Objeto informado por você: <strong>{p.objectDraft}</strong>. <button type="button" className="underline"
            onClick={() => p.onObjectDraft("")}>Alterar</button></p>}
        {periodChoiceRequired && <p className="text-xs text-slate-600">Escolha um período para obter o quantitativo daquele momento, sem somar diferentes períodos.</p>}
        {p.countUnit === "outro" && <label className="flex items-center gap-2 text-sm">
          Nome da unidade: <input value={p.customCountUnit} onChange={e=>p.onCustomCountUnit(e.target.value)}
          className="max-w-[220px] rounded-md border border-blue-200 px-2 py-1" placeholder="Descreva a unidade"/>
        </label>}
        {requiresPopulation && p.mapping.population && <p className="text-xs leading-5 text-slate-600">
          A população usada é a da mesma linha, no mesmo território e período de cada quantidade; essa premissa aparece em “Método e limitações”.</p>}
        {p.extra}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <button type="button" data-testid="execute-analysis" onClick={p.onExecute}
            disabled={!ready} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40">
            <Play size={14}/> {p.executing ? "Analisando..." : "Executar análise"}
          </button>
          {p.preparing && <span role="status" className="text-xs text-slate-500">Verificando as condições da análise...</span>}
        </div>
        {status !== "available" && !p.preparing && <p role="status" data-testid="pending-reasons" className="text-xs leading-5 text-amber-900">
          {p.capability?.reasons?.length ? p.capability.reasons.slice(0,3).join(" ") :
            "Ainda há condições a conferir para esta análise."}
        </p>}
        {p.advanced && <details className="rounded-lg border border-slate-100 px-2 py-2">
          <summary className="flex cursor-pointer items-center gap-1 text-xs font-medium text-teal">
            <SlidersHorizontal size={14}/> Ajustar condições específicas ou situações excepcionais
          </summary>
          <div className="mt-3">{p.advanced}</div>
        </details>}
      </div>
    </div>
  </section>;
}
