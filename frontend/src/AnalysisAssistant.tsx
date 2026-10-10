import { FormEvent, useEffect, useRef, useState } from "react";
import { AlertCircle, ArrowRight, BrainCircuit, CheckCircle2, LoaderCircle,
  MessageSquare, RefreshCw, Send, ShieldCheck, UserRound } from "lucide-react";

type Operation = "density" | "counts" | "distribution" | "comparisons" | "temporal" |
  "aggregate" | "spatial" | "ranking" | "rotation" | "report";
type Proposal = {
  operation: Operation | null; indicator: "density" | "quantity" | null;
  territory: string; period: string; category: string;
};
type Verification = { source: "BACKEND_PREFLIGHT"; capability_status: "available" | "needs_confirmation" | "unavailable" | "not_selected"; slots: Record<"period" | "category" | "territory", string>; blockers: string[]; ready_to_execute: false; next_action: "confirm_in_interface" };
type Reply = { reply: string; proposal: Proposal; verification?: Verification; requires_confirmation: boolean;
  executed: boolean; origin: string; note: string; model: string; privacy: string };
type Status = { configured: boolean; model: string; requests_used_today: number;
  local_daily_limit: number; provider_quota_verified: boolean; executes_analyses: boolean };
type ChatTurn = { role: "user" | "assistant"; content: string; proposal?: Proposal; verification?: Verification };
type Props = { apiBase: string; file: File | null; sheet: string; mapping: object; options: object; contextReady: boolean; contextVersion: string; onSelectAnalysis: (operation: Operation) => void };
const STATUS_LABEL: Record<Verification["capability_status"], string> = {
  available: "Requisitos técnicos atendidos no pré-exame; ainda depende da confirmação humana",
  needs_confirmation: "Há confirmações ou parâmetros pendentes",
  unavailable: "Capacidade não habilitada com a configuração atual",
  not_selected: "Capacidade não identificada",
};
const SLOT_LABEL: Record<string, string> = {
  found_in_dataset: "Encontrado na base",
  not_confirmed_in_dataset: "Não confirmado nos valores da base",
  not_requested: "Não informado",
  requires_unit_confirmation: "Confirmar unidade e nível territorial",
};

const ANALYSIS: Record<Operation, string> = {
  density: "Densidade", counts: "Quantitativos", distribution: "Distribuição",
  comparisons: "Comparações", temporal: "Evolução temporal", aggregate: "Agregações",
  spatial: "Análise espacial", ranking: "Rankings e recortes",
  rotation: "Rotatividade", report: "Relatórios",
};

export default function AnalysisAssistant({ apiBase, file, sheet, mapping, options, contextReady, contextVersion, onSelectAnalysis }: Props) {
  const [status, setStatus] = useState<Status | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [draft, setDraft] = useState("");
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const chatEnd = useRef<HTMLDivElement>(null);
  const revision = useRef(0);

  async function refreshStatus() {
    setLoadingStatus(true);
    try {
      const response = await fetch(apiBase + "/api/llm/status");
      if (!response.ok) throw new Error("Serviço de IA indisponível.");
      const body = await response.json() as Status;
      setStatus(body);
    } catch {
      setStatus(null);
    } finally {
      setLoadingStatus(false);
    }
  }

  useEffect(() => { void refreshStatus(); }, [apiBase]);
  useEffect(() => {
    // A nova base ou os novos parâmetros invalidam propostas anteriores.
    revision.current += 1;
    setTurns([]);
    setError("");
  }, [contextVersion]);
  useEffect(() => {
    if (turns.length) chatEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (sending || !status?.configured || !privacyAccepted || message.length < 3 || message.length > 800 ||
        (!!file && !contextReady)) return;
    const requestRevision = revision.current;
    const history = turns.filter(t => t.role === "user").slice(-4).map(t => t.content);
    setSending(true);
    setError("");
    try {
      let response: Response;
      if (file) {
        const form = new FormData();
        form.append("file", file);
        form.append("sheet", sheet);
        form.append("message", message);
        form.append("history", JSON.stringify(history));
        form.append("mapping", JSON.stringify(mapping));
        form.append("options", JSON.stringify(options));
        response = await fetch(apiBase + "/api/llm/interpret-context", { method: "POST", body: form });
      } else {
        response = await fetch(apiBase + "/api/llm/interpret", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, history }),
        });
      }
      const body = await response.json();
      if (requestRevision !== revision.current) return;
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Não foi possível interpretar o pedido.");
      const validated = body as Reply;
      if (!validated.proposal || validated.executed !== false || validated.origin !== "INTERPRETACAO_LLM" ||
          (!!file && validated.verification?.source !== "BACKEND_PREFLIGHT"))
        throw new Error("A resposta não atende ao contrato de interpretação e verificação.");
      setTurns(previous => [...previous, {role:"user", content:message},
        {role:"assistant", content:validated.reply, proposal:validated.proposal, verification:validated.verification}]);
      setDraft("");
      void refreshStatus();
    } catch (exc) {
      if (requestRevision === revision.current)
        setError(exc instanceof Error ? exc.message : "Não foi possível acessar a API.");
    } finally {
      setSending(false);
    }
  }

  return <section id="assistente" aria-label="Assistente de análise territorial"
    className="section-anchor mt-14 rounded-[24px] border border-cyan-100 bg-white p-5 shadow-card sm:p-7">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        <span className="rounded-xl bg-cyan-50 p-3 text-teal"><BrainCircuit size={23}/></span>
        <div><p className="text-[11px] font-bold uppercase tracking-[.19em] text-teal">Interação assistida · experimental</p>
          <h2 className="mt-1 text-xl font-bold text-ink sm:text-2xl">Converse sobre a análise que deseja realizar</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Descreva seu objetivo em linguagem natural. O Gemini propõe uma capacidade analítica;
            você confere e decide se deseja prosseguir. Nenhum cálculo é executado nesta conversa.
          </p></div>
      </div>
      <div className="no-print flex items-center gap-2">
        <span aria-live="polite" className={["rounded-full px-3 py-1.5 text-xs font-semibold",
          status?.configured ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"].join(" ")}>
          {status?.configured ? "Gemini configurado" : "Gemini não configurado"}
        </span>
        <button type="button" onClick={() => {void refreshStatus();}} disabled={loadingStatus}
          aria-label="Verificar configuração do Gemini"
          className="rounded-lg border border-line p-2 text-slate-600 hover:bg-slate-50 disabled:opacity-50">
          <RefreshCw size={16} className={loadingStatus ? "animate-spin" : ""}/>
        </button>
      </div>
    </div>

    {status?.configured && <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-600">
      <span>Modelo: <strong>{status.model}</strong></span>
      <span>Contador local: <strong>{status.requests_used_today}/{status.local_daily_limit}</strong> solicitações no dia</span>
      <span className="text-amber-700">Franquia e faturamento da Google não verificados pelo aplicativo.</span>
    </div>}
    {!status?.configured && <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-900">
      A conversação ainda não está disponível. Configure a variável de ambiente
      <code className="mx-1 rounded bg-white px-1.5 py-0.5">GEMINI_API_KEY</code>
      no terminal do backend Python e reinicie o servidor. Não informe sua chave neste campo,
      no GitHub ou na interface.
    </p>}

    <p className="mt-4 rounded-xl border border-cyan-100 bg-cyan-50/60 px-4 py-3 text-xs leading-5 text-slate-700">
      {file ? contextReady
        ? "Base carregada: o Python confere os campos e requisitos antes de revisar a proposta. Nenhum registro é enviado ao Gemini."
        : "Aguarde a validação da base para ativar a interpretação contextual."
        : "Sem base carregada: interpretação preliminar, sem verificar períodos ou categorias mencionados."}
    </p>
    <div className="mt-6 overflow-hidden rounded-2xl border border-line bg-slate-50/50">
      <div className="flex items-center gap-2 border-b border-line bg-white px-4 py-3 text-xs font-semibold text-slate-600">
        <MessageSquare size={16} className="text-teal"/> Conversa nesta aba · {turns.length / 2} solicitações concluídas
      </div>
      <div role="log" aria-label="Histórico da conversa" aria-live="polite"
        className="max-h-[400px] min-h-[150px] space-y-4 overflow-y-auto px-4 py-5">
        {!turns.length && <div className="max-w-2xl space-y-2 text-sm text-slate-600">
          <p className="font-semibold text-ink">Exemplos de objetivos:</p>
          <p>“Quero analisar a densidade de médicos por município em 202406.”</p>
          <p>“Mostre a distribuição de profissionais pelos quintis de densidade.”</p>
          <p className="text-xs text-slate-500">Não digite nomes de pessoas, identificadores individuais, CPFs nem dados sensíveis.</p>
        </div>}
        {turns.map((turn, index) => <div key={index} className={["flex gap-2", turn.role === "user" ? "justify-end" : "justify-start"].join(" ")}>
          {turn.role === "assistant" && <BrainCircuit size={17} className="mt-2 shrink-0 text-teal"/>}
          <div className={["max-w-[94%] rounded-2xl px-4 py-3 text-sm leading-6 sm:max-w-[85%]",
            turn.role === "user" ? "bg-teal text-white" : "border border-line bg-white text-slate-700"].join(" ")}>
            <p className="whitespace-pre-wrap break-words">{turn.content}</p>
            {turn.proposal && <div className="mt-3 space-y-2 border-t border-line pt-3 text-xs">
              <p className="font-semibold text-slate-700">Proposta sujeita a confirmação</p>
              {turn.proposal.period && <p>Período mencionado: {turn.proposal.period}</p>}
              {turn.proposal.category && <p>Categoria mencionada: {turn.proposal.category}</p>}
              {turn.proposal.territory && <p>Território mencionado: {turn.proposal.territory}</p>}
              {turn.proposal.operation && <button type="button"
                onClick={() => onSelectAnalysis(turn.proposal!.operation!)}
                className="no-print inline-flex items-center gap-2 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 font-bold text-teal hover:bg-cyan-100">
                Ver requisitos de {ANALYSIS[turn.proposal.operation]} <ArrowRight size={14}/>
              </button>}
              {turn.verification && <div className="rounded-xl border border-cyan-100 bg-cyan-50/60 p-3 text-slate-700">
                <p className="font-semibold">Revisão determinística do Python</p>
                <p className="mt-1">{STATUS_LABEL[turn.verification.capability_status]}</p>
                {(["period", "category", "territory"] as const).filter(k => !!turn.proposal?.[k]).map(k =>
                  <p key={k} className="mt-1">{k === "period" ? "Período" : k === "category" ? "Categoria" : "Território"}: {" "}
                    {SLOT_LABEL[turn.verification!.slots[k]] || "Verificação pendente"}</p>)}
                {turn.verification.blockers.length > 0 && <div className="mt-2">
                  <p className="font-semibold">Pontos a resolver:</p>
                  <ul className="ml-4 mt-1 list-disc space-y-1">{turn.verification.blockers.map((reason, i) =>
                    <li key={i}>{reason}</li>)}</ul>
                </div>}
              </div>}
              <p className="text-slate-500">A seleção apenas abre a capacidade; não autoriza cálculo nem confirma campos.</p>
            </div>}
          </div>
          {turn.role === "user" && <UserRound size={17} className="mt-2 shrink-0 text-slate-500"/>}
        </div>)}
        {sending && <p role="status" className="flex items-center gap-2 text-sm text-teal">
          <LoaderCircle size={16} className="animate-spin"/> Interpretando o pedido...
        </p>}
        <div ref={chatEnd}/>
      </div>
    </div>

    <form onSubmit={send} className="no-print mt-4 space-y-3">
      <label className="block text-xs font-bold text-slate-700" htmlFor="assistant-input">Seu pedido de análise</label>
      <textarea id="assistant-input" rows={3} maxLength={800} value={draft}
        onChange={e => setDraft(e.target.value)} disabled={sending}
        placeholder="Ex.: quero comparar a densidade de médicos entre municípios em junho de 2024"
        className="w-full resize-y rounded-xl border border-line bg-white px-4 py-3 text-sm leading-6 text-ink focus:border-teal focus:outline-none"/>
      <label className="flex items-start gap-2 text-xs leading-5 text-slate-600">
        <input type="checkbox" className="mt-0.5" checked={privacyAccepted} onChange={e => setPrivacyAccepted(e.target.checked)}/>
        <span>Confirmo que meu pedido não contém dados pessoais, identificadores ou informações sensíveis.
          Estou ciente de que o texto minimizado é enviado à API externa do Gemini.</span>
      </label>
      {error && <p role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800">
        <AlertCircle size={16} className="shrink-0"/>{error}
      </p>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-xs text-slate-500"><ShieldCheck size={15} className="text-teal"/>
          O arquivo importado não é enviado ao Gemini; as análises continuam no Python.</p>
        <button type="submit" disabled={!status?.configured || !privacyAccepted || draft.trim().length < 3 || sending || (!!file && !contextReady)}
          className="inline-flex items-center gap-2 rounded-xl bg-teal px-5 py-3 text-sm font-bold text-white hover:bg-ink disabled:cursor-not-allowed disabled:opacity-40">
          {sending ? <LoaderCircle size={17} className="animate-spin"/> : <Send size={17}/>}
          {sending ? "Enviando..." : "Interpretar com Gemini"}
        </button>
      </div>
    </form>
    <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-slate-500">
      <CheckCircle2 size={14} className="mt-0.5 shrink-0"/>
      Iteração 2: o Python examina o contexto da base e os requisitos antes de apresentar a proposta.
      O Gemini não executa análises, não define parâmetros substantivos nem substitui a confirmação humana.
    </p>
  </section>;
}
