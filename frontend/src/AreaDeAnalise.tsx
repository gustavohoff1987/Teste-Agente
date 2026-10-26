import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent as EventoPonteiro,
  type ReactNode } from "react";
import { ArrowLeftRight, ChartScatter, ChevronDown, Columns2, Crosshair, Database, Download, Filter, FilterX, GripVertical, Layers3,
  ListOrdered, LoaderCircle, Map as MapaIcone, Pause, Play, RefreshCw, Ruler, Scale, SlidersHorizontal, Undo, Upload, Wrench, X } from "lucide-react";
import {
  ErroDoMotor, pedirMapa, pedirPainel, type FonteDoMotor, type MapaOpcoes, type Pendencia, type PainelConjuntoPedido,
  type PainelItem, type PainelMunicipios, type PainelNivel, type PainelOpcoes, type PainelResposta, type ReferenciaElegivel,
} from "./painelApi";
import {
  ABAS, CLASSES_TENDENCIA, DESCRICAO_DAS_CLASSES, INDICADORES, MAX_LIGACOES, NOME_SELECAO, ORDEM_DAS_VISOES, TEXTO_DAS_FONTES,
  TEXTO_ESCOLHA_DOS_DADOS, TEXTO_SEM_SELECAO, TITULO_DO_SISTEMA, LARGURA_LADO_A_LADO, LIMITE_LEVE, MINIMO_TENDENCIA, NOMES_FAMILIAS,
  NOMES_FAMILIA_TENDENCIA, NOMES_RELACOES, NOMES_VISOES, NOTA_TPL11, ROTULOS_GENERICOS, TEXTO_SEM_POPULACAO, ajustesDaAnalise, aplicarPedido,
  artigo, avisoDaFamilia, basesEmUso, basesPossiveis, bloqueioDoPedido, camadaDeCor, chaveDoPedido, comparacaoQueContinua, contextoDoGrafico,
  corContinuaDoMapa, corOrdinal, corteAtivo, cronologica, definicaoInicial, disponibilidadeDaFamilia, disponibilidadeDoMapa, empilharPasso,
  dentroDosFiltros, destaqueDaAnalise, escreverLimites, exibirCompetencia, familiaCalculada, formatarNumero, formatarVariacao, generoDe, gradienteDaVariacao, grupoDaUnidade,
  grupoDoItem, gruposDaFonte, intervaloDaSerie, intervaloEntre, itensParaOMapa, janelaPadrao, lerEstadoSalvo, lerLimites, ligacoesDoMapa,
  limiteDaVariacao, limparNivel, listaDeCompetencias, lugarDoUniverso, maisRecente, maiuscula, montarCsv, montarDica, montarOpcoes,
  apresentacaoDaAba, nomeDaUnidade, normalizarBases, notaSemClassificacao, novoConjunto, ordemNeutra, paletaDoGrafico, paresDasBases, pedidoDependeDoIndicador, pintar,
  pinturaDoMapa, prefixoDe, precisaQuintisDoMapa, referenciaElegivel, resumoDosTerritoriosBase, resumoDoUniverso, ritmoDaJanela, ritmosDaBase, RITMOS_TENDENCIA,
  rotulosEfetivos, salvarEstado, semSelecao, separarItens, significadoDaClasse, tamanhoDoMapa, textoDaMarca, textoDoDesfazer, textoDoDesfeito,
  textoDoMetodo, textoDosTerritoriosBase, textoForaDoDesenho, textoInstrucaoGrupos, tituloDaAnalise, todosOs, umA, visaoEfetiva,
  type Aba, type Ajuste, type Apresentacao, type ContextoDoGrafico, type Corte, type DefinicaoAnalise, type Disponivel, type Escala,
  type EstadoSalvo, type Familia, type FonteDados, type FuncaoPainel, type NiveisDaBase, type PassoDaInteracao, type PedidoDoChat,
  type UnidadeDoCatalogo, type Visao, type Vista,
} from "./painelModel";
import type { DadosDoMapa, MapaHandle, MapaProps, Posicoes, VistaDesenho } from "./mapaContrato";
import PainelChart, { type FaseAnimacao, type LinhaDeReferencia } from "./PainelChart";
import PainelSeries, { LegendaDaSerie, MAX_SERIES, Velocidades } from "./PainelSeries";
import PainelSetas, { LegendaDoQuadro } from "./PainelSetas";
import PainelRotatividade from "./PainelRotatividade";
import PainelRuler from "./PainelRuler";
import PainelTerritorios from "./PainelTerritorios";
import PainelDetalhes from "./PainelDetalhes";
import MapaAnalise from "./MapaAnalise";
import { animarTransicao, posicoesDoGrafico } from "./transicaoVistas";
import { GavetaComparar, GavetaCondicoes, GavetaExportar, GavetaJuntar, GavetaOrdenar, GavetaReferencia } from "./PainelGavetas";
import { useEsquemaDeCor } from "./useEsquemaDeCor";
import IconeVassoura from "./IconeVassoura";
import "./analise.css";

// Área de análise da página única (22/10/2026). Numa linha de abas (23/10/2026), que aparece só com os dados prontos
// (24/10/2026): a Seleção de Territórios, o conjunto analisado, compartilhado por todas as análises, e as quatro análises
// (Análise de Distribuição, Análise Espacial, Análise de Tendência e Análise de Rotatividade). A Seleção mostra só a escolha dos
// territórios (o Brasil, os estados ou os municípios; nada de resultado), em duas áreas: a lista, à esquerda, e o que já está
// marcado, à direita; cada análise começa por "Entenda esta análise" (recolhível) e pelos ajustes dela, num painel colado na aba.
// Abaixo, nas análises: o título dinâmico com a frase-resumo do motor, a barra de funções com a escala e a vista do desenho
// (Gráfico | Mapa | Lado a lado), os painéis laterais e os Detalhes; na Análise de Tendência (24/10/2026), o desenho fica logo
// abaixo dos ajustes, com a explicação num painel à direita, de largura ajustável pela divisória. Antes dos dados (E0), só a
// identificação e as duas entradas dos dados. Todo número vem do motor (/api/painel e /api/painel/mapa, pelo cliente
// painelApi.ts); a tela só posiciona, filtra (estado visual) e desenha. Trocar de vista é estado visual e não pede nada novo ao
// motor (RQ-REP-06). No alto, fixos (24/10/2026, segunda rodada): Desfazer (o "Voltar" até 25/10/2026), sequencial, como o Ctrl+Z,
// de toda a interação na área (a seleção, as abas, os ajustes, os filtros e a vista), e Limpar seleção, que tira os territórios em
// análise sem apagar os dados.
// A conversa age sobre o gráfico pela prop `pedido`; a estrutura da página recebe o contexto (onContexto) e o estado salvo
// (onSalvar) e pode reabrir sem recalcular (restaurar).

export type { ContextoDoGrafico, EstadoSalvo, Familia, FonteDados, NiveisDaBase, PedidoDoChat, UnidadeDoCatalogo, Visao } from "./painelModel";

export type AreaDeAnaliseProps = {
  /** null = E0, antes dos dados. */
  fonte: FonteDados | null;
  periodos: string[];
  categorias: string[];
  categoria: string;
  /** Base do Brasil: o bloco "niveis" da inspeção (estados e total de municípios). */
  niveis?: NiveisDaBase;
  /** Catálogo das unidades para a lista e a busca. */
  municipios: UnidadeDoCatalogo[];
  /** Comando da conversa (cada id novo é aplicado uma vez). */
  pedido: { id: number; pedido: PedidoDoChat } | null;
  /** Estado do Histórico a reabrir sem recalcular. */
  restaurar: EstadoSalvo | null;
  onContexto: (contexto: ContextoDoGrafico) => void;
  onSalvar: (estado: EstadoSalvo) => void;
  /** As duas entradas dos dados (24/10/2026): "Usar dados do Brasil" e "Enviar meus dados" (que abre a janela de envio, com o
   * modelo de planilha). */
  onEscolherFonte: (tipo: "brasil" | "arquivo") => void;
  /** "Trocar" da fonte: a escolha dos dados volta aqui, na área central, com o cancelamento. */
  trocandoFonte?: boolean;
  onCancelarTroca?: () => void;
};

const MAX_CACHE = 6;
const FUNCOES: { chave: FuncaoPainel; rotulo: string; icone: ReactNode }[] = [
  { chave: "regua", rotulo: "Régua", icone: <Ruler size={15} aria-hidden="true"/> },
  { chave: "condicoes", rotulo: "Condições", icone: <Filter size={15} aria-hidden="true"/> },
  { chave: "ordenar", rotulo: "Ordenar", icone: <ListOrdered size={15} aria-hidden="true"/> },
  { chave: "comparar", rotulo: "Comparar", icone: <ArrowLeftRight size={15} aria-hidden="true"/> },
  { chave: "juntar", rotulo: "Juntar", icone: <Layers3 size={15} aria-hidden="true"/> },
  { chave: "exportar", rotulo: "Exportar", icone: <Download size={15} aria-hidden="true"/> },
];
const TITULOS_PAINEL: Record<FuncaoPainel, string> = { regua: "Régua", condicoes: "Condições", ordenar: "Ordenar", comparar: "Comparar",
  juntar: "Juntar", exportar: "Exportar", referencia: "Território de referência" };
const VISTAS: { chave: VistaDesenho; rotulo: string; icone: ReactNode }[] = [
  { chave: "grafico", rotulo: "Gráfico", icone: <ChartScatter size={14} aria-hidden="true"/> },
  { chave: "mapa", rotulo: "Mapa", icone: <MapaIcone size={14} aria-hidden="true"/> },
  { chave: "lado", rotulo: "Lado a lado", icone: <Columns2 size={14} aria-hidden="true"/> },
];
const NOMES_VISTAS: Record<VistaDesenho, string> = { grafico: "Gráfico", mapa: "Mapa", lado: "Lado a lado" };
/** Duração da troca animada entre o gráfico e o mapa (ms) e o limite de espera por ela. */
const DURACAO_TRANSICAO = 700;
const esperar = (ms: number) => new Promise<void>(resolve => window.setTimeout(resolve, ms));
/** Painel da explicação ao lado do desenho da tendência (24/10/2026): largura inicial e limites, em px (no máximo metade da área). */
const LATERAL_INICIAL = 340, LATERAL_MIN = 240, LATERAL_MAX = 620;

/** Consulta de mídia acompanhada (movimento reduzido, largura da janela). */
function useMidia(consulta: string): boolean {
  const [ativa, setAtiva] = useState(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia(consulta).matches);
  useEffect(() => {
    if (!window.matchMedia) return;
    const media = window.matchMedia(consulta);
    const atualizar = () => setAtiva(media.matches);
    atualizar();
    media.addEventListener?.("change", atualizar);
    return () => media.removeEventListener?.("change", atualizar);
  }, [consulta]);
  return ativa;
}

function baixar(nome: string, corpo: string, tipo: string) {
  const url = URL.createObjectURL(new Blob([corpo], { type: tipo }));
  const link = document.createElement("a");
  link.href = url; link.download = nome; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Id do botão de cada aba (os seletores das análises continuam os de antes). */
const idDaAba = (aba: Aba) => aba === "territorios" ? "analise-aba-territorios" : "analise-familia-" + aba;
/** O que a Seleção guarda de cada nível. */
type Escolha = Pick<DefinicaoAnalise, "nivel" | "base" | "estados" | "conjuntos">;
const escolhaDe = (d: DefinicaoAnalise): Escolha => ({ nivel: d.nivel, base: d.base, estados: d.estados, conjuntos: d.conjuntos });
/** O que o Desfazer devolve (24/10/2026): a definição da análise (a seleção e os ajustes), a aba, a lista aberta e o estado visual
 * das análises (a vista, a escala, a régua, os itens marcados e os filtros). */
type EstadoDaInteracao = { def: DefinicaoAnalise; aba: Aba; aberto: string | null; vista: VistaDesenho; escala: Escala; corte: Corte | null;
  selecionados: string[]; filtroClasse: string | null; soAtende: boolean };

/** O corpo da apresentação de uma aba: parágrafos, a lista das classes (na tendência) e a nota. */
function TextoDaApresentacao({ aba, apresentacao, destaque = [] }: { aba: Aba; apresentacao: Apresentacao; destaque?: string[] }) {
  return <div data-testid="analise-apresentacao" data-aba={aba} className="analise-apresentacao">
    {apresentacao.paragrafos.map((texto, indice) => <p key={indice}>{texto}</p>)}
    {apresentacao.itens && <div data-testid="analise-apresentacao-classes" className="analise-apresentacao-classes">
      <p className="analise-apresentacao-subtitulo">O que significa cada classe</p>
      <dl>{apresentacao.itens.map(item => {
        // Termo destacado pela conversa ("não entendi a aceleração"): a explicação da tela, aberta e à vista.
        const destacado = destaque.includes(item.termo);
        return <div key={item.termo} data-testid={destacado ? "analise-apresentacao-destaque" : undefined}
          className={destacado ? "analise-apresentacao-destaque" : undefined}><dt>{item.termo}</dt><dd>{item.texto}</dd></div>;
      })}</dl>
    </div>}
    {apresentacao.nota && <p className="analise-apresentacao-nota">{apresentacao.nota}</p>}
  </div>;
}
/** "Entenda esta análise" (24/10/2026): a explicação começa recolhida em todas as análises, desde a primeira visita (25/10/2026,
 * pedido do responsável; antes, abria na primeira visita, menos na Tendência), para não ocupar espaço: o desenho fica no alto, e
 * a pessoa abre a explicação quando quiser. Se a pessoa a abre ou fecha, a aba guarda a escolha na sessão da página. */
const explicacaoAberta = new Map<Aba, boolean>();
/** A explicação pedida pela conversa (26/10/2026): abre o "Entenda" da aba e destaca os termos; `n` muda a cada pedido. Cada
 * pedido abre o quadro uma vez: voltar à aba depois não o reabre se a pessoa o fechou. */
type ExplicacaoPedida = { n: number; aba: Aba; termos: string[] };
const explicacaoAtendida = new Map<Aba, number>();
let explicacoesPedidas = 0;  // numeração única na página, também entre montagens da área (Nova análise, Histórico)
function EntendaEstaAnalise({ aba, apresentacao, pedida }: { aba: Aba; apresentacao: Apresentacao; pedida?: ExplicacaoPedida | null }) {
  const [aberta, setAberta] = useState(() => explicacaoAberta.get(aba) ?? false);
  const quadro = useRef<HTMLDetailsElement>(null);
  const destaque = pedida && pedida.aba === aba ? pedida.termos : [];
  useEffect(() => {
    if (!pedida || pedida.aba !== aba || explicacaoAtendida.get(aba) === pedida.n) return;
    explicacaoAtendida.set(aba, pedida.n);
    explicacaoAberta.set(aba, true);
    setAberta(true);
    const alvo = quadro.current?.querySelector(".analise-apresentacao-destaque") ?? quadro.current;
    alvo?.scrollIntoView?.({ block: "nearest", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }, [pedida?.n]);
  return <details ref={quadro} data-testid="analise-entenda" data-aba={aba} open={aberta} className="analise-entenda"
    onToggle={event => { const valor = event.currentTarget.open; if (valor !== aberta) { explicacaoAberta.set(aba, valor); setAberta(valor); } }}>
    <summary data-testid="analise-entenda-botao"><ChevronDown size={15} aria-hidden="true" className="analise-entenda-seta"/>
      Entenda esta análise<span className="sr-only">: {apresentacao.titulo}</span></summary>
    <TextoDaApresentacao aba={aba} apresentacao={apresentacao} destaque={destaque}/>
  </details>;
}

export default function AreaDeAnalise(props: AreaDeAnaliseProps) {
  const { fonte, periodos, categorias, niveis, municipios, pedido, restaurar } = props;
  const tipo = fonte?.tipo ?? null;
  const chaveFonte = fonte ? [fonte.tipo, fonte.datasetVersion, fonte.nome, fonte.sheet, fonte.arquivo?.name ?? "", fonte.arquivo?.size ?? ""].join("|") : "";
  const grupos = useMemo(() => gruposDaFonte(niveis, municipios), [niveis, municipios]);
  const idsDosGrupos = useMemo(() => grupos.map(item => item.id), [grupos]);
  const grupoDeMapa = useMemo(() => new Map(municipios.map(item => [item.id, grupoDaUnidade(item)])), [municipios]);
  const grupoDe = useCallback((id: string) => grupoDeMapa.get(id) ?? prefixoDe(id), [grupoDeMapa]);
  const pronto = !!fonte && periodos.length > 0 && (fonte.tipo !== "brasil" || !!niveis);
  // Planilha sem população: só a quantidade (a Densidade fica desligada, com o motivo); as premissas do painel Colunas vão em
  // todo pedido.
  const temPopulacao = tipo !== "arquivo" || !!fonte?.mapping?.population;
  const premissasDaFonte = tipo === "arquivo" ? fonte?.premissas : undefined;
  // O mapa precisa das coordenadas: a base do Brasil tem a sede de cada município; a planilha, as colunas de latitude e longitude.
  const temCoordenadas = tipo === "brasil" || (!!fonte?.mapping?.latitude && !!fonte?.mapping?.longitude);
  const movimentoReduzido = useMidia("(prefers-reduced-motion: reduce)");
  const largo = useMidia("(min-width: " + LARGURA_LADO_A_LADO + "px)");
  // Modo escuro (23/10/2026): a paleta das bolhas e das legendas segue o esquema de cor do aparelho; a impressão é sempre clara.
  const paleta = paletaDoGrafico(useEsquemaDeCor());

  const [def, setDef] = useState<DefinicaoAnalise>(() => definicaoInicial({ tipo, periodos, categoria: props.categoria, temGrupos: !!niveis,
    temPopulacao, premissas: premissasDaFonte }));
  /** Referência pedida na conversa por critério: o atributo citado já vem escolhido no Território de referência. */
  const [criterioDoChat, setCriterioDoChat] = useState<{ atributo: "densidade" | "quantidade" | "populacao"; ordem: "desc" | "asc" } | null>(null);
  /** Desfazer (24/10/2026, segunda rodada): os passos da interação, o mais recente no fim. */
  const [passos, setPassos] = useState<PassoDaInteracao<EstadoDaInteracao>[]>([]);
  /** O que a última mudança coletiva da Seleção fez ("Municípios da Bahia desmarcados."), mostrado junto do que está marcado. */
  const [avisoSelecao, setAvisoSelecao] = useState<string | null>(null);
  /** Aba à vista: a Seleção de Territórios ou uma análise. A análise desenhada é a da definição (def.familia): a Seleção e a aba de
   * uma análise que não pode ser executada mostram a apresentação e o motivo, e o desenho continua com a última análise. */
  const [aba, setAba] = useState<Aba>("territorios");
  const [explicacaoPedida, setExplicacaoPedida] = useState<ExplicacaoPedida | null>(null);
  const [escala, setEscala] = useState<Escala>("linear");
  const [corte, setCorte] = useState<Corte | null>(null);
  const [selecionados, setSelecionados] = useState<string[]>([]);
  const [painel, setPainel] = useState<FuncaoPainel | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);
  const [vista, setVista] = useState<Vista>("final");
  const [fase, setFase] = useState<FaseAnimacao>("parado");
  const [soAtende, setSoAtende] = useState(false);
  const [filtroClasse, setFiltroClasse] = useState<string | null>(null);
  const [ferramentas, setFerramentas] = useState(false);
  const [faixasTexto, setFaixasTexto] = useState("");
  const [resposta, setResposta] = useState<PainelResposta | null>(null);
  const [calculado, setCalculado] = useState<{ chave: string; def: DefinicaoAnalise; familia: Familia; opcoes: PainelOpcoes } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<{ mensagem: string; pendencia: Pendencia | null } | null>(null);
  const [tentativa, setTentativa] = useState(0);
  const [aviso, setAviso] = useState("");
  // Vista do desenho (estado visual da sessão, guardado no Histórico): o gráfico é a vista inicial; a escolha não se perde ao
  // trocar de território ou de competência. Ao abrir a Análise de Tendência (24/10/2026), o gráfico. Sem o mapa disponível,
  // aparece o gráfico, e a escolha fica guardada.
  const [vistaEscolhida, setVistaEscolhida] = useState<VistaDesenho>("grafico");
  /** Cor contínua do mapa: a escolha saiu com a pergunta "Como pintar o mapa?" (23/10/2026); o estado salvo guarda false. */
  const corContinua = false;
  const [motivoVistaAberto, setMotivoVistaAberto] = useState(false);
  /** Vista de destino desenhada invisível durante a troca animada (as posições de destino são lidas nela). */
  const [oculta, setOculta] = useState<"grafico" | "mapa" | null>(null);
  /** O mapa, depois de aparecer, continua montado (oculto) enquanto houver mapa: volta como foi deixado, com o zoom. */
  const [mapaMontado, setMapaMontado] = useState(false);
  /** Destaque cruzado no lado a lado: o item sob o mouse num desenho aparece destacado no outro. */
  const [ativoCruzado, setAtivoCruzado] = useState<string | null>(null);
  const [dadosDoMapa, setDadosDoMapa] = useState<{ chave: string; dados: DadosDoMapa } | null>(null);
  const [carregandoMapa, setCarregandoMapa] = useState(false);
  const [erroMapa, setErroMapa] = useState<{ chave: string; mensagem: string; pendencia: Pendencia | null } | null>(null);
  const [tentativaMapa, setTentativaMapa] = useState(0);
  /** Largura do painel da explicação ao lado do desenho da tendência (a divisória a ajusta). */
  const [larguraLateral, setLarguraLateral] = useState(LATERAL_INICIAL);
  const cache = useRef(new Map<string, PainelResposta>());
  const cacheMapa = useRef(new Map<string, DadosDoMapa>());
  const contextoRef = useRef(props.onContexto); contextoRef.current = props.onContexto;
  const salvarRef = useRef(props.onSalvar); salvarRef.current = props.onSalvar;
  const visualRef = useRef({ escala, corte, selecionados, vista: vistaEscolhida, corContinua });
  visualRef.current = { escala, corte, selecionados, vista: vistaEscolhida, corContinua };
  const tituloPainelRef = useRef<HTMLHeadingElement>(null);
  const gatilhoRef = useRef<HTMLElement | null>(null);
  const faixasRef = useRef<HTMLInputElement>(null);
  const quadroRef = useRef<HTMLDivElement>(null);
  const graficoRef = useRef<HTMLDivElement>(null);
  const corpoRef = useRef<HTMLDivElement>(null);
  const mapaRef = useRef<MapaHandle>(null);
  const transicao = useRef(0);

  // ------------------------------------------------------------------------------------------ Desfazer: o histórico da interação
  // Cada ação reversível guarda, antes de mudar, o estado da interação (registrar); depois da mudança, o passo só entra no
  // histórico se algo de fato mudou. Desfazer devolve o estado do último passo. Ações seguidas do mesmo tipo contínuo (o arraste da
  // régua) viram um passo só (empilharPasso).
  const estadoDaInteracao = (): EstadoDaInteracao => ({ def, aba, aberto, vista: vistaEscolhida, escala, corte, selecionados, filtroClasse,
    soAtende });
  const pendente = useRef<PassoDaInteracao<EstadoDaInteracao> | null>(null);
  function registrar(rotulo: string, tipoDoPasso = rotulo) {
    const agora = Date.now();
    // Na mesma ação (o mesmo clique), vale o primeiro registro: é ele que descreve o que a pessoa fez.
    if (pendente.current && agora - pendente.current.quando < 40) return;
    pendente.current = { rotulo, tipo: tipoDoPasso, quando: agora, estado: estadoDaInteracao() };
  }
  const instantaneo = JSON.stringify(estadoDaInteracao());
  useEffect(() => {
    const passo = pendente.current;
    if (!passo) return;
    pendente.current = null;
    if (JSON.stringify(passo.estado) !== instantaneo) setPassos(atual => empilharPasso(atual, passo));
  }, [instantaneo]);
  function desfazer() {
    const atual = instantaneo;
    let pilha = passos;
    while (pilha.length && JSON.stringify(pilha[pilha.length - 1].estado) === atual) pilha = pilha.slice(0, -1);
    const passo = pilha[pilha.length - 1];
    if (!passo) { setPassos([]); return; }
    pendente.current = null;
    setPassos(pilha.slice(0, -1));
    const e = passo.estado;
    setDef(e.def); setAba(e.aba); setAberto(e.aberto); setVistaEscolhida(e.vista); setEscala(e.escala); setCorte(e.corte);
    setSelecionados(e.selecionados); setFiltroClasse(e.filtroClasse); setSoAtende(e.soAtende);
    if (painel === "referencia" && e.def.familia !== "espacial") setPainel(null);
    setVista("final"); setFase("parado"); setAvisoSelecao(null);
    setAviso(textoDoDesfeito(passo));
  }
  const passoADesfazer = passos[passos.length - 1] ?? null;

  const rotulos = rotulosEfetivos(resposta?.rotulos, fonte?.rotulos, tipo);
  const temIdentificador = !!fonte?.mapping?.identity;
  const disponibilidade = resposta?.disponibilidade ?? null;
  const comBolhasDeGrupo = tipo === "brasil" && grupos.length > 0 && (disponibilidade?.estados?.disponivel ?? disponibilidade?.grupos?.disponivel ?? true);
  const disponivelDe = useCallback((familia: Familia): Disponivel => disponibilidadeDaFamilia(familia, { fonte: tipo, nivel: def.nivel,
    disponibilidade, temIdentificador, rotulos }), [tipo, def.nivel, disponibilidade, temIdentificador, rotulos]);
  /** O mapa numa definição (a da tela ou a que resulta de um pedido da conversa). */
  const mapaDe = (d: DefinicaoAnalise) => disponibilidadeDoMapa({ fonte: tipo, temCoordenadas, nivel: d.nivel,
    series: d.nivel === "municipios" && d.familia === "tendencia" && visaoEfetiva(d) === "series", rotatividade: d.familia === "rotatividade", rotulos });
  const nomes = useMemo(() => new Map<string, string>([...municipios.map(item => [item.id, nomeDaUnidade(item)] as [string, string]),
    ...(resposta?.itens || []).map(item => [item.id, item.rotulo] as [string, string])]), [municipios, resposta]);
  /** Grupo da lista de uma bolha de grupo (estado) do motor. */
  const grupoDaBolha = useCallback((id: string) => {
    const item = resposta?.itens.find(atual => atual.id === id);
    return grupoDoItem(item ?? { id, uf: null, rotulo: id }, grupos);
  }, [resposta, grupos]);
  const unidadesDoGrupo = useCallback((id: string) => {
    const grupo = grupoDaBolha(id);
    return grupo === null ? null : grupos.find(item => item.id === grupo)?.unidades ?? null;
  }, [grupoDaBolha, grupos]);

  // ------------------------------------------------------------------------------------------ fonte nova: abertura (E1)
  const iniciado = useRef("");
  const pedidoPendente = useRef<{ id: number; pedido: PedidoDoChat } | null>(null);
  const ultimoPedido = useRef<number | null>(null);
  const reiniciarVisual = () => { setCorte(null); setSelecionados([]); setPainel(null); setAberto(null); setVista("final"); setFase("parado");
    setSoAtende(false); setFiltroClasse(null); setFaixasTexto(""); setOculta(null); setAtivoCruzado(null); setMotivoVistaAberto(false); };
  useEffect(() => {
    if (!fonte) {
      if (iniciado.current) { iniciado.current = ""; cache.current.clear(); cacheMapa.current.clear(); setResposta(null); setCalculado(null); setErro(null);
        setDadosDoMapa(null); setErroMapa(null); reiniciarVisual(); setPassos([]); pendente.current = null; setAvisoSelecao(null);
        setDef(definicaoInicial({ tipo: null, periodos, categoria: props.categoria, temGrupos: false })); }
      return;
    }
    if (!pronto || iniciado.current === chaveFonte) return;
    iniciado.current = chaveFonte;
    cache.current.clear();
    cacheMapa.current.clear();
    reiniciarVisual();
    setResposta(null); setCalculado(null); setErro(null); setDadosDoMapa(null); setErroMapa(null);
    let inicial = definicaoInicial({ tipo, periodos, categoria: props.categoria, temGrupos: grupos.length > 0, temPopulacao,
      premissas: premissasDaFonte });
    // Outra fonte, outro histórico: o Desfazer não volta a uma seleção de outra base.
    setPassos([]); pendente.current = null; setAvisoSelecao(null);
    const pendentePedido = pedidoPendente.current ?? (pedido && pedido.id !== ultimoPedido.current ? pedido : null);
    if (pendentePedido) {
      pedidoPendente.current = null;
      ultimoPedido.current = pendentePedido.id;
      const resultado = aplicarPedido(inicial, pendentePedido.pedido, { periodos, nomes, temGrupos: grupos.length > 0, grupoDe, mapa: mapaDe,
        todosOsEstados: idsDosGrupos, temBrasil: tipo === "brasil" && grupos.length > 0,
        disponivel: familia => disponibilidadeDaFamilia(familia, { fonte: tipo, nivel: inicial.nivel, disponibilidade: null, temIdentificador, rotulos }) });
      if (!temPopulacao && pendentePedido.pedido.indicador === "densidade") { resultado.definicao.indicador = "quantidade"; resultado.mensagens.push(TEXTO_SEM_POPULACAO); }
      inicial = resultado.definicao;
      if (resultado.selecao) setSelecionados(resultado.selecao);
      if (resultado.abrir) setPainel(resultado.abrir);
      if (resultado.vista) setVistaEscolhida(resultado.vista);
      setCriterioDoChat(resultado.criterio);
      setAviso(["Pedido da conversa aplicado ao gráfico.", ...resultado.mensagens].join(" "));
    } else setAviso((tipo === "brasil" ? "Dados do Brasil carregados." : "Planilha carregada.") + " " + TEXTO_SEM_SELECAO);
    setDef(inicial);
    setAba(semSelecao(inicial) ? "territorios" : inicial.familia);
  }, [fonte, pronto, chaveFonte]);
  // Competência e categoria que chegam depois da fonte.
  useEffect(() => { if (pronto && !def.competencia && periodos.length) setDef(atual => ({ ...atual, competencia: maisRecente(periodos) })); }, [pronto, periodos]);
  useEffect(() => { if (!def.categoria && props.categoria) setDef(atual => ({ ...atual, categoria: props.categoria })); }, [props.categoria]);
  // O período com que a Análise de Tendência abre (24/10/2026): o anual (janelaPadrao), à vista no campo Período. Vale ao entrar na
  // aba, por um pedido da conversa sem ritmo e ao reabrir um estado sem janela; a pessoa troca pelo semestral quando quiser.
  useEffect(() => {
    if (!pronto || def.familia !== "tendencia" || def.janela.length) return;
    const janela = janelaPadrao(periodos);
    if (janela.length) setDef(atual => atual.familia === "tendencia" && !atual.janela.length ? { ...atual, janela } : atual);
  }, [pronto, def.familia, def.janela.length, periodos]);

  // ------------------------------------------------------------------------------------------ pedido ao motor
  const dispAtual = disponivelDe(def.familia);
  const familiaPedida = familiaCalculada(def, dispAtual.disponivel && !dispAtual.pendente);
  const bloqueio = pronto ? bloqueioDoPedido(def, { fonte: tipo, rotulos }) : "Preparando os dados…";
  const quintisDoMapa = precisaQuintisDoMapa(def, familiaPedida, mapaDe(def).disponivel);
  const rotulosDoPedido = tipo === "arquivo" ? fonte?.rotulos : undefined;
  const opcoes = useMemo(() => bloqueio ? null : montarOpcoes(def, familiaPedida, grupoDe, { quintisDoMapa, todosOsEstados: idsDosGrupos,
    rotulos: rotulosDoPedido, periodos }), [def, familiaPedida, bloqueio, grupoDe, quintisDoMapa, idsDosGrupos, rotulosDoPedido, periodos]);
  const chave = opcoes ? chaveFonte + "::" + chaveDoPedido(opcoes) : "";
  const fonteMotor: FonteDoMotor | null = useMemo(() => fonte ? { tipo: fonte.tipo, apiBase: fonte.apiBase, datasetVersion: fonte.datasetVersion,
    sheet: fonte.sheet, mapping: fonte.mapping, arquivo: fonte.arquivo, geoVersion: fonte.geoVersion } : null, [fonte]);
  const nomesDoCatalogo = useMemo(() => new Map(municipios.map(item => [item.id, nomeDaUnidade(item)] as [string, string])), [municipios]);
  const lugarDe = useCallback((d: DefinicaoAnalise) => lugarDoUniverso({ nivel: d.nivel, base: d.base, conjuntos: d.conjuntos.length, grupos,
    rotulos, brasil: tipo === "brasil", grupoDe, estados: d.estados, nomes: nomesDoCatalogo }), [grupos, rotulos, tipo, grupoDe, nomesDoCatalogo]);
  const tituloDe = useCallback((d: DefinicaoAnalise, familia: Familia, r: PainelResposta | null) => {
    const ref = d.referencia;
    const porItem = referenciaElegivel(ref);
    return tituloDaAnalise({ fonte: tipo, familia, visao: visaoEfetiva(d), indicador: d.indicador, nivel: d.nivel, categoria: d.categoria,
      competencia: d.competencia, janela: d.janela, rotatividade: d.rotatividade, lugar: lugarDe(d), rotulos,
      serie: familia === "tendencia" && d.visao === "series" ? intervaloDaSerie(d, periodos) : undefined, referenciaPorItem: porItem,
      referencia: !ref || referenciaElegivel(ref) ? null : (r?.referencia?.membros.map(m => m.rotulo).join(" e ") ||
        ref.membros.map(id => nomes.get(id) || id).join(" e ")) });
  }, [tipo, lugarDe, rotulos, nomes, periodos]);

  // Histórico: a restauração roda antes do pedido ao motor, para a resposta guardada entrar no cache antes; assim, reabrir
  // uma análise igual ao estado inicial (os estados) não pede de novo. A vista e a cor do mapa voltam como foram guardadas (um
  // estado de antes delas reabre no gráfico).
  const ultimoRestaurado = useRef<EstadoSalvo | null>(null);
  useEffect(() => {
    if (!restaurar || restaurar === ultimoRestaurado.current || !pronto || iniciado.current !== chaveFonte) return;
    ultimoRestaurado.current = restaurar;
    const lido = lerEstadoSalvo(restaurar);
    if (!lido) { setAviso("Não foi possível reabrir esta análise: o estado salvo não tem a forma esperada."); return; }
    registrar("Reabrir uma análise do Histórico");
    reiniciarVisual();
    setEscala(lido.visual.escala); setCorte(lido.visual.corte); setSelecionados(lido.visual.selecionados);
    setVistaEscolhida(lido.visual.vista ?? "grafico");
    setDef(lido.definicao);
    setAba(semSelecao(lido.definicao) ? "territorios" : lido.definicao.familia);
    if (lido.resposta && lido.opcoes) {
      cache.current.set(lido.chave, lido.resposta);
      setResposta(lido.resposta);
      setCalculado({ chave: lido.chave, def: lido.definicao, familia: lido.familia, opcoes: lido.opcoes });
    }
    setAviso("Análise reaberta do Histórico, sem recalcular.");
  }, [restaurar, pronto, chaveFonte]);

  useEffect(() => {
    if (!fonteMotor || !opcoes) {
      setCarregando(false);
      // Sem territórios escolhidos, nada da seleção anterior fica à vista (nem gráfico, nem mapa, nem frase-resumo).
      if (fonteMotor && pronto && semSelecao(def)) { setResposta(null); setCalculado(null); setErro(null); }
      return;
    }
    if (calculado?.chave === chave) { setCarregando(false); setErro(null); return; }
    const emCache = cache.current.get(chave);
    if (emCache) {
      setResposta(emCache); setCalculado({ chave, def, familia: familiaPedida, opcoes }); setErro(null); setCarregando(false);
      return;
    }
    const controle = new AbortController(), pedidoDef = def, pedidoFamilia = familiaPedida, pedidoOpcoes = opcoes;
    setCarregando(true);
    setErro(null);
    const timer = window.setTimeout(() => {
      pedirPainel(fonteMotor, pedidoOpcoes, controle.signal)
        .then(corpo => {
          if (controle.signal.aborted) return;
          cache.current.set(chave, corpo);
          while (cache.current.size > MAX_CACHE) cache.current.delete(cache.current.keys().next().value as string);
          setResposta(corpo);
          setCalculado({ chave, def: pedidoDef, familia: pedidoFamilia, opcoes: pedidoOpcoes });
          // Histórico: cada cálculo guarda o estado, que reabre sem recalcular.
          const visual = visualRef.current;
          salvarRef.current(salvarEstado(tituloDe(pedidoDef, pedidoFamilia, corpo).titulo, { chave, familia: pedidoFamilia, opcoes: pedidoOpcoes,
            definicao: pedidoDef, visual: { escala: visual.escala, corte: null, selecionados: visual.selecionados, vista: visual.vista,
              corContinua: visual.corContinua } }, corpo));
        })
        .catch((exc: unknown) => {
          if (controle.signal.aborted) return;
          setErro({ mensagem: exc instanceof Error ? exc.message : "Não foi possível montar o gráfico.",
            pendencia: exc instanceof ErroDoMotor ? exc.pendencia : null });
        })
        .finally(() => { if (!controle.signal.aborted) setCarregando(false); });
    }, 150);
    return () => { controle.abort(); window.clearTimeout(timer); };
  }, [chave, tentativa]);

  function voltarAoCalculado() {
    if (!calculado) return;
    registrar("Voltar ao último gráfico calculado");
    setDef(calculado.def);
    setAviso("De volta ao último gráfico calculado.");
  }

  // ------------------------------------------------------------------------------------------ comando da conversa e Histórico
  useEffect(() => {
    if (!pedido || pedido.id === ultimoPedido.current) return;
    if (!pronto || iniciado.current !== chaveFonte) { pedidoPendente.current = pedido; return; }
    ultimoPedido.current = pedido.id;
    const { explicar, ...resto } = pedido.pedido;
    if (explicar) {
      // Explicação pedida na conversa: abre "Entenda esta análise" na aba e destaca os termos; não muda o gráfico.
      const termos = explicar.termos.map(codigo => CLASSES_TENDENCIA.find(classe => classe.codigo === codigo)?.rotulo)
        .filter((rotulo): rotulo is string => !!rotulo);
      if (def.familia === explicar.aba) setAba(explicar.aba);
      setExplicacaoPedida({ n: ++explicacoesPedidas, aba: explicar.aba, termos });
      if (!Object.values(resto).some(valor => valor !== undefined && valor !== null)) return;
    }
    const resultado = aplicarPedido(def, pedido.pedido, { periodos, nomes, temGrupos: comBolhasDeGrupo, disponivel: disponivelDe, grupoDe, mapa: mapaDe,
      todosOsEstados: idsDosGrupos, temBrasil: comBolhasDeGrupo });
    if (!temPopulacao && pedido.pedido.indicador === "densidade") { resultado.definicao.indicador = "quantidade"; resultado.mensagens.push(TEXTO_SEM_POPULACAO); }
    // O pedido da conversa também é um passo do Desfazer (24/10/2026): Desfazer devolve o que estava antes dele.
    registrar("Aplicar o pedido da conversa");
    // A comparação pedida na conversa vale como veio; a de antes só continua com os itens dela na análise.
    if (pedido.pedido.funcao !== "comparar") resultado.definicao.comparar = comparacaoQueContinua(def, resultado.definicao, grupoDe);
    setDef(resultado.definicao);
    if (resultado.selecao) setSelecionados(resultado.selecao);
    if (resultado.abrir) setPainel(resultado.abrir);
    setCriterioDoChat(resultado.criterio);
    // Os pedidos da conversa são sobre o gráfico: com a Seleção à vista (que não mostra resultados), a análise aparece.
    const abaDoPedido: Aba | null = pedido.pedido.familia && resultado.definicao.familia === pedido.pedido.familia ? pedido.pedido.familia
      : aba === "territorios" && !semSelecao(resultado.definicao) ? resultado.definicao.familia : null;
    if (abaDoPedido) setAba(abaDoPedido);
    const base = resultado.definicao.base;
    if (resultado.definicao.nivel === "municipios" && base.estados.length === 1 && !base.ids.length) setAberto(base.estados[0]);
    if (resultado.definicao.nivel === "estados") setAberto(null);
    // "Ver no mapa" e "volte ao gráfico": estado visual. O mapa que só passa a existir com o pedido (os municípios de um estado)
    // abre sem a troca animada; o que já existia, com ela. Ao abrir a tendência pela conversa, o gráfico, como pelo clique na aba.
    if (resultado.vista === "grafico" || (!resultado.vista && resultado.definicao.familia === "tendencia" && def.familia !== "tendencia"))
      trocarVista("grafico", false, false);
    else if (resultado.vista === "mapa" && vistaExibida === "grafico") {
      if (mapa.disponivel) trocarVista("mapa", false, false);
      else setVistaEscolhida("mapa");
    }
    setAviso(["Pedido da conversa aplicado ao gráfico.", ...resultado.mensagens].join(" "));
  }, [pedido, pronto, chaveFonte]);


  // ------------------------------------------------------------------------------------------ reproduzir (Trajetória)
  useEffect(() => {
    if (fase === "preparar") {
      let segundo = 0;
      const primeiro = requestAnimationFrame(() => { segundo = requestAnimationFrame(() => { setFase("tocar"); setVista("final"); }); });
      return () => { cancelAnimationFrame(primeiro); cancelAnimationFrame(segundo); };
    }
    if (fase === "tocar") {
      const timer = window.setTimeout(() => setFase("parado"), 1700);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [fase]);

  // ------------------------------------------------------------------------------------------ o que está na tela
  const defDesenho = calculado?.def ?? def;
  const familiaDesenho: Familia = calculado?.familia ?? "distribuicao";
  const visaoDesenho = visaoEfetiva(defDesenho);
  // O indicador desenhado é o do pedido só quando ele muda a resposta (grupos, faixas, tendência...); senão, o escolhido agora.
  const indicadorNoPedido = !!calculado && pedidoDependeDoIndicador(calculado.opcoes);
  const indicador = indicadorNoPedido ? defDesenho.indicador : def.indicador;
  const distanciaNaTela = familiaDesenho === "espacial" && !!resposta?.referencia;
  const referenciaPorItem = distanciaNaTela && resposta?.referencia?.tipo === "elegiveis";
  const relacaoNaTela = referenciaPorItem ? resposta?.referencia?.relacao ?? null : null;
  const serieNaTela = familiaDesenho === "tendencia" && !!resposta?.serie;
  const tendenciaNaTela = familiaDesenho === "tendencia" && !!resposta?.competencia_inicial && !serieNaTela;
  // A visão entre a Tendência e a Trajetória é só estado visual: segue a escolha atual, desde que o motor tenha devolvido a tendência
  // (quatro competências ou mais). A Série temporal tem pedido próprio (o intervalo dela).
  const temTendencia = tendenciaNaTela && defDesenho.janela.length >= MINIMO_TENDENCIA && (!!resposta?.tendencia || !!resposta?.itens.some(item => item.tendencia));
  const visaoNaTela: Visao = serieNaTela ? "series" : !tendenciaNaTela ? "mudanca" : def.visao === "classes" && temTendencia ? "classes" : "mudanca";
  const series = visaoNaTela === "series";
  // Visão Tendência: o quadro de setas (24/10/2026), no lugar das bolhas; o cometa, com "Primeira", "Última" e "Reproduzir", fica na
  // Trajetória. A dica do mapa continua com a variação nas duas visões.
  const quadroDeSetas = tendenciaNaTela && visaoNaTela === "classes";
  const cometa = tendenciaNaTela && visaoNaTela === "mudanca";
  const dicaComVariacao = tendenciaNaTela && visaoNaTela !== "series";
  const rotatividadeNaTela = familiaDesenho === "rotatividade";
  const camada = series ? "unica" : tendenciaNaTela ? (visaoNaTela === "mudanca" ? "variacao" : "classes") : camadaDeCor(familiaDesenho, visaoDesenho, resposta, defDesenho);
  const camadaFinal = resposta?.condicoes && defDesenho.condicoes.length ? "condicoes" : resposta?.ordenacao && defDesenho.ordenar ? "ordem" : camada;

  // Vista do desenho e mapa. Os estados não têm ponto (o atalho leva aos municípios); a planilha precisa de latitude e
  // longitude; a Série temporal é só do gráfico. "Lado a lado" só com a janela larga; ao estreitar, volta ao mapa.
  const mapa = disponibilidadeDoMapa({ fonte: tipo, temCoordenadas, nivel: def.nivel, series: series || (def.familia === "tendencia" && def.visao === "series"),
    rotatividade: def.familia === "rotatividade" || rotatividadeNaTela, rotulos });
  const vistaExibida: VistaDesenho = !mapa.disponivel ? "grafico" : vistaEscolhida === "lado" && !largo ? "mapa" : vistaEscolhida;
  const mapaNaTela = vistaExibida !== "grafico";
  const lado = vistaExibida === "lado";
  useEffect(() => { if (!largo && vistaEscolhida === "lado") setVistaEscolhida("mapa"); }, [largo, vistaEscolhida]);
  useEffect(() => { if (mapaNaTela) setMapaMontado(true); }, [mapaNaTela]);
  useEffect(() => { if (mapa.disponivel) setMotivoVistaAberto(false); }, [mapa.disponivel]);
  useEffect(() => { if (!lado) setAtivoCruzado(null); }, [lado]);
  // Pontos do mapa: os do motor na competência do que está desenhado, pedidos quando o mapa aparece e, em segundo plano, quando o
  // gráfico mostra unidades com o mapa disponível (o mapinha da dica usa os mesmos pontos). Memória por fonte e competência.
  const competenciaDoMapa = resposta?.competencia || def.competencia;
  const categoriaDoMapa = resposta?.categoria || def.categoria;
  const chaveMapa = fonte && competenciaDoMapa ? chaveFonte + "::" + JSON.stringify([competenciaDoMapa, categoriaDoMapa, tipo === "arquivo" ? def.premissas : {}]) : "";
  const dadosAtuais = dadosDoMapa?.dados ?? null;
  const dadosConferem = !!dadosDoMapa && dadosDoMapa.chave === chaveMapa;
  const erroDoMapa = erroMapa && erroMapa.chave === chaveMapa ? erroMapa : null;
  const semCoordenada = useMemo(() => mapaNaTela && dadosConferem && dadosAtuais
    ? new Map(dadosAtuais.semCoordenada.map(item => [item.id, item.motivo] as [string, string])) : null, [mapaNaTela, dadosConferem, dadosAtuais]);

  const exibicao = { distancia: distanciaNaTela, variacao: tendenciaNaTela && visaoNaTela === "mudanca",
    tendencia: tendenciaNaTela && visaoNaTela === "classes", condicoes: !!resposta?.condicoes && defDesenho.condicoes.length > 0,
    rotatividade: rotatividadeNaTela, semCoordenada };
  const { plotaveis, fora } = useMemo(() => resposta ? separarItens(resposta.itens, indicador, exibicao) : { plotaveis: [], fora: [] },
    [resposta, indicador, exibicao.distancia, exibicao.variacao, exibicao.tendencia, exibicao.condicoes, exibicao.rotatividade, exibicao.semCoordenada]);
  const filtrosVisuais = useMemo(() => ({ indicador, corte, soAtende, condicoes: exibicao.condicoes, filtroClasse, tendencia: exibicao.tendencia }),
    [indicador, corte, soAtende, filtroClasse, exibicao.condicoes, exibicao.tendencia]);
  const visiveis = useMemo(() => plotaveis.filter(item => dentroDosFiltros(item, filtrosVisuais)), [plotaveis, filtrosVisuais]);
  const selecao = useMemo(() => selecionados.filter(id => (resposta?.itens || []).some(item => item.id === id)), [selecionados, resposta]);
  // Territórios base da Análise Espacial (25/10/2026, pedido do responsável; cumulativos desde a terceira rodada do dia): todos os
  // selecionados (o padrão) ou alguns, escolhidos no painel do Território de referência; cada um aparece ligado ao seu território
  // de referência no gráfico (a referência como bolha de contexto, no 0 km) e no mapa. Só estado visual: o pedido ao motor é o
  // mesmo; a base que sai da análise deixa de valer. Clicar numa bolha continua só marcando.
  const basesDaReferencia = useMemo(() => resposta ? basesPossiveis(resposta.itens) : [], [resposta]);
  const todasAsBases = !def.territoriosBase;
  const idsDasBases = useMemo(() => basesEmUso(def.territoriosBase, basesDaReferencia), [def.territoriosBase, basesDaReferencia]);
  const pares = useMemo(() => distanciaNaTela && resposta ? paresDasBases(resposta, idsDasBases) : [], [distanciaNaTela, resposta, idsDasBases]);
  // As ligações do gráfico: das bases à vista (dentro da régua e dos filtros), as marcadas primeiro, até MAX_LIGACOES.
  const paresLigados = useMemo(() => {
    const aVista = new Set(visiveis.map(item => item.id)), marcadas = new Set(selecao);
    return pares.filter(par => par.referencias.length > 0 && aVista.has(par.base.id))
      .sort((a, b) => Number(marcadas.has(b.base.id)) - Number(marcadas.has(a.base.id))).slice(0, MAX_LIGACOES);
  }, [pares, visiveis, selecao]);
  // Destaque da análise (26/10/2026): com a comparação em exibição, só os comparados ficam inteiros no gráfico de bolhas; na
  // análise espacial com territórios base escolhidos um a um, as bases e as referências delas. As demais bolhas esmaecem.
  const destaque = useMemo(() => destaqueDaAnalise(def.comparar, todasAsBases ? [] : pares,
    new Set((resposta?.itens || []).map(item => item.id))), [def.comparar, todasAsBases, pares, resposta]);
  function escolherBases(ids: string[] | null, rotulo: string) {
    const nova = ids === null ? null : normalizarBases(ids, basesDaReferencia);
    if (JSON.stringify(nova) === JSON.stringify(def.territoriosBase ?? null)) return;
    ajustar(rotulo, { territoriosBase: nova });
  }
  const limiteVariacao = useMemo(() => resposta ? limiteDaVariacao(resposta, indicador, plotaveis) : 0, [resposta, indicador, plotaveis]);
  const totalGrupos = resposta?.grupos ? ({ quartis: 4, quintis: 5, decis: 10 } as Record<string, number>)[resposta.grupos.tipo] ?? resposta.grupos.contagens.length : 0;
  const totalFaixas = resposta?.faixas ? Math.max(resposta.faixas.rotulos.length, resposta.faixas.contagens.length) : 0;
  const primeiros = resposta?.ordenacao?.primeiros ?? null;
  const pintura = useMemo(() => {
    const parametros = { camada: camadaFinal, indicador, limiteVariacao, totalGrupos, totalFaixas, primeiros, paleta };
    return (item: PainelItem) => pintar(item, parametros);
  }, [camadaFinal, indicador, limiteVariacao, totalGrupos, totalFaixas, primeiros, paleta]);
  const limiares = useMemo(() => corte ? [corte.minimo, corte.maximo] : [], [corte]);
  const dominio = resposta?.dominios[indicador] ?? null;
  const idsNaTela = useMemo(() => visiveis.map(item => item.id), [visiveis]);
  const { titulo, subtitulo } = tituloDe(def, familiaPedida, resposta);
  // Frase-resumo do motor, abaixo do subtítulo. Ela fala do indicador do cálculo (o da resposta; numa resposta de antes, o do
  // pedido): se a troca do indicador não pediu nada novo ao motor, a frase sai até voltar o indicador do cálculo ou chegar um
  // cálculo novo, para nunca descrever o outro indicador.
  const indicadorDoCalculo = resposta?.indicador ?? calculado?.opcoes.indicador ?? null;
  const resumoNaTela = resposta?.resumo?.texto && (!indicadorDoCalculo || indicadorDoCalculo === indicador) ? resposta.resumo.texto : null;
  const referenciasDaResposta = useMemo(() => referenciaPorItem ? (resposta?.referencia?.membros ?? []).map(m => m.id) : [],
    [referenciaPorItem, resposta]);
  const contexto = useMemo(() => ({ ...contextoDoGrafico(def, idsNaTela, titulo, grupoDe, referenciasDaResposta), vista: vistaExibida,
    resumo: resumoNaTela, mapaDisponivel: mapa.disponivel, motivoSemMapa: mapa.motivo, comparar: [...def.comparar] }),
  [def, idsNaTela, titulo, grupoDe, referenciasDaResposta, vistaExibida, resumoNaTela, mapa.disponivel, mapa.motivo]);
  const ultimoContexto = useRef("");
  useEffect(() => {
    const json = JSON.stringify(contexto);
    if (json === ultimoContexto.current) return;
    ultimoContexto.current = json;
    contextoRef.current(contexto);
  }, [contexto]);

  const querMapa = !!fonteMotor && !!chaveMapa && mapa.disponivel && (mapaNaTela || (resposta?.nivel === "municipios" && plotaveis.length > 0));
  useEffect(() => {
    if (!querMapa || !fonteMotor) { setCarregandoMapa(false); return; }
    const emCache = cacheMapa.current.get(chaveMapa);
    if (emCache) { setDadosDoMapa({ chave: chaveMapa, dados: emCache }); setErroMapa(null); setCarregandoMapa(false); return; }
    const controle = new AbortController(), chavePedida = chaveMapa;
    // Nas planilhas, as premissas e os rótulos vão como no gráfico; na base do Brasil, o motor recusa os dois.
    const pedidoMapa: MapaOpcoes = { competencia: competenciaDoMapa, categoria: categoriaDoMapa,
      ...(tipo === "arquivo" && Object.keys(def.premissas).length ? { premissas: def.premissas } : {}),
      ...(tipo === "arquivo" && fonte?.rotulos ? { rotulos: fonte.rotulos } : {}) };
    setCarregandoMapa(true);
    setErroMapa(null);
    pedirMapa(fonteMotor, pedidoMapa, controle.signal)
      .then(dados => {
        if (controle.signal.aborted) return;
        cacheMapa.current.set(chavePedida, dados);
        while (cacheMapa.current.size > MAX_CACHE) cacheMapa.current.delete(cacheMapa.current.keys().next().value as string);
        setDadosDoMapa({ chave: chavePedida, dados });
      })
      .catch((exc: unknown) => {
        if (controle.signal.aborted) return;
        setErroMapa({ chave: chavePedida, mensagem: exc instanceof Error ? exc.message : "Não foi possível obter os pontos do mapa.",
          pendencia: exc instanceof ErroDoMotor ? exc.pendencia : null });
      })
      .finally(() => { if (!controle.signal.aborted) setCarregandoMapa(false); });
    return () => controle.abort();
  }, [querMapa, chaveMapa, tentativaMapa]);

  // ------------------------------------------------------------------------------------------ ações
  const mudar = (parte: Partial<DefinicaoAnalise>) => setDef(atual => ({ ...atual, ...parte }));
  /** Um ajuste da análise (o indicador, a competência, o período, a visão…): um passo do Desfazer. */
  const ajustar = (rotulo: string, parte: Partial<DefinicaoAnalise>) => { registrar(rotulo); mudar(parte); };
  const alternar = useCallback((id: string) => {
    registrar((selecionados.includes(id) ? "Desmarcar " : "Marcar ") + (nomes.get(id) || id) + " no desenho");
    setSelecionados(atual => atual.includes(id) ? atual.filter(item => item !== id) : [...atual, id]);
  }, [selecionados, nomes, def, aba, aberto, vistaEscolhida, escala, corte, filtroClasse, soAtende]);
  /** Toda aba abre (23/10/2026): a Seleção de Territórios, e cada análise com a apresentação dela; a que não pode ser executada
   * com os dados mostra o motivo, e o desenho continua com a última análise. Trocar de aba é um passo do Desfazer. */
  function escolherAba(proxima: Aba) {
    if (proxima === aba) return;
    registrar("Abrir a " + (proxima === "territorios" ? NOME_SELECAO : NOMES_FAMILIAS[proxima]));
    if (proxima === "territorios") { setAba("territorios"); return; }
    escolherFamilia(proxima);
  }
  function escolherFamilia(familia: Familia) {
    const disponivel = disponivelDe(familia);
    setAba(familia);
    if (!disponivel.disponivel) { setAviso(NOMES_FAMILIAS[familia] + " indisponível com estes dados: " + disponivel.motivo); return; }
    mudar({ familia });
    setFiltroClasse(null);
    // Ao abrir a Análise de Tendência (24/10/2026): o gráfico como apresentação (o mapa continua como alternativa) e o período anual,
    // que o efeito do período padrão aplica quando a janela está vazia.
    if (familia === "tendencia" && aba !== "tendencia") { setVistaEscolhida("grafico"); setMotivoVistaAberto(false); }
    // O território de referência é pedido depois da seleção: sem territórios, a aba mostra a apresentação e os ajustes.
    const comSelecao = def.nivel === "municipios" && !semSelecao(def);
    if (familia === "espacial" && !def.referencia && comSelecao) abrirPainel("referencia");
    else if (painel === "referencia") setPainel(null);
    if (disponivel.pendente) setAviso(NOMES_FAMILIAS[familia] + ": " + disponivel.motivo);
  }
  function teclasAbas(event: KeyboardEvent<HTMLButtonElement>, indice: number) {
    const proxima = event.key === "ArrowRight" ? (indice + 1) % ABAS.length : event.key === "ArrowLeft" ? (indice + ABAS.length - 1) % ABAS.length
      : event.key === "Home" ? 0 : event.key === "End" ? ABAS.length - 1 : null;
    if (proxima === null) return;
    event.preventDefault();
    document.getElementById(idDaAba(ABAS[proxima]))?.focus();
  }
  /** Com as unidades à vista, a análise espacial que esperava por elas pede o território de referência. */
  function pedirOQueFalta() {
    if (def.familia === "espacial" && !def.referencia && disponivelDe("espacial").disponivel) abrirPainel("referencia");
  }
  /** Mudança feita na Seleção de Territórios: o nível em análise e a escolha de cada nível. Cada uma é um passo do Desfazer; a
   * coletiva (muitos de uma vez) também aparece por escrito junto do que está marcado. */
  function mudarEscolha(parte: Partial<Escolha>, rotulo: string, coletiva = false) {
    registrar(rotulo);
    if (parte.nivel && parte.nivel !== def.nivel) setSelecionados([]);
    trocarEscolha({ ...escolhaDe(def), ...parte });
    setCorte(null);
    setAvisoSelecao(coletiva ? rotulo : null);
  }
  /** A escolha nova, com a comparação só enquanto os itens dela continuam na análise. */
  function trocarEscolha(escolha: Escolha) {
    mudar({ ...escolha, comparar: comparacaoQueContinua(def, escolha, grupoDe) });
  }
  /** Juntar ou desfazer um conjunto: uma mudança no que está na análise, como as da Seleção (um passo do Desfazer). */
  function mudarConjuntos(conjuntos: PainelConjuntoPedido[], rotulo: string) {
    registrar(rotulo);
    trocarEscolha({ ...escolhaDe(def), conjuntos });
  }
  function escolherNivel(nivel: PainelNivel) {
    const grupo = rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
    const nome = nivel === "brasil" ? "Brasil" : nivel === "estados" ? grupo.plural : rotulos.unidade.plural;
    mudarEscolha({ nivel }, "Trocar o nível para " + nome);
    setAviso(nivel === "brasil" ? "Brasil inteiro na análise, como uma unidade." : nivel === "estados"
      ? maiuscula(grupo.plural) + ": marque " + (generoDe(grupo) === "f" ? "uma, várias ou todas." : "um, vários ou todos.")
      : maiuscula(rotulos.unidade.plural) + ": a seleção continua como estava.");
  }
  /** Limpar seleção (24/10/2026, controle global, no alto): tira os territórios do nível em uso (limparNivel, decisão 5 de
   * 25/10/2026: em Municípios, os municípios e os conjuntos; em Estados, os estados), sem apagar a base carregada, os ajustes das
   * análises nem a escolha guardada dos outros níveis. No nível Brasil, o país é a própria unidade: o botão fica desligado, com o
   * motivo. Os desenhos que dependem da seleção saem, e a comparação sai com os itens. É um passo do Desfazer. */
  const selecaoLimpa = limparNivel(escolhaDe(def));
  const temSelecaoParaLimpar = selecaoLimpa !== null;
  function limparSelecao() {
    if (!selecaoLimpa) return;
    registrar("Limpar seleção");
    trocarEscolha(selecaoLimpa);
    setSelecionados([]); setCorte(null); setSoAtende(false); setFiltroClasse(null);
    setAvisoSelecao("Seleção limpa.");
    setAviso("Seleção limpa: nenhum território na análise. A base de dados continua carregada. Para desfazer, use o botão Desfazer.");
  }
  /** Navegação que troca o que está na análise (abrir um estado pela bolha, o atalho do mapa): um passo do Desfazer. */
  function navegar(parte: Partial<Escolha>, rotulo: string) {
    registrar(rotulo);
    trocarEscolha({ ...escolhaDe(def), ...parte });
    setSelecionados([]); setCorte(null);
  }
  const voltarAosGrupos = "Voltar " + (generoDe(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!) === "f" ? "às " : "aos ") +
    (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural;
  /** A bolha de um estado ("Ver os N municípios"): os municípios dele na análise. */
  function abrirGrupoDaBolha(id: string) {
    const grupo = grupoDaBolha(id);
    if (grupo === null) { setAviso("Não foi possível associar esta bolha a um item da lista de territórios."); return; }
    const info = grupos.find(item => item.id === grupo);
    navegar({ nivel: "municipios", base: { todos: false, estados: [grupo], ids: [] } },
      "Abrir " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " de " + (info ? info.nome : grupo));
    setAberto(grupo);
    setAviso("Mostrando " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " de " + (info ? info.nome : grupo) +
      ". Para voltar " + (generoDe(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!) === "f" ? "às " : "aos ") +
      (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural + ", use Desfazer, no alto.");
    pedirOQueFalta();
  }
  /** A lista de um estado na Seleção ("Ver os N municípios ›" e "Voltar aos estados"): navegação, um passo do Desfazer. */
  function abrirLista(grupo: string | null) {
    if (grupo === aberto) return;
    const info = grupo ? grupos.find(item => item.id === grupo) : null;
    registrar(grupo ? "Abrir a lista de " + (info?.nome ?? grupo) : voltarAosGrupos);
    setAberto(grupo);
  }
  function abrirPainel(qual: FuncaoPainel) {
    gatilhoRef.current = document.activeElement as HTMLElement | null;
    setPainel(qual);
    setFerramentas(false);
    requestAnimationFrame(() => tituloPainelRef.current?.focus({ preventScroll: true }));
  }
  function fecharPainel() {
    setPainel(null);
    requestAnimationFrame(() => gatilhoRef.current?.focus?.({ preventScroll: true }));
  }
  /** Volta à Seleção de Territórios, a qualquer momento, com o foco na lista. */
  function irParaTerritorios() {
    setFerramentas(false);
    if (aba !== "territorios") registrar("Abrir a " + NOME_SELECAO);
    setAba("territorios");
    requestAnimationFrame(() => {
      const tituloSel = document.getElementById("analise-territorios-titulo");
      tituloSel?.scrollIntoView({ block: "nearest", behavior: movimentoReduzido ? "auto" : "smooth" });
      tituloSel?.focus({ preventScroll: true });
    });
  }
  function juntar(rotulo: string) {
    const membros = selecao.filter(id => resposta?.itens.find(item => item.id === id)?.tipo === "municipio");
    if (membros.length < 2) return;
    const conjunto = novoConjunto(def.conjuntos, membros, rotulo);
    mudarConjuntos([...def.conjuntos, conjunto], "Juntar " + conjunto.rotulo);
    setSelecionados([conjunto.id]);
    setAviso("Conjunto " + conjunto.rotulo + " criado: a bolha mostra a soma das contagens dos componentes.");
  }
  function desfazerConjunto(id: string) {
    const conjunto = def.conjuntos.find(item => item.id === id);
    mudarConjuntos(def.conjuntos.filter(item => item.id !== id), "Desfazer o conjunto " + (conjunto?.rotulo ?? id));
    setSelecionados(atual => atual.filter(item => item !== id));
  }
  function aplicarReferencia(referencia: ReferenciaElegivel) {
    ajustar("Aplicar o território de referência", { referencia, familia: "espacial" });
    setAviso("Território de referência aplicado: o eixo horizontal passa a ser a distância até a referência de cada " + rotulos.unidade.singular + ".");
  }
  function mudarCompetencia(valor: string) { ajustar("Trocar a competência para " + exibirCompetencia(valor), { competencia: valor }); setCorte(null); }
  function reproduzir() {
    if (!cometa) return;
    if (movimentoReduzido || plotaveis.length > LIMITE_LEVE) { setVista("final"); return; }
    setVista("inicial");
    setFase("preparar");
  }
  function escolherPendencia(chavePendencia: string, valor: string) {
    // Os papéis confirmados formam uma lista (confirmed_roles); as demais premissas são um valor só.
    const atuais = def.premissas[chavePendencia];
    const novo = chavePendencia === "confirmed_roles"
      ? [...new Set([...(Array.isArray(atuais) ? atuais : typeof atuais === "string" ? [atuais] : []), valor])] : valor;
    ajustar("Confirmar uma premissa", { premissas: { ...def.premissas, [chavePendencia]: novo } });
    setAviso("Premissa confirmada: " + chavePendencia + " = " + valor + ".");
  }
  /** O Histórico guarda a vista e a cor do mapa escolhidas depois do cálculo (a mesma análise, sem novo pedido). */
  function guardarVisual(parte: { vista?: VistaDesenho }) {
    if (!calculado || !resposta) return;
    salvarRef.current(salvarEstado(tituloDe(calculado.def, calculado.familia, resposta).titulo, { chave: calculado.chave, familia: calculado.familia,
      opcoes: calculado.opcoes, definicao: calculado.def, visual: { escala, corte: null, selecionados, vista: vistaEscolhida, corContinua, ...parte } }, resposta));
  }
  /** Troca a vista do desenho (estado visual: nada é pedido ao motor). Entre o gráfico e o mapa, sem movimento reduzido e com até
   * LIMITE_LEVE itens, as bolhas deslizam até os pontos: posições de origem, a vista de destino invisível, as posições de destino
   * no quadro seguinte, a animação e a revelação. No lado a lado, e nos demais casos, a troca é direta. A troca pela pessoa é um
   * passo do Desfazer. */
  function trocarVista(nova: VistaDesenho, conferir = true, comPasso = true) {
    if (conferir && nova !== "grafico" && !mapa.disponivel) {
      setMotivoVistaAberto(true);
      setAviso("Mapa indisponível: " + (mapa.motivo ?? ""));
      return;
    }
    setMotivoVistaAberto(false);
    const de = vistaExibida;
    if (nova === vistaEscolhida && nova === de) return;
    if (comPasso) registrar("Trocar a vista para " + NOMES_VISTAS[nova]);
    setVistaEscolhida(nova);
    guardarVisual({ vista: nova });
    setAviso(nova === "grafico" ? "Gráfico à vista." : nova === "mapa" ? "Mapa à vista: a mesma análise do gráfico." : "Gráfico e mapa lado a lado.");
    const token = ++transicao.current;
    const posicoesDe = (qual: VistaDesenho): Posicoes => qual === "grafico" ? (graficoRef.current ? posicoesDoGrafico(graficoRef.current) : new Map())
      : mapaRef.current?.posicoes() ?? new Map();
    const animar = !movimentoReduzido && plotaveis.length <= LIMITE_LEVE && de !== nova && de !== "lado" && nova !== "lado" && !!resposta;
    const origem = animar ? posicoesDe(de) : new Map();
    if (!origem.size) { setOculta(null); return; }
    setOculta(nova === "grafico" ? "grafico" : "mapa");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (token !== transicao.current) return;
      const destino = posicoesDe(nova), raiz = quadroRef.current;
      const animacao = raiz && destino.size
        ? Promise.race([animarTransicao(raiz, origem, destino, DURACAO_TRANSICAO).catch(() => undefined), esperar(DURACAO_TRANSICAO * 2)])
        : Promise.resolve();
      void animacao.then(() => { if (token === transicao.current) setOculta(null); });
    }));
  }
  /** Atalho dos estados: os municípios dos estados escolhidos (ou de todos), já no mapa (um passo do Desfazer). */
  function verUnidadesNoMapa() {
    const alguns = def.estados.length > 0 && def.estados.length < grupos.length;
    navegar({ nivel: "municipios", base: alguns ? { todos: false, estados: [...def.estados], ids: [] } : { todos: true, estados: [], ids: [] } },
      "Ver " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " no mapa");
    setAberto(null);
    setMotivoVistaAberto(false);
    setVistaEscolhida("mapa");
    setAviso(maiuscula(alguns ? artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " dos estados escolhidos" : todosOs(rotulos.unidade)) +
      " no mapa. Para voltar " + (generoDe(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!) === "f" ? "às " : "aos ") +
      (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural + ", use Desfazer, no alto.");
    pedirOQueFalta();
  }
  /** Limpar filtros (a função das análises, 24/10/2026): a régua, as condições, a ordenação, a comparação, o filtro da classe e os
   * itens marcados no desenho; a seleção de territórios e os ajustes da análise continuam. Desfazer devolve os filtros. */
  const filtrosAtivos = !!corte || def.condicoes.length > 0 || !!def.ordenar || def.comparar.length > 0 || !!filtroClasse || soAtende ||
    selecionados.length > 0;
  function limparFiltros() {
    registrar("Limpar filtros");
    mudar({ condicoes: [], ordenar: null, comparar: [] });
    setCorte(null); setSoAtende(false); setFiltroClasse(null); setSelecionados([]);
    if (painel === "regua" || painel === "condicoes" || painel === "ordenar" || painel === "comparar") setPainel(null);
    setAviso("Filtros limpos: os territórios e os ajustes da análise continuam. Para desfazer, use o botão Desfazer.");
  }
  // Com o Brasil como unidade, só Exportar vale: um painel aberto antes (a régua, as condições…) fecha, em vez de ficar à vista
  // sem efeito.
  useEffect(() => {
    if (def.nivel === "brasil" && painel && painel !== "exportar") setPainel(null);
  }, [def.nivel]);
  function exportarCsv() {
    if (!resposta) return;
    baixar("analise_" + (resposta.competencia || "grafico") + ".csv", montarCsv(resposta, { familia: familiaDesenho, indicador, rotulos }), "text/csv;charset=utf-8");
  }
  function exportarMetodo() {
    if (!resposta) return;
    baixar("metodo_" + (resposta.competencia || "grafico") + ".txt", textoDoMetodo(resposta, titulo, calculado?.opcoes ?? null, resumoNaTela),
      "text/plain;charset=utf-8");
  }
  /** A divisória entre o desenho e a explicação da tendência: arrastar (ou as setas, com o foco nela) muda a largura do painel da
   * explicação, entre LATERAL_MIN e a metade da área (no máximo LATERAL_MAX). */
  const limitarLateral = (valor: number) => {
    const total = corpoRef.current?.clientWidth ?? 1200;
    return Math.round(Math.min(Math.max(valor, LATERAL_MIN), Math.max(LATERAL_MIN, Math.min(LATERAL_MAX, total / 2))));
  };
  function arrastarDivisoria(event: EventoPonteiro<HTMLDivElement>) {
    const corpo = corpoRef.current, alvo = event.currentTarget;
    if (!corpo) return;
    event.preventDefault();
    alvo.setPointerCapture?.(event.pointerId);
    const mover = (e: PointerEvent) => setLarguraLateral(limitarLateral(corpo.getBoundingClientRect().right - e.clientX));
    const soltar = () => { alvo.removeEventListener("pointermove", mover); alvo.removeEventListener("pointerup", soltar);
      alvo.removeEventListener("pointercancel", soltar); };
    alvo.addEventListener("pointermove", mover); alvo.addEventListener("pointerup", soltar); alvo.addEventListener("pointercancel", soltar);
  }
  function teclasDivisoria(event: KeyboardEvent<HTMLDivElement>) {
    const passo = event.shiftKey ? 80 : 24;
    if (event.key === "ArrowLeft") setLarguraLateral(atual => limitarLateral(atual + passo));
    else if (event.key === "ArrowRight") setLarguraLateral(atual => limitarLateral(atual - passo));
    else if (event.key === "Home") setLarguraLateral(limitarLateral(LATERAL_MIN));
    else if (event.key === "End") setLarguraLateral(limitarLateral(LATERAL_MAX));
    else return;
    event.preventDefault();
  }

  // ------------------------------------------------------------------------------------------ partes da tela
  const unidade = rotulos.unidade;
  const semUnidades = semSelecao(def);
  const estadoTela = !fonte ? "E0" : def.nivel === "estados" || semUnidades ? "E1"
    : painel ? "E4" : def.familia !== "distribuicao" ? "E3" : "E2";
  const totalDeUnidades = niveis?.municipios.total ?? municipios.filter(item => !item.selection_reason).length;
  const avisoFamilia = pronto ? avisoDaFamilia(def, dispAtual) : null;
  // Território de referência sem resultado (24/10/2026): nenhum dos territórios em análise ficou com referência (ninguém da base
  // atende à condição; ou os que atendem ficam fora da delimitação de cada um, só o próprio território atende ou falta a
  // coordenada de um território). A mensagem diz o que aconteceu, com a condição e as contagens do motor, e o que fazer; o motivo
  // de cada um, que só o motor sabe, fica em Não avaliáveis.
  const referenciaDaTela = referenciaPorItem && resposta?.referencia?.tipo === "elegiveis" ? resposta.referencia : null;
  const unidadesComReferencia = referenciaDaTela ? (resposta?.itens || []).filter(item => item.tipo === "municipio") : [];
  const fUnidade = generoDe(unidade) === "f", cadaUm = fUnidade ? "cada uma" : "cada um";
  const semReferencia = referenciaDaTela && unidadesComReferencia.length && unidadesComReferencia.every(item => !item.referenciaDoItem?.length)
    ? (referenciaDaTela.elegiveis?.atende === 0
      ? (fUnidade ? "Nenhuma " : "Nenhum ") + unidade.singular + " da base atende à condição " + (referenciaDaTela.condicao?.texto ?? "") +
        ": não há território de referência. Mude o atributo, o operador ou o valor de corte."
      : (fUnidade ? "Nenhuma d" : "Nenhum d") + artigo(unidade, true) + " " + unidade.plural + " em análise ficou com território de " +
        "referência nesta definição: quem atende à condição pode estar fora da delimitação de " + cadaUm + ", só " + artigo(unidade, false) +
        " própri" + (fUnidade ? "a " : "o ") + unidade.singular + " pode atender, ou falta a coordenada de um território. O motivo de " +
        cadaUm + " está em Não avaliáveis, nos Detalhes.")
    : null;
  // Fora do gráfico (25/10/2026): quem não tem o valor que o posiciona (o indicador; na análise espacial, a distância até o
  // território de referência; na rotatividade, a coorte) fica dito junto do desenho, pelo nome, com o caminho do motivo, e o mapa
  // mostra essas unidades no lugar delas. Sem nenhum território de referência, vale o aviso acima; na Série temporal (que desenha as
  // séries) e com só o mapa à vista, não se aplica.
  const foraDoGrafico = resposta && !semUnidades && !semReferencia && !series && vistaExibida !== "mapa"
    ? textoForaDoDesenho(fora, { rotulos, mapa: mapa.disponivel }) : null;
  const naVisaoDeGrupos = (resposta?.nivel ?? def.nivel) === "estados" && familiaDesenho === "distribuicao" && def.nivel === "estados";
  const funcaoDesabilitada = (chaveFuncao: FuncaoPainel): string | null => {
    if (!resposta) return "Disponível depois do primeiro gráfico.";
    if (familiaDesenho === "rotatividade" && ["regua", "condicoes", "ordenar", "comparar", "juntar"].includes(chaveFuncao))
      return "A rotatividade mostra barras da coorte inicial; esta função vale para as bolhas.";
    if (chaveFuncao === "juntar" && def.nivel === "estados") {
      const grupo = rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
      return "Na visão " + (generoDe(grupo) === "f" ? "das " : "dos ") + grupo.plural + ", Juntar fica desligado: " + unidade.plural + " e " +
        grupo.plural + " nunca se somam.";
    }
    // O Brasil como unidade (24/10/2026): um território só; o que separa, ordena, compara ou junta vários não se aplica.
    if (def.nivel === "brasil" && chaveFuncao !== "exportar")
      return "Com o Brasil como unidade, há um território só: esta função vale para vários.";
    if (chaveFuncao === "regua" && series) return "Na Série temporal, a régua não se aplica.";
    return null;
  };
  const especie = INDICADORES[indicador];
  const contextoBrasil: LinhaDeReferencia | null = indicador === "densidade" && resposta?.contextoBrasil?.densidade !== null && resposta?.contextoBrasil?.densidade !== undefined
    ? { valor: resposta.contextoBrasil.densidade, rotulo: "Brasil · " + formatarNumero(resposta.contextoBrasil.densidade) +
      (resposta.contextoBrasil.competencia && resposta.contextoBrasil.competencia !== resposta.competencia ? " (" + exibirCompetencia(resposta.contextoBrasil.competencia) + ")" : "") }
    : null;
  const cortes: LinhaDeReferencia[] = camadaFinal === "grupos" && resposta?.grupos ? resposta.grupos.cortes.map(valor => ({ valor, rotulo: textoDaMarca(valor) }))
    : camadaFinal === "faixas" ? defDesenho.agrupar.faixas.map(valor => ({ valor, rotulo: textoDaMarca(valor) })) : [];
  const faixasDistancia: LinhaDeReferencia[] = distanciaNaTela ? defDesenho.faixasDistancia.map(valor => ({ valor, rotulo: textoDaMarca(valor) + " km" })) : [];
  const referenciaDesenhada = defDesenho.referencia;
  const rotuloDistancia = referenciaPorItem ? "Distância até o território de referência (km)"
    : referenciaDesenhada && !referenciaElegivel(referenciaDesenhada) && referenciaDesenhada.membros.length > 1
      ? "Distância até o membro mais próximo da referência (km)" : "Distância até a referência (km)";
  /** Texto antes do nome no rótulo direto: a posição do motor na ordenação (até os 12 primeiros), no gráfico e no mapa. */
  const extraDoRotulo = camadaFinal === "ordem" ? (item: PainelItem) => item.ordem?.posicao !== null && item.ordem && (primeiros === null ||
    item.ordem.posicao <= primeiros) && (primeiros ?? 99) <= 12 ? item.ordem.posicao + "º" : null : undefined;

  /** Amostra do não avaliável: a bolha vazada, com o anel tracejado, nas cores do esquema em uso. */
  const amostraVazada = { background: paleta.vazia, border: "1.5px dashed " + paleta.naoAvaliavel };
  // Legenda da camada de cor: a do gráfico, com os seletores de teste; a cópia que vai ao mapa (a mesma legenda) sai sem eles, para
  // o lado a lado e o mapa montado e oculto não repetirem os data-testid do gráfico.
  const legendaDaCor = (comIds: boolean): ReactNode => {
    const id = (valor: string) => comIds ? valor : undefined;
    if (!resposta) return null;
    if (camadaFinal === "variacao") {
      return <div data-testid={id("analise-legenda-cor")} data-camada="variacao" className="max-w-xs">
        <div className="h-2.5 rounded-full" style={{ background: gradienteDaVariacao(paleta) }} aria-hidden="true"/>
        <div className="relative mt-1 h-4 text-[11px] tabular-nums text-slate-600" aria-hidden="true">
          {([[0, -limiteVariacao], [50, 0], [100, limiteVariacao]] as const).map(([posicao, valor]) =>
            <span key={posicao} className="absolute whitespace-nowrap" style={{ left: posicao + "%", transform: posicao === 0 ? "none" : posicao === 100 ? "translateX(-100%)" : "translateX(-50%)" }}>
              {valor === 0 ? "0,00%" : formatarVariacao(valor)}</span>)}
        </div>
        <p className="mt-1 leading-4">Cor: variação da {especie.rotulo.toLowerCase()} entre {exibirCompetencia(resposta.competencia_inicial)} e{" "}
          {exibirCompetencia(resposta.competencia)}: azul é aumento; laranja, redução; cinza, sem mudança. Contínua, sem classes.</p>
      </div>;
    }
    const itensLegenda: { chave: string; cor: string | null; texto: string; contagem: number | null; vazada?: boolean }[] = [];
    if (camadaFinal === "classes") {
      (["CRESCIMENTO", "DECLINIO", "NENHUMA"] as const).forEach(familia => itensLegenda.push({ chave: familia, cor: paleta.tendencia[familia],
        texto: NOMES_FAMILIA_TENDENCIA[familia], contagem: resposta.tendencia?.familias[familia] ?? null }));
      itensLegenda.push({ chave: "NAO_AVALIAVEL", cor: null, vazada: true, texto: "Não avaliável", contagem: resposta.tendencia?.naoAvaliaveis ?? resposta.tendencia?.contagens.NAO_AVALIAVEL ?? null });
    } else if (camadaFinal === "grupos" && resposta.grupos) {
      for (let i = 1; i <= totalGrupos; i++) itensLegenda.push({ chave: String(i), cor: corOrdinal(i, totalGrupos, paleta),
        texto: resposta.grupos.rotulos[i - 1] || i + "º grupo", contagem: resposta.grupos.contagens[i - 1] ?? null });
    } else if (camadaFinal === "faixas" && resposta.faixas) {
      resposta.faixas.rotulos.forEach((rotulo, i) => itensLegenda.push({ chave: String(i + 1), cor: corOrdinal(i + 1, totalFaixas, paleta), texto: rotulo,
        contagem: resposta.faixas!.contagens[i] ?? null }));
      if (resposta.faixas.fora !== null) itensLegenda.push({ chave: "fora", cor: paleta.neutra, texto: "Fora das faixas", contagem: resposta.faixas.fora });
    } else if (camadaFinal === "condicoes" && resposta.condicoes) {
      itensLegenda.push({ chave: "ATENDE", cor: paleta.bolha, texto: "Atendem a todas as condições", contagem: resposta.condicoes.contagens.ATENDE ?? null },
        { chave: "NAO_ATENDE", cor: paleta.neutra, texto: "Não atendem", contagem: resposta.condicoes.contagens.NAO_ATENDE ?? null },
        { chave: "NAO_AVALIAVEL", cor: null, vazada: true, texto: "Sem dado para avaliar", contagem: resposta.condicoes.contagens.NAO_AVALIAVEL ?? null });
    } else if (camadaFinal === "ordem" && resposta.ordenacao) {
      itensLegenda.push({ chave: "primeiros", cor: paleta.bolha, texto: primeiros !== null ? "Os " + primeiros + " primeiros (posições da ordenação" +
        (resposta.ordenacao.empatesNoCorte ? ", com os empatados no corte)" : ")") : "Com posição na ordenação", contagem: null },
        { chave: "demais", cor: paleta.neutra, texto: "Demais", contagem: null });
    }
    if (!itensLegenda.length) return null;
    return <ul data-testid={id("analise-legenda-cor")} data-camada={camadaFinal} className="flex flex-col gap-1" aria-label="Legenda das cores">
      {itensLegenda.map(item => <li key={item.chave} data-testid={id("analise-legenda-cor-item")} data-chave={item.chave} data-contagem={item.contagem ?? ""}
        className="flex items-center gap-1.5">
        <span className="analise-amostra-bolha" style={item.vazada ? amostraVazada : { background: item.cor ?? paleta.bolha }} aria-hidden="true"/>
        <span>{item.texto}{item.contagem !== null ? <> · <strong className="tabular-nums text-ink">{formatarNumero(item.contagem, true)}</strong></> : ""}</span>
      </li>)}
      {camadaFinal === "grupos" && totalGrupos > 5 && <li className="leading-4">Nos decis, só as linhas de corte: mais de cinco tons não se distinguem.</li>}
    </ul>;
  };
  const legendaCor = legendaDaCor(true);
  const legendaDoMapa = legendaDaCor(false);

  const notasDoGrafico = [
    // As bolhas de grupo só existem na base do Brasil (os estados, da fonte estadual de profissionais únicos).
    ...(resposta?.nivel === "estados" ? [maiuscula("cada " + (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular) + " conta os profissionais únicos da " +
      "fonte estadual: quem atua em mais de " + umA(unidade) + " conta uma vez. A bolha não é a soma das bolhas d" + artigo(unidade, true) + " " +
      unidade.plural + ", e os dois níveis nunca aparecem juntos."] : []),
  ];
  const notaClasses = notaSemClassificacao(resposta?.tendencia ?? null, { rotulos, brasil: tipo === "brasil" });
  // Com um território só (24/10/2026), as contagens por classe saem: o resultado dele e o que a classe quer dizer ficam na frase
  // do resultado. Com vários, só as classes que têm territórios.
  const naoAvaliaveis = resposta?.tendencia ? resposta.tendencia.naoAvaliaveis ?? resposta.tendencia.contagens.NAO_AVALIAVEL ?? null : null;
  const filtrarClasse = (classe: string) => {
    registrar(filtroClasse === classe ? "Tirar o filtro da classe" : "Filtrar a classe");
    setFiltroClasse(atual => atual === classe ? null : classe);
  };
  const contagemClasses = exibicao.tendencia && resposta?.tendencia && (resposta.itens.length > 1 || !!filtroClasse) ? <div data-testid="analise-contagem-classes"
    className="analise-contagem-classes" role="group" aria-label="Contagem por classe de tendência (clique para filtrar)">
    {CLASSES_TENDENCIA.map(classe => {
      const n = resposta.tendencia!.contagens[classe.codigo] ?? 0;
      // A classe do filtro em uso continua à vista, mesmo sem territórios, para o filtro poder ser desligado.
      if (!n && filtroClasse !== classe.codigo) return null;
      return <button key={classe.codigo} type="button" data-testid="analise-contagem-classe" data-classe={classe.codigo} data-contagem={n}
        aria-pressed={filtroClasse === classe.codigo} title={DESCRICAO_DAS_CLASSES[classe.codigo]} className="analise-contagem"
        onClick={() => filtrarClasse(classe.codigo)}>
        <span className="analise-amostra-bolha" style={{ background: paleta.tendencia[classe.familia] }} aria-hidden="true"/>
        {classe.rotulo} <strong className="tabular-nums text-ink">{formatarNumero(n, true)}</strong></button>;
    })}
    {(!!naoAvaliaveis || filtroClasse === "NAO_AVALIAVEL") && <button type="button" data-testid="analise-contagem-classe" data-classe="NAO_AVALIAVEL" data-contagem={naoAvaliaveis ?? 0}
      aria-pressed={filtroClasse === "NAO_AVALIAVEL"} className="analise-contagem" onClick={() => filtrarClasse("NAO_AVALIAVEL")}>
      <span className="analise-amostra-bolha" style={amostraVazada} aria-hidden="true"/>
      Não avaliável <strong className="tabular-nums text-ink">{formatarNumero(naoAvaliaveis ?? 0, true)}</strong></button>}
    {resposta.tendencia.bloqueio && <p className="w-full text-xs text-amber-900">{resposta.tendencia.bloqueio}</p>}
    {notaClasses && <p data-testid="analise-nota-sem-classificacao" className="analise-nota-classes">{notaClasses}</p>}
  </div> : null;

  // Série temporal (24/10/2026): com até 12 itens, todos aparecem; com mais, os marcados (no quadro, nas bolhas ou na tabela).
  const itensSeries = useMemo(() => {
    if (!series || !resposta) return [];
    const comSerie = resposta.itens.filter(item => !!item.serie);
    if (selecao.length) {
      const porId = new Map(comSerie.map(item => [item.id, item]));
      return selecao.map(id => porId.get(id)).filter((item): item is PainelItem => !!item);
    }
    return comSerie.length <= MAX_SERIES ? comSerie : [];
  }, [series, resposta, selecao]);

  // Mapa (MapaProps do contrato): todas as unidades em análise, sem os estados, também as que o gráfico deixa de fora por falta do
  // valor que as posiciona (25/10/2026: sem território de referência, sem o indicador ou sem a coorte, cada uma no lugar dela, com a
  // pintura da camada ou vazada); a régua e os filtros esmaecem (decisão de 23/10).
  const itensDoMapa = useMemo(() => resposta ? itensParaOMapa(resposta.itens) : [], [resposta]);
  const dentroDoMapa = useMemo(() => new Set(itensDoMapa.filter(item => dentroDosFiltros(item, filtrosVisuais)).map(item => item.id)),
    [itensDoMapa, filtrosVisuais]);
  const corDoMapa = useMemo(() => corContinuaDoMapa({ rotatividade: rotatividadeNaTela, indicador, dominios: resposta?.dominios ?? {} }),
    [rotatividadeNaTela, indicador, resposta]);
  const tamanhoNoMapa = useMemo(() => tamanhoDoMapa({ rotatividade: rotatividadeNaTela, indicador, dominios: resposta?.dominios ?? {} }),
    [rotatividadeNaTela, indicador, resposta]);
  const pinturaMapa = pinturaDoMapa({ camada: camadaFinal, rotatividade: rotatividadeNaTela, gruposDoMapa: !!resposta?.gruposMapa });
  // Os quintis do mapa (grupos_mapa, do motor): a cor de cada ponto pelo grupo dele e a legenda com os rótulos e as contagens.
  const totalGruposMapa = resposta?.gruposMapa ? ({ quartis: 4, quintis: 5, decis: 10 } as Record<string, number>)[resposta.gruposMapa.tipo] ??
    resposta.gruposMapa.contagens.length : 0;
  const pinturaNoMapa = useMemo(() => {
    if (pinturaMapa !== "quintis") return pintura;
    return (item: PainelItem) => item.grupoMapa ? { cor: corOrdinal(item.grupoMapa.indice, totalGruposMapa, paleta) ?? paleta.bolha, vazada: false, apagada: false }
      : { cor: paleta.vazia, vazada: true, apagada: false };
  }, [pinturaMapa, pintura, totalGruposMapa, paleta]);
  const legendaDosQuintis = pinturaMapa === "quintis" && resposta?.gruposMapa ? <ul className="flex flex-col gap-1" aria-label="Legenda dos quintis do mapa">
    {Array.from({ length: totalGruposMapa }, (_, i) => {
      const contagem = resposta.gruposMapa!.contagens[i];
      return <li key={i} data-testid="mapa-quintil" data-chave={i + 1} data-contagem={contagem ?? ""} className="flex items-center gap-1.5">
        <span className="analise-amostra-bolha" style={{ background: corOrdinal(i + 1, totalGruposMapa, paleta) ?? paleta.bolha }} aria-hidden="true"/>
        <span>{resposta.gruposMapa!.rotulos[i] || (i + 1) + "º grupo"}{contagem !== undefined
          ? <> · <strong className="tabular-nums text-ink">{formatarNumero(contagem, true)}</strong></> : ""}</span>
      </li>;
    })}
  </ul> : null;
  // As ligações do mapa, até MAX_LIGACOES: primeiro as dos territórios base escolhidos um a um, depois as das unidades marcadas e,
  // com todos os selecionados como base, as dos demais, na ordem dos nomes. As bases escolhidas ganham o anel, como as marcadas.
  const ligacoes = useMemo(() => distanciaNaTela && resposta ? ligacoesDoMapa(resposta.itens,
    [...new Set([...(todasAsBases ? [] : idsDasBases), ...selecao, ...(todasAsBases ? idsDasBases : [])])]) : [],
  [distanciaNaTela, resposta, selecao, idsDasBases, todasAsBases]);
  const selecaoDoMapa = useMemo(() => todasAsBases || !pares.length ? selecao : [...new Set([...selecao, ...pares.map(par => par.base.id)])],
    [todasAsBases, pares, selecao]);
  const nomesDasReferencias = useMemo(() => new Map((resposta?.referencia?.membros ?? []).map(membro => [membro.id, membro.rotulo] as [string, string])),
    [resposta]);
  // A mira do mapa: os membros da referência; por elegibilidade, os territórios de referência (todos, até MAX_LIGACOES; com mais,
  // os dos itens marcados, os mesmos das ligações).
  const referenciasDoMapa = useMemo(() => {
    if (!distanciaNaTela) return [];
    const membros = (resposta?.referencia?.membros ?? []).map(membro => membro.id).filter(Boolean);
    if (!referenciaPorItem || membros.length <= MAX_LIGACOES) return membros;
    return [...new Set(ligacoes.flatMap(ligacao => ligacao.para))];
  }, [distanciaNaTela, referenciaPorItem, resposta, ligacoes]);
  const dicaDe = useCallback((item: PainelItem) => montarDica(item, { indicador, competencia: resposta?.competencia ?? "",
    competenciaInicial: resposta?.competencia_inicial || null, distancia: distanciaNaTela, variacao: dicaComVariacao && !!resposta?.competencia_inicial,
    tendencia: !!item.tendencia, nomes, limiares, rotulos, unidadesDoGrupo, relacao: relacaoNaTela, trajetoria: cometa }),
  [indicador, resposta, distanciaNaTela, dicaComVariacao, nomes, limiares, rotulos, unidadesDoGrupo, relacaoNaTela, cometa]);
  // A escala muda só o desenho ("como ver"): fica na barra junto da vista, só quando se aplica (no gráfico, fora da rotatividade
  // e da Série temporal). Linear por padrão; a logarítmica só por escolha e com valores positivos. O mapa não tem escala própria:
  // a cor contínua da rotatividade vai de 0 a 100%.
  const escalaNoGrafico = (vistaExibida === "grafico" || lado) && !rotatividadeNaTela && !series && !quadroDeSetas;
  const logPossivel = !!dominio && dominio[0] > 0;
  const propsDoMapa: MapaProps | null = resposta && dadosAtuais ? {
    itens: itensDoMapa, dentro: dentroDoMapa, dados: dadosAtuais, indicador, pintura: pinturaMapa, pintar: pinturaNoMapa,
    valorContinuo: corDoMapa.valor, rotuloContinuo: corDoMapa.rotulo, dominio: corDoMapa.dominio, escala: "linear",
    tamanho: tamanhoNoMapa, contextoBrasil: rotatividadeNaTela ? null : contextoBrasil,
    legendaCor: pinturaMapa === "quintis" ? legendaDosQuintis : legendaDoMapa, selecionados: selecaoDoMapa, referencias: referenciasDoMapa, ligacoes,
    nomesDasReferencias, comTerritoriosBase: pares.length > 0, extraDoRotulo, dicaDe, rotulos,
    brasil: tipo === "brasil", referenciaPorItem,
    ativoExterno: lado ? ativoCruzado : null, onAtivo: lado ? setAtivoCruzado : undefined, onAlternar: alternar,
    carregando: carregando || carregandoMapa || !dadosConferem,
  } : null;
  const convite = !!resposta && vistaExibida === "grafico" && mapa.disponivel && (exibicao.condicoes || distanciaNaTela);
  const montarMapa = mapa.disponivel && (mapaNaTela || mapaMontado);

  /** As duas entradas dos dados (24/10/2026), as mesmas da conversa: "Usar dados do Brasil" e "Enviar meus dados", que abre a
   * janela de envio (com o modelo de planilha). Na abertura (E0), com a identificação do sistema no alto e ao centro; no "Trocar"
   * da fonte, com o cancelamento, e a análise atual continua à vista até a nova fonte ficar pronta. */
  const botoesDasFontes = (grande: boolean) => <>
    <button type="button" data-testid="analise-fonte-brasil" className={"analise-botao-primario" + (grande ? " analise-botao-grande" : "")}
      onClick={() => props.onEscolherFonte("brasil")}><Database size={grande ? 18 : 16} aria-hidden="true"/>Usar dados do Brasil</button>
    <button type="button" data-testid="analise-fonte-arquivo" className={"analise-botao-secundario" + (grande ? " analise-botao-grande" : "")}
      onClick={() => props.onEscolherFonte("arquivo")}><Upload size={grande ? 18 : 16} aria-hidden="true"/>Enviar meus dados</button>
  </>;
  const abertura = <div data-testid="analise-abertura" className="analise-abertura analise-abertura-inicial">
    <h2 id="analise-titulo" data-testid="analise-titulo" className="analise-abertura-sistema">{TITULO_DO_SISTEMA}</h2>
    <p data-testid="analise-abertura-chamada" className="analise-abertura-chamada">{TEXTO_ESCOLHA_DOS_DADOS}</p>
    <p className="analise-abertura-texto">{TEXTO_DAS_FONTES}</p>
    <div className="analise-abertura-botoes">{botoesDasFontes(true)}</div>
  </div>;
  const trocaDaFonte = <div data-testid="analise-troca-fonte" className="analise-abertura analise-abertura-troca analise-nao-imprimir">
    <p className="analise-abertura-titulo">Trocar os dados</p>
    <p className="analise-abertura-texto">Escolha a nova fonte. A análise atual continua à vista até a nova fonte ficar pronta.</p>
    <div className="flex flex-wrap justify-center gap-2">
      {botoesDasFontes(false)}
      {props.onCancelarTroca && <button type="button" data-testid="analise-troca-cancelar" className="analise-botao-secundario"
        onClick={props.onCancelarTroca}><X size={15} aria-hidden="true"/>Cancelar</button>}
    </div>
  </div>;

  // Antes do desenho: a abertura (E0), o preparo, a base carregada sem seleção e o primeiro pedido. Valem para as duas vistas.
  const antesDoDesenho = (() => {
    if (semUnidades) return <div data-testid="analise-vazio" className="analise-vazio">
      <p className="font-semibold text-ink">{tipo === "brasil" ? "Os dados do Brasil foram carregados e estão prontos para a análise."
        : "A planilha foi carregada e está pronta para a análise."}</p>
      <p className="max-w-lg text-sm leading-6 text-slate-600">{TEXTO_SEM_SELECAO} Os resultados aparecem aqui assim que você escolher; nada é
        calculado antes disso.</p>
      {aba !== "territorios" && <button type="button" data-testid="analise-ir-selecao" className="analise-botao-secundario" onClick={irParaTerritorios}>
        <MapaIcone size={15} aria-hidden="true"/>Abrir a Seleção de Territórios</button>}
    </div>;
    if (!resposta) return <p role="status" data-testid="analise-carregando" className="analise-vazio">{!erro && <><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>
      Calculando os valores…</>}</p>;
    return null;
  })();

  // A análise de tendência na tela (24/10/2026): o desenho logo abaixo dos ajustes e, à direita, o painel da explicação.
  const layoutTendencia = familiaDesenho === "tendencia" && !!resposta && !semUnidades;
  const desenhoDoGrafico = (() => {
    if (!resposta) return null;
    if (familiaDesenho === "rotatividade" && calculado?.def.rotatividade) return <PainelRotatividade itens={visiveis} rotulos={rotulos}
      inicial={calculado.def.rotatividade.inicial} final={calculado.def.rotatividade.final}/>;
    if (series) return itensSeries.length ? <PainelSeries itens={itensSeries} competencias={resposta.serie?.competencias ?? []}
      indicador={indicador} rotulos={rotulos}/>
      : <div data-testid="analise-series-vazio" className="analise-vazio">
        <p className="font-semibold text-ink">Escolha até {MAX_SERIES} {unidade.plural} para ver a série temporal.</p>
        <p className="text-xs text-slate-600">Marque na tabela (Detalhes) ou, na visão Tendência, clique nas linhas do quadro de setas.</p>
      </div>;
    if (quadroDeSetas) return <PainelSetas itens={visiveis} janela={resposta.tendencia?.janela.length ? resposta.tendencia.janela : defDesenho.janela}
      indicador={indicador} rotulos={rotulos} selecionados={selecao} pelaPosicao={camadaFinal === "ordem"} condicoes={camadaFinal === "condicoes"}
      legenda={layoutTendencia ? undefined : legendaCor} onAlternar={alternar} ativoExterno={lado ? ativoCruzado : null} onAtivo={lado ? setAtivoCruzado : undefined}/>;
    // Com o mapa disponível, a dica da bolha mostra o mapinha ("onde fica?"); no lado a lado, o destaque é cruzado com o mapa.
    return <PainelChart resposta={resposta} itens={visiveis} todos={plotaveis} indicador={indicador} escala={escala} distancia={distanciaNaTela}
      cometa={cometa} trajetoria={cometa} relacao={relacaoNaTela} pares={paresLigados} basesEscolhidas={!todasAsBases} destaque={destaque} vista={vista} fase={fase} pintura={pintura} selecionados={selecao} limiares={limiares}
      nomes={nomes} carregando={carregando}
      rotuloDistancia={rotuloDistancia} rotulos={rotulos} contextoBrasil={contextoBrasil} cortes={cortes} corte={corteAtivo(corte, dominio) ? corte : null}
      faixasDistancia={faixasDistancia} unidadesDoGrupo={unidadesDoGrupo} legendaCor={layoutTendencia ? null : legendaCor} notas={notasDoGrafico}
      extraDoRotulo={extraDoRotulo}
      rotuloSempre={item => item.tipo === "estado" || (camadaFinal === "ordem" && primeiros !== null && primeiros <= 12 && item.ordem?.posicao !== null &&
        item.ordem !== null && (item.ordem.posicao as number) <= primeiros)}
      onAlternar={alternar} onAbrirGrupo={abrirGrupoDaBolha}
      pontosDoMapa={mapa.disponivel && dadosConferem ? dadosAtuais?.pontos ?? null : null}
      ativoExterno={lado ? ativoCruzado : null} onAtivo={lado ? setAtivoCruzado : undefined}/>;
  })();

  const desenhoDoMapa = (() => {
    if (!montarMapa || !resposta) return null;
    const falha = erroDoMapa && <div role="alert" data-testid="analise-mapa-erro" className="analise-erro">
      <p>Não foi possível obter os pontos do mapa: {erroDoMapa.mensagem}</p>
      {erroDoMapa.pendencia && <div data-testid="analise-mapa-pendencia" className="mt-2 space-y-1.5">
        <p className="font-semibold">{erroDoMapa.pendencia.texto || "Antes de desenhar o mapa, é preciso uma escolha."}</p>
        <div className="flex flex-wrap gap-1.5">{erroDoMapa.pendencia.opcoes.map(opcao => <button key={opcao.valor} type="button"
          data-testid="analise-mapa-pendencia-opcao" data-valor={opcao.valor} className="analise-botao-secundario"
          onClick={() => escolherPendencia(erroDoMapa.pendencia!.chave, opcao.valor)}>{opcao.rotulo}</button>)}</div>
      </div>}
      <div className="mt-2 flex flex-wrap gap-3">
        {!lado && <button type="button" data-testid="analise-mapa-voltar" onClick={() => trocarVista("grafico")} className="font-semibold underline">
          Voltar ao gráfico</button>}
        <button type="button" data-testid="analise-mapa-tentar" onClick={() => setTentativaMapa(valor => valor + 1)}
          className="inline-flex items-center gap-1 font-semibold underline"><RefreshCw size={13} aria-hidden="true"/>Tentar novamente</button>
      </div>
    </div>;
    if (propsDoMapa) return <>{falha}<MapaAnalise ref={mapaRef} {...propsDoMapa}/></>;
    if (falha) return falha;
    return <p role="status" data-testid="analise-mapa-carregando" className="analise-vazio"><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>
      Buscando os pontos do mapa…</p>;
  })();

  const conteudoPainel = (() => {
    if (!painel || !fonteMotor) return null;
    switch (painel) {
      case "regua": return resposta ? <PainelRuler indicador={indicador} dominio={dominio} escala={escala} corte={corte}
        onCorte={novo => { registrar("Ajustar a régua", "continuo:regua"); setCorte(novo); }}
        plural={naVisaoDeGrupos ? rotulos.grupo?.plural ?? "grupos" : unidade.plural}/> : null;
      case "referencia": return <GavetaReferencia pedida={def.referencia} ativa={distanciaNaTela ? resposta?.referencia ?? null : null} nomes={nomes}
        rotulos={rotulos} brasil={tipo === "brasil"} grupos={grupos} temPopulacao={temPopulacao} faixas={def.faixasDistancia}
        criterioInicial={criterioDoChat} onAplicar={aplicarReferencia} bases={basesDaReferencia} territoriosBase={def.territoriosBase ?? null} onBases={escolherBases}
        onRemover={() => { ajustar("Remover a referência", { referencia: null, faixasDistancia: [] }); setAviso("Referência removida: volta o eixo único."); }}
        onFaixas={limites => ajustar("Aplicar as faixas de distância", { faixasDistancia: limites })}/>;
      case "condicoes": return <GavetaCondicoes condicoes={def.condicoes} espacial={distanciaNaTela} resposta={resposta} rotulos={rotulos}
        soAtende={soAtende} onSoAtende={valor => { registrar(valor ? "Mostrar só quem atende" : "Mostrar todos"); setSoAtende(valor); }}
        onAplicar={condicoes => ajustar(condicoes.length ? "Aplicar as condições" : "Limpar as condições", { condicoes })}/>;
      case "ordenar": return <GavetaOrdenar ordenar={def.ordenar} espacial={distanciaNaTela} mudanca={exibicao.variacao} resposta={resposta}
        indicador={indicador} onAplicar={ordenar => ajustar(ordenar ? "Ordenar" : "Limpar a ordenação", { ordenar })}/>;
      case "comparar": return <GavetaComparar itens={resposta?.itens || []} selecionados={selecao} pedidos={def.comparar} resposta={resposta}
        nomes={nomes} rotulos={rotulos} onAlternar={alternar}
        onLimpar={() => { registrar("Limpar a escolha da comparação"); setSelecionados([]); mudar({ comparar: [] }); }}
        onComparar={ids => ajustar("Comparar", { comparar: ids })}/>;
      case "juntar": return <GavetaJuntar itens={resposta?.itens || []} selecionados={selecao} conjuntos={def.conjuntos} rotulos={rotulos}
        nivelGrupos={def.nivel === "estados"} onJuntar={juntar} onDesfazer={desfazerConjunto} onAlternar={alternar}/>;
      case "exportar": return <GavetaExportar pronto={!!resposta} onCsv={exportarCsv} onImprimir={() => window.print()} onMetodo={exportarMetodo}/>;
      default: return null;
    }
  })();

  // Ajustes da análise escolhida, no painel colado na aba (23/10/2026): só o que vale para ela (painelModel.ajustesDaAnalise).
  const ajustes = pronto ? ajustesDaAnalise({ familia: def.familia, nivel: def.nivel, disponivel: dispAtual.disponivel, categorias: categorias.length,
    visao: def.visao }) : [];
  const ordenadas = useMemo(() => cronologica(periodos), [periodos]);
  const ajuste = (qual: Ajuste): ReactNode => {
    switch (qual) {
      case "indicador": return <div key={qual} data-ajuste={qual} className="analise-rotulo-campo">
        <span aria-hidden="true">Indicador</span>
        <div role="radiogroup" aria-label="Indicador" className="analise-segmentos mt-1">
          {(["densidade", "quantidade"] as const).map(valor => {
            // Planilha sem população: a densidade fica desligada, com o motivo à vista e no title.
            const desligado = valor === "densidade" && !temPopulacao;
            return <button key={valor} type="button" role="radio" aria-checked={def.indicador === valor} data-testid={"analise-indicador-" + valor}
              disabled={desligado} title={desligado ? TEXTO_SEM_POPULACAO : undefined} aria-describedby={desligado ? "analise-indicador-motivo" : undefined}
              onClick={() => { if (def.indicador === valor) return; ajustar("Trocar o indicador para " + INDICADORES[valor].rotulo, { indicador: valor }); setCorte(null); }}>
              {INDICADORES[valor].rotulo}</button>;
          })}
        </div>
        {!temPopulacao && <span id="analise-indicador-motivo" data-testid="analise-indicador-motivo" className="analise-ajuste-nota">{TEXTO_SEM_POPULACAO}</span>}
      </div>;
      case "categoria": return <label key={qual} data-ajuste={qual} className="analise-rotulo-campo">Categoria
        <select data-testid="analise-categoria" value={def.categoria} onChange={event => ajustar("Trocar a categoria", { categoria: event.target.value })}
          className="analise-campo">
          {categorias.map(valor => <option key={valor} value={valor}>{valor}</option>)}
        </select>
      </label>;
      case "competencia": return <label key={qual} data-ajuste={qual} className="analise-rotulo-campo">Competência
        <select data-testid="analise-competencia" value={def.competencia} onChange={event => mudarCompetencia(event.target.value)} className="analise-campo">
          {[...ordenadas].reverse().map(periodo => <option key={periodo} value={periodo}>{exibirCompetencia(periodo)}</option>)}
        </select>
      </label>;
      case "agrupar": return <div key={qual} data-ajuste={qual} className="flex flex-wrap items-end gap-1.5">
        <label className="analise-rotulo-campo">Grupos e faixas
          <select data-testid="analise-agrupar" value={def.agrupar.tipo} className="analise-campo"
            onChange={event => ajustar("Trocar os grupos e faixas", { agrupar: { tipo: event.target.value as DefinicaoAnalise["agrupar"]["tipo"], faixas: def.agrupar.faixas } })}>
            <option value="nenhum">Nenhum</option><option value="quartis">Quartis</option><option value="quintis">Quintis</option>
            <option value="decis">Decis (só as linhas de corte)</option><option value="faixas">Faixas digitadas</option>
          </select>
        </label>
        {def.agrupar.tipo === "faixas" && <div className="flex items-end gap-1.5">
          <label className="analise-rotulo-campo">Limites ({especie.contagem ? "profissionais" : "por 1.000 hab."})
            <input ref={faixasRef} data-testid="analise-faixas" value={faixasTexto || escreverLimites(def.agrupar.faixas)} placeholder="0; 1; 2; 5" inputMode="decimal"
              onChange={event => setFaixasTexto(event.target.value)} className="analise-campo w-36"/>
          </label>
          <button type="button" data-testid="analise-faixas-aplicar" className="analise-botao-secundario" disabled={lerLimites(faixasTexto).length < 2}
            onClick={() => { ajustar("Aplicar as faixas", { agrupar: { tipo: "faixas", faixas: lerLimites(faixasTexto) } }); setFaixasTexto(""); }}>Aplicar faixas</button>
        </div>}
      </div>;
      case "referencia": {
        // O território de referência (24/10/2026): o que está em uso, em palavras, e o botão que abre o fluxo.
        const pedida = def.referencia;
        const resumoRef = !pedida ? "nenhum ainda" : referenciaElegivel(pedida)
          ? NOMES_RELACOES[pedida.relacao] + " · " + (resposta?.referencia?.tipo === "elegiveis" && resposta.referencia.delimitacao?.texto
            ? resposta.referencia.delimitacao.texto + " · " + (resposta.referencia.condicao?.texto ?? "") : "definido")
          : resposta?.referencia?.membros.map(m => m.rotulo).join(", ") || pedida.membros.map(id => nomes.get(id) || id).join(", ");
        const resumoBase = distanciaNaTela && basesDaReferencia.length ? resumoDosTerritoriosBase(idsDasBases, todasAsBases,
          id => basesDaReferencia.find(base => base.id === id)?.rotulo ?? id) : "";
        return <div key={qual} data-ajuste={qual} className="flex flex-wrap items-end gap-1.5">
          <span className="analise-rotulo-campo">Território de referência
            <span data-testid="analise-referencia-resumo" className="analise-resumo">{resumoRef}{resumoBase}</span>
          </span>
          <button type="button" data-testid="analise-referencia-escolher" className="analise-botao-secundario" onClick={() => abrirPainel("referencia")}>
            {pedida ? "Mudar" : "Definir o território de referência"}</button>
        </div>;
      }
      case "janela": {
        // Campo Período (24/10/2026): o ritmo, e a janela são os últimos 4 períodos dele. Abre no anual (janelaPadrao, segunda
        // rodada de 24/10/2026); o ritmo que a base não tem fica desligado, com o motivo. Orienta a Tendência e a Trajetória.
        const ritmos = ritmosDaBase(periodos);
        const ritmoAtual = ritmoDaJanela(def.janela, periodos);
        const plural = RITMOS_TENDENCIA.find(item => item.ritmo === ritmoAtual)?.plural;
        const texto = plural ? "Últimos 4 períodos " + plural + ": " + listaDeCompetencias(def.janela) + "."
          : "Escolha anual ou semestral: a análise usa os últimos 4 períodos.";
        return <div key={qual} data-ajuste={qual} className="analise-rotulo-campo">
          <span aria-hidden="true">Período</span>
          <div role="radiogroup" aria-label="Período da tendência" aria-describedby="analise-periodo-texto" className="analise-segmentos mt-1">
            {ritmos.map(item => <button key={item.ritmo} type="button" role="radio" aria-checked={ritmoAtual === item.ritmo}
              data-testid={"analise-periodo-" + item.ritmo} disabled={!item.janela.length} title={item.motivo ?? listaDeCompetencias(item.janela)}
              onClick={() => { if (ritmoAtual === item.ritmo) return; ajustar("Trocar o período para " + item.rotulo.toLowerCase(), { janela: item.janela, familia: "tendencia" });
                setFiltroClasse(null); }}>{item.rotulo}</button>)}
          </div>
          <span id="analise-periodo-texto" data-testid="analise-periodo-texto" className="analise-ajuste-apoio">{texto}</span>
          {ritmos.filter(item => item.motivo).map(item => <span key={item.ritmo} data-testid={"analise-periodo-motivo-" + item.ritmo}
            className="analise-ajuste-nota">{item.rotulo}: {item.motivo}</span>)}
        </div>;
      }
      case "serie": {
        // Série temporal (24/10/2026): o intervalo, de toda a série da base (do primeiro ao último período que ela tem) ou entre as
        // competências escolhidas.
        const intervalo = intervaloDaSerie(def, periodos);
        const inicio = intervalo[0] ?? "", fim = intervalo[intervalo.length - 1] ?? "";
        const toda = !def.serie?.length;
        const escolher = (de: string, ate: string) => {
          const novo = intervaloEntre(periodos, de, ate);
          ajustar("Trocar o intervalo da série temporal", { serie: novo });
        };
        return <div key={qual} data-ajuste={qual} data-testid="analise-serie-intervalo" className="analise-rotulo-campo">
          <span aria-hidden="true">Intervalo da série</span>
          <div className="mt-1 flex flex-wrap items-end gap-1.5">
            <label className="analise-rotulo-campo">De
              <select data-testid="analise-serie-inicio" value={inicio} className="analise-campo" onChange={event => escolher(event.target.value, fim)}>
                {ordenadas.map(c => <option key={c} value={c} disabled={c > fim}>{exibirCompetencia(c)}</option>)}
              </select>
            </label>
            <label className="analise-rotulo-campo">Até
              <select data-testid="analise-serie-fim" value={fim} className="analise-campo" onChange={event => escolher(inicio, event.target.value)}>
                {ordenadas.map(c => <option key={c} value={c} disabled={c < inicio}>{exibirCompetencia(c)}</option>)}
              </select>
            </label>
            <button type="button" data-testid="analise-serie-toda" aria-pressed={toda} className="analise-botao-secundario" disabled={toda}
              onClick={() => ajustar("Ver toda a série", { serie: [] })}>Toda a série</button>
          </div>
          <span data-testid="analise-serie-texto" className="analise-ajuste-apoio">{toda ? "Toda a série da base: " : "Intervalo escolhido: "}
            {exibirCompetencia(inicio)} a {exibirCompetencia(fim)} ({intervalo.length} competências).</span>
        </div>;
      }
      case "visao": return <div key={qual} data-ajuste={qual} className="flex flex-wrap items-end gap-1.5">
        <div className="analise-rotulo-campo">
          <span aria-hidden="true">Visão</span>
          <div role="group" aria-label="Visão da tendência" className="analise-segmentos mt-1">
            {ORDEM_DAS_VISOES.map(visao => {
              const desligada = visao === "classes" && def.janela.length > 0 && def.janela.length < MINIMO_TENDENCIA;
              return <button key={visao} type="button" data-testid={"analise-visao-" + visao} aria-pressed={def.visao === visao} disabled={desligada}
                title={desligada ? "A tendência exige pelo menos " + MINIMO_TENDENCIA + " competências." : undefined}
                onClick={() => { if (def.visao === visao) return; ajustar("Trocar a visão para " + NOMES_VISOES[visao], { visao });
                  setFiltroClasse(null); }}>{NOMES_VISOES[visao]}</button>;
            })}
          </div>
        </div>
        {cometa && <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Competência mostrada">
          {(["inicial", "final"] as const).map(qualVista => <button key={qualVista} type="button" data-testid={"analise-vista-" + qualVista}
            aria-pressed={vista === qualVista} disabled={fase !== "parado"} className="analise-botao-secundario" onClick={() => setVista(qualVista)}>
            {qualVista === "inicial" ? "Primeira (" + exibirCompetencia(resposta?.competencia_inicial) + ")" : "Última (" + exibirCompetencia(resposta?.competencia) + ")"}</button>)}
          <button type="button" data-testid="analise-reproduzir" className="analise-botao-secundario" disabled={fase !== "parado"} onClick={reproduzir}>
            {fase !== "parado" ? <Pause size={14} aria-hidden="true"/> : <Play size={14} aria-hidden="true"/>}
            {movimentoReduzido || plotaveis.length > LIMITE_LEVE ? "Ir para a última" : "Reproduzir"}</button>
        </div>}
      </div>;
      case "periodos": {
        return <div key={qual} data-ajuste={qual} className="flex flex-wrap items-end gap-1.5">
          <label className="analise-rotulo-campo">Período inicial da coorte
            <select data-testid="analise-rot-inicial" value={def.rotatividade?.inicial ?? ""} className="analise-campo"
              onChange={event => ajustar("Trocar o período inicial da coorte", { rotatividade: { inicial: event.target.value, final: def.rotatividade?.final ?? "" } })}>
              <option value="">Escolha</option>{ordenadas.slice(0, -1).map(c => <option key={c} value={c}>{exibirCompetencia(c)}</option>)}
            </select>
          </label>
          <label className="analise-rotulo-campo">Período final
            <select data-testid="analise-rot-final" value={def.rotatividade?.final ?? ""} className="analise-campo"
              onChange={event => ajustar("Trocar o período final da coorte", { rotatividade: { inicial: def.rotatividade?.inicial ?? "", final: event.target.value } })}>
              <option value="">Escolha</option>{ordenadas.filter(c => !def.rotatividade?.inicial || c > def.rotatividade.inicial).map(c =>
                <option key={c} value={c}>{exibirCompetencia(c)}</option>)}
            </select>
          </label>
        </div>;
      }
      default: return null;
    }
  };

  const vistasNaBarra = VISTAS.filter(item => item.chave !== "lado" || largo);
  // A aba de uma análise que não pode ser executada com estes dados: a apresentação e o motivo, sem os ajustes.
  const dispDaAba = aba !== "territorios" ? disponivelDe(aba) : null;
  const motivoDaAba = fonte && dispDaAba && !dispDaAba.disponivel ? dispDaAba : null;
  const resumoDaSelecao = !fonte ? "Escolha os dados primeiro" : !pronto ? "Preparando os dados…"
    : semUnidades ? "Nenhum território selecionado"
    : resumoDoUniverso({ nivel: def.nivel, base: def.base, estados: def.estados, conjuntos: def.conjuntos.length, grupos, rotulos,
      total: totalDeUnidades, grupoDe, nomes: nomesDoCatalogo });
  // A Seleção de Territórios é só seleção (24/10/2026): o título, a frase-resumo, o desenho e os Detalhes ficam nas análises.
  const naSelecao = aba === "territorios";
  // O que a classe quer dizer, junto do resultado de um território só (o motor já disse qual é a classe na frase-resumo).
  const unicoComTendencia = tendenciaNaTela && resumoNaTela && resposta?.itens.length === 1 && resposta.itens[0].tendencia
    ? resposta.itens[0].tendencia : null;
  const significado = unicoComTendencia && resposta?.tendencia ? significadoDaClasse(unicoComTendencia) : null;
  // A unidade escolhida no quadro de setas: as velocidades dela ficam no painel da explicação.
  const itemDasVelocidades = quadroDeSetas && selecao.length ? resposta?.itens.find(item => item.id === selecao[selecao.length - 1] && item.tendencia) ?? null : null;

  const subtituloEResumo = <>
    <p data-testid="analise-subtitulo" className="analise-subtitulo">{subtitulo}</p>
    {/* Frase-resumo do motor: lida pelos leitores de tela a cada mudança; também na impressão e no arquivo de método. */}
    <p data-testid="analise-resumo" aria-live="polite" className="analise-frase-resumo">{resumoNaTela ?? ""}</p>
    {significado && <p data-testid="analise-resumo-significado" className="analise-frase-significado">{significado}</p>}
  </>;
  const painelDaFuncao = painel && conteudoPainel ? <aside id="analise-painel" data-testid="analise-painel" data-painel={painel}
    aria-labelledby="analise-painel-titulo" className="analise-painel analise-nao-imprimir"
    onKeyDown={event => { if (event.key === "Escape") { event.stopPropagation(); fecharPainel(); } }}>
    <div className="analise-painel-cabecalho">
      <h3 id="analise-painel-titulo" ref={tituloPainelRef} tabIndex={-1} className="text-sm font-bold text-ink outline-none">{TITULOS_PAINEL[painel]}</h3>
      <button type="button" data-testid="analise-painel-fechar" className="analise-icone" aria-label={"Fechar " + TITULOS_PAINEL[painel]} onClick={fecharPainel}>
        <X size={16} aria-hidden="true"/></button>
    </div>
    <div className="analise-painel-corpo">{conteudoPainel}</div>
  </aside> : null;
  const larguraMaxima = Math.max(LATERAL_MIN, Math.min(LATERAL_MAX, Math.round((corpoRef.current?.clientWidth ?? 1200) / 2)));

  return <section id="area-de-analise" data-testid="area-de-analise" data-estado={estadoTela} data-familia={def.familia} data-nivel={def.nivel}
    data-desenho={vistaExibida} data-aba={aba} aria-labelledby="analise-titulo" className="analise">
    {/* Desfazer e Limpar seleção (24/10/2026, segunda rodada): fixos no alto da área, lado a lado, em todas as abas, sem rolar. */}
    {pronto && <div data-testid="analise-controles-globais" role="toolbar" aria-label="Desfazer e limpar seleção"
      className="analise-controles-globais analise-nao-imprimir">
      <button type="button" data-testid="analise-desfazer" className="analise-controle-global" onClick={desfazer} disabled={!passoADesfazer}
        title={textoDoDesfazer(passoADesfazer)} aria-label={textoDoDesfazer(passoADesfazer)} data-passos={passos.length}>
        <Undo size={18} aria-hidden="true"/>Desfazer</button>
      <button type="button" data-testid="analise-limpar-selecao" className="analise-controle-global" onClick={limparSelecao}
        disabled={!temSelecaoParaLimpar} title={temSelecaoParaLimpar ? "Tira os territórios em análise; os dados carregados continuam."
          : def.nivel === "brasil" ? "No nível Brasil, o país inteiro é a unidade em análise: não há seleção para limpar."
          : "Nenhum território selecionado."}>
        <IconeVassoura size={18} aria-hidden="true"/>Limpar seleção</button>
      <span data-testid="analise-controles-territorios" className="analise-controles-territorios">
        <MapaIcone size={14} aria-hidden="true"/><span className="truncate">{resumoDaSelecao}</span></span>
    </div>}
    {!fonte && abertura}
    {fonte && props.trocandoFonte && trocaDaFonte}
    {fonte && !pronto && <p data-testid="analise-preparando" role="status" className="analise-vazio"><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>
      Preparando os dados…</p>}
    {/* Abas numa linha (roláveis no celular), só com os dados prontos: a Seleção de Territórios e as quatro análises, só com os
        nomes (24/10/2026). O painel da aba escolhida, colado nela: na Seleção, a orientação curta e a escolha; nas análises,
        "Entenda esta análise" (recolhível), o motivo (quando não pode ser executada) e os ajustes. */}
    {pronto && <div className="analise-familias-bloco analise-com-ajustes">
      <div role="tablist" aria-label="Seleção de territórios e análises" className="analise-familias analise-nao-imprimir">
        {ABAS.map((item, indice) => {
          const ativa = aba === item;
          if (item === "territorios") return <button key={item} id={idDaAba(item)} type="button" role="tab" data-testid="analise-aba-territorios"
            aria-selected={ativa} aria-controls="analise-aba-painel" tabIndex={ativa ? 0 : -1} className="analise-familia analise-aba-selecao"
            onClick={() => escolherAba(item)} onKeyDown={event => teclasAbas(event, indice)}>
            <span className="analise-familia-nome">{NOME_SELECAO}</span>
            <span data-testid="analise-aba-territorios-resumo" className="analise-familia-apoio">{resumoDaSelecao}</span>
          </button>;
          const disponivel = disponivelDe(item);
          return <button key={item} id={idDaAba(item)} type="button" role="tab" data-testid={"analise-familia-" + item}
            data-disponivel={disponivel.disponivel ? "true" : "false"} aria-selected={ativa} aria-controls="analise-aba-painel"
            tabIndex={ativa ? 0 : -1} title={!disponivel.disponivel ? disponivel.motivo : undefined}
            className={"analise-familia" + (!disponivel.disponivel ? " analise-familia-indisponivel" : "")}
            onClick={() => escolherAba(item)} onKeyDown={event => teclasAbas(event, indice)}>
            <span className="analise-familia-nome">{NOMES_FAMILIAS[item]}</span>
          </button>;
        })}
      </div>
      <div role="tabpanel" id="analise-aba-painel" data-testid="analise-aba-painel" data-aba={aba} aria-labelledby={idDaAba(aba)}
        className="analise-aba-painel analise-nao-imprimir">
        {naSelecao ? <>
          <div className="analise-selecao-intro">
            <h3 className="sr-only">{NOME_SELECAO}</h3>
            <TextoDaApresentacao aba={aba} apresentacao={apresentacaoDaAba(aba, { rotulos, brasil: tipo === "brasil", comGrupos: grupos.length > 0 })}/>
          </div>
          <PainelTerritorios rotulos={rotulos} brasil={tipo === "brasil"} grupos={grupos} comNiveis={comBolhasDeGrupo} unidades={municipios}
            total={totalDeUnidades} nivel={def.nivel} base={def.base} estados={def.estados} conjuntos={def.conjuntos} aberto={aberto}
            aviso={avisoSelecao} verAnalise={"Ver a " + NOMES_FAMILIAS[def.familia]}
            onNivel={escolherNivel} onBase={(base, acao, coletiva) => mudarEscolha({ nivel: "municipios", base }, acao, coletiva)}
            onEstados={(estados, acao, coletiva) => mudarEscolha({ nivel: "estados", estados }, acao, coletiva)}
            onAbrir={abrirLista} onDesfazerConjunto={desfazerConjunto}
            onVerAnalise={() => escolherAba(def.familia)}/>
        </> : <>
          <EntendaEstaAnalise key={aba} aba={aba} pedida={explicacaoPedida}
            apresentacao={apresentacaoDaAba(aba, { rotulos, brasil: tipo === "brasil", comGrupos: grupos.length > 0 })}/>
          {motivoDaAba && <p data-testid="analise-familia-motivo" role="status" className="analise-motivo">
            <strong className="text-ink">Indisponível com estes dados:</strong> {motivoDaAba.motivo}
            {motivoDaAba.enviarDados && <button type="button" data-testid="analise-enviar-dados" className="analise-botao-secundario ml-2"
              onClick={() => props.onEscolherFonte("arquivo")}><Upload size={14} aria-hidden="true"/>Enviar meus dados</button>}
            <span className="analise-motivo-desenho">O desenho abaixo continua com a {NOMES_FAMILIAS[def.familia]}.</span>
          </p>}
          {!motivoDaAba && <div data-testid="analise-ajustes" data-familia={def.familia} className="analise-ajustes">
            {ajustes.map(ajuste)}
          </div>}
          <p data-testid="analise-selecao-resumo" className="analise-selecao-resumo">
            <MapaIcone size={14} aria-hidden="true"/><span><strong className="text-ink">Territórios:</strong> {resumoDaSelecao}</span>
            <button type="button" data-testid="analise-selecao-alterar" className="analise-link" onClick={irParaTerritorios}>
              {semUnidades ? "Selecionar os territórios" : "Alterar a seleção"}</button>
          </p>
        </>}
      </div>
    </div>}

    {pronto && <div data-testid="analise-resultados" hidden={naSelecao} className="analise-resultados">
    <header className="analise-cabecalho">
      <h2 id="analise-titulo" tabIndex={-1} data-testid="analise-titulo" className="analise-titulo">{titulo}</h2>
      {!layoutTendencia && subtituloEResumo}
    </header>

    <div ref={corpoRef} className={"analise-corpo" + (layoutTendencia ? " analise-corpo-tendencia" : painel ? " analise-corpo-com-painel" : "") +
      (lado ? " analise-corpo-lado" : "")} style={layoutTendencia ? { "--analise-largura-lateral": larguraLateral + "px" } as CSSProperties : undefined}>
      <div id="analise-centro" className="analise-centro">
        <div className="analise-funcoes analise-nao-imprimir">
          <div className="analise-funcoes-linha">
            <button type="button" data-testid="analise-ferramentas" className="analise-ferramentas-botao" aria-expanded={ferramentas}
              aria-controls="analise-funcoes-lista" onClick={() => setFerramentas(valor => !valor)}><Wrench size={15} aria-hidden="true"/>Ferramentas</button>
            <div id="analise-funcoes-lista" role="toolbar" aria-label="Funções" className={"analise-funcoes-lista" + (ferramentas ? " analise-funcoes-abertas" : "")}>
              {FUNCOES.map(funcao => {
                const motivo = funcaoDesabilitada(funcao.chave);
                return <button key={funcao.chave} type="button" data-testid={"analise-funcao-" + funcao.chave} disabled={!!motivo} title={motivo ?? undefined}
                  aria-expanded={painel === funcao.chave} aria-controls="analise-painel" className="analise-funcao"
                  onClick={() => painel === funcao.chave ? fecharPainel() : abrirPainel(funcao.chave)}>
                  {funcao.icone}{funcao.rotulo}{funcao.chave === "comparar" && selecao.length ? " (" + selecao.length + ")" : ""}</button>;
              })}
            </div>
            {/* Limpar filtros (24/10/2026): os filtros da análise em uso, nunca a seleção de territórios nem os ajustes; o ícone do
                filtro riscado o distingue do Limpar seleção, no alto. Desfazer devolve os filtros. */}
            {filtrosAtivos && <div className="analise-limpar" role="group" aria-label="Limpar os filtros">
              <button type="button" data-testid="analise-limpar-filtros" className="analise-funcao"
                title="Tira a régua, as condições, a ordenação, a comparação, o filtro da classe e os itens marcados. Os territórios e os ajustes continuam."
                onClick={limparFiltros}><FilterX size={15} aria-hidden="true"/>Limpar filtros</button>
            </div>}
            {/* Junto do desenho: a escala (só quando se aplica) e a vista (Gráfico | Mapa | Lado a lado), sempre à vista. */}
            <div data-testid="analise-barra-desenho" className="analise-barra-desenho">
              {escalaNoGrafico && <label className="analise-escala">Escala
                <select data-testid="analise-escala" value={logPossivel ? escala : "linear"}
                  onChange={event => { registrar("Trocar a escala"); setEscala(event.target.value as Escala); }} className="analise-campo">
                  <option value="linear">Linear (a partir do zero)</option>
                  <option value="logaritmica" disabled={!logPossivel}>Logarítmica{logPossivel ? "" : " (exige valores positivos)"}</option>
                </select>
              </label>}
              <div role="group" aria-label="Vista do desenho" data-testid="analise-desenho" className="analise-segmentos analise-desenho">
                {vistasNaBarra.map(item => {
                  const desligada = item.chave !== "grafico" && !mapa.disponivel;
                  return <button key={item.chave} type="button" data-testid={"analise-desenho-" + item.chave} aria-pressed={vistaExibida === item.chave}
                    aria-disabled={desligada || undefined} title={desligada ? mapa.motivo ?? undefined : undefined}
                    aria-describedby={desligada && motivoVistaAberto ? "analise-desenho-motivo" : undefined} onClick={() => trocarVista(item.chave)}>
                    {item.icone}{item.rotulo}</button>;
                })}
              </div>
            </div>
          </div>
          {motivoVistaAberto && !mapa.disponivel && <p id="analise-desenho-motivo" data-testid="analise-desenho-motivo" role="status" className="analise-motivo">
            <strong className="text-ink">Mapa:</strong> {mapa.motivo}
            {mapa.atalho && <button type="button" data-testid="analise-desenho-atalho" className="analise-botao-secundario ml-2" onClick={verUnidadesNoMapa}>
              <MapaIcone size={14} aria-hidden="true"/>{mapa.atalho}</button>}
            <button type="button" className="analise-icone ml-1" aria-label="Fechar o motivo do mapa" onClick={() => setMotivoVistaAberto(false)}>
              <X size={14} aria-hidden="true"/></button>
          </p>}
        </div>

        <div className="analise-avisos">
          {carregando && resposta && <p role="status" data-testid="analise-atualizando" className="analise-status"><LoaderCircle size={15} className="animate-spin" aria-hidden="true"/>
            Atualizando o gráfico…</p>}
          {erro && <div role="alert" data-testid="analise-erro" className="analise-erro">
            <p>Não foi possível calcular o gráfico com a última mudança: {erro.mensagem}</p>
            {erro.pendencia && <div data-testid="analise-pendencia" className="mt-2 space-y-1.5">
              <p className="font-semibold">{erro.pendencia.texto || "Antes de calcular, é preciso uma escolha."}</p>
              <div className="flex flex-wrap gap-1.5">{erro.pendencia.opcoes.map(opcao => <button key={opcao.valor} type="button" data-testid="analise-pendencia-opcao"
                data-valor={opcao.valor} className="analise-botao-secundario" onClick={() => escolherPendencia(erro.pendencia!.chave, opcao.valor)}>{opcao.rotulo}</button>)}</div>
            </div>}
            <div className="mt-2 flex flex-wrap gap-3">
              {calculado && <button type="button" data-testid="analise-voltar-calculado" onClick={voltarAoCalculado} className="font-semibold underline">
                Voltar ao último gráfico calculado</button>}
              <button type="button" data-testid="analise-tentar" onClick={() => setTentativa(valor => valor + 1)} className="inline-flex items-center gap-1 font-semibold underline">
                <RefreshCw size={13} aria-hidden="true"/>Tentar novamente</button>
            </div>
          </div>}
          {avisoFamilia && fonte && !semUnidades && <p data-testid="analise-aviso-familia" role="status" className="analise-aviso-familia">
            <SlidersHorizontal size={14} aria-hidden="true"/>{avisoFamilia}</p>}
          {semReferencia && !semUnidades && <p data-testid="analise-ref-sem-resultado" role="status" className="analise-aviso-familia">
            <SlidersHorizontal size={14} aria-hidden="true"/><span>{semReferencia}{" "}
              <button type="button" data-testid="analise-ref-sem-resultado-mudar" className="analise-link" onClick={() => abrirPainel("referencia")}>
                Mudar o território de referência</button></span></p>}
          {foraDoGrafico && <p data-testid="analise-fora-do-grafico" role="status" className="analise-aviso-familia">
            <ChartScatter size={14} aria-hidden="true"/><span>{foraDoGrafico}</span></p>}
          {/* Territórios base (25/10/2026): cada base, a referência dela e a distância do motor, à vista no gráfico e no mapa. */}
          {/* Sem nenhuma referência entre várias bases, o aviso acima já diz o motivo. */}
          {distanciaNaTela && basesDaReferencia.length > 0 && !semUnidades && (pares.length < 2 || pares.some(par => par.referencias.length > 0)) &&
            <p data-testid="analise-par-base" role="status" className="analise-aviso-familia">
            <Crosshair size={14} aria-hidden="true"/><span>{textoDosTerritoriosBase({ pares, todos: todasAsBases, ligados: paresLigados.length,
              relacao: relacaoNaTela })}{" "}
              <button type="button" data-testid="analise-par-base-mudar" className="analise-link" onClick={() => abrirPainel("referencia")}>
                {!pares.length ? "Escolher os territórios base" : pares.length === 1 && !todasAsBases ? "Mudar o território base"
                  : "Mudar os territórios base"}</button></span></p>}
          {resposta?.nivel === "estados" && def.nivel === "estados" && <p data-testid="analise-instrucao" className="analise-instrucao">
            <Scale size={14} aria-hidden="true"/>{textoInstrucaoGrupos(rotulos)}</p>}
          {/* Convite ao mapa depois das Condições e na Análise espacial: "onde ficam?" é a pergunta que o mapa responde. */}
          {convite && <p className="analise-convite analise-nao-imprimir"><MapaIcone size={14} aria-hidden="true"/>
            <button type="button" data-testid="analise-convite-mapa" className="analise-link" onClick={() => trocarVista("mapa")}>Ver onde ficam no mapa</button></p>}
        </div>

        {!layoutTendencia && contagemClasses}
        <div ref={quadroRef} className={"analise-quadro" + (lado && !antesDoDesenho ? " analise-quadro-lado" : "")}>
          {antesDoDesenho ?? <>
            {(vistaExibida === "grafico" || lado) && <div ref={graficoRef} data-testid="analise-vista-grafico"
              className={"analise-vista" + (oculta === "grafico" ? " analise-vista-oculta" : "")}>{desenhoDoGrafico}</div>}
            {montarMapa && <div data-testid="analise-vista-mapa" hidden={!mapaNaTela}
              className={"analise-vista" + (oculta === "mapa" ? " analise-vista-oculta" : "")}>{desenhoDoMapa}</div>}
          </>}
        </div>
        {distanciaNaTela && <p data-testid="analise-nota-distancia" className="analise-nota">{NOTA_TPL11} (TPL-11)</p>}
      </div>

      {/* Tendência (24/10/2026): a divisória ajustável e, à direita, a explicação do que está no desenho (como ler, a frase-resumo,
          as contagens por classe, a legenda e as velocidades da linha escolhida), com o painel da função aberta por cima dela. */}
      {layoutTendencia && <div data-testid="analise-divisoria" role="separator" aria-orientation="vertical" tabIndex={0}
        aria-label="Divisória entre o desenho e a explicação: arraste ou use as setas para mudar a largura"
        aria-valuemin={LATERAL_MIN} aria-valuemax={larguraMaxima} aria-valuenow={larguraLateral}
        className="analise-divisoria analise-nao-imprimir" onPointerDown={arrastarDivisoria} onKeyDown={teclasDivisoria}>
        <GripVertical size={14} aria-hidden="true"/></div>}
      {layoutTendencia ? <div data-testid="analise-tendencia-lateral" className="analise-lateral">
        {painelDaFuncao}
        <section data-testid="analise-explicacao" aria-label="Como ler este resultado" className="analise-explicacao">
          <h3 className="analise-explicacao-titulo">Como ler</h3>
          {subtituloEResumo}
          {contagemClasses}
          {quadroDeSetas && <LegendaDoQuadro legenda={legendaCor} rotulos={rotulos}/>}
          {cometa && legendaCor && <div className="analise-legenda analise-explicacao-bloco">{legendaCor}</div>}
          {series && <LegendaDaSerie indicador={indicador} rotulos={rotulos}/>}
          {quadroDeSetas && (itemDasVelocidades
            ? <Velocidades item={itemDasVelocidades} indicador={indicador} unidadeTempo={resposta?.tendencia?.unidadeTempo ?? null}/>
            : <p className="analise-explicacao-dica">Clique numa linha do quadro para ver as velocidades dela aqui.</p>)}
        </section>
      </div> : painelDaFuncao}
    </div>

    {resposta && !semUnidades && <PainelDetalhes resposta={resposta} itens={visiveis} fora={fora} familia={familiaDesenho} indicador={indicador}
      distancia={distanciaNaTela} variacao={exibicao.variacao} tendencia={exibicao.tendencia} rotulos={rotulos} selecionados={selecao}
      limiares={limiares} corteAtivo={corteAtivo(corte, dominio)} onAlternar={alternar}/>}
    </div>}
    <p aria-live="polite" className="sr-only" data-testid="analise-aviso">{aviso}</p>
  </section>;
}
