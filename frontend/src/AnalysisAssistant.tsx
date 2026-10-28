import { FormEvent, Fragment, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowDown, Database, FileUp, Info, LoaderCircle, RefreshCw, Send } from "lucide-react";
import BrandAvatar from "./BrandAvatar";
import ChatFloatingBox from "./ChatFloatingBox";
import { sessionFetch as fetch, contextRevision } from "./conversationSession";
import { comandoDeFonte, conversaParaEnvio, guardarAnterior, guiaDaConversa, memoriaVazia, normalizeCommand, opcoesDaConversa,
  pedidoDaOperacao, pedidoDeResumo, pedidoDoPainel, pedidosDasAcoes, pendenteDaResposta, previousResultCommand, respostaAOferta,
  respostaDaVista, respostaDoResumo, rotuloDoPedido, viewCommand, voltarAnteriores, type MemoriaDaConversa,
  type ResultView } from "./conversaGrafico";
import { dataLocal, type ContextoDoGrafico, type PedidoDoChat, type Rotulos } from "./paginaUnica";
import { acrescentar, avisoDaResposta, avisoDeDemora, avisoDeFalha, blocosDoTexto, estaNoFim, horaDaMensagem, mensagemDeAviso,
  novoId, posicaoDaRolagem, turnosParaEnvio, ultimaResposta, type Aviso, type Mensagem, type Trecho,
  type Turno as TurnoEnviado } from "./historicoConversa";

// Conversa da página única (22/10/2026), sempre na caixa flutuante com o rosto do agente. Antes dos dados, ela pergunta o que
// a pessoa quer analisar e oferece "Usar dados do Brasil" e "Enviar meus dados" (24/10/2026: a mesma janela de envio da área
// central, com o modelo de planilha). Com os dados prontos, cada pedido vai primeiro
// ao intérprete local (/api/exploration/interpret) e, sem resposta local, ao intérprete contextual
// (/api/llm/interpret-context); sem dados, ao intérprete preliminar (/api/llm/interpret). Quando a resposta traz o campo
// `painel`, ele vira um pedido para a área de análise, que muda o gráfico; a conversa não calcula nada. O contexto de cada
// pedido sai do que está no gráfico (ContextoDoGrafico). Respondidos na própria tela, sem o intérprete: a vista do desenho
// ("ver no mapa", "volte ao gráfico", que viram um pedido `{ vista }` para a área), "agora a tabela" e o pedido de resumo ("o
// que esse gráfico mostra?", com a frase-resumo do motor). Desde 26/10/2026, a caixa mostra a conversa inteira, em ordem: as
// mensagens da pessoa como ela escreveu e as respostas do agente (historicoConversa.ts); a indisponibilidade da conversa aparece
// como aviso cordial no próprio histórico, sem código nem mensagem técnica. Ao backend vai a janela das mensagens mais recentes
// (`turnos`), que ele tria antes do provedor; arquivos, linhas e nomes de campo nunca vão ao provedor de IA. Desde 26/10/2026: o
// pedido de análise antes dos dados recebe na hora o lembrete de escolher a base (sem o provedor) e fica guardado até ela ficar
// pronta, quando segue pelo caminho completo (desde 28/10/2026, com lugares do Brasil ou os dados da pessoa citados, a oferta
// dessa fonte, com o botão dela na resposta e "sim" para escolhê-la); a resposta que pede continuação (`continuar`, como
// "assim que o gráfico estiver pronto, comparo …") é enviada sozinha quando o motor calcula o gráfico novo; nenhum pedido fica
// girando além do prazo da tela.

/** Alternativa de esclarecimento: com operation, reinterpreta o pedido com a escolha; com send, envia o rascunho como
 * mensagem (por exemplo, uma das leituras de "últimos 5 anos"); sem nenhum dos dois, vai para a caixa de texto. */
type Choice = { label: string; draft: string; operation?: string; indicator?: "quantity" | "density" | null; send?: boolean };
type Clarification = { code: string; prompt: string; reason: string; source: "CATALOGO_LOCAL"; choices: Choice[]; answered: false };
type Proposal = { operation: string | null; indicator: "density" | "quantity" | null; territory: string; period: string; category: string };
type Exploration = { handled: boolean; reply?: string; clarification?: string; operation?: string; pending_operation?: string;
  pending_ids?: string[]; requested_count?: number | null; choices?: Choice[]; criteria_pending_ranking?: string; painel?: unknown;
  /** Gestor de diálogo (26/10/2026): a memória da resposta, quantos estados anteriores a tela desfaz, as ações de tela e a
   * pergunta sem alternativas (modelo da resposta) ou o pedido original de uma pergunta com alternativas. */
  memoria?: Record<string, unknown>; desfazer?: number; acoes?: unknown; modelo_de_resposta?: string; pedido_original?: string;
  /** Pedido que a tela envia sozinha quando o motor calcular o gráfico novo (26/10/2026). */
  continuar?: string };
type Reply = { exploration?: Exploration; dialogue_action?: string; reply: string; proposal: Proposal;
  verification?: { source: string }; clarification?: Clarification; executed: boolean; origin: string; painel?: unknown;
  /** Pedido de análise antes da escolha dos dados: o lembrete de escolher a base; o pedido fica guardado (26/10/2026). */
  aguarda_base?: boolean;
  /** Com o lembrete (28/10/2026): a fonte oferecida (lugares do Brasil ou os dados da pessoa citados) ou a escolhida (os
   * dados do Brasil citados como fonte, como o botão). */
  fonte_sugerida?: "brasil" | "arquivo"; fonte_escolhida?: "brasil" | "arquivo" };
type Status = { configured: boolean; disponivel?: boolean; indisponibilidade?: { tipo?: string; titulo?: string; texto?: string } };
/** Mensagem do histórico, com a pergunta de esclarecimento e o pedido que a provocou (para as alternativas). */
type Turn = Mensagem & { clarification?: Clarification; request?: string; fonte?: string };
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
/** Prazos da tela (26/10/2026): o aviso de que o pedido ainda está em andamento, o fim da espera (o backend tem 75 s por
 * chamada ao provedor e não começa chamada nova depois de 20 s do pedido) e a espera da continuação pelo gráfico novo. */
const AVISO_DE_ANDAMENTO_MS = 12000, AVISO_DE_DEMORA_MS = 45000, PRAZO_DA_CONVERSA_MS = 100000;
const ESPERA_DA_CONTINUACAO_MS = 8000, MAX_CONTINUACOES = 2;
/** A fonte oferecida antes dos dados, como alternativa da resposta: o mesmo que o botão do alto (28/10/2026). */
const OPCAO_DA_FONTE: Record<"brasil" | "arquivo", Choice> = {
  brasil: { label: "Usar dados do Brasil", draft: "usar dados do Brasil", send: true },
  arquivo: { label: "Enviar meus dados", draft: "enviar meus dados", send: true } };
const SEGUIMENTO = /^(?:certo[,.! ]*|ok[,.! ]*|sim[,.! ]*|entendi[,.! ]*|vamos[,.! ]*|pode calcular[?.! ]*|quantos? tem[?.! ]*|certo[,.! ]+quantos? tem[?.! ]*|e agora[?.! ]*|continue[?.! ]*)$/i;

/** Falha da conversa: o status e o detalhe ficam para escolher o aviso cordial; a tela nunca os mostra crus. */
class ErroDaConversa extends Error {
  constructor(readonly status: number | null, readonly detalhe?: unknown) { super("Falha da conversa."); }
}

async function lerResposta(response: Response): Promise<any> {
  const raw = await response.text();
  let body: any;
  try { body = JSON.parse(raw); }
  catch { throw new ErroDaConversa(response.status); }
  if (!response.ok) throw new ErroDaConversa(response.status, body?.detail);
  return body;
}

/** Os trechos de um texto da conversa (historicoConversa.blocosDoTexto): o rótulo do começo do parágrafo em negrito e os
 * exemplos de pedido em destaque. Só realça: o texto é o mesmo. */
function Trechos({ trechos }: { trechos: Trecho[] }) {
  return <>{trechos.map((trecho, indice) => trecho.tipo === "texto" ? <Fragment key={indice}>{trecho.texto}</Fragment>
    : <span key={indice} className={trecho.tipo === "rotulo" ? "chat-rotulo" : "chat-exemplo"}>{trecho.texto}</span>)}</>;
}

/** A resposta em parágrafos separados; as quebras entre eles continuam no texto, escondidas (o conteúdo não muda). */
function TextoDaResposta({ texto }: { texto: string }) {
  return <div className="chat-texto">{blocosDoTexto(texto).map((bloco, indice) => bloco.tipo === "separador"
    ? <span key={indice} className="chat-separador">{bloco.texto}</span>
    : <p key={indice}><Trechos trechos={bloco.trechos}/></p>)}</div>;
}

function textoDoPedido(pedido: PedidoDoChat | null): string {
  const rotulo = rotuloDoPedido(pedido), desenho = pedido?.vista === "mapa" ? "mapa" : "gráfico";
  return rotulo ? "Pronto: " + rotulo + " no " + desenho + "." : desenho === "mapa" ? "Mapa atualizado com o seu pedido."
    : "Gráfico atualizado com o seu pedido.";
}

export default function AnalysisAssistant({ apiBase, privacyAccepted, fonteEscolhida, fonte, fonteChave, colunasPendentes,
  contexto, rotulos, displayedResultId, onEscolherFonte, onPedido, onAnaliseAnterior }: Props) {
  const pronta = !!fonte;
  const [status, setStatus] = useState<Status | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sending, setSending] = useState(false);
  const latestReply = ultimaResposta(turns);
  // Rolagem do histórico: a chegada de uma resposta só leva ao fim quem está acompanhando o fim; quem lê mensagens antigas
  // fica onde está e vê o botão "Ir para a mensagem mais recente".
  const historico = useRef<HTMLOListElement>(null);
  const noFim = useRef(true);
  const [novidade, setNovidade] = useState(false);
  // Lembrete da escolha dos dados (26/10/2026): depois de um pedido de análise sem base, os dois botões da escolha ficam em
  // destaque até a pessoa escolher; desde 28/10/2026, com uma fonte oferecida, só o botão dela.
  const [lembrete, setLembrete] = useState<false | "ambos" | "brasil" | "arquivo">(false);
  // Pedido em andamento há algum tempo: 1 depois de 12 s, 2 depois de 45 s (o texto do indicador muda; nada é reenviado).
  const [demora, setDemora] = useState(0);
  const adicionar = (mensagem: Turn) => setTurns(previous => acrescentar(previous, { hora: horaDaMensagem(), ...mensagem }) as Turn[]);
  const avisar = (aviso: Aviso) => adicionar(mensagemDeAviso(aviso));
  /** Falha de rede ou do serviço: o aviso cordial no histórico; a mensagem da pessoa continua onde está. A espera
   * interrompida pelo prazo da tela tem o seu próprio aviso. */
  const avisarFalha = (exc: unknown) => avisar((exc as { name?: string } | null)?.name === "AbortError" ? avisoDeDemora()
    : avisoDeFalha(exc instanceof ErroDaConversa ? exc.status : null, exc instanceof ErroDaConversa ? exc.detalhe : undefined));
  useLayoutEffect(() => {
    const lista = historico.current;
    if (!lista) return;
    if (!noFim.current) { setNovidade(true); return; }
    // Quem acompanha o fim vê a mensagem nova junto com a pergunta que a provocou: numa resposta longa, a pergunta fica no
    // alto e o começo da resposta logo abaixo (posicaoDaRolagem), em vez de a pergunta sumir acima da área visível.
    const mensagens = lista.querySelectorAll<HTMLElement>('[data-testid="chat-mensagem"]');
    const nova = mensagens[mensagens.length - 1], anterior = mensagens.length > 1 ? mensagens[mensagens.length - 2] : null;
    const topo = (item: HTMLElement) => item.getBoundingClientRect().top - lista.getBoundingClientRect().top + lista.scrollTop;
    lista.scrollTop = nova ? posicaoDaRolagem({ fim: lista.scrollHeight, altura: lista.clientHeight, topoDaNova: topo(nova),
      topoDaAnterior: anterior ? topo(anterior) : null, alturaDaAnterior: anterior?.offsetHeight ?? 0,
      anteriorDaPessoa: anterior?.dataset.papel === "usuario" && nova.dataset.papel !== "usuario" }) : lista.scrollHeight;
    setNovidade(false);
  }, [turns.length, sending]);
  useEffect(() => {
    if (!sending) { setDemora(0); return; }
    const andamento = window.setTimeout(() => setDemora(1), AVISO_DE_ANDAMENTO_MS);
    const espera = window.setTimeout(() => setDemora(2), AVISO_DE_DEMORA_MS);
    return () => { window.clearTimeout(andamento); window.clearTimeout(espera); };
  }, [sending]);
  useEffect(() => { if (fonteEscolhida) { setLembrete(false); sugestao.current = null; } }, [fonteEscolhida]);
  function aoRolar() {
    const lista = historico.current;
    if (!lista) return;
    noFim.current = estaNoFim(lista.scrollTop, lista.scrollHeight, lista.clientHeight);
    if (noFim.current) setNovidade(false);
  }
  function irAoFim() {
    const lista = historico.current;
    if (!lista) return;
    lista.scrollTop = lista.scrollHeight;
    noFim.current = true;
    setNovidade(false);
  }

  const revision = useRef(0);
  // Pendências da conversa: municípios que faltam ("Com qual outro município?"), direção da ordenação e o pedido feito antes
  // dos dados, que segue quando a fonte fica pronta (interpretado de novo, com os municípios citados nele).
  const pendingTerritories = useRef<{ operation: string; requestedCount?: number | null; ids?: string[]; fonte: string } | null>(null);
  const pendingRanking = useRef<string | null>(null);
  const pendingRequest = useRef("");
  const pendingPedido = useRef<PedidoDoChat | null>(null);
  // A fonte oferecida pela última resposta antes dos dados (28/10/2026): "sim" a escolhe; qualquer outra mensagem a esquece.
  const sugestao = useRef<"brasil" | "arquivo" | null>(null);
  // Continuação pedida pela resposta (26/10/2026), como "assim que o gráfico estiver pronto, comparo …": quando o motor calcula o
  // gráfico novo (outro resultado em exibição), a tela envia o pedido sozinha, sem mostrá-lo como mensagem da pessoa; sem
  // gráfico novo em 8 s, segue com o que está na tela. No máximo duas continuações seguidas; um pedido novo da pessoa a cancela.
  const continuacao = useRef<{ texto: string; resultado: string; fonte: string; passo: number; desde: number } | null>(null);
  const passoAtual = useRef(0);
  const [relogioDaContinuacao, setRelogioDaContinuacao] = useState(0);
  // Memória da conversa (26/10/2026) que vai ao gestor de diálogo do backend a cada pedido: o esclarecimento sem resposta, a
  // memória da última resposta e os estados do gráfico antes dos pedidos aplicados pela conversa. Nada dela vai ao provedor.
  const memoria = useRef<MemoriaDaConversa>(memoriaVazia());
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
    pendingTerritories.current = null;
    pendingRanking.current = null;
    memoria.current = memoriaVazia();
  }, [fonteChave]);
  useEffect(() => {
    if (!pronta || !pendingRequest.current || sending) return;
    const request = pendingRequest.current, pedido = pendingPedido.current;
    pendingRequest.current = "";
    pendingPedido.current = null;
    // O pedido feito antes dos dados segue pelo caminho completo: o intérprete local e, sem resposta local, o comando que já
    // tinha sido interpretado ou o intérprete contextual (26/10/2026; antes, sem resposta local, o pedido se perdia).
    void processar(request, turnosParaEnvio(turns), { retomada: true, pedido });
  }, [pronta, fonteChave, sending]);
  useEffect(() => {
    const pendente = continuacao.current;
    if (!pendente || sending) return;
    if (pendente.fonte !== fonteChave) { continuacao.current = null; return; }
    const esperou = Date.now() - pendente.desde;
    if ((displayedResultId && displayedResultId !== pendente.resultado) || esperou >= ESPERA_DA_CONTINUACAO_MS) {
      continuacao.current = null;
      void processar(pendente.texto, turnosParaEnvio(turns), { passo: pendente.passo });
      return;
    }
    const timer = window.setTimeout(() => setRelogioDaContinuacao(valor => valor + 1), ESPERA_DA_CONTINUACAO_MS - esperou + 50);
    return () => window.clearTimeout(timer);
  }, [displayedResultId, sending, relogioDaContinuacao, fonteChave]);

  function responder(local: Local, request: string) {
    adicionar({ id: novoId("agente"), papel: "agente", texto: local.text, request, fonte: atual.current.fonteChave,
      ...(local.choices?.length ? { clarification: { code: "ESCOLHA_DE_LEITURA", prompt: local.text, reason: "",
        source: "CATALOGO_LOCAL" as const, choices: local.choices, answered: false as const } } : {}) });
  }
  const append = (texto: string) => adicionar({ id: novoId("agente"), papel: "agente", texto });
  /** Pedido de apresentação: a resposta e, quando a vista muda, o pedido `{ vista }` para a área (sem recalcular). */
  function aplicarVista(vista: ResultView): string {
    const resposta = respostaDaVista(vista, atual.current.fonte ? atual.current.contexto : null);
    if (resposta.pedido) pedir.current(resposta.pedido);
    return resposta.texto;
  }

  function formulario(origem: FonteDaConversa): FormData {
    const form = new FormData();
    if (origem.tipo === "brasil") {
      form.append("dataset", "brazil"); form.append("scope", "municipal"); form.append("dataset_version", origem.datasetVersion);
    } else if (origem.arquivo) form.append("file", origem.arquivo);
    form.append("sheet", origem.sheet);
    form.append("context_revision", String(contextRevision()));
    form.append("mapping", JSON.stringify(origem.mapping));
    form.append("conversa", conversaParaEnvio(memoria.current));
    form.append("displayed_result_id", atual.current.displayedResultId);
    return form;
  }
  /** O pedido do gráfico que a resposta traz: guarda o estado de antes (ou volta a um estado guardado, quando a resposta
   * desfaz) e o entrega à área. As ações de tela (abrir "Entenda esta análise") vão pelo mesmo caminho, sem recalcular. */
  function aplicar(pedido: PedidoDoChat | null, resposta: { desfazer?: unknown; acoes?: unknown } = {}) {
    if (pedido) {
      const desfazer = typeof resposta.desfazer === "number" ? resposta.desfazer : 0;
      memoria.current.anteriores = desfazer ? voltarAnteriores(memoria.current.anteriores, desfazer)
        : guardarAnterior(memoria.current.anteriores, atual.current.contexto);
      pedir.current(pedido);
    }
    for (const acao of pedidosDasAcoes(resposta.acoes)) pedir.current(acao);
  }
  /** A memória que a resposta devolve e a pendência que ela deixa (alternativas ou pergunta com modelo de resposta). */
  function lembrar(resposta: Exploration | Reply, mensagem: string, aplicou: boolean) {
    const r = resposta as Exploration;
    memoria.current.memoria = r.memoria ?? (aplicou ? null : memoria.current.memoria);
    memoria.current.pendente = pendenteDaResposta(r, mensagem);
  }
  /** Opções do pedido: as da fonte (escolhas da planilha), o contexto do gráfico e as pendências da conversa. */
  function opcoes(): Record<string, unknown> {
    const { fonte: origem, contexto: grafico, fonteChave: chave } = atual.current;
    const pendente = pendingTerritories.current;
    return { ...(origem?.opcoes || {}), ...opcoesDaConversa(grafico, dataLocal()),
      ...(pendente && pendente.fonte === chave ? { conversation_pending_operation: pendente.operation,
        conversation_requested_count: pendente.requestedCount ?? null,
        ...(pendente.ids?.length ? { conversation_pending_ids: pendente.ids } : {}) } : {}),
      ...(pendingRanking.current ? { criteria_pending_ranking: pendingRanking.current } : {}) };
  }

  /** Resposta do intérprete local: guarda as pendências e entrega o campo `painel` à área. */
  function aceitar(proposal: Exploration): Local {
    // A pendência (por exemplo, "compare Manaus" → "com qual outro?") guarda a unidade já identificada para a mensagem
    // seguinte; um pedido aplicado ao gráfico a encerra.
    if (proposal.pending_operation) pendingTerritories.current = { operation: proposal.pending_operation,
      requestedCount: proposal.requested_count, ids: Array.isArray(proposal.pending_ids) ? proposal.pending_ids : undefined,
      fonte: atual.current.fonteChave };
    else if ((proposal.operation || proposal.painel) && !proposal.clarification) pendingTerritories.current = null;
    pendingRanking.current = proposal.criteria_pending_ranking || null;
    if (typeof proposal.continuar === "string" && proposal.continuar.trim() && passoAtual.current < MAX_CONTINUACOES)
      continuacao.current = { texto: proposal.continuar, resultado: atual.current.displayedResultId,
        fonte: atual.current.fonteChave, passo: passoAtual.current + 1, desde: Date.now() };
    const pedido = pedidoDoPainel(proposal.painel);
    aplicar(pedido, proposal);
    lembrar(proposal, mensagemAtual.current, !!pedido);
    return { text: proposal.clarification || proposal.reply || (pedido ? textoDoPedido(pedido) : "Pedido recebido; nada foi calculado."),
      ...(proposal.choices?.length ? { choices: proposal.choices } : {}) };
  }

  // A mensagem em interpretação, para a pendência que a resposta deixa ("Compare Rio de Janeiro…" → "Município.").
  const mensagemAtual = useRef("");
  async function explorar(message: string, choice?: { operation: string; indicator?: "quantity" | "density" | null },
    signal?: AbortSignal): Promise<Local | null> {
    const origem = atual.current.fonte;
    if (!origem) return null;
    mensagemAtual.current = message;
    const pedidoRevision = revision.current;
    const form = formulario(origem);
    form.append("message", message);
    const base = opcoes();
    form.append("options", JSON.stringify(choice ? { ...base, conversation_operation_choice: choice.operation,
      exploration_indicator: choice.indicator || base.exploration_indicator } : base));
    const response = await fetch(apiBase + "/api/exploration/interpret", { method: "POST", body: form, signal });
    const proposal = await lerResposta(response) as Exploration;
    if (pedidoRevision !== revision.current) return { text: "A fonte de dados mudou durante a interpretação. Envie o pedido de novo." };
    if (!proposal.handled) {
      if (!choice) return null;
      // Escolha explícita entre alternativas, sem o campo `painel` na resposta: a operação escolhida vale no gráfico.
      const pedido = pedidoDaOperacao(choice.operation, choice.indicator);
      aplicar(pedido);
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
    // A mensagem aparece na hora, exatamente como foi escrita, e fica no histórico mesmo que a resposta falhe.
    const janela = turnosParaEnvio(turns);
    adicionar({ id: novoId("usuario"), papel: "usuario", texto: message });
    noFim.current = true;
    setDraft("");
    continuacao.current = null;  // o pedido novo da pessoa vale mais que a continuação que ainda esperava o gráfico
    // A escolha da fonte pela conversa é a mesma ação dos botões; desde 28/10/2026, também o "sim" à fonte oferecida.
    const oferecida = sugestao.current;
    sugestao.current = null;
    const resposta = !fonteEscolhida && oferecida ? respostaAOferta(message) : null;
    const escolha = comandoDeFonte(message) ?? (resposta === "sim" ? oferecida : null);
    if (escolha) {
      if (escolha === "brasil" && fonteEscolhida === "brasil") {
        append(pronta ? "Os dados do Brasil já estão em uso." : "Estou preparando os dados do Brasil.");
        return;
      }
      onEscolherFonte(escolha);
      // Com um pedido guardado, ele segue quando a base fica pronta (28/10/2026; antes, a resposta mandava escolher os
      // territórios, e o pedido seguia mesmo assim).
      append(escolha === "brasil" ? (pendingRequest.current
          ? "Dados do Brasil escolhidos. Vou prepará-los e, em seguida, sigo com o seu pedido."
          : "Dados do Brasil escolhidos. Vou prepará-los; em seguida, escolha os territórios na Seleção de " +
          "Territórios ou me diga quais quer ver: o nome de um estado ou de municípios, ou “todos os estados”.")
        : "Abri a janela de envio: escolha o arquivo CSV ou Excel. O modelo de planilha também está nela. Depois, confira as colunas " +
          "no painel Colunas, no alto da página.");
      return;
    }
    if (resposta === "nao") {
      setLembrete(oferecida === "brasil" ? "arquivo" : "brasil");
      append(oferecida === "brasil" ? "Tudo bem. Para usar os seus dados, escolha “Enviar meus dados”: a janela de envio aceita " +
          "CSV ou Excel e traz o modelo de planilha. Assim que a base estiver pronta, sigo com o seu pedido."
        : "Tudo bem. Se quiser, use os dados do Brasil: escolha “Usar dados do Brasil”. Assim que a base estiver pronta, sigo " +
          "com o seu pedido.");
      return;
    }
    const normalized = normalizeCommand(message);
    if (!fonteEscolhida && /^(?:ola|oi|bom dia|boa tarde|boa noite)$/.test(normalized)) {
      append("Olá! O que você quer analisar? Prefere usar os dados do Brasil ou enviar os seus?");
      return;
    }
    if (!pronta && pendingRequest.current && SEGUIMENTO.test(message)) {
      append("Para continuar, escolha os dados: “Usar dados do Brasil” ou “Enviar meus dados”.");
      if (!fonteEscolhida) setLembrete("ambos");
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
    // "O que esse gráfico mostra?": a frase-resumo verificada do motor, como veio, sem o intérprete nem o provedor de IA. A
    // memória da conversa lembra que o resultado foi resumido, para as perguntas seguintes ("não entendi a aceleração").
    if (pedidoDeResumo(message)) {
      append(respostaDoResumo(pronta ? atual.current.contexto : null));
      memoria.current.memoria = { ato: "resumo", topico: "resultado", registro: "objetivo" };
      memoria.current.pendente = null;
      return;
    }
    if (fonteEscolhida && !pronta) {
      pendingRequest.current = message;
      append(fonteEscolhida === "arquivo" && colunasPendentes
        ? "Confira as colunas no painel Colunas e escolha “Começar a análise”; em seguida, sigo com o seu pedido."
        : "Estou preparando os dados; assim que o gráfico estiver pronto, sigo com o seu pedido.");
      return;
    }
    await processar(message, janela);
  }

  /** O caminho completo de um pedido: o da pessoa, o guardado antes dos dados (`retomada`, com o comando que já tinha sido
   * interpretado, se houver) ou a continuação que uma resposta pediu (`passo`). Os pedidos de apresentação e a análise
   * anterior ficam na tela; os demais vão ao intérprete local e, sem resposta local, ao contextual (com dados) ou ao
   * preliminar (sem dados). Nenhum pedido espera mais que o prazo da tela. */
  async function processar(message: string, janela: TurnoEnviado[],
    modo: { retomada?: boolean; pedido?: PedidoDoChat | null; passo?: number } = {}) {
    const prefixo = modo.retomada ? "Com os dados prontos, sigo com o seu pedido. " : "";
    // Pedidos de apresentação (a vista do desenho e a tabela) e a análise anterior: nada é recalculado.
    if (atual.current.fonte) {
      if (previousResultCommand(message)) { append(prefixo + onAnaliseAnterior()); return; }
      const vista = viewCommand(message);
      if (vista) { append(prefixo + aplicarVista(vista)); return; }
    }
    const requestRevision = revision.current;
    const history = turns.filter(turn => turn.papel === "usuario").slice(-4).map(turn => turn.texto);
    const controle = new AbortController();
    const prazo = window.setTimeout(() => controle.abort(), PRAZO_DA_CONVERSA_MS);
    passoAtual.current = modo.passo ?? 0;
    setSending(true);
    try {
      if (atual.current.fonte) {
        const local = await explorar(message, undefined, controle.signal);
        if (local !== null) { responder({ ...local, text: prefixo + local.text }, message); return; }
        if (modo.retomada && modo.pedido) {
          // O comando interpretado antes dos dados segue direto para o gráfico.
          aplicar(modo.pedido);
          responder({ text: "Segui com o seu pedido. " + textoDoPedido(modo.pedido) }, message);
          return;
        }
      }
      const origem = atual.current.fonte;
      let response: Response;
      if (origem) {
        const form = formulario(origem);
        form.append("message", message);
        form.append("context_ready", "true");
        form.append("history", JSON.stringify(history));
        form.append("turnos", JSON.stringify(janela));
        form.append("displayed_result_id", atual.current.displayedResultId);
        form.append("options", JSON.stringify(opcoes()));
        response = await fetch(apiBase + "/api/llm/interpret-context", { method: "POST", body: form, signal: controle.signal });
      } else {
        response = await fetch(apiBase + "/api/llm/interpret", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, history, turnos: janela, context_revision: contextRevision(), lembrar_base: true }),
          signal: controle.signal });
      }
      const body = await lerResposta(response);
      if (requestRevision !== revision.current) return;
      // Sem o Gemini (limite de consultas, rede, configuração): o aviso cordial como resposta, no mesmo histórico.
      const aviso = avisoDaResposta(body);
      if (aviso) { avisar(aviso); void refreshStatus(); return; }
      const validated = body as Reply;
      if (!validated.proposal || validated.executed !== false || !["INTERPRETACAO_LLM", "CANAL_SISTEMICO"].includes(validated.origin) ||
          (!!origem && !!validated.proposal.operation && validated.verification?.source !== "BACKEND_PREFLIGHT"))
        throw new ErroDaConversa(null);
      const resolved = origem && validated.exploration?.handled ? validated.exploration : null;
      const vista = VISTAS.get(validated.dialogue_action || "");
      let texto: string, choices: Choice[] | undefined;
      if (resolved) {
        mensagemAtual.current = message;
        const local = aceitar({ ...resolved, painel: resolved.painel ?? validated.painel });
        texto = local.text;
        choices = local.choices;
      } else if (vista) texto = aplicarVista(vista);
      else if (validated.dialogue_action === "previous_result" && origem) texto = onAnaliseAnterior();
      else {
        const pedido = pedidoDoPainel(validated.painel) ??
          (origem ? null : pedidoDaOperacao(validated.proposal.operation, validated.proposal.indicator));
        if (!origem && validated.aguarda_base) {
          // Pedido de análise sem base (26/10/2026): o lembrete de escolher os dados, respondido na hora pelo backend, com os
          // dois botões da escolha em destaque; o pedido fica guardado e segue quando a base estiver pronta. Desde 28/10/2026,
          // com uma fonte oferecida, o botão dela em destaque e na resposta ("sim" também a escolhe); com os dados do Brasil
          // citados como fonte, a escolha deles, como o botão.
          pendingRequest.current = message;
          pendingPedido.current = null;
          if (validated.fonte_escolhida) onEscolherFonte(validated.fonte_escolhida);
          else if (!fonteEscolhida) {
            setLembrete(validated.fonte_sugerida ?? "ambos");
            sugestao.current = validated.fonte_sugerida ?? null;
            if (validated.fonte_sugerida) choices = [OPCAO_DA_FONTE[validated.fonte_sugerida]];
          }
          texto = validated.reply;
        } else if (!origem && (pedido || validated.proposal.operation)) {
          // Pedido antes dos dados: fica guardado e segue quando a base estiver pronta.
          pendingRequest.current = message;
          pendingPedido.current = pedido;
          if (!fonteEscolhida) setLembrete("ambos");
          const rotulo = rotuloDoPedido(pedido);
          texto = "Entendi" + (rotulo ? ": " + rotulo : "") + ". Para começar, prefere usar os dados do Brasil ou enviar os " +
            "seus? Depois sigo direto para o gráfico.";
        } else {
          aplicar(pedido);
          lembrar(validated, message, !!pedido);
          texto = validated.reply;
        }
      }
      const clarification: Clarification | undefined = choices?.length ? { code: "ESCOLHA_DE_LEITURA", prompt: texto, reason: "",
        source: "CATALOGO_LOCAL", choices, answered: false } : validated.clarification;
      adicionar({ id: novoId("agente"), papel: "agente", texto, clarification, request: message, fonte: atual.current.fonteChave });
      void refreshStatus();
    } catch (exc) {
      if (requestRevision === revision.current) avisarFalha(exc);
    } finally {
      window.clearTimeout(prazo);
      setSending(false);
    }
  }

  async function escolherAlternativa(choice: Choice, turno: Turn) {
    // A fonte oferecida antes dos dados (28/10/2026) é escolhida como pela conversa, antes de a base ficar pronta.
    if (choice.send && (pronta || comandoDeFonte(choice.draft))) {
      memoria.current.pendente = null;
      void submit(choice.draft);
      return;
    }
    if (!choice.operation || !turno.request || !pronta) {
      setDraft(choice.draft);
      document.getElementById("assistant-input")?.focus();
      return;
    }
    setSending(true);
    memoria.current.pendente = null;  // a escolha em botão responde ao esclarecimento
    continuacao.current = null;
    passoAtual.current = 0;
    adicionar({ id: novoId("usuario"), papel: "usuario", texto: "Escolho: " + choice.label });
    noFim.current = true;
    try {
      const local = await explorar(turno.request, { operation: choice.operation, indicator: choice.indicator });
      responder(local || { text: "Escolha recebida; nada foi calculado." }, turno.request);
    } catch (exc) {
      avisarFalha(exc);
    } finally {
      setSending(false);
    }
  }

  const ultima = turns.at(-1);
  const alternativas = ultima?.papel === "agente" && ultima.clarification?.source === "CATALOGO_LOCAL" &&
    ultima.clarification.choices.length > 0 &&
    <div className="mx-4 mb-3 flex flex-wrap gap-2" role="group" aria-label="Alternativas de esclarecimento">
      {ultima.clarification.choices.map(choice =>
        <button key={choice.label} type="button" disabled={sending || (ultima.fonte ?? "") !== fonteChave}
          onClick={() => void escolherAlternativa(choice, ultima)}
          className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-teal-texto hover:bg-cyan-100 disabled:opacity-40">
          {choice.label}</button>)}
    </div>;
  // Os exemplos da orientação mudam conforme a conversa avança (26/10/2026), sempre sem nomes de lugar.
  const pedidosDaPessoa = turns.filter(turno => turno.papel === "usuario").length;
  const guia = guiaDaConversa({ tipo: fonteEscolhida, pronta, colunasPendentes }, contexto, rotulos, pedidosDaPessoa);
  const andamento = demora >= 2 ? "O serviço de conversa está demorando mais que o normal; aguarde mais um pouco…"
    : demora === 1 ? "Ainda estou trabalhando no seu pedido…" : "Interpretando o pedido…";

  return <ChatFloatingBox ocupado={sending} ampla={!fonteEscolhida}>
    <div className="px-4 pt-3" data-testid="painel-chat-guia" data-compacta={turns.length ? "true" : "false"}>
      <p className="text-sm leading-5 text-slate-700"><Trechos trechos={blocosDoTexto(guia).flatMap(bloco =>
        bloco.tipo === "paragrafo" ? bloco.trechos : [{ tipo: "texto" as const, texto: bloco.texto }])}/></p>
      {!fonteEscolhida && <div className="chat-escolha-dos-dados mt-2 flex flex-wrap gap-2" role="group"
        aria-label="Escolha dos dados na conversa" data-lembrete={lembrete === "ambos" ? "true" : lembrete || "false"}>
        {/* As mesmas duas entradas da área central (24/10/2026); "Enviar meus dados" abre a mesma janela de envio, com o modelo de
            planilha. */}
        <button type="button" data-testid="chat-fonte-brasil" disabled={!privacyAccepted} onClick={() => onEscolherFonte("brasil")}
          className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-teal bg-white px-3 py-2 text-sm font-semibold text-teal-texto hover:bg-cyan-50 disabled:opacity-40">
          <Database size={16} aria-hidden="true"/>Usar dados do Brasil</button>
        <button type="button" data-testid="chat-fonte-arquivo" disabled={!privacyAccepted} onClick={() => onEscolherFonte("arquivo")}
          className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-teal bg-white px-3 py-2 text-sm font-semibold text-teal-texto hover:bg-cyan-50 disabled:opacity-40">
          <FileUp size={16} aria-hidden="true"/>Enviar meus dados</button>
      </div>}
      {(loadingStatus || (status && status.disponivel === false) || !status) &&
        <div role="status" data-testid="chat-estado-do-servico" className="chat-estado-servico mt-2">
        {loadingStatus ? "Preparando a conversa…" : <>
          <strong className="block">{status?.indisponibilidade?.titulo ?? "Assistente conversacional temporariamente indisponível"}</strong>
          {status?.indisponibilidade?.tipo === "cota" ? "O limite de consultas ao assistente conversacional foi atingido neste momento."
            : "O recurso de conversa não está disponível neste momento."} Os botões, os controles e os pedidos diretos sobre o
          gráfico continuam disponíveis.</>}
        {!loadingStatus && <button type="button" onClick={() => { void refreshStatus(); }}
          className="ml-2 inline-flex items-center gap-1 font-semibold underline"><RefreshCw size={12} aria-hidden="true"/>Verificar de novo</button>}
      </div>}
    </div>
    <div className="chat-historico-moldura">
      <ol ref={historico} onScroll={aoRolar} className="chat-historico no-print" data-testid="chat-historico" role="log"
        aria-live="polite" aria-label="Histórico da conversa">
        {turns.map(turno => {
          const ultimaDoAgente = turno.id === latestReply?.id;
          if (turno.papel === "usuario")
            return <li key={turno.id} className="chat-mensagem chat-mensagem-usuario" data-testid="chat-mensagem" data-papel="usuario"
              data-hora={turno.hora}>
              <span className="sr-only">Você: </span><p className="whitespace-pre-wrap">{turno.texto}</p></li>;
          if (turno.papel === "aviso")
            return <li key={turno.id} className="chat-mensagem chat-aviso" data-testid="chat-mensagem" data-papel="aviso">
              <div {...(ultimaDoAgente ? { "data-testid": "latest-reply" } : {})} className="chat-aviso-corpo">
                <Info size={16} aria-hidden="true" className="shrink-0"/>
                <div><strong className="block">{turno.titulo}</strong><p className="whitespace-pre-wrap">{turno.texto}</p></div>
              </div></li>;
          return <li key={turno.id} className="chat-mensagem chat-mensagem-agente" data-testid="chat-mensagem" data-papel="agente">
            <BrandAvatar size={28}/>
            <div {...(ultimaDoAgente ? { "data-testid": "latest-reply" } : {})} className="latest-reply chat-balao-agente"
              data-hora={turno.hora}>
              <span className="sr-only">Agente: </span><TextoDaResposta texto={turno.texto}/></div></li>;
        })}
        {sending && <li className="chat-mensagem chat-mensagem-agente chat-processando" role="status" data-testid="chat-processando">
          <LoaderCircle size={16} className="animate-spin" aria-hidden="true"/>{andamento}</li>}
      </ol>
      {novidade && <button type="button" data-testid="chat-ir-ao-fim" onClick={irAoFim} className="chat-ir-ao-fim">
        <ArrowDown size={14} aria-hidden="true"/>Ir para a mensagem mais recente</button>}
    </div>
    {alternativas}
    <div className="conversation-dock no-print" data-testid="conversation-dock">
      <form id="conversation-composer" onSubmit={send} className="conversation-composer space-y-2">
        <div className="conversation-input-shell rounded-2xl border-2 bg-white shadow-sm transition">
          <label className="sr-only" htmlFor="assistant-input">Descreva sua análise ou faça uma pergunta</label>
          <textarea id="assistant-input" rows={2} maxLength={800} value={draft}
            onChange={event => setDraft(event.target.value)} disabled={sending || !privacyAccepted}
            onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault(); event.currentTarget.form?.requestSubmit();
            }}}
            placeholder={pronta ? "Peça uma mudança no gráfico ou faça uma pergunta…" : "Descreva sua análise ou faça uma pergunta…"}
            className="block min-h-[64px] w-full resize-none rounded-t-2xl border-0 bg-transparent px-4 py-4 text-[15px] leading-6 text-ink focus:outline-none"/>
          <div className="flex items-center justify-between gap-3 px-3 pb-3">
            <span className="text-[12px] text-slate-500">Enter para enviar · Shift + Enter para nova linha</span>
            <button type="submit" aria-label="Enviar mensagem" title="Enviar mensagem"
              disabled={!privacyAccepted || draft.trim().length < 2 || sending}
              className="conversation-send inline-flex h-10 w-10 items-center justify-center rounded-xl text-white transition disabled:cursor-not-allowed disabled:opacity-40">
              {sending ? <LoaderCircle size={18} className="animate-spin" aria-hidden="true"/> : <Send size={19} aria-hidden="true"/>}
            </button>
          </div>
        </div>
        <details className="text-[12px] text-slate-500"><summary className="cursor-pointer">Privacidade da conversa</summary>
          <p className="mt-1">As mensagens passam por proteção de identificadores antes do serviço de IA. Para explicar, ele recebe os
            resultados agregados que estão na tela; arquivos, registros individuais e nomes de colunas não são enviados.</p>
        </details>
      </form>
    </div>
  </ChatFloatingBox>;
}
