import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileBarChart2, RefreshCw } from "lucide-react";
import AnalysisAssistant, { type FonteDaConversa } from "./AnalysisAssistant";
import AreaDeAnalise from "./AreaDeAnalise";
import BarraDaFonte, { type CatalogoDaFonte } from "./BarraDaFonte";
import BrandAvatar from "./BrandAvatar";
import ColunasDaPlanilha from "./ColunasDaPlanilha";
import HistoricoDeAnalises from "./HistoricoDeAnalises";
import JanelaDeEnvio from "./JanelaDeEnvio";
import SessionPrivacy, { useSessionPrivacy } from "./SessionPrivacy";
import WelcomeHero from "./WelcomeHero";
import WorkspaceDialog from "./WorkspaceDialog";
import { endSession, sessionFetch as fetch, trackSession, updateContextRevision } from "./conversationSession";
import { ROTULOS_DO_BRASIL, analiseAnterior, contextoDaPlanilha, csvDaResposta, disponibilidadeDaPlanilha, escolhasIniciais,
  horaDe, mapeamentoDaConversa, mapeamentoDaPlanilha, pendenciasDasColunas, premissasDaPlanilha, registrarEstado, resultadoDaSessao, resumoDaFonte,
  type AnaliseGuardada, type ContextoDoGrafico, type EscolhasDaPlanilha, type EstadoSalvo, type FonteDados,
  type PedidoDoChat } from "./paginaUnica";
import type { Levels } from "./territorialScope";
import type { Territory } from "./TerritorialSelection";

// Página única de análise (22/10/2026; reorganizada em 23/10/2026 e 24/10/2026). Primeiro, o aceite de privacidade. No alto, o
// nome do agente e o banner de apresentação; abaixo dele, à esquerda, com os dados prontos, a navegação (Nova sessão, Nova
// análise e Histórico) e o resumo da fonte em uso, com "Trocar". As duas entradas dos dados (Usar dados do Brasil e Enviar meus
// dados) ficam na área central e na conversa, com as mesmas ações; "Enviar meus dados" abre sempre a mesma janela de envio
// (JanelaDeEnvio), com o modelo de planilha XLSX. Abaixo, a área de análise (AreaDeAnalise), que desenha o gráfico com os
// valores do motor; ao lado, sempre, a conversa na caixa flutuante. As telas clássicas (catálogo de análises, preparação, resultados em abas, mapa, investigação e
// diagnósticos compostos) saíram do produto. O motor (/api/analyze e as capacidades) continua.

const API = import.meta.env.VITE_API_BASE_URL || "";
const VAZIO: string[] = [];
const SEM_MUNICIPIOS: Territory[] = [];

type Capacidade = { status: string; reasons: string[] };
type PreExame = { capabilities: Record<string, Capacidade>; territory_choices?: Territory[]; selection_reason?: string;
  values?: { territories: string[]; periods: string[]; categories: string[] };
  territorial_hierarchy?: { status?: string; levels: { role: string; column: string }[] };
  coordinate_separator?: string | null };
type Inspecao = { requires_sheet: boolean; sheets: string[]; columns: string[]; row_count: number;
  suggested_mapping: Record<string, string>; suggested_columns?: Record<string, string[]>; periods: string[];
  categories: string[]; preflight: PreExame | null; curated_defaults?: { category?: string } | null;
  source?: { version?: string } | null; niveis?: Levels; catalog?: CatalogoDaFonte | null };
/** A fonte em uso pela área: pronta (base do Brasil examinada ou planilha com as colunas escolhidas). */
type FonteAtiva = { chave: string; dados: FonteDados; resumo: string; periodos: string[]; categorias: string[]; categoria: string;
  niveis?: Levels; municipios: Territory[]; conversa: FonteDaConversa; catalogo: CatalogoDaFonte | null;
  planilha: { arquivoId: number; inspecao: Inspecao; escolhas: EscolhasDaPlanilha; preExame: PreExame | null } | null };
/** A fonte em preparação: leitura, escolha da aba e painel "Colunas". A fonte em uso continua até esta ficar pronta. */
type Preparo = { geracao: number; arquivoId: number; tipo: "brasil" | "arquivo"; arquivo: File | null; aba: string;
  lendo: boolean; erro: string; inspecao: Inspecao | null; escolhas: EscolhasDaPlanilha | null; preExame: PreExame | null;
  conferindo: boolean; erroDoPreExame: string; pendencias: string[] | null };

async function lerResposta(response: Response): Promise<any> {
  const raw = await response.text();
  let body: any;
  try { body = JSON.parse(raw); }
  catch {
    throw new Error("Não foi possível interpretar a resposta do serviço (HTTP " + response.status + "). Tente novamente ou procure suporte.");
  }
  if (!response.ok) {
    const message = typeof body?.detail === "string" ? body.detail : "Falha no processamento da solicitação.";
    throw new Error(message + " (HTTP " + response.status + ")");
  }
  return body;
}

function mensagemDeErro(exc: unknown): string {
  const texto = exc instanceof Error ? exc.message : String(exc);
  return /failed to fetch|networkerror|fetch failed|network request failed/i.test(texto)
    ? "Não foi possível acessar o serviço de análise. Tente novamente em instantes." : texto;
}

function baixar(nome: string, corpo: string, tipo: string) {
  const url = URL.createObjectURL(new Blob([corpo], { type: tipo }));
  const link = document.createElement("a");
  link.href = url; link.download = nome; link.click();
  URL.revokeObjectURL(url);
}

const novoPreparo = (geracao: number, tipo: "brasil" | "arquivo", arquivo: File | null): Preparo => ({ geracao, arquivoId: geracao,
  tipo, arquivo, aba: "", lendo: true, erro: "", inspecao: null, escolhas: null, preExame: null, conferindo: false,
  erroDoPreExame: "", pendencias: null });

function fonteDoBrasil(inspecao: Inspecao): FonteAtiva {
  const versao = inspecao.source?.version || "";
  const categorias = inspecao.categories || [];
  const dados: FonteDados = { tipo: "brasil", apiBase: API, datasetVersion: versao, sheet: "", mapping: {}, arquivo: null,
    nome: "Dados do Brasil", geoVersion: inspecao.catalog?.complemento_geografico?.token || undefined, rotulos: ROTULOS_DO_BRASIL };
  return { chave: "brasil:" + versao, dados, resumo: resumoDaFonte({ tipo: "brasil", nome: dados.nome, categorias,
    periodos: inspecao.periods || [] }), periodos: inspecao.periods || [], categorias,
    categoria: inspecao.curated_defaults?.category || categorias[0] || "", niveis: inspecao.niveis,
    municipios: inspecao.preflight?.territory_choices || [],
    conversa: { tipo: "brasil", datasetVersion: versao, arquivo: null, sheet: "", mapping: inspecao.suggested_mapping || {}, opcoes: {} },
    catalogo: inspecao.catalog || null, planilha: null };
}

function fonteDaPlanilha(preparo: Preparo, arquivo: File, inspecao: Inspecao, escolhas: EscolhasDaPlanilha): FonteAtiva {
  const preExame = preparo.preExame ?? inspecao.preflight;
  const periodos = preExame?.values?.periods?.length ? preExame.values.periods : inspecao.periods || [];
  // Sem coluna de categoria, a categoria é o objeto da análise escrito pela pessoa (o mesmo que vai em category_constant).
  const categorias = escolhas.mapeamento.category
    ? preExame?.values?.categories?.length ? preExame.values.categories : inspecao.categories || []
    : escolhas.objeto.trim() ? [escolhas.objeto.trim()] : [];
  const dados: FonteDados = { tipo: "arquivo", apiBase: API, datasetVersion: "", sheet: preparo.aba,
    mapping: mapeamentoDaPlanilha(escolhas.mapeamento), arquivo, nome: arquivo.name, premissas: premissasDaPlanilha(escolhas),
    rotulos: escolhas.rotulos };
  const { options } = contextoDaPlanilha(escolhas);
  return { chave: "arquivo:" + preparo.arquivoId + ":" + JSON.stringify([preparo.aba, dados.mapping, dados.premissas, dados.rotulos]),
    dados, resumo: resumoDaFonte({ tipo: "arquivo", nome: arquivo.name, categorias, periodos, rotulos: escolhas.rotulos }),
    periodos, categorias, categoria: categorias[0] || "", municipios: preExame?.territory_choices || [],
    // A conversa recebe também os nomes da unidade e do grupo ("distrito", "província") para responder com eles.
    conversa: { tipo: "arquivo", datasetVersion: "", arquivo, sheet: preparo.aba, mapping: mapeamentoDaConversa(escolhas),
      opcoes: { ...options, rotulos: escolhas.rotulos } },
    catalogo: null, planilha: { arquivoId: preparo.arquivoId, inspecao, escolhas, preExame } };
}

function App() {
  const privacy = useSessionPrivacy();
  useEffect(() => { if (privacy.accepted) return trackSession(); }, [privacy.accepted]);
  const [serverStatus, setServerStatus] = useState<"checking" | "online" | "offline">("checking");
  const [ativa, setAtiva] = useState<FonteAtiva | null>(null);
  const [preparo, setPreparo] = useState<Preparo | null>(null);
  const [escolhendo, setEscolhendo] = useState(false);
  /** A janela "Enviar meus dados" (24/10/2026), aberta por qualquer entrada que envia dados. */
  const [enviando, setEnviando] = useState(false);
  const geracao = useRef(0);
  // Histórico: cada análise guarda o último estado informado pela área (onSalvar). A área é montada de novo (chave) em Nova
  // análise, ao reabrir do Histórico e ao trocar de fonte; na primeira fonte, ela passa de E0 a E1 sem remontar.
  const [analises, setAnalises] = useState<AnaliseGuardada[]>([]);
  const [emExibicao, setEmExibicao] = useState(1);
  const analiseAtual = useRef(1);
  const proximaAnalise = useRef(2);
  const [montagem, setMontagem] = useState<{ n: number; restaurar: EstadoSalvo | null }>({ n: 0, restaurar: null });
  const [pedido, setPedido] = useState<{ id: number; pedido: PedidoDoChat } | null>(null);
  const pedidoId = useRef(0);
  const [contexto, setContexto] = useState<ContextoDoGrafico | null>(null);
  const [aviso, setAviso] = useState("");
  const [confirmarSessao, setConfirmarSessao] = useState(false);
  const [encerrando, setEncerrando] = useState(false);
  const [erroDaSessao, setErroDaSessao] = useState("");
  const fonteAtual = useRef<FonteAtiva | null>(ativa);
  fonteAtual.current = ativa;

  useEffect(() => {
    document.title = "Agente Diagnóstico Territorial";
    let alive = true;
    fetch(API + "/api/health").then(async response => { await lerResposta(response); if (alive) setServerStatus("online"); })
      .catch(() => { if (alive) setServerStatus("offline"); });
    return () => { alive = false; };
  }, []);
  // O aviso da página (Histórico, Nova análise, fonte pronta) some sozinho depois de alguns segundos.
  useEffect(() => {
    if (!aviso) return;
    const timer = window.setTimeout(() => setAviso(""), 10000);
    return () => window.clearTimeout(timer);
  }, [aviso]);

  // ---- Área de análise: contexto, Histórico e pedidos da conversa ----
  const onContexto = useCallback((novo: ContextoDoGrafico) =>
    setContexto(atual => atual && JSON.stringify(atual) === JSON.stringify(novo) ? atual : novo), []);
  const onSalvar = useCallback((estado: EstadoSalvo) => {
    const fonte = fonteAtual.current;
    if (!fonte) return;
    setAnalises(lista => registrarEstado(lista, { id: analiseAtual.current, fonteChave: fonte.chave, fonteNome: fonte.dados.nome, estado }));
  }, []);
  const onPedido = useCallback((novo: PedidoDoChat) => {
    pedidoId.current += 1;
    setPedido({ id: pedidoId.current, pedido: novo });
  }, []);

  function novaMontagem(restaurar: EstadoSalvo | null, id?: number) {
    const proximo = id ?? proximaAnalise.current++;
    analiseAtual.current = proximo;
    setEmExibicao(proximo);
    setPedido(null);
    setContexto(null);
    setMontagem(atual => ({ n: atual.n + 1, restaurar }));
  }
  function ativar(nova: FonteAtiva) {
    const anterior = fonteAtual.current;
    fonteAtual.current = nova;
    // A revisão de contexto da sessão muda com a fonte em uso: as respostas da conversa em trânsito deixam de valer. Muda antes
    // de a página desenhar a nova fonte (27/10/2026; antes, num efeito da página, que roda depois dos efeitos da conversa e da
    // área): o pedido guardado antes dos dados e os primeiros pedidos com a fonte já saem com a revisão nova.
    if (anterior?.chave !== nova.chave) updateContextRevision();
    setAtiva(nova);
    setEscolhendo(false);
    // Troca de fonte: a análise anterior fica no Histórico, e a área recomeça com a nova fonte.
    if (anterior && anterior.chave !== nova.chave) novaMontagem(null);
  }
  function novaAnalise() {
    if (!ativa) return;
    const guardada = analises.some(item => item.id === analiseAtual.current);
    novaMontagem(null);
    setAviso(guardada ? "Análise guardada no Histórico. Nova análise com os mesmos dados." : "Nova análise com os mesmos dados.");
  }
  function abrirDoHistorico(id: number): boolean {
    const item = analises.find(entrada => entrada.id === id);
    if (!item || !ativa || item.fonteChave !== ativa.chave || id === analiseAtual.current) return false;
    novaMontagem(item.estado, item.id);
    setAviso("Análise reaberta como estava, sem recalcular: " + (item.estado.titulo || "análise sem título") + ".");
    return true;
  }
  function analiseAnteriorDaConversa(): string {
    const anterior = ativa ? analiseAnterior(analises, analiseAtual.current, ativa.chave) : null;
    if (!anterior || !abrirDoHistorico(anterior.id)) return "Ainda não há análise anterior nesta sessão, com estes dados.";
    return "Reabri a análise anterior, sem recalcular: " + (anterior.estado.titulo || "análise sem título") + ".";
  }

  // ---- Fonte de dados ----
  async function inspecionar(arquivo: File | null, aba: string): Promise<Inspecao> {
    const form = new FormData();
    if (arquivo) form.append("file", arquivo);
    else { form.append("dataset", "brazil"); form.append("scope", "municipal"); form.append("operation", ""); }
    form.append("sheet", aba);
    return await lerResposta(await fetch(API + "/api/inspect", { method: "POST", body: form })) as Inspecao;
  }
  async function escolherBrasil() {
    if (!privacy.accepted) return;
    if (ativa?.dados.tipo === "brasil" && !preparo) { setEscolhendo(false); return; }
    const minha = ++geracao.current;
    setEscolhendo(false);
    setPreparo(novoPreparo(minha, "brasil", null));
    try {
      const inspecao = await inspecionar(null, "");
      if (minha !== geracao.current) return;
      setServerStatus("online");
      setPreparo(null);
      ativar(fonteDoBrasil(inspecao));
      setAviso("Dados do Brasil prontos.");
    } catch (exc) {
      if (minha !== geracao.current) return;
      setPreparo(atual => atual && atual.geracao === minha ? { ...atual, lendo: false, erro: mensagemDeErro(exc) } : atual);
    }
  }
  function abrirArquivo() {
    if (privacy.accepted) setEnviando(true);
  }
  async function lerPlanilha(minha: number, arquivo: File, aba: string) {
    try {
      const inspecao = await inspecionar(arquivo, aba);
      if (minha !== geracao.current) return;
      setServerStatus("online");
      setPreparo(atual => atual && atual.geracao === minha ? { ...atual, aba, lendo: false, erro: "", inspecao,
        escolhas: inspecao.requires_sheet ? null : escolhasIniciais(inspecao.suggested_mapping), preExame: inspecao.preflight } : atual);
    } catch (exc) {
      if (minha !== geracao.current) return;
      setPreparo(atual => atual && atual.geracao === minha ? { ...atual, lendo: false, erro: mensagemDeErro(exc) } : atual);
    }
  }
  async function escolherArquivo(arquivo: File | undefined) {
    if (!arquivo || !privacy.accepted) return;
    setEnviando(false);
    const minha = ++geracao.current;
    setEscolhendo(false);
    const base = novoPreparo(minha, "arquivo", arquivo);
    if (!/\.(csv|xls|xlsx)$/i.test(arquivo.name)) {
      setPreparo({ ...base, lendo: false, erro: "Formato não reconhecido. Selecione um arquivo CSV, XLS ou XLSX." });
      return;
    }
    if (arquivo.size > 30 * 1024 * 1024) {
      setPreparo({ ...base, lendo: false, erro: "Arquivo acima de 30 MB, o limite experimental desta versão; a planilha não foi processada." });
      return;
    }
    setPreparo(base);
    await lerPlanilha(minha, arquivo, "");
  }
  function escolherAba(aba: string) {
    if (!preparo?.arquivo || !aba) return;
    const minha = ++geracao.current;
    setPreparo({ ...preparo, geracao: minha, aba, lendo: true, erro: "", escolhas: null });
    void lerPlanilha(minha, preparo.arquivo, aba);
  }
  function mudarEscolhas(proximas: EscolhasDaPlanilha) {
    setPreparo(atual => atual ? { ...atual, escolhas: proximas,
      pendencias: atual.pendencias ? pendenciasDasColunas(proximas) : null } : atual);
  }
  function comecarPlanilha() {
    if (!preparo?.arquivo || !preparo.inspecao || !preparo.escolhas) return;
    const pendencias = pendenciasDasColunas(preparo.escolhas);
    if (pendencias.length) { setPreparo({ ...preparo, pendencias }); return; }
    const fonte = fonteDaPlanilha(preparo, preparo.arquivo, preparo.inspecao, preparo.escolhas);
    geracao.current += 1;  // nenhuma resposta pendente do pré-exame volta a esta preparação
    setPreparo(null);
    ativar(fonte);
    setAviso("Planilha pronta: " + fonte.dados.rotulos.unidade.plural + " de " + fonte.dados.nome + ".");
  }
  function reabrirColunas() {
    const planilha = ativa?.planilha;
    if (!planilha || !ativa.dados.arquivo) return;
    const minha = ++geracao.current;
    setEscolhendo(false);
    setPreparo({ geracao: minha, arquivoId: planilha.arquivoId, tipo: "arquivo", arquivo: ativa.dados.arquivo, aba: ativa.dados.sheet,
      lendo: false, erro: "", inspecao: planilha.inspecao, escolhas: planilha.escolhas, preExame: planilha.preExame, conferindo: false,
      erroDoPreExame: "", pendencias: null });
  }
  function cancelarPreparo() {
    geracao.current += 1;
    setPreparo(null);
    setEscolhendo(false);
  }
  // Escolha da fonte pelos botões da área (abertura) e pela conversa: as mesmas ações da barra.
  const escolherBrasilAtual = useRef(escolherBrasil);
  escolherBrasilAtual.current = escolherBrasil;
  const abrirArquivoAtual = useRef(abrirArquivo);
  abrirArquivoAtual.current = abrirArquivo;
  const onEscolherFonte = useCallback((tipo: "brasil" | "arquivo") => {
    if (tipo === "brasil") void escolherBrasilAtual.current();
    else abrirArquivoAtual.current();
  }, []);

  // Pré-exame das colunas da planilha: a cada escolha, o backend recalcula o que a planilha permite (nada é decidido aqui).
  const planilhaEmPreparo = preparo?.tipo === "arquivo" && preparo.arquivo && preparo.inspecao && !preparo.inspecao.requires_sheet &&
    preparo.escolhas ? preparo : null;
  const chaveDoPreExame = planilhaEmPreparo?.escolhas ? JSON.stringify(contextoDaPlanilha(planilhaEmPreparo.escolhas)) : "";
  useEffect(() => {
    if (!planilhaEmPreparo?.escolhas || !planilhaEmPreparo.arquivo) return;
    const minha = planilhaEmPreparo.geracao, arquivo = planilhaEmPreparo.arquivo, aba = planilhaEmPreparo.aba;
    const { mapping, options } = contextoDaPlanilha(planilhaEmPreparo.escolhas);
    const controle = new AbortController();
    setPreparo(atual => atual && atual.geracao === minha ? { ...atual, conferindo: true, erroDoPreExame: "" } : atual);
    const timer = window.setTimeout(async () => {
      const form = new FormData();
      form.append("file", arquivo); form.append("sheet", aba);
      form.append("mapping", JSON.stringify(mapping)); form.append("options", JSON.stringify(options));
      try {
        const preExame = await lerResposta(await fetch(API + "/api/preflight", { method: "POST", body: form, signal: controle.signal })) as PreExame;
        if (!controle.signal.aborted) setPreparo(atual => atual && atual.geracao === minha ? { ...atual, preExame, conferindo: false } : atual);
      } catch (exc) {
        if (!controle.signal.aborted)
          setPreparo(atual => atual && atual.geracao === minha ? { ...atual, conferindo: false, erroDoPreExame: mensagemDeErro(exc) } : atual);
      }
    }, 250);
    return () => { controle.abort(); window.clearTimeout(timer); };
  }, [planilhaEmPreparo?.geracao, chaveDoPreExame]);

  const sugestoes = useMemo(() => {
    const inspecao = preparo?.inspecao;
    if (!inspecao) return {};
    // Grupo territorial: as colunas que o backend reconhece como nível superior (estado, província, departamento…).
    const superiores = (preparo?.preExame?.territorial_hierarchy?.levels || [])
      .filter(nivel => nivel.role.startsWith("territorio_superior")).map(nivel => nivel.column);
    return { ...(inspecao.suggested_columns || {}),
      grupo_territorial: [...new Set([...(inspecao.suggested_columns?.grupo_territorial || []), ...superiores])] };
  }, [preparo?.inspecao, preparo?.preExame]);

  // ---- Nova sessão ----
  async function encerrarSessao() {
    setEncerrando(true);
    setErroDaSessao("");
    try { await endSession(); }
    catch (exc) { setErroDaSessao(mensagemDeErro(exc)); setEncerrando(false); }
  }
  const estadoEmExibicao = analises.find(item => item.id === emExibicao)?.estado ?? null;
  const csvEmExibicao = estadoEmExibicao ? csvDaResposta(estadoEmExibicao.resposta) : "";

  const itensDoHistorico = analises.map(item => ({ id: item.id, titulo: item.estado.titulo || "Análise sem título",
    quando: horaDe(item.estado.quando), fonte: item.fonteNome, mesmaFonte: item.fonteChave === ativa?.chave,
    emExibicao: item.id === emExibicao }));
  const colunasEmPreparo = preparo?.escolhas && preparo.inspecao && !preparo.inspecao.requires_sheet ? preparo : null;

  return <div id="topo" className="pagina min-h-screen bg-canvas">
    {!privacy.accepted && <SessionPrivacy onAccept={privacy.accept}/>}
    {confirmarSessao && <WorkspaceDialog id="new-session-confirmation" title="Deseja iniciar uma nova sessão?" busy={encerrando}
      onClose={() => setConfirmarSessao(false)}>
      <p className="mt-4 text-sm leading-6">Ao iniciar uma nova sessão, a conversa, as análises do Histórico e a fonte de dados atual
        deixam de estar disponíveis. Se quiser conservar a análise em exibição, exporte-a antes de continuar.</p>
      <p className="mt-3 text-xs leading-5">O CSV traz os valores da análise em exibição, em precisão integral; Imprimir / PDF
        imprime a página. Para guardar outra análise, reabra-a pelo Histórico e exporte. Nada fica salvo entre sessões.</p>
      {estadoEmExibicao && <p className="mt-2 text-sm font-semibold" data-testid="session-current-analysis">Em exibição: {estadoEmExibicao.titulo}</p>}
      <div className="dialog-actions">
        <button type="button" data-testid="session-export-csv" disabled={!csvEmExibicao || encerrando}
          onClick={() => baixar("analise_em_exibicao.csv", csvEmExibicao, "text/csv;charset=utf-8")}>Exportar CSV</button>
        <button type="button" data-testid="session-print" disabled={!estadoEmExibicao || encerrando} onClick={() => window.print()}>Imprimir / PDF</button>
        <button type="button" data-testid="cancel-new-session" disabled={encerrando} onClick={() => setConfirmarSessao(false)}>Continuar nesta sessão</button>
        <button type="button" data-testid="confirm-new-session" disabled={encerrando} onClick={() => void encerrarSessao()}>
          {encerrando ? "Encerrando sessão…" : "Iniciar nova sessão"}</button>
      </div>
      {erroDaSessao && <p role="alert" className="mt-3 text-sm text-rose-800">{erroDaSessao}</p>}
    </WorkspaceDialog>}
    {enviando && privacy.accepted && <JanelaDeEnvio apiBase={API} onArquivo={arquivo => { void escolherArquivo(arquivo); }}
      onFechar={() => setEnviando(false)}/>}
    <header className="pagina-cabecalho" data-testid="pagina-cabecalho">
      <div className="pagina-topo">
        <a href="#topo" className="pagina-marca" data-testid="pagina-marca"
          onClick={event => { event.preventDefault(); window.scrollTo({ top: 0, behavior:
            window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); }}>
          <BrandAvatar size={40}/>
          <span className="min-w-0"><strong>Agente Diagnóstico Territorial</strong><small>da Força de Trabalho na Saúde</small></span>
        </a>
      </div>
      <WelcomeHero/>
      {/* Nova sessão, Nova análise e Histórico só com os dados prontos (24/10/2026): antes, a primeira ação é escolher os dados. */}
      {ativa && <div className="pagina-acoes">
        <nav aria-label="Navegação principal" data-testid="main-navigation" className="main-navigation no-print">
          <button type="button" data-testid="nav-new-session" onClick={() => { setErroDaSessao(""); setConfirmarSessao(true); }}>
            <RefreshCw size={18} aria-hidden="true"/>Nova sessão</button>
          <button type="button" data-testid="nav-new-analysis" onClick={novaAnalise}>
            <FileBarChart2 size={18} aria-hidden="true"/>Nova análise</button>
          <HistoricoDeAnalises itens={itensDoHistorico} desabilitado={false} onAbrir={id => { abrirDoHistorico(id); }}/>
        </nav>
      </div>}
      <BarraDaFonte desabilitado={!privacy.accepted} ativa={ativa ? { tipo: ativa.dados.tipo, resumo: ativa.resumo } : null}
        escolhendo={escolhendo} catalogo={ativa?.catalogo ?? null} apiBase={API}
        preparo={preparo ? { tipo: preparo.tipo, nome: preparo.arquivo?.name || "", lendo: preparo.lendo, erro: preparo.erro,
          abas: preparo.inspecao?.requires_sheet ? preparo.inspecao.sheets : null, aba: preparo.aba, colunas: !!colunasEmPreparo } : null}
        onTrocar={() => setEscolhendo(true)}
        onCancelar={cancelarPreparo} onAba={escolherAba} onColunas={ativa?.planilha && !preparo ? reabrirColunas : undefined}>
        {colunasEmPreparo?.escolhas && colunasEmPreparo.inspecao && <ColunasDaPlanilha colunas={colunasEmPreparo.inspecao.columns}
          sugestoes={sugestoes} escolhas={colunasEmPreparo.escolhas}
          disponibilidade={disponibilidadeDaPlanilha(colunasEmPreparo.preExame?.capabilities, colunasEmPreparo.escolhas,
            colunasEmPreparo.preExame?.coordinate_separator === null)}
          pedirSeparador={colunasEmPreparo.preExame?.coordinate_separator === null} conferindo={colunasEmPreparo.conferindo}
          erro={colunasEmPreparo.erroDoPreExame} pendencias={colunasEmPreparo.pendencias} emUso={!!ativa?.planilha}
          onEscolhas={mudarEscolhas} onComecar={comecarPlanilha}/>}
      </BarraDaFonte>
      <p role="status" data-testid="pagina-aviso" className="pagina-aviso no-print">{aviso}</p>
    </header>
    {serverStatus === "offline" && <div role="status" className="no-print mx-4 rounded-lg bg-rose-50 px-4 py-2 text-xs text-rose-800">
      Serviço de análise temporariamente indisponível.</div>}
    <main className="pagina-principal">
      <AreaDeAnalise key={"area-" + montagem.n} fonte={ativa?.dados ?? null} periodos={ativa?.periodos ?? VAZIO}
        categorias={ativa?.categorias ?? VAZIO} categoria={ativa?.categoria ?? ""} niveis={ativa?.niveis}
        municipios={ativa?.municipios ?? SEM_MUNICIPIOS} pedido={pedido} restaurar={montagem.restaurar}
        onContexto={onContexto} onSalvar={onSalvar} onEscolherFonte={onEscolherFonte}
        trocandoFonte={escolhendo && !!ativa && !preparo} onCancelarTroca={() => setEscolhendo(false)}/>
    </main>
    <AnalysisAssistant apiBase={API} privacyAccepted={privacy.accepted}
      fonteEscolhida={ativa?.dados.tipo ?? preparo?.tipo ?? null} fonte={ativa?.conversa ?? null} fonteChave={ativa?.chave ?? ""}
      colunasPendentes={!ativa && !!colunasEmPreparo} contexto={contexto} rotulos={ativa?.dados.rotulos ?? null}
      displayedResultId={resultadoDaSessao(estadoEmExibicao)} onEscolherFonte={onEscolherFonte} onPedido={onPedido}
      onAnaliseAnterior={analiseAnteriorDaConversa}/>
    <footer className="pagina-rodape no-print">
      <p>Agente Diagnóstico Territorial · Protótipo experimental v0.1</p>
    </footer>
  </div>;
}

export default App;
