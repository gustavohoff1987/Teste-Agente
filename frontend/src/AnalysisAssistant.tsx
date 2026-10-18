import { FormEvent, useEffect, useRef, useState, type ReactNode } from "react";
import BrandAvatar from "./BrandAvatar";
import ChatAnalysisCarousel, {type ChatFeature} from "./ChatAnalysisCarousel";
import { AlertCircle, ArrowRight, LoaderCircle,
  MessageSquare, RefreshCw, Send, ShieldCheck, UserRound } from "lucide-react";

import { ANALYSIS_LABELS, type Operation } from "./analysisCatalog";
import { sessionFetch as fetch, contextRevision } from "./conversationSession";
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
type Props = { displayedResultId?: string; apiBase: string; privacyAccepted: boolean; file: File | null; sheet: string; mapping: object; options: object; contextReady: boolean; contextVersion: string; validationVersion: string; features: ChatFeature<Operation>[]; active: Operation | null; selecting: boolean; onSelectAnalysis: (operation: Operation, proposal?: Proposal) => void; sourceChoice: ReactNode; sourceReady: boolean; sourceSummary: string; preparation: ReactNode; resultContent: ReactNode; resultsOnly?: boolean; dataset?: string; scope?: string; datasetVersion?: string;
  onChooseBrazil: () => void; onChooseImport: () => void; onResolved: (proposal: TerritorialProposal) => string; catalogOpen: boolean; running: boolean; investigationContent: ReactNode; onStarted: () => void; hasResult: boolean; selection: ReactNode; onRequest: (message: string) => void; onExplore: (message: string, choice?: {operation: Operation; indicator?: "quantity" | "density" | null}) => Promise<string | null> };
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

export default function AnalysisAssistant({ displayedResultId = "", apiBase, privacyAccepted, file, sheet, mapping, options, contextReady, contextVersion, validationVersion, features, active, selecting, onSelectAnalysis, sourceChoice, sourceReady, sourceSummary, preparation, resultContent, selection, onRequest, onExplore, catalogOpen, running, investigationContent, onStarted, hasResult, onChooseBrazil, onChooseImport, onResolved, resultsOnly = false, dataset = "", scope = "auto", datasetVersion = "" }: Props) {
  const hasSource = !!file || !!dataset;
  const [status, setStatus] = useState<Status | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);



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
  }, [validationVersion, displayedResultId]);
  useEffect(() => {
    if (sourceReady && pendingProposal.current?.operation) {
      const proposal = pendingProposal.current;
      pendingProposal.current = null;
      onSelectAnalysis(proposal.operation!, proposal);
    }
  }, [sourceReady]);
  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTo({top: log.scrollHeight, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});
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
    // A resposta à escolha de fonte pertence à etapa ativa, não ao interpretador analítico.
    // Botões e texto compartilham as mesmas ações de seleção governadas pelo App.
    if (!hasSource) {
      const sourceReply = message.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase()
        .replace(/[.,!?]/g, " ").replace(/\\s+/g, " ").trim();
      if (/^(?:(?:quero|vou|prefiro|usar|utilizar|escolho|seleciono|pode usar|quero usar) )*(?:(?:os|a|a base|a base de|a base do) )?(?:dados do brasil|base do brasil|base brasileira|brasil)$/.test(sourceReply)) {
        onChooseBrazil();
        setTurns(previous => [...previous, {role:"assistant", content:"Dados do Brasil selecionados. Vou preparar a fonte oficial; depois escolha a análise desejada."}]);
        return;
      }
      if (/^(?:(?:quero|vou|prefiro|usar|utilizar|escolho|seleciono|quero usar) )*(?:importar|upload|enviar arquivo|meus dados|importar meus dados|importar arquivo)$/.test(sourceReply)) {
        onChooseImport();
        setTurns(previous => [...previous, {role:"assistant", content:"Selecione o arquivo CSV ou Excel que deseja importar."}]);
        return;
      }
    }
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
    if (sourceReady && active && followup && /^(?:pode calcular|sim|vamos)[?.! ]*$/i.test(message)) {
      append("Sua análise já está selecionada. Confira os campos e as confirmações na preparação; quando estiverem completos, poderá calcular e ver o resultado nesta investigação.");
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
        form.append("context_revision", String(contextRevision()));
        form.append("displayed_result_id", displayedResultId);
        form.append("mapping", JSON.stringify(mapping));
        form.append("options", JSON.stringify(options));
        response = await fetch(apiBase + "/api/llm/interpret-context", { method: "POST", body: form });
      } else {
        response = await fetch(apiBase + "/api/llm/interpret", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, history, context_revision: contextRevision() }),
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
    <div className="integrated-investigation" data-results-focus={resultsOnly}>
    <div className="conversation-pane no-print" data-testid="conversation-pane">
    <div className="agent-guidance">
      <BrandAvatar size={46}/><div><h2 className="font-bold text-ink">Agente Diagnóstico Territorial</h2>
      <p>{running ? "Estou acompanhando a execução pelo motor determinístico." : hasResult ? "Vamos explorar os resultados e continuar a investigação." : sourceReady ? active ? "Confira os recortes e as confirmações para calcular." : sourceSummary : "Olá! Conte o que deseja analisar ou escolha seus dados para começar."}</p></div>
    </div>
    {!status?.configured && <div role="status" className="mt-3 rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-900">
      <p>{loadingStatus ? "Preparando a conversa..." : "Perguntas livres estão temporariamente indisponíveis. A exploração dos municípios selecionados e os controles de análise continuam disponíveis."}</p>
      {!loadingStatus && <button type="button" onClick={() => {void refreshStatus();}}
        className="mt-2 inline-flex items-center gap-1 font-semibold underline">
        <RefreshCw size={13}/> Tentar novamente
      </button>}
    </div>}

    {/* As mensagens continuam em memória para contexto, sem histórico visual.
        As alternativas de esclarecimento permanecem disponíveis junto à resposta atual. */}
    {turns.at(-1)?.role === "assistant" && turns.at(-1)?.clarification?.source === "CATALOGO_LOCAL" &&
      <div className="mx-4 mb-3 flex flex-wrap gap-2" aria-label="Alternativas de esclarecimento">
        {turns.at(-1)!.clarification!.choices.map(choice =>
          <button key={choice.label} type="button" disabled={sending || selecting}
            onClick={async () => {
              const current = turns.at(-1)!;
              if (!choice.operation || !current.request || !sourceReady) {
                setDraft(choice.draft); document.getElementById("assistant-input")?.focus(); return;
              }
              setSending(true); setError("");
              setTurns(previous => [...previous,{role:"user",content:"Escolho: " + choice.label}]);
              onRequest(current.request);
              try {
                const reply = await onExplore(current.request, {operation:choice.operation,indicator:choice.indicator});
                setTurns(previous => [...previous,{role:"assistant",content:reply || "Análise escolhida. Revise a preparação abaixo."}]);
              } catch (exc) { setError(exc instanceof Error ? exc.message : "Não foi possível preparar a escolha."); }
              finally { setSending(false); }
            }}
            className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-teal hover:bg-cyan-100">{choice.label}</button>)}
      </div>}
    {!sourceReady && <div className="px-4 pb-4">{sourceChoice}</div>}
    {sourceReady && <div className="px-4 pb-4">
      <details className="no-print text-xs text-teal"><summary className="cursor-pointer">Trocar fonte de dados</summary>{sourceChoice}</details>
      <p data-testid="current-source" className="mt-2 text-xs text-slate-500">Fonte atual: {dataset ? "Dados do Brasil" : file?.name || "Dados importados"}</p>
    </div>}
    {(catalogOpen || sourceReady && !active) && <div className="px-4 pb-4" data-testid="analysis-catalog">
      <ChatAnalysisCarousel features={features} selected={active} disabled={selecting} onSelect={onSelectAnalysis}/>
    </div>}
    {active && !catalogOpen && <details className="m-4 mt-0 text-xs text-teal">
      <summary className="cursor-pointer">Escolher outra análise</summary>
      <ChatAnalysisCarousel features={features} selected={active} disabled={selecting} onSelect={onSelectAnalysis}/>
    </details>}
    </div>
    <section className="analysis-pane" data-testid="analysis-pane" aria-label="Área de análises e resultados">
      <div className="analysis-scroll" data-testid="analysis-scroll">
        {investigationContent}
        <div className="preparation-context" data-testid="preparation-context">
          {sourceReady && active && turns.at(-1)?.role === "assistant" && <div className="latest-reply mb-3" role="status" data-testid="latest-reply">
            <BrandAvatar size={30}/><p className="whitespace-pre-wrap">{turns.at(-1)?.content}</p>
          </div>}
          {sourceReady && active && <div className="agent-guidance no-print"><BrandAvatar size={36}/><p>Vamos preparar {ANALYSIS[active].toLowerCase()}. Escolha os territórios, períodos e parâmetros abaixo; as validações orientam o que falta confirmar.</p></div>}
          {sourceReady && selection}
          {preparation}
        </div>
        {resultContent}
        {resultsOnly && !hasResult && <p className="p-4 text-sm">Seus resultados aparecerão aqui após o primeiro cálculo. Comece em Nova análise ou converse comigo.</p>}
      </div>
    </section>
    <div className="conversation-dock no-print" data-testid="conversation-dock">
      {(!sourceReady || !active) && turns.at(-1) && <div className="latest-reply" role="status" data-testid="latest-reply">
        {turns.at(-1)?.role === "assistant" ? <BrandAvatar size={30}/> : <UserRound size={25} aria-label="Seu pedido"/>}<div><p className="whitespace-pre-wrap">{turns.at(-1)?.content}</p>

      </div>}
      {sending && <p role="status" className="flex items-center gap-2 px-4 pt-2 text-sm text-teal"><LoaderCircle size={16} className="animate-spin"/>Interpretando o pedido…</p>}
    <form id="conversation-composer" onSubmit={send} className="conversation-composer space-y-2">
      <div className="conversation-input-shell rounded-2xl border-2 bg-white shadow-sm transition">
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
            className="conversation-send inline-flex h-10 w-10 items-center justify-center rounded-xl text-white transition disabled:cursor-not-allowed disabled:opacity-40">
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

    </div>
  </section>;
}
