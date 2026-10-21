import { FormEvent, useEffect, useRef, useState, type ReactNode } from "react";
import {navigationCommand, normalizeCommand, previousResultCommand, viewCommand, type NavigationTarget, type ResultView,
  type WorkspaceStage} from "./workspaceNavigation";
import BrandAvatar from "./BrandAvatar";
import ChatAnalysisCarousel, {type ChatFeature} from "./ChatAnalysisCarousel";
import ChatFloatingBox from "./ChatFloatingBox";
import { AlertCircle, ArrowRight, LayoutDashboard, LoaderCircle, MapPin,
  MessageSquare, RefreshCw, Send, ShieldCheck, UserRound } from "lucide-react";

import { ANALYSIS_LABELS, type Operation } from "./analysisCatalog";
import { sessionFetch as fetch, contextRevision } from "./conversationSession";
type Proposal = {
  operation: Operation | null; indicator: "density" | "quantity" | null;
  territory: string; period: string; category: string;
};
type Verification = { source: "BACKEND_PREFLIGHT"; capability_status: "available" | "needs_confirmation" | "unavailable" | "not_selected"; slots: Record<"period" | "category" | "territory", string>; blockers: string[]; ready_to_execute: false; next_action: "confirm_in_interface" };
/** Alternativa de esclarecimento: com operation, reinterpreta o pedido com a escolha; com send, envia o rascunho como
 * mensagem do usuário (por exemplo, uma das leituras de "últimos 5 anos"); sem nenhum dos dois, vai para a caixa de texto. */
type ClarificationChoice = {label: string; draft: string; operation?: Operation; indicator?: "quantity" | "density" | null;
  send?: boolean};
type Clarification = {code: string; prompt: string; reason: string; source: "CATALOGO_LOCAL";
  choices: ClarificationChoice[]; answered: false};
/** Resposta da interpretação local (sem o provedor de IA), com as alternativas quando a conversa pergunta. */
export type LocalAnswer = {text: string; choices?: ClarificationChoice[]};
export type TerritorialProposal = {handled: boolean; reply?: string; clarification?: string; operation?: Operation;
  /** Estados citados como objeto (prefixo IBGE), na base oficial: vão para a abrangência territorial. */
  territory_ids?: string[]; estados?: string[]; pending_operation?: Operation; requested_count?: number | null;
  options_patch?: {period_filter?: string; period_filters?: string[]; temporal_indicator?: "quantity" | "density";
    comparison_indicator?: "quantity" | "density"}; selection_changed?: boolean; reset_selection?: boolean;
  /** Leituras de "últimos N anos" (AT-34): a conversa pergunta, com uma alternativa para cada leitura. */
  choices?: ClarificationChoice[]};
type Reply = { exploration?: TerritorialProposal; dialogue_action?: string; reply: string; proposal: Proposal; verification?: Verification; clarification?: Clarification; requires_confirmation: boolean;
  executed: boolean; origin: string; note: string; model: string; privacy: string };
type Status = { configured: boolean; model: string; requests_used_today: number;
  local_daily_limit: number; provider_quota_verified: boolean; executes_analyses: boolean };
type ChatTurn = { role: "user" | "assistant"; content: string; proposal?: Proposal;
  verification?: Verification; clarification?: Clarification; request?: string; context?: string };
type Props = { notice: string; workspaceStage: WorkspaceStage; onStage: (stage: NavigationTarget) => void; onMultiplePeriods: () => boolean;
  territorySummary?: {label: string; text: string; selected: boolean; selectable: boolean}; territoriesOpen: boolean; onTerritoriesOpen: (open: boolean) => void; displayedResultId?: string; apiBase: string; privacyAccepted: boolean; file: File | null; sheet: string; mapping: object; options: object; contextReady: boolean; contextVersion: string; validationVersion: string; features: ChatFeature<Operation>[]; active: Operation | null; selecting: boolean; onSelectAnalysis: (operation: Operation, proposal?: Proposal) => void; sourceChoice: ReactNode; sourceReady: boolean; sourceSummary: string; preparation: ReactNode; resultContent: ReactNode; resultsOnly?: boolean; dataset?: string; scope?: string; datasetVersion?: string;
  onChooseBrazil: () => void; onChooseImport: () => void; onResolved: (proposal: TerritorialProposal) => string; catalogOpen: boolean; running: boolean; investigationContent: ReactNode; onStarted: () => void; hasResult: boolean; selection: ReactNode; onRequest: (message: string) => void; onExplore: (message: string, choice?: {operation: Operation; indicator?: "quantity" | "density" | null}) => Promise<LocalAnswer | null>;
  /** Reabre o resultado anterior da sessão, sem recalcular, e devolve a resposta da conversa. */
  onPreviousResult: () => string;
  /** "painel": só no painel integrado, a conversa (alternativas, última resposta e campo de envio) vai para uma caixa
   * flutuante arrastável, com os mesmos ids e textos; a preparação e os resultados clássicos ficam montados e ocultos.
   * Sem a propriedade, o layout do chat é o de sempre. */
  layout?: "classico" | "painel";
  /** Com a base do Brasil pronta: botão "Abrir o painel integrado" junto da fonte atual. */
  onOpenPainel?: () => void };
const VIEW_LABEL: Record<ResultView, string> = {mapa: "Mapa", graficos: "Gráficos", tabela: "Tabela"};
const VIEW_ACTION = new Map<string, ResultView>([["show_map", "mapa"], ["show_chart", "graficos"], ["show_table", "tabela"]]);
const STATUS_LABEL: Record<Verification["capability_status"], string> = {
  available: "Requisitos técnicos atendidos no pré-exame; ainda depende da sua execução na preparação",
  needs_confirmation: "Há escolhas pendentes",
  unavailable: "Capacidade não habilitada com a configuração atual",
  not_selected: "Capacidade não identificada",
};
const SLOT_LABEL: Record<string, string> = {
  found_in_dataset: "Encontrado na base",
  not_confirmed_in_dataset: "Não encontrado nos valores da base",
  not_requested: "Não informado",
  set_in_scope: "Definido na abrangência territorial",
};

const ANALYSIS = ANALYSIS_LABELS;

export default function AnalysisAssistant({ notice, workspaceStage, onStage: setWorkspaceStage, onMultiplePeriods, territorySummary, territoriesOpen, onTerritoriesOpen, displayedResultId = "", apiBase, privacyAccepted, file, sheet, mapping, options, contextReady, contextVersion, validationVersion, features, active, selecting, onSelectAnalysis, sourceChoice, sourceReady, sourceSummary, preparation, resultContent, selection, onRequest, onExplore, catalogOpen, running, investigationContent, onStarted, hasResult, onChooseBrazil, onChooseImport, onResolved, onPreviousResult, resultsOnly = false, dataset = "", scope = "auto", datasetVersion = "", layout = "classico", onOpenPainel }: Props) {
  const hasSource = !!file || !!dataset;
  const staged = sourceReady && !!active;
  const [status, setStatus] = useState<Status | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [started, setStarted] = useState(false);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const latestReply = [...turns].reverse().find(turn => turn.role === "assistant");

  const revision = useRef(0);
  const ready = useRef(contextReady);
  ready.current = contextReady;
  const pendingProposal = useRef<Proposal | null>(null);
  // Pedido feito antes da escolha dos dados: com a base pronta, é interpretado de novo (os territórios citados valem).
  const pendingRequest = useRef("");
  const explore = useRef(onExplore);
  explore.current = onExplore;
  const selectAnalysis = useRef(onSelectAnalysis);
  selectAnalysis.current = onSelectAnalysis;

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
    if (!sourceReady || !pendingProposal.current?.operation) return;
    const proposal = pendingProposal.current, request = pendingRequest.current;
    pendingProposal.current = null;
    pendingRequest.current = "";
    if (!request) { onSelectAnalysis(proposal.operation!, proposal); return; }
    // Com a base pronta, o pedido inicial passa pela interpretação local: os municípios citados nele vão para a
    // abrangência, sem que o usuário precise repeti-los. Sem interpretação local, vale a análise proposta, como antes.
    void (async () => {
      const deadline = Date.now() + 20000;
      while (!ready.current && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 100));
      let local: LocalAnswer | null = null;
      try { if (ready.current) local = await explore.current(request); } catch { local = null; }
      if (local) answer(local, request);
      else selectAnalysis.current(proposal.operation!, proposal);
    })();
  }, [sourceReady]);

  /** Resposta local na conversa; com alternativas, elas ficam junto à resposta, como os demais esclarecimentos. */
  function answer(local: LocalAnswer, request: string) {
    setTurns(previous => [...previous, {role:"assistant", content:local.text, request, context:contextVersion,
      ...(local.choices?.length ? {clarification:{code:"ESCOLHA_DE_LEITURA", prompt:local.text, reason:"", source:"CATALOGO_LOCAL" as const,
        choices:local.choices, answered:false as const}} : {})}]);
  }

  function openView(view: ResultView): string {
    if (!hasResult) return "Ainda não há resultado calculado. Depois do cálculo, ele aparece nas abas Mapa, Gráficos e Tabela.";
    setWorkspaceStage("results");
    window.dispatchEvent(new CustomEvent("adt:view", {detail: view}));
    return "Resultado aberto na aba " + VIEW_LABEL[view] + ". Nada foi recalculado.";
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    await submit(draft.trim());
  }

  async function submit(message: string) {
    if (sending || !privacyAccepted || message.length < 2 || message.length > 800) return;
    setStarted(true);
    onStarted();
    onRequest(message);
    setTurns(previous => [...previous, {role:"user", content:message}]);
    setDraft("");
    // A resposta à escolha de fonte pertence à etapa ativa, não ao interpretador analítico.
    // Botões e texto compartilham as mesmas ações de seleção governadas pelo App.
    if (!hasSource) {
      const sourceReply = normalizeCommand(message);
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
    // Comandos conversacionais e botões alteram a mesma etapa visual.
    if (sourceReady && active) {
      if (/^(?:quero |desejo )?(?:analisar|selecionar|escolher) (?:varios|multiplos) periodos$/.test(normalizeCommand(message))) {
        const opened = onMultiplePeriods();
        setTurns(previous => [...previous, {role:"assistant", content: opened
          ? "Escolha os períodos na preparação. Cada competência será analisada separadamente."
          : "Esta análise exige uma competência por vez. Para trabalhar com vários períodos, escolha Quantitativos ou Evolução temporal."}]);
        return;
      }
      const target = navigationCommand(message, workspaceStage, hasResult || running);
      if (target && (target !== "results" || hasResult || running)) {
        setWorkspaceStage(target);
        setTurns(previous => [...previous, {role:"assistant",content:target === "territories"
          ? territorySummary?.selectable === false ? "No recorte nacional há um único território, o Brasil. Para escolher municípios, use a abrangência Municípios na preparação."
          : "Seleção de territórios aberta na preparação. Sua seleção anterior foi preservada."
          : target === "preparation" ? "Preparação aberta. Confira os territórios, o período e os parâmetros para calcular."
          : "Resultados da investigação abertos."}]);
        return;
      }
    }
    const followup = /^(?:certo[,.! ]*|ok[,.! ]*|sim[,.! ]*|entendi[,.! ]*|vamos[,.! ]*|pode calcular[?.! ]*|quantos? tem[?.! ]*|certo[,.! ]+quantos? tem[?.! ]*|e agora[?.! ]*|continue[?.! ]*)$/i.test(message);
    const append = (content: string) => setTurns(previous => [
      ...previous, {role:"assistant", content}
    ]);
    // Abas do resultado e resultado anterior: só a apresentação muda, nada é recalculado.
    if (sourceReady && hasResult) {
      const view = viewCommand(message);
      if (view) { append(openView(view)); return; }
      if (previousResultCommand(message)) { append(onPreviousResult()); return; }
    }
    // Não reinterpretar o mesmo pedido quando a base ou alguma escolha
    // necessária ainda não foi feita. O próximo passo já é conhecido.
    if (!sourceReady && active && followup) {
      append("Para continuar, escolha os dados que deseja utilizar. Depois, mostrarei os campos para você escolher.");
      return;
    }
    if (sourceReady && active && followup && /^(?:pode calcular|sim|vamos)[?.! ]*$/i.test(message)) {
      append("Sua análise já está selecionada. Confira os campos e as escolhas na preparação; quando estiverem completos, poderá calcular e ver o resultado nesta investigação.");
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
        if (local !== null) {answer(local, message); return;}
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
      const action = validated.dialogue_action || "";
      const viewAction = VIEW_ACTION.get(action);
      const responseText = resolved ? onResolved(resolved) : viewAction ? openView(viewAction)
        : action === "previous_result" ? onPreviousResult() : !sourceReady && suggested
        ? "Entendi. Podemos fazer essa análise de " + ANALYSIS[suggested].toLowerCase() +
          ". Para começar, prefere usar os dados do Brasil atualmente disponibilizados nesta plataforma ou importar os seus? Depois seguiremos diretamente com a análise."
        : validated.reply;
      // Leituras pendentes da interpretação local (por exemplo, "últimos 5 anos") ficam como alternativas da resposta.
      const readings: Clarification | undefined = resolved?.choices?.length ? {code:"ESCOLHA_DE_LEITURA", prompt:responseText,
        reason:"", source:"CATALOGO_LOCAL", choices:resolved.choices, answered:false} : undefined;
      setTurns(previous => [...previous,
        {role:"assistant", content:responseText, proposal:validated.proposal, verification:validated.verification, clarification:readings || validated.clarification, request:message, context:contextVersion}]);
      // A interpretação escolhe a capacidade, não executa a análise.
      // O usuário ainda escolhe os recortes e executa a análise.
      if (suggested && !resolved) {
        if (!sourceReady) { pendingProposal.current = validated.proposal; pendingRequest.current = message; }
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

  // Painel integrado: a conversa vai para a caixa flutuante (mesmos ids e textos); a preparação e os resultados clássicos
  // continuam montados, ocultos, e voltam como estavam. No layout clássico, a marcação é a de sempre.
  const floating = layout === "painel";
  const alternatives = turns.at(-1)?.role === "assistant" && turns.at(-1)?.clarification?.source === "CATALOGO_LOCAL" &&
      <div className="mx-4 mb-3 flex flex-wrap gap-2" aria-label="Alternativas de esclarecimento">
        {turns.at(-1)!.clarification!.choices.map(choice =>
          <button key={choice.label} type="button" disabled={sending || selecting || turns.at(-1)?.context !== contextVersion}
            onClick={async () => {
              const current = turns.at(-1)!;
              if (choice.send && sourceReady) { void submit(choice.draft); return; }
              if (!choice.operation || !current.request || !sourceReady) {
                setDraft(choice.draft); document.getElementById("assistant-input")?.focus(); return;
              }
              setSending(true); setError("");
              setTurns(previous => [...previous,{role:"user",content:"Escolho: " + choice.label}]);
              onRequest(current.request);
              try {
                const reply = await onExplore(current.request, {operation:choice.operation,indicator:choice.indicator});
                setTurns(previous => [...previous,{role:"assistant",content:reply?.text || "Análise escolhida. Revise a preparação abaixo."}]);
              } catch (exc) { setError(exc instanceof Error ? exc.message : "Não foi possível preparar a escolha."); }
              finally { setSending(false); }
            }}
            className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-teal hover:bg-cyan-100">{choice.label}</button>)}
      </div>;
  const dock = <div className="conversation-dock no-print" data-testid="conversation-dock">
      {latestReply && <div className="latest-reply" role="status" data-testid="latest-reply">
        <BrandAvatar size={30}/><div><p className="whitespace-pre-wrap">{latestReply.content}</p></div>
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
    </div>;

  return <section id={floating ? undefined : "assistente"} aria-label={floating ? undefined : "Assistente de análise territorial"}
    className={floating ? "painel-chat-host" : "assistant-panel section-anchor conversation-workspace rounded-[24px] border border-line bg-white shadow-sm"}>
    <div className="integrated-investigation" data-results-focus={resultsOnly} hidden={floating}>
    <div className="conversation-pane no-print" data-testid="conversation-pane">
    <div className="agent-guidance">
      <BrandAvatar size={46}/><div><h2 className="font-bold text-ink">Agente Diagnóstico Territorial</h2>
      <p>{running ? "Estou acompanhando a execução pelo motor determinístico." : hasResult ? "Vamos explorar os resultados e continuar a investigação." : sourceReady ? active ? "Confira os recortes e as escolhas para calcular." : sourceSummary : "Olá! Conte o que deseja analisar ou escolha seus dados para começar."}</p></div>
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
    {!floating && alternatives}
    {!sourceReady && <div className="px-4 pb-4">{sourceChoice}</div>}
    {sourceReady && <div className="px-4 pb-4">
      <details className="no-print text-xs text-teal"><summary className="cursor-pointer">Trocar fonte de dados</summary>{sourceChoice}</details>
      <p data-testid="current-source" className="mt-2 text-xs text-slate-500">Fonte atual: {dataset ? "Dados do Brasil" : file?.name || "Dados importados"}</p>
      {onOpenPainel && dataset && <button type="button" data-testid="open-painel" onClick={onOpenPainel}
        className="no-print mt-2 inline-flex items-center gap-2 rounded-lg border border-teal bg-white px-3 py-2 text-xs font-semibold text-teal hover:bg-cyan-50">
        <LayoutDashboard size={15} aria-hidden="true"/>Abrir o painel integrado</button>}
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
      {/* Abas: o contorno desce da aba ativa e envolve todo o conteúdo da etapa (preparação ou resultados). */}
      {staged && <nav aria-label="Etapas da investigação" data-testid="stage-tabs" className="stage-tabs no-print">
        {([
          ["preparation", "1. Preparação"],
          ["results", "2. Resultados"],
        ] as const).map(([id,label])=><button key={id} type="button" aria-current={workspaceStage === id ? "step" : undefined}
          aria-controls="etapa-da-investigacao" disabled={id === "results" && !hasResult && !running}
          onClick={()=>setWorkspaceStage(id)} className="stage-tab">{label}</button>)}
      </nav>}
      <div id="etapa-da-investigacao" className={staged ? "stage-frame" : undefined} data-testid="stage-frame">
        {notice && <p role="status" className="no-print my-3 text-xs text-teal">{notice}</p>}
        {(!sourceReady || !active) && investigationContent}
        {sourceReady && active && <div className="preparation-context" data-testid="preparation-context" hidden={workspaceStage === "results"}>
          <div className="agent-guidance no-print"><BrandAvatar size={36}/><p>Realize as configurações conforme a sua escolha.</p></div>
          {/* Territórios fazem parte da preparação: um resumo de uma linha, expandido só quando o usuário pede. */}
          {territorySummary && <section id="territorios" aria-label="Territórios da análise" data-testid="territory-card"
            className="no-print section-anchor mb-4 rounded-2xl border border-line bg-white">
            <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
              <p className="flex min-w-0 items-start gap-2 text-sm text-slate-700"><MapPin size={16} className="mt-0.5 shrink-0 text-teal"/>
                <span className="min-w-0"><strong className="text-ink">{territorySummary.label}:</strong> {territorySummary.text}</span></p>
              {territorySummary.selectable && selection && <button type="button" data-testid="territory-toggle" aria-expanded={territoriesOpen}
                aria-controls="territorios-painel" onClick={() => onTerritoriesOpen(!territoriesOpen)}
                className={"rounded-lg px-3 py-2 text-xs font-semibold " + (territoriesOpen ? "bg-teal text-white" : "border border-teal text-teal hover:bg-cyan-50")}>
                {territoriesOpen ? "Concluir seleção" : territorySummary.selected ? "Alterar territórios" : "Escolher territórios"}</button>}
            </div>
            {territorySummary.selectable && selection &&
              <div id="territorios-painel" hidden={!territoriesOpen} className="border-t border-line px-4 pb-2">{selection}</div>}
          </section>}
          {preparation}
        </div>}
        <div className="results-stage" hidden={sourceReady && !!active && workspaceStage !== "results"}>
          {sourceReady && active && investigationContent}
          {resultContent}
          {sourceReady && active && hasResult && <button type="button" onClick={()=>setWorkspaceStage("preparation")}
            className="no-print m-4 rounded-lg border border-line px-4 py-2 text-xs font-semibold text-teal">Voltar à preparação</button>}
        </div>
        {resultsOnly && !hasResult && <p className="p-4 text-sm">Seus resultados aparecerão aqui após o primeiro cálculo. Comece em Nova análise ou converse comigo.</p>}
      </div>
      </div>
    </section>
    {!floating && dock}

    </div>
    {floating && <ChatFloatingBox ocupado={sending}>{alternatives}{dock}</ChatFloatingBox>}
  </section>;
}
