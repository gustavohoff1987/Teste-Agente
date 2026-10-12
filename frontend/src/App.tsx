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
import SessionPrivacy, { useSessionPrivacy } from "./SessionPrivacy";
import type { Multiplicity, ResolutionOptions } from "./DataResolution";
import type { LucideIcon } from "lucide-react";
import {
  ArrowDownToLine, ArrowRight, BarChart3, Calculator, CheckCircle2,
  Home, Menu, X, MessageCircle, Grid2X2,
  ChevronDown, ClipboardList, Clock3, Database, Download, FileBarChart2, FileSpreadsheet,
  FileUp, FolderUp, Bot, Info, Layers3, ListFilter,
  LoaderCircle, MapPinned, MoveRight, RefreshCw, SearchCheck, Settings2, ShieldCheck,
  Sparkles, TrendingUp, UploadCloud, UsersRound, XCircle
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis
} from "recharts";

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
type Requirement = { status: "met" | "needs_confirmation" | "missing"; title: string; detail: string };
type Capability = { status: "available" | "needs_confirmation" | "unavailable"; reasons: string[]; requirements: Requirement[] };
type Preflight = {
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
  source?: { dataset: string; label: string; scope: "national" | "municipal"; version: string;
    default_scopes: Record<Operation, "national" | "municipal"> };
};
type Metric = { label: string; value: string | number };
type AnalysisResult = { title: string; description: string; rows: Record<string, unknown>[]; total_rows: number; metrics: Metric[]; notes: string[]; metadata: Record<string, unknown>; detail_rows?: Record<string, unknown>[] };
type Feature = { id: Operation; title: string; detail: string; icon: LucideIcon; tone: string };

const API = import.meta.env.VITE_API_BASE_URL || "";

async function readApiResponse(response: Response): Promise<any> {
  const raw = await response.text();
  let body: any;
  try { body = JSON.parse(raw); }
  catch {
    throw new Error("O servidor retornou uma resposta inválida (HTTP " + response.status + "). Verifique as janelas do Python e do Vite.");
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
    return "Não foi possível alcançar o motor Python. Confirme que o FastAPI está ativo na porta 8000 e a interface Vite na porta 5173.";
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
  { id: "report", title: ANALYSIS_LABELS.report, detail: "Consolidação, tabelas e exportações", icon: FileBarChart2, tone: "slate" }
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
  const [step, setStep] = useState(0);
  const steps = useRef<Partial<Record<Operation, number>>>({});
  const [scopeNotice, setScopeNotice] = useState("");
  const [preflightAttempt, setPreflightAttempt] = useState(0);
  const [active, setActive] = useState<Operation | null>(null);
  const [inlineConfirmed, setInlineConfirmed] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [serverStatus, setServerStatus] = useState<"checking" | "online" | "offline">("checking");
  const [periodFilter, setPeriodFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [reference, setReference] = useState("");
  const [crs, setCrs] = useState("");
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
      objectDraft, quantiles, distributionIndicator };
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
    setPeriodFilter(o.period_filter); setCategoryFilter(o.category_filter); setReference(o.reference_territory);
    setResolutions(saved.resolutions); setConfirmedNoOverlap(o.no_overlap_confirmed); setCrs(o.crs);
    setQuantiles(saved.quantiles); setDistributionIndicator(saved.distributionIndicator);
    setTemporalIndicator(o.temporal_indicator); setReportIndicator(o.report_indicator);
  }

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const selectedFeature = FEATURES.find(f => f.id === active);
  const plot = useMemo(() => {
    if (!result?.rows.length) return null;
    const keys = Object.keys(result.rows[0]);
    const numeric = ["Densidade por 1.000", "Quantidade", "Variação (%)", "Rotatividade (%)", "Distância (km)", "Unidades"].find(k => keys.includes(k)) || keys.find(k => result.rows.some(r => typeof r[k] === "number"));
    const category = keys.includes("Classe") ? "Classe" : keys.find(k => result.rows.some(r => typeof r[k] === "string"));
    if (!numeric || !category) return null;
    return { numeric, category, values: result.rows.slice(0, 12).map(r => ({ name: String(r[category] ?? "").slice(0, 35), value: typeof r[numeric] === "number" ? r[numeric] : null })) };
  }, [result]);

  async function inspectFile(nextFile: File | null, nextSheet = "", level = "auto", operation = "", preserve = false) {
    if (!privacy.accepted) return;
    if (!preserve) setSourceGeneration(value => value + 1);
    const previous = preserve && inspection?.source ? { info: inspection, saved: snapshotPreparation() } : null;
    if (previous) scopeDrafts.current[previous.info.source!.version + ":" + previous.info.source!.scope] = previous.saved;
    const currentUpload = ++uploadRevision.current;
    revision.current += 1;
    setInspecting(true);
    setUploadError("");
    setError("");
    setResult(null);
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
      setConfirmedRoles([]);
      setFtsScopeConfirmed(false);
      setSinglePeriodConfirmed(false);
      setCountUnit("");
      setCustomCountUnit("");
      setPopulationAligned(false);
      setTemporalCompared(false);
      setTerritoryStable(false);
      setLongitudinalIdentity(false);
      setIdentityCountConfirmed(false);
      setCategoryConstant("");
      setObjectDraft(details.suggested_category_constant || "");
      setObjectConfirmed(false);
      setPreflight(details.preflight);
      setPreflightError("");
      setServerStatus("online");
      setPeriodFilter("");
      setCategoryFilter("");
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
    setResult(null);
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
    setUsingBrazil(true); setInlineConfirmed(false); setFile(null); setSheet(""); setBrazilLevel("auto");
    void inspectFile(null, "", "auto", active || "");
  }
  function selectAnalysis(operation: Operation) {
    if (active) steps.current[active] = step;
    setStep(steps.current[operation] || 0);
    setActive(operation); setResult(null); setError(""); setInlineConfirmed(false);
    if (usingBrazil) {
      const nextScope = brazilLevel === "auto" ? inspection?.source?.default_scopes[operation] : brazilLevel;
      if (!nextScope || nextScope !== inspection?.source?.scope) void inspectFile(null, "", brazilLevel, operation, true);
    }
  }
  function semanticOptions() {
    return {
      ...resolutions,
      hierarchy_columns: hierarchyColumns,
      period_filter: periodFilter, category_filter: categoryFilter,
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
      object_confirmed: objectConfirmed
    };
  }
  function associateColumn(column: string, role: Role | "") {
    if (role === "count") setCountUnit("");
    if (role === "identity") { setIdentityCountConfirmed(false); setLongitudinalIdentity(false); }
    if (role === "period") { setPopulationAligned(false); setTemporalCompared(false); setTerritoryStable(false); }
    if (role === "territory" || role === "territory_id") {
      setPopulationAligned(false); setTerritoryStable(false); setReference("");
      setConfirmedNoOverlap(false); setResolutions(previous => ({number_format: previous.number_format}));
    }
    const previouslyAssociated = (Object.entries(mapping).find(([, value]) => value === column) || [])[0] as Role | undefined;
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
    setResult(null);
    setError("");
  }
  async function run(op: Operation) {
    if (!privacy.accepted) return;
    setActive(op); setResult(null); setError("");
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
        : "A importação não foi concluída. Confira a mensagem na área de upload antes de executar a análise.");
      document.getElementById("dados")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    setUploadError("");
    setRunning(true);
    const currentRevision = revision.current;
    const form = new FormData();
    appendSource(form); form.append("operation", op);
    form.append("mapping", JSON.stringify(mapping));
    form.append("options", JSON.stringify(semanticOptions()));
    try {
      const response = await fetch(API + "/api/analyze", { method: "POST", body: form });
      const body = await readApiResponse(response);
      if (currentRevision !== revision.current) return;
      setResult(body as AnalysisResult);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    } catch (exc) {
      if (currentRevision !== revision.current) return;
      setError(readableError(exc));
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    }
    finally { setRunning(false); }
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
  // O servidor recalcula a matriz após qualquer associação ou confirmação.
  // Nenhuma habilitação é decidida apenas no navegador.
  useEffect(() => {
    revision.current += 1;
    setResult(null);
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
      periodFilter, categoryFilter, populationAligned, temporalCompared, territoryStable,
      longitudinalIdentity, identityCountConfirmed, categoryConstant, objectConfirmed,
      ftsScopeConfirmed, singlePeriodConfirmed, reference, crs, confirmedNoOverlap, resolutions, quantiles, distributionIndicator, temporalIndicator, reportIndicator, hierarchyColumns]);

  useEffect(() => { revision.current += 1; setResult(null); setError(""); }, [active]);

  const sideLink = (label: string, view: "home" | "results", Icon: LucideIcon, target?: string) =>
    <button type="button" onClick={() => navigate(view, target)}
      className={["flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition",
        page === view && !target ? "bg-blue-600 text-white" : "text-slate-200 hover:bg-white/10 hover:text-white"].join(" ")}>
      <Icon size={18}/>{label}
    </button>;

  const visibleRequirements = preparationRequirements(active ? preflight?.capabilities[active]?.requirements || [] : []);

  const sourceChoice = <div id="dados" className="mt-3 space-y-3">
    <div className="grid gap-2 sm:grid-cols-2">
      <button type="button" onClick={chooseBrazil} disabled={!privacy.accepted || inspecting}
        className={"flex items-center gap-3 rounded-xl border px-3 py-3 text-left text-sm transition hover:border-blue-400 disabled:opacity-40 " +
          (usingBrazil ? "border-blue-500 bg-blue-50" : "border-line bg-white")}>
        <Database size={20} className="shrink-0 text-teal"/>
        <span><strong className="block">Usar dados do Brasil</strong><small className="text-slate-500">Fontes nacional e municipal</small></span>
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
    <input ref={inputRef} disabled={!privacy.accepted} type="file" accept=".csv,.xls,.xlsx" className="sr-only"
      onChange={e => {const next=e.target.files?.[0];e.target.value = "";void chooseFile(next);}}/>
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
              onChange={e => { const level = e.target.value as typeof brazilLevel; setBrazilLevel(level); const resolved = level === "auto" ? inspection.source?.default_scopes[active || "density"] : level; if (resolved !== inspection.source?.scope) void inspectFile(null, "", level, active || "", true); }}>
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
              setResult(null);
            }}
            onSelectCode={column => {
              if(column) associateColumn(column, "territory_id");
              else {setMapping(p => ({...p, territory_id: ""})); setConfirmedRoles(p => p.filter(role => role !== "territory_id"));setResult(null);}
            }}
            onConfirmCode={() => setConfirmedRoles(p => [...new Set<Role>([...p, "territory_id"])])}
            onSelect={(role, column) => {
              if (column) associateColumn(column, role);
              else {
                setMapping(prev => ({...prev, [role]: ""}));
                setConfirmedRoles(prev => prev.filter(x => x !== role));
                setResult(null);
              }
              if (role === "category") {
                setObjectConfirmed(false);
                setCategoryConstant("");
              }
            }}
            onConfirmRole={role => {
              setConfirmedRoles(prev => [...new Set([...prev, role])]);
              setResult(null);
            }}
            onDraft={value => {
              setObjectDraft(value);
              setObjectConfirmed(false);
              setCategoryConstant("");
              setResult(null);
            }}
            onConfirmObject={() => {
              if (!mapping.category) setCategoryConstant(objectDraft.trim());
              else setConfirmedRoles(prev => [...new Set<Role>([...prev, "category"])]);
              setObjectConfirmed(true);
              setResult(null);
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
              onChange={v => {setPeriodFilter(v); setResult(null);}}/>
            <SelectField label="Filtrar por categoria" value={categoryFilter}
              options={preflight?.values.categories || inspection.categories}
              onChange={v => {setCategoryFilter(v); setResult(null);}}/>
            {(active === "temporal" || active === "report") && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
              {active === "temporal" ? "Indicador da evolução temporal" : "Indicador do relatório"}
              <select aria-label={active === "temporal" ? "Indicador da evolução temporal" : "Indicador do relatório"}
                className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={active === "temporal" ? temporalIndicator : reportIndicator}
                onChange={e => { (active === "temporal" ? setTemporalIndicator : setReportIndicator)(e.target.value as "" | "density" | "quantity"); setResult(null); }}>
                <option value="">Selecione o indicador</option>
                <option value="quantity">Quantidade na unidade declarada</option>
                <option value="density">Densidade por 1.000 habitantes</option>
              </select>
            </label>}
            {active === "distribution" && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
              Indicador da distribuição
              <select aria-label="Indicador da distribuição" className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={distributionIndicator} onChange={e => {setDistributionIndicator(e.target.value as "" | "density" | "quantity");setResult(null);}}>
                <option value="">Selecione o indicador</option>
                <option value="density">Densidade por 1.000 habitantes</option>
                <option value="quantity">Quantidade na unidade declarada</option>
              </select>
            </label>}
          </div>
        </div>}

            <DataResolution operation={active} columns={inspection.columns}
            mapping={mapping} diagnostic={preflight?.multiplicity} options={resolutions} setOptions={setResolutions}
            periods={preflight?.values.periods || inspection.periods}
            selectIdentity={column => {if(column) associateColumn(column, "identity"); else setMapping(p => ({...p, identity: ""}));}}
            identityConfirmed={identityCountConfirmed} confirmIdentity={setIdentityCountConfirmed}
            confirmCoordinates={() => setConfirmedRoles(p => [...new Set<Role>([...p, "latitude", "longitude"])])}/>
            <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50/40 p-4 sm:p-5">
              <h4 className="text-sm font-bold text-ink">Completar informações para esta análise</h4>
              <p className="mt-1 text-xs leading-5 text-slate-600">Preencha somente os dados que correspondem à estrutura real da sua base. Uma confirmação não substitui informações ausentes.</p>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {active !== "spatial" && active !== "rotation" && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Onde estão os quantitativos dos profissionais?
                    <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.count || ""} onChange={e => {
                        if (e.target.value) associateColumn(e.target.value, "count");
                        else { setMapping(prev=>({...prev,count:""})); setConfirmedRoles(prev=>prev.filter(x=>x!=="count"));setResult(null); }
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
                      aria-label="O que o quantitativo representa?" value={countUnit} onChange={e => {setCountUnit(e.target.value);setResult(null);}}>
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
                {(["density","comparisons","ranking","aggregate"].includes(active) || (active === "distribution" && distributionIndicator === "density") || (active === "temporal" && temporalIndicator === "density") || (active === "report" && reportIndicator === "density")) && <>
                  <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">
                    Coluna com a população correspondente
                    <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                      value={mapping.population || ""} onChange={e => {
                        if (e.target.value) associateColumn(e.target.value, "population");
                        else {setMapping(prev=>({...prev,population:""}));setConfirmedRoles(prev=>prev.filter(x=>x!=="population"));setResult(null);}
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
                {active === "spatial" && <>
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
                  <SelectField label="Território de referência" value={reference}
                    options={preflight?.values.territories || []} onChange={setReference}/>
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
      scope={inspection.source?.scope || "municipal"}
      onScope={v=>{setBrazilLevel(v);setInlineConfirmed(false);if(v!==inspection.source?.scope)void inspectFile(null,"",v,active,true);}}
      columns={inspection.columns}
      mapping={mapping}
      onField={(role:FieldRole,column)=>{setInlineConfirmed(false);
        if(column)associateColumn(column,role as Role);
        else {setMapping(p=>({...p,[role]:""}));setConfirmedRoles(p=>p.filter(r=>r!==role));setResult(null);}
        if(role==="population")setPopulationAligned(false);
      }}
      countUnit={countUnit}
      onCountUnit={v=>{setCountUnit(v);setInlineConfirmed(false);}}
      customCountUnit={customCountUnit}
      onCustomCountUnit={setCustomCountUnit}
      indicator={active==="distribution"?distributionIndicator:active==="temporal"?temporalIndicator:reportIndicator}
      onIndicator={v=>{
        if(active==="distribution")setDistributionIndicator(v);
        if(active==="temporal")setTemporalIndicator(v);
        if(active==="report")setReportIndicator(v);
        setInlineConfirmed(false);
      }}
      periodFilter={periodFilter}
      periods={preflight?.values.periods || inspection.periods}
      onPeriod={v=>{setPeriodFilter(v);setInlineConfirmed(false);}}
      categoryFilter={categoryFilter}
      categories={preflight?.values.categories || inspection.categories}
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
      advanced={advancedPreparation}
    /></div> : null;
  const resultContent = (result || running || error) ? (<>
      <section id="resultados" ref={resultsRef} className="section-anchor mt-4 pt-3">
        <button type="button" onClick={() => document.getElementById("preparacao-conversacional")?.scrollIntoView({behavior:"smooth"})}
          className="no-print mb-5 inline-flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-xs font-semibold text-teal hover:bg-blue-50">
          <ArrowRight size={15} className="rotate-180"/> Voltar às opções
        </button>
        <SectionHeader eyebrow="03 · Interpretar" title="Resultados do diagnóstico" description="Os resultados são calculados no motor Python e apresentados com método, cobertura e limitações explícitas."/>
        <div className="rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7 print-content">
          <div className="no-print flex flex-wrap items-start justify-between gap-4 border-b border-line pb-6">
            <div className="flex items-start gap-3">
              <span className="rounded-xl bg-teal-50 p-2.5 text-teal">{selectedFeature ? <selectedFeature.icon size={22}/> : <ClipboardList size={22}/>}</span>
              <div><h3 className="font-bold text-ink">{selectedFeature ? selectedFeature.title : "Selecione uma análise"}</h3><p className="mt-1 text-xs text-slate-500">{selectedFeature?.detail || "Os resultados aparecerão aqui após a execução."}</p></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button disabled={!result} onClick={() => result && exportCsv(result.rows)} className="flex items-center gap-1.5 rounded-xl border border-line px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-40"><ArrowDownToLine size={14}/> {active === "distribution" ? "Resumo CSV" : "CSV"}</button>
              <button disabled={!result} onClick={() => result && downloadText("metodo_diagnostico.json", JSON.stringify({title: result.title, notes: result.notes, ...result.metadata}, null, 2), "application/json")} className="rounded-xl border px-3 py-2 text-xs disabled:opacity-40">Método e parâmetros</button>
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
              O motor analítico está processando a base. Os resultados aparecerão aqui ao concluir.
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
            <p className="mt-2 text-sm leading-6 text-slate-500">{result.description}</p>
            {result.metrics.length > 0 && <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {result.metrics.map(metric => <div key={metric.label} className="rounded-2xl border border-line bg-slate-50 px-5 py-5"><p className="text-xs font-medium text-slate-500">{metric.label}</p><p className="mt-2 text-2xl font-bold text-ink">{pretty(metric.value)}</p></div>)}
            </div>}
            {active === "distribution" && result.detail_rows && <DistributionResults
              summary={result.rows} detail={result.detail_rows} onExport={exportCsv}/>}
            {active !== "distribution" && plot && <div className="mt-7 rounded-2xl border border-line p-4 sm:p-6">
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
            {active !== "distribution" && result.rows.length > 0 && <div className="mt-7 overflow-hidden rounded-2xl border border-line">
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
          </div>}
        </div>
      </section>

  </>) : null;

  return <div className="min-h-screen bg-canvas">
    {!privacy.accepted && <SessionPrivacy onAccept={privacy.accept}/>}
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
        onSelectAnalysis={selectAnalysis}
        sourceChoice={sourceChoice}
        sourceReady={!!inspection && !inspection.requires_sheet && !inspecting}
        sourceSummary={usingBrazil
          ? inspection && !inspecting ? "As fontes do Brasil e dos municípios estão disponíveis. Escolha uma análise; ajustaremos a abrangência quando necessário." : "Estou preparando as fontes do Brasil."
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
