import { FormEvent, useEffect, useRef, useState } from "react";
import BrandAvatar from "./BrandAvatar";
import ChatAnalysisCarousel, {type ChatFeature} from "./ChatAnalysisCarousel";
import { AlertCircle, ArrowRight, LoaderCircle,
  MessageSquare, RefreshCw, Send, ShieldCheck, UserRound } from "lucide-react";

type Operation = "density" | "counts" | "distribution" | "comparisons" | "temporal" |
  "aggregate" | "spatial" | "ranking" | "rotation" | "report";
type Proposal = {
  operation: Operation | null; indicator: "density" | "quantity" | null;
  territory: string; period: string; category: string;
};
type Verification = { source: "BACKEND_PREFLIGHT"; capability_status: "available" | "needs_confirmation" | "unavailable" | "not_selected"; slots: Record<"period" | "category" | "territory", string>; blockers: string[]; ready_to_execute: false; next_action: "confirm_in_interface" };
type Clarification = {code: string; prompt: string; reason: string; source: "CATALOGO_LOCAL";
  choices: {label: string; draft: string}[]; answered: false};
type Reply = { reply: string; proposal: Proposal; verification?: Verification; clarification?: Clarification; requires_confirmation: boolean;
  executed: boolean; origin: string; note: string; model: string; privacy: string };
type Status = { configured: boolean; model: string; requests_used_today: number;
  local_daily_limit: number; provider_quota_verified: boolean; executes_analyses: boolean };
type ChatTurn = { role: "user" | "assistant"; content: string; proposal?: Proposal;
  verification?: Verification; clarification?: Clarification };
type Props = { apiBase: string; privacyAccepted: boolean; file: File | null; sheet: string; mapping: object; options: object; contextReady: boolean; contextVersion: string; validationVersion: string; features: ChatFeature<Operation>[]; active: Operation | null; selecting: boolean; onSelectAnalysis: (operation: Operation) => void; dataset?: string; scope?: string; datasetVersion?: string };
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

export default function AnalysisAssistant({ apiBase, privacyAccepted, file, sheet, mapping, options, contextReady, contextVersion, validationVersion, features, active, selecting, onSelectAnalysis, dataset = "", scope = "auto", datasetVersion = "" }: Props) {
  const hasSource = !!file || !!dataset;
  const [status, setStatus] = useState<Status | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [draft, setDraft] = useState("");
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
    // Mudanças na preparação invalidam respostas pendentes sem apagar a conversa.
    revision.current += 1;
  }, [validationVersion]);
  useEffect(() => {
    if (turns.length) chatEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (sending || !privacyAccepted || message.length < 2 || message.length > 800) return;
    const requestRevision = revision.current;
    const history = turns.filter(t => t.role === "user").slice(-4).map(t => t.content);
    setSending(true);
    setError("");
    try {
      let response: Response;
      if (hasSource && contextReady) {
        const form = new FormData();
        if (dataset) {
          form.append("dataset", dataset); form.append("scope", scope); form.append("dataset_version", datasetVersion);
        } else if (file) form.append("file", file);
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
      if (!validated.proposal || validated.executed !== false ||
          !["INTERPRETACAO_LLM", "CANAL_SISTEMICO"].includes(validated.origin) ||
          (hasSource && contextReady && !!validated.proposal.operation && validated.verification?.source !== "BACKEND_PREFLIGHT"))
        throw new Error("A resposta não atende ao contrato de interpretação e verificação.");
      setTurns(previous => [...previous, {role:"user", content:message},
        {role:"assistant", content:validated.reply, proposal:validated.proposal, verification:validated.verification, clarification:validated.clarification}]);
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
    className="assistant-panel section-anchor rounded-[24px] border border-line bg-white p-5 shadow-sm sm:p-7">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-50">
          <BrandAvatar size={42}/>
        </span>
        <div>
          <h2 className="text-xl font-bold text-ink sm:text-2xl">Converse com o Agente Diagnóstico Territorial</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
            Descreva a análise que deseja realizar. O agente propõe os próximos passos;
            você confere os parâmetros antes de qualquer execução.
          </p>
        </div>
      </div>
    </div>

    {!status?.configured && <div role="status" className="mt-3 rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-900">
      <p>{loadingStatus ? "Conectando à conversa..." : "O Gemini está indisponível. Saudações, orientações do agente e análises determinísticas continuam disponíveis."}</p>
      {!loadingStatus && <button type="button" onClick={() => {void refreshStatus();}}
        className="mt-2 inline-flex items-center gap-1 font-semibold underline">
        <RefreshCw size={13}/> Tentar novamente
      </button>}
    </div>}

    <p className="mt-4 rounded-xl border border-cyan-100 bg-cyan-50/60 px-4 py-3 text-xs leading-5 text-slate-700">
      {hasSource ? contextReady
        ? "Base carregada: o Python confere os campos e requisitos antes de revisar a proposta. Nenhum registro é enviado ao Gemini."
        : "Base em preparação: dúvidas gerais funcionam; propostas contextuais aguardam a validação da base."
        : "Sem base carregada: posso apresentar as análises disponíveis e orientar a importação."}
    </p>
    <div className="mt-5 overflow-hidden rounded-2xl border border-line bg-slate-50/40">
      <div className="flex items-center gap-2 border-b border-line bg-white px-4 py-3 text-xs font-semibold text-slate-600">
        <MessageSquare size={16} className="text-teal"/> Sua conversa {turns.length > 0 ? "· " + turns.length / 2 + " solicitações" : ""}
      </div>
      <div role="log" aria-label="Histórico da conversa" aria-live="polite"
        className="max-h-[540px] min-h-[200px] space-y-4 overflow-y-auto px-4 py-5">
        {!turns.length && <div className="max-w-3xl space-y-3 text-sm text-slate-600">
          <div className="flex items-start gap-3">
            <BrandAvatar size={33} className="shrink-0"/>
            <div>
              <p className="font-bold text-ink">Olá! Que tipo de análise você deseja fazer?</p>
              <p className="mt-1 text-xs leading-6 text-slate-600">
                Posso apresentar os tipos de análise, orientar a preparação dos dados
                e propor próximos passos. Os cálculos são realizados pelo Python, após suas confirmações.
              </p>
            </div>
          </div>
          <ChatAnalysisCarousel features={features} selected={active} disabled={selecting}
            onSelect={onSelectAnalysis}/>
          <p className="pt-2 text-xs font-semibold text-slate-500">Ou experimente uma pergunta:</p>
          <div className="flex flex-wrap gap-2">
            {["Quero analisar a densidade de médicos por município em 202406",
              "Mostre a distribuição de profissionais pelos quintis de densidade",
              "Como evoluiu a quantidade de profissionais ao longo dos períodos?"].map(example =>
              <button type="button" key={example} onClick={() => setDraft(example)}
                className="rounded-full border border-blue-100 bg-white px-3 py-2 text-left text-xs text-slate-600 hover:border-blue-300 hover:bg-blue-50">
                {example}
              </button>)}
          </div>
        </div>}
        {turns.length > 0 && <ChatAnalysisCarousel features={features} selected={active}
          disabled={selecting} onSelect={onSelectAnalysis}/>}
        {turns.map((turn, index) => <div key={index} className={["flex gap-2", turn.role === "user" ? "justify-end" : "justify-start"].join(" ")}>
          {turn.role === "assistant" && <BrandAvatar size={27} className="mt-1 shrink-0"/>}
          <div className={["max-w-[94%] rounded-2xl px-4 py-3 text-sm leading-6 sm:max-w-[85%]",
            turn.role === "user" ? "bg-teal text-white" : "border border-line bg-white text-slate-700"].join(" ")}>
            <p className="whitespace-pre-wrap break-words">{turn.content}</p>
            {turn.role === "assistant" && turn.clarification?.source === "CATALOGO_LOCAL" &&
              turn.clarification.choices.length > 0 &&
              <div className="mt-3 flex flex-wrap gap-2" aria-label="Alternativas de esclarecimento">
                {turn.clarification.choices.map(choice =>
                  <button key={choice.label} type="button"
                    onClick={() => {
                      // Apenas prepara uma manifestação textual; não executa nem confirma.
                      setDraft(choice.draft);
                      document.getElementById("assistant-input")?.focus();
                    }}
                    className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-teal hover:bg-cyan-100">
                    {choice.label}
                  </button>)}
              </div>}
            {turn.proposal && (turn.proposal.operation || turn.proposal.period || turn.proposal.category || turn.proposal.territory) && <div className="mt-3 space-y-2 border-t border-line pt-3 text-xs">
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
      <div className="rounded-2xl border border-blue-200 bg-white shadow-sm transition focus-within:border-teal focus-within:ring-2 focus-within:ring-cyan-100">
        <label className="sr-only" htmlFor="assistant-input">Descreva sua análise ou faça uma pergunta</label>
        <textarea id="assistant-input" rows={3} maxLength={800} value={draft}
          onChange={e => setDraft(e.target.value)} disabled={sending || !privacyAccepted}
          onKeyDown={e => { if(e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault(); e.currentTarget.form?.requestSubmit();
          }}}
          placeholder="Descreva sua análise ou faça uma pergunta..."
          className="block min-h-[106px] w-full resize-y rounded-t-2xl border-0 bg-transparent px-4 py-4 text-sm leading-6 text-ink focus:outline-none"/>
        <div className="flex items-center justify-between gap-3 px-3 pb-3">
          <span className="text-[11px] text-slate-500">Enter para enviar · Shift + Enter para nova linha</span>
          <button type="submit" aria-label="Enviar mensagem" title="Enviar mensagem"
            disabled={!privacyAccepted || draft.trim().length < 2 || sending}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40">
            {sending ? <LoaderCircle size={18} className="animate-spin"/> : <Send size={19}/>}
          </button>
        </div>
      </div>
      {error && <p role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800">
        <AlertCircle size={16} className="shrink-0"/>{error}
      </p>}
      <p className="flex items-center gap-1.5 text-[11px] text-slate-500"><ShieldCheck size={14} className="text-teal"/>
        As mensagens são tratadas para reduzir a exposição de dados antes de serem encaminhadas a um serviço externo de IA. Arquivos e registros individuais não são enviados a esse serviço.
      </p>
    </form>
  </section>;
}
