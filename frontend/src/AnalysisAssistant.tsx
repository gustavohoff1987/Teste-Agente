import { FormEvent, useEffect, useRef, useState, type ReactNode } from "react";
import BrandAvatar from "./BrandAvatar";
import ChatAnalysisCarousel, {type ChatFeature} from "./ChatAnalysisCarousel";
import { scrollAnalysisTo } from "./workspaceNavigation";
import { AlertCircle, ArrowRight, LoaderCircle,
  MessageSquare, RefreshCw, Send, ShieldCheck, UserRound } from "lucide-react";

import { ANALYSIS_LABELS, type Operation } from "./analysisCatalog";
type Proposal = {
  operation: Operation | null; indicator: "density" | "quantity" | null;
  territory: string; period: string; category: string;
};
type Verification = { source: "BACKEND_PREFLIGHT"; capability_status: "available" | "needs_confirmation" | "unavailable" | "not_selected"; slots: Record<"period" | "category" | "territory", string>; blockers: string[]; ready_to_execute: false; next_action: "confirm_in_interface" };
type Clarification = {code: string; prompt: string; reason: string; source: "CATALOGO_LOCAL";
  choices: {label: string; draft: string; operation?: Operation; indicator?: "quantity" | "density" | null}[]; answered: false};
export type TerritorialProposal = {handled: boolean; reply?: string; clarification?: string; operation?: Operation;
  territory_ids?: string[]; pending_operation?: Operation; requested_count?: number | null;
  options_patch?: {period_filter?: string; period_filters?: string[]; temporal_indicator?: "quantity" | "density";
    comparison_indicator?: "quantity" | "density"; component_sum_confirmed?: boolean}; selection_changed?: boolean; reset_selection?: boolean};
type Reply = { exploration?: TerritorialProposal; reply: string; proposal: Proposal; verification?: Verification; clarification?: Clarification; requires_confirmation: boolean;
  executed: boolean; origin: string; note: string; model: string; privacy: string };
type Status = { configured: boolean; model: string; requests_used_today: number;
  local_daily_limit: number; provider_quota_verified: boolean; executes_analyses: boolean };
type ChatTurn = { role: "user" | "assistant"; content: string; proposal?: Proposal;
  verification?: Verification; clarification?: Clarification; request?: string; context?: string };
type Props = { apiBase: string; privacyAccepted: boolean; file: File | null; sheet: string; mapping: object; options: object; contextReady: boolean; contextVersion: string; validationVersion: string; features: ChatFeature<Operation>[]; active: Operation | null; selecting: boolean; onSelectAnalysis: (operation: Operation, proposal?: Proposal) => void; sourceChoice: ReactNode; sourceReady: boolean; sourceSummary: string; preparation: ReactNode; resultContent: ReactNode; dataset?: string; scope?: string; datasetVersion?: string;
  onResolved: (proposal: TerritorialProposal) => string; historyContent: ReactNode; onStarted: () => void; hasResult: boolean; selection: ReactNode; onRequest: (message: string) => void; onExplore: (message: string, choice?: {operation: Operation; indicator?: "quantity" | "density" | null}) => Promise<string | null> };
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

export default function AnalysisAssistant({ apiBase, privacyAccepted, file, sheet, mapping, options, contextReady, contextVersion, validationVersion, features, active, selecting, onSelectAnalysis, sourceChoice, sourceReady, sourceSummary, preparation, resultContent, selection, onRequest, onExplore, historyContent, onStarted, hasResult, onResolved, dataset = "", scope = "auto", datasetVersion = "" }: Props) {
  const hasSource = !!file || !!dataset;
  const [status, setStatus] = useState<Status | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const chatEnd = useRef<HTMLDivElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const analysisRef = useRef<HTMLDivElement>(null);
  const revision = useRef(0);
  const ready = useRef(contextReady);
  ready.current = contextReady;
  const pendingProposal = useRef<Proposal | null>(null);

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
    // Mudanças de fonte invalidam interpretações pendentes, mas não apagam o
    // pedido que levou o usuário a escolher seus dados.
    revision.current += 1;
    setError("");
  }, [contextVersion]);
  useEffect(() => {
    // Mudanças na preparação invalidam respostas pendentes sem apagar a conversa.
    revision.current += 1;
  }, [validationVersion]);
  useEffect(() => {
    if (sourceReady && pendingProposal.current?.operation) {
      const proposal = pendingProposal.current;
      pendingProposal.current = null;
      onSelectAnalysis(proposal.operation!, proposal);
    }
  }, [sourceReady]);
  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTo({top: log.scrollHeight, behavior: "smooth"});
  }, [turns, sourceReady, active]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (sending || !privacyAccepted || message.length < 2 || message.length > 800) return;
    setStarted(true);
    onStarted();
    onRequest(message);
    setTurns(previous => [...previous, {role:"user", content:message}]);
    setDraft("");
    const followup = /^(?:certo[,.! ]*|ok[,.! ]*|sim[,.! ]*|entendi[,.! ]*|vamos[,.! ]*|pode calcular[?.! ]*|quantos? tem[?.! ]*|certo[,.! ]+quantos? tem[?.! ]*|e agora[?.! ]*|continue[?.! ]*)$/i.test(message);
    const append = (content: string) => setTurns(previous => [
      ...previous, {role:"assistant", content}
    ]);
    // Não reinterpretar o mesmo pedido quando a base ou alguma confirmação
    // necessária ainda não foi escolhida. O próximo passo já é conhecido.
    if (!sourceReady && active && followup) {
      append("Para continuar, escolha os dados que deseja utilizar. Depois, mostrarei os campos que precisam da sua confirmação.");
      return;
    }
    if (sourceReady && active && followup) {
      append("Sua análise já está selecionada. Confira os campos e as confirmações na preparação; quando estiverem completos, poderá calcular e ver o resultado no painel de análise.");
      return;
    }
    if (!hasSource && /^(?:ol[aá]|oi|bom dia|boa tarde|boa noite)[!. ]*$/i.test(message)) {
      append(started ? "Olá! Pode perguntar sobre as análises disponíveis ou me contar o que deseja explorar."
        : "Olá! Para começar, prefere usar os dados do Brasil atualmente disponibilizados nesta plataforma ou importar seus próprios dados?");
      return;
    }
    if (hasSource && !sourceReady) {
      append("Estou preparando os dados. Assim que estiverem disponíveis, continuaremos a análise.");
      return;
    }
    // Perguntas sobre o conteúdo da base pública não precisam consumir Gemini
    // nem exigir que o usuário tenha escolhido previamente uma fonte.
    const normalized = message.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    if (/\b(?:dados|base|informacoes)\b/.test(normalized) &&
        /\bbrasil\b/.test(normalized) &&
        /\b(?:o que|quais|contem|possui|tem|disponivel|cobertura|periodos|profissoes|categorias|explicar|descrever)\b/.test(normalized)) {
      setSending(true);
      setError("");
      try {
        const response = await fetch(apiBase + "/api/brazil/description");
        const body = await response.json();
        if (!response.ok || typeof body.description !== "string")
          throw new Error("Não foi possível consultar a descrição.");
        append(body.description);
      } catch {
        append("Ainda não consegui consultar a descrição dos dados do Brasil. Você pode tentar novamente ou importar seus próprios dados.");
      } finally {
        setSending(false);
      }
      return;
    }
    const requestRevision = revision.current;
    const history = turns.filter(t => t.role === "user").slice(-4).map(t => t.content);
    setSending(true);
    setError("");
    try {
      if (sourceReady) {
        const local = await onExplore(message);
        if (local !== null) {append(local); return;}
      }
      // O pré-exame da última seleção pode estar terminando; a mensagem aguarda sem
      // perder o pedido nem pedir ao usuário que o repita.
      if (hasSource) {
        const deadline = Date.now() + 20000;
        while (!ready.current && revision.current === requestRevision && Date.now() < deadline)
          await new Promise(resolve => setTimeout(resolve, 100));
        if (revision.current !== requestRevision) throw new Error("As opções mudaram. Revise o pedido com a preparação atual.");
        if (!ready.current) throw new Error("A validação ainda está em andamento. Aguarde a preparação ficar disponível.");
      }
      let response: Response;
      if (hasSource) {
        const form = new FormData();
        if (dataset) {
          form.append("dataset", dataset); form.append("scope", scope); form.append("dataset_version", datasetVersion);
        } else if (file) form.append("file", file);
        form.append("sheet", sheet);
        form.append("message", message);
        form.append("context_ready", String(ready.current));
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
      const suggested = validated.proposal.operation;
      const resolved = sourceReady && validated.exploration?.handled ? validated.exploration : null;
      const responseText = resolved ? onResolved(resolved) : !sourceReady && suggested
        ? "Entendi. Podemos fazer essa análise de " + ANALYSIS[suggested].toLowerCase() +
          ". Para começar, prefere usar os dados do Brasil atualmente disponibilizados nesta plataforma ou importar os seus? Depois seguiremos diretamente com a análise."
        : validated.reply;
      setTurns(previous => [...previous,
        {role:"assistant", content:responseText, proposal:validated.proposal, verification:validated.verification, clarification:validated.clarification, request:message, context:contextVersion}]);
      // A interpretação escolhe a capacidade, não executa a análise.
      // O usuário ainda confirma recortes e condições metodológicas.
      if (suggested && !resolved) {
        if (!sourceReady) pendingProposal.current = validated.proposal;
        onSelectAnalysis(suggested, validated.proposal);
      }
      void refreshStatus();
    } catch (exc) {
      if (requestRevision === revision.current)
        setError(exc instanceof Error ? exc.message : "Não foi possível acessar a API.");
    } finally {
      setSending(false);
    }
  }

  return <section id="assistente" aria-label="Assistente de análise territorial"
    className="assistant-panel section-anchor conversation-workspace rounded-[24px] border border-line bg-white shadow-sm">
    <header className="no-print workspace-heading">
      <BrandAvatar size={32}/>
      <div><h2 className="font-bold text-ink">Agente Diagnóstico Territorial</h2>
        <p className="text-xs text-slate-500">Converse à esquerda e acompanhe sua análise à direita.</p></div>
    </header>
    <div className="workspace-columns">
    <div className="conversation-pane no-print" data-testid="conversation-pane">
    {!status?.configured && <div role="status" className="mt-3 rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-900">
      <p>{loadingStatus ? "Preparando a conversa..." : "Perguntas livres estão temporariamente indisponíveis. A exploração dos municípios selecionados e os controles de análise continuam disponíveis."}</p>
      {!loadingStatus && <button type="button" onClick={() => {void refreshStatus();}}
        className="mt-2 inline-flex items-center gap-1 font-semibold underline">
        <RefreshCw size={13}/> Tentar novamente
      </button>}
    </div>}

    <div className="conversation-thread">
      <div className="flex items-center gap-2 border-b border-line bg-white px-4 py-3 text-xs font-semibold text-slate-600">
        <MessageSquare size={16} className="text-teal"/> Sua conversa {turns.length > 0 ? "· " + turns.filter(turn => turn.role === "user").length + " solicitações" : ""}
      </div>
      {sourceReady && <p data-testid="current-source" className="border-b border-line bg-white px-4 py-2 text-[11px] text-slate-500">
        Fonte atual: {dataset ? "Dados do Brasil" : file?.name || "Dados importados"}
      </p>}
      <div ref={logRef} role="log" aria-label="Histórico da conversa" aria-live="polite"
        className="conversation-log space-y-4 px-4 py-5" data-testid="conversation-log">
        <div className="max-w-3xl space-y-3 text-sm leading-6 text-slate-700">
          <div className="flex items-start gap-3">
            <BrandAvatar size={33} className="shrink-0"/>
            <div className="space-y-2">
              <p className="font-semibold text-ink">Olá! Sou o Agente Diagnóstico Territorial.</p>
              <p>Conte o que deseja analisar ou faça uma pergunta. Vou orientar os próximos passos.</p>
            </div>
          </div>

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
                    disabled={sending || selecting || !!turn.context && turn.context !== contextVersion}
                    onClick={async () => {
                      if (!choice.operation || !turn.request || !sourceReady) {
                        setDraft(choice.draft); document.getElementById("assistant-input")?.focus(); return;
                      }
                      setSending(true); setError("");
                      setTurns(previous => [...previous,{role:"user",content:"Escolho: " + choice.label}]);
                      onRequest(turn.request);
                      try {
                        const reply = await onExplore(turn.request, {operation:choice.operation,indicator:choice.indicator});
                        setTurns(previous => [...previous,{role:"assistant",content:reply || "Análise escolhida. Revise a preparação à direita."}]);
                      } catch (exc) { setError(exc instanceof Error ? exc.message : "Não foi possível preparar a escolha."); }
                      finally { setSending(false); }
                    }}
                    className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-teal hover:bg-cyan-100">
                    {choice.label}
                  </button>)}
              </div>}

          </div>
          {turn.role === "user" && <UserRound size={17} className="mt-2 shrink-0 text-slate-500"/>}
        </div>)}
        {(started || hasSource) && !sourceReady && <div className="ml-9 space-y-2">
          {!hasSource && <p className="text-sm text-slate-700">Escolha os dados para prosseguirmos:</p>}
          {sourceChoice}
        </div>}
        {sourceReady && <div className="ml-9 max-w-3xl space-y-3 text-sm text-slate-700">
          <details className="no-print text-xs text-teal">
            <summary className="cursor-pointer">Trocar fonte de dados</summary>
            {sourceChoice}
          </details>
          {!active && <p>{sourceSummary || "Seus dados estão disponíveis para análise."} Qual análise você gostaria de realizar?</p>}
          {!active && <ChatAnalysisCarousel features={features} selected={active}
            disabled={selecting} onSelect={onSelectAnalysis}/>}
          {active && <details className="text-xs text-slate-500">
            <summary className="cursor-pointer">Escolher outra análise</summary>
            <div className="mt-2"><ChatAnalysisCarousel features={features} selected={active}
              disabled={selecting} onSelect={onSelectAnalysis}/></div>
          </details>}
        </div>}
        {sending && <p role="status" className="flex items-center gap-2 text-sm text-teal">
          <LoaderCircle size={16} className="animate-spin"/> Interpretando o pedido...
        </p>}
        <div ref={chatEnd}/>
      </div>
    </div>

    <form id="conversation-composer" onSubmit={send} className="conversation-composer space-y-2">
      <div className="rounded-2xl border border-blue-200 bg-white shadow-sm transition focus-within:border-teal focus-within:ring-2 focus-within:ring-cyan-100">
        <label className="sr-only" htmlFor="assistant-input">Descreva sua análise ou faça uma pergunta</label>
        <textarea id="assistant-input" rows={2} maxLength={800} value={draft}
          onChange={e => setDraft(e.target.value)} disabled={sending || !privacyAccepted}
          onKeyDown={e => { if(e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault(); e.currentTarget.form?.requestSubmit();
          }}}
          placeholder="Descreva sua análise ou faça uma pergunta..."
          className="block min-h-[64px] w-full resize-none rounded-t-2xl border-0 bg-transparent px-4 py-4 text-sm leading-6 text-ink focus:outline-none"/>
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
    </div>
    <section className="analysis-pane" data-testid="analysis-pane" aria-label="Área de análises e resultados">
      <div className="analysis-toolbar no-print">
        {historyContent}
        <nav aria-label="Navegar na análise" className="flex gap-2">
          <button type="button" disabled={!active} className="rounded-lg border px-3 py-2 text-xs text-teal disabled:opacity-40"
            onClick={() => scrollAnalysisTo("preparacao-conversacional")}>Ver preparação</button>
          <button type="button" disabled={!hasResult} className="rounded-lg border px-3 py-2 text-xs text-teal disabled:opacity-40"
            onClick={() => scrollAnalysisTo("resultados")}>Ver resultado</button>
        </nav>
      </div>
      <div className="analysis-scroll" ref={analysisRef} data-testid="analysis-scroll">
        {sourceReady && selection}
        {preparation}
        {resultContent}
        {!active && !hasResult && <div className="rounded-2xl border border-dashed border-line bg-slate-50 p-6 text-sm leading-6 text-slate-600">
          <h3 className="font-bold text-ink">Sua análise aparece aqui</h3>
          <p className="mt-2">Escolha os dados e descreva o que deseja comparar, calcular ou explorar. Você pode continuar conversando enquanto consulta os resultados.</p>
        </div>}
      </div>
    </section>
    </div>
  </section>;
}
