import { FormEvent, useEffect, useRef, useState } from "react";
import { AlertCircle, Database, FileUp, LoaderCircle, RefreshCw, Send } from "lucide-react";
import BrandAvatar from "./BrandAvatar";
import ChatFloatingBox from "./ChatFloatingBox";
import { sessionFetch as fetch, contextRevision } from "./conversationSession";
import { comandoDeFonte, guiaDaConversa, normalizeCommand, opcoesDaConversa, pedidoDaOperacao, pedidoDoPainel,
  previousResultCommand, respostaDaVista, rotuloDoPedido, viewCommand, type ResultView } from "./conversaGrafico";
import { dataLocal, type ContextoDoGrafico, type PedidoDoChat, type Rotulos } from "./paginaUnica";

// Conversa da página única (22/10/2026), sempre na caixa flutuante com o rosto do agente. Antes dos dados, ela pergunta o que
// a pessoa quer analisar e oferece "Dados do Brasil" e "Enviar meus dados". Com os dados prontos, cada pedido vai primeiro
// ao intérprete local (/api/exploration/interpret) e, sem resposta local, ao intérprete contextual
// (/api/llm/interpret-context); sem dados, ao intérprete preliminar (/api/llm/interpret). Quando a resposta traz o campo
// `painel`, ele vira um pedido para a área de análise, que muda o gráfico; a conversa não calcula nada. O contexto de cada
// pedido sai do que está no gráfico (ContextoDoGrafico). Nenhum dado, arquivo, nome de campo ou valor da base vai ao provedor
// de IA: o backend só lhe entrega o pedido sanitizado e estados enumerados.

/** Alternativa de esclarecimento: com operation, reinterpreta o pedido com a escolha; com send, envia o rascunho como
 * mensagem (por exemplo, uma das leituras de "últimos 5 anos"); sem nenhum dos dois, vai para a caixa de texto. */
type Choice = { label: string; draft: string; operation?: string; indicator?: "quantity" | "density" | null; send?: boolean };
type Clarification = { code: string; prompt: string; reason: string; source: "CATALOGO_LOCAL"; choices: Choice[]; answered: false };
type Proposal = { operation: string | null; indicator: "density" | "quantity" | null; territory: string; period: string; category: string };
type Exploration = { handled: boolean; reply?: string; clarification?: string; operation?: string; pending_operation?: string;
  requested_count?: number | null; choices?: Choice[]; criteria_pending_ranking?: string; painel?: unknown };
type Reply = { exploration?: Exploration; dialogue_action?: string; reply: string; proposal: Proposal;
  verification?: { source: string }; clarification?: Clarification; executed: boolean; origin: string; painel?: unknown };
type Status = { configured: boolean };
type Turn = { role: "user" | "assistant"; content: string; clarification?: Clarification; request?: string; fonte?: string };
type Local = { text: string; choices?: Choice[] };

/** O que acompanha cada pedido ao intérprete (nunca ao provedor de IA): a referência à base do Brasil ou o arquivo enviado
 * (reenviado só ao backend local), o mapeamento das colunas e as opções da fonte (escolhas da planilha). */
export type FonteDaConversa = { tipo: "brasil" | "arquivo"; datasetVersion: string; arquivo: File | null; sheet: string;
  mapping: Record<string, string>; opcoes: Record<string, unknown> };

type Props = {
  apiBase: string;
  privacyAccepted: boolean;
  /** Fonte escolhida, pronta ou em preparação (null: abertura, antes dos dados). */
  fonteEscolhida: "brasil" | "arquivo" | null;
  /** Fonte pronta, em uso no gráfico (null enquanto não há dados). */
  fonte: FonteDaConversa | null;
  /** Identidade da fonte em uso: mudar de fonte invalida as respostas em trânsito. */
  fonteChave: string;
  /** Planilha esperando a escolha das colunas no painel "Colunas". */
  colunasPendentes: boolean;
  contexto: ContextoDoGrafico | null;
  rotulos: Rotulos | null;
  /** Resultado do gráfico guardado na sessão do backend, para perguntas sobre o que está na tela. */
  displayedResultId: string;
  onEscolherFonte: (tipo: "brasil" | "arquivo") => void;
  /** Resposta com o campo `painel`: o pedido para a área (um id novo a cada comando, no App). */
  onPedido: (pedido: PedidoDoChat) => void;
  /** "Volte ao resultado anterior": reabre a análise anterior do Histórico, sem recalcular, e devolve a resposta. */
  onAnaliseAnterior: () => string;
};

const VISTAS = new Map<string, ResultView>([["show_map", "mapa"], ["show_chart", "graficos"], ["show_table", "tabela"]]);
const SEGUIMENTO = /^(?:certo[,.! ]*|ok[,.! ]*|sim[,.! ]*|entendi[,.! ]*|vamos[,.! ]*|pode calcular[?.! ]*|quantos? tem[?.! ]*|certo[,.! ]+quantos? tem[?.! ]*|e agora[?.! ]*|continue[?.! ]*)$/i;

async function lerResposta(response: Response): Promise<any> {
  const raw = await response.text();
  let body: any;
  try { body = JSON.parse(raw); }
  catch { throw new Error("Não foi possível interpretar a resposta do serviço (HTTP " + response.status + "). Tente novamente."); }
  if (!response.ok) throw new Error((typeof body?.detail === "string" ? body.detail : "Falha no processamento da solicitação.") +
    " (HTTP " + response.status + ")");
  return body;
}

function textoDoPedido(pedido: PedidoDoChat | null): string {
  const rotulo = rotuloDoPedido(pedido);
  return rotulo ? "Pronto: " + rotulo + " no gráfico." : "Gráfico atualizado com o seu pedido.";
}

export default function AnalysisAssistant({ apiBase, privacyAccepted, fonteEscolhida, fonte, fonteChave, colunasPendentes,
  contexto, rotulos, displayedResultId, onEscolherFonte, onPedido, onAnaliseAnterior }: Props) {
  const pronta = !!fonte;
  const [status, setStatus] = useState<Status | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const latestReply = [...turns].reverse().find(turn => turn.role === "assistant");

  const revision = useRef(0);
  // Pendências da conversa: municípios que faltam ("Com qual outro município?"), direção da ordenação e o pedido feito antes
  // dos dados, que segue quando a fonte fica pronta (interpretado de novo, com os municípios citados nele).
  const pendingTerritories = useRef<{ operation: string; requestedCount?: number | null; fonte: string } | null>(null);
  const pendingRanking = useRef<string | null>(null);
  const pendingRequest = useRef("");
  const pendingPedido = useRef<PedidoDoChat | null>(null);
  // Valores atuais para as respostas assíncronas: a fonte e o gráfico podem mudar enquanto a resposta chega.
  const atual = useRef({ fonte, fonteChave, contexto, displayedResultId });
  atual.current = { fonte, fonteChave, contexto, displayedResultId };
  const pedir = useRef(onPedido);
  pedir.current = onPedido;

  async function refreshStatus() {
    setLoadingStatus(true);
    try {
      const response = await fetch(apiBase + "/api/llm/status");
      if (!response.ok) throw new Error("Serviço de IA indisponível.");
      setStatus(await response.json() as Status);
    } catch {
      setStatus(null);
    } finally {
      setLoadingStatus(false);
    }
  }

  useEffect(() => { void refreshStatus(); }, [apiBase]);
  useEffect(() => {
    // Outra fonte: as respostas em trânsito e as pendências daquela fonte deixam de valer; a conversa continua.
    revision.current += 1;
    setError("");
    pendingTerritories.current = null;
    pendingRanking.current = null;
  }, [fonteChave]);
  useEffect(() => {
    if (!pronta || !pendingRequest.current) return;
    const request = pendingRequest.current, pedido = pendingPedido.current;
    pendingRequest.current = "";
    pendingPedido.current = null;
    void (async () => {
      let local: Local | null = null;
      try { local = await explorar(request); } catch { local = null; }
      if (local) responder(local, request);
      else if (pedido) {
        pedir.current(pedido);
        responder({ text: "Segui com o seu pedido. " + textoDoPedido(pedido) }, request);
      }
    })();
  }, [pronta, fonteChave]);

  function responder(local: Local, request: string) {
    setTurns(previous => [...previous, { role: "assistant", content: local.text, request, fonte: atual.current.fonteChave,
      ...(local.choices?.length ? { clarification: { code: "ESCOLHA_DE_LEITURA", prompt: local.text, reason: "",
        source: "CATALOGO_LOCAL" as const, choices: local.choices, answered: false as const } } : {}) }]);
  }
  const append = (content: string) => setTurns(previous => [...previous, { role: "assistant", content }]);

  function formulario(origem: FonteDaConversa): FormData {
    const form = new FormData();
    if (origem.tipo === "brasil") {
      form.append("dataset", "brazil"); form.append("scope", "municipal"); form.append("dataset_version", origem.datasetVersion);
    } else if (origem.arquivo) form.append("file", origem.arquivo);
    form.append("sheet", origem.sheet);
    form.append("context_revision", String(contextRevision()));
    form.append("mapping", JSON.stringify(origem.mapping));
    return form;
  }
  /** Opções do pedido: as da fonte (escolhas da planilha), o contexto do gráfico e as pendências da conversa. */
  function opcoes(): Record<string, unknown> {
    const { fonte: origem, contexto: grafico, fonteChave: chave } = atual.current;
    const pendente = pendingTerritories.current;
    return { ...(origem?.opcoes || {}), ...opcoesDaConversa(grafico, dataLocal()),
      ...(pendente && pendente.fonte === chave ? { conversation_pending_operation: pendente.operation,
        conversation_requested_count: pendente.requestedCount ?? null } : {}),
      ...(pendingRanking.current ? { criteria_pending_ranking: pendingRanking.current } : {}) };
  }

  /** Resposta do intérprete local: guarda as pendências e entrega o campo `painel` à área. */
  function aceitar(proposal: Exploration): Local {
    if (proposal.pending_operation) pendingTerritories.current = { operation: proposal.pending_operation,
      requestedCount: proposal.requested_count, fonte: atual.current.fonteChave };
    else if (proposal.operation && !proposal.clarification) pendingTerritories.current = null;
    pendingRanking.current = proposal.criteria_pending_ranking || null;
    const pedido = pedidoDoPainel(proposal.painel);
    if (pedido) pedir.current(pedido);
    return { text: proposal.clarification || proposal.reply || (pedido ? textoDoPedido(pedido) : "Pedido recebido; nada foi calculado."),
      ...(proposal.choices?.length ? { choices: proposal.choices } : {}) };
  }

  async function explorar(message: string, choice?: { operation: string; indicator?: "quantity" | "density" | null }): Promise<Local | null> {
    const origem = atual.current.fonte;
    if (!origem) return null;
    const pedidoRevision = revision.current;
    const form = formulario(origem);
    form.append("message", message);
    const base = opcoes();
    form.append("options", JSON.stringify(choice ? { ...base, conversation_operation_choice: choice.operation,
      exploration_indicator: choice.indicator || base.exploration_indicator } : base));
    const response = await fetch(apiBase + "/api/exploration/interpret", { method: "POST", body: form });
    const proposal = await lerResposta(response) as Exploration;
    if (pedidoRevision !== revision.current) return { text: "A fonte de dados mudou durante a interpretação. Envie o pedido de novo." };
    if (!proposal.handled) {
      if (!choice) return null;
      // Escolha explícita entre alternativas, sem o campo `painel` na resposta: a operação escolhida vale no gráfico.
      const pedido = pedidoDaOperacao(choice.operation, choice.indicator);
      if (pedido) pedir.current(pedido);
      return { text: pedido ? textoDoPedido(pedido) : "Escolha recebida; nada foi calculado." };
    }
    // Escolha respondida pelo intérprete local, mas sem o campo `painel` e sem nova pergunta: vale a operação escolhida.
    if (choice && !pedidoDoPainel(proposal.painel) && !proposal.clarification && !proposal.pending_operation)
      return aceitar({ ...proposal, painel: pedidoDaOperacao(choice.operation, choice.indicator) });
    return aceitar(proposal);
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    await submit(draft.trim());
  }

  async function submit(message: string) {
    if (sending || !privacyAccepted || message.length < 2 || message.length > 800) return;
    setTurns(previous => [...previous, { role: "user", content: message }]);
    setDraft("");
    setError("");
    // A escolha da fonte pela conversa é a mesma ação dos botões.
    const escolha = comandoDeFonte(message);
    if (escolha) {
      if (escolha === "brasil" && fonteEscolhida === "brasil") {
        append(pronta ? "Os dados do Brasil já estão em uso." : "Estou preparando os dados do Brasil.");
        return;
      }
      onEscolherFonte(escolha);
      append(escolha === "brasil" ? "Dados do Brasil escolhidos. Vou prepará-los; em seguida, o gráfico mostra os estados."
        : "Escolha o arquivo CSV ou Excel. Depois, confira as colunas no painel Colunas, no alto da página.");
      return;
    }
    const normalized = normalizeCommand(message);
    if (!fonteEscolhida && /^(?:ola|oi|bom dia|boa tarde|boa noite)$/.test(normalized)) {
      append("Olá! O que você quer analisar? Prefere começar com os dados do Brasil ou enviar os seus?");
      return;
    }
    if (!pronta && pendingRequest.current && SEGUIMENTO.test(message)) {
      append("Para continuar, escolha os dados: “Dados do Brasil” ou “Enviar meus dados”.");
      return;
    }
    // Perguntas sobre o conteúdo da base pública: consulta local, sem o provedor de IA e sem exigir a escolha da fonte.
    if (/\b(?:dados|base|informacoes)\b/.test(normalized) && /\bbrasil\b/.test(normalized) &&
        /\b(?:o que|quais|contem|possui|tem|disponivel|cobertura|periodos|profissoes|categorias|explicar|descrever)\b/.test(normalized)) {
      setSending(true);
      try {
        const response = await fetch(apiBase + "/api/brazil/description");
        const body = await response.json();
        if (!response.ok || typeof body.description !== "string") throw new Error("Não foi possível consultar a descrição.");
        append(body.description);
      } catch {
        append("Ainda não consegui consultar a descrição dos dados do Brasil. Você pode tentar novamente ou enviar os seus dados.");
      } finally {
        setSending(false);
      }
      return;
    }
    if (fonteEscolhida && !pronta) {
      pendingRequest.current = message;
      append(fonteEscolhida === "arquivo" && colunasPendentes
        ? "Confira as colunas no painel Colunas e escolha “Começar a análise”; em seguida, sigo com o seu pedido."
        : "Estou preparando os dados; assim que o gráfico estiver pronto, sigo com o seu pedido.");
      return;
    }
    // Pedidos de apresentação e a análise anterior: nada é recalculado.
    if (pronta) {
      if (previousResultCommand(message)) { append(onAnaliseAnterior()); return; }
      const vista = viewCommand(message);
      if (vista) { append(respostaDaVista(vista)); return; }
    }
    const requestRevision = revision.current;
    const history = turns.filter(turn => turn.role === "user").slice(-4).map(turn => turn.content);
    setSending(true);
    try {
      if (pronta) {
        const local = await explorar(message);
        if (local !== null) { responder(local, message); return; }
      }
      const origem = atual.current.fonte;
      let response: Response;
      if (origem) {
        const form = formulario(origem);
        form.append("message", message);
        form.append("context_ready", "true");
        form.append("history", JSON.stringify(history));
        form.append("displayed_result_id", atual.current.displayedResultId);
        form.append("options", JSON.stringify(opcoes()));
        response = await fetch(apiBase + "/api/llm/interpret-context", { method: "POST", body: form });
      } else {
        response = await fetch(apiBase + "/api/llm/interpret", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, history, context_revision: contextRevision() }) });
      }
      const body = await response.json();
      if (requestRevision !== revision.current) return;
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Não foi possível interpretar o pedido.");
      const validated = body as Reply;
      if (!validated.proposal || validated.executed !== false || !["INTERPRETACAO_LLM", "CANAL_SISTEMICO"].includes(validated.origin) ||
          (!!origem && !!validated.proposal.operation && validated.verification?.source !== "BACKEND_PREFLIGHT"))
        throw new Error("A resposta não atende ao contrato de interpretação e verificação.");
      const resolved = origem && validated.exploration?.handled ? validated.exploration : null;
      const vista = VISTAS.get(validated.dialogue_action || "");
      let texto: string, choices: Choice[] | undefined;
      if (resolved) {
        const local = aceitar({ ...resolved, painel: resolved.painel ?? validated.painel });
        texto = local.text;
        choices = local.choices;
      } else if (vista) texto = respostaDaVista(vista);
      else if (validated.dialogue_action === "previous_result" && origem) texto = onAnaliseAnterior();
      else {
        const pedido = pedidoDoPainel(validated.painel) ??
          (origem ? null : pedidoDaOperacao(validated.proposal.operation, validated.proposal.indicator));
        if (!origem && (pedido || validated.proposal.operation)) {
          // Pedido antes dos dados: fica guardado e segue quando a base estiver pronta.
          pendingRequest.current = message;
          pendingPedido.current = pedido;
          const rotulo = rotuloDoPedido(pedido);
          texto = "Entendi" + (rotulo ? ": " + rotulo : "") + ". Para começar, prefere usar os dados do Brasil ou enviar os " +
            "seus? Depois sigo direto para o gráfico.";
        } else {
          if (pedido) pedir.current(pedido);
          texto = validated.reply;
        }
      }
      const clarification: Clarification | undefined = choices?.length ? { code: "ESCOLHA_DE_LEITURA", prompt: texto, reason: "",
        source: "CATALOGO_LOCAL", choices, answered: false } : validated.clarification;
      setTurns(previous => [...previous, { role: "assistant", content: texto, clarification, request: message,
        fonte: atual.current.fonteChave }]);
      void refreshStatus();
    } catch (exc) {
      if (requestRevision === revision.current) setError(exc instanceof Error ? exc.message : "Não foi possível acessar a API.");
    } finally {
      setSending(false);
    }
  }

  async function escolherAlternativa(choice: Choice, turno: Turn) {
    if (choice.send && pronta) { void submit(choice.draft); return; }
    if (!choice.operation || !turno.request || !pronta) {
      setDraft(choice.draft);
      document.getElementById("assistant-input")?.focus();
      return;
    }
    setSending(true);
    setError("");
    setTurns(previous => [...previous, { role: "user", content: "Escolho: " + choice.label }]);
    try {
      const local = await explorar(turno.request, { operation: choice.operation, indicator: choice.indicator });
      responder(local || { text: "Escolha recebida; nada foi calculado." }, turno.request);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Não foi possível aplicar a escolha.");
    } finally {
      setSending(false);
    }
  }

  const ultima = turns.at(-1);
  const alternativas = ultima?.role === "assistant" && ultima.clarification?.source === "CATALOGO_LOCAL" &&
    ultima.clarification.choices.length > 0 &&
    <div className="mx-4 mb-3 flex flex-wrap gap-2" role="group" aria-label="Alternativas de esclarecimento">
      {ultima.clarification.choices.map(choice =>
        <button key={choice.label} type="button" disabled={sending || (ultima.fonte ?? "") !== fonteChave}
          onClick={() => void escolherAlternativa(choice, ultima)}
          className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-teal hover:bg-cyan-100 disabled:opacity-40">
          {choice.label}</button>)}
    </div>;
  const guia = guiaDaConversa({ tipo: fonteEscolhida, pronta, colunasPendentes }, contexto, rotulos);

  return <ChatFloatingBox ocupado={sending} ampla={!fonteEscolhida}>
    <div className="px-4 pt-3" data-testid="painel-chat-guia">
      <p className="text-sm leading-5 text-slate-700">{guia}</p>
      {!fonteEscolhida && <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Escolha dos dados na conversa">
        <button type="button" data-testid="chat-fonte-brasil" disabled={!privacyAccepted} onClick={() => onEscolherFonte("brasil")}
          className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-teal bg-white px-3 py-2 text-sm font-semibold text-teal hover:bg-cyan-50 disabled:opacity-40">
          <Database size={16} aria-hidden="true"/>Dados do Brasil</button>
        <button type="button" data-testid="chat-fonte-arquivo" disabled={!privacyAccepted} onClick={() => onEscolherFonte("arquivo")}
          className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-teal bg-white px-3 py-2 text-sm font-semibold text-teal hover:bg-cyan-50 disabled:opacity-40">
          <FileUp size={16} aria-hidden="true"/>Enviar meus dados</button>
      </div>}
      {!status?.configured && <div role="status" className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-[11px] leading-4 text-amber-900">
        {loadingStatus ? "Preparando a conversa…" : "Perguntas livres estão temporariamente indisponíveis. Os pedidos sobre o " +
          "gráfico e a escolha dos dados continuam disponíveis."}
        {!loadingStatus && <button type="button" onClick={() => { void refreshStatus(); }}
          className="ml-2 inline-flex items-center gap-1 font-semibold underline"><RefreshCw size={12} aria-hidden="true"/>Tentar novamente</button>}
      </div>}
    </div>
    {alternativas}
    <div className="conversation-dock no-print" data-testid="conversation-dock">
      {latestReply && <div className="latest-reply" role="status" data-testid="latest-reply">
        <BrandAvatar size={30}/><div><p className="whitespace-pre-wrap">{latestReply.content}</p></div>
      </div>}
      {sending && <p role="status" className="flex items-center gap-2 px-4 pt-2 text-sm text-teal">
        <LoaderCircle size={16} className="animate-spin" aria-hidden="true"/>Interpretando o pedido…</p>}
      <form id="conversation-composer" onSubmit={send} className="conversation-composer space-y-2">
        <div className="conversation-input-shell rounded-2xl border-2 bg-white shadow-sm transition">
          <label className="sr-only" htmlFor="assistant-input">Descreva sua análise ou faça uma pergunta</label>
          <textarea id="assistant-input" rows={2} maxLength={800} value={draft}
            onChange={event => setDraft(event.target.value)} disabled={sending || !privacyAccepted}
            onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault(); event.currentTarget.form?.requestSubmit();
            }}}
            placeholder={pronta ? "Peça uma mudança no gráfico ou faça uma pergunta…" : "Descreva sua análise ou faça uma pergunta…"}
            className="block min-h-[64px] w-full resize-none rounded-t-2xl border-0 bg-transparent px-4 py-4 text-sm leading-6 text-ink focus:outline-none"/>
          <div className="flex items-center justify-between gap-3 px-3 pb-3">
            <span className="text-[11px] text-slate-500">Enter para enviar · Shift + Enter para nova linha</span>
            <button type="submit" aria-label="Enviar mensagem" title="Enviar mensagem"
              disabled={!privacyAccepted || draft.trim().length < 2 || sending}
              className="conversation-send inline-flex h-10 w-10 items-center justify-center rounded-xl text-white transition disabled:cursor-not-allowed disabled:opacity-40">
              {sending ? <LoaderCircle size={18} className="animate-spin" aria-hidden="true"/> : <Send size={19} aria-hidden="true"/>}
            </button>
          </div>
        </div>
        {error && <p role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800">
          <AlertCircle size={16} className="shrink-0" aria-hidden="true"/>{error}
        </p>}
        <details className="text-[11px] text-slate-500"><summary className="cursor-pointer">Privacidade da conversa</summary>
          <p className="mt-1">As mensagens passam por proteção de identificadores. Arquivos, registros e valores da base não são
            enviados ao serviço de IA.</p>
        </details>
      </form>
    </div>
  </ChatFloatingBox>;
}
