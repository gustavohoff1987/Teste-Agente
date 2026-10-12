import { FormEvent, useEffect, useRef, useState, type ReactNode } from "react";
import BrandAvatar from "./BrandAvatar";
import ChatAnalysisCarousel, {type ChatFeature} from "./ChatAnalysisCarousel";
import { AlertCircle, ArrowRight, LoaderCircle,
  MessageSquare, RefreshCw, Send, ShieldCheck, UserRound } from "lucide-react";

import { ANALYSIS_LABELS, type Operation } from "./analysisCatalog";
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
type Props = { apiBase: string; privacyAccepted: boolean; file: File | null; sheet: string; mapping: object; options: object; contextReady: boolean; contextVersion: string; validationVersion: string; features: ChatFeature<Operation>[]; active: Operation | null; selecting: boolean; onSelectAnalysis: (operation: Operation) => void; sourceChoice: ReactNode; sourceReady: boolean; sourceSummary: string; preparation: ReactNode; resultContent: ReactNode; dataset?: string; scope?: string; datasetVersion?: string };
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

const ANALYSIS = ANALYSIS_LABELS;

export default function AnalysisAssistant({ apiBase, privacyAccepted, file, sheet, mapping, options, contextReady, contextVersion, validationVersion, features, active, selecting, onSelectAnalysis, sourceChoice, sourceReady, sourceSummary, preparation, resultContent, dataset = "", scope = "auto", datasetVersion = "" }: Props) {
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
      if (hasSource) {
        const form = new FormData();
        if (dataset) {
          form.append("dataset", dataset); form.append("scope", scope); form.append("dataset_version", datasetVersion);
        } else if (file) form.append("file", file);
        form.append("sheet", sheet);
        form.append("message", message);
        form.append("context_ready", String(contextReady));
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
          (hasSource && !!validated.proposal.operation && validated.verification?.source !== "BACKEND_PREFLIGHT"))
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
            você ajusta o que for necessário e acompanha os resultados aqui mesmo.
          </p>
        </div>
      </div>
    </div>

    {!status?.configured && <div role="status" className="mt-3 rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-900">
      <p>{loadingStatus ? "Preparando a conversa..." : "O assistente está temporariamente indisponível para perguntas livres. Você ainda pode escolher e executar análises."}</p>
      {!loadingStatus && <button type="button" onClick={() => {void refreshStatus();}}
        className="mt-2 inline-flex items-center gap-1 font-semibold underline">
        <RefreshCw size={13}/> Tentar novamente
      </button>}
    </div>}

    <div className="mt-5 overflow-hidden rounded-2xl border border-line bg-slate-50/40">
      <div className="flex items-center gap-2 border-b border-line bg-white px-4 py-3 text-xs font-semibold text-slate-600">
        <MessageSquare size={16} className="text-teal"/> Sua conversa {turns.length > 0 ? "· " + turns.length / 2 + " solicitações" : ""}
      </div>
      <div role="log" aria-label="Histórico da conversa" aria-live="polite"
        className="min-h-[200px] space-y-4 px-4 py-5">
        <div className="max-w-3xl space-y-3 text-sm leading-6 text-slate-700">
          <div className="flex items-start gap-3">
            <BrandAvatar size={33} className="shrink-0"/>
            <div className="space-y-2">
              <p className="font-semibold text-ink">Olá! Vamos começar pelos seus dados.</p>
              <p>Você prefere utilizar as fontes brasileiras ou importar uma base própria?</p>
            </div>
          </div>
          {sourceChoice}
          {sourceReady && <>
            <div className="flex items-start gap-3 pt-2">
              <BrandAvatar size={33} className="shrink-0"/>
              <div className="space-y-2">
                <p>{sourceSummary || "Seus dados estão disponíveis para análise."}</p>
                <p>Que tipo de análise você deseja realizar?</p>
              </div>
            </div>
            <ChatAnalysisCarousel features={features} selected={active}
              disabled={selecting} onSelect={onSelectAnalysis}/>
          </>}
          {!sourceReady && <p className="text-xs text-slate-500">Você também pode escrever sua pergunta abaixo.</p>}
        </div>
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
            {turn.proposal && (turn.proposal.operation || turn.proposal.period || turn.proposal.category || turn.proposal.territory) && <div className="mt-3 space-y-2 text-xs leading-6">
              <p>Podemos seguir com {turn.proposal.operation ? ANALYSIS[turn.proposal.operation].toLowerCase() : "sua análise"}
                {turn.proposal.period ? " no período " + turn.proposal.period : ""}
                {turn.proposal.category ? ", para " + turn.proposal.category : ""}.
                Você poderá ajustar os campos na própria conversa.</p>
              {turn.proposal.operation && <button type="button"
                onClick={() => onSelectAnalysis(turn.proposal!.operation!)}
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-2 py-1 font-semibold text-teal hover:bg-blue-50">
                Continuar com {ANALYSIS[turn.proposal.operation]} <ArrowRight size={13}/>
              </button>}
              {turn.verification?.capability_status === "unavailable" &&
                <p className="text-amber-800">Ainda há informações necessárias para essa análise. Confira as opções abaixo.</p>}
            </div>}
          </div>
          {turn.role === "user" && <UserRound size={17} className="mt-2 shrink-0 text-slate-500"/>}
        </div>)}
        {preparation}
        {resultContent}
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
      <details className="text-[11px] text-slate-500"><summary className="cursor-pointer">Privacidade da conversa</summary>
        <p className="mt-1">As mensagens passam por proteção de identificadores. Arquivos e registros individuais não são enviados ao serviço de IA.</p>
      </details>
    </form>
  </section>;
}
