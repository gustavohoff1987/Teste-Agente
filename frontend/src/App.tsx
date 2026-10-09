import { useEffect, useMemo, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowDownToLine, ArrowRight, ArrowUpRight, BarChart3, Calculator, CheckCircle2,
  ChevronDown, ClipboardList, Clock3, Database, Download, FileBarChart2, FileSpreadsheet,
  FileUp, Fingerprint, FolderUp, Bot, HelpCircle, Info, Layers3, ListFilter,
  LoaderCircle, MapPinned, MoveRight, RefreshCw, SearchCheck, Settings2, ShieldCheck,
  Sparkles, Table2, TrendingUp, UploadCloud, UsersRound, XCircle
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis
} from "recharts";

type Role = "territory" | "period" | "category" | "count" | "population" | "latitude" | "longitude" | "identity";
type Operation = "density" | "counts" | "distribution" | "comparisons" | "temporal" | "aggregate" | "spatial" | "ranking" | "rotation" | "report";
type Mapping = Partial<Record<Role, string>>;
type FieldStatus = "recognized" | "confirmed" | "proposed" | "unmapped";
type ColumnProfile = {
  name: string; type: string; missing: number; suspicious_header: boolean;
  proposal: { role: Role; status: "recognized" | "proposed"; evidence: string }[];
};
type Capability = { status: "available" | "needs_confirmation" | "unavailable"; reasons: string[] };
type Preflight = {
  capabilities: Record<Operation, Capability>;
  field_states: Record<Role, { status: FieldStatus; column: string; message: string; evidence?: string }>;
  profile: {row_count: number; column_count: number; recognized_roles: number};
};
type Inspection = {
  requires_sheet: boolean; sheets: string[]; columns: string[]; row_count: number;
  suggested_mapping: Mapping; periods: string[]; categories: string[]; territories: string[];
  column_profiles: ColumnProfile[]; preflight: Preflight | null; suggested_category_constant: string;
};
type Metric = { label: string; value: string | number };
type AnalysisResult = { title: string; description: string; rows: Record<string, unknown>[]; total_rows: number; metrics: Metric[]; notes: string[] };
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
  { key: "territory", label: "Território", help: "Município, polo, DSEI ou outro recorte declarado" },
  { key: "period", label: "Período", help: "Ano ou referência temporal" },
  { key: "category", label: "Categoria", help: "Profissão ou categoria da FTS" },
  { key: "count", label: "Quantidade", help: "Contagem com significado estabelecido" },
  { key: "population", label: "População", help: "Denominador territorial" },
  { key: "latitude", label: "Latitude", help: "Graus decimais" },
  { key: "longitude", label: "Longitude", help: "Graus decimais" },
  { key: "identity", label: "Identificador individual", help: "Apenas para contagem distinta ou coortes" }
];
const TONES: Record<string, string> = {
  teal: "bg-teal-50 text-teal-700", indigo: "bg-indigo-50 text-indigo-700",
  violet: "bg-violet-50 text-violet-700", orange: "bg-orange-50 text-orange-700",
  blue: "bg-blue-50 text-blue-700", emerald: "bg-emerald-50 text-emerald-700",
  rose: "bg-rose-50 text-rose-700", amber: "bg-amber-50 text-amber-700",
  cyan: "bg-cyan-50 text-cyan-700", slate: "bg-slate-100 text-slate-700"
};
const shortNum = (n: number) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(n);
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
  const escape = (v: unknown) => '"' + (v === null || v === undefined ? "" : String(v)).replaceAll('"', '""') + '"';
  downloadText("resultado_diagnostico.csv", [cols.map(escape).join(";"), ...rows.map(r => cols.map(c => escape(r[c])).join(";"))].join("\r\n"),
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
    <select className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink outline-none" value={value} onChange={e => onChange(e.target.value)}>
      <option value="">Todos / não selecionado</option>
      {options.map(v => <option key={v} value={v}>{v}</option>)}
    </select>
  </label>;
}
function App() {
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
  const [confirmedNoOverlap, setConfirmedNoOverlap] = useState(false);
  const [ftsScopeConfirmed, setFtsScopeConfirmed] = useState(false);
  const [singlePeriodConfirmed, setSinglePeriodConfirmed] = useState(false);
  const [confirmedRoles, setConfirmedRoles] = useState<Role[]>([]);
  const [countUnit, setCountUnit] = useState("");
  const [populationAligned, setPopulationAligned] = useState(false);
  const [temporalCompared, setTemporalCompared] = useState(false);
  const [territoryStable, setTerritoryStable] = useState(false);
  const [longitudinalIdentity, setLongitudinalIdentity] = useState(false);
  const [identityCountConfirmed, setIdentityCountConfirmed] = useState(false);
  const [categoryConstant, setCategoryConstant] = useState("");
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [preflighting, setPreflighting] = useState(false);
  const [preflightError, setPreflightError] = useState("");

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const selectedFeature = FEATURES.find(f => f.id === active);
  const plot = useMemo(() => {
    if (!result?.rows.length) return null;
    const keys = Object.keys(result.rows[0]);
    const numeric = keys.find(k => result.rows.some(r => typeof r[k] === "number"));
    const category = keys.find(k => result.rows.some(r => typeof r[k] === "string"));
    if (!numeric || !category) return null;
    return { numeric, category, values: result.rows.slice(0, 12).map(r => ({ name: String(r[category] ?? "").slice(0, 20), value: Number(r[numeric] ?? 0) })) };
  }, [result]);

  async function inspectFile(nextFile: File, nextSheet = "") {
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
      setInspection(details);
      setMapping(details.suggested_mapping);
      setConfirmedRoles([]);
      setFtsScopeConfirmed(false);
      setSinglePeriodConfirmed(false);
      setCountUnit("");
      setPopulationAligned(false);
      setTemporalCompared(false);
      setTerritoryStable(false);
      setLongitudinalIdentity(false);
      setIdentityCountConfirmed(false);
      setCategoryConstant("");
      setPreflight(details.preflight);
      setPreflightError("");
      setServerStatus("online");
      setPeriodFilter("");
      setCategoryFilter("");
      setReference("");
    } catch (exc) {
      const message = readableError(exc);
      setUploadError(message);
      if (message.includes("Não foi possível alcançar")) setServerStatus("offline");
    } finally { setInspecting(false); }
  }
  async function chooseFile(next: File | undefined) {
    if (!next) return;
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
      period_filter: periodFilter, category_filter: categoryFilter,
      reference_territory: reference, crs, quantile_count: quantiles,
      no_overlap_confirmed: confirmedNoOverlap,
      fts_scope_confirmed: ftsScopeConfirmed,
      single_period_confirmed: singlePeriodConfirmed,
      confirmed_roles: confirmedRoles,
      count_unit: countUnit,
      population_denominator_confirmed: populationAligned,
      temporal_comparability_confirmed: temporalCompared,
      territory_longitudinal_confirmed: territoryStable,
      longitudinal_identity_confirmed: longitudinalIdentity,
      identity_count_confirmed: identityCountConfirmed,
      category_constant: categoryConstant
    };
  }
  function associateColumn(column: string, role: Role | "") {
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
    setResult(null);
    setError("");
  }
  async function run(op: Operation) {
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
    const form = new FormData();
    form.append("file", file); form.append("sheet", sheet); form.append("operation", op);
    form.append("mapping", JSON.stringify(mapping));
    form.append("options", JSON.stringify(semanticOptions()));
    try {
      const response = await fetch(API + "/api/analyze", { method: "POST", body: form });
      const body = await readApiResponse(response);
      setResult(body as AnalysisResult);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (exc) {
      setError(readableError(exc));
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    }
    finally { setRunning(false); }
  }
  function sampleCsv() {
    downloadText("modelo_dados_territoriais.csv",
      "Territorio;Ano;Categoria;Quantidade;Populacao;Latitude;Longitude\r\nMunicipio A;2024;Medicos;120;80000;-15.8;-47.9\r\nMunicipio B;2024;Medicos;65;65000;-16.2;-48.1\r\n",
      "text/csv;charset=utf-8");
  }

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
    if (!inspection || inspection.requires_sheet || !file) return;
    let cancelled = false;
    setPreflighting(true);
    setPreflight(null);
    setPreflightError("");
    const timer = window.setTimeout(async () => {
      const form = new FormData();
      form.append("file", file);
      form.append("sheet", sheet);
      form.append("mapping", JSON.stringify(mapping));
      form.append("options", JSON.stringify({
        reference_territory: reference, crs,
        no_overlap_confirmed: confirmedNoOverlap,
        fts_scope_confirmed: ftsScopeConfirmed,
        single_period_confirmed: singlePeriodConfirmed,
        confirmed_roles: confirmedRoles,
        count_unit: countUnit,
        population_denominator_confirmed: populationAligned,
        temporal_comparability_confirmed: temporalCompared,
        territory_longitudinal_confirmed: territoryStable,
        longitudinal_identity_confirmed: longitudinalIdentity,
        identity_count_confirmed: identityCountConfirmed,
        category_constant: categoryConstant
      }));
      try {
        const response = await fetch(API + "/api/preflight", { method: "POST", body: form });
        const next = await readApiResponse(response) as Preflight;
        if (!cancelled) setPreflight(next);
      } catch (exc) {
        if (!cancelled) setPreflightError(readableError(exc));
      } finally {
        if (!cancelled) setPreflighting(false);
      }
    }, 250);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [inspection, file, sheet, mapping, confirmedRoles, countUnit,
      populationAligned, temporalCompared, territoryStable,
      longitudinalIdentity, identityCountConfirmed, categoryConstant,
      ftsScopeConfirmed, singlePeriodConfirmed, reference, crs, confirmedNoOverlap]);

  return <div className="min-h-screen bg-canvas">
    <header className="no-print sticky top-0 z-30 border-b border-white/70 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1350px] items-center justify-between gap-3 px-5 py-3.5 lg:px-10">
        <a href="#inicio" className="flex items-center gap-3">
          <span className="rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-slate-950"><Bot size={23} strokeWidth={2.2} /></span>
          <span><span className="block text-sm font-bold leading-tight tracking-tight text-ink sm:text-base">Agente Diagnóstico Territorial</span>
            <span className="block text-[10px] font-medium uppercase tracking-[.14em] text-slate-500">Força de Trabalho na Saúde</span></span>
        </a>
        <nav className="hidden items-center gap-8 text-sm font-semibold text-slate-500 md:flex">
          <a href="#dados" className="hover:text-teal">Dados</a>
          <a href="#analises" className="hover:text-teal">Análises</a>
          <a href="#resultados" className="hover:text-teal">Resultados</a>
        </nav>
        <span aria-live="polite" className={["flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold",
          serverStatus === "online" ? "border-emerald-100 bg-emerald-50 text-emerald-700" :
          serverStatus === "offline" ? "border-rose-100 bg-rose-50 text-rose-700" :
          "border-slate-200 bg-slate-50 text-slate-500"].join(" ")}>
          {serverStatus === "online" ? <CheckCircle2 size={13}/> : serverStatus === "offline" ? <XCircle size={13}/> : <LoaderCircle size={13} className="animate-spin"/>}
          {serverStatus === "online" ? "Motor conectado" : serverStatus === "offline" ? "Motor indisponível" : "Conectando"}
        </span>
      </div>
    </header>
    <main id="inicio" className="mx-auto max-w-[1350px] px-4 pb-20 pt-6 sm:px-6 lg:px-10">
      <section className="hero-gradient relative overflow-hidden rounded-[28px] px-6 py-10 text-white shadow-card sm:px-10 sm:py-14 lg:px-14">
        <div className="hero-pattern absolute inset-y-0 right-0 w-[40%] opacity-40" />
        <div className="relative z-10 max-w-3xl">
          <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1.5 text-[11px] font-semibold tracking-wide"><Sparkles size={13}/> INTELIGÊNCIA ANALÍTICA DETERMINÍSTICA</span>
          <h1 className="max-w-3xl text-3xl font-semibold leading-[1.15] tracking-tight sm:text-4xl lg:text-5xl">Transforme dados em diagnósticos territoriais.</h1>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-cyan-50/90 sm:text-base">Explore a distribuição, a evolução e as desigualdades territoriais da força de trabalho na saúde. Envie seus dados, escolha uma análise e visualize resultados rastreáveis — sem precisar escrever comandos.</p>
          <a href="#dados" className="no-print mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-ink shadow-lg transition hover:bg-cyan-50">Começar análise <ArrowRight size={17}/></a>
        </div>
      </section>
      <section id="dados" className="section-anchor mt-14">
        <SectionHeader eyebrow="01 · Preparar" title="Comece pelos seus dados" description="Carregue um arquivo estruturado. O sistema examina a estrutura e identifica quais campos estão disponíveis antes de realizar qualquer cálculo."/>
        <div className="grid gap-5 lg:grid-cols-[1.25fr_.85fr]">
          <div className="rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7">
            <div className="mb-5 flex items-center justify-between">
              <div className="flex items-center gap-2.5"><span className="rounded-xl bg-cyan-50 p-2.5 text-teal"><FolderUp size={21}/></span><h3 className="font-bold text-ink">Importar base de dados</h3></div>
              <span className="text-xs font-semibold text-slate-400">CSV · XLS · XLSX</span>
            </div>
            <input ref={inputRef} type="file" accept=".csv,.xls,.xlsx" className="hidden" onChange={e => { const next = e.target.files?.[0]; e.target.value = ""; void chooseFile(next); }} />
            <div className="cursor-pointer rounded-[18px] border-2 border-dashed border-cyan-200 bg-gradient-to-b from-cyan-50/75 to-white px-5 py-10 text-center transition hover:border-teal"
              role="button" tabIndex={0} onClick={() => inputRef.current?.click()}
              onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); } }}>
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-teal shadow-sm"><UploadCloud size={27} strokeWidth={1.7}/></div>
              <p className="text-base font-bold text-ink">{file ? file.name : "Selecione seu arquivo para começar"}</p>
              <p className="mt-2 text-xs text-slate-500">{file ? "Clique para substituir a base selecionada." : "CSV ou Excel (.xls/.xlsx) · Limite experimental de 30 MB"}</p>
              <span className="mt-5 inline-flex items-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-xs font-bold text-white"><FileUp size={15}/> Selecionar arquivo</span>
            </div>
            {inspecting && <div role="status" aria-live="polite" className="mt-4 flex items-center gap-2 rounded-xl bg-cyan-50 px-4 py-3 text-sm font-semibold text-teal">
              <LoaderCircle size={17} className="animate-spin"/> Lendo e validando a estrutura do arquivo. Aguarde...
            </div>}
            {uploadError && <div role="alert" className="mt-4 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              <XCircle size={17} className="mt-0.5 shrink-0"/> <div><strong>Importação não concluída.</strong><p className="mt-1 leading-5">{uploadError}</p></div>
            </div>}
            {inspection?.requires_sheet && <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-4">
              <p className="mb-3 flex items-center gap-2 text-sm font-bold text-amber-900"><Info size={17}/> Arquivo recebido: escolha uma planilha para continuar.</p>
              <label className="flex flex-col gap-1 text-xs font-bold text-slate-700">Aba do arquivo Excel
                <select className="rounded-xl border border-amber-200 bg-white px-3 py-2.5 text-sm font-normal text-ink" value={sheet} onChange={e => { const next = e.target.value; setSheet(next); if (file && next) void inspectFile(file, next); }}>
                  <option value="">Selecione uma aba</option>
                  {inspection.sheets.map(name => <option key={name} value={name}>{name}</option>)}
                </select>
              </label>
            </div>}
            {inspection && !inspection.requires_sheet && <div role="status" aria-live="polite" className="mt-5 flex flex-wrap items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <CheckCircle2 size={19}/><span className="font-bold">Arquivo importado e examinado com sucesso</span>
              <span className="text-xs">{shortNum(inspection.row_count)} linhas · {inspection.columns.length} colunas{sheet ? " · Aba: " + sheet : ""}</span>
              <p className="w-full text-xs leading-5">Agora confira as associações de campos abaixo e clique em um cartão de análise. O arquivo é utilizado apenas nesta sessão local do navegador.</p>
            </div>}
            <p className="mt-4 text-xs leading-5 text-slate-500"><Info size={13} className="mr-1 inline"/> O exame inicial não produz diagnóstico. Nenhum arquivo é guardado pelo backend após a requisição; evite enviar bases com dados pessoais desnecessários.</p>
          </div>
          <div className="rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7">
            <div className="mb-5 flex items-center gap-2.5"><span className="rounded-xl bg-blue-50 p-2.5 text-blue-700"><Table2 size={21}/></span><h3 className="font-bold text-ink">Como estruturar seus dados</h3></div>
            <p className="mb-4 text-xs leading-6 text-slate-500">Este é um exemplo recomendado, não um modelo obrigatório. A compatibilidade depende dos campos necessários a cada análise.</p>
            <div className="overflow-x-auto rounded-xl border border-line">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-[11px] text-slate-500"><tr>{["Território", "Período", "Categoria", "Quantidade", "População"].map(x => <th key={x} className="whitespace-nowrap px-3 py-3">{x}</th>)}</tr></thead>
                <tbody className="text-slate-700"><tr>{["A", "2024", "Médicos", "120", "80.000"].map((x, i) => <td key={i} className="whitespace-nowrap border-t border-line px-3 py-3">{x}</td>)}</tr>
                  <tr>{["B", "2024", "Médicos", "65", "65.000"].map((x, i) => <td key={i} className="whitespace-nowrap border-t border-line px-3 py-3">{x}</td>)}</tr></tbody>
              </table>
            </div>
            <button onClick={sampleCsv} className="no-print mt-4 flex items-center gap-2 text-sm font-bold text-teal hover:underline"><Download size={16}/> Baixar modelo CSV</button>
            <div className="mt-5 grid gap-3 border-t border-line pt-4 text-xs text-slate-600">
              <p><span className="font-bold text-ink">Para densidade:</span> quantitativos e população correspondente.</p>
              <p><span className="font-bold text-ink">Para análises espaciais:</span> coordenadas e referencial geodésico.</p>
              <p><span className="font-bold text-ink">Para rotatividade:</span> identificador individual com significado longitudinal autorizado.</p>
            </div>
          </div>
        </div>
        {inspection && !inspection.requires_sheet && <div id="associacoes" className="section-anchor mt-5 rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7">
          <div className="mb-5 flex items-center gap-3">
            <span className="rounded-xl bg-slate-100 p-2.5 text-slate-600"><Settings2 size={20}/></span>
            <div>
              <h3 className="font-bold text-ink">Reconhecimento e habilitação dos dados</h3>
              <p className="text-xs leading-5 text-slate-500">O sistema reconhece os cabeçalhos governados e apresenta correspondências propostas. Você só precisa esclarecer campos ambíguos e significados exigidos pela análise.</p>
            </div>
          </div>
          {preflighting && <p role="status" className="mb-4 flex items-center gap-2 text-xs text-teal"><LoaderCircle size={15} className="animate-spin"/> Recalculando a disponibilidade das análises...</p>}
          {preflightError && <p role="alert" className="mb-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">{preflightError}</p>}
          <div className="mb-3 grid gap-2 sm:grid-cols-[1fr_1fr]">
            {inspection.column_profiles.map(profile => {
              const associated = (Object.entries(mapping).find(([, value]) => value === profile.name) || [])[0] as Role | undefined;
              const field = associated ? preflight?.field_states[associated] : null;
              const status = field?.status || (associated ? "proposed" : "unmapped");
              return <div key={profile.name} className="rounded-xl border border-line bg-slate-50/50 p-3.5">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <strong className="max-w-full break-all text-xs text-ink">{profile.name}</strong>
                  <span className={["rounded-full px-2 py-1 text-[10px] font-bold",
                    status === "recognized" || status === "confirmed" ? "bg-emerald-50 text-emerald-700" :
                    status === "proposed" ? "bg-amber-50 text-amber-700" : "bg-slate-200 text-slate-600"].join(" ")}>
                    {status === "recognized" ? "Reconhecido" : status === "confirmed" ? "Confirmado" :
                      status === "proposed" ? "A confirmar" : "Sem associação"}
                  </span>
                </div>
                <p className="mb-2 text-[11px] text-slate-500">{profile.type} · {profile.missing} ausências</p>
                <label className="flex flex-col gap-1 text-xs font-medium text-slate-600">
                  Significado para a análise
                  <select className="w-full min-w-0 rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink"
                    value={associated || ""} onChange={e => associateColumn(profile.name, e.target.value as Role | "")}>
                    <option value="">Não atribuído / auxiliar</option>
                    {ROLES.map(role => <option key={role.key} value={role.key}>{role.label}</option>)}
                  </select>
                </label>
                {associated && status === "proposed" && <button type="button" className="mt-3 rounded-lg bg-amber-100 px-3 py-2 text-xs font-bold text-amber-900 hover:bg-amber-200"
                  onClick={() => setConfirmedRoles(prev => [...new Set([...prev, associated])])}>
                  Confirmar associação como {ROLES.find(x => x.key === associated)?.label}
                </button>}
                {profile.suspicious_header && <p className="mt-2 text-[11px] leading-4 text-amber-800">Cabeçalho incomum: verifique se a primeira linha da planilha contém os nomes reais das colunas.</p>}
                {profile.proposal.length > 0 && <p className="mt-2 text-[11px] leading-4 text-slate-500">{profile.proposal[0].evidence}</p>}
              </div>;
            })}
          </div>
          <div className="mt-5 rounded-xl border border-cyan-100 bg-cyan-50/40 p-4">
            <h4 className="mb-3 text-sm font-bold text-ink">Significados complementares</h4>
            <p className="mb-4 text-xs leading-5 text-slate-600">Estas confirmações não são inferidas do nome da coluna. Elas somente habilitam as operações que dependem delas.</p>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">Unidade de contagem
                <select className="rounded-lg border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink" value={countUnit} onChange={e => {setCountUnit(e.target.value);setResult(null);}}>
                  <option value="">Não informada</option>
                  <option value="pessoas">Pessoas distintas no recorte informado</option>
                  <option value="vinculos">Vínculos de trabalho</option>
                  <option value="postos">Postos de trabalho</option>
                  <option value="outro">Outra unidade (verifique a adequação)</option>
                </select>
              </label>
              {!mapping.category && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-700">Categoria constante da base, se aplicável
                <input className="rounded-lg border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                  value={categoryConstant} placeholder={inspection.suggested_category_constant || "Ex.: Médicos"}
                  onChange={e => {setCategoryConstant(e.target.value); setResult(null);}}/>
                {inspection.suggested_category_constant && <span className="text-[11px] font-normal text-slate-500">Sugestão extraída do cabeçalho: {inspection.suggested_category_constant}. Confirme digitando.</span>}
              </label>}
            </div>
            <div className="mt-5 grid gap-3 text-xs text-slate-700 sm:grid-cols-2">
              <label className="flex items-start gap-2"><input type="checkbox" checked={ftsScopeConfirmed} onChange={e => setFtsScopeConfirmed(e.target.checked)}/> Declaro que a base ou categoria informada integra a força de trabalho na saúde</label>
              <label className="flex items-start gap-2"><input type="checkbox" checked={singlePeriodConfirmed} onChange={e => setSinglePeriodConfirmed(e.target.checked)}/> A base é de um único período (sem coluna temporal)</label>
              {mapping.population && <label className="flex items-start gap-2"><input type="checkbox" checked={populationAligned} onChange={e => setPopulationAligned(e.target.checked)}/> Confirmo que a população é o denominador pertinente, com território e período alinhados</label>}
              {mapping.period && <label className="flex items-start gap-2"><input type="checkbox" checked={temporalCompared} onChange={e => setTemporalCompared(e.target.checked)}/> Confirmo a convenção temporal e a comparabilidade dos quantitativos entre períodos</label>}
              {mapping.territory && mapping.period && <label className="flex items-start gap-2"><input type="checkbox" checked={territoryStable} onChange={e => setTerritoryStable(e.target.checked)}/> Confirmo que a identidade territorial é comparável entre períodos</label>}
              {mapping.identity && <label className="flex items-start gap-2"><input type="checkbox" checked={identityCountConfirmed} onChange={e => setIdentityCountConfirmed(e.target.checked)}/> Confirmo identidade individual adequada à contagem distinta</label>}
              {mapping.identity && mapping.period && <label className="flex items-start gap-2"><input type="checkbox" checked={longitudinalIdentity} onChange={e => setLongitudinalIdentity(e.target.checked)}/> Confirmo identidade pessoal válida longitudinalmente para rotatividade</label>}
            </div>
            {mapping.latitude && mapping.longitude && <div className="mt-5 grid gap-3 border-t border-cyan-100 pt-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-xs font-semibold text-slate-700">Referencial geodésico (se conhecido)
                <select className="rounded-lg border border-line bg-white px-3 py-2.5 text-sm font-normal" value={crs} onChange={e => setCrs(e.target.value)}>
                  <option value="">Não informado</option><option value="SIRGAS2000">SIRGAS2000</option>
                </select>
              </label>
              <SelectField label="Território de referência" value={reference} options={inspection.territories} onChange={setReference}/>
            </div>}
          </div>
        </div>}
      </section>
      <section id="analises" className="section-anchor mt-14">
        <SectionHeader eyebrow="02 · Explorar" title="Escolha sua análise" description="Os dez cartões permanecem visíveis. Apenas as análises habilitadas pela verificação de campos e significados ficam destacadas; as demais indicam o que falta." />
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-5">
          {FEATURES.map((f, index) => <button key={f.id} type="button" onClick={() => { void run(f.id); }}
            className={["feature-card no-print group flex min-h-[177px] flex-col items-start rounded-[20px] border bg-white p-4 text-left shadow-card sm:p-5",
              active === f.id ? "feature-card-active" : "border-line",
              preflight?.capabilities[f.id]?.status === "available" && !preflighting ? "ring-1 ring-teal-100" : "opacity-55 grayscale-[.3] hover:opacity-85"
              ].join(" ")}
            aria-disabled={preflight?.capabilities[f.id]?.status !== "available"}
            title={preflight?.capabilities[f.id]?.reasons.join(" ") || "Análise habilitada"}
            aria-pressed={active === f.id}>
            <span className="flex w-full items-start justify-between">
              <span className={["flex h-11 w-11 items-center justify-center rounded-2xl", TONES[f.tone]].join(" ")}><f.icon size={21} strokeWidth={1.85}/></span>
              <ArrowUpRight size={17} className="text-slate-300 transition group-hover:text-teal" />
            </span>
            <span className="mt-5 block text-sm font-bold text-ink">{f.title}</span>
            <span className="mt-1 block text-[11px] leading-5 text-slate-500">{f.detail}</span>
            <span className={["mt-auto pt-3 text-[10px] font-bold",
              preflight?.capabilities[f.id]?.status === "available" ? "text-emerald-700" : "text-slate-500"].join(" ")}>
              {preflighting ? "Verificando..." : preflight?.capabilities[f.id]?.status === "available" ? "Disponível" :
                preflight?.capabilities[f.id]?.status === "needs_confirmation" ? "Requer confirmação" : "Não habilitada"}
            </span>
          </button>)}
        </div>
        <div className="mt-5 rounded-[18px] border border-cyan-100 bg-cyan-50/70 px-5 py-4 text-sm text-slate-600">
          <div className="flex items-start gap-3"><HelpCircle size={20} className="mt-0.5 shrink-0 text-teal"/><p className="leading-6"><strong className="text-ink">Como funciona:</strong> a importação realiza somente o exame habilitador. Um cartão destacado executa a operação quando selecionado. Um cartão esmaecido continua consultável, mas não dispara cálculo enquanto os requisitos não forem atendidos.</p></div>
        </div>
        {active && preflight?.capabilities[active]?.status !== "available" && <div role="status" className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <strong>{preflight?.capabilities[active]?.status === "needs_confirmation" ? "Confirmação necessária" : "Análise não habilitada nesta base"}</strong>
          <ul className="mt-2 list-inside list-disc space-y-1">{(preflight?.capabilities[active]?.reasons || ["Carregue e examine uma base para conhecer os requisitos."]).map((reason,i) => <li key={i}>{reason}</li>)}</ul>
          <button type="button" className="mt-3 text-xs font-bold underline" onClick={() => document.getElementById("associacoes")?.scrollIntoView({ behavior: "smooth", block: "start" })}>Rever associação de campos</button>
        </div>}
      </section>
      <section id="resultados" ref={resultsRef} className="section-anchor mt-14">
        <SectionHeader eyebrow="03 · Interpretar" title="Resultados do diagnóstico" description="Os resultados são calculados no motor Python e apresentados com método, cobertura e limitações explícitas."/>
        <div className="rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7 print-content">
          <div className="no-print flex flex-wrap items-start justify-between gap-4 border-b border-line pb-6">
            <div className="flex items-start gap-3">
              <span className="rounded-xl bg-teal-50 p-2.5 text-teal">{selectedFeature ? <selectedFeature.icon size={22}/> : <ClipboardList size={22}/>}</span>
              <div><h3 className="font-bold text-ink">{selectedFeature ? selectedFeature.title : "Selecione uma análise"}</h3><p className="mt-1 text-xs text-slate-500">{selectedFeature?.detail || "Os resultados aparecerão aqui após a execução."}</p></div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button disabled={!result} onClick={() => result && exportCsv(result.rows)} className="flex items-center gap-1.5 rounded-xl border border-line px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-40"><ArrowDownToLine size={14}/> CSV</button>
              <button disabled={!result} onClick={() => window.print()} className="flex items-center gap-1.5 rounded-xl border border-line px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-40"><FileSpreadsheet size={14}/> Imprimir / PDF</button>
            </div>
          </div>
          {inspection && !inspection.requires_sheet && <div className="no-print grid gap-4 border-b border-line py-5 sm:grid-cols-2 lg:grid-cols-4">
            <SelectField label="Filtrar por período" value={periodFilter} options={inspection.periods} onChange={v => {setPeriodFilter(v); setResult(null);}}/>
            <SelectField label="Filtrar por categoria" value={categoryFilter} options={inspection.categories} onChange={v => {setCategoryFilter(v); setResult(null);}}/>
            {active === "distribution" && <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">Número de classes
              <select className="rounded-xl border border-line px-3 py-2.5 text-sm" value={quantiles} onChange={e => {setQuantiles(Number(e.target.value)); setResult(null);}}>{[4, 5, 10].map(v=><option value={v} key={v}>{v}</option>)}</select></label>}
            {active === "spatial" && <>
              <SelectField label="Território de referência" value={reference} options={inspection.territories} onChange={setReference}/>
              <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-600">Referencial geodésico
                <select className="rounded-xl border border-line px-3 py-2.5 text-sm" value={crs} onChange={e=>setCrs(e.target.value)}><option value="">Não informado</option><option value="SIRGAS2000">SIRGAS2000</option></select></label>
            </>}
            {active === "aggregate" && <label className="col-span-2 flex items-center gap-2 self-center text-xs text-slate-700"><input type="checkbox" checked={confirmedNoOverlap} onChange={e=>setConfirmedNoOverlap(e.target.checked)}/> Declaro que não há sobreposição de pessoas nos territórios considerados</label>}
          </div>}
          {active && inspection && !inspection.requires_sheet && preflight?.capabilities[active]?.status === "available" && <div className="no-print mt-5 flex justify-end">
            <button disabled={running} onClick={()=>{void run(active);}} className="flex items-center gap-2 rounded-xl bg-teal px-4 py-2.5 text-sm font-bold text-white hover:bg-ink disabled:opacity-50">
              {running ? <LoaderCircle size={16} className="animate-spin"/> : <Calculator size={16}/>} {running ? "Calculando..." : "Executar / atualizar análise"}</button>
          </div>}
          {error && <div role="alert" className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><XCircle size={18} className="shrink-0"/>{error}</div>}
          {running && <div className="flex items-center justify-center gap-2 py-16 text-sm text-teal"><LoaderCircle className="animate-spin"/> Processando dados...</div>}
          {!running && !result && !error && <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="mb-4 rounded-2xl bg-slate-50 p-5 text-slate-300"><Database size={34} strokeWidth={1.6}/></span>
            <p className="text-base font-bold text-ink">Seu diagnóstico começa aqui</p>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">Carregue uma base, confira os significados e selecione um cartão habilitado. A análise nunca é executada durante o upload.</p>
          </div>}
          {result && <div className="pt-6">
            <h3 className="text-xl font-bold text-ink">{result.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-500">{result.description}</p>
            {result.metrics.length > 0 && <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {result.metrics.map(metric => <div key={metric.label} className="rounded-2xl border border-line bg-slate-50 px-5 py-5"><p className="text-xs font-medium text-slate-500">{metric.label}</p><p className="mt-2 text-2xl font-bold text-ink">{pretty(metric.value)}</p></div>)}
            </div>}
            {plot && <div className="mt-7 rounded-2xl border border-line p-4 sm:p-6">
              <div className="mb-4 flex items-center gap-2"><BarChart3 size={18} className="text-teal"/><h4 className="text-sm font-bold text-ink">Visualização dos resultados</h4></div>
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
            {result.rows.length > 0 && <div className="mt-7 overflow-hidden rounded-2xl border border-line">
              <div className="flex items-center justify-between border-b border-line px-5 py-4"><h4 className="text-sm font-bold text-ink">Tabela detalhada</h4><span className="text-xs text-slate-400">{result.total_rows} linhas · até 150 exibidas</span></div>
              <div className="max-h-[520px] overflow-auto"><table className="data-table w-full">
                <thead className="sticky top-0 bg-slate-50"><tr>{Object.keys(result.rows[0]).map(k=><th key={k}>{k}</th>)}</tr></thead>
                <tbody>{result.rows.map((row,i)=><tr key={i}>{Object.keys(result.rows[0]).map(k=><td key={k}>{pretty(row[k])}</td>)}</tr>)}</tbody>
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
        <p className="flex items-center gap-2"><Fingerprint size={15}/> Processamento determinístico · Diagnósticos territoriais</p>
      </footer>
    </main>
  </div>;
}

export default App;
