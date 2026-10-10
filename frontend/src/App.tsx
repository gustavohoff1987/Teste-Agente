import { useEffect, useMemo, useRef, useState } from "react";
import ContextConfig from "./ContextConfig";
import RequirementChecklist from "./RequirementChecklist";
import DataResolution from "./DataResolution";
import DistributionResults, { displayPeriod } from "./DistributionResults";
import AnalysisAssistant from "./AnalysisAssistant";
import BrandAvatar from "./BrandAvatar";
import AnalysisCarousel from "./AnalysisCarousel";
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
  Sparkles, Table2, TrendingUp, UploadCloud, UsersRound, XCircle
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis
} from "recharts";

type Role = "territory" | "territory_id" | "period" | "category" | "count" | "population" | "latitude" | "longitude" | "identity";
type Operation = "density" | "counts" | "distribution" | "comparisons" | "temporal" | "aggregate" | "spatial" | "ranking" | "rotation" | "report";
type Mapping = Partial<Record<Role, string>>;
type FieldStatus = "recognized" | "confirmed" | "proposed" | "unmapped";
type ColumnProfile = {
  name: string; type: string; missing: number; suspicious_header: boolean;
  proposal: { role: Role; status: "recognized" | "proposed"; evidence: string }[];
};
type Requirement = { status: "met" | "needs_confirmation" | "missing"; title: string; detail: string };
type Capability = { status: "available" | "needs_confirmation" | "unavailable"; reasons: string[]; requirements: Requirement[] };
type Preflight = {
  multiplicity: Multiplicity;
  capabilities: Record<Operation, Capability>;
  field_states: Record<Role, { status: FieldStatus; column: string; message: string; evidence?: string }>;
  values: {territories: string[]; periods: string[]; categories: string[]};
  profile: {row_count: number; column_count: number; recognized_roles: number};
};
type Inspection = {
  requires_sheet: boolean; sheets: string[]; columns: string[]; row_count: number;
  suggested_mapping: Mapping; periods: string[]; categories: string[]; territories: string[];
  column_profiles: ColumnProfile[]; preflight: Preflight | null; suggested_category_constant: string;
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
  { id: "density", title: "Densidade", detail: "Profissionais por 1.000 habitantes", icon: Calculator, tone: "teal" },
  { id: "counts", title: "Quantitativos", detail: "Contagens absolutas da força de trabalho", icon: UsersRound, tone: "indigo" },
  { id: "distribution", title: "Distribuição", detail: "Quantis, posições e frequências", icon: BarChart3, tone: "violet" },
  { id: "comparisons", title: "Comparações", detail: "Territórios, categorias e períodos", icon: MoveRight, tone: "orange" },
  { id: "temporal", title: "Evolução temporal", detail: "Mudanças e tendências", icon: TrendingUp, tone: "blue" },
  { id: "aggregate", title: "Agregações", detail: "Conjuntos territoriais e indicadores", icon: Layers3, tone: "emerald" },
  { id: "spatial", title: "Análise espacial", detail: "Distâncias e referências geográficas", icon: MapPinned, tone: "rose" },
  { id: "ranking", title: "Recortes e rankings", detail: "Seleções, posições e ordenações", icon: ListFilter, tone: "amber" },
  { id: "rotation", title: "Rotatividade", detail: "Permanência da coorte inicial", icon: RefreshCw, tone: "cyan" },
  { id: "report", title: "Relatórios", detail: "Consolidação, tabelas e exportações", icon: FileBarChart2, tone: "slate" }
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
  const [page, setPage] = useState<"home" | "results">(() => ["#resultados", "#filtros-resultados"].includes(window.location.hash) ? "results" : "home");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [sheet, setSheet] = useState("");
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [mapping, setMapping] = useState<Mapping>({});
  const [inspecting, setInspecting] = useState(false);
  const [running, setRunning] = useState(false);
  const [active, setActive] = useState<Operation | null>(null);
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

  async function inspectFile(nextFile: File, nextSheet = "") {
    if (!privacy.accepted) return;
    const currentUpload = ++uploadRevision.current;
    setInspecting(true);
    setUploadError("");
    setError("");
    setResult(null);
    setInspection(null);
    const form = new FormData();
    form.append("file", nextFile);
    form.append("sheet", nextSheet);
    try {
      const response = await fetch(API + "/api/inspect", { method: "POST", body: form });
      const details = await readApiResponse(response) as Inspection;
      if (currentUpload !== uploadRevision.current) return;
      setInspection(details);
      setMapping(details.suggested_mapping);
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
    setFile(next);
    setSheet("");
    setActive(null);
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
  function semanticOptions() {
    return {
      ...resolutions,
      period_filter: periodFilter, category_filter: categoryFilter,
      reference_territory: reference, crs, quantile_count: quantiles,
      distribution_indicator: distributionIndicator,
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
    if (!file || !inspection || inspection.requires_sheet || inspecting) {
      setUploadError(inspection?.requires_sheet
        ? "Selecione uma aba do arquivo Excel para concluir a importação."
        : inspecting ? "Aguarde a conclusão do exame do arquivo."
        : "A importação não foi concluída. Confira a mensagem na área de upload antes de executar a análise.");
      document.getElementById("dados")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    setUploadError("");
    setRunning(true);
    navigate("results");
    const currentRevision = revision.current;
    const form = new FormData();
    form.append("file", file); form.append("sheet", sheet); form.append("operation", op);
    form.append("mapping", JSON.stringify(mapping));
    form.append("options", JSON.stringify(semanticOptions()));
    try {
      const response = await fetch(API + "/api/analyze", { method: "POST", body: form });
      const body = await readApiResponse(response);
      if (currentRevision !== revision.current) return;
      setResult(body as AnalysisResult);
      navigate("results");
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    } catch (exc) {
      if (currentRevision !== revision.current) return;
      setError(readableError(exc));
      navigate("results");
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    }
    finally { setRunning(false); }
  }
  function sampleCsv() {
    downloadText("modelo_dados_territoriais.csv",
      "Territorio;Ano;Categoria;Quantidade;Populacao;Latitude;Longitude\r\nMunicipio A;2024;Medicos;120;80000;-15.8;-47.9\r\nMunicipio B;2024;Medicos;65;65000;-16.2;-48.1\r\n",
      "text/csv;charset=utf-8");
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
    const onHashChange = () => setPage(["#resultados", "#filtros-resultados"].includes(window.location.hash) ? "results" : "home");
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
    if (!inspection || inspection.requires_sheet || !file) return;
    let cancelled = false;
    const controller = new AbortController();
    setPreflighting(true);
    setPreflightError("");
    const timer = window.setTimeout(async () => {
      const form = new FormData();
      form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      form.append("options", JSON.stringify({
        ...resolutions, quantile_count: quantiles,
        distribution_indicator: distributionIndicator,
        reference_territory: reference, crs,
        no_overlap_confirmed: confirmedNoOverlap,
        fts_scope_confirmed: ftsScopeConfirmed,
        single_period_confirmed: singlePeriodConfirmed,
        confirmed_roles: confirmedRoles,
        count_unit: countUnit,
        custom_count_unit: customCountUnit,
        period_filter: periodFilter,
        category_filter: categoryFilter,
        population_denominator_confirmed: populationAligned,
        temporal_comparability_confirmed: temporalCompared,
        territory_longitudinal_confirmed: territoryStable,
        longitudinal_identity_confirmed: longitudinalIdentity,
        identity_count_confirmed: identityCountConfirmed,
        category_constant: categoryConstant,
        require_object_confirmation: true,
        object_confirmed: objectConfirmed
      }));
      try {
        const response = await fetch(API + "/api/preflight", { method: "POST", body: form, signal: controller.signal });
        const next = await readApiResponse(response) as Preflight;
        if (!cancelled) setPreflight(next);
      } catch (exc) {
        if (!cancelled) { setPreflight(null); setPreflightError(readableError(exc)); }
      } finally {
        if (!cancelled) setPreflighting(false);
      }
    }, 250);
    return () => { cancelled = true; controller.abort(); window.clearTimeout(timer); };
  }, [inspection, file, sheet, mapping, confirmedRoles, countUnit, customCountUnit,
      periodFilter, categoryFilter, populationAligned, temporalCompared, territoryStable,
      longitudinalIdentity, identityCountConfirmed, categoryConstant, objectConfirmed,
      ftsScopeConfirmed, singlePeriodConfirmed, reference, crs, confirmedNoOverlap, resolutions, quantiles, distributionIndicator]);

  useEffect(() => { revision.current += 1; setResult(null); setError(""); }, [active]);

  const sideLink = (label: string, view: "home" | "results", Icon: LucideIcon, target?: string) =>
    <button type="button" onClick={() => navigate(view, target)}
      className={["flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition",
        page === view && !target ? "bg-blue-600 text-white" : "text-slate-200 hover:bg-white/10 hover:text-white"].join(" ")}>
      <Icon size={18}/>{label}
    </button>;

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
        {sideLink("Resultados", "results", BarChart3)}
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
          {sideLink("Resultados", "results", BarChart3)}
        </nav>}
      </header>
      {serverStatus === "offline" && <div role="status" className="no-print mx-auto mt-3 max-w-[1260px] rounded-lg bg-rose-50 px-4 py-2 text-xs text-rose-800">Serviço de análise temporariamente indisponível.</div>}
      <main id="inicio" className="mx-auto max-w-[1330px] px-4 pb-16 pt-6 sm:px-7 lg:px-10">
      <div className={page === "home" ? "" : "hidden"}>
      <WelcomeHero onChat={() => navigate("home", "assistente")} onImport={() => inputRef.current?.click()}/>
      <section id="dados" className="section-anchor mt-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-[20px] border border-blue-100 bg-blue-50/90 p-4 sm:p-5">
            <span className="mb-3 inline-flex rounded-xl bg-white p-2.5 text-blue-700"><Database size={23}/></span>
            <h2 className="text-sm font-bold text-ink sm:text-base">Usar dados do Brasil</h2>
            <p className="mt-1 min-h-[45px] text-xs leading-5 text-slate-600">
              Base nacional em preparação para uso no protótipo.
            </p>
            <span title="A base ainda não foi disponibilizada no projeto"
              className="mt-4 inline-flex w-full cursor-not-allowed justify-center rounded-xl border border-blue-200 bg-blue-100 px-3 py-3 text-xs font-semibold text-blue-800">
              Disponível em breve
            </span>
          </div>
          <div className="rounded-[20px] border border-emerald-100 bg-emerald-50/80 p-4 sm:p-5">
            <span className="mb-3 inline-flex rounded-xl bg-white p-2.5 text-emerald-700"><FileUp size={23}/></span>
            <h2 className="text-sm font-bold text-ink sm:text-base">Importar seus dados</h2>
            <p className="mt-1 min-h-[45px] text-xs leading-5 text-slate-600">
              Utilize dados de qualquer país ou território.
            </p>
            <input ref={inputRef} disabled={!privacy.accepted} type="file" accept=".csv,.xls,.xlsx" className="hidden"
              onChange={e => { const next = e.target.files?.[0]; e.target.value = ""; void chooseFile(next); }}/>
            <button type="button" onClick={() => inputRef.current?.click()}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-300 bg-white px-3 py-3 text-xs font-bold text-emerald-800 hover:bg-emerald-100">
              <UploadCloud size={16}/> Importar arquivo <span className="text-[10px] font-normal">CSV ou Excel</span>
            </button>
          </div>
          <div className="rounded-[20px] border border-amber-100 bg-amber-50/65 p-4 sm:p-5">
            <span className="mb-3 inline-flex rounded-xl bg-white p-2.5 text-amber-700"><Table2 size={23}/></span>
            <h2 className="text-sm font-bold text-ink sm:text-base">Estrutura dos dados</h2>
            <p className="mt-1 min-h-[45px] text-xs leading-5 text-slate-600">
              Baixe o modelo recomendado e preencha com seus dados.
            </p>
            <button type="button" onClick={sampleCsv}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-amber-200 bg-white px-3 py-3 text-xs font-bold text-amber-900 hover:bg-amber-100">
              <Download size={16}/> Baixar modelo CSV
            </button>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">O modelo é recomendado, mas não obrigatório. A compatibilidade depende da análise escolhida.</p>
        {inspecting && <p role="status" className="mt-3 flex items-center gap-2 rounded-xl bg-cyan-50 px-4 py-3 text-xs text-teal">
          <LoaderCircle size={16} className="animate-spin"/> Examinando os dados. Aguarde...</p>}
        {uploadError && <p role="alert" className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
          <XCircle size={15} className="mr-2 inline"/>{uploadError}</p>}
        {inspection?.requires_sheet && <div className="mt-4 rounded-xl border border-amber-200 bg-white p-4">
          <label className="flex flex-col gap-2 text-xs font-semibold text-ink">Selecione a aba do arquivo Excel
            <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm"
              value={sheet} onChange={e=>{const next=e.target.value;setSheet(next);if(file&&next)void inspectFile(file,next);}}>
              <option value="">Selecione uma aba</option>
              {inspection.sheets.map(name=><option key={name} value={name}>{name}</option>)}
            </select>
          </label>
        </div>}
        {inspection && !inspection.requires_sheet && <div role="status" className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-emerald-200 bg-white px-4 py-3 text-xs text-emerald-800">
          <CheckCircle2 size={17}/>
          <strong>{file?.name || "Arquivo"} carregado</strong>
          <span className="text-slate-500">{shortNum(inspection.row_count)} registros · {inspection.columns.length} colunas</span>
          <button type="button" className="ml-auto font-semibold underline" onClick={()=>navigate("home","preparacao")}>Revisar campos</button>
        </div>}
      </section>

      <div className="analysis-workspace">
      <AnalysisCarousel<Operation> features={FEATURES} active={active}
        capabilities={preflight?.capabilities} checking={preflighting || inspecting} hasData={!!inspection && !inspection.requires_sheet}
        onSelect={operation => {
          setActive(operation);
          setResult(null);
          setError("");
        }}
        onRequirements={() => navigate("home", "requisitos")}/>
      <AnalysisAssistant
        apiBase={API}
        privacyAccepted={privacy.accepted}
        file={file}
        sheet={sheet}
        mapping={mapping}
        options={semanticOptions()}
        contextReady={!!inspection && !inspection.requires_sheet && !!preflight && !preflighting && !inspecting}
        contextVersion={JSON.stringify({
          file: file?.name, modified: file?.lastModified, size: file?.size,
          sheet, mapping, options: semanticOptions()
        })}
        onSelectAnalysis={operation => {
        setActive(operation);
        setResult(null);
        navigate("home", "requisitos");
      }}/>
      </div>
      <section id="preparacao" className="section-anchor mt-7">
        {inspection && !inspection.requires_sheet && <h2 className="mb-3 text-xl font-bold text-ink">Confira os dados carregados</h2>}
        {inspection && !inspection.requires_sheet && <>
          {preflighting && <p role="status" className="mt-4 flex items-center gap-2 text-xs text-teal"><LoaderCircle size={15} className="animate-spin"/> Conferindo as informações da base...</p>}
          {preflightError && <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{preflightError}</p>}
          <ContextConfig columns={inspection.columns} mapping={mapping}
            fieldStates={preflight?.field_states} categories={preflight?.values.categories || inspection.categories}
            suggestedCategory={inspection.suggested_category_constant} objectDraft={objectDraft}
            objectConfirmed={objectConfirmed}
            territoryCode={mapping.territory_id || ""}
            codeConfirmed={preflight?.field_states.territory_id?.status === "confirmed"}
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
        </>}
      </section>
      <section id="requisitos" className="section-anchor mt-7">
        {active && inspection && !inspection.requires_sheet && <div className="mb-4 rounded-2xl border border-line bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-bold text-ink">Parâmetros da análise</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <SelectField label="Filtrar por período" value={periodFilter}
              options={preflight?.values.periods || inspection.periods}
              onChange={v => {setPeriodFilter(v); setResult(null);}}/>
            <SelectField label="Filtrar por categoria" value={categoryFilter}
              options={preflight?.values.categories || inspection.categories}
              onChange={v => {setCategoryFilter(v); setResult(null);}}/>
            {active === "distribution" && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
              Indicador da distribuição
              <select aria-label="Indicador da distribuição" className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={distributionIndicator} onChange={e => {setDistributionIndicator(e.target.value as "" | "density" | "quantity");setResult(null);}}>
                <option value="">Selecione o indicador</option>
                <option value="density">Densidade por 1.000 habitantes</option>
                <option value="quantity">Quantidade absoluta de profissionais</option>
              </select>
            </label>}
          </div>
        </div>}
        {active && error && <p role="alert" className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800">{error}</p>}
        {active && <RequirementChecklist analysis={selectedFeature?.title || "esta análise"}
          status={!inspection || preflightError ? "unavailable" : !preflight || preflighting ? "loading" : preflight.capabilities[active]?.status || "unavailable"}
          requirements={preflightError ? [{status: "missing", title: "Verificação não concluída", detail: preflightError}] : preflight?.capabilities[active]?.requirements || (!inspection ? [
            {status: "missing", title: "Base de dados", detail: "Importe uma planilha para verificar os requisitos desta análise."}
          ] : [])}
          onExecute={() => { void run(active); }} executing={running}>
          {active === "distribution" && inspection && <button type="button" className="mt-4 inline-flex text-xs font-bold text-teal underline"
            onClick={() => navigate("results", "filtros-resultados")}>
            Escolher período, categoria e indicador da distribuição
          </button>}
          {inspection && !inspection.requires_sheet && <details
            key={active + ":" + (preflight?.capabilities[active]?.status || "loading")}
            open={preflight?.capabilities[active]?.status !== "available"}
            className="mt-5 rounded-xl border border-cyan-100 bg-slate-50/50 p-4">
            <summary className="cursor-pointer text-sm font-bold text-ink">
              Informações complementares
              <span className="ml-2 font-normal text-slate-600">
                {preflight?.capabilities[active]?.status === "available" ? "— concluídas (editar)" : "— conferir o que falta"}
              </span>
            </summary>
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
                {["density","comparisons","ranking","aggregate"].includes(active) && <>
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
                {active !== "spatial" && !mapping.period && <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                  <input type="checkbox" checked={singlePeriodConfirmed} onChange={e => setSinglePeriodConfirmed(e.target.checked)}/>
                  Confirmo que a base se refere a um único período
                </label>}
                {active !== "spatial" && <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                  <input type="checkbox" checked={ftsScopeConfirmed} onChange={e => setFtsScopeConfirmed(e.target.checked)}/>
                  Confirmo que os trabalhadores informados fazem parte da força de trabalho na saúde
                </label>}
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
                      <option value="">Não informado</option><option value="SIRGAS2000">SIRGAS2000</option><option value="WGS84">WGS84</option>
                    </select>
                  </label>
                  <SelectField label="Território de referência" value={reference}
                    options={preflight?.values.territories || []} onChange={setReference}/>
                </>}
                {active === "aggregate" && <>
                  <SelectField label="Selecionar período" value={periodFilter} options={preflight?.values.periods || []} onChange={v => {setPeriodFilter(v);setResult(null);}}/>
                  <SelectField label="Selecionar categoria" value={categoryFilter} options={preflight?.values.categories || []} onChange={v => {setCategoryFilter(v);setResult(null);}}/>
                  <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
                    <input type="checkbox" checked={confirmedNoOverlap} onChange={e => setConfirmedNoOverlap(e.target.checked)}/>
                    Declaro ausência de sobreposição das pessoas entre territórios, se desejar interpretar o total como pessoas únicas
                  </label>
                </>}
              </div>
              <button type="button" className="mt-4 text-xs font-bold text-teal underline"
                onClick={() => document.getElementById("associacoes")?.scrollIntoView({behavior:"smooth",block:"start"})}>
                Rever espaço, tempo e objeto
              </button>
            </div>
          </details>}
        </RequirementChecklist>}
      </section>
      </div>
      <section id="resultados" ref={resultsRef} className={["section-anchor pt-3", page === "results" ? "" : "hidden"].join(" ")}>
        <button type="button" onClick={() => navigate("home", "requisitos")}
          className="no-print mb-5 inline-flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-xs font-semibold text-teal hover:bg-blue-50">
          <ArrowRight size={15} className="rotate-180"/> Voltar à análise
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
          {inspection && !inspection.requires_sheet && <div id="filtros-resultados" className="no-print border-b border-line py-5">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div><h4 className="text-sm font-bold text-ink">Escolha o recorte da análise</h4>
              <p className="mt-1 text-xs leading-5 text-slate-600">Defina período e categoria. Para a distribuição, escolha também o indicador usado na classificação dos territórios.</p></div>
              {active && <span className="rounded-lg bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600">Os resultados são recalculados após executar / atualizar</span>}
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <SelectField label="Filtrar por período" value={periodFilter} options={preflight?.values.periods || inspection.periods} onChange={v => {setPeriodFilter(v); setResult(null);}}/>
            <SelectField label="Filtrar por categoria" value={categoryFilter} options={preflight?.values.categories || inspection.categories} onChange={v => {setCategoryFilter(v); setResult(null);}}/>
            {active === "distribution" && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">
              Indicador da distribuição
              <select aria-label="Indicador da distribuição" className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={distributionIndicator} onChange={e => {setDistributionIndicator(e.target.value as "" | "density" | "quantity");setResult(null);}}>
                <option value="">Selecione o indicador</option>
                <option value="density">Densidade de profissionais por 1.000 habitantes</option>
                <option value="quantity">Quantidade absoluta de profissionais</option>
              </select>
              <span className="font-normal leading-5 text-slate-500">A densidade exige população correspondente. Os quintis nunca misturam períodos e categorias.</span>
            </label>}
            {active === "spatial" && <>
              <SelectField label="Território de referência" value={reference} options={preflight?.values.territories || inspection.territories} onChange={setReference}/>
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">Referencial geodésico
                <select className="rounded-xl border border-line px-3 py-2.5 text-sm" value={crs} onChange={e=>setCrs(e.target.value)}><option value="">Não informado</option><option value="SIRGAS2000">SIRGAS2000</option></select></label>
            </>}
            {active === "aggregate" && <label className="col-span-2 flex items-center gap-2 self-center text-xs text-slate-700"><input type="checkbox" checked={confirmedNoOverlap} onChange={e=>setConfirmedNoOverlap(e.target.checked)}/> Declaro que não há sobreposição de pessoas nos territórios considerados</label>}
            </div>
          </div>}
          {active && inspection && !inspection.requires_sheet && preflight?.capabilities[active]?.status === "available" && <div className="no-print mt-5 flex justify-end">
            <button disabled={running} onClick={()=>{void run(active);}} className="flex items-center gap-2 rounded-xl bg-teal px-4 py-2.5 text-sm font-bold text-white hover:bg-ink disabled:opacity-50">
              {running ? <LoaderCircle size={16} className="animate-spin"/> : <Calculator size={16}/>} {running ? "Calculando..." : "Executar / atualizar análise"}</button>
          </div>}
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
              <div className="h-[280px] w-full"><ResponsiveContainer width="100%" height="100%">
                <BarChart data={plot.values} margin={{top:5,right:12,bottom:35,left:0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9eff4" vertical={false}/>
                  <XAxis dataKey="name" tick={{fontSize:10,fill:"#668094"}} interval={0} angle={-27} textAnchor="end" height={65}/>
                  <YAxis tick={{fontSize:11,fill:"#668094"}} width={48}/>
                  <Tooltip formatter={(v: number) => shortNum(v)}/>
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
      <footer className="no-print mt-14 flex flex-col items-start justify-between gap-3 border-t border-line pt-6 text-xs text-slate-400 sm:flex-row sm:items-center">
        <p>Agente Diagnóstico Territorial · Protótipo experimental v0.1</p>
      </footer>
      </main>
    </div>
  </div>;
}

export default App;
