import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent as EventoPonteiro,
  type ReactNode } from "react";
import { ArrowLeftRight, ChartScatter, ChevronDown, Columns2, Crosshair, Database, Download, Filter, FilterX, GripVertical,
  ListOrdered, LoaderCircle, Map as MapaIcone, Pause, Play, RefreshCw, Ruler, Scale, SlidersHorizontal, Undo, Upload, Wrench, X } from "lucide-react";
import {
  ErroDoMotor, pedirCriterios, pedirLugar, pedirMapa, pedirPainel, type FonteDoMotor, type LugarOpcoes, type MapaOpcoes, type Pendencia,
  type PainelConjuntoPedido, type PainelItem, type PainelMunicipios, type PainelNivel, type PainelOpcoes, type PainelResposta,
  type RespostaLugar, type RespostaCriterios,
} from "./painelApi";
import {
  ABAS, CLASSES_TENDENCIA, DESCRICAO_DAS_CLASSES, INDICADORES, MAX_LIGACOES, NOME_SELECAO, ORDEM_DAS_VISOES, TEXTO_DAS_FONTES,
  TEXTO_ESCOLHA_DOS_DADOS, TEXTO_SEM_SELECAO, TITULO_DO_SISTEMA, LARGURA_LADO_A_LADO, LIMITE_LEVE, MINIMO_TENDENCIA, NOMES_FAMILIAS,
  NOMES_FAMILIA_TENDENCIA, NOMES_VISOES, NOTA_TPL11, ROTULOS_GENERICOS, TEXTO_SEM_POPULACAO, ajustesDaAnalise, aplicarPedido,
  artigo, avisoDaFamilia, baseVazia, basesPossiveis, bloqueioDoPedido, camadaDeCor, chaveDoPedido, comparacaoQueContinua, consultaEmUso, consultaInicial,
  contextoDoGrafico, fraseDaConsulta, lugarDaConsulta, mesmaConsulta, normalizarBase, textoDaFraseDaConsulta,
  corContinuaDoMapa, corOrdinal, corteAtivo, cronologica, definicaoInicial, disponibilidadeDaFamilia, disponibilidadeDoMapa, empilharPasso,
  dentroDosFiltros, destaqueDaAnalise, escreverLimites, exibirCompetencia, familiaCalculada, formatarNumero, formatarVariacao, generoDe, gradienteDaVariacao, grupoDaUnidade,
  grupoDoItem, gruposDaFonte, intervaloDaSerie, intervaloEntre, itensParaOMapa, janelaPadrao, lerEstadoSalvo, lerLimites, ligacoesDoMapa,
  competenciaPorExtenso, limiteDaVariacao, limparEscolha, listaDeCompetencias, lugarDoUniverso, maisRecente, maiuscula, montarCsv, montarDica,
  escolhaDaArvore, gruposParciais, unificarEscolha, type ContextoDaArvore, ativarEstados, desativarEstados, ativarRegioes, desativarRegioes,
  conjuntosComMembrosNos, conjuntoDeEstados, nivelDaSelecao, baseSemOsEstados, unidadeMarcada, foraDaRotatividade,
  MAX_CONJUNTOS, REGIOES_DO_BRASIL, RESSALVA_DA_SOMA, TEXTO_MAX_GRUPOS, competenciaAbreviada, contagemPorTipo, emGrupos, gruposDaRegiao, regioesDaFonte, rotulosDaVista, type GrupoInfo,
  regraConfere, textoDaRegra, quantos, criteriosDasCondicoes, type RegraDaSelecao, baseComUnidades, baseSemUnidades, membrosNaSelecao, deOndeEhOResultado, desdeDaFaixa, destaquesDaOrdem, lugarConfere, lugarDaTrilha, nomeCurtoDoNivel, nomeDoTodo, normalizarArvore, textoDaReferencia, textoEspacialNosGrupos,
  textoVerUnidadesDosGrupos, type ParteDaTrilha,
  montarOpcoes, profissionaisDe,
  apresentacaoDaAba, nomeDaUnidade, notaSemClassificacao, novoConjunto, ordemNeutra, paletaDoGrafico, paresDasBases, pedidoDependeDoIndicador, pintar,
  pinturaDoMapa, prefixoDe, precisaQuintisDoMapa, resumoDoUniverso, ritmoDaJanela, ritmosDaBase, RITMOS_TENDENCIA,
  rotulosEfetivos, salvarEstado, semSelecao, semTerritorios, separarItens, significadoDaClasse, tamanhoDoMapa, textoDaMarca, textoDoDesfazer, textoDoDesfeito,
  textoDoMetodo, textoDosTerritoriosBase, textoForaDoDesenho, textoInstrucaoGrupos, tituloDaAnalise, todosOs, umA, visaoEfetiva,
  type Aba, type Ajuste, type Apresentacao, type ContextoDoGrafico, type Corte, type DefinicaoAnalise, type Disponivel, type Escala,
  type ConsultaTerritorios, type DesfechoDoPedido, type EstadoSalvo, type Familia, type FonteDados, type FuncaoPainel, type NiveisDaBase,
  type PassoDaInteracao, type PedidoDoChat, type SituacaoDoPedido, type UnidadeDoCatalogo, type Visao, type Vista,
} from "./painelModel";
import type { DadosDoMapa, MapaHandle, MapaProps, Posicoes, VistaDesenho } from "./mapaContrato";
import PainelChart, { type FaseAnimacao, type LinhaDeReferencia } from "./PainelChart";
import PainelSeries, { LegendaDaSerie, MAX_SERIES, Velocidades, type SerieDeReferencia } from "./PainelSeries";
import PainelSetas, { LegendaDoQuadro } from "./PainelSetas";
import PainelRotatividade from "./PainelRotatividade";
import PainelRuler from "./PainelRuler";
import PainelTerritorios, { type AcaoDaSelecao } from "./PainelTerritorios";
import AgruparSelecionados, { type ConjuntoPorProximidade } from "./AgruparSelecionados";
import SelecionarPorCriterios, { type PedidoDosCriterios, type UsoDosCriterios } from "./SelecionarPorCriterios";
import PainelAbrangencia from "./PainelAbrangencia";
import FaixaDoLugar, { Trilha } from "./FaixaDoLugar";
import PainelDetalhes from "./PainelDetalhes";
import MapaAnalise from "./MapaAnalise";
import { animarTransicao, posicoesDoGrafico } from "./transicaoVistas";
import { GavetaComparar, GavetaCondicoes, GavetaExportar, GavetaOrdenar } from "./PainelGavetas";
import type { GrupoAgregado } from "./AgregarTerritorios";
import ListaDosGrupos from "./ListaDosGrupos";
import { useNarrow } from "./useNarrow";
import EscolhaDosTerritorios from "./EscolhaDosTerritorios";
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
// (onSalvar) e pode reabrir sem recalcular (restaurar). Desde 05/11/2026, cada pedido da conversa tem um desfecho (onDesfecho),
// informado quando a área de fato o mostra ou não consegue: a conversa só diz que fez o que foi pedido com a confirmação.

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
  /** Confirmação de execução (05/11/2026): o desfecho de cada pedido da conversa (o id da prop `pedido`), quando a área de fato
   * o mostra: o motor calculou a definição que resultou dele (e os pontos do mapa chegaram, quando o mapa foi pedido), ou o que
   * impediu (a parte recusada, o que falta, a falha do motor, outra mudança que tomou o lugar dele). */
  onDesfecho?: (desfecho: DesfechoDoPedido) => void;
  /** A reabertura de um estado do Histórico (`restaurar`): true quando ele foi reaberto como estava. */
  onRestaurado?: (ok: boolean) => void;
};

/** O rótulo do passo do Desfazer de um pedido da conversa: os demais passos são mudanças feitas na área (05/11/2026: uma delas,
 * antes do fim de um pedido, toma o lugar dele). */
const ROTULO_DO_PEDIDO = "Aplicar o pedido da conversa";

const MAX_CACHE = 6;
/** Repetições automáticas de um pedido recusado por ocupado (01/11/2026). */
const MAX_REPETICOES_OCUPADO = 2;
const FUNCOES: { chave: FuncaoPainel; rotulo: string; icone: ReactNode }[] = [
  { chave: "regua", rotulo: "Régua", icone: <Ruler size={15} aria-hidden="true"/> },
  { chave: "condicoes", rotulo: "Condições", icone: <Filter size={15} aria-hidden="true"/> },
  { chave: "ordenar", rotulo: "Ordenar", icone: <ListOrdered size={15} aria-hidden="true"/> },
  { chave: "comparar", rotulo: "Comparar", icone: <ArrowLeftRight size={15} aria-hidden="true"/> },
  { chave: "exportar", rotulo: "Exportar", icone: <Download size={15} aria-hidden="true"/> },
];
const TITULOS_PAINEL: Record<FuncaoPainel, string> = { regua: "Régua", condicoes: "Condições", ordenar: "Ordenar", comparar: "Comparar",
  exportar: "Exportar", referencia: "Escolha dos territórios" };
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
const NENHUM_REALCE: string[] = [];
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
  // O grupo de cima de uma planilha com dois níveis (07/11/2026, item 1 do comando): só com a coluna escolhida no painel Colunas
  // (nada é presumido), pelo catálogo (o segundo valor da hierarquia de cada unidade).
  const superiorDaFonte = tipo === "arquivo" ? fonte?.mapping?.grupo_territorial_superior ?? "" : "";
  const { regioes, regiaoDoGrupo } = useMemo(() => superiorDaFonte ? regioesDaFonte(municipios, grupos)
    : { regioes: [] as GrupoInfo[], regiaoDoGrupo: new Map<string, string>() }, [superiorDaFonte, municipios, grupos]);
  const idsDasRegioes = useMemo(() => regioes.map(item => item.id), [regioes]);
  const grupoDeMapa = useMemo(() => new Map(municipios.map(item => [item.id, grupoDaUnidade(item)])), [municipios]);
  const grupoDe = useCallback((id: string) => grupoDeMapa.get(id) ?? prefixoDe(id), [grupoDeMapa]);
  // A seleção unificada (05/11/2026): as unidades de cada grupo (os municípios de cada estado) e o total, para a árvore reconhecer
  // as abrangências completas (o estado inteiro, o Brasil inteiro).
  const idsPorGrupo = useMemo(() => {
    const mapa = new Map<string, string[]>();
    for (const item of municipios) {
      if (item.selection_reason) continue;
      const grupo = grupoDaUnidade(item);
      if (!mapa.has(grupo)) mapa.set(grupo, []);
      mapa.get(grupo)!.push(item.id);
    }
    return mapa;
  }, [municipios]);
  const arvore: ContextoDaArvore = useMemo(() => ({ grupos, unidadesDoGrupo: (grupo: string) => idsPorGrupo.get(grupo) ?? [], grupoDe,
    total: niveis?.municipios.total ?? municipios.filter(item => !item.selection_reason).length,
    ...(regioes.length ? { regioes, regiaoDoGrupo: (grupo: string) => regiaoDoGrupo.get(grupo) ?? "" } : {}) }),
    [grupos, idsPorGrupo, grupoDe, niveis, municipios, regioes, regiaoDoGrupo]);
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
  /** Referência pedida na conversa por critério: o filtro do atributo citado já vem na Referência da Escolha dos territórios. */
  const [criterioDoChat, setCriterioDoChat] = useState<{ atributo: "densidade" | "quantidade" | "populacao"; ordem: "desc" | "asc" } | null>(null);
  /** Desfazer (24/10/2026, segunda rodada): os passos da interação, o mais recente no fim. */
  const [passos, setPassos] = useState<PassoDaInteracao<EstadoDaInteracao>[]>([]);
  /** O que a última mudança coletiva da Seleção fez ("Municípios da Bahia desmarcados."), mostrado junto do que está marcado. */
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
  // O erro do motor, com a chave do pedido que falhou e, no ocupado, se a nova tentativa automática já está marcada (05/11/2026:
  // o desfecho de um pedido da conversa espera a nova tentativa).
  const [erro, setErro] = useState<{ mensagem: string; pendencia: Pendencia | null; chave?: string; repetindo?: boolean } | null>(null);
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
  const [erroMapa, setErroMapa] = useState<{ chave: string; mensagem: string; pendencia: Pendencia | null; repetindo?: boolean } | null>(null);
  const [tentativaMapa, setTentativaMapa] = useState(0);
  // Ocupado (01/11/2026): o serviço respondeu que está no limite (503 com `ocupado`). O pedido é repetido sozinho, depois do
  // tempo que o serviço indica, no máximo MAX_REPETICOES_OCUPADO vezes por gráfico ou mapa; depois, fica o "Tentar novamente".
  const repeticoesOcupado = useRef(new Map<string, number>());
  const repetirSeOcupado = (exc: unknown, chave: string, repetir: () => void): (() => void) | undefined => {
    if (!(exc instanceof ErroDoMotor) || !exc.ocupado) return undefined;
    const vezes = repeticoesOcupado.current.get(chave) ?? 0;
    if (vezes >= MAX_REPETICOES_OCUPADO) return undefined;
    repeticoesOcupado.current.set(chave, vezes + 1);
    const id = window.setTimeout(repetir, (exc.tenteEm ?? 5) * 1000);
    return () => window.clearTimeout(id);
  };
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
  /** Mudanças feitas na área (todo passo do Desfazer que não é um pedido da conversa, e o próprio Desfazer): uma delas, antes do fim
   * de um pedido da conversa, toma o lugar dele (05/11/2026). */
  const manuais = useRef(0);
  function registrar(rotulo: string, tipoDoPasso = rotulo) {
    if (rotulo !== ROTULO_DO_PEDIDO) manuais.current += 1;
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
    manuais.current += 1;
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
    setVista("final"); setFase("parado");
    setAviso(textoDoDesfeito(passo));
  }
  const passoADesfazer = passos[passos.length - 1] ?? null;

  const rotulos = rotulosEfetivos(resposta?.rotulos, fonte?.rotulos, tipo);
  const temIdentificador = !!fonte?.mapping?.identity;
  const disponibilidade = resposta?.disponibilidade ?? null;
  // As bolhas de grupo: na base do Brasil, os estados; desde 07/11/2026 (item 1 do comando), também os grupos da coluna-mãe de
  // uma planilha, pelas unidades de cada um (o motor diz se o nível existe).
  const comBolhasDeGrupo = !!tipo && grupos.length > 0 && (disponibilidade?.estados?.disponivel ?? disponibilidade?.grupos?.disponivel ?? true);
  // O todo vendo por grupo (06/11/2026): só na base do Brasil. Numa planilha, o todo continua mostrando as unidades, e os grupos
  // aparecem pelo "Ver por" (07/11/2026).
  const todoPorGrupo = comBolhasDeGrupo && tipo === "brasil";
  const disponivelDe = useCallback((familia: Familia): Disponivel => disponibilidadeDaFamilia(familia, { fonte: tipo, nivel: def.nivel,
    disponibilidade, temIdentificador, rotulos }), [tipo, def.nivel, disponibilidade, temIdentificador, rotulos]);
  /** O mapa numa definição (a da tela ou a que resulta de um pedido da conversa). */
  const mapaDe = (d: DefinicaoAnalise) => disponibilidadeDoMapa({ fonte: tipo, temCoordenadas, nivel: d.nivel,
    series: d.nivel === "municipios" && d.familia === "tendencia" && visaoEfetiva(d) === "series", rotatividade: d.familia === "rotatividade", rotulos });
  // Os nomes dos territórios: as unidades do catálogo, os itens da resposta e, para os conjuntos de estados (comando V22), os
  // estados pelo id "uf:".
  const nomes = useMemo(() => new Map<string, string>([...municipios.map(item => [item.id, nomeDaUnidade(item)] as [string, string]),
    ...grupos.map(grupo => ["uf:" + grupo.id, grupo.nome] as [string, string]),
    ...(resposta?.itens || []).map(item => [item.id, item.rotulo] as [string, string])]), [municipios, grupos, resposta]);
  /** Grupo da lista de uma bolha de grupo (estado) do motor. */
  // No nível de cima (07/11/2026), a bolha é um grupo de cima, com as unidades dos grupos dele.
  const gruposDaBolha = resposta?.nivel === "regioes" ? regioes : grupos;
  const grupoDaBolha = useCallback((id: string) => {
    const item = resposta?.itens.find(atual => atual.id === id);
    return grupoDoItem(item ?? { id, uf: null, rotulo: id }, gruposDaBolha);
  }, [resposta, gruposDaBolha]);
  const unidadesDoGrupo = useCallback((id: string) => {
    const grupo = grupoDaBolha(id);
    return grupo === null ? null : gruposDaBolha.find(item => item.id === grupo)?.unidades ?? null;
  }, [grupoDaBolha, gruposDaBolha]);
  // A trilha e o lugar em uso (06/11/2026, itens 2 e 3 do comando): lidos da seleção em uso, iguais em todas as abas.
  const lugar = useMemo(() => lugarDaTrilha(escolhaDe(def), { arvore, nomeDoTodo: nomeDoTodo(tipo !== "arquivo", rotulos), nomes, comGrupos: comBolhasDeGrupo,
    regra: def.regra }), [def.nivel, def.base, def.estados, def.conjuntos, def.regra, arvore, tipo, nomes, comBolhasDeGrupo, rotulos]);
  // A regra da seleção por critérios em uso (07/11/2026, item 6 do comando): vale enquanto a seleção for a que ela produziu.
  const regraEmUso = regraConfere(def.regra, def) ? def.regra! : null;
  // Os grupos de cima de uma planilha com dois níveis (07/11/2026): com a hierarquia consistente, eles podem entrar como unidade
  // ("Só a zona", na árvore). O "Ver por" saiu (comando V22, decisão 3): o estado como unidade é escolhido na própria árvore.
  const comRegioes = comBolhasDeGrupo && regioes.length > 0 && (disponibilidade?.regioes?.disponivel ?? true);
  const [numerosDoLugar, setNumerosDoLugar] = useState<{ chave: string; base: string; dados: RespostaLugar } | null>(null);
  // O painel "Selecionar por critérios" (07/11/2026): fechado (null), aberto vazio, com a regra a reaplicar ou com o pedido da
  // conversa (com a prévia ao abrir; `n` conta os pedidos, para o mesmo pedido repetido abrir de novo).
  const [criterios, setCriterios] = useState<{ inicial: RegraDaSelecao["pedido"] | null; previa?: boolean; n?: number;
    aviso?: string } | null>(null);
  // A ação aberta no painel direito da Seleção (comando V22, seção 3): a lista dos selecionados (padrão), "Aplicar critérios de
  // seleção" ou "Agrupar territórios selecionados"; a árvore continua à vista. A conversa, as Condições e "Reaplicar em outra
  // competência" abrem os critérios preenchidos.
  const [acaoSelecao, setAcaoSelecao] = useState<AcaoDaSelecao>("lista");
  // O agrupamento aberto: um conjunto novo ou o conjunto em edição (✎); `km`, a distância de um pedido que veio dos critérios.
  const [agrupamento, setAgrupamento] = useState<{ n: number; editando?: { id: string; grupo: GrupoAgregado } | null; km?: number | null } | null>(null);
  const [carregandoLugar, setCarregandoLugar] = useState(false);
  const [erroLugar, setErroLugar] = useState<{ chave: string; mensagem: string } | null>(null);
  const cacheLugar = useRef(new Map<string, RespostaLugar>());

  // ------------------------------------------------------------------------------------------ fonte nova: abertura (E1)
  const iniciado = useRef("");
  const pedidoPendente = useRef<{ id: number; pedido: PedidoDoChat } | null>(null);
  const ultimoPedido = useRef<number | null>(null);
  const reiniciarVisual = () => { setCorte(null); setSelecionados([]); setPainel(null); setAberto(null); setVista("final"); setFase("parado");
    setSoAtende(false); setFiltroClasse(null); setFaixasTexto(""); setOculta(null); setAtivoCruzado(null); setMotivoVistaAberto(false); };
  useEffect(() => {
    if (!fonte) {
      if (iniciado.current) { iniciado.current = ""; cache.current.clear(); cacheMapa.current.clear(); setResposta(null); setCalculado(null); setErro(null);
        setDadosDoMapa(null); setErroMapa(null); reiniciarVisual(); setPassos([]); pendente.current = null;
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
    setPassos([]); pendente.current = null;
    const pendentePedido = pedidoPendente.current ?? (pedido && pedido.id !== ultimoPedido.current ? pedido : null);
    if (pendentePedido) {
      pedidoPendente.current = null;
      ultimoPedido.current = pendentePedido.id;
      const resultado = aplicarPedido(inicial, pendentePedido.pedido, { periodos, nomes, temGrupos: grupos.length > 0, grupoDe, mapa: mapaDe,
        todosOsEstados: idsDosGrupos, temBrasil: tipo === "brasil" && grupos.length > 0, unidadesDoGrupo: arvore.unidadesDoGrupo,
        disponivel: familia => disponibilidadeDaFamilia(familia, { fonte: tipo, nivel: inicial.nivel, disponibilidade: null, temIdentificador, rotulos }) });
      if (!temPopulacao && pendentePedido.pedido.indicador === "densidade") { resultado.definicao.indicador = "quantidade"; resultado.mensagens.push(TEXTO_SEM_POPULACAO); }
      // A árvore mostra o que está na análise (05/11/2026): os estados ou o Brasil pedidos ficam marcados nela.
      inicial = { ...resultado.definicao, ...unificarEscolha(escolhaDe(resultado.definicao), arvore) };
      if (resultado.selecao) setSelecionados(resultado.selecao);
      if (resultado.abrir) setPainel(resultado.abrir);
      if (resultado.vista) setVistaEscolhida(resultado.vista);
      setCriterioDoChat(resultado.criterio);
      setAviso(["Pedido da conversa aplicado ao gráfico.", ...resultado.mensagens].join(" "));
      iniciarExecucao(pendentePedido.id, resultado.mensagens, { mudou: true, mapa: resultado.vista === "mapa" });
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
  const totalDoPedido = tipo === "arquivo" ? fonte?.totalInformado ?? null : null;
  const opcoes = useMemo(() => bloqueio ? null : montarOpcoes(def, familiaPedida, grupoDe, { quintisDoMapa,
    todosOsEstados: def.nivel === "regioes" ? idsDasRegioes : idsDosGrupos, rotulos: rotulosDoPedido, periodos, totalInformado: totalDoPedido }),
    [def, familiaPedida, bloqueio, grupoDe, quintisDoMapa, idsDosGrupos, idsDasRegioes, rotulosDoPedido, periodos, totalDoPedido]);
  const chave = opcoes ? chaveFonte + "::" + chaveDoPedido(opcoes) : "";
  const fonteMotor: FonteDoMotor | null = useMemo(() => fonte ? { tipo: fonte.tipo, apiBase: fonte.apiBase, datasetVersion: fonte.datasetVersion,
    sheet: fonte.sheet, mapping: fonte.mapping, arquivo: fonte.arquivo, geoVersion: fonte.geoVersion } : null, [fonte]);
  const nomesDoCatalogo = useMemo(() => new Map(municipios.map(item => [item.id, nomeDaUnidade(item)] as [string, string])), [municipios]);
  const lugarDe = useCallback((d: DefinicaoAnalise) => lugarDoUniverso({ nivel: d.nivel, base: d.base, conjuntos: d.conjuntos.length, grupos,
    rotulos, brasil: tipo === "brasil", grupoDe, estados: d.estados, nomes: nomesDoCatalogo, regioes }),
    [grupos, rotulos, tipo, grupoDe, nomesDoCatalogo, regioes]);
  const tituloDe = useCallback((d: DefinicaoAnalise, familia: Familia) => {
    // Na Análise Espacial com a Escolha dos territórios, o lugar do título é o da base da consulta (27/10/2026).
    // Na Análise Espacial e na Rotatividade, os estados como unidade e os conjuntos de estados ficam de fora (comando V22, seção 2): o
    // lugar do título é o do que a análise mede.
    const medido = (familia === "espacial" || familia === "rotatividade") && d.nivel === "municipios" &&
      (d.estados.length > 0 || d.conjuntos.some(conjuntoDeEstados)) ? { ...d, estados: [], conjuntos: d.conjuntos.filter(c => !conjuntoDeEstados(c)) } : d;
    const lugar = familia === "espacial" && medido.consulta ? lugarDaConsulta(medido.consulta, { rotulos, brasil: tipo === "brasil", grupos, nomes,
      selecao: lugarDe(medido) }) : lugarDe(medido);
    // Os tipos de território no desenho (10/11/2026): com conjuntos ou estados como unidade, o subtítulo diz "Cada bolha é um
    // município, um conjunto ou um estado (como unidade)"; só com as unidades, como antes.
    const tipos = medido.nivel === "municipios" ? { unidades: !baseVazia(medido.base), conjuntos: medido.conjuntos.length > 0, estados: medido.estados.length > 0 }
      : emGrupos(medido.nivel) ? { unidades: medido.estados.length > 0 || !medido.conjuntos.length, conjuntos: medido.conjuntos.length > 0, estados: false } : null;
    return tituloDaAnalise({ fonte: tipo, familia, visao: visaoEfetiva(d), indicador: d.indicador, nivel: d.nivel, categoria: d.categoria,
      competencia: d.competencia, janela: d.janela, rotatividade: d.rotatividade, lugar, rotulos, tipos,
      serie: familia === "tendencia" && d.visao === "series" ? intervaloDaSerie(d, periodos) : undefined });
  }, [tipo, lugarDe, rotulos, nomes, periodos, grupos]);

  // Histórico: a restauração roda antes do pedido ao motor, para a resposta guardada entrar no cache antes; assim, reabrir
  // uma análise igual ao estado inicial (os estados) não pede de novo. A vista e a cor do mapa voltam como foram guardadas (um
  // estado de antes delas reabre no gráfico).
  const ultimoRestaurado = useRef<EstadoSalvo | null>(null);
  useEffect(() => {
    if (!restaurar || restaurar === ultimoRestaurado.current || !pronto || iniciado.current !== chaveFonte) return;
    ultimoRestaurado.current = restaurar;
    const lido = lerEstadoSalvo(restaurar);
    if (!lido) {
      setAviso("Não foi possível reabrir esta análise: o estado salvo não tem a forma esperada.");
      restauradoRef.current?.(false);
      return;
    }
    registrar("Reabrir uma análise do Histórico");
    reiniciarVisual();
    setEscala(lido.visual.escala); setCorte(lido.visual.corte); setSelecionados(lido.visual.selecionados);
    setVistaEscolhida(lido.visual.vista ?? "grafico");
    setDef({ ...lido.definicao, ...unificarEscolha(escolhaDe(lido.definicao), arvore) });
    setAba(semTerritorios(lido.definicao) ? "territorios" : lido.definicao.familia);
    if (lido.resposta && lido.opcoes) {
      cache.current.set(lido.chave, lido.resposta);
      setResposta(lido.resposta);
      setCalculado({ chave: lido.chave, def: lido.definicao, familia: lido.familia, opcoes: lido.opcoes });
    }
    setAviso("Análise reaberta do Histórico, sem recalcular.");
    restauradoRef.current?.(true);
  }, [restaurar, pronto, chaveFonte]);

  useEffect(() => {
    if (!fonteMotor || !opcoes) {
      setCarregando(false);
      // Sem territórios escolhidos, nada da seleção anterior fica à vista (nem gráfico, nem mapa, nem frase-resumo).
      if (fonteMotor && pronto && semTerritorios(def)) { setResposta(null); setCalculado(null); setErro(null); }
      return;
    }
    if (calculado?.chave === chave) { setCarregando(false); setErro(null); return; }
    const emCache = cache.current.get(chave);
    if (emCache) {
      // A memória das respostas guarda as mais recentemente usadas (05/11/2026): reaproveitar renova a entrada, e o limite descarta
      // a usada há mais tempo (antes, a inserida há mais tempo, mesmo que tivesse acabado de ser reaproveitada).
      cache.current.delete(chave); cache.current.set(chave, emCache);
      setResposta(emCache); setCalculado({ chave, def, familia: familiaPedida, opcoes }); setErro(null); setCarregando(false);
      return;
    }
    const controle = new AbortController(), pedidoDef = def, pedidoFamilia = familiaPedida, pedidoOpcoes = opcoes;
    let cancelarRepeticao: (() => void) | undefined;
    setCarregando(true);
    setErro(null);
    const timer = window.setTimeout(() => {
      pedirPainel(fonteMotor, pedidoOpcoes, controle.signal)
        .then(corpo => {
          if (controle.signal.aborted) return;
          repeticoesOcupado.current.delete("painel:" + chave);
          cache.current.set(chave, corpo);
          while (cache.current.size > MAX_CACHE) cache.current.delete(cache.current.keys().next().value as string);
          setResposta(corpo);
          setCalculado({ chave, def: pedidoDef, familia: pedidoFamilia, opcoes: pedidoOpcoes });
          // Histórico: cada cálculo guarda o estado, que reabre sem recalcular.
          const visual = visualRef.current;
          salvarRef.current(salvarEstado(tituloDe(pedidoDef, pedidoFamilia).titulo, { chave, familia: pedidoFamilia, opcoes: pedidoOpcoes,
            definicao: pedidoDef, visual: { escala: visual.escala, corte: null, selecionados: visual.selecionados, vista: visual.vista,
              corContinua: visual.corContinua } }, corpo));
        })
        .catch((exc: unknown) => {
          if (controle.signal.aborted) return;
          cancelarRepeticao = repetirSeOcupado(exc, "painel:" + chave, () => setTentativa(valor => valor + 1));
          setErro({ mensagem: exc instanceof Error ? exc.message : "Não foi possível montar o gráfico.",
            pendencia: exc instanceof ErroDoMotor ? exc.pendencia : null, chave, repetindo: !!cancelarRepeticao });
        })
        .finally(() => { if (!controle.signal.aborted) setCarregando(false); });
    }, 150);
    return () => { controle.abort(); window.clearTimeout(timer); cancelarRepeticao?.(); };
  }, [chave, tentativa]);

  // Os números do lugar em uso (06/11/2026): a faixa e as linhas do todo e do grupo, do motor (POST /api/painel/lugar), à parte
  // do gráfico: trocar o "Ver por" não os pede de novo. Na competência da análise; a variação, desde o primeiro dos últimos 4
  // períodos anuais; na Série temporal, também os valores das competências dela. Desde 07/11/2026 (item 1.4 do comando), também
  // numa planilha: o todo e o grupo pelas unidades, com as escolhas do painel Colunas.
  const competenciaDaFaixa = opcoes?.competencia ?? def.competencia;
  const pedidoDoLugar: LugarOpcoes | null = useMemo(() => {
    if (!fonte || !pronto || !tipo || lugar.tipo === "nenhum" || !competenciaDaFaixa) return null;
    if (tipo === "arquivo" && !opcoes) return null;
    const desde = desdeDaFaixa(periodos, competenciaDaFaixa);
    // No grupo de cima (07/11/2026), os números dele, pelas unidades.
    return { competencia: competenciaDaFaixa, categoria: def.categoria, ...(lugar.grupo ? { grupo: lugar.grupo } : {}),
      ...(lugar.tipo === "regiao" && lugar.regiao ? { regiao: lugar.regiao } : {}),
      ...(desde ? { desde } : {}), ...(opcoes?.serie ? { serie: opcoes.serie } : {}),
      ...(tipo === "arquivo" && opcoes ? { ...(opcoes.premissas ? { premissas: opcoes.premissas } : {}),
        ...(opcoes.total_informado ? { total_informado: opcoes.total_informado } : {}),
        ...(opcoes.rotulos ? { rotulos: opcoes.rotulos } : {}) } : {}) };
  }, [fonte, pronto, tipo, lugar.tipo, lugar.grupo, lugar.regiao, competenciaDaFaixa, def.categoria, periodos, opcoes?.serie, opcoes?.premissas, opcoes?.rotulos,
    opcoes?.total_informado]);
  const chaveDoLugar = pedidoDoLugar ? chaveFonte + "::" + JSON.stringify(pedidoDoLugar) : "";
  // Sem a série, a mesma faixa: trocar de aba (a Série temporal pede a série) mantém os números à vista enquanto chega o pedido novo.
  const baseDoLugar = pedidoDoLugar ? chaveFonte + "::" + JSON.stringify({ ...pedidoDoLugar, serie: undefined }) : "";
  useEffect(() => {
    if (!fonteMotor || !pedidoDoLugar) { setCarregandoLugar(false); return; }
    const emCache = cacheLugar.current.get(chaveDoLugar);
    if (emCache) { setNumerosDoLugar({ chave: chaveDoLugar, base: baseDoLugar, dados: emCache }); setErroLugar(null); setCarregandoLugar(false); return; }
    const controle = new AbortController(), chavePedida = chaveDoLugar, basePedida = baseDoLugar, pedidoFeito = pedidoDoLugar;
    setCarregandoLugar(true);
    setErroLugar(null);
    const timer = window.setTimeout(() => {
      pedirLugar(fonteMotor, pedidoFeito, controle.signal)
        .then(dados => {
          if (controle.signal.aborted) return;
          cacheLugar.current.set(chavePedida, dados);
          while (cacheLugar.current.size > MAX_CACHE) cacheLugar.current.delete(cacheLugar.current.keys().next().value as string);
          setNumerosDoLugar({ chave: chavePedida, base: basePedida, dados });
        })
        .catch((exc: unknown) => {
          if (controle.signal.aborted) return;
          setErroLugar({ chave: chavePedida, mensagem: exc instanceof Error ? exc.message : "Não foi possível obter os números do lugar." });
        })
        .finally(() => { if (!controle.signal.aborted) setCarregandoLugar(false); });
    }, 150);
    return () => { controle.abort(); window.clearTimeout(timer); };
  }, [chaveDoLugar]);
  const numerosNaFaixa = numerosDoLugar && (numerosDoLugar.chave === chaveDoLugar || numerosDoLugar.base === baseDoLugar) ? numerosDoLugar.dados : null;
  const erroNaFaixa = erroLugar && erroLugar.chave === chaveDoLugar ? erroLugar.mensagem : null;

  // A proteção (06/11/2026, item 4.6 do comando): o resultado à vista é de outra seleção — o cálculo da seleção em uso ainda não
  // chegou (depois de um instante, para não piscar a cada mudança) ou falhou. A aba diz de que lugar ele é, com "Atualizar", e o
  // desenho fica esmaecido, em vez de exibi-lo como atual.
  const outraSelecao = !!calculado && !!resposta && calculado.chave !== chave && !!chave &&
    JSON.stringify(escolhaDe(calculado.def)) !== JSON.stringify(escolhaDe(def));
  const [demorou, setDemorou] = useState(false);
  useEffect(() => {
    setDemorou(false);
    if (!outraSelecao || !carregando) return;
    const timer = window.setTimeout(() => setDemorou(true), 700);
    return () => window.clearTimeout(timer);
  }, [outraSelecao, carregando, chave]);
  const falhouAAtual = !!erro && (!erro.chave || erro.chave === chave);
  const desatualizada = outraSelecao && (demorou || falhouAAtual);
  const deOndeEhOCalculado = desatualizada && calculado ? deOndeEhOResultado(lugarDaTrilha(escolhaDe(calculado.def),
    { arvore, nomeDoTodo: nomeDoTodo(tipo !== "arquivo", rotulos), nomes, comGrupos: comBolhasDeGrupo }),
    { grupos, brasil: tipo === "brasil", rotulos }) : "";

  function voltarAoCalculado() {
    if (!calculado) return;
    registrar("Voltar ao último gráfico calculado");
    setDef(calculado.def);
    setAviso("De volta ao último gráfico calculado.");
  }

  // ------------------------------------------------------------------------------------------ confirmação dos pedidos da conversa
  // Desde 05/11/2026, cada pedido da conversa tem um desfecho, informado à página (onDesfecho) quando a área de fato o mostra: o
  // motor calculou a definição que resultou do pedido (e os pontos do mapa chegaram, quando o mapa foi pedido), ou o que impediu
  // (a parte recusada pela área, o que falta para o cálculo, a falha do motor, outra mudança que tomou o lugar dele). A conversa só
  // diz "Mostrei" ou "Ordenei" com o desfecho "concluido". O desfecho é conferido depois do render com as mudanças do pedido e com
  // a área estável (a definição e a interação iguais em dois renders seguidos), para nunca valer o estado de antes dele.
  const execucao = useRef<{ id: number; mensagens: string[]; mudou: boolean; mapa: boolean; semCalculo: boolean; manuais: number;
    render: number; lugar: { parte: ParteDaTrilha; escolha: Escolha } | null } | null>(null);
  // O destaque pedido pela resposta de valor da conversa (06/11/2026, item 4.2): os lugares citados, em destaque no gráfico em uso
  // enquanto a análise não muda (a chave do pedido ao motor). Estado visual: nada é recalculado.
  const [realce, setRealce] = useState<{ ids: string[]; chave: string } | null>(null);
  // Os grupos em tela estreita (06/11/2026, item 7 do comando): vendo por estado no celular, o padrão é a lista ordenada pelo motor;
  // um controle troca para as bolhas. Estado visual: nada é recalculado.
  const estreita = useNarrow();
  const [vistaDosGrupos, setVistaDosGrupos] = useState<"lista" | "bolhas">("lista");
  // O foco da Análise Espacial (comando V22, seção 7): a base em foco, com a referência dela, a ligação e a distância exata; as
  // demais relações esmaecem. Estado visual: nada é pedido ao motor nem recalculado.
  const [focoEspacial, setFocoEspacial] = useState<string | null>(null);
  // As regiões abertas na árvore da Seleção (comando V22): guardadas aqui, porque a aba desmonta o painel.
  const [regioesAbertas, setRegioesAbertas] = useState<string[]>([]);
  const renders = useRef(0);
  renders.current += 1;
  const visto = useRef("");
  const [, setRelogioDaExecucao] = useState(0);
  const [ultimoDesfecho, setUltimoDesfecho] = useState<{ id: number; situacao: SituacaoDoPedido } | null>(null);
  const desfechoRef = useRef(props.onDesfecho); desfechoRef.current = props.onDesfecho;
  const restauradoRef = useRef(props.onRestaurado); restauradoRef.current = props.onRestaurado;
  /** Começa a esperar o desfecho de um pedido aplicado agora; o que ainda esperava foi substituído por este. */
  function iniciarExecucao(id: number, mensagens: string[], c: { mudou: boolean; mapa: boolean; semCalculo?: boolean;
    lugar?: { parte: ParteDaTrilha; escolha: Escolha } | null }) {
    if (execucao.current) informarDesfecho("substituido", ["Um pedido novo da conversa tomou o lugar deste antes de ele terminar."]);
    execucao.current = { id, mensagens: [...mensagens], mudou: c.mudou, mapa: c.mapa, semCalculo: !!c.semCalculo,
      manuais: manuais.current, render: renders.current, lugar: c.lugar ?? null };
    setRelogioDaExecucao(valor => valor + 1);
  }
  /** Informa o desfecho do pedido em curso, com o que está na tela agora (o título e, com o cálculo à vista, o resultado). */
  function informarDesfecho(situacao: SituacaoDoPedido, mensagens: string[]) {
    const em = execucao.current;
    if (!em) return;
    execucao.current = null;
    const calculou = situacao === "concluido" || situacao === "parcial";
    desfechoRef.current?.({ id: em.id, situacao, mensagens: [...new Set(mensagens.filter(Boolean))], titulo,
      resultado: calculou ? resposta?.sessao?.resultId ?? null : null, execucao: calculou ? resposta?.chave_execucao ?? null : null,
      semTerritorios: situacao === "pendente" && semTerritorios(def) });
    setUltimoDesfecho({ id: em.id, situacao });
  }

  // ------------------------------------------------------------------------------------------ comando da conversa e Histórico
  useEffect(() => {
    if (!pedido || pedido.id === ultimoPedido.current) return;
    if (!pronto || iniciado.current !== chaveFonte) { pedidoPendente.current = pedido; return; }
    ultimoPedido.current = pedido.id;
    const { explicar, destacar, criterios: criteriosDoChat, ...resto } = pedido.pedido;
    setRealce(null);
    // Selecionar por critérios pela conversa (07/11/2026, item 6.9 do comando): o painel da Seleção abre preenchido, com a prévia do
    // motor; nada muda na análise até a pessoa escolher no painel ("Usar como seleção" ou "Usar cada conjunto como um território").
    if (criteriosDoChat) {
      setAba("territorios");
      setCriterios(atual => ({ inicial: criteriosDoChat, previa: true, n: (atual?.n ?? 0) + 1 }));
      setAcaoSelecao("criterios");
      iniciarExecucao(pedido.id, [], { mudou: true, mapa: false, semCalculo: true });
      return;
    }
    // O destaque da resposta de valor (06/11/2026, item 4.2): os lugares citados que estão no gráfico em uso ficam em destaque, sem
    // mudar a análise; sem nenhum deles no gráfico, nada é destacado, e a resposta diz isso.
    if (destacar && !explicar && !Object.values(resto).some(valor => valor !== undefined && valor !== null)) {
      const presentes = destacar.ids.filter(id => idsNaTela.includes(id));
      if (presentes.length) setRealce({ ids: presentes, chave });
      iniciarExecucao(pedido.id, presentes.length ? [] : ["O lugar citado não está no gráfico em uso; nada foi destacado."],
        { mudou: presentes.length > 0, mapa: false, semCalculo: true });
      return;
    }
    if (explicar) {
      // Explicação pedida na conversa: abre "Entenda esta análise" na aba e destaca os termos; não muda o gráfico.
      const termos = explicar.termos.map(codigo => CLASSES_TENDENCIA.find(classe => classe.codigo === codigo)?.rotulo)
        .filter((rotulo): rotulo is string => !!rotulo);
      if (def.familia === explicar.aba) setAba(explicar.aba);
      setExplicacaoPedida({ n: ++explicacoesPedidas, aba: explicar.aba, termos });
      if (!Object.values(resto).some(valor => valor !== undefined && valor !== null)) {
        iniciarExecucao(pedido.id, [], { mudou: true, mapa: false, semCalculo: true });
        return;
      }
    }
    const resultado = aplicarPedido(def, pedido.pedido, { periodos, nomes, temGrupos: comBolhasDeGrupo, disponivel: disponivelDe, grupoDe, mapa: mapaDe,
      todosOsEstados: idsDosGrupos, temBrasil: todoPorGrupo, unidadesDoGrupo: arvore.unidadesDoGrupo,
      todasAsRegioes: comRegioes ? idsDasRegioes : [], gruposDaRegiao: regiao => gruposDaRegiao(regiao, arvore) });
    if (!temPopulacao && pedido.pedido.indicador === "densidade") { resultado.definicao.indicador = "quantidade"; resultado.mensagens.push(TEXTO_SEM_POPULACAO); }
    // A árvore mostra o que está na análise (05/11/2026): os estados ou o Brasil pedidos ficam marcados nela.
    resultado.definicao = { ...resultado.definicao, ...unificarEscolha(escolhaDe(resultado.definicao), arvore) };
    // O pedido da conversa também é um passo do Desfazer (24/10/2026): Desfazer devolve o que estava antes dele.
    registrar(ROTULO_DO_PEDIDO);
    // A comparação pedida na conversa vale como veio; a de antes só continua com os itens dela na análise (com a Escolha dos
    // territórios pedida na conversa, 28/10/2026, a base é a da consulta, e a comparação de antes sai).
    if (pedido.pedido.funcao !== "comparar" && !(pedido.pedido.consulta && resultado.definicao.consulta))
      resultado.definicao.comparar = comparacaoQueContinua(def, resultado.definicao, grupoDe);
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
    if (emGrupos(resultado.definicao.nivel)) setAberto(null);
    // "Ver no mapa" e "volte ao gráfico": estado visual. O mapa que só passa a existir com o pedido (os municípios de um estado)
    // abre sem a troca animada; o que já existia, com ela. Ao abrir a tendência pela conversa, o gráfico, como pelo clique na aba.
    if (resultado.vista === "grafico" || (!resultado.vista && resultado.definicao.familia === "tendencia" && def.familia !== "tendencia"))
      trocarVista("grafico", false, false);
    else if (resultado.vista === "mapa" && vistaExibida === "grafico") {
      if (mapa.disponivel) trocarVista("mapa", false, false);
      else setVistaEscolhida("mapa");
    }
    setAviso(["Pedido da conversa aplicado ao gráfico.", ...resultado.mensagens].join(" "));
    // O que o pedido mudou na área (a definição, a marcação, um painel, a vista ou a aba): sem nada disso e com motivos, ele foi
    // recusado por inteiro.
    const mudou = JSON.stringify(resultado.definicao) !== JSON.stringify(def) || !!resultado.selecao || !!resultado.abrir ||
      !!resultado.criterio || !!resultado.vista || !!explicar || (!!abaDoPedido && abaDoPedido !== aba);
    // O pedido que leva a um lugar (06/11/2026, item 4.4): o lugar da trilha que ele deve deixar na tela, conferido no desfecho.
    const escolhaPedida = escolhaDe(resultado.definicao);
    const partePedida = pedido.pedido.municipios || pedido.pedido.nivel ? lugarDaTrilha(escolhaPedida, { arvore,
      nomeDoTodo: nomeDoTodo(tipo !== "arquivo", rotulos), nomes, comGrupos: comBolhasDeGrupo }).partes.find(parte => parte.atual) ?? null : null;
    iniciarExecucao(pedido.id, resultado.mensagens, { mudou, mapa: resultado.vista === "mapa",
      lugar: partePedida ? { parte: partePedida, escolha: escolhaPedida } : null });
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
  // Escolha dos territórios (27/10/2026): a referência é a mais próxima de cada item. O resultado à vista é o da consulta calculada
  // quando não há cálculo em curso nem erro (a janela diz "Resultado em dia com a consulta.").
  const referenciaPorItem = distanciaNaTela && resposta?.referencia?.tipo === "consulta";
  const consultaNaTela = referenciaPorItem && !carregando && !erro && mesmaConsulta(calculado?.def.consulta, def.consulta);
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

  // Vista do desenho e mapa. Vendo por estado (06/11/2026), cada estado é uma bolha no ponto de desenho do motor; a planilha
  // precisa de latitude e longitude; a Série temporal é só do gráfico. "Lado a lado" só com a janela larga; ao estreitar, volta ao
  // mapa.
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
  // Vendo por estado, o pedido do mapa leva `grupos`: o ponto de desenho de cada estado, do motor (06/11/2026).
  // Os pontos de desenho dos estados também com os estados como unidade junto dos municípios (comando V22): cada estado da seleção
  // fica no ponto dele, e os conjuntos de estados contornam os estados membros.
  const gruposNoMapa = tipo === "brasil" && (def.nivel === "estados" || (def.nivel === "municipios" &&
    (def.estados.length > 0 || def.conjuntos.some(conjuntoDeEstados))));
  const chaveMapa = fonte && competenciaDoMapa ? chaveFonte + "::" + JSON.stringify([competenciaDoMapa, categoriaDoMapa, tipo === "arquivo" ? def.premissas : {},
    gruposNoMapa]) : "";
  const dadosAtuais = dadosDoMapa?.dados ?? null;
  const dadosConferem = !!dadosDoMapa && dadosDoMapa.chave === chaveMapa;
  // Vendo por estado (06/11/2026): os pontos de desenho dos estados entram no mapa junto das sedes (que ficam de fundo); a nota e os
  // nomes do mapa falam dos estados.
  const estadosNoMapa = resposta?.nivel === "estados" && !!dadosAtuais?.grupos;
  // Níveis na mesma seleção (comando V22): os estados da resposta entram no mapa, cada um no ponto de desenho dele; os nomes e a nota
  // continuam os dos municípios.
  const estadosJuntosNoMapa = !estadosNoMapa && !!resposta?.niveis?.includes("estados") && !!dadosAtuais?.grupos;
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
  // Base e referência da Análise Espacial (25/10/2026, pedido do responsável): cada território da base aparece ligado à referência
  // mais próxima dele no gráfico (a referência como bolha de contexto, no 0 km) e no mapa. Desde a Escolha dos territórios
  // (27/10/2026), a base é a da consulta, calculada pelo motor: toda unidade da resposta é da base. Clicar numa bolha continua só
  // marcando.
  const basesDaReferencia = useMemo(() => resposta ? basesPossiveis(resposta.itens) : [], [resposta]);
  const idsDasBases = useMemo(() => basesDaReferencia.map(base => base.id), [basesDaReferencia]);
  // Os conjuntos da base também são territórios-base na Análise Espacial (comando V22, seções 6 e 7): a referência e a distância pelo
  // membro mais próximo, com a ligação, o foco e a contagem da base.
  const idsDosConjuntosDaBase = useMemo(() => resposta ? resposta.itens.filter(item => item.tipo === "conjunto" && !item.referencia)
    .map(item => item.id) : [], [resposta]);
  const pares = useMemo(() => distanciaNaTela && resposta ? paresDasBases(resposta, [...idsDasBases, ...idsDosConjuntosDaBase], true) : [],
    [distanciaNaTela, resposta, idsDasBases, idsDosConjuntosDaBase]);
  // As ligações do gráfico: das bases à vista (dentro da régua e dos filtros), as marcadas primeiro, até MAX_LIGACOES.
  const paresLigados = useMemo(() => {
    const aVista = new Set(visiveis.map(item => item.id)), marcadas = new Set(selecao);
    return pares.filter(par => par.referencias.length > 0 && aVista.has(par.base.id))
      .sort((a, b) => Number(marcadas.has(b.base.id)) - Number(marcadas.has(a.base.id))).slice(0, MAX_LIGACOES);
  }, [pares, visiveis, selecao]);
  // Destaque da análise (26/10/2026): com a comparação em exibição, só os comparados ficam inteiros no gráfico de bolhas. As demais
  // bolhas esmaecem. Com o foco da Análise Espacial (comando V22), a base em foco e a referência dela.
  const parDoFoco = focoEspacial && distanciaNaTela ? pares.find(par => par.base.id === focoEspacial) ?? null : null;
  useEffect(() => { if (focoEspacial && !parDoFoco) setFocoEspacial(null); }, [focoEspacial, parDoFoco]);
  const destaque = useMemo(() => parDoFoco ? [parDoFoco.base.id, ...parDoFoco.referencias.map(ref => ref.id)]
    : destaqueDaAnalise(def.comparar, new Set((resposta?.itens || []).map(item => item.id))), [def.comparar, resposta, parDoFoco]);
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
  const { titulo, subtitulo } = tituloDe(def, familiaPedida);
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

  // O desfecho do pedido da conversa em curso (05/11/2026), conferido a cada render: só depois do render com as mudanças do pedido
  // e com a área estável; antes do fim, uma mudança feita na área toma o lugar dele. O erro do motor e o do mapa só valem para o
  // pedido em exibição e esperam a nova tentativa automática do ocupado; sem os pontos do mapa pedido, o desfecho é "parcial".
  const estabilidade = instantaneo + "|" + chave + "|" + vistaExibida;
  useEffect(() => {
    const em = execucao.current;
    if (!em || renders.current <= em.render) return;
    if (visto.current !== estabilidade) { visto.current = estabilidade; setRelogioDaExecucao(valor => valor + 1); return; }
    if (manuais.current !== em.manuais) {
      informarDesfecho("substituido", ["Outra mudança feita na área de análise tomou o lugar do pedido antes de ele terminar."]);
      return;
    }
    if (!em.mudou && em.mensagens.length) { informarDesfecho("recusado", em.mensagens); return; }
    if (em.semCalculo) { informarDesfecho("concluido", em.mensagens); return; }
    if (bloqueio) { informarDesfecho("pendente", [...em.mensagens, bloqueio]); return; }
    if (carregando) return;
    if (erro && (!erro.chave || erro.chave === chave)) {
      if (!erro.repetindo) informarDesfecho("falhou", [...em.mensagens, erro.mensagem]);
      return;
    }
    if (!calculado || calculado.chave !== chave) return;
    // A confirmação conferida (06/11/2026, item 4.4): o pedido que leva a um lugar só é concluído com o resultado em tela desse
    // lugar — a trilha e os itens do gráfico; senão, o desfecho diz o que faltou, e o pedido não fica como concluído.
    if (em.lugar) {
      const falta = lugarConfere(em.lugar, lugarDaTrilha(escolhaDe(calculado.def), { arvore, nomeDoTodo: nomeDoTodo(tipo !== "arquivo", rotulos),
        nomes, comGrupos: comBolhasDeGrupo }), resposta?.itens ?? [], grupoDe);
      if (falta) { informarDesfecho("parcial", [...em.mensagens, falta]); return; }
    }
    // O mapa pedido fica à vista, mas sem os pontos (o motor os recusou): o pedido foi feito só em parte, com o motivo.
    if (em.mapa && mapaNaTela) {
      if (erroDoMapa) {
        if (!erroDoMapa.repetindo) informarDesfecho("parcial", [...em.mensagens, "Mapa: " + erroDoMapa.mensagem]);
        return;
      }
      if (!dadosConferem) return;
    }
    informarDesfecho(em.mensagens.length ? "parcial" : "concluido", em.mensagens);
  });

  // Os mini mapas da Seleção (07/11/2026, item 7 do comando de 07/11/2026) usam as mesmas coordenadas do mapa. Desde o comando V22, o
  // mapa da seleção fica sempre no painel direito: os pontos vêm com o primeiro território selecionado ou com os critérios e o
  // agrupamento abertos; sem seleção, nada é pedido ao motor.
  const querMapaNaSelecao = aba === "territorios" && (acaoSelecao !== "lista" || !semSelecao(def));
  const querMapa = !!fonteMotor && !!chaveMapa && mapa.disponivel && (mapaNaTela || querMapaNaSelecao ||
    (resposta?.nivel === "municipios" && plotaveis.length > 0));
  useEffect(() => {
    if (!querMapa || !fonteMotor) { setCarregandoMapa(false); return; }
    const emCache = cacheMapa.current.get(chaveMapa);
    if (emCache) { setDadosDoMapa({ chave: chaveMapa, dados: emCache }); setErroMapa(null); setCarregandoMapa(false); return; }
    const controle = new AbortController(), chavePedida = chaveMapa;
    // Nas planilhas, as premissas e os rótulos vão como no gráfico; na base do Brasil, o motor recusa os dois.
    const pedidoMapa: MapaOpcoes = { competencia: competenciaDoMapa, categoria: categoriaDoMapa,
      ...(tipo === "arquivo" && Object.keys(def.premissas).length ? { premissas: def.premissas } : {}),
      ...(tipo === "arquivo" && fonte?.rotulos ? { rotulos: fonte.rotulos } : {}), ...(gruposNoMapa ? { grupos: true } : {}) };
    let cancelarRepeticao: (() => void) | undefined;
    setCarregandoMapa(true);
    setErroMapa(null);
    pedirMapa(fonteMotor, pedidoMapa, controle.signal)
      .then(dados => {
        if (controle.signal.aborted) return;
        repeticoesOcupado.current.delete("mapa:" + chavePedida);
        cacheMapa.current.set(chavePedida, dados);
        while (cacheMapa.current.size > MAX_CACHE) cacheMapa.current.delete(cacheMapa.current.keys().next().value as string);
        setDadosDoMapa({ chave: chavePedida, dados });
      })
      .catch((exc: unknown) => {
        if (controle.signal.aborted) return;
        cancelarRepeticao = repetirSeOcupado(exc, "mapa:" + chavePedida, () => setTentativaMapa(valor => valor + 1));
        setErroMapa({ chave: chavePedida, mensagem: exc instanceof Error ? exc.message : "Não foi possível obter os pontos do mapa.",
          pendencia: exc instanceof ErroDoMotor ? exc.pendencia : null, repetindo: !!cancelarRepeticao });
      })
      .finally(() => { if (!controle.signal.aborted) setCarregandoMapa(false); });
    return () => { controle.abort(); cancelarRepeticao?.(); };
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
    // A Escolha dos territórios abre ao entrar na Análise Espacial sem consulta calculada (27/10/2026): desde 06/11/2026, a base é a
    // seleção em uso, e a janela escolhe a referência (até essa data, a base podia partir do país, de regiões ou de estados).
    if (familia === "espacial" && !def.consulta && def.nivel === "municipios") abrirPainel("referencia");
    else if (painel === "referencia" && familia !== "espacial") setPainel(null);
    if (disponivel.pendente) setAviso(NOMES_FAMILIAS[familia] + ": " + disponivel.motivo);
  }
  function teclasAbas(event: KeyboardEvent<HTMLButtonElement>, indice: number) {
    const proxima = event.key === "ArrowRight" ? (indice + 1) % ABAS.length : event.key === "ArrowLeft" ? (indice + ABAS.length - 1) % ABAS.length
      : event.key === "Home" ? 0 : event.key === "End" ? ABAS.length - 1 : null;
    if (proxima === null) return;
    event.preventDefault();
    document.getElementById(idDaAba(ABAS[proxima]))?.focus();
  }
  /** Com as unidades à vista, a análise espacial que esperava por elas pede a Escolha dos territórios. */
  function pedirOQueFalta() {
    if (def.familia === "espacial" && !def.consulta && disponivelDe("espacial").disponivel) abrirPainel("referencia");
  }
  /** Mudança feita na Seleção de Territórios: o nível em análise e a escolha de cada nível. Cada uma é um passo do Desfazer; a
   * coletiva (muitos de uma vez) também aparece por escrito junto do que está marcado. */
  function mudarEscolha(parte: Partial<Escolha>, rotulo: string) {
    registrar(rotulo);
    const proxima = { ...escolhaDe(def), ...parte };
    if (nivelDaSelecao(proxima) !== def.nivel) setSelecionados([]);
    trocarEscolha(proxima);
    setCorte(null);
  }
  /** A escolha nova, com o nível que ela pede (comando V22: só estados como unidade é o nível estados; com municípios, o nível
   * municipios, com os estados à parte) e a comparação só enquanto os itens dela continuam na análise. */
  function trocarEscolha(escolha: Escolha) {
    const proxima = { ...escolha, nivel: nivelDaSelecao(escolha) };
    mudar({ ...proxima, comparar: comparacaoQueContinua(def, proxima, grupoDe) });
  }
  /** "Ver os municípios destes estados" (a Análise Espacial com só estados como unidade): os municípios deles, inteiros, no lugar
   * deles. Um passo do Desfazer. */
  function verUnidadesDosEstados() {
    if (!def.estados.length) return;
    const grupos = def.nivel === "regioes" ? def.estados.flatMap(regiao => gruposDaRegiao(regiao, arvore)) : def.estados;
    mudarEscolha({ nivel: "municipios", base: normalizarArvore({ todos: false, estados: [...grupos], ids: [] }, arvore), estados: [],
      conjuntos: def.conjuntos.filter(conjunto => !conjuntoDeEstados(conjunto)) },
    "Ver " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " " + (grupos.length === 1 ? "de " + (grupos.find(Boolean) ?? "") : "destes " +
      (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural));
    pedirOQueFalta();
  }
  /** Uma mudança na árvore da Seleção de Territórios: a escolha nova, normalizada (comando V22: os estados como unidade ficam à
   * parte, e os municípios deles não entram). Marcar o Brasil marca os municípios (os estados que estão como unidade continuam). */
  function mudarArvore(base: PainelMunicipios, acao: string) {
    mudarEscolha(escolhaDaArvore(escolhaDe(def), base, arvore), acao);
  }
  /** "Só o estado" e "Só os estados" (comando V22, decisão 3): os estados entram na seleção como unidade, e os municípios deles saem,
   * num só passo do Desfazer; desligar tira o estado e deixa os municípios livres, sem nenhum marcado. Um conjunto de municípios com
   * membros no estado impede, com o aviso (o conjunto seria somado ao estado). */
  function estadosComoUnidade(gruposPedidos: string[], ativar: boolean, acao: string) {
    if (ativar) {
      const comMembros = conjuntosComMembrosNos(def.conjuntos, gruposPedidos, grupoDe);
      if (comMembros.length) {
        setAviso("Não foi possível pôr como unidade: " + comMembros.map(conjunto => conjunto.rotulo).join(", ") + " tem membros " +
          (gruposPedidos.length === 1 ? "nesse " : "nesses ") + (gruposPedidos.length === 1 ? (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular
            : (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural) + ". Desfaça o conjunto antes (o estado inteiro não é somado aos municípios dele).");
        return;
      }
      mudarEscolha(ativarEstados(escolhaDe(def), gruposPedidos, arvore), acao);
    } else mudarEscolha(desativarEstados(escolhaDe(def), gruposPedidos), acao);
  }
  /** "Só a zona", numa planilha com dois níveis: o grupo de cima como unidade, sozinho (não se mistura com outros níveis). */
  function regioesComoUnidade(regioesPedidas: string[], ativar: boolean, acao: string) {
    mudarEscolha(ativar ? ativarRegioes(escolhaDe(def), regioesPedidas) : desativarRegioes(escolhaDe(def), regioesPedidas), acao);
  }
  /** Limpar seleção (24/10/2026, controle global, no alto): desde 05/11/2026, com a seleção unificada, tira a seleção inteira (a
   * árvore, os estados como unidades, o Brasil inteiro e os conjuntos; limparEscolha), e a unidade volta aos municípios, sem apagar a
   * base carregada nem os ajustes das análises (até 05/11/2026, decisão 5 de 25/10/2026, só a escolha do nível em uso). Os desenhos
   * que dependem da seleção saem, e a comparação sai com os itens. É um passo do Desfazer. */
  const selecaoLimpa = limparEscolha(escolhaDe(def));
  const temSelecaoParaLimpar = selecaoLimpa !== null;
  function limparSelecao() {
    if (!selecaoLimpa) return;
    registrar("Limpar seleção");
    trocarEscolha(selecaoLimpa);
    setSelecionados([]); setCorte(null); setSoAtende(false); setFiltroClasse(null);
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
  // ------------------------------------------------------------------------------------------ selecionar por critérios
  // Selecionar por critérios (07/11/2026, item 6 do comando de 06/11/2026; decisão 4): o painel da Seleção, com a prévia do motor; só
  // "Usar como seleção" ou "Usar cada conjunto como um território" muda a análise (um passo do Desfazer). A regra fica com a seleção que
  // ela produziu: a trilha, o método e os Detalhes a mostram enquanto a seleção for a dela.
  function usarCriterios(previa: RespostaCriterios, pedido: RegraDaSelecao["pedido"], uso: UsoDosCriterios) {
    // Comando V22 (seção 4): o resultado entra no lugar da seleção atual (o padrão: os estados como unidade e os conjuntos de antes
    // saem, como dito no rodapé) ou junto com ela; junto, os municípios de um estado como unidade e os membros de um conjunto da
    // seleção não entram, e o aviso diz quantos ficaram de fora e por quê. Os conjuntos por proximidade saíram daqui (seção 5).
    const membrosDeConjuntos = new Set(def.conjuntos.flatMap(conjunto => conjunto.membros));
    const unidadesDosEstados = new Set(uso.junto ? def.estados : []);
    const doEstado = uso.junto ? previa.ids.filter(id => unidadesDosEstados.has(grupoDe(id))) : [];
    const doConjunto = uso.junto ? previa.ids.filter(id => !unidadesDosEstados.has(grupoDe(id)) && membrosDeConjuntos.has(id)) : [];
    const fora = new Set([...doEstado, ...doConjunto]);
    const ids = previa.ids.filter(id => !fora.has(id));
    const base = uso.junto ? baseSemOsEstados(baseComUnidades(def.base, ids, contextoDaBase), def.estados, arvore)
      : normalizarArvore({ todos: false, estados: [], ids }, arvore);
    const texto = previa.regra.texto;
    const regra: RegraDaSelecao | null = uso.junto ? null : { texto, competencia: previa.competencia, total: previa.atendem, base, conjuntos: [],
      pedido: { ...pedido, agrupar: null } };
    registrar("Selecionar por critérios: " + texto);
    mudar({ nivel: "municipios", base, estados: uso.junto ? def.estados : [], conjuntos: uso.junto ? def.conjuntos : [], comparar: [],
      regra: regra ?? undefined, competencia: previa.competencia });
    setSelecionados([]); setCorte(null); setCriterios(null);
    const emPalavras = texto + " em " + competenciaAbreviada(previa.competencia);
    const deFora = [doEstado.length ? quantos(doEstado.length, rotulos.unidade) + " de estado que já está como unidade" : "",
      doConjunto.length ? quantos(doConjunto.length, rotulos.unidade) + " que já estão num conjunto" : ""].filter(Boolean);
    setAviso((uso.junto ? "Entraram junto com a seleção os que atendem: " + emPalavras : "Seleção por critérios: " + textoDaRegra(regra!)) + "." +
      (deFora.length ? " Ficaram de fora " + deFora.join(" e ") + " (não são somados duas vezes)." : ""));
    // Um pedido com agrupamento (da conversa ou de uma regra de antes): depois de usar como seleção, o agrupamento por proximidade
    // abre com a distância pedida, sobre a seleção nova.
    const kmPedido = (pedido.agrupar as { km?: unknown } | null)?.km;
    if (typeof kmPedido === "number" && kmPedido > 0) { setAgrupamento(atual => ({ n: (atual?.n ?? 0) + 1, km: kmPedido })); setAcaoSelecao("agrupar"); }
    else setAcaoSelecao("lista");
    pedirOQueFalta();
  }

  /** "Usar como seleção" nas Condições (07/11/2026, item 6.10 do comando): as condições aplicadas vão para "Selecionar por
   * critérios", na Seleção, preenchido e com a prévia, procurando na seleção em uso; a análise só muda com a escolha no painel. */
  function usarCondicoesComoSelecao() {
    const convertido = criteriosDasCondicoes(def.condicoes, !semSelecao(def));
    if (!convertido) return;
    setPainel(null);
    setAba("territorios");
    setCriterios(atual => ({ inicial: convertido.pedido, previa: true, n: (atual?.n ?? 0) + 1,
      aviso: convertido.semDistancia ? "A distância até a referência ficou nas Condições: aqui, a distância é até " +
        (generoDe(rotulos.unidade) === "f" ? "uma " : "um ") + rotulos.unidade.singular + " (“a até … km de”)." : undefined }));
    setAcaoSelecao("criterios");
    setAviso("As condições foram para “Aplicar critérios de seleção”, na Seleção, com a prévia; nada mudou na análise.");
  }

  function abrirGrupoDaBolha(id: string) {
    const grupo = grupoDaBolha(id);
    if (grupo === null) { setAviso("Não foi possível associar esta bolha a um item da lista de territórios."); return; }
    if (resposta?.nivel === "regioes") {
      // A bolha de um grupo de cima (07/11/2026): as unidades dos grupos dele, vendo por unidade.
      const nome = regioes.find(item => item.id === grupo)?.nome ?? grupo;
      navegar({ nivel: "municipios", base: { todos: false, estados: gruposDaRegiao(grupo, arvore), ids: [] }, estados: [], conjuntos: [] },
        "Abrir " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " de " + nome);
      setAberto(null);
      setAviso("Mostrando " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " de " + nome + ". Para voltar, toque em " +
        nomeDoTodo(false, rotulos) + " na trilha, no alto.");
      pedirOQueFalta();
      return;
    }
    const info = grupos.find(item => item.id === grupo);
    navegar({ nivel: "municipios", base: { todos: false, estados: [grupo], ids: [] }, estados: [],
      conjuntos: def.conjuntos.filter(conjunto => !conjuntoDeEstados(conjunto)) },
      "Abrir " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " de " + (info ? info.nome : grupo));
    setAberto(grupo);
    // Voltar é pela trilha (06/11/2026, G4): o Desfazer continua desfazendo ações, mas não é o caminho para mudar de nível.
    setAviso("Mostrando " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " de " + (info ? info.nome : grupo) +
      ". Para voltar, toque em " + nomeDoTodo(tipo !== "arquivo", rotulos) + " na trilha, no alto.");
    pedirOQueFalta();
  }
  /** Tocar numa unidade (06/11/2026, item 3.4 do comando): o lugar dela na trilha ("Brasil › Pará › MARABA (PA)"), com o cartão do
   * território. Um passo do Desfazer. */
  function abrirUnidade(id: string) {
    const nome = nomes.get(id) || id;
    navegar({ nivel: "municipios", base: { todos: false, estados: [], ids: [id] }, estados: [], conjuntos: [] }, "Abrir " + nome);
    const grupo = grupoDe(id);
    setAberto(grupo || null);
    setAviso("Mostrando " + nome + ". Para voltar, toque " + (grupo ? "no nome do " + (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular +
      " ou " : "") + "em " + nomeDoTodo(tipo !== "arquivo", rotulos) + " na trilha, no alto.");
    pedirOQueFalta();
  }
  /** A trilha (06/11/2026, item 3): cada parte leva àquele nível — o todo (o Brasil inteiro, vendo por estado na base do Brasil) ou o
   * grupo inteiro (o estado, vendo por município). Um passo do Desfazer: um Desfazer, em seguida, volta ao lugar de antes. */
  function irNaTrilha(parte: ParteDaTrilha) {
    const grupo = rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
    if (parte.chave === "todo") {
      // O todo na base do Brasil: todos os estados como unidade ("Só os estados" do Brasil; comando V22); numa planilha, as unidades.
      navegar(todoPorGrupo ? { nivel: "estados", base: { todos: false, estados: [], ids: [] }, estados: [...idsDosGrupos], conjuntos: [] }
        : { nivel: "municipios", base: { todos: true, estados: [], ids: [] }, estados: [], conjuntos: [] }, "Ir para " + parte.rotulo + " na trilha");
      setAberto(null);
      setAviso(parte.rotulo + (todoPorGrupo ? ": " + todosOs(grupo) + " como unidade." : ": " + todosOs(rotulos.unidade) + "."));
    } else if (parte.chave === "regiao" && parte.id) {
      // O grupo de cima (07/11/2026): as unidades dos grupos dele, vendo por unidade (o "Ver por" oferece os grupos dele).
      navegar({ nivel: "municipios", base: { todos: false, estados: gruposDaRegiao(parte.id, arvore), ids: [] }, estados: [], conjuntos: [] },
        "Ir para " + parte.rotulo + " na trilha");
      setAberto(null);
      const superior = rotulosDaVista(rotulos, "regioes").grupo ?? ROTULOS_GENERICOS.grupo!;
      setAviso(parte.rotulo + ": " + todosOs(rotulos.unidade) + (generoDe(superior) === "f" ? " dela." : " dele."));
      pedirOQueFalta();
    } else if (parte.chave === "grupo" && parte.id) {
      navegar({ nivel: "municipios", base: { todos: false, estados: [parte.id], ids: [] }, estados: [], conjuntos: [] },
        "Ir para " + parte.rotulo + " na trilha");
      setAberto(parte.id);
      setAviso(parte.rotulo + ": " + todosOs(rotulos.unidade) + (generoDe(grupo) === "f" ? " dela." : " dele."));
      pedirOQueFalta();
    }
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
  // Agregar territórios (06/11/2026, item 5 do comando de navegação por níveis; no lugar do Juntar das Ferramentas das análises): o
  // grupo vem do painel da Seleção de Territórios. Com "O grupo fica no lugar dos membros", eles saem da seleção (a mesma exclusão
  // da árvore), e desfazer o grupo os devolve. Cada mudança é um passo do Desfazer; a soma é do motor (CAP-AGR-01).
  const coordenadasDaSelecao = mapa.disponivel && dadosConferem ? dadosAtuais?.pontos ?? null : null;
  // As regiões na árvore da base do Brasil (item 3): os estados pelo primeiro dígito do código do IBGE.
  const secoesDoBrasil = useMemo(() => tipo === "brasil" && grupos.length ? {
    regioes: ["1", "2", "5", "3", "4"].map(id => REGIOES_DO_BRASIL.find(regiao => regiao.id === id)!).map(({ id, nome }) => ({ id, nome, sigla: "", rotuloGrupo: "",
      unidades: grupos.filter(grupo => grupo.id.charAt(0) === id).reduce((soma, grupo) => soma + (grupo.unidades || 0), 0) })),
    regiaoDoGrupo: (grupo: string) => grupo.charAt(0) } : null, [tipo, grupos]);
  /** A extensão de ponta a ponta de um conjunto à mão (item 7.8), medida pelo motor: a mesma rota da prévia, na seleção dos membros. */
  const medirExtensao = fonteMotor ? async (membros: string[], signal: AbortSignal) => {
    const dados = await pedirCriterios(fonteMotor, { competencia: def.competencia, categoria: def.categoria,
      criterios: { partir_de: { tipo: "selecao" }, filtros: [] }, agrupar: { km: 5000 }, base: { municipios: { todos: false, estados: [], ids: membros } },
      ...(tipo === "arquivo" && Object.keys(def.premissas).length ? { premissas: def.premissas } : {}), ...(tipo === "arquivo" ? { rotulos } : {}) }, signal);
    const unico = dados.grupos?.length === 1 && dados.grupos[0].membros.length === membros.length ? dados.grupos[0] : null;
    return unico ? unico.extensaoKm : null;
  } : undefined;
  const valoresDosConjuntos = useMemo(() => new Map((resposta?.itens ?? []).filter(item => item.tipo === "conjunto")
    .map(item => [item.id, { quantidade: item.quantidade, densidade: item.densidade }] as [string, { quantidade: number | null;
      densidade: number | null }])), [resposta]);
  const contextoDaBase = { grupoDe, unidadesDoGrupo: arvore.unidadesDoGrupo, todosOsGrupos: idsDosGrupos,
    todasAsUnidades: municipios.map(item => item.id) };
  // Os candidatos do agrupamento (comando V22, seção 5): só os municípios selecionados individualmente (e, ao editar um conjunto, os
  // membros dele) e os estados como unidade.
  const selecionadosIndividualmente = useMemo(() => def.nivel === "regioes" ? [] : municipios.filter(item => !item.selection_reason &&
    unidadeMarcada(def.base, item.id, grupoDaUnidade(item))), [municipios, def.base, def.nivel]);
  const motivoDoAgrupar = selecionadosIndividualmente.length + def.estados.length < 2 && !def.conjuntos.length
    ? "Selecione ao menos dois territórios para agrupar." : null;
  function editarConjunto(id: string) {
    const conjunto = def.conjuntos.find(item => item.id === id);
    if (!conjunto) return;
    setAgrupamento(atual => ({ n: (atual?.n ?? 0) + 1, editando: { id, grupo: { rotulo: conjunto.rotulo, membros: [...conjunto.membros],
      substitui: !!conjunto.substitui } } }));
    setAcaoSelecao("agrupar");
  }
  const fecharAcao = () => { setAcaoSelecao("lista"); setAgrupamento(null); };
  function criarGrupo(grupo: GrupoAgregado) {
    if (grupo.membros.length < 2) return;
    if (def.conjuntos.length >= MAX_CONJUNTOS) { setAviso(TEXTO_MAX_GRUPOS); return; }
    const novo = novoConjunto(def.conjuntos, grupo.membros, grupo.rotulo);
    registrar("Agrupar " + novo.rotulo);
    // Um conjunto de estados como unidade (comando V22, seção 5): os estados dele saem da lista dos estados como unidade, se ele fica
    // no lugar deles, e a soma é a das fontes estaduais.
    if (conjuntoDeEstados(novo)) {
      const grupos = novo.membros.map(id => id.slice(3));
      const retirados = grupo.substitui ? grupos.filter(id => def.estados.includes(id)) : [];
      // Os municípios dos estados do conjunto não ficam na seleção (o estado inteiro já está na análise, dentro do conjunto).
      trocarEscolha({ ...escolhaDe(def), base: baseSemOsEstados(def.base, grupos, arvore), estados: def.estados.filter(id => !retirados.includes(id)),
        conjuntos: [...def.conjuntos, { ...novo, substitui: grupo.substitui, retirados: retirados.map(id => "uf:" + id), versao: 1 }] });
      setAviso("Conjunto " + novo.rotulo + " criado: a bolha mostra a soma das contagens estaduais dos " + grupos.length + " estados.");
      setAcaoSelecao("lista"); setAgrupamento(null);
      return;
    }
    // Com o grupo no lugar dos membros, saem da seleção os que estavam nela; o grupo guarda quais, para devolver só esses.
    const retirados = grupo.substitui ? membrosNaSelecao(def.base, novo.membros, grupoDe) : [];
    const conjunto = { ...novo, substitui: grupo.substitui, retirados, versao: 1 };
    const base = retirados.length ? baseSemUnidades(def.base, retirados, contextoDaBase) : def.base;
    trocarEscolha({ ...escolhaDe(def), base, conjuntos: [...def.conjuntos, conjunto] });
    setAviso("Conjunto " + conjunto.rotulo + " criado" + (grupo.substitui ? ", no lugar dos membros" : "") +
      ": a bolha mostra a soma das contagens dos componentes.");
    setAcaoSelecao("lista"); setAgrupamento(null);
  }
  /** "Por proximidade" (comando V22, seção 5): cada conjunto do motor entra no lugar dos membros, que saem da seleção; os sem
   * conjunto continuam selecionados, cada um como território individual. Um passo do Desfazer. */
  function usarProximidade(lista: ConjuntoPorProximidade[], km: number) {
    if (!lista.length) return;
    if (def.conjuntos.length + lista.length > MAX_CONJUNTOS) { setAviso(TEXTO_MAX_GRUPOS); return; }
    registrar("Agrupar por proximidade (a até " + formatarNumero(km) + " km)");
    let base = def.base;
    let conjuntos = [...def.conjuntos];
    for (const item of lista) {
      const novo = novoConjunto(conjuntos, item.membros, item.rotulo);
      const retirados = membrosNaSelecao(base, novo.membros, grupoDe);
      base = retirados.length ? baseSemUnidades(base, retirados, contextoDaBase) : base;
      conjuntos = [...conjuntos, { ...novo, substitui: true, retirados, versao: 1 }];
    }
    trocarEscolha({ ...escolhaDe(def), base, conjuntos });
    setAviso(quantos(lista.length, { singular: "conjunto", plural: "conjuntos" }) + " por proximidade (a até " + formatarNumero(km) +
      " km entre os membros) no lugar dos membros; os demais continuam selecionados individualmente.");
    setAcaoSelecao("lista"); setAgrupamento(null);
  }
  function salvarGrupo(id: string, grupo: GrupoAgregado) {
    const antigo = def.conjuntos.find(item => item.id === id);
    if (!antigo || grupo.membros.length < 2) return;
    registrar("Editar o conjunto " + antigo.rotulo);
    const devolver = antigo.substitui ? antigo.retirados ?? antigo.membros : [];
    const devolvida = devolver.length ? baseComUnidades(def.base, devolver, contextoDaBase) : def.base;
    const membros = [...new Set(grupo.membros)];
    const retirados = grupo.substitui ? membrosNaSelecao(devolvida, membros, grupoDe) : [];
    const base = retirados.length ? baseSemUnidades(devolvida, retirados, contextoDaBase) : devolvida;
    // A versão da composição sobe a cada edição (comando V22, seção 5): o id fica, e o que foi calculado antes não muda em silêncio.
    trocarEscolha({ ...escolhaDe(def), base, conjuntos: def.conjuntos.map(item => item.id === id
      ? { id, rotulo: grupo.rotulo.trim().slice(0, 120) || antigo.rotulo, membros, substitui: grupo.substitui, retirados,
        versao: (antigo.versao ?? 1) + 1 } : item) });
    setAcaoSelecao("lista"); setAgrupamento(null);
  }
  function desfazerConjunto(id: string) {
    const conjunto = def.conjuntos.find(item => item.id === id);
    registrar("Desfazer o conjunto " + (conjunto?.rotulo ?? id));
    const devolver = conjunto?.substitui ? conjunto.retirados ?? conjunto.membros : [];
    // Um conjunto de estados devolve os estados dele como unidade (os que saíram da lista quando ele foi criado).
    if (conjunto && conjuntoDeEstados(conjunto)) {
      const estados = [...new Set([...def.estados, ...devolver.map(item => item.slice(3))])];
      trocarEscolha({ ...escolhaDe(def), estados, conjuntos: def.conjuntos.filter(item => item.id !== id) });
      setSelecionados(atual => atual.filter(item => item !== id));
      return;
    }
    const base = devolver.length ? baseSemOsEstados(baseComUnidades(def.base, devolver, contextoDaBase), def.estados, arvore) : def.base;
    trocarEscolha({ ...escolhaDe(def), base, conjuntos: def.conjuntos.filter(item => item.id !== id) });
    setSelecionados(atual => atual.filter(item => item !== id));
  }
  /** "Calcular" da Escolha dos territórios: a consulta vai à análise (um passo do Desfazer); o motor calcula a base, a referência e
   * a distância de cada território da base até a referência mais próxima. */
  function calcularConsulta(consulta: ConsultaTerritorios) {
    // A base pode mudar com a consulta: a comparação de antes sai (o motor recusa itens fora do gráfico).
    ajustar("Calcular a escolha dos territórios", { consulta, familia: "espacial", nivel: "municipios", comparar: [] });
    setAviso("Escolha dos territórios calculada: o eixo horizontal é a distância até a referência mais próxima de cada " + rotulos.unidade.singular + ".");
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
    salvarRef.current(salvarEstado(tituloDe(calculado.def, calculado.familia).titulo, { chave: calculado.chave, familia: calculado.familia,
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
    navegar({ nivel: "municipios", base: alguns ? { todos: false, estados: [...def.estados], ids: [] } : { todos: true, estados: [], ids: [] },
      estados: [], conjuntos: def.conjuntos.filter(conjunto => !conjuntoDeEstados(conjunto)) },
      "Ver " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " no mapa");
    setAberto(null);
    setMotivoVistaAberto(false);
    setVistaEscolhida("mapa");
    setAviso(maiuscula(alguns ? artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " dos estados escolhidos" : todosOs(rotulos.unidade)) +
      " no mapa. Para voltar " + (generoDe(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!) === "f" ? "às " : "aos ") +
      (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural + ", use Desfazer, no alto.");
    pedirOQueFalta();
  }
  // O painel aberto à direita da Seleção (comando V22, seção 3): os critérios ou o agrupamento, no lugar da lista; a árvore fica à vista.
  const painelDaAcaoDaSelecao = acaoSelecao === "criterios" && fonteMotor ? <SelecionarPorCriterios
      key={JSON.stringify(criterios?.inicial ?? null) + ":" + (criterios?.n ?? 0)} aviso={criterios?.aviso} fonte={fonteMotor} rotulos={rotulos}
      nomeDoTodo={nomeDoTodo(tipo !== "arquivo", rotulos)} unidades={municipios} competencia={def.competencia} periodos={periodos}
      categoria={def.categoria} premissas={tipo === "arquivo" ? def.premissas : undefined}
      grupos={grupos} regioes={secoesDoBrasil?.regioes ?? regioes} regiaoDoGrupo={secoesDoBrasil?.regiaoDoGrupo ?? (regioes.length ? arvore.regiaoDoGrupo : undefined)}
      marcados={{ base: def.nivel === "municipios" && !baseVazia(def.base) ? normalizarBase(def.base, grupoDe) : null,
        grupos: def.nivel === "estados" ? def.estados : [], vendoPorGrupo: def.nivel === "estados" }}
      inicial={(criterios?.inicial ?? null) as PedidoDosCriterios | null} coordenadas={coordenadasDaSelecao}
      conjuntosNaAnalise={def.conjuntos.map(conjunto => ({ id: conjunto.id, rotulo: conjunto.rotulo }))}
      algoNaAnalise={!semSelecao(def)}
      naSelecao={{ estados: def.nivel === "regioes" ? [] : def.estados, membrosDeConjuntos: def.conjuntos.flatMap(conjunto => conjunto.membros),
        conjuntos: def.conjuntos.length, grupoDe }}
      onUsar={(previa, pedidoDosCriterios, uso) => usarCriterios(previa, pedidoDosCriterios, uso)}
      onCancelar={() => { setCriterios(null); setAcaoSelecao("lista"); }}/>
    : acaoSelecao === "agrupar" && agrupamento ? <AgruparSelecionados key={"agrupar:" + agrupamento.n} fonte={fonteMotor} rotulos={rotulos}
      brasil={tipo === "brasil"} grupos={grupos}
      unidades={agrupamento.editando ? [...selecionadosIndividualmente, ...municipios.filter(item => agrupamento.editando!.grupo.membros.includes(item.id) &&
        !selecionadosIndividualmente.includes(item))] : selecionadosIndividualmente}
      estados={def.nivel === "regioes" ? [] : def.estados} base={normalizarBase(def.base, grupoDe)} competencia={def.competencia}
      categoria={def.categoria} premissas={tipo === "arquivo" ? def.premissas : undefined}
      conjuntosNaAnalise={def.conjuntos.map(conjunto => ({ id: conjunto.id, rotulo: conjunto.rotulo }))} coordenadas={coordenadasDaSelecao}
      medirExtensao={medirExtensao} editando={agrupamento.editando ?? null} kmInicial={agrupamento.km ?? null}
      onCriar={criarGrupo} onSalvar={salvarGrupo} onUsarProximidade={usarProximidade} onCancelar={fecharAcao}/> : null;
  /** Foca uma base da Análise Espacial (comando V22, seção 7); a mesma base de novo limpa o foco. Vem do gráfico e do mapa. */
  function focarBase(id: string) {
    setFocoEspacial(atual => atual === id ? null : id);
  }
  /** "MARABA (PA) → referência mais próxima: ITUPIRANGA (PA) · 47,93 km": a distância do motor, sem recálculo para o desenho, no
   * formato da tela (10/11/2026; antes, também com todas as casas, que já vão no CSV). */
  const foraDaRotacao = useMemo(() => foraDaRotatividade(def, id => grupos.find(item => item.id === id)?.nome ?? id,
    rotulos.grupo ?? ROTULOS_GENERICOS.grupo!), [def.nivel, def.estados, def.conjuntos, grupos, rotulos]);
  function textoDoFoco(par: (typeof pares)[number]): string {
    const item = resposta?.itens.find(atual => atual.id === par.base.id);
    const distancia = item?.distancia_km ?? null;
    return par.base.rotulo + " → " + (par.referencias.length > 1 ? "referências mais próximas (empate): " : "referência mais próxima: ") +
      (par.referencias.map(ref => ref.rotulo).join(", ") || "nenhuma") + (distancia === null ? " · distância não avaliável"
        : " · " + formatarNumero(distancia) + " km") +
      (item?.tipo === "conjunto" && item.membroDaReferencia ? " · pelo membro mais próximo, " + item.membroDaReferencia.rotulo : "") + ".";
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
    baixar("analise_" + (resposta.competencia || "grafico") + ".csv", montarCsv(resposta, { familia: familiaDesenho, indicador, rotulos,
      brasil: tipo === "brasil" }), "text/csv;charset=utf-8");
  }
  function exportarMetodo() {
    if (!resposta) return;
    baixar("metodo_" + (resposta.competencia || "grafico") + ".txt", textoDoMetodo(resposta, titulo, calculado?.opcoes ?? null, resumoNaTela,
      { rotulos, brasil: tipo === "brasil", regra: regraEmUso ? textoDaRegra(regraEmUso) : null }), "text/plain;charset=utf-8");
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
  const semUnidades = semTerritorios(def);
  const estadoTela = !fonte ? "E0" : emGrupos(def.nivel) || semUnidades ? "E1"
    : painel ? "E4" : def.familia !== "distribuicao" ? "E3" : "E2";
  const totalDeUnidades = niveis?.municipios.total ?? municipios.filter(item => !item.selection_reason).length;
  const avisoFamilia = pronto ? avisoDaFamilia(def, dispAtual) : null;
  // Escolha dos territórios sem referência (27/10/2026): nenhum território da base ficou com referência mais próxima (ninguém pode
  // ser referência; ou o recorte de cada um não tem outra referência; ou falta a coordenada de uma referência). A mensagem diz o
  // que aconteceu, com as contagens do motor, e o que fazer; o motivo de cada um, que só o motor sabe, fica em Não avaliáveis.
  const referenciaDaTela = referenciaPorItem && resposta?.referencia?.tipo === "consulta" ? resposta.referencia : null;
  const unidadesComReferencia = referenciaDaTela ? (resposta?.itens || []).filter(item => item.tipo === "municipio") : [];
  const fUnidade = generoDe(unidade) === "f", cadaUm = fUnidade ? "cada uma" : "cada um";
  const semReferencia = referenciaDaTela && unidadesComReferencia.length && unidadesComReferencia.every(item => !item.referenciaDoItem?.length)
    ? (referenciaDaTela.contagens?.referencia.final === 0
      ? (fUnidade ? "Nenhuma " : "Nenhum ") + unidade.singular + " pode ser referência com esta escolha dos territórios: não há referência. " +
        "Mude a aba Referência."
      : (fUnidade ? "Nenhuma d" : "Nenhum d") + artigo(unidade, true) + " " + unidade.plural + " da base ficou com referência: o recorte de " +
        cadaUm + " não tem outra referência, ou falta a coordenada de uma referência. O motivo de " + cadaUm + " está em Não avaliáveis, " +
        "nos Detalhes.")
    : null;
  // Fora do gráfico (25/10/2026): quem não tem o valor que o posiciona (o indicador; na análise espacial, a distância até a
  // referência mais próxima; na rotatividade, a coorte) fica dito junto do desenho, pelo nome, com o caminho do motivo, e o mapa
  // mostra essas unidades no lugar delas. Sem nenhuma referência, vale o aviso acima; na Série temporal (que desenha as
  // séries) e com só o mapa à vista, não se aplica.
  const foraDoGrafico = resposta && !semUnidades && !semReferencia && !series && vistaExibida !== "mapa"
    ? textoForaDoDesenho(fora, { rotulos, mapa: mapa.disponivel }) : null;
  const naVisaoDeGrupos = emGrupos(resposta?.nivel ?? def.nivel) && familiaDesenho === "distribuicao" && emGrupos(def.nivel);
  const funcaoDesabilitada = (chaveFuncao: FuncaoPainel): string | null => {
    if (!resposta) return "Disponível depois do primeiro gráfico.";
    if (familiaDesenho === "rotatividade" && ["regua", "condicoes", "ordenar", "comparar"].includes(chaveFuncao))
      return "A rotatividade mostra barras da coorte inicial; esta função vale para as bolhas.";
    // Um território só (o nível Brasil de antes de 06/11/2026, que não é mais escolhido na tela): o que separa, ordena, compara ou
    // junta vários não se aplica.
    if (def.nivel === "brasil" && chaveFuncao !== "exportar") return "Com um território só, esta função não se aplica: ela vale para vários.";
    if (chaveFuncao === "regua" && series) return "Na Série temporal, a régua não se aplica.";
    return null;
  };
  const especie = INDICADORES[indicador];
  // O todo como referência fixa (06/11/2026, item 2.3): a linha tracejada "Brasil 2,36" na densidade, com o valor do motor (a mesma
  // contagem da fonte nacional); dentro de um grupo, também a linha dele ("Pará 1,19"), da fonte estadual (POST /api/painel/lugar).
  const densidadeDoTodo = resposta?.contextoBrasil?.densidade ?? null;
  const contextoBrasil: LinhaDeReferencia | null = indicador === "densidade" && densidadeDoTodo !== null
    ? { valor: densidadeDoTodo, rotulo: textoDaReferencia(nomeDoTodo(tipo !== "arquivo", rotulos), densidadeDoTodo) +
      (resposta?.contextoBrasil?.competencia && resposta.contextoBrasil.competencia !== resposta.competencia ? " (" + exibirCompetencia(resposta.contextoBrasil.competencia) + ")" : "") }
    : null;
  const grupoNaFaixa = numerosNaFaixa?.grupo ?? null;
  const densidadeDoGrupo: number | null = grupoNaFaixa && lugar.grupo && grupoNaFaixa.id === "uf:" + lugar.grupo ? grupoNaFaixa.densidade : null;
  const linhaDoGrupo: LinhaDeReferencia | null = indicador === "densidade" && densidadeDoGrupo !== null && grupoNaFaixa !== null &&
    (resposta?.nivel ?? def.nivel) === "municipios"
    ? { valor: densidadeDoGrupo, rotulo: textoDaReferencia(nomeCurtoDoNivel(grupoNaFaixa), densidadeDoGrupo) } : null;
  const cortes: LinhaDeReferencia[] = camadaFinal === "grupos" && resposta?.grupos ? resposta.grupos.cortes.map(valor => ({ valor, rotulo: textoDaMarca(valor) }))
    : camadaFinal === "faixas" ? defDesenho.agrupar.faixas.map(valor => ({ valor, rotulo: textoDaMarca(valor) })) : [];
  const faixasDistancia: LinhaDeReferencia[] = distanciaNaTela ? defDesenho.faixasDistancia.map(valor => ({ valor, rotulo: textoDaMarca(valor) + " km" })) : [];
  const rotuloDistancia = referenciaPorItem ? "Distância até a referência mais próxima (km)"
    : (resposta?.referencia?.membros.length ?? 0) > 1 ? "Distância até o membro mais próximo da referência (km)" : "Distância até a referência (km)";
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
        <div className="relative mt-1 h-4 text-[12px] tabular-nums text-slate-600" aria-hidden="true">
          {([[0, -limiteVariacao], [50, 0], [100, limiteVariacao]] as const).map(([posicao, valor]) =>
            <span key={posicao} className="absolute whitespace-nowrap" style={{ left: posicao + "%", transform: posicao === 0 ? "none" : posicao === 100 ? "translateX(-100%)" : "translateX(-50%)" }}>
              {valor === 0 ? "0,00%" : formatarVariacao(valor)}</span>)}
        </div>
        <p className="mt-1 leading-4">Cor: variação da {especie.rotulo.toLowerCase()} entre {exibirCompetencia(resposta.competencia_inicial)} e{" "}
          {exibirCompetencia(resposta.competencia)}: azul é aumento; laranja, redução; cinza, sem mudança. Contínua, sem classes.</p>
      </div>;
    }
    // Com conjuntos na comparação (08/11/2026, item 4 do comando de 08/11/2026), cada contagem diz também quantos são unidades e quantos
    // são conjuntos (os números do motor, em `por_tipo`); nos grupos por posição, só as unidades entram.
    const itensLegenda: { chave: string; cor: string | null; texto: string; contagem: number | null; vazada?: boolean;
      porTipo?: { unidades: number | null; conjuntos: number | null } | null }[] = [];
    const tendenciaPorTipo = resposta.tendencia?.porTipo ?? null, faixasPorTipo = resposta.faixas?.porTipo ?? null,
      condicoesPorTipo = resposta.condicoes?.porTipo ?? null;
    if (camadaFinal === "classes") {
      (["CRESCIMENTO", "DECLINIO", "NENHUMA"] as const).forEach(familia => itensLegenda.push({ chave: familia, cor: paleta.tendencia[familia],
        texto: NOMES_FAMILIA_TENDENCIA[familia], contagem: resposta.tendencia?.familias[familia] ?? null,
        porTipo: tendenciaPorTipo && { unidades: tendenciaPorTipo.unidades.familias[familia] ?? 0, conjuntos: tendenciaPorTipo.conjuntos.familias[familia] ?? 0 } }));
      itensLegenda.push({ chave: "NAO_AVALIAVEL", cor: null, vazada: true, texto: "Não avaliável", contagem: resposta.tendencia?.naoAvaliaveis ?? resposta.tendencia?.contagens.NAO_AVALIAVEL ?? null,
        porTipo: tendenciaPorTipo && { unidades: tendenciaPorTipo.unidades.naoAvaliaveis, conjuntos: tendenciaPorTipo.conjuntos.naoAvaliaveis } });
    } else if (camadaFinal === "grupos" && resposta.grupos) {
      for (let i = 1; i <= totalGrupos; i++) itensLegenda.push({ chave: String(i), cor: corOrdinal(i, totalGrupos, paleta),
        texto: resposta.grupos.rotulos[i - 1] || i + "º grupo", contagem: resposta.grupos.contagens[i - 1] ?? null });
    } else if (camadaFinal === "faixas" && resposta.faixas) {
      resposta.faixas.rotulos.forEach((rotulo, i) => itensLegenda.push({ chave: String(i + 1), cor: corOrdinal(i + 1, totalFaixas, paleta), texto: rotulo,
        contagem: resposta.faixas!.contagens[i] ?? null,
        porTipo: faixasPorTipo && { unidades: faixasPorTipo.unidades.contagens[i] ?? 0, conjuntos: faixasPorTipo.conjuntos.contagens[i] ?? 0 } }));
      if (resposta.faixas.fora !== null) itensLegenda.push({ chave: "fora", cor: paleta.neutra, texto: "Fora das faixas", contagem: resposta.faixas.fora,
        porTipo: faixasPorTipo && { unidades: faixasPorTipo.unidades.fora, conjuntos: faixasPorTipo.conjuntos.fora } });
    } else if (camadaFinal === "condicoes" && resposta.condicoes) {
      const porSituacao = (situacao: "ATENDE" | "NAO_ATENDE" | "NAO_AVALIAVEL") => condicoesPorTipo &&
        { unidades: condicoesPorTipo.unidades[situacao] ?? 0, conjuntos: condicoesPorTipo.conjuntos[situacao] ?? 0 };
      itensLegenda.push({ chave: "ATENDE", cor: paleta.bolha, texto: "Atendem a todas as condições", contagem: resposta.condicoes.contagens.ATENDE ?? null,
        porTipo: porSituacao("ATENDE") },
        { chave: "NAO_ATENDE", cor: paleta.neutra, texto: "Não atendem", contagem: resposta.condicoes.contagens.NAO_ATENDE ?? null, porTipo: porSituacao("NAO_ATENDE") },
        { chave: "NAO_AVALIAVEL", cor: null, vazada: true, texto: "Sem dado para avaliar", contagem: resposta.condicoes.contagens.NAO_AVALIAVEL ?? null,
          porTipo: porSituacao("NAO_AVALIAVEL") });
    } else if (camadaFinal === "ordem" && resposta.ordenacao) {
      itensLegenda.push({ chave: "primeiros", cor: paleta.bolha, texto: primeiros !== null ? "Os " + primeiros + " primeiros (posições da ordenação" +
        (resposta.ordenacao.empatesNoCorte ? ", com os empatados no corte)" : ")") : "Com posição na ordenação", contagem: null },
        { chave: "demais", cor: paleta.neutra, texto: "Demais", contagem: null });
    }
    if (!itensLegenda.length) return null;
    // Estados como unidade junto com os municípios (comando V22, seção 2): cada nível tem os próprios grupos, posições e contagens; a
    // legenda separa os dois, com os números de cada nível (do motor, em `por_nivel`).
    const dosEstados = resposta.porNivel?.estados ?? null;
    const grupoDaLegenda = (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural;
    const textoDosEstados = !dosEstados ? null : camadaFinal === "grupos" && dosEstados.grupos
      ? maiuscula(grupoDaLegenda) + " como unidade, nos grupos próprios: " + dosEstados.grupos.rotulos.map((rotulo, i) => rotulo + " · " +
        formatarNumero(dosEstados.grupos!.contagens[i] ?? 0, true)).join("; ") + "."
      : camadaFinal === "grupos" ? maiuscula(grupoDaLegenda) + " como unidade: sem grupos por posição (são menos de dois)."
        : camadaFinal === "condicoes" && dosEstados.condicoes ? maiuscula(grupoDaLegenda) + " como unidade: atendem · " +
          formatarNumero(dosEstados.condicoes.contagens.ATENDE ?? 0, true) + "; não atendem · " + formatarNumero(dosEstados.condicoes.contagens.NAO_ATENDE ?? 0, true) +
          (dosEstados.condicoes.contagens.NAO_AVALIAVEL ? "; sem dado · " + formatarNumero(dosEstados.condicoes.contagens.NAO_AVALIAVEL, true) : "") + "."
          : camadaFinal === "faixas" && dosEstados.faixas ? maiuscula(grupoDaLegenda) + " como unidade: " + dosEstados.faixas.rotulos.map((rotulo, i) =>
            rotulo + " · " + formatarNumero(dosEstados.faixas!.contagens[i] ?? 0, true)).join("; ") + "."
            : camadaFinal === "classes" && dosEstados.tendencia ? maiuscula(grupoDaLegenda) + " como unidade: " + (["CRESCIMENTO", "DECLINIO", "NENHUMA"] as const)
              .map(familia => NOMES_FAMILIA_TENDENCIA[familia] + " · " + formatarNumero(dosEstados.tendencia!.familias[familia] ?? 0, true)).join("; ") + "."
              : camadaFinal === "ordem" ? maiuscula(grupoDaLegenda) + " como unidade: posições próprias, sem misturar com " + artigo(rotulos.unidade, true) + " " +
                rotulos.unidade.plural + "." : null;
    return <ul data-testid={id("analise-legenda-cor")} data-camada={camadaFinal} className="flex flex-col gap-1" aria-label="Legenda das cores">
      {dosEstados && <li data-testid={id("analise-legenda-nivel-unidades")} className="leading-4 font-semibold">{maiuscula(rotulos.unidade.plural)}:</li>}
      {itensLegenda.map(item => <li key={item.chave} data-testid={id("analise-legenda-cor-item")} data-chave={item.chave} data-contagem={item.contagem ?? ""}
        data-conjuntos={item.porTipo ? item.porTipo.conjuntos ?? 0 : ""} className="flex items-center gap-1.5">
        <span className="analise-amostra-bolha" style={item.vazada ? amostraVazada : { background: item.cor ?? paleta.bolha }} aria-hidden="true"/>
        <span>{item.texto}{item.contagem !== null ? <> · <strong className="tabular-nums text-ink">{formatarNumero(item.contagem, true)}</strong></> : ""}
          {item.porTipo && !!item.porTipo.conjuntos && " (" + contagemPorTipo(item.porTipo.unidades, item.porTipo.conjuntos, unidade) + ")"}</span>
      </li>)}
      {camadaFinal === "grupos" && totalGrupos > 5 && <li className="leading-4">Nos decis, só as linhas de corte: mais de cinco tons não se distinguem.</li>}
      {textoDosEstados && <li data-testid={id("analise-legenda-nivel-estados")} className="leading-4">{textoDosEstados} Cada nível tem a própria
        fonte e as próprias medidas de posição: nenhuma mistura {artigo(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!, true)} {grupoDaLegenda} e{" "}
        {artigo(rotulos.unidade, true)} {rotulos.unidade.plural}.</li>}
    </ul>;
  };
  const legendaCor = legendaDaCor(true);
  const legendaDoMapa = legendaDaCor(false);

  const somaNosGrupos = emGrupos(resposta?.nivel) && tipo === "arquivo" && !!resposta?.itens.some(item => item.contagem === "SOMA_DOS_COMPONENTES");
  // O nome do grupo das bolhas: o grupo ou, no nível de cima (07/11/2026), o grupo de cima.
  const grupoDasBolhas = rotulosDaVista(rotulos, resposta?.nivel ?? def.nivel).grupo ?? ROTULOS_GENERICOS.grupo!;
  const notasDoGrafico = [
    // As bolhas de grupo numa planilha (07/11/2026, item 1 do comando): cada grupo pelas unidades dele, com a origem do motor e,
    // na soma, a ressalva (G3).
    ...(emGrupos(resposta?.nivel) && tipo === "arquivo" ? [maiuscula("cada " + grupoDasBolhas.singular) + " vem d" +
      artigo(unidade, true) + " " + unidade.plural + " del" + (generoDe(grupoDasBolhas) === "f" ? "a" : "e") + ": " +
      (somaNosGrupos ? "a soma. " + RESSALVA_DA_SOMA : "as pessoas únicas, pelo identificador individual (quem atua em mais de " + umA(unidade) +
        " conta uma vez).") + " Os dois níveis nunca são somados nem misturados nos mesmos grupos."] : []),
    // As bolhas dos estados, na base do Brasil (a fonte estadual de profissionais únicos).
    ...(resposta?.nivel === "estados" && tipo === "brasil" ? [maiuscula("cada " + (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular) + " conta os profissionais únicos da " +
      "fonte estadual: quem atua em mais de " + umA(unidade) + " conta uma vez. A bolha não é a soma das bolhas d" + artigo(unidade, true) + " " +
      unidade.plural + "; os dois níveis nunca são somados nem misturados nos mesmos grupos."] : []),
  ];
  // Os textos que nomeiam o nível seguem o nível em uso (07/11/2026, item 1.3 do comando): vendo por estado, "Nenhum estado
  // recebeu classe", não "Nenhum município".
  const rotulosDaNota = emGrupos(resposta?.nivel ?? def.nivel) ? { unidade: grupoDasBolhas, grupo: null } : rotulos;
  const notaClasses = notaSemClassificacao(resposta?.tendencia ?? null, { rotulos: rotulosDaNota, brasil: tipo === "brasil" });
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
        {classe.rotulo} <strong className="tabular-nums text-ink">{formatarNumero(n, true)}</strong>
        {!!resposta.tendencia!.porTipo?.conjuntos.contagens[classe.codigo] && " (" + contagemPorTipo(resposta.tendencia!.porTipo.unidades.contagens[classe.codigo],
          resposta.tendencia!.porTipo.conjuntos.contagens[classe.codigo], unidade) + ")"}</button>;
    })}
    {(!!naoAvaliaveis || filtroClasse === "NAO_AVALIAVEL") && <button type="button" data-testid="analise-contagem-classe" data-classe="NAO_AVALIAVEL" data-contagem={naoAvaliaveis ?? 0}
      aria-pressed={filtroClasse === "NAO_AVALIAVEL"} className="analise-contagem" onClick={() => filtrarClasse("NAO_AVALIAVEL")}>
      <span className="analise-amostra-bolha" style={amostraVazada} aria-hidden="true"/>
      Não avaliável <strong className="tabular-nums text-ink">{formatarNumero(naoAvaliaveis ?? 0, true)}</strong></button>}
    {resposta.tendencia.bloqueio && <p className="w-full text-xs text-amber-900">{resposta.tendencia.bloqueio}</p>}
    {notaClasses && <p data-testid="analise-nota-sem-classificacao" className="analise-nota-classes">{notaClasses}</p>}
  </div> : null;

  // O que cada ponto e cada linha é no nível em uso (06/11/2026): vendo por estado, "Cada linha é um estado".
  const rotulosDoNivel = useMemo(() => emGrupos(resposta?.nivel ?? def.nivel)
    ? { unidade: rotulosDaVista(rotulos, resposta?.nivel ?? def.nivel).grupo ?? ROTULOS_GENERICOS.grupo!, grupo: null }
    : rotulos, [resposta?.nivel, def.nivel, rotulos]);
  // As linhas de referência da Série temporal (06/11/2026): o todo e, dentro de um grupo, o grupo, com os valores do motor na
  // densidade (na quantidade, o total do todo não se compara ao de cada território, e as linhas ficam de fora).
  const referenciasDaSerie: SerieDeReferencia[] = useMemo(() => {
    if (!series || indicador !== "densidade" || !numerosNaFaixa) return [];
    return [numerosNaFaixa.grupo, numerosNaFaixa.todo].filter((nivel): nivel is NonNullable<typeof nivel> => !!nivel && !!nivel.serie)
      .filter(nivel => nivel.nivel === "todo" || (lugar.grupo !== null && nivel.id === "uf:" + lugar.grupo))
      .map(nivel => ({ id: nivel.id, rotulo: nomeCurtoDoNivel(nivel), observacoes: nivel.serie!.map(valor => ({ competencia: valor.competencia, valor: valor.densidade })) }));
  }, [series, indicador, numerosNaFaixa, lugar.grupo]);
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
  // valor que as posiciona (25/10/2026: sem distância até a referência, sem o indicador ou sem a coorte, cada uma no lugar dela, com a
  // pintura da camada ou vazada); a régua e os filtros esmaecem (decisão de 23/10).
  const itensDoMapa = useMemo(() => resposta ? itensParaOMapa(resposta.itens, estadosNoMapa || estadosJuntosNoMapa) : [],
    [resposta, estadosNoMapa, estadosJuntosNoMapa]);
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
  // As ligações do mapa, até MAX_LIGACOES: primeiro as das unidades marcadas, depois as dos demais territórios da base, na ordem dos
  // nomes.
  const ligacoes = useMemo(() => distanciaNaTela && resposta ? ligacoesDoMapa(resposta.itens,
    [...new Set([...selecao, ...idsDasBases, ...idsDosConjuntosDaBase])]) : [], [distanciaNaTela, resposta, selecao, idsDasBases, idsDosConjuntosDaBase]);
  // O destaque da resposta de valor (06/11/2026) aparece também no mapa, com o anel e o nome dos marcados (estado visual).
  const realceNaTela = realce && realce.chave === chave ? realce.ids : NENHUM_REALCE;
  const selecaoDoMapa = realceNaTela.length ? [...new Set([...selecao, ...realceNaTela])] : selecao;
  const nomesDasReferencias = useMemo(() => new Map((resposta?.referencia?.membros ?? []).map(membro => [membro.id, membro.rotulo] as [string, string])),
    [resposta]);
  // A mira do mapa: os membros da referência; com a Escolha dos territórios, as referências mais próximas (todas, até MAX_LIGACOES;
  // com mais, as das ligações).
  const referenciasDoMapa = useMemo(() => {
    if (!distanciaNaTela) return [];
    const membros = (resposta?.referencia?.membros ?? []).map(membro => membro.id).filter(Boolean);
    if (!referenciaPorItem || membros.length <= MAX_LIGACOES) return membros;
    return [...new Set(ligacoes.flatMap(ligacao => ligacao.para))];
  }, [distanciaNaTela, referenciaPorItem, resposta, ligacoes]);
  // Tocar no desenho (06/11/2026, item 3 do comando): o estado desce até ele; a unidade abre o lugar dela; com a Comparar
  // abertas (a escolha de itens em curso), tocar marca e desmarca, como antes.
  const marcando = painel === "comparar";
  const dicaDe = useCallback((item: PainelItem) => montarDica(item, { indicador, competencia: resposta?.competencia ?? "",
    competenciaInicial: resposta?.competencia_inicial || null, distancia: distanciaNaTela, variacao: dicaComVariacao && !!resposta?.competencia_inicial,
    tendencia: !!item.tendencia, nomes, limiares, rotulos, unidadesDoGrupo, porItem: referenciaPorItem, trajetoria: cometa, abrirUnidade: !marcando }),
  [indicador, resposta, distanciaNaTela, dicaComVariacao, nomes, limiares, rotulos, unidadesDoGrupo, referenciaPorItem, cometa, marcando]);
  function tocarNoDesenho(id: string) {
    const item = resposta?.itens.find(atual => atual.id === id);
    if (item?.tipo === "estado") abrirGrupoDaBolha(id);
    else if (item?.tipo === "municipio" && !marcando) abrirUnidade(id);
    else alternar(id);
  }
  const dadosNoMapa = useMemo(() => {
    if (!dadosAtuais || !dadosAtuais.grupos) return dadosAtuais;
    if (estadosNoMapa) return { ...dadosAtuais, pontos: new Map([...dadosAtuais.pontos, ...dadosAtuais.grupos]) };
    if (!estadosJuntosNoMapa || !resposta) return dadosAtuais;
    // Só os estados da seleção: os demais pontos de desenho não viram fundo (o fundo são as sedes).
    const naResposta = new Set(resposta.itens.filter(item => item.tipo === "estado").map(item => item.id));
    const membros = new Set(resposta.itens.flatMap(item => item.tipo === "conjunto" ? item.membros ?? [] : []).filter(id => id.startsWith("uf:")));
    return { ...dadosAtuais, pontos: new Map([...dadosAtuais.pontos, ...[...dadosAtuais.grupos].filter(([id]) => naResposta.has(id) || membros.has(id))]) };
  }, [dadosAtuais, estadosNoMapa, estadosJuntosNoMapa, resposta]);
  // A escala muda só o desenho ("como ver"): fica na barra junto da vista, só quando se aplica (no gráfico, fora da rotatividade
  // e da Série temporal). Linear por padrão; a logarítmica só por escolha e com valores positivos. O mapa não tem escala própria:
  // a cor contínua da rotatividade vai de 0 a 100%.
  const escalaNoGrafico = (vistaExibida === "grafico" || lado) && !rotatividadeNaTela && !series && !quadroDeSetas;
  const logPossivel = !!dominio && dominio[0] > 0;
  const propsDoMapa: MapaProps | null = resposta && dadosNoMapa ? {
    itens: itensDoMapa, dentro: dentroDoMapa, dados: dadosNoMapa, indicador, pintura: pinturaMapa, pintar: pinturaNoMapa,
    valorContinuo: corDoMapa.valor, rotuloContinuo: corDoMapa.rotulo, dominio: corDoMapa.dominio, escala: "linear",
    tamanho: tamanhoNoMapa, contextoBrasil: rotatividadeNaTela ? null : contextoBrasil,
    legendaCor: pinturaMapa === "quintis" ? legendaDosQuintis : legendaDoMapa, selecionados: selecaoDoMapa, referencias: referenciasDoMapa, ligacoes,
    nomesDasReferencias, comTerritoriosBase: pares.length > 0, extraDoRotulo, dicaDe,
    rotulos: estadosNoMapa ? { unidade: rotulos.grupo ?? ROTULOS_GENERICOS.grupo!, grupo: null } : rotulos,
    nota: estadosNoMapa ? dadosAtuais?.notaDosGrupos ?? null : null,
    brasil: tipo === "brasil", referenciaPorItem,
    ativoExterno: lado ? ativoCruzado : null, onAtivo: lado ? setAtivoCruzado : undefined, onAlternar: tocarNoDesenho,
    // O foco da Análise Espacial (comando V22, seção 7), o mesmo do gráfico: os dois ficam sincronizados.
    foco: parDoFoco ? parDoFoco.base.id : null, onFocar: distanciaNaTela && pares.length && !marcando ? focarBase : undefined,
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
  // A lista dos grupos (06/11/2026, item 7): em tela estreita, vendo por estado, na Distribuição, com a ordem do motor.
  const listaDosGrupos = estreita && familiaDesenho === "distribuicao" && emGrupos(resposta?.nivel) &&
    !!resposta.ordemDoIndicador?.itens.length;
  // Nas bolhas dos estados, os nomes só dos destaques: os 3 maiores e os 3 menores pela ordem do motor (os marcados e o tocado, o
  // gráfico já rotula). Antes de 06/11/2026, as 27 siglas ficavam sempre à vista.
  const destaquesDosGrupos = useMemo(() => destaquesDaOrdem(resposta?.ordemDoIndicador ?? null), [resposta]);
  // Numa seleção mista (comando V22), os estados como unidade levam o nome no gráfico pela ordem do nível deles (os 3 maiores e
  // os 3 menores; com até 6 estados, todos), para não se confundirem com os municípios.
  const destaquesDosEstados = useMemo(() => destaquesDaOrdem(resposta?.porNivel?.estados?.ordemDoIndicador ?? null), [resposta]);
  const desenhoDoGrafico = (() => {
    if (!resposta) return null;
    if (listaDosGrupos && vistaDosGrupos === "lista")
      return <ListaDosGrupos itens={resposta.itens} ordem={resposta.ordemDoIndicador!.itens} indicador={indicador}
        todo={contextoBrasil} limiares={limiares} plural={(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural}
        onAbrir={abrirGrupoDaBolha}/>;
    if (familiaDesenho === "rotatividade" && calculado?.def.rotatividade) return <PainelRotatividade itens={visiveis} rotulos={rotulos}
      inicial={calculado.def.rotatividade.inicial} final={calculado.def.rotatividade.final}/>;
    if (series) return itensSeries.length ? <PainelSeries itens={itensSeries} competencias={resposta.serie?.competencias ?? []}
      indicador={indicador} rotulos={rotulosDoNivel} referencias={referenciasDaSerie}/>
      : <div data-testid="analise-series-vazio" className="analise-vazio">
        <p className="font-semibold text-ink">Escolha até {MAX_SERIES} {rotulosDoNivel.unidade.plural} para ver a série temporal.</p>
        <p className="text-xs text-slate-600">Marque na tabela (Detalhes) ou, na visão Tendência, clique nas linhas do quadro de setas.</p>
      </div>;
    if (quadroDeSetas) return <PainelSetas itens={visiveis} janela={resposta.tendencia?.janela.length ? resposta.tendencia.janela : defDesenho.janela}
      indicador={indicador} rotulos={rotulosDoNivel} selecionados={selecao} pelaPosicao={camadaFinal === "ordem"} condicoes={camadaFinal === "condicoes"}
      legenda={layoutTendencia ? undefined : legendaCor} onAlternar={alternar} ativoExterno={lado ? ativoCruzado : null} onAtivo={lado ? setAtivoCruzado : undefined}/>;
    // No nível da unidade (06/11/2026, item 3.4), a Distribuição não desenha um gráfico de uma bolha só: o cartão do território, no
    // alto, faz o papel dele (o mapa continua mostrando onde ela fica).
    if (lugar.tipo === "unidade" && familiaDesenho === "distribuicao" && tipo === "brasil" && resposta.itens.length === 1)
      return <p data-testid="analise-cartao-no-lugar" role="status" className="analise-vazio">
        <span className="font-semibold text-ink">{resposta.itens[0].rotulo}</span> está no cartão, no alto: com um território só, ele
        fica no lugar do gráfico. O mapa mostra onde fica; a trilha leva {generoDe(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!) === "f" ? "à " : "ao "}
        {(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular} e ao {nomeDoTodo(true)}.</p>;
    // Com o mapa disponível, a dica da bolha mostra o mapinha ("onde fica?"); no lado a lado, o destaque é cruzado com o mapa.
    return <PainelChart resposta={resposta} itens={visiveis} todos={plotaveis} indicador={indicador} escala={escala} distancia={distanciaNaTela}
      cometa={cometa} trajetoria={cometa} porItem={referenciaPorItem} pares={paresLigados} destaque={realceNaTela.length ? realceNaTela : destaque}
      foco={parDoFoco ? parDoFoco.base.id : null} onFocar={distanciaNaTela && pares.length ? focarBase : undefined}
      realce={realceNaTela} vista={vista} fase={fase} pintura={pintura} selecionados={selecao} limiares={limiares}
      nomes={nomes} carregando={carregando}
      rotuloDistancia={rotuloDistancia} rotulos={rotulos} contextoBrasil={contextoBrasil} cortes={cortes} corte={corteAtivo(corte, dominio) ? corte : null}
      faixasDistancia={faixasDistancia} unidadesDoGrupo={unidadesDoGrupo} legendaCor={layoutTendencia ? null : legendaCor} notas={notasDoGrafico}
      linhaDoGrupo={linhaDoGrupo} onAbrirUnidade={abrirUnidade} marcando={marcando}
      extraDoRotulo={extraDoRotulo}
      rotuloSempre={item => (item.tipo === "estado" && (destaquesDosGrupos.has(item.id) || destaquesDosEstados.has(item.id))) || (camadaFinal === "ordem" && primeiros !== null && primeiros <= 12 && item.ordem?.posicao !== null &&
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
      case "referencia": return <EscolhaDosTerritorios fonte={fonteMotor} aplicada={def.consulta}
        inicial={consultaInicial({ comSelecao: def.nivel === "municipios" && !semSelecao(def) })}
        pedido={{ competencia: def.competencia, categoria: def.categoria, base: { municipios: normalizarBase(def.base, grupoDe) },
          ...(tipo === "arquivo" && Object.keys(def.premissas).length ? { premissas: def.premissas } : {}),
          ...(tipo === "arquivo" && fonte?.rotulos ? { rotulos: fonte.rotulos } : {}) }}
        contexto={"Categoria profissional: " + maiuscula(profissionaisDe(def.categoria)) + " · Competência: " + competenciaPorExtenso(def.competencia)}
        rotulos={rotulos} brasil={tipo === "brasil"} grupos={grupos} temPopulacao={temPopulacao} nomes={nomes}
        emDia={consultaNaTela} calculando={carregando && def.familia === "espacial"} criterio={criterioDoChat}
        usadas={consultaNaTela && referenciaDaTela ? { referencias: referenciaDaTela.membros.map(membro => membro.rotulo),
          base: basesDaReferencia.length === 1 ? basesDaReferencia[0].rotulo : null } : null}
        faixas={def.faixasDistancia} onFaixas={limites => ajustar("Aplicar as faixas de distância", { faixasDistancia: limites })}
        onCalcular={calcularConsulta} selecaoVazia={semSelecao({ ...def, nivel: "municipios" })} conjuntos={def.conjuntos}
        onAlterarSelecao={() => { setPainel(null); irParaTerritorios(); }}/>;
      case "condicoes": return <GavetaCondicoes condicoes={def.condicoes} espacial={distanciaNaTela} resposta={resposta} rotulos={rotulos}
        soAtende={soAtende} onSoAtende={valor => { registrar(valor ? "Mostrar só quem atende" : "Mostrar todos"); setSoAtende(valor); }}
        onAplicar={condicoes => ajustar(condicoes.length ? "Aplicar as condições" : "Limpar as condições", { condicoes })}
        onUsarComoSelecao={def.nivel === "municipios" && criteriosDasCondicoes(def.condicoes, true) ? usarCondicoesComoSelecao : undefined}/>;
      case "ordenar": return <GavetaOrdenar rotulos={rotulos} ordenar={def.ordenar} espacial={distanciaNaTela} mudanca={exibicao.variacao} resposta={resposta}
        indicador={indicador} onAplicar={ordenar => ajustar(ordenar ? "Ordenar" : "Limpar a ordenação", { ordenar })}/>;
      case "comparar": return <GavetaComparar itens={resposta?.itens || []} selecionados={selecao} pedidos={def.comparar} resposta={resposta}
        nomes={nomes} rotulos={rotulos} onAlternar={alternar}
        onLimpar={() => { registrar("Limpar a escolha da comparação"); setSelecionados([]); mudar({ comparar: [] }); }}
        onComparar={ids => ajustar("Comparar", { comparar: ids })}/>;
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
        // A Escolha dos territórios (27/10/2026): a frase-resumo da consulta calculada e o botão que abre a janela.
        const frase = def.consulta ? textoDaFraseDaConsulta(fraseDaConsulta(def.consulta, { rotulos, brasil: tipo === "brasil", grupos, nomes,
          selecaoComConjuntos: def.conjuntos.some(conjunto => !conjuntoDeEstados(conjunto)) }))
          : "nenhuma ainda";
        return <div key={qual} data-ajuste={qual} className="flex flex-wrap items-end gap-1.5">
          <span className="analise-rotulo-campo">Territórios
            <span data-testid="analise-referencia-resumo" className="analise-resumo">{frase}</span>
          </span>
          <button type="button" data-testid="analise-referencia-escolher" className="analise-botao-secundario" onClick={() => abrirPainel("referencia")}>
            Escolha dos territórios</button>
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
    : resumoDoUniverso({ nivel: def.nivel, base: def.base, estados: def.estados, conjuntos: def.conjuntos.length, grupos, regioes, rotulos,
      total: totalDeUnidades, grupoDe, nomes: nomesDoCatalogo });
  // A Seleção de Territórios é só seleção (24/10/2026): o título, a frase-resumo, o desenho e os Detalhes ficam nas análises.
  const naSelecao = aba === "territorios";
  // Vendo por estado, a Análise Espacial mostra só a mensagem e o botão (06/11/2026, item 3.5 do comando).
  const espacialNosGrupos = aba === "espacial" && emGrupos(def.nivel);
  // O cartão do território (06/11/2026, item 3.4): os valores da unidade vêm do resultado em dia com o lugar; na Análise Espacial, com
  // a distância até a referência mais próxima.
  const unidadeDoLugar = lugar.tipo === "unidade" && calculado?.chave === chave ? resposta?.itens.find(item => item.id === lugar.unidade) ?? null : null;
  const distanciaDaUnidade = unidadeDoLugar && distanciaNaTela ? { valor: unidadeDoLugar.distancia_km,
    texto: referenciaPorItem ? "até a referência mais próxima" : "até a referência" } : null;
  // O que a classe quer dizer, junto do resultado de um território só (o motor já disse qual é a classe na frase-resumo).
  const unicoComTendencia = tendenciaNaTela && resumoNaTela && resposta?.itens.length === 1 && resposta.itens[0].tendencia
    ? resposta.itens[0].tendencia : null;
  const significado = unicoComTendencia && resposta?.tendencia ? significadoDaClasse(unicoComTendencia) : null;
  // A unidade escolhida no quadro de setas: as velocidades dela ficam no painel da explicação.
  const itemDasVelocidades = quadroDeSetas && selecao.length ? resposta?.itens.find(item => item.id === selecao[selecao.length - 1] && item.tendencia) ?? null : null;

  // Os totais individualizados da abrangência (05/11/2026): o Brasil inteiro pela fonte nacional e cada estado inteiro pela fonte
  // estadual, do motor, junto do resultado que o desenho mostra; na Seleção, só quando a resposta é a da seleção atual.
  const totaisDe = (r: PainelResposta | null, d: DefinicaoAnalise | null, compacto: boolean) => r && d && r.nivel === "municipios" &&
    d.nivel === "municipios" && !consultaEmUso(d) ? <PainelAbrangencia completa={r.abrangenciaCompleta} brasil={r.contextoBrasil}
      parciais={gruposParciais(d.base, arvore)} categoria={r.categoria || def.categoria} rotulos={rotulos} compacto={compacto}/> : null;
  const totaisNoResultado = totaisDe(resposta, calculado?.def ?? null, false);
  const totaisNaSelecao = calculado?.chave === chave ? totaisDe(resposta, calculado?.def ?? null, true) : null;
  const subtituloEResumo = <>
    <p data-testid="analise-subtitulo" className="analise-subtitulo">{subtitulo}</p>
    {/* Frase-resumo do motor: lida pelos leitores de tela a cada mudança; também na impressão e no arquivo de método. */}
    <p data-testid="analise-resumo" aria-live="polite" className="analise-frase-resumo">{resumoNaTela ?? ""}</p>
    {significado && <p data-testid="analise-resumo-significado" className="analise-frase-significado">{significado}</p>}
    {totaisNoResultado}
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

  // Os atributos do pedido da conversa (05/11/2026): o último com desfecho, a situação dele e o resultado do motor em exibição (o id
  // guardado na sessão), para conferir a associação entre o comando e o que a área mostra.
  return <section id="area-de-analise" data-testid="area-de-analise" data-estado={estadoTela} data-familia={def.familia} data-nivel={def.nivel}
    data-desenho={vistaExibida} data-aba={aba} data-pedido-da-conversa={ultimoDesfecho?.id ?? ""} data-desfecho={ultimoDesfecho?.situacao ?? ""}
    data-resultado={resposta?.sessao?.resultId ?? ""} aria-labelledby="analise-titulo" className="analise">
    {/* Desfazer e Limpar seleção (24/10/2026, segunda rodada): fixos no alto da área, lado a lado, em todas as abas, sem rolar. */}
    {pronto && <div data-testid="analise-controles-globais" role="toolbar" aria-label="Desfazer e limpar seleção"
      className="analise-controles-globais analise-nao-imprimir">
      <button type="button" data-testid="analise-desfazer" className="analise-controle-global" onClick={desfazer} disabled={!passoADesfazer}
        title={textoDoDesfazer(passoADesfazer)} aria-label={textoDoDesfazer(passoADesfazer)} data-passos={passos.length}>
        <Undo size={18} aria-hidden="true"/>Desfazer</button>
      <button type="button" data-testid="analise-limpar-selecao" className="analise-controle-global" onClick={limparSelecao}
        disabled={!temSelecaoParaLimpar} title={temSelecaoParaLimpar ? "Tira os territórios em análise; os dados carregados continuam."
          : "Nenhum território selecionado."}>
        <IconeVassoura size={18} aria-hidden="true"/>Limpar seleção</button>
      <span data-testid="analise-controles-territorios" className="analise-controles-territorios">
        <MapaIcone size={14} aria-hidden="true"/><span className="truncate">{resumoDaSelecao}</span></span>
    </div>}
    {/* A trilha (06/11/2026, item 3.1): no alto da área de análise, sempre visível e igual em todas as abas. */}
    {pronto && <Trilha partes={lugar.partes} vazia={lugar.tipo === "nenhum"}
      grupoParcial={(lugar.tipo === "grupo" && !lugar.grupoInteiro) || (lugar.tipo === "regiao" && !lugar.regiaoInteira)}
      onIr={irNaTrilha}/>}
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
          <PainelTerritorios rotulos={rotulos} brasil={tipo === "brasil"} grupos={grupos} unidades={municipios} total={totalDeUnidades}
            nivel={def.nivel} base={def.base} estados={def.estados} conjuntos={def.conjuntos} aberto={aberto} onAbrir={abrirLista}
            secoesDaArvore={secoesDoBrasil ?? (regioes.length ? { regioes, regiaoDoGrupo: arvore.regiaoDoGrupo! } : null)}
            regioesComoUnidade={tipo === "arquivo" && comRegioes} onRegioesComoUnidade={regioesComoUnidade}
            regioesAbertas={regioesAbertas} onRegioesAbertas={setRegioesAbertas}
            coordenadas={coordenadasDaSelecao} totais={totaisNaSelecao} onBase={mudarArvore} onEstadosComoUnidade={estadosComoUnidade}
            onDesfazerConjunto={desfazerConjunto} onEditarConjunto={editarConjunto}
            valoresDosConjuntos={valoresDosConjuntos} profissionais={profissionaisDe(def.categoria)}
            acao={acaoSelecao} painelDaAcao={painelDaAcaoDaSelecao} analiseAberta={NOMES_FAMILIAS[def.familia]}
            onConfirmar={() => escolherAba(def.familia)}
            onCriterios={fonteMotor ? () => { setCriterios(atual => atual ?? { inicial: null }); setAcaoSelecao("criterios"); } : undefined}
            onAgrupar={() => { setAgrupamento(atual => ({ n: (atual?.n ?? 0) + 1 })); setAcaoSelecao("agrupar"); }}
            motivoDoAgrupar={motivoDoAgrupar}
            regra={regraEmUso ? { texto: textoDaRegra(regraEmUso), onReaplicar: () => {
              setCriterios(atual => ({ inicial: regraEmUso.pedido, n: (atual?.n ?? 0) + 1 }));
              setAcaoSelecao("criterios");
            } } : null}/>
        </> : <>
          {/* A faixa fixa do lugar em uso (06/11/2026, item 2.2): no alto de todas as abas de análise; no nível da unidade, o cartão. */}
          {!!tipo && <FaixaDoLugar lugar={lugar} numeros={numerosNaFaixa} carregando={carregandoLugar} erro={erroNaFaixa}
            categoria={def.categoria} rotulos={rotulos} resumo={resumoDaSelecao} verPor={[]} nivel={def.nivel} onVerPor={() => undefined}
            unidade={unidadeDoLugar} distancia={distanciaDaUnidade}/>}
          <EntendaEstaAnalise key={aba} aba={aba} pedida={explicacaoPedida}
            apresentacao={apresentacaoDaAba(aba, { rotulos, brasil: tipo === "brasil", comGrupos: grupos.length > 0 })}/>
          {motivoDaAba && <p data-testid="analise-familia-motivo" role="status" className="analise-motivo">
            <strong className="text-ink">Indisponível com estes dados:</strong> {motivoDaAba.motivo}
            {motivoDaAba.enviarDados && <button type="button" data-testid="analise-enviar-dados" className="analise-botao-secundario ml-2"
              onClick={() => props.onEscolherFonte("arquivo")}><Upload size={14} aria-hidden="true"/>Enviar meus dados</button>}
            <span className="analise-motivo-desenho">O desenho abaixo continua com a {NOMES_FAMILIAS[def.familia]}.</span>
          </p>}
          {/* Análise Espacial vendo por estado (06/11/2026, item 3.5): só a mensagem e o botão que troca o "Ver por" para município,
              sem o gráfico, o título e os ajustes da Distribuição. */}
          {espacialNosGrupos && <div data-testid="analise-espacial-grupos" role="status" className="analise-espacial-grupos">
            <p className="analise-espacial-grupos-texto">{textoEspacialNosGrupos(rotulos)}</p>
            <button type="button" data-testid="analise-espacial-ver-unidades" className="analise-botao-primario"
              onClick={verUnidadesDosEstados}>{textoVerUnidadesDosGrupos(rotulos)}</button>
          </div>}
          {!motivoDaAba && !espacialNosGrupos && <div data-testid="analise-ajustes" data-familia={def.familia} className="analise-ajustes">
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

    {pronto && <div data-testid="analise-resultados" hidden={naSelecao || espacialNosGrupos} className="analise-resultados">
    <header className="analise-cabecalho">
      <h2 id="analise-titulo" tabIndex={-1} data-testid="analise-titulo" className="analise-titulo">{titulo}</h2>
      {!layoutTendencia && subtituloEResumo}
    </header>

    <div ref={corpoRef} className={"analise-corpo" + (layoutTendencia ? " analise-corpo-tendencia" : painel ? " analise-corpo-com-painel" : "") +
      (painel === "referencia" ? " analise-corpo-territorios" : "") + (lado ? " analise-corpo-lado" : "")} style={layoutTendencia ? { "--analise-largura-lateral": larguraLateral + "px" } as CSSProperties : undefined}>
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
              {listaDosGrupos && vistaExibida !== "mapa" && <div role="group" data-testid="analise-grupos-vista"
                aria-label={"Os " + (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural + " em lista ou em bolhas"}
                className="analise-segmentos analise-desenho">
                {(["lista", "bolhas"] as const).map(qual => <button key={qual} type="button" data-testid={"analise-grupos-" + qual}
                  aria-pressed={vistaDosGrupos === qual} onClick={() => setVistaDosGrupos(qual)}>{qual === "lista" ? "Lista" : "Bolhas"}</button>)}
              </div>}
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
          {desatualizada && <div role={falhouAAtual ? "alert" : "status"} data-testid="analise-desatualizada" className="analise-erro">
            <p>Esta análise ainda é {deOndeEhOCalculado}: o cálculo da seleção em uso {falhouAAtual ? "não deu certo" : "ainda não chegou"}.</p>
            <button type="button" data-testid="analise-atualizar" onClick={() => setTentativa(valor => valor + 1)}
              className="mt-1 inline-flex items-center gap-1 font-semibold underline"><RefreshCw size={13} aria-hidden="true"/>Atualizar</button>
          </div>}
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
                Mudar a escolha dos territórios</button></span></p>}
          {foraDoGrafico && <p data-testid="analise-fora-do-grafico" role="status" className="analise-aviso-familia">
            <ChartScatter size={14} aria-hidden="true"/><span>{foraDoGrafico}</span></p>}
          {/* O foco da Análise Espacial (comando V22, seção 7): a base, a referência, a distância geodésica do motor (em precisão
              integral, sem recalcular) e o controle que limpa o foco. */}
          {parDoFoco && <div data-testid="analise-foco-espacial" role="status" className="analise-foco-espacial">
            <Crosshair size={14} aria-hidden="true"/>
            <span>{textoDoFoco(parDoFoco)}</span>
            <button type="button" data-testid="analise-foco-limpar" className="analise-link" onClick={() => setFocoEspacial(null)}>Limpar o foco</button>
          </div>}
          {/* Os territórios que esta análise não mede (comando V22, seção 2): quais e por quê. */}
          {!!resposta?.foraDaAnalise?.length && !semUnidades && <p data-testid="analise-fora-da-analise" role="status" className="analise-aviso-familia">
            <ChartScatter size={14} aria-hidden="true"/><span>Fora desta análise: {resposta.foraDaAnalise.map(item => item.tipo === "estado"
              ? item.rotulo.replace(/\s*\([A-Z]{2}\)$/, "") + " (" + (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular + ")" : item.rotulo).join(", ")}.{" "}
              {maiuscula(resposta.foraDaAnalise[0].motivo.replace(/^Fora da Análise Espacial: /, ""))}</span></p>}
          {/* Na rotatividade, os estados como unidade e os conjuntos de estados não entram no pedido (comando V22, seção 2): quais e
              por quê. */}
          {def.familia === "rotatividade" && foraDaRotacao.length > 0 && !semUnidades && <p data-testid="analise-fora-da-rotatividade" role="status"
            className="analise-aviso-familia"><ChartScatter size={14} aria-hidden="true"/><span>Fora desta análise: {foraDaRotacao.join(", ")}. A
            rotatividade acompanha pessoas em cada {rotulos.unidade.singular}; {(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).plural} como
            unidade não entram.</span></p>}
          {/* Base e referência (25/10/2026): cada território da base, a referência mais próxima dele e a distância do motor, à vista no
              gráfico e no mapa. Sem nenhuma referência entre vários, o aviso acima já diz o motivo. */}
          {distanciaNaTela && basesDaReferencia.length > 0 && !semUnidades && (pares.length < 2 || pares.some(par => par.referencias.length > 0)) &&
            <p data-testid="analise-par-base" role="status" className="analise-aviso-familia">
            <Crosshair size={14} aria-hidden="true"/><span>{textoDosTerritoriosBase({ pares, ligados: paresLigados.length, rotulos })}{" "}
              <button type="button" data-testid="analise-par-base-mudar" className="analise-link" onClick={() => abrirPainel("referencia")}>
                Mudar a escolha dos territórios</button></span></p>}
          {emGrupos(resposta?.nivel) && emGrupos(def.nivel) && <p data-testid="analise-instrucao" className="analise-instrucao">
            <Scale size={14} aria-hidden="true"/>{textoInstrucaoGrupos(rotulosDaVista(rotulos, def.nivel))}</p>}
          {/* Convite ao mapa depois das Condições e na Análise espacial: "onde ficam?" é a pergunta que o mapa responde. */}
          {convite && <p className="analise-convite analise-nao-imprimir"><MapaIcone size={14} aria-hidden="true"/>
            <button type="button" data-testid="analise-convite-mapa" className="analise-link" onClick={() => trocarVista("mapa")}>Ver onde ficam no mapa</button></p>}
        </div>

        {!layoutTendencia && contagemClasses}
        <div ref={quadroRef} data-testid="analise-quadro" data-desatualizada={desatualizada ? "true" : undefined}
          className={"analise-quadro" + (lado && !antesDoDesenho ? " analise-quadro-lado" : "") + (desatualizada ? " analise-quadro-desatualizado" : "")}>
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
          {quadroDeSetas && <LegendaDoQuadro legenda={legendaCor} rotulos={rotulosDoNivel}/>}
          {cometa && legendaCor && <div className="analise-legenda analise-explicacao-bloco">{legendaCor}</div>}
          {series && <LegendaDaSerie indicador={indicador} rotulos={rotulosDoNivel}/>}
          {quadroDeSetas && (itemDasVelocidades
            ? <Velocidades item={itemDasVelocidades} indicador={indicador} unidadeTempo={resposta?.tendencia?.unidadeTempo ?? null}/>
            : <p className="analise-explicacao-dica">Clique numa linha do quadro para ver o ritmo de variação dela aqui.</p>)}
        </section>
      </div> : painelDaFuncao}
    </div>

    {resposta && !semUnidades && <PainelDetalhes resposta={resposta} itens={visiveis} fora={fora} familia={familiaDesenho} indicador={indicador}
      distancia={distanciaNaTela} variacao={exibicao.variacao} tendencia={exibicao.tendencia} rotulos={rotulosDoNivel} selecionados={selecao}
      limiares={limiares} corteAtivo={corteAtivo(corte, dominio)} onAlternar={alternar} regra={regraEmUso ? textoDaRegra(regraEmUso) : null}/>}
    </div>}
    <p aria-live="polite" className="sr-only" data-testid="analise-aviso">{aviso}</p>
  </section>;
}
