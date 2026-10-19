import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ContextConfig from "./ContextConfig";
import RequirementChecklist from "./RequirementChecklist";
import DataResolution from "./DataResolution";
import { displayPeriod } from "./DistributionResults";
import ResultWorkspace, { type RepresentationRecord, type Sibling } from "./ResultWorkspace";
import ResultHeader from "./ResultHeader";
import { periodsInText } from "./headerModel";
import PreviousAnalyses from "./PreviousAnalyses";
import InvestigationOverview, { ResultIdentity } from "./InvestigationOverview";
import { resultSummary, selectionCompatibility } from "./investigation";
import { InvestigationViewState, type ViewMemory } from "./InvestigationViewState";
import ResultTable from "./ResultTable";
import { tableColumns } from "./representation";
import { comparisonWindow, valuesPeriodOf } from "./periods";
import { scrollAnalysisTo, type NavigationTarget, type WorkspaceStage } from "./workspaceNavigation";
import { governedRoles } from "./curatedPreparation";
import { fieldOptions } from "./fieldChoices";
import { EMPTY_SCOPE, describeScope, effectiveScope, fromMembers, municipalOnly, periodsForScope,
  type Abrangencia, type Levels, type ScopeSelection } from "./territorialScope";
import TerritorialScopeSelector from "./TerritorialScopeSelector";
import AnalysisAssistant, {type TerritorialProposal} from "./AnalysisAssistant";
import ConversationalPreparation, {GOVERNED_CRS, type FieldRole} from "./ConversationalPreparation";
import BrandAvatar from "./BrandAvatar";
import WorkspaceDialog from "./WorkspaceDialog";
import { analyticalRequest, attachResult, diagnosticLabel, presentationIntent, type Diagnostic, type Placement } from "./diagnostics";
import PreparationPanel, { preparationRequirements } from "./PreparationPanel";
import WelcomeHero from "./WelcomeHero";
import TerritorialSelection, {type Territory} from "./TerritorialSelection";
import ReferenceSetup, {type ReferenceMode} from "./ReferenceSetup";
import CriteriaBuilder from "./CriteriaBuilder";
import {type CriteriaMetadata} from "./CriteriaResults";
import { ATTRIBUTE_LABELS, addCondition, complete, describe as describeCriteria, leaves as criteriaLeaves, nextId as nextLeafId,
  uses as criteriaUses, type BandsSpec, type CriteriaNode, type Leaf, type RankingSpec } from "./criteriaTree";
import SessionPrivacy, { useSessionPrivacy } from "./SessionPrivacy";
import { sessionFetch as fetch, contextRevision, updateContextRevision, trackSession, endSession } from "./conversationSession";
import type { Multiplicity, ResolutionOptions } from "./DataResolution";
import type { LucideIcon } from "lucide-react";
import {
  ArrowDownToLine, ArrowRight, BarChart3, Calculator, CheckCircle2, Filter,
  Home, Menu, X, Grid2X2,
  ChevronDown, ClipboardList, Clock3, Database, Download, FileBarChart2, FileSpreadsheet,
  FileUp, FolderUp, Bot, Info, Layers3, ListFilter,
  LoaderCircle, LocateFixed, MapPinned, MoveRight, RefreshCw, SearchCheck, Settings2, ShieldCheck,
  Sparkles, TrendingUp, UploadCloud, UsersRound, XCircle
} from "lucide-react";

type Role = "territory" | "territory_id" | "period" | "category" | "count" | "population" | "latitude" | "longitude" | "identity";
import { ANALYSIS_LABELS, type Operation } from "./analysisCatalog";
type Mapping = Partial<Record<Role, string>>;
type SuperiorLevel = "territorio_superior_1" | "territorio_superior_2";
type SuperiorMapping = Partial<Record<SuperiorLevel, string>>;
type FieldStatus = "recognized" | "confirmed" | "proposed" | "unmapped";
type ColumnProfile = {
  name: string; type: string; missing: number; suspicious_header: boolean;
  proposal: { role: Role; status: "recognized" | "proposed"; evidence: string }[];
};
// "needs_confirmation" é o valor do contrato da API para "escolha pendente" (D1: nenhuma confirmação de campo).
type Requirement = { status: "met" | "needs_confirmation" | "missing"; title: string; detail: string; kind?: "escolha" | "dados"; step?: 0 | 1 };
type FieldOrigin = "PERFIL_GOVERNADO" | "REGRA_CONFIGURADA" | "ESCOLHA_DO_USUARIO" | "SUGESTAO_NAO_ESCOLHIDA";
type Capability = { status: "available" | "needs_confirmation" | "unavailable"; reasons: string[]; requirements: Requirement[];
  /** Base oficial com abrangência: estado de cada nível e da seleção (mistura ou mínimo pendente). */
  niveis?: Record<string, { status: string; reasons: string[] }> };
type Preflight = {
  territory_choices?: Territory[]; selection_reason?: string;
  multiplicity: Multiplicity;
  territorial_hierarchy?: {status: string; levels: {role: string; column: string}[]; warnings: string[]};
  capabilities: Record<Operation, Capability>;
  field_states: Record<Role, { status: FieldStatus; column: string; message: string; evidence?: string; origin?: FieldOrigin }>;
  values: {territories: string[]; periods: string[]; categories: string[]};
  /** Objeto de análise: reconhecido (catálogo ou perfil), informado por você ou ausente. */
  object?: {status: "reconhecido" | "informado" | "ausente"; origin: string | null};
  /** Premissas aplicadas pelo backend nesta preparação (perfil oficial e premissas da análise). */
  premises?: string[];
  /** Separador das coordenadas verificado nos dados (null: formato misto; "" quando não se aplica). */
  coordinate_separator?: string | null;
  profile: {row_count: number; column_count: number; recognized_roles: number};
  /** Base oficial: escolha pendente na abrangência territorial (mistura de níveis ou mínimo de territórios). */
  abrangencia_pendente?: string;
};
type Inspection = {
  requires_sheet: boolean; sheets: string[]; columns: string[]; row_count: number;
  suggested_mapping: Mapping; suggested_columns?: Partial<Record<Role, string[]>>; periods: string[]; categories: string[]; territories: string[];
  column_profiles: ColumnProfile[]; preflight: Preflight | null; suggested_category_constant: string;
  derived_fields?: { column: string; role: Role; source_columns: string[]; format: string }[];
  curated_defaults?: { mapping: Mapping; category: string; scope: "national" | "municipal"; count_unit: string;
    confirmed_roles: Role[]; governed_roles?: Role[]; fts_scope_confirmed: boolean; object_confirmed: boolean;
    population_denominator_confirmed: boolean;
    premises?: { option: string; label: string; origin: string; operations: Operation[] }[] } | null;
  source?: { dataset: string; label: string; scope: "national" | "municipal"; version: string;
    default_scopes: Partial<Record<Operation, "national" | "municipal">> };
  /** Base oficial: Brasil, estados e regras de cada análise para a abrangência territorial (sem dados ao provedor). */
  niveis?: Levels;
  catalog?: { modo: string; versao: string; versao_governada: string | null; versao_fixada: string | null;
    integridade: string; complemento_geografico?: { estado: string; sha256?: string; identificador?: string;
      versao?: string; motivo?: string; token: string } } | null;
};
type Metric = { label: string; value: string | number };
type AnalysisResult = { result_id: string; title: string; description: string; rows: Record<string, unknown>[]; total_rows: number; metrics: Metric[]; notes: string[]; metadata: Record<string, unknown>; detail_rows?: Record<string, unknown>[]; conversation_reference?: {available: boolean} };
type Exploration = TerritorialProposal & {
  criteria_patch?: {mode?: "replace" | "and" | "or"; leaf?: Omit<Leaf, "id">; ranking?: {attribute: RankingSpec["attribute"]; direction: "asc" | "desc"};
    top_n?: number; exact_n?: boolean; compare?: "previous"}; criteria_pending_ranking?: RankingSpec["attribute"]};
type CriteriaComparison = {criteria?: CriteriaNode; ranking?: RankingSpec; label: string};
type Feature = { id: Operation; title: string; detail: string; icon: LucideIcon; tone: string };

const API = import.meta.env.VITE_API_BASE_URL || "";
const SPATIAL_OPERATIONS: Operation[] = ["spatial", "nearest"];

async function readApiResponse(response: Response): Promise<any> {
  const raw = await response.text();
  let body: any;
  try { body = JSON.parse(raw); }
  catch {
    throw new Error("Não foi possível interpretar a resposta do serviço (HTTP " + response.status + "). Tente novamente ou procure suporte.");
  }
  if (!response.ok) {
    const message = typeof body?.detail === "string" ? body.detail : "Falha no processamento da solicitação.";
    throw new Error(message + " (HTTP " + response.status + ")");
  }
  return body;
}

function readableError(exc: unknown): string {
  const value = exc instanceof Error ? exc.message : String(exc);
  if (/failed to fetch|networkerror|fetch failed|network request failed/i.test(value)) {
    return "Não foi possível acessar o serviço de análise. Tente novamente em instantes.";
  }
  return value;
}

const FEATURES: Feature[] = [
  { id: "density", title: ANALYSIS_LABELS.density, detail: "Profissionais por 1.000 habitantes", icon: Calculator, tone: "teal" },
  { id: "counts", title: ANALYSIS_LABELS.counts, detail: "Contagens absolutas da força de trabalho", icon: UsersRound, tone: "indigo" },
  { id: "distribution", title: ANALYSIS_LABELS.distribution, detail: "Quartis, quintis e decis, posições e frequências", icon: BarChart3, tone: "violet" },
  { id: "comparisons", title: ANALYSIS_LABELS.comparisons, detail: "Territórios, categorias e períodos", icon: MoveRight, tone: "orange" },
  { id: "temporal", title: ANALYSIS_LABELS.temporal, detail: "Mudanças e tendências", icon: TrendingUp, tone: "blue" },
  { id: "aggregate", title: ANALYSIS_LABELS.aggregate, detail: "Conjuntos territoriais e indicadores", icon: Layers3, tone: "emerald" },
  { id: "spatial", title: ANALYSIS_LABELS.spatial, detail: "Distâncias e referências geográficas", icon: MapPinned, tone: "rose" },
  { id: "ranking", title: ANALYSIS_LABELS.ranking, detail: "Seleções, posições e ordenações", icon: ListFilter, tone: "amber" },
  { id: "rotation", title: ANALYSIS_LABELS.rotation, detail: "Permanência da coorte inicial", icon: RefreshCw, tone: "cyan" },
  { id: "report", title: ANALYSIS_LABELS.report, detail: "Consolidação, tabelas e exportações", icon: FileBarChart2, tone: "slate" },
  { id: "nearest", title: ANALYSIS_LABELS.nearest, detail: "Referência geográfica mais próxima de cada alvo", icon: LocateFixed, tone: "amber" },
  { id: "criteria", title: ANALYSIS_LABELS.criteria, detail: "Condições combinadas, réguas, rankings e recortes", icon: Filter, tone: "violet" }
];
const ROLES: { key: Role; label: string; help: string }[] = [
  { key: "territory_id", label: "Código territorial", help: "Distingue unidades com nomes iguais" },
  { key: "territory", label: "Território", help: "Município, polo, DSEI ou outro recorte declarado" },
  { key: "period", label: "Período", help: "Ano ou referência temporal" },
  { key: "category", label: "Categoria", help: "Profissão ou categoria da FTS" },
  { key: "count", label: "Quantidade", help: "Contagem com significado estabelecido" },
  { key: "population", label: "População", help: "Denominador territorial" },
  { key: "latitude", label: "Latitude", help: "Graus decimais" },
  { key: "longitude", label: "Longitude", help: "Graus decimais" },
  { key: "identity", label: "Identificador individual", help: "Apenas para contagem distinta ou coortes" }
];
const sameList = (a: string[], b: string[]) => a.length === b.length && a.every((value, index) => value === b[index]);
const shortNum = (n: number) => new Intl.NumberFormat("pt-BR", n !== 0 && Math.abs(n) < 1e-6
  ? { notation: "scientific", maximumSignificantDigits: 8 } : { maximumFractionDigits: 6 }).format(n);
function downloadText(name: string, body: string, mime: string) {
  const url = URL.createObjectURL(new Blob([body], { type: mime }));
  const link = document.createElement("a");
  link.href = url; link.download = name; link.click();
  URL.revokeObjectURL(url);
}
function exportCsv(rows: Record<string, unknown>[]) {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const escape = (v: unknown) => {
    let value = v === null || v === undefined ? "" : String(v);
    if (typeof v === "string" && /^[\s]*[=+@\-]/.test(value)) value = "'" + value;
    return '"' + value.replaceAll('"', '""') + '"';
  };
  downloadText("resultado_diagnostico.csv", "\uFEFF" + [cols.map(escape).join(";"), ...rows.map(r => cols.map(c => escape(r[c])).join(";"))].join("\r\n"),
    "text/csv;charset=utf-8");
}
function SectionHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description?: string }) {
  return <div className="mb-6">
    <div className="mb-2 text-[11px] font-bold uppercase tracking-[.23em] text-teal">{eyebrow}</div>
    <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-[29px]">{title}</h2>
    {description && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{description}</p>}
  </div>;
}
function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return <label className="flex min-w-0 flex-col gap-1.5 text-xs font-semibold text-slate-600">
    {label}
    <select aria-label={label} className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink outline-none" value={value} onChange={e => onChange(e.target.value)}>
      <option value="">Todos / não selecionado</option>
      {(label.toLowerCase().includes("período") ? [...options].sort((a,b)=>b.localeCompare(a,"pt-BR",{numeric:true})) : options).map(v =>
        <option key={v} value={v}>{label.toLowerCase().includes("período") ? displayPeriod(v) : v}</option>)}
    </select>
  </label>;
}
function App() {
  const privacy = useSessionPrivacy();
  useEffect(() => { if (privacy.accepted) return trackSession(); }, [privacy.accepted]);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [workspaceStage, setWorkspaceStage] = useState<WorkspaceStage>("preparation");
  // A seleção territorial é um bloco da preparação, recolhido até o usuário pedir.
  const [territoriesOpen, setTerritoriesOpen] = useState(false);
  const [multiplePeriods, setMultiplePeriods] = useState(false);
  const [periodEditor, setPeriodEditor] = useState(0);
  const [page, setPage] = useState<"home" | "results">("home");
  const [confirmNewAnalysis, setConfirmNewAnalysis] = useState(false);
  const [confirmNewSession, setConfirmNewSession] = useState(false);
  const [closingSession, setClosingSession] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([]);
  const [diagnosticId, setDiagnosticId] = useState(1);
  const nextDiagnostic = useRef(1);
  const placement = useRef<Placement | null>(null);
  const pendingRun = useRef<Operation | null>(null);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [usingBrazil, setUsingBrazil] = useState(false);
  const [sheet, setSheet] = useState("");
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [sourceVersion, setSourceVersion] = useState("");
  const [sourceGeneration, setSourceGeneration] = useState(0);
  const [mapping, setMapping] = useState<Mapping>({});
  const [hierarchyColumns, setHierarchyColumns] = useState<SuperiorMapping>({});
  const [inspecting, setInspecting] = useState(false);
  const [running, setRunning] = useState(false);
  const runningRef = useRef(false);
  const [step, setStep] = useState(0);
  const steps = useRef<Partial<Record<Operation, number>>>({});
  const [preflightAttempt, setPreflightAttempt] = useState(0);
  const [active, setActive] = useState<Operation | null>(null);
  const [requestedCategory, setRequestedCategory] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [territoryIds, setTerritoryIds] = useState<string[]>([]);
  // Base oficial: Brasil, estados, "Todos os municípios" e grupos por estado marcados na abrangência territorial. Os
  // municípios marcados ficam em territoryIds, a seleção compartilhada entre as análises, a conversa e as transferências.
  const [territoryScope, setTerritoryScope] = useState<ScopeSelection>(EMPTY_SCOPE);
  // Indicação da conversa ("no Brasil", "nos municípios") feita antes da escolha da base, aplicada ao carregá-la.
  const scopeHint = useRef<"national" | "municipal" | null>(null);
  const [comparisonIndicator, setComparisonIndicator] = useState<"quantity" | "density">("density");
  const [requestedIndicator, setRequestedIndicator] = useState<{operation:Operation; indicator:"quantity" | "density"; generation:number} | null>(null);
  const [requestText, setRequestText] = useState("");
  type Historical = {result: AnalysisResult; request: string; sourceKey: string; contextKey: string;
    preparation: ReturnType<typeof snapshotPreparation>; invalidReason: string};
  const [history, setHistory] = useState<Historical[]>([]);
  const [historyNotice, setHistoryNotice] = useState("");
  const viewMemory = useRef<Record<string, ViewMemory>>({});
  const [visualSelection, setVisualSelection] = useState<string[]>([]);
  const [resultExpanded, setResultExpanded] = useState(true);
  const pendingTerritories = useRef<{operation: Operation; requestedCount?: number | null; source: string} | null>(null);
  const [selectionProposal, setSelectionProposal] = useState<Exploration | null>(null);
  const [error, setError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [serverStatus, setServerStatus] = useState<"checking" | "online" | "offline">("checking");
  const [sourceDiagnostic, setSourceDiagnostic] = useState<Record<string, unknown> | null>(null);
  const [periodFilter, setPeriodFilter] = useState("");
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([]);
  // Comparação com janela (D6): competência dos valores escolhida na caixa "Competência dos valores"; sem escolha, a última.
  const [comparisonValuesPeriod, setComparisonValuesPeriod] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [reference, setReference] = useState("");
  const [crs, setCrs] = useState("");
  const [referenceMode, setReferenceMode] = useState<ReferenceMode>("");
  const [referenceIds, setReferenceIds] = useState<string[]>([]);
  const [criterionOperator, setCriterionOperator] = useState("");
  const [criterionValue, setCriterionValue] = useState("");
  const [criteriaTree, setCriteriaTree] = useState<CriteriaNode | null>(null);
  const [criteriaRanking, setCriteriaRanking] = useState<RankingSpec | null>(null);
  const [criteriaBands, setCriteriaBands] = useState<BandsSpec | null>(null);
  const [distanceScope, setDistanceScope] = useState("");
  const [eligibilityScope, setEligibilityScope] = useState("");
  const [criteriaComparison, setCriteriaComparison] = useState<CriteriaComparison | null>(null);
  const pendingRanking = useRef<RankingSpec["attribute"] | null>(null);
  const [quantiles, setQuantiles] = useState(5);
  const [distributionIndicator, setDistributionIndicator] = useState<"" | "quantity" | "density">("");
  const [temporalIndicator, setTemporalIndicator] = useState<"" | "quantity" | "density">("");
  const [reportIndicator, setReportIndicator] = useState<"" | "quantity" | "density">("");
  // D1: só escolhas. Os papéis escolhidos seguem no campo "confirmed_roles" do contrato da API (significado: escolhidos);
  // período único é uma opção do seletor de período; o objeto de análise é o texto informado. As antigas declarações
  // são premissas aplicadas pelo backend, com nota no resultado: a tela não as pede nem envia.
  const [singlePeriod, setSinglePeriod] = useState(false);
  const [selectedRoles, setSelectedRoles] = useState<Role[]>([]);
  const [countUnit, setCountUnit] = useState("");
  const [customCountUnit, setCustomCountUnit] = useState("");
  const [objectDraft, setObjectDraft] = useState("");
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [preflighting, setPreflighting] = useState(false);
  const [preflightError, setPreflightError] = useState("");
  const [resolutions, setResolutions] = useState<ResolutionOptions>({});
  const revision = useRef(0);
  const uploadRevision = useRef(0);

  function snapshotPreparation() {
    return { mapping: {...mapping}, options: semanticOptions(), resolutions: {...resolutions},
      objectDraft, quantiles, distributionIndicator, selectedPeriods, multiplePeriods, territoryIds, territoryScope, comparisonIndicator,
      comparisonValuesPeriod,
      referenceMode, referenceIds, criterionOperator, criterionValue,
      criteriaTree, criteriaRanking, criteriaBands, distanceScope, eligibilityScope, criteriaComparison };
  }
  function restorePreparation(saved: ReturnType<typeof snapshotPreparation>) {
    const o = saved.options;
    setMapping(saved.mapping); setSelectedRoles(o.confirmed_roles);
    setHierarchyColumns(o.hierarchy_columns);
    setSinglePeriod(!!o.single_period_confirmed);
    setCountUnit(o.count_unit); setCustomCountUnit(o.custom_count_unit);
    setObjectDraft(saved.objectDraft);
    setPeriodFilter(o.period_filter); setSelectedPeriods(saved.selectedPeriods);
    setMultiplePeriods(saved.multiplePeriods);
    setCategoryFilter(o.category_filter); setReference(o.reference_territory);
    setResolutions(saved.resolutions); setCrs(o.crs);
    setQuantiles(saved.quantiles); setDistributionIndicator(saved.distributionIndicator);
    setTemporalIndicator(o.temporal_indicator); setReportIndicator(o.report_indicator);
    setTerritoryIds(saved.territoryIds); setTerritoryScope(saved.territoryScope || EMPTY_SCOPE);
    setComparisonIndicator(saved.comparisonIndicator);
    setComparisonValuesPeriod(saved.comparisonValuesPeriod || "");
    setReferenceMode(saved.referenceMode); setReferenceIds(saved.referenceIds);
    setCriterionOperator(saved.criterionOperator); setCriterionValue(saved.criterionValue);
    setCriteriaTree(saved.criteriaTree); setCriteriaRanking(saved.criteriaRanking); setCriteriaBands(saved.criteriaBands);
    setDistanceScope(saved.distanceScope); setEligibilityScope(saved.eligibilityScope); setCriteriaComparison(saved.criteriaComparison);
  }

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const selectedFeature = FEATURES.find(f => f.id === active);
  const sourceKey = JSON.stringify({source: usingBrazil ? "brazil" : "upload:" + sourceGeneration,
    version: sourceVersion, scope: inspection?.source?.scope, sheet});
  // Premissas aplicadas pelo backend nesta preparação (perfil oficial e premissas da análise, com nota no resultado):
  // a interface não as pede. Vêm do último pré-exame; antes dele, as do perfil oficial.
  const governedPremises = new Set(preflight?.premises ||
    (usingBrazil ? (inspection?.curated_defaults?.premises || []).map(item => item.option) : []));
  // Base oficial: as configurações reúnem, na caixa "Abrangência territorial", o Brasil (total nacional) e os municípios.
  // Nunca cai no fluxo das bases importadas, mesmo com uma coluna alterada.
  const configurationPanel = usingBrazil && !!inspection?.curated_defaults;
  const municipalScope = !usingBrazil || inspection?.source?.scope === "municipal";
  // Abrangência territorial da base oficial (D3): a inspeção é sempre municipal e traz o bloco "niveis" (estados, Brasil
  // e as regras de cada análise). Trocar de análise não recarrega a base: só a parte da seleção que a análise aceita vale
  // nela (sem nada aplicável, o padrão da análise), e o backend confere o pedido.
  const levels = usingBrazil ? inspection?.niveis : undefined;
  const officialScope = configurationPanel && !!levels;
  const levelRule = officialScope && active ? levels!.operacoes[active] : undefined;
  const effective = officialScope ? effectiveScope(territoryScope, territoryIds, levelRule) : null;

  const conversationSourceKey = JSON.stringify({source:usingBrazil ? "brazil" : "upload:" + sourceGeneration,
    version:sourceVersion,sheet});
  const geoToken = inspection?.catalog?.complemento_geografico?.token || "";
  const resultGeoToken = (item: AnalysisResult) => {
    const geo = item.metadata.complemento_geografico as {sha256?: string; estado?: string} | undefined;
    return geo ? geo.sha256 || geo.estado || "" : "";
  };
  // Resultado espacial calculado com outra versão da camada não é retomado nem reutilizado em silêncio.
  const compatible = (item: {sourceKey: string; result: AnalysisResult}) =>
    item.sourceKey === sourceKey && (!resultGeoToken(item.result) || resultGeoToken(item.result) === geoToken);
  const criteriaDistance = criteriaUses(criteriaTree, "distancia", criteriaRanking, criteriaBands) ||
    criteriaLeaves(criteriaComparison?.criteria || null).some(leaf => leaf.attribute === "distancia");
  // Critérios só dependem das coordenadas (e da camada complementar) quando usam a distância.
  const spatialRequest = (operation: Operation) => SPATIAL_OPERATIONS.includes(operation) || (operation === "criteria" && criteriaDistance);
  const requestKey = (operation: Operation) => JSON.stringify({sourceKey, operation, mapping,
    ...(spatialRequest(operation) ? {geo: geoToken} : {}),
    options: {...semanticOptions(), territory_ids: semanticOptions().territory_ids ? [...territoryIds].sort() : undefined,
      // Mesma abrangência em outra ordem de marcação é o mesmo pedido (o backend também normaliza a ordem).
      abrangencia: effective ? {...effective.abrangencia, municipios: {...effective.abrangencia.municipios,
        ids: [...effective.abrangencia.municipios.ids].sort()}} : undefined}});
  const historical = history.find(item=>item.result.result_id===result?.result_id);
  const resultOperation = result?.metadata.operation as Operation | undefined;
  const resultFeature = FEATURES.find(item=>item.id===resultOperation);
  // Estas notas técnicas continuam na exportação, mas não na apresentação dos resultados.
  const resultNotes = result?.notes.filter(note =>
    !note.startsWith("Período AAAAMM composto em memória") && !note.startsWith("Identificação territorial:")) || [];
  const resultStatus = historical?.invalidReason ? "INVALIDADO" :
    historical && active && historical.contextKey===requestKey(active) ? "VIGENTE" : "NAO_VIGENTE";
  useEffect(() => { updateContextRevision(); }, [sourceKey, JSON.stringify(mapping),
    JSON.stringify(semanticOptions()), active, result?.result_id]);
  type NearestMetadata = {conjunto_referencias?: {forma: string; membros: {id: string}[]}; cobertura_referencias?: unknown[]};
  const nearestMetadata = result?.metadata.nearest_reference as NearestMetadata | undefined;
  const nearestMembers = nearestMetadata?.conjunto_referencias?.membros.map(item=>item.id) || [];
  // Registro da representação em uso (transformações visuais), exportado com “Método e parâmetros”.
  const representationRecord = useRef<RepresentationRecord | null>(null);
  const keepRepresentation = useCallback((record: RepresentationRecord) => {
    representationRecord.current = record;
    const selected = (record.selecao_visual as string[]) || [];
    setVisualSelection(previous => sameList(previous, selected) ? previous : selected);
  }, []);
  // Outras competências do mesmo pedido já calculadas e compatíveis: navegação sem fabricar resultados.
  const siblings = useMemo<Sibling[]>(() => {
    if (!result || !historical) return [];
    // Só para agrupar competências: opção desmarcada ou vazia equivale a opção ausente (o motor lê ambas como
    // não declaradas). O estado vigente continua exigindo a chave exata da solicitação.
    const empty = (value: unknown) => value === false || value === "" || value === null || value === undefined ||
      (Array.isArray(value) ? !value.length : typeof value === "object" && !Object.keys(value as object).length);
    const keyWithoutPeriod = (item: Historical) => {
      try {
        const parsed = JSON.parse(item.contextKey);
        const options = Object.entries(parsed.options || {}).filter(([key, value]) =>
          key !== "period_filter" && key !== "period_filters" && key !== "comparison_values_period" && !empty(value))
          .sort(([a], [b]) => a.localeCompare(b));
        return JSON.stringify({...parsed, options});
      } catch { return item.contextKey; }
    };
    const reference = keyWithoutPeriod(historical);
    return history.filter(item => !item.invalidReason && compatible(item) && keyWithoutPeriod(item) === reference)
      .map(item => ({item, periods: (item.result.metadata.periods as string[] | undefined) || []}))
      .filter(entry => entry.periods.length === 1)
      .map(entry => ({id: entry.item.result.result_id, period: entry.periods[0], current: entry.item.result.result_id === result.result_id}))
      .sort((a, b) => a.period.localeCompare(b.period, "pt-BR", {numeric: true}));
  }, [result, history, historical, sourceKey, geoToken]);

  function resetReferences() {
    setReferenceMode(""); setReferenceIds([]); setCriterionOperator(""); setCriterionValue("");
    // Critérios citam territórios e referências da base anterior: nunca atravessam uma troca de fonte.
    setCriteriaTree(null); setCriteriaRanking(null); setCriteriaBands(null); setDistanceScope(""); setEligibilityScope("");
    setCriteriaComparison(null); pendingRanking.current = null;
  }
  /** Competências de toda a seleção de uma análise: com o Brasil, as da fonte nacional (e a união com as municipais
   * quando há outros níveis); sem ele, as da fonte municipal. */
  function scopePeriodsOf(details: Inspection | null, operation: Operation | "", scope: ScopeSelection, ids: string[]): string[] {
    const municipal = details?.periods || [];
    const rule = usingBrazil && details?.curated_defaults && details.niveis && operation ? details.niveis.operacoes[operation] : undefined;
    return rule ? periodsForScope(effectiveScope(scope, ids, rule), details!.niveis!.brasil.periodos, municipal) : municipal;
  }
  async function inspectFile(nextFile: File | null, nextSheet = "", level = "auto", operation = "") {
    if (!privacy.accepted) return;
    setSourceGeneration(value => value + 1); setTerritoryIds([]); setTerritoryScope(EMPTY_SCOPE); resetReferences(); setTerritoriesOpen(false);
    const currentUpload = ++uploadRevision.current;
    revision.current += 1;
    setInspecting(true);
    setUploadError("");
    setError("");
    setInspection(null); setPreflight(null);
    const form = new FormData();
    if (nextFile) form.append("file", nextFile);
    else { form.append("dataset", "brazil"); form.append("scope", level); form.append("operation", operation); }
    form.append("sheet", nextSheet);
    try {
      const response = await fetch(API + "/api/inspect", { method: "POST", body: form });
      const details = await readApiResponse(response) as Inspection;
      if (currentUpload !== uploadRevision.current) return;
      // Indicação da conversa feita antes da escolha da base ("no Brasil", "nos municípios").
      const hint = nextFile ? null : scopeHint.current;
      scopeHint.current = null;
      const scope = hint === "national" ? {...EMPTY_SCOPE, brasil: true} : hint === "municipal" ? {...EMPTY_SCOPE, todos: true} : EMPTY_SCOPE;
      setTerritoryScope(scope);
      setInspection(details);
      setSourceVersion(details.source?.version || "");
      setMapping(details.suggested_mapping);
      setHierarchyColumns({});
      // Os papéis do perfil oficial e os reconhecidos por regra são estabelecidos pelo backend; nada é escolhido aqui.
      setSelectedRoles([]);
      setSinglePeriod(false);
      setCountUnit(details.curated_defaults?.count_unit || "");
      setCustomCountUnit("");
      // A sugestão do cabeçalho vira um botão "Usar sugestão": nunca é aplicada sozinha.
      setObjectDraft("");
      setPreflight(details.preflight);
      setPreflightError("");
      setServerStatus("online");
      setPeriodFilter("");
      // Comparação: a janela padrão é a série anual de junho (D6), com os valores na última competência dela.
      const window = operation === "comparisons" ? comparisonWindow(scopePeriodsOf(details, operation, scope, [])) : [];
      setSelectedPeriods(operation === "temporal" ? scopePeriodsOf(details, operation, scope, []) : window);
      setMultiplePeriods(operation === "temporal" || window.length > 0);
      setComparisonValuesPeriod("");
      setWorkspaceStage("preparation");
      setCategoryFilter(details.curated_defaults?.category || "");
      setReference("");
      setResolutions({});
      setCrs("");
      setQuantiles(5);
      setDistributionIndicator("");
      setTemporalIndicator(""); setReportIndicator("");
    } catch (exc) {
      if (currentUpload !== uploadRevision.current) return;
      const message = readableError(exc);
      setUploadError(message);
      if (message.includes("Não foi possível alcançar")) setServerStatus("offline");
    } finally { if (currentUpload === uploadRevision.current) setInspecting(false); }
  }
  async function chooseFile(next: File | undefined) {
    if (!next || !privacy.accepted) return;
    uploadRevision.current += 1;
    setStep(0); steps.current = {};
    setUsingBrazil(false);
    setFile(next);
    setSheet("");
    // Preserva apenas a escolha da capacidade; as escolhas de colunas são reiniciadas.

    setUploadError("");
    setInspection(null);
    setPreflight(null);
    if (!/\.(csv|xls|xlsx)$/i.test(next.name)) {
      setUploadError("Formato não reconhecido. Selecione um arquivo CSV, XLS ou XLSX.");
      return;
    }
    if (next.size > 30 * 1024 * 1024) {
      setUploadError("Arquivo acima de 30 MB. Este é o limite experimental da versão atual; a base não foi processada.");
      return;
    }
    await inspectFile(next);
  }
  function appendSource(form: FormData) {
    form.append("context_revision", String(contextRevision()));
    if (usingBrazil) {
      form.append("dataset", "brazil");
      form.append("scope", inspection?.source?.scope || "auto");
      form.append("dataset_version", inspection?.source?.version || "");
    } else if (file) form.append("file", file);
    form.append("sheet", sheet);
  }
  function chooseBrazil() {
    if (!privacy.accepted) return;
    setStep(0); steps.current = {};
    setUsingBrazil(true); setFile(null); setSheet("");
    // A inspeção da base oficial é sempre municipal, com o bloco dos níveis (Brasil, estados e municípios).
    void inspectFile(null, "", "municipal", active || "");
  }
  function selectAnalysis(operation: Operation, proposal?: {
    category: string; period: string; territory: string; indicator: "density" | "quantity" | null
  }) {
    setCatalogOpen(false); setPeriodEditor(0);
    setPage("home"); setWorkspaceStage("preparation"); setTerritoriesOpen(false);
    setRequestedIndicator(proposal?.indicator ? {operation, indicator:proposal.indicator, generation:sourceGeneration} : null);
    if (pendingTerritories.current?.operation !== operation) pendingTerritories.current = null;
    setRequestedCategory(proposal?.category || "");
    const territory = (proposal?.territory || "").normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const hinted = /municipio|municipios|municipal|cidade|cidades/.test(territory) ? "municipal"
      : /^(?:brasil|pais|nacional)$/.test(territory) ? "national" : null;
    // Trocar de análise não recarrega a base nem troca de fonte: a abrangência marcada continua, e só a parte que a
    // análise aceita vale nela. Um pedido explícito ("no Brasil", "nos municípios") ajusta a seleção.
    let scope = territoryScope, ids = territoryIds;
    if (hinted && (usingBrazil || !inspection)) {
      if (!inspection) scopeHint.current = hinted;
      else if (hinted === "national") { scope = {...EMPTY_SCOPE, brasil: true}; ids = []; replaceSelection(scope, ids); }
      else if (!territoryIds.length && !territoryScope.grupos.length) {
        scope = {...EMPTY_SCOPE, todos: true}; replaceSelection(scope, ids);
      }
    }
    if (active) steps.current[active] = step;
    setStep(steps.current[operation] || 0);
    setActive(operation);  setError("");
    if (operation === "temporal") {
      setPeriodFilter(""); setMultiplePeriods(true);
      if (!selectedPeriods.length) setSelectedPeriods(scopePeriodsOf(inspection, operation, scope, ids));
      if (!temporalIndicator) setTemporalIndicator(active === "counts" ? "quantity" : "density");
    }
    if (operation === "comparisons" && !periodFilter && !(multiplePeriods && selectedPeriods.length)) {
      // Sem período escolhido, a comparação começa na série anual de junho (D6), com os valores na última competência.
      const window = comparisonWindow(scopePeriodsOf(inspection, operation, scope, ids));
      if (window.length) { setMultiplePeriods(true); setSelectedPeriods(window); setComparisonValuesPeriod(""); }
    }
  }
  useEffect(() => {
    if (!requestedIndicator) return;
    if (requestedIndicator.generation !== sourceGeneration || requestedIndicator.operation !== active) {
      setRequestedIndicator(null); return;
    }
    if (inspecting || !inspection) return;
    const {operation, indicator} = requestedIndicator;
    if (operation === "comparisons") setComparisonIndicator(indicator);
    if (operation === "distribution") setDistributionIndicator(indicator);
    if (operation === "temporal") setTemporalIndicator(indicator);
    if (operation === "report") setReportIndicator(indicator);
    setRequestedIndicator(null);
  }, [requestedIndicator, sourceGeneration, active, inspecting, inspection]);
  // Somente uma correspondência literal inequívoca permite aplicar automaticamente
  // o filtro pedido. Equivalências semânticas permanecem para escolha explícita.
  useEffect(() => {
    if (!inspection || inspection.requires_sheet || inspecting || !requestedCategory || categoryFilter) return;
    const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();
    const matches = inspection.categories.filter(value => normalize(value) === normalize(requestedCategory));
    if (matches.length === 1) setCategoryFilter(matches[0]);
  }, [requestedCategory, inspection, inspecting, categoryFilter]);

  // Competência dos valores da comparação: período único, ou a escolhida (ou a última) da janela de vários períodos. Função
  // (e não constante): semanticOptions é chamada antes deste ponto do componente.
  function comparisonPeriod() {
    return valuesPeriodOf(multiplePeriods ? "" : periodFilter, multiplePeriods ? selectedPeriods : [], comparisonValuesPeriod);
  }
  function semanticOptions() {
    // Base oficial: a abrangência territorial (Brasil, estados e municípios) segue em "abrangencia", só com a parte que a
    // análise aceita (ou o padrão dela); o backend resolve a rota e confere o pedido. Nas demais, os territórios marcados.
    const territorial: {abrangencia?: Abrangencia; territory_ids?: string[]} = effective ? {abrangencia: effective.abrangencia}
      : territoryIds.length && (!usingBrazil || inspection?.source?.scope === "municipal") ? {territory_ids: territoryIds} : {};
    return {
      ...resolutions,
      // Base oficial: o separador decimal e o referencial são premissas internas; nada antigo da tela os substitui.
      ...(governedPremises.has("number_format") ? {number_format: undefined} : {}),
      ...territorial,
      comparison_indicator: comparisonIndicator,
      // Comparação com competência dos valores (D6): a competência única ou a escolhida na janela (padrão: a última).
      ...(active === "comparisons" && comparisonPeriod() ? {comparison_values_period: comparisonPeriod()} : {}),
      hierarchy_columns: hierarchyColumns,
      period_filter: periodFilter, period_filters: selectedPeriods,
      category_filter: categoryFilter,
      reference_territory: reference, crs: governedPremises.has("crs") ? "" : crs, quantile_count: quantiles,
      distribution_indicator: distributionIndicator,
      temporal_indicator: temporalIndicator, report_indicator: reportIndicator,
      // Papéis escolhidos pelo usuário (contrato: "confirmed_roles"). Nenhuma chave de premissa é enviada, nem como
      // false: um false explícito recusaria a premissa no backend (K1).
      confirmed_roles: selectedRoles,
      ...(singlePeriod && !mapping.period ? {single_period_confirmed: true} : {}),
      count_unit: countUnit,
      custom_count_unit: customCountUnit,
      ...(objectDraft.trim() ? (mapping.category ? {object_declaration: objectDraft.trim()} : {category_constant: objectDraft.trim()}) : {}),
      ...((active === "nearest" || (active === "criteria" && criteriaDistance)) && referenceMode ? {reference_mode: referenceMode, ...(referenceMode === "list"
        ? {reference_ids: referenceIds} : {reference_criterion: {operator: criterionOperator, value: criterionValue}})} : {}),
      ...(active === "criteria" ? {
        ...(criteriaTree ? {criteria: criteriaTree} : {}),
        ...(criteriaRanking ? {ranking: {attribute: criteriaRanking.attribute, direction: criteriaRanking.direction || undefined,
          ...(criteriaRanking.top_n ? {top_n: criteriaRanking.top_n, exact_n: !!criteriaRanking.exact_n} : {}),
          ...(criteriaTree ? {set: criteriaRanking.set || "atende"} : {})}} : {}),
        ...(criteriaBands ? {bands: criteriaBands} : {}),
        ...(distanceScope ? {distance_scope: distanceScope} : {}), ...(eligibilityScope ? {eligibility_scope: eligibilityScope} : {}),
        ...(criteriaComparison ? {comparison: criteriaComparison} : {})} : {})
    };
  }
  /** Substitui a seleção territorial (Brasil, estados e grupos da base oficial; municípios marcados). */
  function replaceSelection(scope: ScopeSelection, ids: string[]) {
    revision.current += 1;
    // Reaplicar a mesma seleção não cria estado novo: o pré-exame vigente já corresponde a ela.
    setTerritoryIds(current=>sameList(current, ids) ? current : ids);
    setTerritoryScope(current => JSON.stringify(current) === JSON.stringify(scope) ? current : scope);
    setSelectionProposal(null);
    // Nenhuma chave de premissa é gravada aqui (K1): as premissas são aplicadas pelo backend a cada pré-exame.
  }
  /** Conversa, "Usar os que atendem", transferências e "Usar como municípios-alvo": a seleção passa a ser esses municípios. */
  function changeTerritories(ids: string[]) {
    replaceSelection(EMPTY_SCOPE, ids);
  }
  function applyExploration(proposal: Exploration) {
    setPeriodEditor(0);
    if (!proposal.operation || !proposal.territory_ids) return;
    changeTerritories(proposal.territory_ids);
    const patch = proposal.options_patch || {};
    if (patch.period_filter) { setPeriodFilter(patch.period_filter); setSelectedPeriods([]); setMultiplePeriods(false); }
    else if (patch.period_filter !== undefined) setPeriodFilter("");
    const periods = patch.period_filters;
    if (periods !== undefined) {
      const next = !periods.length && proposal.operation === "temporal" ? scopePeriodsOf(inspection, "temporal", EMPTY_SCOPE,
        proposal.territory_ids) : periods;
      setSelectedPeriods(current=>sameList(current, next) ? current : next);
      if (periods.length || proposal.operation === "temporal") { setPeriodFilter(""); setMultiplePeriods(true); }
    }
    if (patch.temporal_indicator) setTemporalIndicator(patch.temporal_indicator);
    if (patch.comparison_indicator) setComparisonIndicator(patch.comparison_indicator);
    setActive(proposal.operation); setError("");
    scrollAnalysisTo("preparacao-conversacional");
  }
  // Resultado anterior comparável: mesma fonte, competência, categoria, universo e, se houver distância, referências.
  function previousCriteria(): {item: Historical; index: number} | null {
    const until = historical ? history.indexOf(historical) : history.length;
    const sorted = (ids?: string[]) => JSON.stringify([...(ids || [])].sort());
    for (let index = Math.min(until, history.length) - 1; index >= 0; index--) {
      const item = history[index], saved = item.preparation;
      if (item.result.metadata.operation !== "criteria" || item.invalidReason || !compatible(item)) continue;
      const sameContext = saved.options.period_filter === periodFilter && saved.options.category_filter === categoryFilter &&
        sorted(saved.territoryIds) === sorted(territoryIds);
      const distance = criteriaLeaves(saved.criteriaTree).some(leaf => leaf.attribute === "distancia") || saved.criteriaRanking?.attribute === "distancia";
      const sameReferences = !distance || JSON.stringify([saved.referenceMode, saved.referenceIds, saved.criterionOperator, saved.criterionValue]) ===
        JSON.stringify([referenceMode, referenceIds, criterionOperator, criterionValue]);
      if (!sameContext || !sameReferences) return null;
      return {item, index};
    }
    return null;
  }
  function compareWithPrevious(): string {
    const previous = previousCriteria();
    if (!previous) return "Não há resultado anterior de critérios no mesmo contexto (base, competência, categoria, universo e referências). " +
      "A comparação direta não foi preparada; retome o resultado desejado pelo histórico ou ajuste o contexto.";
    const saved = previous.item.preparation;
    setCriteriaComparison({...(saved.criteriaTree ? {criteria: saved.criteriaTree} : {}),
      ...(saved.criteriaRanking?.top_n ? {ranking: saved.criteriaRanking} : {}), label: "resultado " + (previous.index + 1)});
    return "Comparação preparada com o resultado " + (previous.index + 1) + " (" + (describeCriteria(saved.criteriaTree, countUnit) || "universo") +
      "). Execute a análise para obter os territórios em ambos, só no atual, só no anterior e indeterminados.";
  }
  function applyCriteriaPatch(patch: NonNullable<Exploration["criteria_patch"]>, reply: string): string {
    // Critérios usam os municípios: o Brasil e os estados marcados não valem nesta análise (sem trocar de fonte).
    if (active !== "criteria") selectAnalysis("criteria");
    return updateCriteria(patch) || reply;
  }
  function updateCriteria(patch: NonNullable<Exploration["criteria_patch"]>): string | null {
    scrollAnalysisTo("preparacao-conversacional");
    if (patch.compare) return compareWithPrevious();
    setCriteriaComparison(null);
    if (patch.leaf) {
      const leaf = {...patch.leaf, id: patch.mode === "replace" || !criteriaTree ? "c1" : nextLeafId(criteriaTree)} as Leaf;
      setCriteriaTree(patch.mode === "replace" || !criteriaTree ? leaf : addCondition(criteriaTree, leaf, patch.mode === "or" ? "or" : "and"));
      if (patch.mode === "replace") { setCriteriaRanking(null); setCriteriaBands(null); }
    }
    if (patch.ranking || patch.top_n) {
      setCriteriaRanking(current => ({...(current || {direction: ""}), ...(patch.ranking || {}),
        ...(patch.top_n ? {top_n: patch.top_n, exact_n: !!patch.exact_n} : {})} as RankingSpec));
    }
    return null;
  }
  function conversationOptions() {
    const pending = pendingTerritories.current;
    // A conversa recebe só os municípios marcados (como antes), nunca a abrangência: Brasil e estados não vão ao
    // interpretador nem ao provedor de IA.
    const {abrangencia: _scope, comparison_values_period: _values, ...options} = semanticOptions() as ReturnType<typeof semanticOptions> &
      {comparison_values_period?: string};
    return {...options, ...(usingBrazil && territoryIds.length ? {territory_ids: territoryIds} : {}),
      exploration_operation: active || "", exploration_indicator:
      active === "counts" ? "quantity" : active === "temporal" ? temporalIndicator || "quantity" : comparisonIndicator,
      ...(pending?.source === conversationSourceKey ? {conversation_pending_operation:pending.operation,
        conversation_requested_count:pending.requestedCount} : {})};
  }
  function acceptExploration(proposal: Exploration): string {
    if (proposal.reset_selection) changeTerritories([]);
    if (proposal.pending_operation) pendingTerritories.current = {operation:proposal.pending_operation,
      requestedCount:proposal.requested_count, source:conversationSourceKey};
    else if (proposal.operation && !proposal.clarification) pendingTerritories.current = null;
    pendingRanking.current = proposal.criteria_pending_ranking || null;
    if (proposal.criteria_patch) return applyCriteriaPatch(proposal.criteria_patch, proposal.reply || "");
    // Nomes explicitamente pedidos autorizam preparar esse novo conjunto; nada é executado.
    if (proposal.operation && proposal.territory_ids) applyExploration(proposal);
    else if (proposal.operation) selectAnalysis(proposal.operation);
    return proposal.clarification || proposal.reply || "Análise preparada. Confira os parâmetros na preparação.";
  }
  async function exploreMessage(message: string, choice?: {operation:Operation; indicator?:"quantity" | "density" | null}): Promise<string | null> {
    if (!inspection || inspecting) return null;
    const currentRevision = revision.current;
    const form = new FormData(); appendSource(form);
    form.append("message", analyticalRequest(message)); form.append("mapping", JSON.stringify(mapping));
    form.append("options", JSON.stringify({...conversationOptions(), ...(choice ? {conversation_operation_choice:choice.operation, exploration_indicator:choice.indicator || conversationOptions().exploration_indicator} : {}), ...(criteriaTree ? {criteria: criteriaTree} : {}),
      ...(criteriaRanking?.attribute ? {ranking: criteriaRanking} : {}),
      ...(pendingRanking.current ? {criteria_pending_ranking: pendingRanking.current} : {})}));
    const response = await fetch(API + "/api/exploration/interpret", {method:"POST", body:form});
    const proposal = await readApiResponse(response) as Exploration;
    if (currentRevision !== revision.current) return "O contexto mudou durante a interpretação. Envie novamente o pedido com a seleção atual.";
    // Pedido explícito pelo país inteiro marca o Brasil (total nacional): a contagem vem do arquivo nacional governado,
    // nunca de um agregado produzido a partir das linhas municipais.
    const normalizedRequest = message.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const wholeBrazil = /\b(?:brasil|nacional|pais inteiro|todo o pais)\b/.test(normalizedRequest) &&
      !/\b(?:municipios?|municipais|municipal|cidades?|por municipio|por cidade)\b/.test(normalizedRequest);
    if (!proposal.handled) {
      if (!choice) return null;
      // A escolha de capacidade também vale antes de haver uma seleção territorial.
      const territory = /\b(?:municipios?|municipal|cidades?)\b/.test(message.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()) ? "municípios" : "";
      selectAnalysis(choice.operation, {category:"", period:"", territory, indicator:choice.indicator || null});
      return "Análise escolhida. Confira o recorte, o indicador e as condições na preparação.";
    }
    const responseText = acceptExploration(proposal);
    if (usingBrazil && levels && wholeBrazil && !proposal.territory_ids?.length && !proposal.criteria_patch)
      replaceSelection({...EMPTY_SCOPE, brasil: true}, []);
    return responseText;
  }
  function exploreSelection(operation: Operation) {
    setRequestText(ANALYSIS_LABELS[operation] + " dos territórios selecionados");
    selectAnalysis(operation);
    scrollAnalysisTo("preparacao-conversacional");
  }
  function openHistorical(item: Historical) {
    if (running || inspecting || preflighting) return;
    const group = diagnostics.find(group => group.id === diagnosticId && group.resultIds.includes(item.result.result_id))
      || diagnostics.find(group => group.resultIds.includes(item.result.result_id));
    if (group) setDiagnosticId(group.id);
    placement.current = null;
    setResultExpanded(true);
    setVisualSelection((viewMemory.current[item.result.result_id]?.selected as string[]) || []);
    setResult(item.result); setHistoryNotice("Análise anterior aberta, sem recalcular."); setError("");
    scrollAnalysisTo("resultados");
  }
  function transferVisualSelection(id: string) {
    if (running || inspecting || preflighting) return;
    const target = history.find(item => item.result.result_id === id);
    if (!historical || !target || !visualSelection.length || !selectionCompatibility(historical, target).allowed) return;
    const memory = viewMemory.current[id] ||= {};
    memory.selected = [...visualSelection]; memory.focusId = visualSelection[0];
    // Filtros pertencem ao resultado de destino. O destaque não altera filtros, parâmetros ou dados.
    openHistorical(target);
    setHistoryNotice("Seleção visual destacada na análise aberta. Indicadores, classes e parâmetros continuam próprios de cada resultado; nenhum cálculo foi executado.");
  }
  function restoreHistorical(item: Historical) {
    if (item.invalidReason || !compatible(item)) return;
    restorePreparation(structuredClone(item.preparation));
    setActive(item.result.metadata.operation as Operation); setRequestText(item.request);
    scrollAnalysisTo("preparacao-conversacional");
    setHistoryNotice("Parâmetros e seleção restaurados; o servidor verificará novamente a preparação.");
  }
  // Os identificadores da seleção derivam do nome/código associados; sem eles, deixam de existir.
  function removeAssociation(role: Role) {
    setMapping(previous => ({...previous, [role]: ""}));
    setSelectedRoles(previous => previous.filter(item => item !== role));
    if (role === "territory" || role === "territory_id") {setTerritoryIds([]); setReferenceIds([]);}
  }
  /** Escolher a coluna estabelece o papel (D1). Só se desfazem as escolhas que dependem da coluna anterior. */
  function associateColumn(column: string, role: Role | "") {
    if (role === "count") setCountUnit("");
    if (role === "territory" || role === "territory_id") {
      setTerritoryIds([]); setReferenceIds([]); setReference("");
      setResolutions(previous => ({number_format: previous.number_format}));
    }
    const previouslyAssociated = (Object.entries(mapping).find(([, value]) => value === column) || [])[0] as Role | undefined;
    // Mover a coluna territorial para outro papel também remove a identidade da seleção.
    if (previouslyAssociated === "territory" || previouslyAssociated === "territory_id") {setTerritoryIds([]); setReferenceIds([]);}
    setMapping(previous => {
      const next = { ...previous };
      for (const key of ROLES) {
        if (next[key.key] === column || (role && key.key === role)) delete next[key.key];
      }
      if (role) next[role] = column;
      return next;
    });
    setSelectedRoles(previous => [...previous.filter(r => r !== previouslyAssociated && r !== role), ...(role ? [role] : [])]);
    if (role === "period") setSinglePeriod(false);

    setError("");
  }
  async function run(op: Operation, confirmedPlacement?: Placement) {
    if (!privacy.accepted || runningRef.current) return;
    setActive(op);  setError("");
    // Uma seleção múltipla esvaziada não autoriza usar todas as competências.
    // O mesmo bloqueio vale para o botão das opções avançadas.
    if (multiplePeriods && ["counts", "temporal", "report", "comparisons"].includes(op) && !selectedPeriods.length &&
        (inspection?.periods.length || 0) > 1) {
      setPeriodEditor(value => value + 1); scrollAnalysisTo("preparacao-conversacional"); return;
    }
    if (preflighting || !preflight) {
      setError("Aguarde a conclusão da verificação de compatibilidade da base.");
      return;
    }
    const capability = preflight.capabilities[op];
    if (!capability || capability.status !== "available") {
      setError(capability?.reasons.join(" ") || "Esta análise não está disponível para a base atual.");
      return;
    }
    if ((!file && !usingBrazil) || !inspection || inspection.requires_sheet || inspecting) {
      setUploadError(inspection?.requires_sheet
        ? "Selecione uma aba do arquivo Excel para concluir a importação."
        : inspecting ? "Aguarde a conclusão do exame do arquivo."
        : "A importação não foi concluída. Confira a mensagem na conversa antes de continuar.");
      scrollAnalysisTo("dados");
      return;
    }
    setUploadError("");
    const contextKey = requestKey(op);
    const chosenPlacement = confirmedPlacement || placement.current;
    const currentGroup = diagnostics.find(group => group.id === diagnosticId);
    const alreadyHere = currentGroup?.resultIds.some(id => history.some(item => item.result.result_id === id && item.contextKey === contextKey && !item.invalidReason));
    if (currentGroup?.resultIds.length && !chosenPlacement && !alreadyHere) {
      pendingRun.current = op; setConfirmNewAnalysis(true); return;
    }
    const destination = chosenPlacement === "independent" && currentGroup?.resultIds.length
      ? ++nextDiagnostic.current : diagnosticId;
    setDiagnosticId(destination);
    const reusable = history.find(item=>item.contextKey===contextKey && !item.invalidReason);
    if (reusable) {
      setDiagnostics(groups => attachResult(groups, destination, reusable.result.result_id));
      placement.current = null;
      setResultExpanded(true);
      setResult(reusable.result); setHistoryNotice("Resultado existente recuperado, sem recalcular.");
      scrollAnalysisTo("resultados");
      return;
    }
    const preparation = structuredClone(snapshotPreparation());
    const originRequest = requestText || "Análise de " + ANALYSIS_LABELS[op];
    runningRef.current = true; setRunning(true); scrollAnalysisTo("resultados");
    const currentRevision = revision.current;
    const form = new FormData();
    appendSource(form); form.append("operation", op);
    if (usingBrazil && spatialRequest(op)) form.append("geo_version", geoToken);
    form.append("mapping", JSON.stringify(mapping));
    form.append("options", JSON.stringify(semanticOptions()));
    try {
      const response = await fetch(API + "/api/analyze", { method: "POST", body: form });
      const body = await readApiResponse(response);
      if (currentRevision !== revision.current) return;
      const calculated = structuredClone(body as AnalysisResult);
      calculated.metadata = {...calculated.metadata, origin_request: originRequest};
      setHistory(previous=>[...previous, {result:calculated, request:originRequest, sourceKey,
        contextKey, preparation, invalidReason:""}]);
      setDiagnostics(groups => attachResult(groups, destination, calculated.result_id));
      placement.current = null;
      setResult(calculated); setResultExpanded(true); setHistoryNotice("");
      scrollAnalysisTo("resultados");
    } catch (exc) {
      if (currentRevision !== revision.current) return;
      setError(readableError(exc));
      scrollAnalysisTo("resultados");
    }
    finally { runningRef.current = false; setRunning(false); }
  }

  function startNewAnalysis(mode: Placement) {
    if (running || inspecting || preflighting) return;
    placement.current = mode;
    setConfirmNewAnalysis(false);
    if (pendingRun.current) {
      const operation = pendingRun.current; pendingRun.current = null;
      void run(operation, mode); return;
    }
    if (mode === "independent" && diagnostics.some(group => group.id === diagnosticId && group.resultIds.length))
      setDiagnosticId(++nextDiagnostic.current);
    setActive(null); if (mode === "independent") setResult(null); setVisualSelection([]);
    setRequestedCategory(""); setRequestedIndicator(null); setRequestText(""); setError("");
    setHistoryNotice("Nova análise iniciada. Resultados anteriores disponíveis no Histórico de análises.");
    setCatalogOpen(true); navigate("home", "analises");
  }
  function requestNewAnalysis() {
    pendingRun.current = null;
    if (result || active || diagnostics.some(group => group.id === diagnosticId && group.resultIds.length)) setConfirmNewAnalysis(true);
    else startNewAnalysis("independent");
  }
  function recordRequest(message: string) {
    setRequestText(message);
    const intent = presentationIntent(message);
    if (intent) placement.current = intent;
  }
  async function closeSession() {
    setClosingSession(true); setSessionError("");
    try { await endSession(); }
    catch (exc) { setSessionError(readableError(exc)); setClosingSession(false); }
  }
  /** Botões, comandos e atalhos usam o mesmo destino; territórios abrem dentro da preparação. */
  function openStage(target: NavigationTarget) {
    if (target === "territories") setTerritoriesOpen(true);
    const stage = target === "results" ? "results" : "preparation";
    setWorkspaceStage(stage); setPage(stage === "results" ? "results" : "home");
  }
  function navigate(view: "home" | "results", target?: string) {
    setPage(view);
    if (view === "results") { setResultExpanded(true); setWorkspaceStage("results"); }
    const fragment = target || (view === "results" ? "resultados" : "inicio");
    // A alteração nativa do hash também rolaria a página antes da navegação do painel.
    if (window.location.hash !== "#" + fragment) window.history.pushState(null, "", "#" + fragment);
    scrollAnalysisTo(view === "results" && result && !target ? "selected-result-content" : fragment);
  }
  useEffect(() => {
    const onHashChange = () => {
      const results = window.location.hash === "#resultados";
      setPage(results ? "results" : "home");
      if (results) setWorkspaceStage("results");
    };
    const onStage = (event: Event) => openStage((event as CustomEvent<NavigationTarget>).detail);
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("adt:stage", onStage);
    return () => { window.removeEventListener("hashchange", onHashChange); window.removeEventListener("adt:stage", onStage); };
  }, []);
  useEffect(() => {
    document.title = "Agente Diagnóstico Territorial";
    let alive = true;
    fetch(API + "/api/health")
      .then(async response => {
        await readApiResponse(response);
        if (alive) setServerStatus("online");
      })
      .catch(() => { if (alive) setServerStatus("offline"); });
    return () => { alive = false; };
  }, []);
  const officialScopeKey = officialScope ? JSON.stringify([active, effective?.abrangencia ?? null]) : "";
  const nearestOptions = (active === "nearest" || (active === "criteria" && criteriaDistance)) && referenceMode
    ? JSON.stringify([referenceMode, referenceIds, criterionOperator, criterionValue]) : "";
  const criteriaOptions = active === "criteria" ? JSON.stringify([criteriaTree, criteriaRanking, criteriaBands, distanceScope,
    eligibilityScope, criteriaComparison]) : "";
  // O servidor recalcula a matriz após qualquer escolha de coluna ou parâmetro.
  // Nenhuma habilitação é decidida apenas no navegador.
  useEffect(() => {
    revision.current += 1;

    if (!inspection || inspection.requires_sheet || (!file && !usingBrazil)) return;
    let cancelled = false;
    const controller = new AbortController();
    setPreflighting(true);
    setPreflightError("");
    const timer = window.setTimeout(async () => {
      const form = new FormData();
      appendSource(form);
      // Base oficial: a rota (municipal, nacional ou níveis) depende da análise e da abrangência que vale nela.
      if (officialScope) form.append("operation", active || "");
      form.append("mapping", JSON.stringify(mapping));
      form.append("options", JSON.stringify(semanticOptions()));
      try {
        const response = await fetch(API + "/api/preflight", { method: "POST", body: form, signal: controller.signal });
        const next = await readApiResponse(response) as Preflight;
        if (!cancelled) setPreflight(next);
      } catch (exc) {
        if (!cancelled) { setPreflight(null); setPreflightError(readableError(exc)); }
      } finally {
        if (!cancelled) setPreflighting(false);
      }
    }, 150);
    return () => { cancelled = true; controller.abort(); window.clearTimeout(timer); };
  }, [inspection, file, usingBrazil, sheet, mapping, selectedRoles, countUnit, customCountUnit, preflightAttempt,
      periodFilter, selectedPeriods, categoryFilter, objectDraft,
      singlePeriod, reference, crs, resolutions, quantiles, distributionIndicator, temporalIndicator, reportIndicator, hierarchyColumns, territoryIds, comparisonIndicator,
      nearestOptions, criteriaOptions, officialScopeKey]);

  useEffect(() => { revision.current += 1;  setError(""); }, [active]);

  // O separador decimal das coordenadas é verificado nos dados; só vira escolha quando o formato é misto.
  const separatorReason = (operation: Operation) =>
    !!preflight?.capabilities[operation]?.reasons.some(reason => /separador decimal|ponto decimal|formato decimal/.test(reason));
  const decimalPending = separatorReason("nearest") || (active === "criteria" && separatorReason("criteria")) ||
    (active === "spatial" && separatorReason("spatial")) || preflight?.coordinate_separator === null;
  const decimalChoice = !governedPremises.has("number_format") && (decimalPending || !!resolutions.number_format);
  const criteriaAll = [...criteriaLeaves(criteriaTree), ...criteriaLeaves(criteriaComparison?.criteria || null)];
  // Caixa "Indicador" dos critérios combinados: atributos numéricos das condições, da ordenação e das faixas.
  const criteriaAttributes = [...new Set([...criteriaAll.map(leaf => leaf.attribute), criteriaRanking?.attribute, criteriaBands?.attribute])]
    .filter(attribute => attribute === "densidade" || attribute === "quantidade" || attribute === "populacao" || attribute === "distancia")
    .map(attribute => ATTRIBUTE_LABELS[attribute!]);
  const criteriaReferencesByCriterion = criteriaDistance && referenceMode === "criterion";
  const criteriaNeeds = {spatial: criteriaDistance,
    count: criteriaAll.some(leaf => leaf.attribute === "densidade" || leaf.attribute === "quantidade") ||
      ["densidade", "quantidade"].includes(criteriaRanking?.attribute || "") || ["densidade", "quantidade"].includes(criteriaBands?.attribute || "") ||
      criteriaReferencesByCriterion,
    population: criteriaAll.some(leaf => leaf.attribute === "densidade" || leaf.attribute === "populacao") ||
      ["densidade", "populacao"].includes(criteriaRanking?.attribute || "") || ["densidade", "populacao"].includes(criteriaBands?.attribute || "") ||
      criteriaReferencesByCriterion};
  // Faixa observada no último resultado de critérios, por condição: só posiciona a régua, nunca escolhe o valor.
  const criteriaRanges = useMemo(() => {
    const ranges: Record<string, [number, number]> = {};
    const evaluations = (result?.metadata.criterios as {avaliacoes?: {nos: Record<string, {valor?: number}>}[]} | undefined)?.avaliacoes || [];
    for (const item of evaluations) for (const [node, detail] of Object.entries(item.nos)) {
      if (typeof detail.valor !== "number") continue;
      const range = ranges[node];
      ranges[node] = range ? [Math.min(range[0], detail.valor), Math.max(range[1], detail.valor)] : [detail.valor, detail.valor];
    }
    return ranges;
  }, [result]);
  const visibleRequirements = preparationRequirements(active ? preflight?.capabilities[active]?.requirements || [] : []);

  const sourceChoice = <div id="dados" className="mt-3 space-y-3">
    <div className="grid gap-2 sm:grid-cols-2">
      <button type="button" onClick={chooseBrazil} disabled={!privacy.accepted || inspecting}
        className={"flex items-center gap-3 rounded-xl border px-3 py-3 text-left text-sm transition hover:border-blue-400 disabled:opacity-40 " +
          (usingBrazil ? "border-blue-500 bg-blue-50" : "border-line bg-white")}>
        <Database size={20} className="shrink-0 text-teal"/>
        <span><strong className="block">Usar dados do Brasil</strong><small className="text-slate-500">Dados para diferentes recortes territoriais</small></span>
        {usingBrazil && <CheckCircle2 size={17} className="ml-auto text-emerald-600"/>}
      </button>
      <div className={"flex items-center gap-2 rounded-xl border px-3 py-3 " +
        (!usingBrazil && file ? "border-blue-500 bg-blue-50" : "border-line bg-white")}>
        <button type="button" onClick={() => inputRef.current?.click()} disabled={!privacy.accepted}
          className="flex min-w-0 flex-1 items-center gap-3 text-left text-sm disabled:opacity-40">
          <FileUp size={20} className="shrink-0 text-teal"/>
          <span><strong className="block">Importar seus dados</strong><small className="text-slate-500">CSV ou Excel</small></span>
        </button>
        <a href={API + "/api/modelo/estrutura-recomendada"} download="modelo_territorial_recomendado.xlsx"
          title="Baixar estrutura recomendada (.xlsx)" aria-label="Baixar estrutura recomendada"
          className="rounded-md p-1 text-teal hover:bg-blue-50"><Download size={17}/></a>
      </div>
    </div>
    {inspecting && <p role="status" className="text-xs text-slate-500">Preparando seus dados...</p>}
    {uploadError && <p role="alert" className="text-xs text-rose-800">{uploadError}</p>}
    {usingBrazil && inspection?.catalog && <details className="text-[11px] leading-5 text-slate-500"
      onToggle={e => { if (e.currentTarget.open) void fetch(API + "/api/brazil/source").then(readApiResponse).then(setSourceDiagnostic).catch(() => setSourceDiagnostic(null)); }}>
      <summary className="cursor-pointer">Diagnóstico técnico da fonte</summary>
      <p>Origem: {inspection.catalog.modo === "repositorio" ? "arquivos versionados no repositório" : "pasta externa configurada"} ·
        versão {inspection.catalog.versao.slice(0, 12)} · integridade {inspection.catalog.integridade}
        {inspection.catalog.versao_fixada ? " · versão fixada explicitamente" : ""}
        {inspection.catalog.complemento_geografico && " · camada geográfica complementar: " + inspection.catalog.complemento_geografico.estado +
          (inspection.catalog.complemento_geografico.versao ? " (versão " + inspection.catalog.complemento_geografico.versao + ")" : "")}</p>
      {sourceDiagnostic && <pre tabIndex={0} aria-label="Origem física e identidade da base" className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(sourceDiagnostic, null, 2)}</pre>}
    </details>}
    {inspection?.requires_sheet && <label className="text-xs text-slate-700">Qual aba deseja utilizar?
      <select className="ml-2 rounded-lg border border-line px-2 py-1" value={sheet}
        onChange={e=>{const next=e.target.value;setSheet(next);if(file&&next)void inspectFile(file,next);}}>
        <option value="">Selecione uma aba</option>
        {inspection.sheets.map(name=><option key={name} value={name}>{name}</option>)}
      </select>
    </label>}
  </div>;

  // Base oficial: a lista vem da inspeção (fonte municipal inteira), nunca do pré-exame de uma rota nacional.
  const territoryItems = officialScope ? inspection?.preflight?.territory_choices || [] : municipalScope ? preflight?.territory_choices || [] : [];
  const territoryNames = new Map(territoryItems.map(item => [item.id, item.name ? item.name + (item.state ? " (" + item.state + ")" : "") : item.label]));
  // Valor da caixa "Abrangência territorial": Brasil, estados e municípios que valem nesta análise, ou o padrão dela.
  const scopeSummary = describeScope(effective || municipalOnly(territoryIds), levels, id => territoryNames.get(id) || id);
  // Escolha pendente na abrangência (mistura de níveis ou mínimo de territórios), informada pelo pré-exame.
  const activeLevels = active ? preflight?.capabilities[active]?.niveis : undefined;
  const territoryPending = officialScope && !preflighting ? activeLevels?.selecao?.status === "needs_confirmation"
    ? activeLevels.selecao.reasons[0] || "" : preflight?.abrangencia_pendente || "" : "";
  const selectionTitle = active === "nearest" ? "Municípios-alvo" : active === "criteria" ? "Universo dos critérios" : "Abrangência territorial";
  // Seleção territorial. Na base oficial, a lista vertical da caixa "Abrangência territorial" (Brasil, estados e municípios);
  // nas bases importadas (e nas referências), a seleção de territórios por pesquisa.
  const selectionContent = inspection && (municipalScope || configurationPanel) ? <>
    {officialScope ? <TerritorialScopeSelector levels={levels!} rule={levelRule} items={territoryItems} scope={territoryScope}
      ids={territoryIds} effective={effective} summary={scopeSummary} title={selectionTitle} pending={territoryPending}
      onChange={next => replaceSelection(next.scope, next.ids)} onClear={() => replaceSelection(EMPTY_SCOPE, [])}
      disabled={running || inspecting} loading={inspecting}/>
    : <TerritorialSelection items={territoryItems} selected={territoryIds} onChange={changeTerritories}
      disabled={running || inspecting} reason={preflight?.selection_reason} embedded={configurationPanel}
      {...(active === "nearest" ? {title: "Municípios-alvo",
        description: "Para cada município-alvo, será indicada a referência mais próxima. Sem seleção, todos os municípios do período são alvos."}
        : active === "criteria" ? {title: "Universo dos critérios",
        description: "Os critérios são avaliados para cada território selecionado. Sem seleção, todos os territórios do período. A seleção não reduz o conjunto de referências."}
        : configurationPanel ? {title: "Municípios",
          description: "Pesquise por nome ou código e marque os municípios. Sem seleção, a análise considera todos os municípios do recorte."} : {})}/>}
    {selectionProposal && <div role="alert" className="no-print my-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs">
      <p>O pedido usará {selectionProposal.territory_ids?.length} territórios em lugar da seleção atual.</p>
      <button type="button" onClick={()=>applyExploration(selectionProposal)} className="mr-2 mt-2 rounded-lg border bg-white px-3 py-2">Usar o recorte mencionado</button>
      <button type="button" onClick={()=>setSelectionProposal(null)} className="mt-2 rounded-lg border bg-white px-3 py-2">Manter seleção atual</button>
    </div>}
    {municipalScope && !!territoryIds.length && <div aria-label="Explorar seleção" className="no-print mb-3 flex flex-wrap gap-2">
      {([ ["comparisons", "Comparar selecionados"], ["temporal", "Examinar evolução temporal"], ["aggregate", "Agregar municípios"] ] as const)
        .filter(([operation])=>!!preflight && (preflight.capabilities[operation].status!=="unavailable" ||
          operation==="temporal" && preflight.values.periods.length>=2 && !!mapping.count))
        .map(([operation,label])=><button key={operation} type="button" disabled={running || inspecting || preflighting}
          onClick={()=>exploreSelection(operation)} className="rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-semibold text-teal disabled:opacity-40">{label}</button>)}
    </div>}
  </> : null;
  // Resumo de uma linha da seleção, mostrado no bloco de territórios da preparação das demais bases. No recorte nacional
  // o bloco só informa que há um único território, para que o comando "territórios" tenha destino. Na base oficial,
  // a caixa "Abrangência territorial" das configurações substitui o bloco.
  const territorySummary = configurationPanel ? undefined : selectionContent ? (() => {
    const shown = territoryIds.slice(0, 3).map(id => territoryNames.get(id) || id);
    const more = territoryIds.length - shown.length;
    return {label: active === "nearest" ? "Municípios-alvo" : active === "criteria" ? "Universo dos critérios" : "Territórios",
      selected: territoryIds.length > 0, selectable: true,
      text: territoryIds.length ? territoryIds.length + (territoryIds.length === 1 ? " selecionado: " : " selecionados: ") +
        shown.join(", ") + (more > 0 ? " e mais " + more : "")
        : active === "nearest" ? "todos os municípios do período (nenhuma seleção)"
        : active === "criteria" ? "todos os territórios do período (nenhuma seleção)" : "todos os territórios do recorte (nenhuma seleção)"};
  })() : usingBrazil && inspection?.source?.scope === "national" ? {label: "Territórios", selected: false, selectable: false,
    text: "Brasil (total nacional). A fonte nacional tem um único território; a escolha de municípios vale para a abrangência Municípios."}
    : undefined;

  // Competências oferecidas: com o Brasil e outros níveis, a união das fontes; nos demais casos, as do pré-exame.
  const scopePeriods = officialScope && effective?.abrangencia.brasil
    ? periodsForScope(effective, levels!.brasil.periodos, inspection?.periods || [])
    : preflight?.values.periods?.length ? preflight.values.periods : inspection?.periods || [];
  const advancedPreparation = (<>
      {active && <div className="preparation-workspace section-anchor mt-5">
        <PreparationPanel title={selectedFeature?.title || "Preparar uma análise"} step={step} onStep={setStep}
          checking={preflighting || inspecting} requirements={visibleRequirements}
          ready={!!active && !preflighting && !inspecting && preflight?.capabilities[active]?.status === "available"}
          notice="">
          {!active ? <p className="text-sm text-slate-600">Escolha uma análise na lista para iniciar a preparação.</p> :
          !inspection || inspection.requires_sheet ? <div className="space-y-3 text-sm text-slate-600">
            <p>{inspecting ? "Conferindo a base selecionada…" : "Carregue os dados do Brasil ou importe um arquivo na área de dados. Se o Excel possuir várias abas, escolha a aba nessa área."}</p>
            {uploadError && <p role="alert">{uploadError}</p>}
          </div> : <>
            {preflightError && <div role="alert" className="mb-3 text-sm text-rose-800">{preflightError}
              <button type="button" className="ml-2 font-bold underline" onClick={() => setPreflightAttempt(n => n + 1)}>Verificar novamente</button>
            </div>}
            {error && <p role="alert" className="mb-3 text-sm text-rose-800">{error}</p>}
            {step === 0 && <>
              <p className="text-xs text-slate-600">{usingBrazil ? "Dados do Brasil" : file?.name} · {shortNum(inspection.row_count)} registros. Os campos reconhecidos já vêm escolhidos; ajuste qualquer coluna pelos seletores.</p>
          <ContextConfig spatial={active === "spatial"} columns={inspection.columns} mapping={mapping}
            periodSources={inspection.derived_fields?.find(field => field.role === "period" && field.column === mapping.period)?.source_columns}
            fieldStates={preflight?.field_states} suggestions={inspection.suggested_columns}
            categories={preflight?.values.categories || inspection.categories}
            suggestedCategory={inspection.suggested_category_constant} objectDraft={objectDraft} objectState={preflight?.object}
            territoryCode={mapping.territory_id || ""}
            singlePeriod={singlePeriod} onSinglePeriod={setSinglePeriod}
            detectedLevels={preflight?.territorial_hierarchy?.levels || inspection.preflight?.territorial_hierarchy?.levels}
            selectedLevels={hierarchyColumns}
            onSelectLevel={(level, column) => setHierarchyColumns(previous => ({...previous, [level]: column}))}
            onSelectCode={column => {
              if(column) associateColumn(column, "territory_id");
              else removeAssociation("territory_id");
            }}
            onSelect={(role, column) => {
              if (column) associateColumn(column, role);
              else removeAssociation(role);
            }}
            onDraft={setObjectDraft}
          />
            </>}
            {step === 1 && <>
        {active && inspection && !inspection.requires_sheet && <div className="mb-4 rounded-2xl border border-line bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-bold text-ink">Parâmetros da análise</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <SelectField label="Filtrar por período" value={periodFilter}
              options={preflight?.values.periods || inspection.periods}
              onChange={v => {setPeriodFilter(v);setSelectedPeriods([]);setMultiplePeriods(false); }}/>
            <SelectField label="Filtrar por categoria" value={categoryFilter}
              options={preflight?.values.categories || inspection.categories}
              onChange={v => {setCategoryFilter(v); }}/>
            {(active === "temporal" || active === "report") && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
              {active === "temporal" ? "Indicador da evolução temporal" : "Indicador do relatório"}
              <select aria-label={active === "temporal" ? "Indicador da evolução temporal" : "Indicador do relatório"}
                className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={active === "temporal" ? temporalIndicator : reportIndicator}
                onChange={e => { (active === "temporal" ? setTemporalIndicator : setReportIndicator)(e.target.value as "" | "density" | "quantity");  }}>
                <option value="">Selecione o indicador</option>
                <option value="quantity">Quantidade na unidade declarada</option>
                <option value="density">Densidade por 1.000 habitantes</option>
              </select>
            </label>}
            {active === "distribution" && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
              Agrupamento da distribuição
              <select aria-label="Agrupamento da distribuição" value={quantiles} onChange={event=>setQuantiles(Number(event.target.value))}
                className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink">
                <option value={4}>Quartis (4 grupos)</option>
                <option value={5}>Quintis (5 grupos)</option>
                <option value={10}>Decis (10 grupos)</option>
              </select>
            </label>}
            {active === "distribution" && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
              Indicador da distribuição
              <select aria-label="Indicador da distribuição" className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={distributionIndicator} onChange={e => {setDistributionIndicator(e.target.value as "" | "density" | "quantity");}}>
                <option value="">Selecione o indicador</option>
                <option value="density">Densidade por 1.000 habitantes</option>
                <option value="quantity">Quantidade na unidade declarada</option>
              </select>
            </label>}
          </div>
        </div>}

            <DataResolution operation={active} columns={inspection.columns}
            mapping={mapping} diagnostic={preflight?.multiplicity} options={resolutions} setOptions={setResolutions}
            periods={preflight?.values.periods?.length ? preflight.values.periods : inspection.periods}
            selectIdentity={column => {if(column) associateColumn(column, "identity"); else removeAssociation("identity");}}
            applied={governedPremises} separatorChoice={decimalChoice}/>
            <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50/40 p-4 sm:p-5">
              <h4 className="text-sm font-bold text-ink">Completar informações para esta análise</h4>
              <p className="mt-1 text-xs leading-5 text-slate-600">Preencha somente os dados que correspondem à estrutura real da sua base. Uma escolha não substitui informações ausentes.</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {active !== "spatial" && active !== "rotation" && (active !== "nearest" || referenceMode === "criterion") &&
                  (active !== "criteria" || criteriaNeeds.count) && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Onde estão os quantitativos dos profissionais?
                    <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.count || ""} onChange={e => {
                        if (e.target.value) associateColumn(e.target.value, "count");
                        else removeAssociation("count");
                      }}>
                      <option value="">Escolher coluna</option>
                      {fieldOptions(inspection.columns, inspection.suggested_columns, "count", {current: mapping.count || ""})
                        .map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    O que o quantitativo representa?
                    <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      aria-label="O que o quantitativo representa?" value={countUnit} onChange={e => {setCountUnit(e.target.value);}}>
                      <option value="">Selecione a unidade de contagem</option>
                      <option value="pessoas">Pessoas distintas no recorte declarado</option>
                      <option value="vinculos">Vínculos de trabalho</option>
                      <option value="postos">Postos de trabalho</option>
                      <option value="outro">Outra unidade</option>
                    </select>
                  </label>
                  {countUnit === "outro" && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Especifique a unidade de contagem
                    <input className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={customCountUnit} onChange={e => setCustomCountUnit(e.target.value)}/>
                  </label>}
                </>}
                {(["density","comparisons","ranking","aggregate"].includes(active) || (active === "distribution" && distributionIndicator === "density") || (active === "temporal" && temporalIndicator === "density") || (active === "report" && reportIndicator === "density") || (active === "nearest" && referenceMode === "criterion") || (active === "criteria" && criteriaNeeds.population)) && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Coluna com a população correspondente
                    <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.population || ""} onChange={e => {
                        if (e.target.value) associateColumn(e.target.value, "population");
                        else removeAssociation("population");
                      }}>
                      <option value="">Escolher coluna</option>
                      {fieldOptions(inspection.columns, inspection.suggested_columns, "population", {current: mapping.population || ""})
                        .map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </select>
                  </label>
                </>}
                {active === "rotation" && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Coluna de identificação individual
                    <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.identity || ""} onChange={e => {if(e.target.value)associateColumn(e.target.value,"identity");else removeAssociation("identity");}}>
                      <option value="">Escolher coluna</option>
                      {fieldOptions(inspection.columns, inspection.suggested_columns, "identity", {current: mapping.identity || ""})
                        .map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </select>
                  </label>
                </>}
                {(active === "spatial" || active === "nearest" || (active === "criteria" && criteriaDistance)) && <>
                  {(["latitude","longitude"] as Role[]).map(role => <label key={role} className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    {role === "latitude" ? "Latitude" : "Longitude"}
                    <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping[role] || ""} onChange={e => {if(e.target.value) associateColumn(e.target.value,role); else removeAssociation(role);}}>
                      <option value="">Escolher coluna</option>
                      {fieldOptions(inspection.columns, inspection.suggested_columns, role, {current: mapping[role] || ""})
                        .map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </select>
                  </label>)}
                  {!governedPremises.has("crs") && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Referencial geodésico informado para a base
                    <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={crs} onChange={e=>setCrs(e.target.value)}>
                      <option value="">Não informado</option><option value="SIRGAS2000">SIRGAS2000</option>
                    </select>
                  </label>}
                  {active === "spatial" && <SelectField label="Território de referência" value={reference}
                    options={preflight?.values.territories || []} onChange={setReference}/>}
                </>}
              </div>
            </div>

            </>}
            {step === 2 && <>
              <div className="rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                <h3 className="font-bold text-ink">Resumo da configuração</h3>
                {(["temporal", "report", "distribution"].includes(active)) && <p>Indicador: {
                  (active === "temporal" ? temporalIndicator : active === "report" ? reportIndicator : distributionIndicator) === "density"
                    ? "Densidade por 1.000 habitantes" : (active === "temporal" ? temporalIndicator : active === "report" ? reportIndicator : distributionIndicator) === "quantity"
                    ? "Quantidade na unidade declarada" : "Aguardando escolha"}</p>}
                <p>Base: {usingBrazil ? "Dados do Brasil — " + (officialScope ? scopeSummary : inspection.source?.scope === "national" ? "Brasil" : "Municípios") : file?.name}</p>
                {inspection.curated_defaults && <p>Campos do perfil oficial: {governedRoles(inspection.curated_defaults, mapping).length} de {
                  Object.keys(inspection.curated_defaults.mapping).length} (os demais seguem a sua escolha)</p>}
                <p>Território: {mapping.territory || "Não associado"}{mapping.territory_id ? " · Identificador: " + mapping.territory_id : ""}</p>
                <p>Período: {periodFilter || selectedPeriods.map(displayPeriod).join(", ") || (multiplePeriods ? "Nenhum período selecionado" : "Todos os períodos da base")} · Categoria: {categoryFilter || (!mapping.category && objectDraft.trim()) || "Categorias da base"}</p>
                <p>Unidade: {countUnit === "outro" ? customCountUnit : countUnit || (mapping.identity && !mapping.count ? "Pessoas distintas (pelo identificador)" : "Conforme a análise")}</p>
                {active === "criteria" && <p className="break-words">Critérios: {describeCriteria(criteriaTree, countUnit) || "nenhum (somente ordenação)"}
                  {criteriaRanking && " · Ordenação: " + criteriaRanking.attribute + " " + (criteriaRanking.direction === "desc" ? "decrescente" :
                    criteriaRanking.direction === "asc" ? "crescente" : "(direção a escolher)") + (criteriaRanking.top_n ? " · " + criteriaRanking.top_n + " primeiros" : "")}
                  {criteriaComparison && " · Comparação com o " + criteriaComparison.label}</p>}
                {(active === "nearest" || (active === "criteria" && criteriaDistance)) && <p>Referências: {referenceMode === "list" ? "lista explícita com " + referenceIds.length + " municípios" :
                  referenceMode === "criterion" ? "densidade por 1.000 habitantes " + (criterionOperator || "?") + " " + (criterionValue || "?") :
                  "aguardando definição"} · Referencial: {governedPremises.has("crs") ? GOVERNED_CRS : crs || "não informado"}</p>}
              </div>
              <RequirementChecklist analysis={selectedFeature?.title || "esta análise"}
                status={preflightError ? "unavailable" : !preflight || preflighting || inspecting ? "loading" : preflight.capabilities[active]?.status || "unavailable"}
                requirements={visibleRequirements.filter(item => item.status === "met")}
                onExecute={() => { void run(active); }} executing={running}/>
            </>}
          </>}
        </PreparationPanel>
      </div>}
  </>);
  const inlinePreparation = active && inspection && !inspection.requires_sheet ?
    <div id="preparacao-conversacional"><ConversationalPreparation
      operation={active}
      sourceBrazil={usingBrazil}
      curated={configurationPanel}
      quantiles={quantiles}
      onQuantiles={setQuantiles}
      selectedPeriods={selectedPeriods}
      multiplePeriods={multiplePeriods}
      periodEditor={periodEditor}
      onSelectedPeriods={values=>{setMultiplePeriods(true);setSelectedPeriods(values);setPeriodFilter("");}}
      scope={inspection.source?.scope || "municipal"}
      onScope={v=>{if(v!==inspection.source?.scope)void inspectFile(null,"",v,active);}}
      territoryPending={!!territoryPending}
      territoriesOpen={territoriesOpen}
      onTerritoriesOpen={setTerritoriesOpen}
      territorySelection={selectionContent}
      territorySummary={scopeSummary}
      rotationPeriods={{initial: resolutions.initial_period || "", final: resolutions.final_period || ""}}
      onRotationPeriod={(which, value) => setResolutions(previous => ({...previous, [which === "initial" ? "initial_period" : "final_period"]: value}))}
      criteriaAttributes={criteriaAttributes}
      columns={inspection.columns}
      mapping={mapping}
      suggestions={inspection.suggested_columns}
      onField={(role:FieldRole,column)=>{
        if(column)associateColumn(column,role as Role);
        else removeAssociation(role as Role);
      }}
      singlePeriod={singlePeriod}
      onSinglePeriod={setSinglePeriod}
      objectState={preflight?.object}
      objectDraft={objectDraft}
      onObjectDraft={setObjectDraft}
      suggestedObject={inspection.suggested_category_constant}
      countUnit={countUnit}
      onCountUnit={setCountUnit}
      customCountUnit={customCountUnit}
      onCustomCountUnit={setCustomCountUnit}
      indicator={active==="comparisons"?comparisonIndicator:active==="distribution"?distributionIndicator:active==="temporal"?temporalIndicator:reportIndicator}
      onIndicator={v=>{
        if(active==="comparisons" && v)setComparisonIndicator(v);
        if(active==="distribution")setDistributionIndicator(v);
        if(active==="temporal")setTemporalIndicator(v);
        if(active==="report")setReportIndicator(v);
      }}
      periodFilter={periodFilter}
      valuesPeriod={comparisonPeriod()}
      onValuesPeriod={setComparisonValuesPeriod}
      periods={scopePeriods}
      onPeriod={v=>{setMultiplePeriods(false);setPeriodFilter(v);setSelectedPeriods([]);}}
      categoryFilter={categoryFilter}
      requestedCategory={requestedCategory}
      categories={preflight?.values.categories?.length ? preflight.values.categories : inspection.categories}
      onCategory={setCategoryFilter}
      reference={reference}
      territories={preflight?.values.territories || inspection.territories}
      onReference={setReference}
      crs={crs}
      onCrs={setCrs}
      governedCrs={governedPremises.has("crs")}
      preparing={preflighting || inspecting}
      capability={preflight?.capabilities[active]}
      onExecute={()=>{void run(active);}}
      executing={running}
      extra={<div className="space-y-2 text-xs leading-5">
        {active === "criteria" && <CriteriaBuilder tree={criteriaTree} onTree={tree=>{setCriteriaTree(tree);setCriteriaComparison(null);}}
          ranking={criteriaRanking} onRanking={setCriteriaRanking} bands={criteriaBands} onBands={setCriteriaBands}
          distanceScope={distanceScope} onDistanceScope={setDistanceScope} eligibilityScope={eligibilityScope} onEligibilityScope={setEligibilityScope}
          period={periodFilter} category={categoryFilter || (!mapping.category ? objectDraft.trim() : "")} countUnit={countUnit === "outro" ? customCountUnit : countUnit}
          categories={preflight?.values.categories?.length ? preflight.values.categories : inspection.categories}
          universe={territoryIds.length ? territoryIds.length + " territórios selecionados" : "todos os territórios do período"}
          selectionIds={territoryIds} ranges={criteriaRanges} disabled={running || inspecting}
          references={<ReferenceSetup mode={referenceMode} onMode={setReferenceMode}
            items={preflight?.territory_choices || []} reason={preflight?.selection_reason}
            referenceIds={referenceIds} onReferenceIds={setReferenceIds}
            operator={criterionOperator} onOperator={setCriterionOperator} value={criterionValue} onValue={setCriterionValue}
            showDecimal={decimalChoice} numberFormat={resolutions.number_format}
            onNumberFormat={value=>setResolutions(previous=>({...previous, number_format: value || undefined}))}
            disabled={running || inspecting}/>}/>}
        {active === "criteria" && criteriaTree && !complete(criteriaTree) && <p role="status" className="text-amber-900">
          Complete o operador e o valor de cada condição.</p>}
        {active === "nearest" && <ReferenceSetup mode={referenceMode} onMode={setReferenceMode}
          items={preflight?.territory_choices || []} reason={preflight?.selection_reason}
          referenceIds={referenceIds} onReferenceIds={setReferenceIds}
          operator={criterionOperator} onOperator={setCriterionOperator} value={criterionValue} onValue={setCriterionValue}
          showDecimal={decimalChoice} numberFormat={resolutions.number_format}
          onNumberFormat={value=>setResolutions(previous=>({...previous, number_format: value || undefined}))}
          disabled={running || inspecting}/>}
        {active === "rotation" && <>
          {/* Na base oficial, os períodos da coorte ficam na caixa "Período" das configurações. */}
          {!configurationPanel && <>
          <label className="flex items-center gap-2">Período inicial
            <select aria-label="Período inicial" value={resolutions.initial_period || ""}
              onChange={e=>setResolutions(p=>({...p,initial_period:e.target.value}))}
              className="min-w-0 rounded-md border border-blue-200 bg-white px-1 py-0.5">
              <option value="">Escolher</option>{(preflight?.values.periods || inspection.periods).map(v=><option key={v}>{v}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2">Período final
            <select aria-label="Período final" value={resolutions.final_period || ""}
              onChange={e=>setResolutions(p=>({...p,final_period:e.target.value}))}
              className="min-w-0 rounded-md border border-blue-200 bg-white px-1 py-0.5">
              <option value="">Escolher</option>{(preflight?.values.periods || inspection.periods).map(v=><option key={v}>{v}</option>)}
            </select>
          </label>
          </>}
        </>}
      </div>}
      referenceMode={referenceMode}
      criteriaNeeds={criteriaNeeds}
      advanced={<>
        {!usingBrazil && mapping.latitude && mapping.longitude && !spatialRequest(active) && <fieldset className="mb-4 rounded-lg border border-line p-3 text-xs">
          <legend>Localização dos dados importados</legend>
          <p className="mb-2 text-slate-600">Use as informações da origem do arquivo. A configuração não é necessária para cálculos sem distância.</p>
          <label className="mr-3 inline-flex flex-col gap-1">Referencial das coordenadas importadas
            <select aria-label="Referencial das coordenadas importadas" value={crs} onChange={event => setCrs(event.target.value)} className="rounded border p-2">
              <option value="">Não informado na origem</option><option value="SIRGAS2000">SIRGAS2000</option></select>
          </label>
          {decimalChoice ? <label className="inline-flex flex-col gap-1">Separador decimal das coordenadas importadas
            <select aria-label="Separador decimal das coordenadas importadas" value={resolutions.number_format || ""}
              onChange={event => setResolutions(previous => ({...previous, number_format: event.target.value || undefined}))} className="rounded border p-2">
              <option value="">Escolher</option><option value="decimal_comma">Vírgula</option><option value="decimal_point">Ponto</option></select>
          </label> : preflight?.coordinate_separator ? <p data-testid="verified-number-format" className="mt-2 text-slate-600">
            Separador decimal das coordenadas: {preflight.coordinate_separator === "decimal_comma" ? "vírgula" : "ponto"}, verificado nos dados.</p> : null}
        </fieldset>}
        {advancedPreparation}
      </>}
    /></div> : null;
  const currentDiagnostic = diagnostics.find(group => group.id === diagnosticId);
  const investigationContent = currentDiagnostic?.resultIds.length ? (
    <InvestigationOverview title={diagnosticLabel(currentDiagnostic)} items={currentDiagnostic.resultIds.map(id => history.find(item => item.result.result_id === id)!).filter(Boolean)} currentId={result?.result_id || null} selected={visualSelection}
      busy={running || inspecting || preflighting} onTransfer={transferVisualSelection}
      onOpen={id => { const item = history.find(entry => entry.result.result_id === id); if (item) openHistorical(item); }}
      onPrepare={() => startNewAnalysis("append")}/>) : null;
  const historyContent = (
<PreviousAnalyses items={history.flatMap(item => diagnostics.filter(group => group.resultIds.includes(item.result.result_id)).map(group => ({
          id: group.id + ":" + item.result.result_id,
          resultId: item.result.result_id,
          title: item.result.title,
          request: item.request,
          periods: (item.result.metadata.periods as string[] | undefined) || [],
          availableForReuse: compatible(item),
          context: diagnosticLabel(group) + " · " + resultSummary(item).scope + " · " + resultSummary(item).status,
        })))} currentId={result && workspaceStage === "results" ? diagnosticId + ":" + result.result_id : null} disabled={running || inspecting || preflighting}
          onOpen={id => {
            const group = diagnostics.find(group => group.resultIds.some(resultId => id === group.id + ":" + resultId));
            const item = group && history.find(entry => id === group.id + ":" + entry.result.result_id);
            if (item && group) { openHistorical(item); setDiagnosticId(group.id); }
          }}/>
  );
  const workspaceEngaged = conversationStarted || !!inspection || usingBrazil || !!file || !!active || history.length > 0;
  const resultContent = (result || running || error) ? (<>
      <section id="resultados" ref={resultsRef} className="section-anchor mt-4 pt-3">
        <button type="button" onClick={() => scrollAnalysisTo("preparacao-conversacional")}
          className="no-print mb-5 inline-flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-xs font-semibold text-teal hover:bg-blue-50">
          <ArrowRight size={15} className="rotate-180"/> Voltar às opções
        </button>
        <div className="agent-guidance"><BrandAvatar size={42}/><div><h2 className="font-bold">{currentDiagnostic ? diagnosticLabel(currentDiagnostic) : "Resultado da análise"}</h2><p>{running ? "Acompanhe a execução pelo motor determinístico." : result ? "O motor determinístico produziu este resultado. Explore gráficos, mapas e tabelas ou pergunte sobre o que está em exibição." : "Confira a orientação abaixo antes de continuar a análise."}</p></div></div>
        {result && <button type="button" aria-expanded={resultExpanded} aria-controls="selected-result-content"
          className="no-print mb-3 rounded-lg border border-line bg-white px-3 py-2 text-xs font-semibold text-teal"
          onClick={() => setResultExpanded(value => !value)}>{resultExpanded ? "Recolher análise" : "Expandir análise"}</button>}
        <div className="rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7 print-content">
          <div className="no-print flex flex-wrap items-start justify-between gap-4 border-b border-line pb-6">
            <div className="flex items-start gap-3">
              <span className="rounded-xl bg-teal-50 p-2.5 text-teal">{resultFeature ? <resultFeature.icon size={22}/> : <ClipboardList size={22}/>}</span>
              <div><h3 className="font-bold text-ink">{resultFeature?.title || "Selecione uma análise"}</h3><p className="mt-1 text-xs text-slate-500">{resultFeature?.detail || "Os resultados aparecerão aqui após a execução."}</p></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button disabled={!result || resultStatus==="INVALIDADO"} data-testid="export-results-csv" onClick={() => result && exportCsv(result.rows)} className="flex items-center gap-1.5 rounded-xl border-2 border-[#24577d] bg-[#102740] px-3 py-2 text-xs font-bold text-white hover:bg-[#1d4d71] disabled:opacity-40"><ArrowDownToLine size={14}/> {resultOperation === "distribution" ? "Resumo CSV" : "CSV"}</button>

              <button disabled={!result} data-testid="print-results-pdf" onClick={() => window.print()} className="flex items-center gap-1.5 rounded-xl border-2 border-[#24577d] bg-white px-3 py-2 text-xs font-bold text-[#102740] hover:bg-blue-50 disabled:opacity-40"><FileSpreadsheet size={14}/> Imprimir / PDF</button>
            </div>
          </div>
          <p className="no-print mt-3 rounded-lg border border-[#b4c9db] bg-[#f1f6fa] px-3 py-2 text-xs leading-5 text-[#173d5c]"><strong>Guarde seus resultados:</strong> o CSV exporta a tabela principal desta análise; tabelas de detalhe têm exportação própria. Imprimir / PDF inclui a visualização e a página da tabela em exibição. Para conservar um diagnóstico, exporte cada componente pelo Histórico. A sessão é temporária.</p>
           <details data-testid="advanced-technical-export" className="no-print mt-2 text-xs text-slate-500"><summary className="cursor-pointer">Opções técnicas avançadas</summary><div className="mt-2">              <button disabled={!result} onClick={() => result && downloadText("metodo_diagnostico.json", JSON.stringify({title: result.title, notes: result.notes, ...result.metadata,
                 result_id:result.result_id, organizacao_na_sessao: diagnostics.filter(group => group.resultIds.includes(result.result_id)).map(group => ({diagnostico: diagnosticLabel(group), componentes: group.resultIds})), validity: historical?.invalidReason ? "INVALIDADO" : "VALIDO", currency:resultStatus,
                invalidation_reason:historical?.invalidReason || "",
                representacao_aplicada: representationRecord.current?.resultado === result.result_id ? representationRecord.current : null}, null, 2), "application/json")} className="rounded-xl border px-3 py-2 text-xs disabled:opacity-40">Baixar registro técnico (JSON)</button></div></details>
           <div id="filtros-resultados" className="no-print mt-4">
            <button type="button" className="font-bold text-teal underline" onClick={() => scrollAnalysisTo("preparacao-conversacional")}>Alterar a preparação</button>
          </div>
          {error && <div role="alert" className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><XCircle size={18} className="shrink-0"/>{error}</div>}
          {running && <div role="status" className="flex flex-col items-center justify-center gap-3 py-16 text-center text-sm text-teal">
            <LoaderCircle size={28} className="animate-spin"/>
            <strong>Preparando seu diagnóstico</strong>
            <p className="max-w-sm text-xs leading-5 text-slate-600">
              A análise está em andamento. Os resultados aparecerão aqui quando estiverem prontos.
            </p>
          </div>}
          {result && <InvestigationViewState.Provider key={result.result_id} value={viewMemory.current[result.result_id] ||= {}}>
            <div id="selected-result-content" hidden={!resultExpanded} className="pt-6">
            <h3 data-testid="result-title" className="text-xl font-bold text-ink">{result.title}</h3>
            <p data-testid="result-status" className={resultOperation === "distribution" && resultStatus === "VIGENTE" ? "sr-only" : "mt-2 text-xs font-semibold text-slate-600"}>
              {resultOperation === "distribution" && resultStatus === "VIGENTE" ? "Resultado disponível" :
                resultStatus === "INVALIDADO" ? "Resultado invalidado: " + historical?.invalidReason :
                resultStatus === "VIGENTE" ? "Resultado válido e vigente no contexto atual" :
                resultOperation === "distribution" ? "Resultado de uma análise anterior. O resultado original permanece disponível." :
                "Resultado histórico válido · não vigente no contexto atual"}
            </p>
            {historical && <ResultIdentity entry={historical}/>}
            {result.conversation_reference?.available === false && <p role="status" className="my-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
              Resultado disponível para consulta e exportação nesta aba. O limite de memória das referências conversacionais foi atingido; a conversa não pode ler este resultado por referência.
            </p>}
            {result.total_rows === 0 && <p role="status" className="my-3 text-sm text-slate-600">Esta análise não produziu linhas de resultado. Consulte o recorte e as limitações antes de preparar outra execução.</p>}
            {historical && <div className="no-print my-3 text-xs text-slate-600">
              <p className="break-words">Solicitação: {historical.request}</p>
              <button type="button" disabled={!!historical.invalidReason || !compatible(historical) || inspecting || running}
                onClick={()=>restoreHistorical(historical)} className="mt-2 text-teal underline disabled:opacity-40">Retomar parâmetros deste resultado</button>
              {!compatible(historical) && <p className="mt-2">A fonte, a versão ou a camada geográfica atual difere da utilizada neste resultado. O conteúdo histórico permanece consultável.</p>}
            </div>}
            {resultOperation === "nearest" && !!nearestMembers.length && historical && compatible(historical) && !historical.invalidReason &&
              <details className="no-print my-3 text-xs">
              <summary className="cursor-pointer font-semibold text-amber-900">Reutilizar as referências deste resultado</summary>
              <p className="my-2">{nearestMembers.length} referências ({nearestMetadata?.conjunto_referencias?.forma === "CRITERIO"
                ? "definidas pelo critério" : "lista explícita"}). O resultado calculado permanece inalterado.</p>
              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={running || inspecting} onClick={()=>{setReferenceMode("list");setReferenceIds(nearestMembers);scrollAnalysisTo("preparacao-conversacional");}}
                  className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-amber-900 disabled:opacity-40">Usar como lista de referências</button>
                <button type="button" disabled={running || inspecting} onClick={()=>{changeTerritories(nearestMembers);scrollAnalysisTo("territorios");}}
                  className="rounded-lg border border-blue-200 bg-white px-3 py-2 text-teal disabled:opacity-40">Usar como municípios-alvo</button>
              </div>
            </details>}
            <p className="mt-2 text-sm leading-6 text-slate-500">{periodsInText(result.description, {number: String, period: displayPeriod})}</p>
            {/* Frase-resumo, indicadores e procedência do motor (D7); sem resumo (resultado antigo), a grade de métricas. */}
            <ResultHeader result={result}/>
            <ResultWorkspace key={result.result_id} result={result} operation={resultOperation || ""}
              reusable={!!historical && compatible(historical) && !historical.invalidReason} disabled={running || inspecting}
              status={resultStatus} siblings={siblings} onExport={exportCsv} onRepresentation={keepRepresentation}
              onOpenSibling={id => { const item = history.find(entry => entry.result.result_id === id); if (item) openHistorical(item); }}
              onReuseSelection={ids => {
                // Base oficial: itens de nível (Brasil e estados) voltam como tais; os demais, como municípios marcados.
                if (officialScope) { const next = fromMembers(ids); replaceSelection(next.scope, next.ids); } else changeTerritories(ids);
                scrollAnalysisTo("territorios");
                setHistoryNotice("Seleção visual levada à preparação: " + ids.length + " território(s). Revise e execute pela preparação."); }}
              onReferences={ids => { setReferenceMode("list"); setReferenceIds(ids); scrollAnalysisTo("preparacao-conversacional"); }}
              onAnnualSeries={periods => {
                // Só muda a seleção de períodos da evolução temporal em preparação; o cálculo continua sendo ação do usuário.
                if (active !== "temporal") { setHistoryNotice("Volte à Evolução temporal para usar a série anual (junho)."); return; }
                setMultiplePeriods(true); setSelectedPeriods(periods); setPeriodFilter("");
                setHistoryNotice("Série anual (junho) escolhida na caixa Período: " + periods.length + " competências. Revise e calcule pela preparação.");
                scrollAnalysisTo("preparacao-conversacional");
              }}/>
            {resultNotes.length > 0 && <div className="mt-6 rounded-xl border border-cyan-100 bg-cyan-50/70 p-5">
              <h4 className="flex items-center gap-2 text-sm font-bold text-ink"><SearchCheck size={17} className="text-teal"/> Método e limitações</h4>
              {resultOperation === "distribution" ? <>
                <p className="mt-3 text-xs leading-6 text-slate-700">
                  Os territórios são divididos em grupos do menor para o maior valor do indicador escolhido,
                  sempre em um mesmo período e categoria profissional.</p>
                <p className="mt-2 text-xs leading-6 text-slate-700">
                  As posições usam os valores completos, sem arredondar antes de comparar. Valores iguais compartilham a mesma posição.
                  Os valores de cada grupo e os detalhes podem ser consultados na tabela.</p>
                <details className="mt-3 text-xs">
                  <summary className="cursor-pointer font-semibold text-teal">Ver informações técnicas completas</summary>
                  <ul className="mt-2 space-y-2 leading-6 text-slate-600">{resultNotes.map((note,i)=><li key={i}>{note}</li>)}</ul>
                </details>
              </> : <ul className="mt-3 space-y-2 text-xs leading-6 text-slate-600">{resultNotes.map((note,i)=><li key={i}>{note}</li>)}</ul>}
            </div>}
            {resultOperation === "temporal" && result.detail_rows && <details className="mt-4 text-xs">
              <summary className="cursor-pointer font-semibold text-teal">Consultar competências da série temporal</summary>
              <button type="button" onClick={()=>exportCsv(result.detail_rows!)} className="no-print my-2 rounded-lg border px-3 py-2">Exportar série CSV</button>
              <div role="region" aria-label="Competências da série temporal">
                <ResultTable key={result.result_id} stateKey="series-detail" rows={result.detail_rows} columns={tableColumns(Object.keys(result.detail_rows[0] || {}))}/>
              </div>
            </details>}
          </div></InvestigationViewState.Provider>}
        </div>
      </section>

  </>) : null;

  return <div className={"min-h-screen bg-canvas" + (workspaceEngaged ? " workspace-engaged" : "")}>
    {!privacy.accepted && <SessionPrivacy onAccept={privacy.accept}/>}
    {confirmNewAnalysis && <WorkspaceDialog id="new-analysis-confirmation" title="Como deseja continuar?"
      onClose={() => {setConfirmNewAnalysis(false); pendingRun.current = null;}}>
      <p className="mt-4 text-sm leading-6">Os resultados concluídos ficam no Histórico desta sessão. Você pode iniciar uma análise independente ou acrescentar um componente ao diagnóstico atual, preservando os resultados e parâmetros de cada análise. Uma preparação ainda não executada pode ser ajustada na próxima análise.</p>
      <div className="dialog-actions">
        <button type="button" data-testid="confirm-new-analysis" onClick={() => startNewAnalysis("independent")}>Iniciar uma análise independente</button>
        <button type="button" data-testid="append-diagnostic" onClick={() => startNewAnalysis("append")}>Acrescentar ao diagnóstico atual</button>
        <button type="button" data-testid="cancel-new-analysis" onClick={() => {setConfirmNewAnalysis(false); pendingRun.current = null;}}>Cancelar</button>
      </div>
    </WorkspaceDialog>}
    {confirmNewSession && <WorkspaceDialog id="new-session-confirmation" title="Deseja iniciar uma nova sessão?" busy={closingSession}
      onClose={() => setConfirmNewSession(false)}>
      <p className="mt-4 text-sm leading-6">Ao iniciar uma nova sessão, suas análises e resultados atuais deixarão de estar disponíveis. Se desejar conservá-los, você pode exportá-los antes de continuar.</p>
      <p className="mt-3 text-xs leading-5">CSV e Imprimir / PDF exportam somente a análise em exibição. Para guardar todas, continue nesta sessão e exporte cada análise pelo Histórico. Não há persistência entre sessões.</p>
      {result && <p className="mt-2 text-sm font-semibold">Em exibição: {result.title}</p>}
      <div className="dialog-actions">
        <button type="button" data-testid="session-export-csv" disabled={!result || closingSession || resultStatus === "INVALIDADO"} onClick={() => result && exportCsv(result.rows)}>Exportar CSV</button>
        <button type="button" disabled={!result || closingSession} onClick={() => window.print()}>Imprimir / PDF</button>
        <button type="button" data-testid="cancel-new-session" disabled={closingSession} onClick={() => setConfirmNewSession(false)}>Continuar nesta sessão</button>
        <button type="button" data-testid="confirm-new-session" disabled={closingSession} onClick={() => void closeSession()}>{closingSession ? "Encerrando sessão…" : "Iniciar nova sessão"}</button>
      </div>
      {sessionError && <p role="alert" className="mt-3 text-sm text-rose-800">{sessionError}</p>}
    </WorkspaceDialog>}
    <input ref={inputRef} disabled={!privacy.accepted} type="file" accept=".csv,.xls,.xlsx" className="sr-only"
      aria-label="Importar arquivo de dados"
      onChange={e => {const next=e.target.files?.[0];e.target.value = "";void chooseFile(next);}}/>
    <div className="min-w-0">
      {serverStatus === "offline" && <div role="status" className="no-print m-4 rounded-lg bg-rose-50 px-4 py-2 text-xs text-rose-800">Serviço de análise temporariamente indisponível.</div>}
      <main id="inicio" className="workspace-main mx-auto px-4 pb-4 pt-4 sm:px-5">
      <div>
      <div className="no-print"><WelcomeHero/></div>
      <nav aria-label="Navegação principal" data-testid="main-navigation" className="main-navigation no-print">
        <button type="button" data-testid="nav-home" onClick={() => navigate("home", "inicio")} aria-current={page === "home" ? "page" : undefined}><Home size={18}/>Início</button>
        <button type="button" data-testid="nav-new-session" onClick={() => {setSessionError(""); setConfirmNewSession(true);}}><RefreshCw size={18}/>Nova sessão</button>
        <button type="button" data-testid="nav-new-analysis" disabled={running || inspecting || preflighting} onClick={requestNewAnalysis}><FileBarChart2 size={18}/>Nova análise</button>
        {historyContent}
        <button type="button" data-testid="nav-results" onClick={() => navigate("results")} aria-current={page === "results" ? "page" : undefined}><BarChart3 size={18}/>Resultados</button>
      </nav>
      <AnalysisAssistant
        notice={historyNotice}
        workspaceStage={workspaceStage}
        onStage={openStage}
        territorySummary={territorySummary}
        territoriesOpen={territoriesOpen}
        onTerritoriesOpen={setTerritoriesOpen}
        onMultiplePeriods={() => {
          if (!active || !["counts", "temporal", "report", "comparisons"].includes(active)) return false;
          if (!multiplePeriods) {setSelectedPeriods(periodFilter ? [periodFilter] : scopePeriodsOf(inspection, active, territoryScope, territoryIds));setPeriodFilter("");}
          setMultiplePeriods(true);setPeriodEditor(value => value + 1);
          scrollAnalysisTo("preparacao-conversacional"); return true;
        }}
        resultsOnly={page === "results"}
        catalogOpen={catalogOpen}
        running={running}
        investigationContent={investigationContent}
        hasResult={!!result || running}
        onStarted={() => setConversationStarted(true)}
        apiBase={API}
        privacyAccepted={privacy.accepted}
        displayedResultId={result?.conversation_reference?.available ? result.result_id : ""}
        file={file}
        dataset={usingBrazil ? "brazil" : ""} scope={inspection?.source?.scope || "auto"}
        datasetVersion={inspection?.source?.version || ""}
        sheet={sheet}
        mapping={mapping}
        options={conversationOptions()}
        contextReady={!!inspection && !inspection.requires_sheet && !!preflight && !preflighting && !inspecting}
        contextVersion={JSON.stringify({
          file: file?.name, modified: file?.lastModified, size: file?.size,
          usingBrazil, datasetVersion: sourceVersion, sourceGeneration, sheet
        })}
        validationVersion={JSON.stringify({mapping, options: semanticOptions(), scope: inspection?.source?.scope})}
        features={FEATURES.map(feature => ({...feature, availability: !preflight || inspecting || preflighting ? "Escolha e prepare os dados para verificar os requisitos." : preflight.capabilities[feature.id]?.status === "available" ? "Requisitos atendidos com a preparação atual." : preflight.capabilities[feature.id]?.status === "needs_confirmation" ? "Há escolhas pendentes." : "Requisitos ainda não atendidos; consulte a preparação."}))}
        active={active}
        selecting={inspecting}
        onSelectAnalysis={(operation,proposal)=>{
          if(!proposal)setRequestText("Análise de " + ANALYSIS_LABELS[operation]);
          selectAnalysis(operation,proposal);
        }}
        onRequest={recordRequest}
        onChooseBrazil={chooseBrazil}
        onChooseImport={() => inputRef.current?.click()}
        onExplore={exploreMessage}
        onResolved={acceptExploration}
        selection={selectionContent}
        sourceChoice={sourceChoice}
        sourceReady={!!inspection && !inspection.requires_sheet && !inspecting}
        sourceSummary={usingBrazil
          ? inspection && !inspecting ? "Os dados do Brasil já estão disponíveis. Escolha uma análise; na caixa Abrangência territorial, marque o Brasil, estados ou municípios." : "Estou preparando os dados do Brasil."
          : file ? inspection && !inspecting ? "Recebi sua base. Escolha o tipo de análise que deseja realizar." : "Estou preparando sua base."
          : ""}
        preparation={inlinePreparation}
        resultContent={resultContent}/>


      </div>
      <footer className="no-print mt-14 flex flex-col items-start justify-between gap-3 border-t border-line pt-6 text-xs text-slate-400 sm:flex-row sm:items-center">
        <p>Agente Diagnóstico Territorial · Protótipo experimental v0.1</p>
      </footer>
      </main>
    </div>
  </div>;
}

export default App;
