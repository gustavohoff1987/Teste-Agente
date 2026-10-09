import { useEffect, useMemo, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";
import {
  ArrowDownToLine, ArrowRight, ArrowUpRight, BarChart3, Calculator, CheckCircle2,
  ChevronDown, ClipboardList, Clock3, Database, Download, FileBarChart2, FileSpreadsheet,
  FileUp, Fingerprint, FolderUp, Globe2, HelpCircle, Info, Layers3, ListFilter,
  LoaderCircle, MapPinned, MoveRight, RefreshCw, SearchCheck, Settings2, ShieldCheck,
  Sparkles, Table2, TrendingUp, UploadCloud, UsersRound, XCircle
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis
} from "recharts";

type Role = "territory" | "period" | "category" | "count" | "population" | "latitude" | "longitude" | "identity";
type Operation = "density" | "counts" | "distribution" | "comparisons" | "temporal" | "aggregate" | "spatial" | "ranking" | "rotation" | "report";
type Mapping = Partial<Record<Role, string>>;
type Inspection = {
  requires_sheet: boolean; sheets: string[]; columns: string[]; row_count: number;
  suggested_mapping: Mapping; periods: string[]; categories: string[]; territories: string[];
};
type Metric = { label: string; value: string | number };
type AnalysisResult = { title: string; description: string; rows: Record<string, unknown>[]; total_rows: number; metrics: Metric[]; notes: string[] };
type Feature = { id: Operation; title: string; detail: string; icon: LucideIcon; tone: string };

const API = import.meta.env.VITE_API_BASE_URL || "";
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
  const [periodFilter, setPeriodFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [reference, setReference] = useState("");
  const [crs, setCrs] = useState("");
  const [quantiles, setQuantiles] = useState(5);
  const [confirmedNoOverlap, setConfirmedNoOverlap] = useState(false);
  const [ftsScopeConfirmed, setFtsScopeConfirmed] = useState(false);
  const [singlePeriodConfirmed, setSinglePeriodConfirmed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const availableColumns = inspection?.columns || [];
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
    setInspecting(true); setError(""); setResult(null); setInspection(null);
    const form = new FormData();
    form.append("file", nextFile); form.append("sheet", nextSheet);
    try {
      const response = await fetch(API + "/api/inspect", { method: "POST", body: form });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Não foi possível examinar o arquivo.");
      const details = body as Inspection;
      setInspection(details); setMapping(details.suggested_mapping);
      setPeriodFilter(""); setCategoryFilter(""); setReference("");
    } catch (exc) { setError(exc instanceof Error ? exc.message : "Falha na conexão com o motor Python."); }
    finally { setInspecting(false); }
  }
  async function chooseFile(next: File | undefined) {
    if (!next) return;
    setFile(next); setSheet(""); setActive(null); setResult(null);
    await inspectFile(next);
  }
  async function run(op: Operation) {
    setActive(op); setResult(null); setError("");
    if (!file || !inspection || inspection.requires_sheet) {
      setError("Carregue uma base válida e conclua a seleção de planilha antes de executar.");
      return;
    }
    setRunning(true);
    const form = new FormData();
    form.append("file", file); form.append("sheet", sheet); form.append("operation", op);
    form.append("mapping", JSON.stringify(mapping));
    form.append("options", JSON.stringify({
      period_filter: periodFilter, category_filter: categoryFilter,
      reference_territory: reference, crs, quantile_count: quantiles,
      no_overlap_confirmed: confirmedNoOverlap,
      fts_scope_confirmed: ftsScopeConfirmed,
      single_period_confirmed: singlePeriodConfirmed
    }));
    try {
      const response = await fetch(API + "/api/analyze", { method: "POST", body: form });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Não foi possível executar a análise.");
      setResult(body as AnalysisResult);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (exc) { setError(exc instanceof Error ? exc.message : "Falha de comunicação com o motor Python."); }
    finally { setRunning(false); }
  }
  function sampleCsv() {
    downloadText("modelo_dados_territoriais.csv",
      "Territorio;Ano;Categoria;Quantidade;Populacao;Latitude;Longitude\r\nMunicipio A;2024;Medicos;120;80000;-15.8;-47.9\r\nMunicipio B;2024;Medicos;65;65000;-16.2;-48.1\r\n",
      "text/csv;charset=utf-8");
  }

  useEffect(() => { document.title = "Agente Diagnóstico Territorial"; }, []);
  return <div className="min-h-screen bg-canvas">
    <header className="no-print sticky top-0 z-30 border-b border-white/70 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1350px] items-center justify-between gap-3 px-5 py-3.5 lg:px-10">
        <a href="#inicio" className="flex items-center gap-3">
          <span className="rounded-xl bg-ink p-2.5 text-white"><Globe2 size={22} strokeWidth={1.8} /></span>
          <span><span className="block text-sm font-bold leading-tight tracking-tight text-ink sm:text-base">Agente Diagnóstico Territorial</span>
            <span className="block text-[10px] font-medium uppercase tracking-[.14em] text-slate-500">Força de Trabalho na Saúde</span></span>
        </a>
        <nav className="hidden items-center gap-8 text-sm font-semibold text-slate-500 md:flex">
          <a href="#dados" className="hover:text-teal">Dados</a>
          <a href="#analises" className="hover:text-teal">Análises</a>
          <a href="#resultados" className="hover:text-teal">Resultados</a>
        </nav>
        <span className="flex items-center gap-1.5 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-[11px] font-bold text-emerald-700">
          <ShieldCheck size={13}/> Sem LLM
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
              <span className="text-xs font-semibold text-slate-400">CSV · XLSX</span>
            </div>
            <input ref={inputRef} type="file" accept=".csv,.xlsx" className="hidden" onChange={e => { void chooseFile(e.target.files?.[0]); }} />
            <div className="cursor-pointer rounded-[18px] border-2 border-dashed border-cyan-200 bg-gradient-to-b from-cyan-50/75 to-white px-5 py-10 text-center transition hover:border-teal"
              role="button" tabIndex={0} onClick={() => inputRef.current?.click()}
              onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); } }}>
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-teal shadow-sm"><UploadCloud size={27} strokeWidth={1.7}/></div>
              <p className="text-base font-bold text-ink">{file ? file.name : "Selecione seu arquivo para começar"}</p>
              <p className="mt-2 text-xs text-slate-500">{file ? "Clique para substituir a base selecionada." : "CSV ou Excel · Limite experimental de 30 MB"}</p>
              <span className="mt-5 inline-flex items-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-xs font-bold text-white"><FileUp size={15}/> Selecionar arquivo</span>
            </div>
            {inspecting && <p className="mt-4 flex items-center gap-2 text-sm text-teal"><LoaderCircle size={16} className="animate-spin"/> Examinando a estrutura...</p>}
            {inspection?.requires_sheet && <div className="mt-5"><SelectField label="Escolha a planilha do arquivo Excel" value={sheet} options={inspection.sheets} onChange={next => { setSheet(next); if (file) void inspectFile(file, next); }}/></div>}
            {inspection && !inspection.requires_sheet && <div className="mt-5 flex flex-wrap items-center gap-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <CheckCircle2 size={17}/><span className="font-bold">Estrutura reconhecida</span><span className="text-xs">{shortNum(inspection.row_count)} linhas · {inspection.columns.length} colunas</span>
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
        {inspection && !inspection.requires_sheet && <div className="mt-5 rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7">
          <div className="mb-5 flex items-center gap-3"><span className="rounded-xl bg-slate-100 p-2.5 text-slate-600"><Settings2 size={20}/></span>
            <div><h3 className="font-bold text-ink">Associar campos da base</h3><p className="text-xs text-slate-500">Sugestões são determinísticas, baseadas em nomes reconhecidos. Confirme os significados necessários.</p></div></div>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {ROLES.map(role => <label key={role.key} className="flex min-w-0 flex-col gap-1.5">
              <span className="text-xs font-bold text-slate-700">{role.label}</span>
              <select className="w-full min-w-0 rounded-xl border border-line bg-slate-50 px-3 py-2.5 text-xs text-ink" value={mapping[role.key] || ""}
                onChange={e => { setMapping(old => ({...old, [role.key]: e.target.value})); setResult(null); }}>
                <option value="">Não associado</option>
                {availableColumns.map(col => <option key={col} value={col}>{col}</option>)}
              </select>
              <span className="text-[10px] leading-4 text-slate-400">{role.help}</span>
            </label>)}
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-5 border-t border-line pt-4">
            <label className="flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={ftsScopeConfirmed} onChange={e => setFtsScopeConfirmed(e.target.checked)}/> Esta base representa a FTS</label>
            <label className="flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={singlePeriodConfirmed} onChange={e => setSinglePeriodConfirmed(e.target.checked)}/> Dados de período único (sem coluna de período)</label>
          </div>
        </div>}
      </section>
      <section id="analises" className="section-anchor mt-14">
        <SectionHeader eyebrow="02 · Explorar" title="Escolha sua análise" description="Cada cartão corresponde a uma operação analítica. Selecione um para executar o cálculo; o sistema informa quando os dados ou significados necessários estiverem ausentes." />
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-5">
          {FEATURES.map((f, index) => <button key={f.id} type="button" onClick={() => { void run(f.id); }}
            className={["feature-card no-print group flex min-h-[177px] flex-col items-start rounded-[20px] border bg-white p-4 text-left shadow-card sm:p-5",
              active === f.id ? "feature-card-active" : "border-line"].join(" ")}
            aria-pressed={active === f.id}>
            <span className="flex w-full items-start justify-between">
              <span className={["flex h-11 w-11 items-center justify-center rounded-2xl", TONES[f.tone]].join(" ")}><f.icon size={21} strokeWidth={1.85}/></span>
              <ArrowUpRight size={17} className="text-slate-300 transition group-hover:text-teal" />
            </span>
            <span className="mt-5 block text-sm font-bold text-ink">{f.title}</span>
            <span className="mt-1 block text-[11px] leading-5 text-slate-500">{f.detail}</span>
            <span className="mt-auto pt-3 text-[10px] font-semibold text-slate-300">{String(index + 1).padStart(2, "0")}</span>
          </button>)}
        </div>
        <div className="mt-5 rounded-[18px] border border-cyan-100 bg-cyan-50/70 px-5 py-4 text-sm text-slate-600">
          <div className="flex items-start gap-3"><HelpCircle size={20} className="mt-0.5 shrink-0 text-teal"/><p className="leading-6"><strong className="text-ink">Como funciona:</strong> o upload apenas examina a estrutura. O cálculo ocorre quando você escolhe uma análise. Não são inventados denominadores, métodos, períodos nem parâmetros normativos.</p></div>
        </div>
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
          {active && inspection && !inspection.requires_sheet && <div className="no-print mt-5 flex justify-end">
            <button disabled={running} onClick={()=>{void run(active);}} className="flex items-center gap-2 rounded-xl bg-teal px-4 py-2.5 text-sm font-bold text-white hover:bg-ink disabled:opacity-50">
              {running ? <LoaderCircle size={16} className="animate-spin"/> : <Calculator size={16}/>} {running ? "Calculando..." : "Executar / atualizar análise"}</button>
          </div>}
          {error && <div role="alert" className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><XCircle size={18} className="shrink-0"/>{error}</div>}
          {running && <div className="flex items-center justify-center gap-2 py-16 text-sm text-teal"><LoaderCircle className="animate-spin"/> Processando dados...</div>}
          {!running && !result && !error && <div className="flex flex-col items-center justify-center py-16 text-center">
            <span className="mb-4 rounded-2xl bg-slate-50 p-5 text-slate-300"><Database size={34} strokeWidth={1.6}/></span>
            <p className="text-base font-bold text-ink">Seu diagnóstico começa aqui</p>
            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">Carregue uma base e selecione um dos cartões acima. Resultados reais substituirão esta área automaticamente.</p>
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
        <p className="flex items-center gap-2"><Fingerprint size={15}/> Processamento determinístico · Sem integração com LLM</p>
      </footer>
    </main>
  </div>;
}

export default App;
