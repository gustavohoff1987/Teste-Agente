import { useEffect, useMemo, useRef, useState } from "react";
import ContextConfig from "./ContextConfig";
import RequirementChecklist from "./RequirementChecklist";
import DataResolution from "./DataResolution";
import DistributionResults, { displayPeriod } from "./DistributionResults";
import AnalysisAssistant from "./AnalysisAssistant";
import ConversationalPreparation, {type FieldRole} from "./ConversationalPreparation";
import BrandAvatar from "./BrandAvatar";
import PreparationPanel, { preparationRequirements } from "./PreparationPanel";
import WelcomeHero from "./WelcomeHero";
import TerritorialSelection, {type Territory} from "./TerritorialSelection";
import ReferenceSetup, {type ReferenceMode} from "./ReferenceSetup";
import SessionPrivacy, { useSessionPrivacy } from "./SessionPrivacy";
import type { Multiplicity, ResolutionOptions } from "./DataResolution";
import type { LucideIcon } from "lucide-react";
import {
  ArrowDownToLine, ArrowRight, BarChart3, Calculator, CheckCircle2,
  Home, Menu, X, MessageCircle, Grid2X2,
  ChevronDown, ClipboardList, Clock3, Database, Download, FileBarChart2, FileSpreadsheet,
  FileUp, FolderUp, Bot, Info, Layers3, ListFilter,
  LoaderCircle, LocateFixed, MapPinned, MoveRight, RefreshCw, SearchCheck, Settings2, ShieldCheck,
  Sparkles, TrendingUp, UploadCloud, UsersRound, XCircle
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis
} from "recharts";

type Role = "territory" | "territory_id" | "period" | "category" | "count" | "population" | "latitude" | "longitude" | "identity";
import { ANALYSIS_LABELS, ENGINE_ONLY_SCOPES, type Operation } from "./analysisCatalog";
type Mapping = Partial<Record<Role, string>>;
type SuperiorLevel = "territorio_superior_1" | "territorio_superior_2";
type SuperiorMapping = Partial<Record<SuperiorLevel, string>>;
type FieldStatus = "recognized" | "confirmed" | "proposed" | "unmapped";
type ColumnProfile = {
  name: string; type: string; missing: number; suspicious_header: boolean;
  proposal: { role: Role; status: "recognized" | "proposed"; evidence: string }[];
};
type Requirement = { status: "met" | "needs_confirmation" | "missing"; title: string; detail: string };
type Capability = { status: "available" | "needs_confirmation" | "unavailable"; reasons: string[]; requirements: Requirement[] };
type Preflight = {
  territory_choices?: Territory[]; selection_reason?: string;
  multiplicity: Multiplicity;
  territorial_hierarchy?: {status: string; levels: {role: string; column: string}[]; warnings: string[]};
  capabilities: Record<Operation, Capability>;
  field_states: Record<Role, { status: FieldStatus; column: string; message: string; evidence?: string }>;
  values: {territories: string[]; periods: string[]; categories: string[]};
  profile: {row_count: number; column_count: number; recognized_roles: number};
};
type Inspection = {
  requires_sheet: boolean; sheets: string[]; columns: string[]; row_count: number;
  suggested_mapping: Mapping; periods: string[]; categories: string[]; territories: string[];
  column_profiles: ColumnProfile[]; preflight: Preflight | null; suggested_category_constant: string;
  derived_fields?: { column: string; role: Role; source_columns: string[]; format: string }[];
  curated_defaults?: { mapping: Mapping; category: string; scope: "national" | "municipal"; count_unit: string;
    confirmed_roles: Role[]; fts_scope_confirmed: boolean; object_confirmed: boolean;
    population_denominator_confirmed: boolean } | null;
  source?: { dataset: string; label: string; scope: "national" | "municipal"; version: string;
    default_scopes: Partial<Record<Operation, "national" | "municipal">> };
};
type Metric = { label: string; value: string | number };
type AnalysisResult = { result_id: string; title: string; description: string; rows: Record<string, unknown>[]; total_rows: number; metrics: Metric[]; notes: string[]; metadata: Record<string, unknown>; detail_rows?: Record<string, unknown>[] };
type Exploration = {handled: boolean; reply?: string; clarification?: string; operation?: Operation;
  territory_ids?: string[]; options_patch?: {period_filter?: string; period_filters?: string[];
    temporal_indicator?: "quantity" | "density"; comparison_indicator?: "quantity" | "density";
    component_sum_confirmed?: boolean}; selection_changed?: boolean};
type Feature = { id: Operation; title: string; detail: string; icon: LucideIcon; tone: string };

const API = import.meta.env.VITE_API_BASE_URL || "";

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
  { id: "distribution", title: ANALYSIS_LABELS.distribution, detail: "Quantis, posições e frequências", icon: BarChart3, tone: "violet" },
  { id: "comparisons", title: ANALYSIS_LABELS.comparisons, detail: "Territórios, categorias e períodos", icon: MoveRight, tone: "orange" },
  { id: "temporal", title: ANALYSIS_LABELS.temporal, detail: "Mudanças e tendências", icon: TrendingUp, tone: "blue" },
  { id: "aggregate", title: ANALYSIS_LABELS.aggregate, detail: "Conjuntos territoriais e indicadores", icon: Layers3, tone: "emerald" },
  { id: "spatial", title: ANALYSIS_LABELS.spatial, detail: "Distâncias e referências geográficas", icon: MapPinned, tone: "rose" },
  { id: "ranking", title: ANALYSIS_LABELS.ranking, detail: "Seleções, posições e ordenações", icon: ListFilter, tone: "amber" },
  { id: "rotation", title: ANALYSIS_LABELS.rotation, detail: "Permanência da coorte inicial", icon: RefreshCw, tone: "cyan" },
  { id: "report", title: ANALYSIS_LABELS.report, detail: "Consolidação, tabelas e exportações", icon: FileBarChart2, tone: "slate" },
  { id: "nearest", title: ANALYSIS_LABELS.nearest, detail: "Referência geográfica mais próxima de cada alvo", icon: LocateFixed, tone: "amber" }
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
function pretty(value: unknown): string {
  if (value === null || value === undefined) return "Não avaliável";
  if (typeof value === "number") return shortNum(value);
  return String(value);
}
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
  const [page, setPage] = useState<"home" | "results">("home");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [usingBrazil, setUsingBrazil] = useState(false);
  const [brazilLevel, setBrazilLevel] = useState<"auto" | "national" | "municipal">("auto");
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
  const [scopeNotice, setScopeNotice] = useState("");
  const [preflightAttempt, setPreflightAttempt] = useState(0);
  const [active, setActive] = useState<Operation | null>(null);
  const [inlineConfirmed, setInlineConfirmed] = useState(false);
  const [requestedCategory, setRequestedCategory] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [territoryIds, setTerritoryIds] = useState<string[]>([]);
  const [comparisonIndicator, setComparisonIndicator] = useState<"quantity" | "density">("density");
  const [requestText, setRequestText] = useState("");
  type Historical = {result: AnalysisResult; request: string; sourceKey: string; contextKey: string;
    preparation: ReturnType<typeof snapshotPreparation>; invalidReason: string};
  const [history, setHistory] = useState<Historical[]>([]);
  const [invalidationReason, setInvalidationReason] = useState("");
  const [historyNotice, setHistoryNotice] = useState("");
  const pendingExploration = useRef<Exploration | null>(null);
  const [selectionProposal, setSelectionProposal] = useState<Exploration | null>(null);
  const [error, setError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [serverStatus, setServerStatus] = useState<"checking" | "online" | "offline">("checking");
  const [periodFilter, setPeriodFilter] = useState("");
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [reference, setReference] = useState("");
  const [crs, setCrs] = useState("");
  const [referenceMode, setReferenceMode] = useState<ReferenceMode>("");
  const [referenceIds, setReferenceIds] = useState<string[]>([]);
  const [criterionOperator, setCriterionOperator] = useState("");
  const [criterionValue, setCriterionValue] = useState("");
  const [quantiles, setQuantiles] = useState(5);
  const [distributionIndicator, setDistributionIndicator] = useState<"" | "quantity" | "density">("");
  const [temporalIndicator, setTemporalIndicator] = useState<"" | "quantity" | "density">("");
  const [reportIndicator, setReportIndicator] = useState<"" | "quantity" | "density">("");
  const [confirmedNoOverlap, setConfirmedNoOverlap] = useState(false);
  const [ftsScopeConfirmed, setFtsScopeConfirmed] = useState(false);
  const [singlePeriodConfirmed, setSinglePeriodConfirmed] = useState(false);
  const [confirmedRoles, setConfirmedRoles] = useState<Role[]>([]);
  const [countUnit, setCountUnit] = useState("");
  const [customCountUnit, setCustomCountUnit] = useState("");
  const [populationAligned, setPopulationAligned] = useState(false);
  const [temporalCompared, setTemporalCompared] = useState(false);
  const [territoryStable, setTerritoryStable] = useState(false);
  const [longitudinalIdentity, setLongitudinalIdentity] = useState(false);
  const [identityCountConfirmed, setIdentityCountConfirmed] = useState(false);
  const [categoryConstant, setCategoryConstant] = useState("");
  const [objectDraft, setObjectDraft] = useState("");
  const [objectConfirmed, setObjectConfirmed] = useState(false);
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [preflighting, setPreflighting] = useState(false);
  const [preflightError, setPreflightError] = useState("");
  const [resolutions, setResolutions] = useState<ResolutionOptions>({});
  const revision = useRef(0);
  const uploadRevision = useRef(0);
  const scopeDrafts = useRef<Record<string, ReturnType<typeof snapshotPreparation>>>({});

  function snapshotPreparation() {
    return { mapping: {...mapping}, options: semanticOptions(), resolutions: {...resolutions},
      objectDraft, quantiles, distributionIndicator, selectedPeriods, territoryIds, comparisonIndicator,
      referenceMode, referenceIds, criterionOperator, criterionValue };
  }
  function restorePreparation(saved: ReturnType<typeof snapshotPreparation>) {
    const o = saved.options;
    setMapping(saved.mapping); setConfirmedRoles(o.confirmed_roles);
    setHierarchyColumns(o.hierarchy_columns);
    setFtsScopeConfirmed(o.fts_scope_confirmed); setSinglePeriodConfirmed(o.single_period_confirmed);
    setCountUnit(o.count_unit); setCustomCountUnit(o.custom_count_unit);
    setPopulationAligned(o.population_denominator_confirmed); setTemporalCompared(o.temporal_comparability_confirmed);
    setTerritoryStable(o.territory_longitudinal_confirmed); setLongitudinalIdentity(o.longitudinal_identity_confirmed);
    setIdentityCountConfirmed(o.identity_count_confirmed); setCategoryConstant(o.category_constant);
    setObjectDraft(saved.objectDraft); setObjectConfirmed(o.object_confirmed);
    setPeriodFilter(o.period_filter); setSelectedPeriods(saved.selectedPeriods);
    setCategoryFilter(o.category_filter); setReference(o.reference_territory);
    setResolutions(saved.resolutions); setConfirmedNoOverlap(o.no_overlap_confirmed); setCrs(o.crs);
    setQuantiles(saved.quantiles); setDistributionIndicator(saved.distributionIndicator);
    setTemporalIndicator(o.temporal_indicator); setReportIndicator(o.report_indicator);
    setTerritoryIds(saved.territoryIds); setComparisonIndicator(saved.comparisonIndicator);
    setReferenceMode(saved.referenceMode); setReferenceIds(saved.referenceIds);
    setCriterionOperator(saved.criterionOperator); setCriterionValue(saved.criterionValue);
  }

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const selectedFeature = FEATURES.find(f => f.id === active);
  const sourceKey = JSON.stringify({source: usingBrazil ? "brazil" : "upload:" + sourceGeneration,
    version: sourceVersion, scope: inspection?.source?.scope, sheet});
  const requestKey = (operation: Operation) => JSON.stringify({sourceKey, operation, mapping,
    options: {...semanticOptions(), territory_ids: semanticOptions().territory_ids ? [...territoryIds].sort() : undefined}});
  const historical = history.find(item=>item.result.result_id===result?.result_id);
  const resultOperation = result?.metadata.operation as Operation | undefined;
  const resultFeature = FEATURES.find(item=>item.id===resultOperation);
  const resultStatus = historical?.invalidReason ? "INVALIDADO" :
    historical && active && historical.contextKey===requestKey(active) ? "VIGENTE" : "NAO_VIGENTE";
  const resultMembers = (result?.metadata.universe as {members?: Territory[]} | undefined)?.members || [];
  type NearestMetadata = {conjunto_referencias?: {forma: string; membros: {id: string}[]}; cobertura_referencias?: unknown[]};
  const nearestMetadata = result?.metadata.nearest_reference as NearestMetadata | undefined;
  const nearestMembers = nearestMetadata?.conjunto_referencias?.membros.map(item=>item.id) || [];
  // A cobertura por alvo pode ter milhares de registros: na tela, só os primeiros; o JSON exportado é integral.
  const metadataText = useMemo(() => {
    if (!result) return "";
    const coverage = nearestMetadata?.cobertura_referencias;
    return JSON.stringify(coverage && coverage.length > 50 ? {...result.metadata, nearest_reference: {...nearestMetadata,
      cobertura_referencias: [...coverage.slice(0, 50), "… mais " + (coverage.length - 50) + " registros por alvo na exportação “Método e parâmetros”"]}}
      : result.metadata, null, 2);
  }, [result]);
  const plot = useMemo(() => {
    if (!result?.rows.length) return null;
    const keys = Object.keys(result.rows[0]);
    const numeric = ["Densidade por 1.000", "Quantidade", "Variação (%)", "Rotatividade (%)", "Distância (km)", "Unidades"].find(k => keys.includes(k)) || keys.find(k => result.rows.some(r => typeof r[k] === "number"));
    const category = keys.includes("Classe") ? "Classe" : keys.find(k => result.rows.some(r => typeof r[k] === "string"));
    if (!numeric || !category) return null;
    return { numeric, category, values: result.rows.slice(0, 12).map(r => ({ name: String(r[category] ?? "").slice(0, 35), value: typeof r[numeric] === "number" ? r[numeric] : null })) };
  }, [result]);

  const scopeFor = (operation: Operation) => inspection?.source?.default_scopes[operation] ?? ENGINE_ONLY_SCOPES[operation];
  function resetReferences() {
    setReferenceMode(""); setReferenceIds([]); setCriterionOperator(""); setCriterionValue("");
  }
  async function inspectFile(nextFile: File | null, nextSheet = "", level = "auto", operation = "", preserve = false) {
    if (!privacy.accepted) return;
    if (!preserve) {setSourceGeneration(value => value + 1); setTerritoryIds([]); resetReferences();}
    const previous = preserve && inspection?.source ? { info: inspection, saved: snapshotPreparation() } : null;
    if (previous) scopeDrafts.current[previous.info.source!.version + ":" + previous.info.source!.scope] = previous.saved;
    const currentUpload = ++uploadRevision.current;
    revision.current += 1;
    setInspecting(true);
    setUploadError("");
    setError("");

    setInspection(null);
    setPreflight(null);
    const form = new FormData();
    if (nextFile) form.append("file", nextFile);
    else { form.append("dataset", "brazil"); form.append("scope", level); form.append("operation", operation); }
    form.append("sheet", nextSheet);
    try {
      const response = await fetch(API + "/api/inspect", { method: "POST", body: form });
      const details = await readApiResponse(response) as Inspection;
      if (currentUpload !== uploadRevision.current) return;
      setInspection(details);
      setSourceVersion(details.source?.version || "");
      setMapping(details.suggested_mapping);
      setHierarchyColumns({});
      setConfirmedRoles(details.curated_defaults?.confirmed_roles || []);
      setFtsScopeConfirmed(!!details.curated_defaults?.fts_scope_confirmed);
      setSinglePeriodConfirmed(false);
      setCountUnit(details.curated_defaults?.count_unit || "");
      setCustomCountUnit("");
      setPopulationAligned(!!details.curated_defaults?.population_denominator_confirmed);
      setTemporalCompared(false);
      setTerritoryStable(false);
      setLongitudinalIdentity(false);
      setIdentityCountConfirmed(false);
      setCategoryConstant("");
      setObjectDraft(details.suggested_category_constant || "");
      setObjectConfirmed(!!details.curated_defaults?.object_confirmed);
      setInlineConfirmed(!!details.curated_defaults);
      setPreflight(details.preflight);
      setPreflightError("");
      setServerStatus("online");
      setPeriodFilter("");
      setSelectedPeriods([]);
      setCategoryFilter(details.curated_defaults?.category || "");
      setReference("");
      setResolutions({});
      setConfirmedNoOverlap(false);
      setCrs("");
      setQuantiles(5);
      setDistributionIndicator("");
      setTemporalIndicator(""); setReportIndicator("");
      setScopeNotice("");
      if (previous && details.source) {
        const sameVersion = previous.info.source!.version === details.source.version;
        const cached = sameVersion ? scopeDrafts.current[details.source.version + ":" + details.source.scope] : undefined;
        if (cached) {
          restorePreparation(cached);
          setScopeNotice("Preparação deste recorte restaurada: a versão dos dados é a mesma. As confirmações serão revalidadas pelo servidor.");
        } else if (sameVersion) {
          // Só atravessam granularidades significados comuns verificáveis na mesma versão.
          // Unicidade, população, território e comparabilidade pertencem a cada recorte.
          const old = previous.saved;
          const equalValues = (a: string[], b: string[]) => a.length < 80 && b.length < 80 && JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
          const periodBefore = previous.info.derived_fields?.find(f => f.column === old.mapping.period);
          const periodAfter = details.derived_fields?.find(f => f.column === details.suggested_mapping.period);
          const samePeriod = !!periodBefore && !!periodAfter && JSON.stringify(periodBefore) === JSON.stringify(periodAfter) && equalValues(previous.info.periods, details.periods);
          const sameCategory = !!old.mapping.category && old.mapping.category === details.suggested_mapping.category && equalValues(previous.info.categories, details.categories);
          setConfirmedRoles(old.options.confirmed_roles.filter(role => (role === "period" && samePeriod) || (role === "category" && sameCategory)));
          if (samePeriod) setPeriodFilter(old.options.period_filter);
          if (sameCategory) {
            setObjectConfirmed(old.options.object_confirmed); setFtsScopeConfirmed(old.options.fts_scope_confirmed);
            setCategoryFilter(old.options.category_filter);
          }
          setScopeNotice("A abrangência mudou. Confirmações comuns de período e categoria foram mantidas quando equivalentes. Território, unidade de contagem, população e comparabilidade precisam ser conferidos neste recorte.");
        } else {
          scopeDrafts.current = {};
          setScopeNotice("A versão dos dados mudou. Revise as associações e confirme novamente os significados e as condições metodológicas.");
        }
      }
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
    scopeDrafts.current = {}; setScopeNotice(""); setStep(0); steps.current = {};
    setUsingBrazil(false); setInlineConfirmed(false);
    setFile(next);
    setSheet("");
    // Preserva apenas a escolha da capacidade; confirmações são reiniciadas.

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
    if (usingBrazil) {
      form.append("dataset", "brazil");
      form.append("scope", inspection?.source?.scope || "auto");
      form.append("dataset_version", inspection?.source?.version || "");
    } else if (file) form.append("file", file);
    form.append("sheet", sheet);
  }
  function chooseBrazil() {
    if (!privacy.accepted) return;
    scopeDrafts.current = {}; setScopeNotice(""); setStep(0); steps.current = {};
    setUsingBrazil(true); setInlineConfirmed(false); setFile(null); setSheet("");
    void inspectFile(null, "", brazilLevel, active || "");
  }
  function selectAnalysis(operation: Operation, proposal?: {
    category: string; period: string; territory: string; indicator: "density" | "quantity" | null
  }) {
    setRequestedCategory(proposal?.category || "");
    const territory = (proposal?.territory || "").normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const hinted = /municipio|municipios|municipal|cidade|cidades/.test(territory) ? "municipal"
      : /^(?:brasil|pais|nacional)$/.test(territory) ? "national"
      : territoryIds.length && brazilLevel!=="national" ? "municipal" : "auto";
    if (hinted !== "auto") setBrazilLevel(hinted);
    if (active) steps.current[active] = step;
    setStep(steps.current[operation] || 0);
    setActive(operation);  setError("");
    setInlineConfirmed(!!inspection?.curated_defaults && !inspecting);
    if (operation === "temporal") {
      setPeriodFilter("");
      if (!temporalIndicator) setTemporalIndicator(active === "counts" ? "quantity" : "density");
    }
    if (usingBrazil) {
      const target = hinted !== "auto" ? hinted : brazilLevel;
      const nextScope = target === "auto" ? scopeFor(operation) : target;
      if (!nextScope || nextScope !== inspection?.source?.scope) void inspectFile(null, "", target, operation, true);
    }
  }
  // Somente uma correspondência literal inequívoca permite aplicar automaticamente
  // o filtro pedido. Equivalências semânticas permanecem para escolha explícita.
  useEffect(() => {
    if (!inspection || inspection.requires_sheet || inspecting || !requestedCategory || categoryFilter) return;
    const normalize = (text: string) => text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();
    const matches = inspection.categories.filter(value => normalize(value) === normalize(requestedCategory));
    if (matches.length === 1) setCategoryFilter(matches[0]);
  }, [requestedCategory, inspection, inspecting, categoryFilter]);

  function semanticOptions() {
    return {
      ...resolutions,
      ...(territoryIds.length && (!usingBrazil || inspection?.source?.scope === "municipal") ? {territory_ids: territoryIds} : {}),
      comparison_indicator: comparisonIndicator,
      hierarchy_columns: hierarchyColumns,
      period_filter: periodFilter, period_filters: selectedPeriods,
      category_filter: categoryFilter,
      reference_territory: reference, crs, quantile_count: quantiles,
      distribution_indicator: distributionIndicator,
      temporal_indicator: temporalIndicator, report_indicator: reportIndicator,
      no_overlap_confirmed: confirmedNoOverlap,
      fts_scope_confirmed: ftsScopeConfirmed,
      single_period_confirmed: singlePeriodConfirmed,
      confirmed_roles: confirmedRoles,
      count_unit: countUnit,
      custom_count_unit: customCountUnit,
      population_denominator_confirmed: populationAligned,
      temporal_comparability_confirmed: temporalCompared,
      territory_longitudinal_confirmed: territoryStable,
      longitudinal_identity_confirmed: longitudinalIdentity,
      identity_count_confirmed: identityCountConfirmed,
      category_constant: categoryConstant,
      require_object_confirmation: true,
      object_confirmed: objectConfirmed,
      ...(active === "nearest" && referenceMode ? {reference_mode: referenceMode, ...(referenceMode === "list"
        ? {reference_ids: referenceIds} : {reference_criterion: {operator: criterionOperator, value: criterionValue}})} : {})
    };
  }
  function changeTerritories(ids: string[]) {
    revision.current += 1;
    // Reaplicar a mesma seleção não cria estado novo: o pré-exame vigente já corresponde a ela.
    setTerritoryIds(current=>sameList(current, ids) ? current : ids); setSelectionProposal(null);
    // Premissas sobre uma união não se transferem para membros diferentes.
    setConfirmedNoOverlap(false); setTerritoryStable(false);
    setResolutions(previous=>previous.comparison_confirmed === false && previous.population_additive_confirmed === false &&
      previous.identity_union_confirmed === false ? previous : {...previous, comparison_confirmed:false,
      population_additive_confirmed:false, identity_union_confirmed:false});
  }
  function applyExploration(proposal: Exploration) {
    if (!proposal.operation || !proposal.territory_ids) return;
    if (usingBrazil && inspection?.source?.scope !== "municipal") {
      pendingExploration.current = proposal; setSelectionProposal(null);
      setBrazilLevel("municipal"); setActive(proposal.operation);
      void inspectFile(null, "", "municipal", proposal.operation, true);
      return;
    }
    changeTerritories(proposal.territory_ids);
    const patch = proposal.options_patch || {};
    if (patch.period_filter !== undefined) setPeriodFilter(patch.period_filter);
    const periods = patch.period_filters;
    if (periods !== undefined) setSelectedPeriods(current=>sameList(current, periods) ? current : periods);
    if (patch.temporal_indicator) setTemporalIndicator(patch.temporal_indicator);
    if (patch.comparison_indicator) setComparisonIndicator(patch.comparison_indicator);
    if (patch.component_sum_confirmed) {
      setConfirmedNoOverlap(false);
      setResolutions(previous=>({...previous, component_sum_confirmed:true, identity_union_confirmed:false}));
    }
    setActive(proposal.operation); setInlineConfirmed(!!inspection?.curated_defaults); setError("");
  }
  async function exploreMessage(message: string): Promise<string | null> {
    if (!inspection || inspecting) return null;
    const currentRevision = revision.current;
    const form = new FormData(); appendSource(form);
    form.append("message", message); form.append("mapping", JSON.stringify(mapping));
    form.append("options", JSON.stringify({...semanticOptions(), exploration_indicator:
      active === "counts" ? "quantity" : active === "temporal" ? temporalIndicator || "quantity" : comparisonIndicator}));
    const response = await fetch(API + "/api/exploration/interpret", {method:"POST", body:form});
    const proposal = await readApiResponse(response) as Exploration;
    if (currentRevision !== revision.current) return "O contexto mudou durante a interpretação. Envie novamente o pedido com a seleção atual.";
    if (!proposal.handled) return null;
    if (proposal.clarification) return proposal.clarification;
    if (proposal.operation && !proposal.territory_ids) {
      // Comando que só prepara a operação: alvos, referências e confirmações seguem nos controles.
      selectAnalysis(proposal.operation);
      return proposal.reply || "Análise preparada. Confira as condições abaixo.";
    }
    if (proposal.selection_changed) {
      setSelectionProposal(proposal);
      return "O pedido menciona um conjunto diferente da seleção atual. Confirme abaixo se deseja usar o recorte mencionado.";
    }
    if (usingBrazil && inspection.source?.scope !== "municipal") {
      pendingExploration.current = proposal;
      setBrazilLevel("municipal"); setActive(proposal.operation || null);
      void inspectFile(null, "", "municipal", proposal.operation, true);
    } else applyExploration(proposal);
    return proposal.reply || "Recorte preparado. Confira as condições e execute a análise.";
  }
  useEffect(()=>{
    if (!inspecting && inspection?.source?.scope === "municipal" && pendingExploration.current) {
      const proposal = pendingExploration.current; pendingExploration.current = null;
      applyExploration(proposal);
    }
  }, [inspection, inspecting]);
  function exploreSelection(operation: Operation) {
    setRequestText(ANALYSIS_LABELS[operation] + " dos territórios selecionados");
    selectAnalysis(operation);
    document.getElementById("preparacao-conversacional")?.scrollIntoView({behavior:"smooth"});
  }
  function openHistorical(item: Historical) {
    setResult(item.result); setInvalidationReason(""); setHistoryNotice(""); setError("");
  }
  function restoreHistorical(item: Historical) {
    if (item.invalidReason || item.sourceKey !== sourceKey) return;
    restorePreparation(structuredClone(item.preparation));
    setActive(item.result.metadata.operation as Operation); setRequestText(item.request);
    setInlineConfirmed(true); setHistoryNotice("Parâmetros e seleção restaurados; o servidor verificará novamente a preparação.");
  }
  // Os identificadores da seleção derivam do nome/código associados; sem eles, deixam de existir.
  function removeAssociation(role: Role) {
    setMapping(previous => ({...previous, [role]: ""}));
    setConfirmedRoles(previous => previous.filter(item => item !== role));
    if (role === "territory" || role === "territory_id") {setTerritoryIds([]); setReferenceIds([]);}
  }
  function associateColumn(column: string, role: Role | "") {
    if (role === "count") setCountUnit("");
    if (role === "identity") { setIdentityCountConfirmed(false); setLongitudinalIdentity(false); }
    if (role === "period") { setPopulationAligned(false); setTemporalCompared(false); setTerritoryStable(false); }
    if (role === "territory" || role === "territory_id") {
      setTerritoryIds([]); setReferenceIds([]);
      setPopulationAligned(false); setTerritoryStable(false); setReference("");
      setConfirmedNoOverlap(false); setResolutions(previous => ({number_format: previous.number_format}));
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
    setConfirmedRoles(previous => [...previous.filter(r => r !== previouslyAssociated && r !== role), ...(role ? [role] : [])]);
    if (role === "category" || previouslyAssociated === "category") {
      setObjectConfirmed(false);
      setCategoryConstant("");
    }

    setError("");
  }
  async function run(op: Operation) {
    if (!privacy.accepted || runningRef.current) return;
    setActive(op);  setError("");
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
      document.getElementById("dados")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    setUploadError("");
    const contextKey = requestKey(op);
    const reusable = history.find(item=>item.contextKey===contextKey && !item.invalidReason);
    if (reusable) {
      setResult(reusable.result); setHistoryNotice("Resultado existente recuperado, sem recalcular.");
      resultsRef.current?.scrollIntoView({behavior:"smooth"});
      return;
    }
    const preparation = structuredClone(snapshotPreparation());
    const originRequest = requestText || "Análise de " + ANALYSIS_LABELS[op];
    runningRef.current = true; setRunning(true);
    const currentRevision = revision.current;
    const form = new FormData();
    appendSource(form); form.append("operation", op);
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
      setResult(calculated); setHistoryNotice("");
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    } catch (exc) {
      if (currentRevision !== revision.current) return;
      setError(readableError(exc));
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    }
    finally { runningRef.current = false; setRunning(false); }
  }

  function navigate(view: "home" | "results", target?: string) {
    setPage(view);
    setMobileMenuOpen(false);
    const fragment = target || (view === "results" ? "resultados" : "inicio");
    if (window.location.hash !== "#" + fragment) window.location.hash = fragment;
    window.setTimeout(() => document.getElementById(fragment)?.scrollIntoView({
      behavior: "smooth", block: "start"
    }), 80);
  }
  useEffect(() => {
    const onHashChange = () => setPage("home");
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
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
  const nearestOptions = active === "nearest" && referenceMode ? JSON.stringify([referenceMode, referenceIds, criterionOperator, criterionValue]) : "";
  // O servidor recalcula a matriz após qualquer associação ou confirmação.
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
  }, [inspection, file, usingBrazil, sheet, mapping, confirmedRoles, countUnit, customCountUnit, preflightAttempt,
      periodFilter, selectedPeriods, categoryFilter, populationAligned, temporalCompared, territoryStable,
      longitudinalIdentity, identityCountConfirmed, categoryConstant, objectConfirmed,
      ftsScopeConfirmed, singlePeriodConfirmed, reference, crs, confirmedNoOverlap, resolutions, quantiles, distributionIndicator, temporalIndicator, reportIndicator, hierarchyColumns, territoryIds, comparisonIndicator,
      nearestOptions]);

  useEffect(() => { revision.current += 1;  setError(""); }, [active]);

  const sideLink = (label: string, view: "home" | "results", Icon: LucideIcon, target?: string) =>
    <button type="button" onClick={() => navigate(view, target)}
      className={["flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition",
        page === view && !target ? "bg-blue-600 text-white" : "text-slate-200 hover:bg-white/10 hover:text-white"].join(" ")}>
      <Icon size={18}/>{label}
    </button>;

  const decimalPending = !!preflight?.capabilities.nearest?.reasons.some(reason => /separador decimal|ponto decimal/.test(reason));
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
    {inspection?.requires_sheet && <label className="text-xs text-slate-700">Qual aba deseja utilizar?
      <select className="ml-2 rounded-lg border border-line px-2 py-1" value={sheet}
        onChange={e=>{const next=e.target.value;setSheet(next);if(file&&next)void inspectFile(file,next);}}>
        <option value="">Selecione uma aba</option>
        {inspection.sheets.map(name=><option key={name} value={name}>{name}</option>)}
      </select>
    </label>}
  </div>;

  const advancedPreparation = (<>
      {active && <div className="preparation-workspace section-anchor mt-5">
        <PreparationPanel title={selectedFeature?.title || "Preparar uma análise"} step={step} onStep={setStep}
          checking={preflighting || inspecting} requirements={visibleRequirements}
          ready={!!active && !preflighting && !inspecting && preflight?.capabilities[active]?.status === "available"}
          notice={scopeNotice}>
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
              <p className="text-xs text-slate-600">{usingBrazil ? "Dados do Brasil" : file?.name} · {shortNum(inspection.row_count)} registros. Confira os significados propostos; confirmações válidas permanecem registradas.</p>
        {usingBrazil && inspection?.source && <div className="mt-3 rounded-xl border border-blue-100 bg-white p-4">
          <label className="flex flex-wrap items-center gap-3 text-xs font-semibold text-ink">
            Abrangência da análise
            <select aria-label="Abrangência da análise" value={brazilLevel}
              className="rounded-xl border border-line bg-white px-3 py-2 text-sm"
              onChange={e => { const level = e.target.value as typeof brazilLevel; setBrazilLevel(level); const resolved = level === "auto" ? scopeFor(active || "density") : level; if (resolved !== inspection.source?.scope) void inspectFile(null, "", level, active || "", true); }}>
              <option value="auto">Conforme a análise escolhida</option>
              <option value="national">Brasil</option>
              <option value="municipal">Municípios</option>
            </select>
          </label>
          <p className="mt-2 text-xs leading-5 text-slate-600">
            Recorte atual: {inspection.source.scope === "national" ? "Brasil" : "Municípios"}.
            A seleção automática acompanha a análise. As fontes nacional e municipal mantêm suas contagens separadas.
          </p>
        </div>}

          <ContextConfig spatial={active === "spatial"} columns={inspection.columns} mapping={mapping}
            periodSources={inspection.derived_fields?.find(field => field.role === "period" && field.column === mapping.period)?.source_columns}
            fieldStates={preflight?.field_states} categories={preflight?.values.categories || inspection.categories}
            suggestedCategory={inspection.suggested_category_constant} objectDraft={objectDraft}
            objectConfirmed={objectConfirmed}
            territoryCode={mapping.territory_id || ""}
            codeConfirmed={preflight?.field_states.territory_id?.status === "confirmed"}
            detectedLevels={preflight?.territorial_hierarchy?.levels || inspection.preflight?.territorial_hierarchy?.levels}
            selectedLevels={hierarchyColumns}
            onSelectLevel={(level, column) => {
              setHierarchyColumns(previous => ({...previous, [level]: column}));

            }}
            onSelectCode={column => {
              if(column) associateColumn(column, "territory_id");
              else removeAssociation("territory_id");
            }}
            onConfirmCode={() => setConfirmedRoles(p => [...new Set<Role>([...p, "territory_id"])])}
            onSelect={(role, column) => {
              if (column) associateColumn(column, role);
              else removeAssociation(role);
              if (role === "category") {
                setObjectConfirmed(false);
                setCategoryConstant("");
              }
            }}
            onConfirmRole={role => {
              setConfirmedRoles(prev => [...new Set([...prev, role])]);

            }}
            onDraft={value => {
              setObjectDraft(value);
              setObjectConfirmed(false);
              setCategoryConstant("");

            }}
            onConfirmObject={() => {
              if (!mapping.category) setCategoryConstant(objectDraft.trim());
              else setConfirmedRoles(prev => [...new Set<Role>([...prev, "category"])]);
              setObjectConfirmed(true);

            }}
          />
                {active !== "spatial" && !mapping.period && <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                  <input type="checkbox" checked={singlePeriodConfirmed} onChange={e => setSinglePeriodConfirmed(e.target.checked)}/>
                  Confirmo que a base se refere a um único período
                </label>}
                {active !== "spatial" && <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                  <input type="checkbox" checked={ftsScopeConfirmed} onChange={e => setFtsScopeConfirmed(e.target.checked)}/>
                  Confirmo que os trabalhadores informados fazem parte da força de trabalho na saúde
                </label>}
            </>}
            {step === 1 && <>
        {active && inspection && !inspection.requires_sheet && <div className="mb-4 rounded-2xl border border-line bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-bold text-ink">Parâmetros da análise</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <SelectField label="Filtrar por período" value={periodFilter}
              options={preflight?.values.periods || inspection.periods}
              onChange={v => {setPeriodFilter(v); }}/>
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
            selectIdentity={column => {if(column) associateColumn(column, "identity"); else setMapping(p => ({...p, identity: ""}));}}
            identityConfirmed={identityCountConfirmed} confirmIdentity={setIdentityCountConfirmed}
            confirmCoordinates={() => setConfirmedRoles(p => [...new Set<Role>([...p, "latitude", "longitude"])])}/>
            <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50/40 p-4 sm:p-5">
              <h4 className="text-sm font-bold text-ink">Completar informações para esta análise</h4>
              <p className="mt-1 text-xs leading-5 text-slate-600">Preencha somente os dados que correspondem à estrutura real da sua base. Uma confirmação não substitui informações ausentes.</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {active !== "spatial" && active !== "rotation" && (active !== "nearest" || referenceMode === "criterion") && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Onde estão os quantitativos dos profissionais?
                    <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.count || ""} onChange={e => {
                        if (e.target.value) associateColumn(e.target.value, "count");
                        else { setMapping(prev=>({...prev,count:""})); setConfirmedRoles(prev=>prev.filter(x=>x!=="count")); }
                      }}>
                      <option value="">Não encontrado nesta base</option>
                      {inspection.columns.map(col => <option key={col} value={col}>{col}</option>)}
                    </select>
                  </label>
                  {mapping.count && preflight?.field_states.count.status === "proposed" &&
                    <button type="button" onClick={() => setConfirmedRoles(prev=>[...new Set<Role>([...prev, "count"])])}
                      className="self-end rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-xs font-bold text-amber-900 hover:bg-amber-100">
                      Confirmar que esta coluna contém quantitativos
                    </button>}
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
                {(["density","comparisons","ranking","aggregate"].includes(active) || (active === "distribution" && distributionIndicator === "density") || (active === "temporal" && temporalIndicator === "density") || (active === "report" && reportIndicator === "density") || (active === "nearest" && referenceMode === "criterion")) && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Coluna com a população correspondente
                    <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.population || ""} onChange={e => {
                        if (e.target.value) associateColumn(e.target.value, "population");
                        else {setMapping(prev=>({...prev,population:""}));setConfirmedRoles(prev=>prev.filter(x=>x!=="population"));}
                        setPopulationAligned(false);
                      }}>
                      <option value="">Não encontrada nesta base</option>
                      {inspection.columns.map(col => <option key={col} value={col}>{col}</option>)}
                    </select>
                  </label>
                  {mapping.population && preflight?.field_states.population.status === "proposed" &&
                    <button type="button" className="self-end rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-xs font-bold text-amber-900"
                      onClick={() => setConfirmedRoles(prev=>[...new Set<Role>([...prev, "population"])])}>Confirmar coluna de população</button>}
                  {mapping.population && <label className="flex items-start gap-2 self-center text-xs leading-5 text-slate-700">
                    <input type="checkbox" checked={populationAligned} onChange={e => setPopulationAligned(e.target.checked)}/>
                    Confirmo que a população corresponde aos territórios e períodos analisados
                  </label>}
                </>}
                {active === "temporal" && <>
                  <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                    <input type="checkbox" checked={temporalCompared} onChange={e => setTemporalCompared(e.target.checked)}/>
                    Confirmo que os períodos e os quantitativos são comparáveis
                  </label>
                  {mapping.territory && <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                    <input type="checkbox" checked={territoryStable} onChange={e => setTerritoryStable(e.target.checked)}/>
                    Confirmo que os territórios mantêm identidade comparável ao longo dos períodos
                  </label>}
                </>}
                {active === "rotation" && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Coluna de identificação individual
                    <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.identity || ""} onChange={e => {if(e.target.value)associateColumn(e.target.value,"identity");else setMapping(prev=>({...prev,identity:""}));}}>
                      <option value="">Não identificada</option>
                      {inspection.columns.map(col=><option key={col} value={col}>{col}</option>)}
                    </select>
                  </label>
                  {mapping.identity && preflight?.field_states.identity.status === "proposed" && <button
                    type="button" className="self-end rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-xs font-bold text-amber-900"
                    onClick={() => setConfirmedRoles(prev=>[...new Set<Role>([...prev, "identity"])])}>Confirmar identificação individual</button>}
                  <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                    <input type="checkbox" checked={longitudinalIdentity} onChange={e => setLongitudinalIdentity(e.target.checked)}/>
                    Confirmo identidade pessoal válida entre os períodos, com abrangência e completude adequadas
                  </label>
                  <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                    <input type="checkbox" checked={territoryStable} onChange={e => setTerritoryStable(e.target.checked)}/>
                    Confirmo a comparabilidade territorial entre períodos, quando aplicável
                  </label>
                </>}
                {(active === "spatial" || active === "nearest") && <>
                  {(["latitude","longitude"] as Role[]).map(role => <label key={role} className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    {role === "latitude" ? "Latitude" : "Longitude"}
                    <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping[role] || ""} onChange={e => {if(e.target.value) associateColumn(e.target.value,role); else setMapping(prev=>({...prev,[role]:""}));}}>
                      <option value="">Não encontrada</option>
                      {inspection.columns.map(col=><option key={col} value={col}>{col}</option>)}
                    </select>
                  </label>)}
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Referencial geodésico informado para a base
                    <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={crs} onChange={e=>setCrs(e.target.value)}>
                      <option value="">Não informado</option><option value="SIRGAS2000">SIRGAS2000</option>
                    </select>
                  </label>
                  {active === "spatial" && <SelectField label="Território de referência" value={reference}
                    options={preflight?.values.territories || []} onChange={setReference}/>}
                </>}
                {active === "aggregate" && <>
                  <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                    <input type="checkbox" checked={confirmedNoOverlap} onChange={e => setConfirmedNoOverlap(e.target.checked)}/>
                    Declaro ausência de sobreposição das pessoas entre territórios, se desejar interpretar o total como pessoas únicas
                  </label>
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
                <p>Base: {usingBrazil ? "Dados do Brasil — " + (inspection.source?.scope === "national" ? "Brasil" : "Municípios") : file?.name}</p>
                <p>Território: {mapping.territory || "Não associado"}{mapping.territory_id ? " · Identificador: " + mapping.territory_id : ""}</p>
                <p>Período: {periodFilter || "Todos os períodos da base"} · Categoria: {categoryFilter || categoryConstant || "Categorias da base"}</p>
                <p>Unidade: {countUnit === "outro" ? customCountUnit : countUnit || (identityCountConfirmed ? "Pessoas distintas" : "Conforme a análise")}</p>
                {active === "nearest" && <p>Referências: {referenceMode === "list" ? "lista explícita com " + referenceIds.length + " municípios" :
                  referenceMode === "criterion" ? "densidade por 1.000 habitantes " + (criterionOperator || "?") + " " + (criterionValue || "?") :
                  "aguardando definição"} · Referencial: {crs || "não informado"}</p>}
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
      curated={!!inspection.curated_defaults}
      selectedPeriods={selectedPeriods}
      onSelectedPeriods={values=>{setSelectedPeriods(values);setPeriodFilter("");}}
      scope={inspection.source?.scope || "municipal"}
      onScope={v=>{setBrazilLevel(v);setInlineConfirmed(false);if(v!==inspection.source?.scope)void inspectFile(null,"",v,active,true);}}
      columns={inspection.columns}
      mapping={mapping}
      onField={(role:FieldRole,column)=>{setInlineConfirmed(false);
        if(column)associateColumn(column,role as Role);
        else removeAssociation(role as Role);
        if(role==="population")setPopulationAligned(false);
      }}
      countUnit={countUnit}
      onCountUnit={v=>{setCountUnit(v);setInlineConfirmed(false);}}
      customCountUnit={customCountUnit}
      onCustomCountUnit={setCustomCountUnit}
      indicator={active==="comparisons"?comparisonIndicator:active==="distribution"?distributionIndicator:active==="temporal"?temporalIndicator:reportIndicator}
      onIndicator={v=>{
        if(active==="comparisons" && v)setComparisonIndicator(v);
        if(active==="distribution")setDistributionIndicator(v);
        if(active==="temporal")setTemporalIndicator(v);
        if(active==="report")setReportIndicator(v);
        setInlineConfirmed(!!inspection.curated_defaults);
      }}
      periodFilter={periodFilter}
      periods={preflight?.values.periods?.length ? preflight.values.periods : inspection.periods}
      onPeriod={v=>{setPeriodFilter(v);setSelectedPeriods([]);setInlineConfirmed(!!inspection.curated_defaults);}}
      categoryFilter={categoryFilter}
      requestedCategory={requestedCategory}
      categories={preflight?.values.categories?.length ? preflight.values.categories : inspection.categories}
      onCategory={v=>{setCategoryFilter(v);setInlineConfirmed(false);}}
      populationAligned={populationAligned}
      onPopulationAligned={setPopulationAligned}
      ftsConfirmed={ftsScopeConfirmed}
      onFtsConfirmed={setFtsScopeConfirmed}
      reference={reference}
      territories={preflight?.values.territories || inspection.territories}
      onReference={setReference}
      crs={crs}
      onCrs={setCrs}
      preparing={preflighting || inspecting}
      confirmed={inlineConfirmed}
      onConfirm={()=>{
        setConfirmedRoles(previous=>[...new Set<Role>([...previous,...(Object.entries(mapping)
          .filter((entry):entry is [Role,string]=>!!entry[1])
          .map(([role])=>role))])]);
        if(mapping.category){setObjectConfirmed(true);}
        else if(objectDraft.trim()){setCategoryConstant(objectDraft.trim());setObjectConfirmed(true);}
        setInlineConfirmed(true);
      }}
      capability={preflight?.capabilities[active]}
      onExecute={()=>{void run(active);}}
      executing={running}
      extra={<div className="space-y-2 text-xs leading-5">
        {active === "nearest" && <ReferenceSetup mode={referenceMode} onMode={setReferenceMode}
          items={preflight?.territory_choices || []} reason={preflight?.selection_reason}
          referenceIds={referenceIds} onReferenceIds={setReferenceIds}
          operator={criterionOperator} onOperator={setCriterionOperator} value={criterionValue} onValue={setCriterionValue}
          showDecimal={decimalPending || !!resolutions.number_format} numberFormat={resolutions.number_format}
          onNumberFormat={value=>setResolutions(previous=>({...previous, number_format: value || undefined}))}
          disabled={running || inspecting}/>}
        {active === "temporal" && <>
          <label className="flex items-start gap-2"><input type="checkbox" checked={temporalCompared}
            onChange={e=>setTemporalCompared(e.target.checked)}/>
            Confirmo que os quantitativos e os períodos são comparáveis.</label>
          {mapping.territory && <label className="flex items-start gap-2"><input type="checkbox" checked={territoryStable}
            onChange={e=>setTerritoryStable(e.target.checked)}/>
            Os territórios correspondem às mesmas unidades ao longo do tempo.</label>}
        </>}
        {["comparisons","ranking"].includes(active) && <label className="flex items-start gap-2">
          <input type="checkbox" checked={!!resolutions.comparison_confirmed}
            onChange={e=>setResolutions(p=>({...p,comparison_confirmed:e.target.checked}))}/>
          As medidas, unidades e populações são comparáveis entre os territórios.</label>}
        {active === "aggregate" && <>
          <label className="flex items-start gap-2"><input type="checkbox" checked={!!resolutions.population_additive_confirmed}
            onChange={e=>setResolutions(p=>({...p,population_additive_confirmed:e.target.checked}))}/>
            As populações são partes sem sobreposição do conjunto agregado.</label>
          <label className="flex items-start gap-2"><input type="checkbox" checked={confirmedNoOverlap}
            onChange={e=>{setConfirmedNoOverlap(e.target.checked);
              if(e.target.checked)setResolutions(p=>({...p,component_sum_confirmed:false}));}}/>
            As contagens representam unidades sem sobreposição entre territórios.</label>
          <label className="flex items-start gap-2"><input type="checkbox" checked={!!resolutions.component_sum_confirmed}
            onChange={e=>{setResolutions(p=>({...p,component_sum_confirmed:e.target.checked}));
              if(e.target.checked)setConfirmedNoOverlap(false);}}/>
            Caso contrário, autorizo somar componentes, mesmo com possível dupla contagem.</label>
        </>}
        {active === "rotation" && <>
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
          <label className="flex items-start gap-2"><input type="checkbox" checked={longitudinalIdentity}
            onChange={e=>setLongitudinalIdentity(e.target.checked)}/>
            O identificador representa a mesma pessoa nos períodos.</label>
          <label className="flex items-start gap-2"><input type="checkbox" checked={territoryStable}
            onChange={e=>setTerritoryStable(e.target.checked)}/>
            As unidades territoriais são comparáveis entre os períodos.</label>
          <label className="flex items-start gap-2"><input type="checkbox" checked={!!resolutions.cohort_coverage_confirmed}
            onChange={e=>setResolutions(p=>({...p,cohort_coverage_confirmed:e.target.checked}))}/>
            A base cobre o mesmo universo de trabalhadores nos períodos considerados.</label>
        </>}
      </div>}
      referenceMode={referenceMode}
      advanced={advancedPreparation}
    /></div> : null;
  const selectionContent = inspection && (!usingBrazil || inspection.source?.scope==="municipal") ? <>
    <TerritorialSelection items={preflight?.territory_choices || []} selected={territoryIds}
      onChange={changeTerritories} disabled={running || inspecting} reason={preflight?.selection_reason}
      {...(active === "nearest" ? {title: "Municípios-alvo",
        description: "Para cada município-alvo, será indicada a referência mais próxima. Sem seleção, todos os municípios do período são alvos."} : {})}/>
    {selectionProposal && <div role="alert" className="no-print my-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs">
      <p>O pedido usará {selectionProposal.territory_ids?.length} territórios em lugar da seleção atual.</p>
      <button type="button" onClick={()=>applyExploration(selectionProposal)} className="mr-2 mt-2 rounded-lg border bg-white px-3 py-2">Usar o recorte mencionado</button>
      <button type="button" onClick={()=>setSelectionProposal(null)} className="mt-2 rounded-lg border bg-white px-3 py-2">Manter seleção atual</button>
    </div>}
    {!!territoryIds.length && <div aria-label="Explorar seleção" className="no-print mb-3 flex flex-wrap gap-2">
      {([ ["comparisons", "Comparar selecionados"], ["temporal", "Examinar evolução temporal"], ["aggregate", "Agregar municípios"] ] as const)
        .filter(([operation])=>!!preflight && (preflight.capabilities[operation].status!=="unavailable" ||
          operation==="temporal" && preflight.values.periods.length>=2 && !!mapping.count))
        .map(([operation,label])=><button key={operation} type="button" disabled={running || inspecting || preflighting}
          onClick={()=>exploreSelection(operation)} className="rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-semibold text-teal disabled:opacity-40">{label}</button>)}
    </div>}
  </> : null;
  const resultContent = (history.length || result || running || error) ? (<>
      <section id="resultados" ref={resultsRef} className="section-anchor mt-4 pt-3">
        <button type="button" onClick={() => document.getElementById("preparacao-conversacional")?.scrollIntoView({behavior:"smooth"})}
          className="no-print mb-5 inline-flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-xs font-semibold text-teal hover:bg-blue-50">
          <ArrowRight size={15} className="rotate-180"/> Voltar às opções
        </button>
        <SectionHeader eyebrow="Sua análise" title="Resultado do diagnóstico" description="Confira os resultados e, quando desejar, exporte os dados ou consulte os detalhes do método."/>
        <nav aria-label="Histórico de resultados" className="no-print mb-4 space-y-2">
          <p className="text-xs text-slate-500">{history.length} resultados preservados nesta sessão</p>
          <ol className="flex max-h-56 flex-wrap gap-2 overflow-y-auto">
            {history.map((item,index)=><li key={item.result.result_id} className="min-w-0 max-w-full">
              <button type="button" onClick={()=>openHistorical(item)} aria-pressed={result?.result_id===item.result.result_id}
                className={"max-w-full rounded-xl border px-3 py-2 text-left text-xs " + (result?.result_id===item.result.result_id ? "border-blue-500 bg-blue-50" : "border-line bg-white")}>
                <strong>{index+1}. {item.result.title}</strong><span className="block break-words text-slate-600">{item.request}</span>
                <span>{item.invalidReason ? "Invalidado" : active && item.contextKey===requestKey(active) ? "Válido · vigente" : "Válido · histórico não vigente"}</span>
              </button>
            </li>)}
          </ol>
          {historical && history.indexOf(historical)>0 && <button type="button" className="rounded-lg border px-3 py-2 text-xs text-teal"
            onClick={()=>openHistorical(history[history.indexOf(historical)-1])}>Voltar ao resultado anterior</button>}
        </nav>
        {historyNotice && <p role="status" className="my-3 text-xs text-teal">{historyNotice}</p>}
        <div className="rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7 print-content">
          <div className="no-print flex flex-wrap items-start justify-between gap-4 border-b border-line pb-6">
            <div className="flex items-start gap-3">
              <span className="rounded-xl bg-teal-50 p-2.5 text-teal">{resultFeature ? <resultFeature.icon size={22}/> : <ClipboardList size={22}/>}</span>
              <div><h3 className="font-bold text-ink">{resultFeature?.title || "Selecione uma análise"}</h3><p className="mt-1 text-xs text-slate-500">{resultFeature?.detail || "Os resultados aparecerão aqui após a execução."}</p></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button disabled={!result || resultStatus==="INVALIDADO"} onClick={() => result && exportCsv(result.rows)} className="flex items-center gap-1.5 rounded-xl border border-line px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-40"><ArrowDownToLine size={14}/> {resultOperation === "distribution" ? "Resumo CSV" : "CSV"}</button>
              <button disabled={!result} onClick={() => result && downloadText("metodo_diagnostico.json", JSON.stringify({title: result.title, notes: result.notes, ...result.metadata,
                result_id:result.result_id, validity: historical?.invalidReason ? "INVALIDADO" : "VALIDO", currency:resultStatus,
                invalidation_reason:historical?.invalidReason || ""}, null, 2), "application/json")} className="rounded-xl border px-3 py-2 text-xs disabled:opacity-40">Método e parâmetros</button>
              <button disabled={!result} onClick={() => window.print()} className="flex items-center gap-1.5 rounded-xl border border-line px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-40"><FileSpreadsheet size={14}/> Imprimir / PDF</button>
            </div>
          </div>
          <div id="filtros-resultados" className="no-print mt-4">
            <button type="button" className="font-bold text-teal underline" onClick={() => document.getElementById("preparacao-conversacional")?.scrollIntoView({behavior:"smooth"})}>Alterar a preparação</button>
          </div>
          {error && <div role="alert" className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><XCircle size={18} className="shrink-0"/>{error}</div>}
          {running && <div role="status" className="flex flex-col items-center justify-center gap-3 py-16 text-center text-sm text-teal">
            <LoaderCircle size={28} className="animate-spin"/>
            <strong>Preparando seu diagnóstico</strong>
            <p className="max-w-sm text-xs leading-5 text-slate-600">
              A análise está em andamento. Os resultados aparecerão aqui quando estiverem prontos.
            </p>
          </div>}
          {!running && !result && !error && <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="mb-4 rounded-2xl bg-slate-50 p-5 text-slate-300"><Database size={34} strokeWidth={1.6}/></span>
            <p className="text-base font-bold text-ink">Seus resultados aparecerão aqui</p>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
              Volte à análise, confirme os campos e os parâmetros e execute quando estiver pronto.
              Nenhum cálculo ocorre apenas por importar dados.
            </p>
            <button type="button" onClick={() => navigate("home", "analises")}
              className="no-print mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-blue-700">
              Escolher uma análise
            </button>
          </div>}
          {result && <div className="pt-6">
            <h3 className="text-xl font-bold text-ink">{result.title}</h3>
            <p data-testid="result-status" className="mt-2 text-xs font-semibold text-slate-600">{resultStatus==="INVALIDADO" ? "Resultado invalidado: " + historical?.invalidReason :
              resultStatus==="VIGENTE" ? "Resultado válido e vigente no contexto atual" : "Resultado histórico válido · não vigente no contexto atual"}</p>
            {historical && <details className="my-3 rounded-lg border border-line p-3 text-xs">
              <summary className="cursor-pointer font-semibold text-teal">Consultar solicitação e parâmetros</summary>
              <p className="mt-3 break-words">Solicitação: {historical.request}</p>
              <p className="break-all">Identidade: {result.result_id}</p>
              <pre tabIndex={0} aria-label="Metadados e parâmetros do resultado" className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-words">{metadataText}</pre>
              <button type="button" disabled={!!historical.invalidReason || historical.sourceKey!==sourceKey || inspecting || running}
                onClick={()=>restoreHistorical(historical)} className="no-print mt-3 rounded-lg border px-3 py-2 text-teal disabled:opacity-40">Retomar parâmetros deste resultado</button>
              {historical.sourceKey!==sourceKey && <p className="mt-2">A fonte ou versão atual difere da utilizada neste resultado. O conteúdo histórico permanece consultável.</p>}
            </details>}
            {!!resultMembers.length && historical?.sourceKey===sourceKey && !historical.invalidReason && <details className="no-print my-3 text-xs">
              <summary className="cursor-pointer font-semibold text-teal">Selecionar territórios deste resultado</summary>
              <p className="my-2">Marque os territórios que deseja reutilizar. O resultado calculado permanece inalterado.</p>
              <div className="max-h-48 overflow-auto rounded-lg border border-line p-2">
                {resultMembers.map(item=><label key={item.id} className="flex min-h-10 items-center gap-2 px-2 py-2">
                  <input type="checkbox" checked={territoryIds.includes(item.id)} disabled={running || inspecting}
                    onChange={()=>changeTerritories(territoryIds.includes(item.id) ? territoryIds.filter(id=>id!==item.id) : [...territoryIds,item.id])}/>{item.label}
                </label>)}
              </div>
            </details>}
            {resultOperation === "nearest" && !!nearestMembers.length && historical?.sourceKey===sourceKey && !historical.invalidReason &&
              <details className="no-print my-3 text-xs">
              <summary className="cursor-pointer font-semibold text-amber-900">Reutilizar as referências deste resultado</summary>
              <p className="my-2">{nearestMembers.length} referências ({nearestMetadata?.conjunto_referencias?.forma === "CRITERIO"
                ? "definidas pelo critério" : "lista explícita"}). O resultado calculado permanece inalterado.</p>
              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={running || inspecting} onClick={()=>{setReferenceMode("list");setReferenceIds(nearestMembers);}}
                  className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-amber-900 disabled:opacity-40">Usar como lista de referências</button>
                <button type="button" disabled={running || inspecting} onClick={()=>changeTerritories(nearestMembers)}
                  className="rounded-lg border border-blue-200 bg-white px-3 py-2 text-teal disabled:opacity-40">Usar como municípios-alvo</button>
              </div>
            </details>}
            <p className="mt-2 text-sm leading-6 text-slate-500">{result.description}</p>
            {result.metrics.length > 0 && <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {result.metrics.map(metric => <div key={metric.label} className="rounded-2xl border border-line bg-slate-50 px-5 py-5"><p className="text-xs font-medium text-slate-500">{metric.label}</p><p className="mt-2 text-2xl font-bold text-ink">{pretty(metric.value)}</p></div>)}
            </div>}
            {resultOperation === "distribution" && result.detail_rows && <DistributionResults
              summary={result.rows} detail={result.detail_rows} onExport={exportCsv}/>}
            {resultOperation !== "distribution" && plot && <div className="mt-7 rounded-2xl border border-line p-4 sm:p-6">
              <div className="mb-4 flex items-center gap-2"><BarChart3 size={18} className="text-teal"/><h4 className="text-sm font-bold text-ink">Visualização dos primeiros 12 registros</h4></div>
              {/* O tooltip oculto preserva a posição anterior; sem recorte, estende a página ao estreitar a janela.
                  A largura máxima mantém o tooltip visível dentro da área de plotagem (eixo Y + margens). */}
              <div className="h-[280px] w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
                <BarChart data={plot.values} margin={{top:5,right:12,bottom:35,left:0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9eff4" vertical={false}/>
                  <XAxis dataKey="name" tick={{fontSize:10,fill:"#668094"}} interval={0} angle={-27} textAnchor="end" height={65}/>
                  <YAxis tick={{fontSize:11,fill:"#668094"}} width={48}/>
                  <Tooltip formatter={(v: number) => shortNum(v)} wrapperStyle={{maxWidth: "calc(100% - 72px)"}} contentStyle={{whiteSpace: "normal"}}/>
                  <Bar dataKey="value" name={plot.numeric} fill="#15919b" radius={[5,5,0,0]} maxBarSize={48}/>
                </BarChart>
              </ResponsiveContainer></div>
            </div>}
            {resultOperation !== "distribution" && result.rows.length > 0 && <div className="mt-7 overflow-hidden rounded-2xl border border-line">
              <div className="flex items-center justify-between border-b border-line px-5 py-4"><h4 className="text-sm font-bold text-ink">Tabela detalhada</h4><span className="text-xs text-slate-400">{result.total_rows} linhas · até 150 exibidas</span></div>
              <div className="max-h-[520px] overflow-auto"><table className="data-table w-full">
                <thead className="sticky top-0 bg-slate-50"><tr>{Object.keys(result.rows[0]).map(k=><th key={k}>{k}</th>)}</tr></thead>
                <tbody>{result.rows.slice(0,150).map((row,i)=><tr key={i}>{Object.keys(result.rows[0]).map(k=><td key={k}>{pretty(row[k])}</td>)}</tr>)}</tbody>
              </table></div>
            </div>}
            {result.notes.length > 0 && <div className="mt-6 rounded-xl border border-cyan-100 bg-cyan-50/70 p-5">
              <h4 className="flex items-center gap-2 text-sm font-bold text-ink"><SearchCheck size={17} className="text-teal"/> Método e limitações</h4>
              <ul className="mt-3 space-y-2 text-xs leading-6 text-slate-600">{result.notes.map((note,i)=><li key={i}>{note}</li>)}</ul>
            </div>}
            {resultOperation === "temporal" && result.detail_rows && <details className="mt-4 text-xs">
              <summary className="cursor-pointer font-semibold text-teal">Consultar competências da série temporal</summary>
              <button type="button" onClick={()=>exportCsv(result.detail_rows!)} className="no-print my-2 rounded-lg border px-3 py-2">Exportar série CSV</button>
              <div tabIndex={0} role="region" aria-label="Competências da série temporal" className="max-h-72 overflow-auto"><table className="data-table w-full"><thead><tr>{Object.keys(result.detail_rows[0] || {}).map(key=><th key={key}>{key}</th>)}</tr></thead>
                <tbody>{result.detail_rows.slice(0,150).map((row,index)=><tr key={index}>{Object.values(row).map((value,i)=><td key={i}>{pretty(value)}</td>)}</tr>)}</tbody></table></div>
            </details>}
            {historical && !historical.invalidReason && <details className="no-print mt-4 text-xs text-slate-500">
              <summary className="cursor-pointer">Registrar correção que invalida este resultado</summary>
              <label className="mt-2 block">Motivo factual da invalidação
                <input value={invalidationReason} onChange={e=>setInvalidationReason(e.target.value)} maxLength={500}
                  className="mt-1 w-full rounded-lg border p-2"/></label>
              <button type="button" disabled={!invalidationReason.trim()} className="mt-2 rounded-lg border px-3 py-2 text-rose-700 disabled:opacity-40"
                onClick={()=>{setHistory(previous=>previous.map(item=>item.result.result_id===result.result_id ? {...item,invalidReason:invalidationReason.trim()} : item));setInvalidationReason("");}}>Invalidar este resultado</button>
            </details>}
          </div>}
        </div>
      </section>

  </>) : null;

  return <div className="min-h-screen bg-canvas">
    {!privacy.accepted && <SessionPrivacy onAccept={privacy.accept}/>}
    <input ref={inputRef} disabled={!privacy.accepted} type="file" accept=".csv,.xls,.xlsx" className="sr-only"
      aria-label="Importar arquivo de dados"
      onChange={e => {const next=e.target.files?.[0];e.target.value = "";void chooseFile(next);}}/>
    <aside className="no-print fixed inset-y-0 left-0 z-40 hidden w-[235px] flex-col bg-[#102740] px-4 py-6 text-white lg:flex">
      <div className="flex items-center gap-3 px-2">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white"><BrandAvatar size={39}/></span>
        <div><p className="text-sm font-bold leading-tight">Agente Diagnóstico Territorial</p>
          <p className="mt-1 text-[10px] leading-4 text-slate-300">Força de Trabalho na Saúde</p></div>
      </div>
      <nav aria-label="Navegação principal" className="mt-12 space-y-1">
        {sideLink("Início", "home", Home)}
        {sideLink("Nova análise", "home", MessageCircle, "assistente")}
        {sideLink("Tipos de análise", "home", Grid2X2, "analises")}
        {sideLink("Resultados", "home", BarChart3, "resultados")}
      </nav>
    </aside>
    <div className="min-w-0 lg:pl-[235px]">
      <header className="no-print sticky top-0 z-30 flex items-center justify-between border-b border-line bg-white/95 px-4 py-3 backdrop-blur-xl lg:hidden">
        <div className="flex items-center gap-2.5">
          <span className="rounded-xl bg-slate-50 p-1"><BrandAvatar size={36}/></span>
          <div><p className="text-xs font-bold text-ink">Agente Diagnóstico Territorial</p>
          <p className="text-[10px] text-slate-500">Força de Trabalho na Saúde</p></div>
        </div>
        <button type="button" aria-label={mobileMenuOpen ? "Fechar menu" : "Abrir menu"} aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen(v => !v)}
          className="rounded-xl border border-line p-2 text-ink">{mobileMenuOpen ? <X size={21}/> : <Menu size={21}/>}</button>
        {mobileMenuOpen && <nav className="absolute left-3 right-3 top-[69px] space-y-1 rounded-2xl bg-[#102740] p-3 shadow-xl">
          {sideLink("Início", "home", Home)}
          {sideLink("Nova análise", "home", MessageCircle, "assistente")}
          {sideLink("Tipos de análise", "home", Grid2X2, "analises")}
          {sideLink("Resultados", "home", BarChart3, "resultados")}
        </nav>}
      </header>
      {serverStatus === "offline" && <div role="status" className="no-print mx-auto mt-3 max-w-[1260px] rounded-lg bg-rose-50 px-4 py-2 text-xs text-rose-800">Serviço de análise temporariamente indisponível.</div>}
      <main id="inicio" className="mx-auto max-w-[1330px] px-4 pb-16 pt-6 sm:px-7 lg:px-10">
      <div className={page === "home" ? "" : "hidden"}>
      <WelcomeHero onChat={() => navigate("home", "assistente")} onImport={() => inputRef.current?.click()}/>
      <AnalysisAssistant
        apiBase={API}
        privacyAccepted={privacy.accepted}
        file={file}
        dataset={usingBrazil ? "brazil" : ""} scope={inspection?.source?.scope || "auto"}
        datasetVersion={inspection?.source?.version || ""}
        sheet={sheet}
        mapping={mapping}
        options={semanticOptions()}
        contextReady={!!inspection && !inspection.requires_sheet && !!preflight && !preflighting && !inspecting}
        contextVersion={JSON.stringify({
          file: file?.name, modified: file?.lastModified, size: file?.size,
          usingBrazil, datasetVersion: sourceVersion, sourceGeneration, sheet
        })}
        validationVersion={JSON.stringify({mapping, options: semanticOptions(), scope: inspection?.source?.scope})}
        features={FEATURES}
        active={active}
        selecting={inspecting}
        onSelectAnalysis={(operation,proposal)=>{
          if(!proposal)setRequestText("Análise de " + ANALYSIS_LABELS[operation]);
          selectAnalysis(operation,proposal);
        }}
        onRequest={setRequestText}
        onExplore={exploreMessage}
        selection={selectionContent}
        sourceChoice={sourceChoice}
        sourceReady={!!inspection && !inspection.requires_sheet && !inspecting}
        sourceSummary={usingBrazil
          ? inspection && !inspecting ? "Os dados do Brasil já estão disponíveis. Escolha uma análise; ajustaremos a abrangência quando necessário." : "Estou preparando os dados do Brasil."
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
