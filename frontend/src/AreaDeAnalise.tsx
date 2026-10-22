import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { ArrowLeftRight, ChevronRight, Database, Download, Filter, Layers3, ListOrdered, LoaderCircle, Map as MapaIcone, Pause, Play,
  RefreshCw, Ruler, Scale, SlidersHorizontal, Upload, Wrench, X } from "lucide-react";
import {
  ErroDoMotor, pedirPainel, type FonteDoMotor, type Pendencia, type PainelConjuntoPedido, type PainelCriterio, type PainelItem,
  type PainelMunicipios, type PainelOpcoes, type PainelReferenciaPedido, type PainelResposta,
} from "./painelApi";
import {
  ATALHOS_JANELA, CLASSES_TENDENCIA, CORES_TENDENCIA, COR_BOLHA, COR_NEUTRA, FAMILIAS, INDICADORES, LIMITE_LEVE, MINIMO_TENDENCIA,
  NOMES_FAMILIAS, NOMES_FAMILIA_TENDENCIA, NOMES_VISOES, NOTA_TPL11, RAMPA_AUMENTO, RAMPA_REDUCAO, ROTULOS_GENERICOS, aplicarPedido, apoioDaFamilia,
  artigo, avisoDaFamilia, baseVazia, bloqueioDoPedido, camadaDeCor, contextoDoGrafico, corOrdinal, corteAtivo, cronologica, definicaoInicial,
  disponibilidadeDaFamilia, escreverLimites, exibirCompetencia, familiaCalculada, formatarNumero, formatarVariacao, generoDe, grupoDaUnidade,
  grupoDoItem, gruposDaFonte, janelaDoAtalho, lerEstadoSalvo, lerLimites, limiteDaVariacao, lugarDoUniverso, maisRecente, montarCsv,
  chaveDoPedido, montarOpcoes, noCorte, pedidoDependeDoIndicador, nomeDaUnidade, novoConjunto, ordemNeutra, pintar, prefixoDe, rotulosEfetivos, salvarEstado, separarItens,
  maiuscula, textoDaMarca, textoDoMetodo, textoInstrucaoGrupos, tituloDaAnalise, trilhaDoUniverso, umA, visaoEfetiva,
  type AtalhoJanela, type ContextoDoGrafico, type Corte, type DefinicaoAnalise, type Disponivel, type Escala, type EstadoSalvo,
  type Familia, type FonteDados, type FuncaoPainel, type NiveisDaBase, type PassoTrilha, type PedidoDoChat, type UnidadeDoCatalogo,
  type Visao, type Vista,
} from "./painelModel";
import PainelChart, { type FaseAnimacao, type LinhaDeReferencia } from "./PainelChart";
import PainelSeries, { MAX_SERIES } from "./PainelSeries";
import PainelRotatividade from "./PainelRotatividade";
import PainelRuler from "./PainelRuler";
import PainelTerritorios from "./PainelTerritorios";
import PainelDetalhes from "./PainelDetalhes";
import { GavetaComparar, GavetaCondicoes, GavetaExportar, GavetaJanela, GavetaJuntar, GavetaOrdenar, GavetaReferencia } from "./PainelGavetas";
import "./analise.css";

// Área de análise da página única (22/10/2026): famílias (Distribuição, Análise espacial, Tendência, Rotatividade), o seletor
// único de indicador, o título dinâmico, a escolha dos territórios sempre à vista, a barra de funções com painéis laterais e,
// abaixo, os Detalhes. Estados E0 (antes dos dados) a E4 (funções em uso). Todo número vem do motor (/api/painel, pelo cliente
// painelApi.ts); a tela só posiciona, filtra (estado visual) e desenha. A conversa age sobre o gráfico pela prop `pedido`; a
// estrutura da página recebe o contexto (onContexto) e o estado salvo (onSalvar) e pode reabrir sem recalcular (restaurar).

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
  onEscolherFonte: (tipo: "brasil" | "arquivo") => void;
};

const MAX_CACHE = 6;
const FUNCOES: { chave: FuncaoPainel | "municipios"; rotulo: string; icone: ReactNode }[] = [
  { chave: "municipios", rotulo: "Municípios", icone: <MapaIcone size={15} aria-hidden="true"/> },
  { chave: "regua", rotulo: "Régua", icone: <Ruler size={15} aria-hidden="true"/> },
  { chave: "condicoes", rotulo: "Condições", icone: <Filter size={15} aria-hidden="true"/> },
  { chave: "ordenar", rotulo: "Ordenar", icone: <ListOrdered size={15} aria-hidden="true"/> },
  { chave: "comparar", rotulo: "Comparar", icone: <ArrowLeftRight size={15} aria-hidden="true"/> },
  { chave: "juntar", rotulo: "Juntar", icone: <Layers3 size={15} aria-hidden="true"/> },
  { chave: "exportar", rotulo: "Exportar", icone: <Download size={15} aria-hidden="true"/> },
];
const TITULOS_PAINEL: Record<FuncaoPainel, string> = { regua: "Régua", condicoes: "Condições", ordenar: "Ordenar", comparar: "Comparar",
  juntar: "Juntar", exportar: "Exportar", referencia: "Referência da distância", janela: "Janela da tendência" };

function useMovimentoReduzido(): boolean {
  const consulta = "(prefers-reduced-motion: reduce)";
  const [reduzido, setReduzido] = useState(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia(consulta).matches);
  useEffect(() => {
    if (!window.matchMedia) return;
    const media = window.matchMedia(consulta);
    const atualizar = () => setReduzido(media.matches);
    atualizar();
    media.addEventListener?.("change", atualizar);
    return () => media.removeEventListener?.("change", atualizar);
  }, []);
  return reduzido;
}

function baixar(nome: string, corpo: string, tipo: string) {
  const url = URL.createObjectURL(new Blob([corpo], { type: tipo }));
  const link = document.createElement("a");
  link.href = url; link.download = nome; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function AreaDeAnalise(props: AreaDeAnaliseProps) {
  const { fonte, periodos, categorias, niveis, municipios, pedido, restaurar } = props;
  const tipo = fonte?.tipo ?? null;
  const chaveFonte = fonte ? [fonte.tipo, fonte.datasetVersion, fonte.nome, fonte.sheet, fonte.arquivo?.name ?? "", fonte.arquivo?.size ?? ""].join("|") : "";
  const grupos = useMemo(() => gruposDaFonte(niveis, municipios), [niveis, municipios]);
  const grupoDeMapa = useMemo(() => new Map(municipios.map(item => [item.id, grupoDaUnidade(item)])), [municipios]);
  const grupoDe = useCallback((id: string) => grupoDeMapa.get(id) ?? prefixoDe(id), [grupoDeMapa]);
  const pronto = !!fonte && periodos.length > 0 && (fonte.tipo !== "brasil" || !!niveis);
  // Planilha sem população: só a quantidade; as premissas do painel Colunas vão em todo pedido.
  const temPopulacao = tipo !== "arquivo" || !!fonte?.mapping?.population;
  const premissasDaFonte = tipo === "arquivo" ? fonte?.premissas : undefined;
  const movimentoReduzido = useMovimentoReduzido();

  const [def, setDef] = useState<DefinicaoAnalise>(() => definicaoInicial({ tipo, periodos, categoria: props.categoria, temGrupos: !!niveis,
    temPopulacao, premissas: premissasDaFonte }));
  /** Referência pedida na conversa por critério: a lista de candidatos abre nessa ordem. */
  const [criterioDoChat, setCriterioDoChat] = useState<PainelCriterio | null>(null);
  const [intencao, setIntencao] = useState<Familia | null>(null);
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
  const [motivoAberto, setMotivoAberto] = useState<Familia | null>(null);
  const [resposta, setResposta] = useState<PainelResposta | null>(null);
  const [calculado, setCalculado] = useState<{ chave: string; def: DefinicaoAnalise; familia: Familia; opcoes: PainelOpcoes } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<{ mensagem: string; pendencia: Pendencia | null } | null>(null);
  const [tentativa, setTentativa] = useState(0);
  const [aviso, setAviso] = useState("");
  const cache = useRef(new Map<string, PainelResposta>());
  const contextoRef = useRef(props.onContexto); contextoRef.current = props.onContexto;
  const salvarRef = useRef(props.onSalvar); salvarRef.current = props.onSalvar;
  const visualRef = useRef({ escala, corte, selecionados }); visualRef.current = { escala, corte, selecionados };
  const tituloPainelRef = useRef<HTMLHeadingElement>(null);
  const gatilhoRef = useRef<HTMLElement | null>(null);

  const rotulos = rotulosEfetivos(resposta?.rotulos, fonte?.rotulos, tipo);
  const temIdentificador = !!fonte?.mapping?.identity;
  const disponibilidade = resposta?.disponibilidade ?? null;
  const comBolhasDeGrupo = tipo === "brasil" && grupos.length > 0 && (disponibilidade?.estados?.disponivel ?? disponibilidade?.grupos?.disponivel ?? true);
  const disponivelDe = useCallback((familia: Familia): Disponivel => disponibilidadeDaFamilia(familia, { fonte: tipo, nivel: def.nivel,
    disponibilidade, temIdentificador, rotulos }), [tipo, def.nivel, disponibilidade, temIdentificador, rotulos]);
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
    setSoAtende(false); setFiltroClasse(null); setFaixasTexto(""); };
  useEffect(() => {
    if (!fonte) {
      if (iniciado.current) { iniciado.current = ""; cache.current.clear(); setResposta(null); setCalculado(null); setErro(null); reiniciarVisual();
        setDef(definicaoInicial({ tipo: null, periodos, categoria: props.categoria, temGrupos: false })); }
      return;
    }
    if (!pronto || iniciado.current === chaveFonte) return;
    iniciado.current = chaveFonte;
    cache.current.clear();
    reiniciarVisual();
    setResposta(null); setCalculado(null); setErro(null);
    let inicial = definicaoInicial({ tipo, periodos, categoria: props.categoria, familia: intencao ?? undefined, temGrupos: grupos.length > 0,
      temPopulacao, premissas: premissasDaFonte });
    setIntencao(null);
    const pendente = pedidoPendente.current ?? (pedido && pedido.id !== ultimoPedido.current ? pedido : null);
    if (pendente) {
      pedidoPendente.current = null;
      ultimoPedido.current = pendente.id;
      const resultado = aplicarPedido(inicial, pendente.pedido, { periodos, nomes, temGrupos: grupos.length > 0, grupoDe,
        disponivel: familia => disponibilidadeDaFamilia(familia, { fonte: tipo, nivel: inicial.nivel, disponibilidade: null, temIdentificador, rotulos }) });
      inicial = resultado.definicao;
      if (resultado.selecao) setSelecionados(resultado.selecao);
      if (resultado.abrir) setPainel(resultado.abrir);
      setCriterioDoChat(resultado.criterio);
      setAviso(["Pedido da conversa aplicado ao gráfico.", ...resultado.mensagens].join(" "));
    }
    setDef(inicial);
  }, [fonte, pronto, chaveFonte]);
  // Competência e categoria que chegam depois da fonte.
  useEffect(() => { if (pronto && !def.competencia && periodos.length) setDef(atual => ({ ...atual, competencia: maisRecente(periodos) })); }, [pronto, periodos]);
  useEffect(() => { if (!def.categoria && props.categoria) setDef(atual => ({ ...atual, categoria: props.categoria })); }, [props.categoria]);

  // ------------------------------------------------------------------------------------------ pedido ao motor
  const dispAtual = disponivelDe(def.familia);
  const familiaPedida = familiaCalculada(def, dispAtual.disponivel && !dispAtual.pendente);
  const bloqueio = pronto ? bloqueioDoPedido(def, { fonte: tipo, rotulos }) : "Preparando os dados…";
  const opcoes = useMemo(() => bloqueio ? null : montarOpcoes(def, familiaPedida, grupoDe), [def, familiaPedida, bloqueio, grupoDe]);
  const chave = opcoes ? chaveFonte + "::" + chaveDoPedido(opcoes) : "";
  const fonteMotor: FonteDoMotor | null = useMemo(() => fonte ? { tipo: fonte.tipo, apiBase: fonte.apiBase, datasetVersion: fonte.datasetVersion,
    sheet: fonte.sheet, mapping: fonte.mapping, arquivo: fonte.arquivo, geoVersion: fonte.geoVersion } : null, [fonte]);
  const lugarDe = useCallback((d: DefinicaoAnalise) => lugarDoUniverso({ nivel: d.nivel, base: d.base, conjuntos: d.conjuntos.length, grupos,
    rotulos, brasil: tipo === "brasil", grupoDe }), [grupos, rotulos, tipo, grupoDe]);
  const tituloDe = useCallback((d: DefinicaoAnalise, familia: Familia, r: PainelResposta | null) => tituloDaAnalise({ fonte: tipo, familia,
    visao: visaoEfetiva(d), indicador: d.indicador, nivel: d.nivel, categoria: d.categoria, competencia: d.competencia, janela: d.janela,
    rotatividade: d.rotatividade, lugar: lugarDe(d), rotulos,
    referencia: d.referencia ? (r?.referencia?.membros.map(m => m.rotulo).join(" e ") || d.referencia.membros.map(id => nomes.get(id) || id).join(" e ")) : null }),
  [tipo, lugarDe, rotulos, nomes]);

  // Histórico: a restauração roda antes do pedido ao motor, para a resposta guardada entrar no cache antes; assim, reabrir
  // uma análise igual ao estado inicial (os estados) não pede de novo.
  const ultimoRestaurado = useRef<EstadoSalvo | null>(null);
  useEffect(() => {
    if (!restaurar || restaurar === ultimoRestaurado.current || !pronto || iniciado.current !== chaveFonte) return;
    ultimoRestaurado.current = restaurar;
    const lido = lerEstadoSalvo(restaurar);
    if (!lido) { setAviso("Não foi possível reabrir esta análise: o estado salvo não tem a forma esperada."); return; }
    reiniciarVisual();
    setEscala(lido.visual.escala); setCorte(lido.visual.corte); setSelecionados(lido.visual.selecionados);
    setDef(lido.definicao);
    if (lido.resposta && lido.opcoes) {
      cache.current.set(lido.chave, lido.resposta);
      setResposta(lido.resposta);
      setCalculado({ chave: lido.chave, def: lido.definicao, familia: lido.familia, opcoes: lido.opcoes });
    }
    setAviso("Análise reaberta do Histórico, sem recalcular.");
  }, [restaurar, pronto, chaveFonte]);

  useEffect(() => {
    if (!fonteMotor || !opcoes) { setCarregando(false); return; }
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
            definicao: pedidoDef, visual: { escala: visual.escala, corte: null, selecionados: visual.selecionados } }, corpo));
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
    setDef(calculado.def);
    setAviso("De volta ao último gráfico calculado.");
  }

  // ------------------------------------------------------------------------------------------ comando da conversa e Histórico
  useEffect(() => {
    if (!pedido || pedido.id === ultimoPedido.current) return;
    if (!pronto || iniciado.current !== chaveFonte) { pedidoPendente.current = pedido; return; }
    ultimoPedido.current = pedido.id;
    const resultado = aplicarPedido(def, pedido.pedido, { periodos, nomes, temGrupos: comBolhasDeGrupo, disponivel: disponivelDe, grupoDe });
    setDef(resultado.definicao);
    if (resultado.selecao) setSelecionados(resultado.selecao);
    if (resultado.abrir) setPainel(resultado.abrir);
    setCriterioDoChat(resultado.criterio);
    const base = resultado.definicao.base;
    if (resultado.definicao.nivel === "municipios" && base.estados.length === 1 && !base.ids.length) setAberto(base.estados[0]);
    if (resultado.definicao.nivel === "estados") setAberto(null);
    setAviso(["Pedido da conversa aplicado ao gráfico.", ...resultado.mensagens].join(" "));
  }, [pedido, pronto, chaveFonte]);


  // ------------------------------------------------------------------------------------------ reproduzir (Mudança e Classes)
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
  const tendenciaNaTela = familiaDesenho === "tendencia" && !!resposta?.competencia_inicial;
  // A visão é só estado visual: segue a escolha atual, desde que o motor tenha devolvido a tendência (quatro competências ou mais).
  const temTendencia = tendenciaNaTela && defDesenho.janela.length >= MINIMO_TENDENCIA && (!!resposta?.tendencia || !!resposta?.itens.some(item => item.tendencia));
  const visaoNaTela: Visao = !tendenciaNaTela ? "mudanca" : def.visao !== "mudanca" && temTendencia ? def.visao : "mudanca";
  const series = visaoNaTela === "series";
  const cometa = tendenciaNaTela && visaoNaTela !== "series";
  const camada = tendenciaNaTela ? (visaoNaTela === "mudanca" ? "variacao" : "classes") : camadaDeCor(familiaDesenho, visaoDesenho, resposta, defDesenho);
  const camadaFinal = resposta?.condicoes && defDesenho.condicoes.length ? "condicoes" : resposta?.ordenacao && defDesenho.ordenar ? "ordem" : camada;
  const exibicao = { distancia: distanciaNaTela, variacao: tendenciaNaTela && visaoNaTela === "mudanca",
    tendencia: tendenciaNaTela && visaoNaTela !== "mudanca", condicoes: !!resposta?.condicoes && defDesenho.condicoes.length > 0,
    rotatividade: familiaDesenho === "rotatividade" };
  const { plotaveis, fora } = useMemo(() => resposta ? separarItens(resposta.itens, indicador, exibicao) : { plotaveis: [], fora: [] },
    [resposta, indicador, exibicao.distancia, exibicao.variacao, exibicao.tendencia, exibicao.condicoes, exibicao.rotatividade]);
  const visiveis = useMemo(() => plotaveis.filter(item => noCorte(item, indicador, corte) &&
    (!soAtende || !exibicao.condicoes || item.condicoes?.situacao === "ATENDE") &&
    (!filtroClasse || !exibicao.tendencia || (filtroClasse === "NAO_AVALIAVEL" ? !item.tendencia?.avaliavel : item.tendencia?.classe === filtroClasse))),
  [plotaveis, indicador, corte, soAtende, filtroClasse, exibicao.condicoes, exibicao.tendencia]);
  const selecao = useMemo(() => selecionados.filter(id => (resposta?.itens || []).some(item => item.id === id)), [selecionados, resposta]);
  const limiteVariacao = useMemo(() => resposta ? limiteDaVariacao(resposta, indicador, plotaveis) : 0, [resposta, indicador, plotaveis]);
  const totalGrupos = resposta?.grupos ? ({ quartis: 4, quintis: 5, decis: 10 } as Record<string, number>)[resposta.grupos.tipo] ?? resposta.grupos.contagens.length : 0;
  const totalFaixas = resposta?.faixas ? Math.max(resposta.faixas.rotulos.length, resposta.faixas.contagens.length) : 0;
  const primeiros = resposta?.ordenacao?.primeiros ?? null;
  const pintura = useMemo(() => {
    const parametros = { camada: camadaFinal, indicador, limiteVariacao, totalGrupos, totalFaixas, primeiros };
    return (item: PainelItem) => pintar(item, parametros);
  }, [camadaFinal, indicador, limiteVariacao, totalGrupos, totalFaixas, primeiros]);
  const limiares = useMemo(() => corte ? [corte.minimo, corte.maximo] : [], [corte]);
  const dominio = resposta?.dominios[indicador] ?? null;
  const logPossivel = !!dominio && dominio[0] > 0;
  const idsNaTela = useMemo(() => visiveis.map(item => item.id), [visiveis]);
  const { titulo, subtitulo } = tituloDe(def, familiaPedida, resposta);
  const contexto = useMemo(() => contextoDoGrafico(def, idsNaTela, titulo, grupoDe), [def, idsNaTela, titulo, grupoDe]);
  const ultimoContexto = useRef("");
  useEffect(() => {
    const json = JSON.stringify(contexto);
    if (json === ultimoContexto.current) return;
    ultimoContexto.current = json;
    contextoRef.current(contexto);
  }, [contexto]);

  // ------------------------------------------------------------------------------------------ ações
  const mudar = (parte: Partial<DefinicaoAnalise>) => setDef(atual => ({ ...atual, ...parte }));
  const alternar = useCallback((id: string) =>
    setSelecionados(atual => atual.includes(id) ? atual.filter(item => item !== id) : [...atual, id]), []);
  function escolherFamilia(familia: Familia) {
    const disponivel = disponivelDe(familia);
    if (!fonte) { setIntencao(familia); setAviso("Você escolheu " + NOMES_FAMILIAS[familia] + ". Agora escolha os dados."); return; }
    if (!disponivel.disponivel) { setMotivoAberto(familia); setAviso(NOMES_FAMILIAS[familia] + " indisponível: " + disponivel.motivo); return; }
    setMotivoAberto(null);
    mudar({ familia });
    setFiltroClasse(null);
    if (familia === "espacial" && !def.referencia && def.nivel === "municipios") abrirPainel("referencia");
    else if (familia === "tendencia" && def.janela.length < 2 && def.nivel === "municipios") abrirPainel("janela");
    else if (painel === "referencia" || painel === "janela") setPainel(null);
    if (disponivel.pendente) setAviso(NOMES_FAMILIAS[familia] + ": " + disponivel.motivo);
  }
  function teclasFamilias(event: KeyboardEvent<HTMLButtonElement>, indice: number) {
    const proxima = event.key === "ArrowRight" ? (indice + 1) % FAMILIAS.length : event.key === "ArrowLeft" ? (indice + FAMILIAS.length - 1) % FAMILIAS.length
      : event.key === "Home" ? 0 : event.key === "End" ? FAMILIAS.length - 1 : null;
    if (proxima === null) return;
    event.preventDefault();
    document.getElementById("analise-familia-" + FAMILIAS[proxima])?.focus();
  }
  function irParaGrupos() {
    mudar({ nivel: "estados" });
    setAberto(null); setSelecionados([]); setCorte(null);
    const grupo = rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
    setAviso("De volta " + (generoDe(grupo) === "f" ? "às " : "aos ") + grupo.plural + ".");
  }
  /** Com as unidades à vista, a família que esperava por elas pede o que falta (a referência ou a janela). */
  function pedirOQueFalta() {
    if (def.familia === "espacial" && !def.referencia && disponivelDe("espacial").disponivel) abrirPainel("referencia");
    else if (def.familia === "tendencia" && def.janela.length < 2 && disponivelDe("tendencia").disponivel) abrirPainel("janela");
  }
  function verGrupo(grupo: string) {
    mudar({ nivel: "municipios", base: { todos: false, estados: [grupo], ids: [] } });
    setAberto(grupo); setSelecionados([]); setCorte(null);
    const info = grupos.find(item => item.id === grupo);
    setAviso("Mostrando " + (info ? info.nome : grupo) + ".");
    pedirOQueFalta();
  }
  function abrirGrupoDaBolha(id: string) {
    const grupo = grupoDaBolha(id);
    if (grupo !== null) verGrupo(grupo);
    else setAviso("Não foi possível associar esta bolha a um item da lista de territórios.");
  }
  function todasAsUnidades() {
    mudar({ nivel: "municipios", base: { todos: true, estados: [], ids: [] } });
    setAberto(null); setSelecionados([]); setCorte(null);
    pedirOQueFalta();
  }
  function mudarBase(base: PainelMunicipios) {
    mudar({ nivel: "municipios", base });
    setCorte(null);
  }
  function acaoDaTrilha(passo: PassoTrilha) {
    if (!passo.acao) return;
    if (passo.acao.tipo === "estados") irParaGrupos();
    else if (passo.acao.tipo === "todos") todasAsUnidades();
    else verGrupo(passo.acao.id);
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
  function irParaTerritorios() {
    setFerramentas(false);
    const titulo = document.getElementById("analise-territorios-titulo");
    titulo?.scrollIntoView({ block: "start", behavior: movimentoReduzido ? "auto" : "smooth" });
    titulo?.focus({ preventScroll: true });
  }
  function juntar(rotulo: string) {
    const membros = selecao.filter(id => resposta?.itens.find(item => item.id === id)?.tipo === "municipio");
    if (membros.length < 2) return;
    const conjunto = novoConjunto(def.conjuntos, membros, rotulo);
    mudar({ conjuntos: [...def.conjuntos, conjunto] });
    setSelecionados([conjunto.id]);
    setAviso("Conjunto " + conjunto.rotulo + " criado. O motor devolve a bolha com a soma das contagens dos componentes.");
  }
  function aplicarReferencia(referencia: PainelReferenciaPedido) {
    mudar({ referencia: { ...referencia, membros: [...new Set(referencia.membros)] }, familia: "espacial" });
    setAviso("Referência pedida ao motor: o eixo horizontal passa a ser a distância.");
  }
  function mudarCompetencia(valor: string) { mudar({ competencia: valor }); setCorte(null); }
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
    mudar({ premissas: { ...def.premissas, [chavePendencia]: novo } });
    setAviso("Premissa confirmada: " + chavePendencia + " = " + valor + ".");
  }
  function exportarCsv() {
    if (!resposta) return;
    baixar("analise_" + (resposta.competencia || "grafico") + ".csv", montarCsv(resposta, { familia: familiaDesenho, indicador, rotulos }), "text/csv;charset=utf-8");
  }
  function exportarMetodo() {
    if (!resposta) return;
    baixar("metodo_" + (resposta.competencia || "grafico") + ".txt", textoDoMetodo(resposta, titulo, calculado?.opcoes ?? null), "text/plain;charset=utf-8");
  }

  // ------------------------------------------------------------------------------------------ partes da tela
  const unidade = rotulos.unidade;
  const semUnidades = def.nivel === "municipios" && baseVazia(def.base) && !def.conjuntos.length;
  const estadoTela = !fonte ? "E0" : def.nivel === "estados" || semUnidades ? "E1"
    : painel ? "E4" : def.familia !== "distribuicao" ? "E3" : "E2";
  const trilha = pronto ? trilhaDoUniverso({ nivel: def.nivel, base: def.base, grupos, rotulos, brasil: tipo === "brasil",
    temGrupos: comBolhasDeGrupo, total: niveis?.municipios.total ?? municipios.filter(item => !item.selection_reason).length, grupoDe }) : [];
  const avisoFamilia = pronto ? avisoDaFamilia(def, dispAtual) : null;
  const naVisaoDeGrupos = (resposta?.nivel ?? def.nivel) === "estados" && familiaDesenho === "distribuicao" && def.nivel === "estados";
  const funcaoDesabilitada = (chaveFuncao: FuncaoPainel | "municipios"): string | null => {
    if (!resposta && chaveFuncao !== "municipios") return "Disponível depois do primeiro gráfico.";
    if (familiaDesenho === "rotatividade" && ["regua", "condicoes", "ordenar", "comparar", "juntar"].includes(chaveFuncao))
      return "A rotatividade mostra barras da coorte inicial; esta função vale para as bolhas.";
    if (chaveFuncao === "juntar" && def.nivel === "estados") {
      const grupo = rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
      return "Na visão " + (generoDe(grupo) === "f" ? "das " : "dos ") + grupo.plural + ", Juntar fica desligado: " + unidade.plural + " e " +
        grupo.plural + " nunca se somam.";
    }
    if (chaveFuncao === "regua" && series) return "Na visão Séries, a régua não se aplica.";
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
  const rotuloDistancia = (defDesenho.referencia?.membros.length ?? 0) > 1 ? "Distância até o membro mais próximo da referência (km)" : "Distância até a referência (km)";

  const legendaCor = ((): ReactNode => {
    if (!resposta) return null;
    if (camadaFinal === "variacao") {
      const gradiente = "linear-gradient(to right, " + [...RAMPA_REDUCAO].reverse().join(", ") + " 48%, " + COR_NEUTRA + " 48% 52%, " +
        RAMPA_AUMENTO.map((cor, indice) => cor + (indice === 0 ? " 52%" : "")).join(", ") + ")";
      return <div data-testid="analise-legenda-cor" data-camada="variacao" className="max-w-xs">
        <div className="h-2.5 rounded-full" style={{ background: gradiente }} aria-hidden="true"/>
        <div className="relative mt-1 h-4 text-[11px] tabular-nums text-slate-600" aria-hidden="true">
          {([[0, -limiteVariacao], [50, 0], [100, limiteVariacao]] as const).map(([posicao, valor]) =>
            <span key={posicao} className="absolute whitespace-nowrap" style={{ left: posicao + "%", transform: posicao === 0 ? "none" : posicao === 100 ? "translateX(-100%)" : "translateX(-50%)" }}>
              {valor === 0 ? "0,00%" : formatarVariacao(valor)}</span>)}
        </div>
        <p className="mt-1 leading-4">Cor: variação da {especie.rotulo.toLowerCase()} entre {exibirCompetencia(resposta.competencia_inicial)} e{" "}
          {exibirCompetencia(resposta.competencia)}, do motor: azul é aumento; laranja, redução; cinza, sem mudança. Contínua, sem classes.</p>
      </div>;
    }
    const itensLegenda: { chave: string; cor: string | null; texto: string; contagem: number | null; vazada?: boolean }[] = [];
    if (camadaFinal === "classes") {
      (["CRESCIMENTO", "DECLINIO", "NENHUMA"] as const).forEach(familia => itensLegenda.push({ chave: familia, cor: CORES_TENDENCIA[familia],
        texto: NOMES_FAMILIA_TENDENCIA[familia], contagem: resposta.tendencia?.familias[familia] ?? null }));
      itensLegenda.push({ chave: "NAO_AVALIAVEL", cor: null, vazada: true, texto: "Não avaliável", contagem: resposta.tendencia?.naoAvaliaveis ?? resposta.tendencia?.contagens.NAO_AVALIAVEL ?? null });
    } else if (camadaFinal === "grupos" && resposta.grupos) {
      for (let i = 1; i <= totalGrupos; i++) itensLegenda.push({ chave: String(i), cor: corOrdinal(i, totalGrupos),
        texto: resposta.grupos.rotulos[i - 1] || i + "º grupo", contagem: resposta.grupos.contagens[i - 1] ?? null });
    } else if (camadaFinal === "faixas" && resposta.faixas) {
      resposta.faixas.rotulos.forEach((rotulo, i) => itensLegenda.push({ chave: String(i + 1), cor: corOrdinal(i + 1, totalFaixas), texto: rotulo,
        contagem: resposta.faixas!.contagens[i] ?? null }));
      if (resposta.faixas.fora !== null) itensLegenda.push({ chave: "fora", cor: COR_NEUTRA, texto: "Fora das faixas", contagem: resposta.faixas.fora });
    } else if (camadaFinal === "condicoes" && resposta.condicoes) {
      itensLegenda.push({ chave: "ATENDE", cor: COR_BOLHA, texto: "Atendem a todas as condições", contagem: resposta.condicoes.contagens.ATENDE ?? null },
        { chave: "NAO_ATENDE", cor: COR_NEUTRA, texto: "Não atendem", contagem: resposta.condicoes.contagens.NAO_ATENDE ?? null },
        { chave: "NAO_AVALIAVEL", cor: null, vazada: true, texto: "Sem dado para avaliar", contagem: resposta.condicoes.contagens.NAO_AVALIAVEL ?? null });
    } else if (camadaFinal === "ordem" && resposta.ordenacao) {
      itensLegenda.push({ chave: "primeiros", cor: COR_BOLHA, texto: primeiros !== null ? "Os " + primeiros + " primeiros (posições do motor" +
        (resposta.ordenacao.empatesNoCorte ? ", com os empatados no corte)" : ")") : "Com posição na ordenação", contagem: null },
        { chave: "demais", cor: COR_NEUTRA, texto: "Demais", contagem: null });
    }
    if (!itensLegenda.length) return null;
    return <ul data-testid="analise-legenda-cor" data-camada={camadaFinal} className="flex flex-col gap-1" aria-label="Legenda das cores">
      {itensLegenda.map(item => <li key={item.chave} data-testid="analise-legenda-cor-item" data-chave={item.chave} data-contagem={item.contagem ?? ""}
        className="flex items-center gap-1.5">
        <span className="analise-amostra-bolha" style={item.vazada ? { background: "#fff", border: "1.5px dashed #898781" } : { background: item.cor ?? COR_BOLHA }} aria-hidden="true"/>
        <span>{item.texto}{item.contagem !== null ? <> · <strong className="tabular-nums text-ink">{formatarNumero(item.contagem, true)}</strong></> : ""}</span>
      </li>)}
      {camadaFinal === "grupos" && totalGrupos > 5 && <li className="leading-4">Nos decis, só as linhas de corte: mais de cinco tons não se distinguem.</li>}
    </ul>;
  })();

  const notasDoGrafico = [
    // As bolhas de grupo só existem na base do Brasil (os estados, da fonte estadual de profissionais únicos).
    ...(resposta?.nivel === "estados" ? [maiuscula("cada " + (rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular) + " conta os profissionais únicos da " +
      "fonte estadual: quem atua em mais de " + umA(unidade) + " conta uma vez. A bolha não é a soma das bolhas d" + artigo(unidade, true) + " " +
      unidade.plural + ", e os dois níveis nunca aparecem juntos."] : []),
  ];
  const contagemClasses = exibicao.tendencia && resposta?.tendencia ? <div data-testid="analise-contagem-classes" className="analise-contagem-classes"
    role="group" aria-label="Contagem por classe de tendência, do motor (clique para filtrar)">
    {CLASSES_TENDENCIA.map(classe => {
      const n = resposta.tendencia!.contagens[classe.codigo];
      if (n === undefined) return null;
      return <button key={classe.codigo} type="button" data-testid="analise-contagem-classe" data-classe={classe.codigo} data-contagem={n}
        aria-pressed={filtroClasse === classe.codigo} className="analise-contagem" onClick={() => setFiltroClasse(atual => atual === classe.codigo ? null : classe.codigo)}>
        <span className="analise-amostra-bolha" style={{ background: CORES_TENDENCIA[classe.familia] }} aria-hidden="true"/>
        {classe.rotulo} <strong className="tabular-nums text-ink">{formatarNumero(n, true)}</strong></button>;
    })}
    {(resposta.tendencia.naoAvaliaveis ?? resposta.tendencia.contagens.NAO_AVALIAVEL) !== undefined && (resposta.tendencia.naoAvaliaveis ?? resposta.tendencia.contagens.NAO_AVALIAVEL) !== null &&
      <button type="button" data-testid="analise-contagem-classe" data-classe="NAO_AVALIAVEL"
        data-contagem={resposta.tendencia.naoAvaliaveis ?? resposta.tendencia.contagens.NAO_AVALIAVEL} aria-pressed={filtroClasse === "NAO_AVALIAVEL"}
        className="analise-contagem" onClick={() => setFiltroClasse(atual => atual === "NAO_AVALIAVEL" ? null : "NAO_AVALIAVEL")}>
        <span className="analise-amostra-bolha" style={{ background: "#fff", border: "1.5px dashed #898781" }} aria-hidden="true"/>
        Não avaliável <strong className="tabular-nums text-ink">{formatarNumero((resposta.tendencia.naoAvaliaveis ?? resposta.tendencia.contagens.NAO_AVALIAVEL) as number, true)}</strong></button>}
    {resposta.tendencia.bloqueio && <p className="w-full text-xs text-amber-900">{resposta.tendencia.bloqueio}</p>}
  </div> : null;

  const itensSeries = useMemo(() => {
    if (!series || !resposta) return [];
    const porId = new Map(resposta.itens.map(item => [item.id, item]));
    return selecao.map(id => porId.get(id)).filter((item): item is PainelItem => !!item && !!item.tendencia && item.tipo !== "estado");
  }, [series, resposta, selecao]);
  function seriesDaClasse(classe: string) {
    const lista = plotaveis.filter(item => item.tendencia?.classe === classe).sort(ordemNeutra).slice(0, MAX_SERIES).map(item => item.id);
    setSelecionados(lista);
  }

  const desenho = (() => {
    if (!fonte) return <div data-testid="analise-abertura" className="analise-abertura">
      <p className="analise-abertura-titulo">Escolha os dados para começar</p>
      <p className="max-w-md text-sm leading-6 text-slate-600">Comece com os dados do Brasil, com os estados e municípios já preparados, ou envie a sua
        planilha. O aceite de privacidade vem antes.</p>
      <div className="flex flex-wrap justify-center gap-2">
        <button type="button" data-testid="analise-fonte-brasil" className="analise-botao-primario" onClick={() => props.onEscolherFonte("brasil")}>
          <Database size={16} aria-hidden="true"/>Dados do Brasil</button>
        <button type="button" data-testid="analise-fonte-arquivo" className="analise-botao-secundario" onClick={() => props.onEscolherFonte("arquivo")}>
          <Upload size={16} aria-hidden="true"/>Enviar meus dados</button>
      </div>
      {intencao && <p data-testid="analise-intencao" role="status" className="text-sm text-teal">Você escolheu {NOMES_FAMILIAS[intencao]}. Agora escolha os dados.</p>}
    </div>;
    if (!pronto) return <p data-testid="analise-preparando" role="status" className="analise-vazio"><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>
      Preparando os dados…</p>;
    if (semUnidades) return <div data-testid="analise-vazio" className="analise-vazio">
      <p className="font-semibold text-ink">{bloqueio}</p>
      <p className="text-xs text-slate-600">Na lista de territórios, {grupos.length ? "abra " + umA(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!) + " ou " : ""}
        marque {unidade.plural}. Procurar pelo nome é opcional.</p>
      <button type="button" className="analise-botao-secundario" onClick={irParaTerritorios}>Ir para a lista de territórios</button>
    </div>;
    if (!resposta) return <p role="status" data-testid="analise-carregando" className="analise-vazio">{!erro && <><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>
      Pedindo os valores ao motor…</>}</p>;
    if (familiaDesenho === "rotatividade" && calculado?.def.rotatividade) return <PainelRotatividade itens={visiveis} rotulos={rotulos}
      inicial={calculado.def.rotatividade.inicial} final={calculado.def.rotatividade.final}/>;
    if (series) return itensSeries.length ? <PainelSeries itens={itensSeries} janela={resposta.tendencia?.janela.length ? resposta.tendencia.janela : defDesenho.janela}
      indicador={indicador} rotulos={rotulos} unidadeTempo={resposta.tendencia?.unidadeTempo ?? null}/>
      : <div data-testid="analise-series-vazio" className="analise-vazio">
        <p className="font-semibold text-ink">Escolha até {MAX_SERIES} {unidade.plural} para ver as séries.</p>
        <p className="text-xs text-slate-600">Marque na tabela (Detalhes) ou clique nas bolhas na visão Classes. Ou use {artigo(unidade, true)} de uma classe:</p>
        <div className="flex flex-wrap justify-center gap-1.5">{CLASSES_TENDENCIA.filter(classe => (resposta.tendencia?.contagens[classe.codigo] ?? 0) > 0).map(classe =>
          <button key={classe.codigo} type="button" data-testid="analise-series-classe" data-classe={classe.codigo} className="analise-chip" onClick={() => seriesDaClasse(classe.codigo)}>
            {classe.rotulo}</button>)}</div>
      </div>;
    return <PainelChart resposta={resposta} itens={visiveis} todos={plotaveis} indicador={indicador} escala={escala} distancia={distanciaNaTela}
      cometa={cometa} vista={vista} fase={fase} pintura={pintura} selecionados={selecao} limiares={limiares} nomes={nomes} carregando={carregando}
      rotuloDistancia={rotuloDistancia} rotulos={rotulos} contextoBrasil={contextoBrasil} cortes={cortes} corte={corteAtivo(corte, dominio) ? corte : null}
      faixasDistancia={faixasDistancia} unidadesDoGrupo={unidadesDoGrupo} legendaCor={legendaCor} notas={notasDoGrafico}
      extraDoRotulo={camadaFinal === "ordem" ? item => item.ordem?.posicao !== null && item.ordem && (primeiros === null || item.ordem.posicao <= primeiros) && (primeiros ?? 99) <= 12
        ? item.ordem.posicao + "º" : null : undefined}
      rotuloSempre={item => item.tipo === "estado" || (camadaFinal === "ordem" && primeiros !== null && primeiros <= 12 && item.ordem?.posicao !== null &&
        item.ordem !== null && (item.ordem.posicao as number) <= primeiros)}
      onAlternar={alternar} onAbrirGrupo={abrirGrupoDaBolha}/>;
  })();

  const conteudoPainel = (() => {
    if (!painel || !fonteMotor) return null;
    switch (painel) {
      case "regua": return resposta ? <PainelRuler indicador={indicador} dominio={dominio} escala={escala} corte={corte} onCorte={setCorte}
        plural={naVisaoDeGrupos ? rotulos.grupo?.plural ?? "grupos" : unidade.plural}/> : null;
      case "referencia": return <GavetaReferencia fonte={fonteMotor} competencia={def.competencia} categoria={def.categoria} base={def.base}
        conjuntos={def.conjuntos} pedida={def.referencia} ativa={distanciaNaTela ? resposta?.referencia ?? null : null} nomes={nomes} rotulos={rotulos}
        catalogo={municipios} premissas={def.premissas} faixas={def.faixasDistancia} criterioInicial={criterioDoChat} onAplicar={aplicarReferencia}
        onRemover={() => { mudar({ referencia: null, faixasDistancia: [] }); setAviso("Referência removida: volta o eixo único."); }}
        onFaixas={limites => mudar({ faixasDistancia: limites })}/>;
      case "janela": return <GavetaJanela periodos={periodos} janela={def.janela} onAplicar={janela => { mudar({ janela, familia: "tendencia" }); setFiltroClasse(null); }}/>;
      case "condicoes": return <GavetaCondicoes condicoes={def.condicoes} espacial={distanciaNaTela} resposta={resposta} rotulos={rotulos}
        soAtende={soAtende} onSoAtende={setSoAtende} onAplicar={condicoes => mudar({ condicoes })}/>;
      case "ordenar": return <GavetaOrdenar ordenar={def.ordenar} espacial={distanciaNaTela} mudanca={exibicao.variacao} resposta={resposta}
        indicador={indicador} onAplicar={ordenar => mudar({ ordenar })}/>;
      case "comparar": return <GavetaComparar itens={resposta?.itens || []} selecionados={selecao} pedidos={def.comparar} resposta={resposta}
        indicador={indicador} distancia={distanciaNaTela} variacao={exibicao.variacao} competenciaInicial={resposta?.competencia_inicial ?? null}
        nomes={nomes} onAlternar={alternar} onLimpar={() => { setSelecionados([]); mudar({ comparar: [] }); }} onComparar={ids => mudar({ comparar: ids })}/>;
      case "juntar": return <GavetaJuntar itens={resposta?.itens || []} selecionados={selecao} conjuntos={def.conjuntos} rotulos={rotulos}
        nivelGrupos={def.nivel === "estados"} onJuntar={juntar}
        onDesfazer={id => { mudar({ conjuntos: def.conjuntos.filter((item: PainelConjuntoPedido) => item.id !== id) }); setSelecionados(atual => atual.filter(item => item !== id)); }}/>;
      case "exportar": return <GavetaExportar pronto={!!resposta} onCsv={exportarCsv} onImprimir={() => window.print()} onMetodo={exportarMetodo}/>;
      default: return null;
    }
  })();

  const opcoesDaFamilia = (() => {
    if (!pronto) return null;
    const partes: ReactNode[] = [];
    if (def.familia === "distribuicao" || def.nivel === "estados") {
      partes.push(<label key="agrupar" className="analise-rotulo-campo">Grupos e faixas
        <select data-testid="analise-agrupar" value={def.agrupar.tipo} className="analise-campo"
          onChange={event => mudar({ agrupar: { tipo: event.target.value as DefinicaoAnalise["agrupar"]["tipo"], faixas: def.agrupar.faixas } })}>
          <option value="nenhum">Nenhum</option><option value="quartis">Quartis</option><option value="quintis">Quintis</option>
          <option value="decis">Decis (só as linhas de corte)</option><option value="faixas">Faixas digitadas</option>
        </select>
      </label>);
      if (def.agrupar.tipo === "faixas") partes.push(<div key="faixas" className="flex items-end gap-1.5">
        <label className="analise-rotulo-campo">Limites ({especie.contagem ? "profissionais" : "por 1.000 hab."})
          <input data-testid="analise-faixas" value={faixasTexto || escreverLimites(def.agrupar.faixas)} placeholder="0; 1; 2; 5" inputMode="decimal"
            onChange={event => setFaixasTexto(event.target.value)} className="analise-campo w-36"/>
        </label>
        <button type="button" data-testid="analise-faixas-aplicar" className="analise-botao-secundario" disabled={lerLimites(faixasTexto).length < 2}
          onClick={() => { mudar({ agrupar: { tipo: "faixas", faixas: lerLimites(faixasTexto) } }); setFaixasTexto(""); }}>Aplicar faixas</button>
      </div>);
    }
    if (def.familia === "espacial" && def.nivel === "municipios") partes.push(<div key="ref" className="flex flex-wrap items-end gap-1.5">
      <span className="analise-rotulo-campo">Referência
        <span data-testid="analise-referencia-resumo" className="analise-resumo">{def.referencia
          ? (resposta?.referencia?.membros.map(m => m.rotulo).join(", ") || def.referencia.membros.map(id => nomes.get(id) || id).join(", ")) : "nenhuma ainda"}</span>
      </span>
      <button type="button" data-testid="analise-referencia-escolher" className="analise-botao-secundario" onClick={() => abrirPainel("referencia")}>
        {def.referencia ? "Mudar" : "Escolher a referência"}</button>
    </div>);
    if (def.familia === "tendencia" && def.nivel === "municipios") {
      partes.push(<div key="janela" className="flex flex-wrap items-end gap-1.5">
        <span className="analise-rotulo-campo">Janela
          <span data-testid="analise-janela-texto" className="analise-resumo">{def.janela.length >= 2
            ? exibirCompetencia(def.janela[0]) + " a " + exibirCompetencia(def.janela[def.janela.length - 1]) + " (" + def.janela.length + " competências)" : "escolha"}</span>
        </span>
        {(Object.keys(ATALHOS_JANELA) as AtalhoJanela[]).map(atalho => {
          const valor = janelaDoAtalho(atalho, periodos);
          return <button key={atalho} type="button" data-testid={"analise-janela-rapida-" + atalho} className="analise-botao-secundario" disabled={valor.length < 2}
            aria-pressed={valor.length >= 2 && valor.join() === def.janela.join()} onClick={() => { mudar({ janela: valor }); setFiltroClasse(null); if (painel === "janela") setPainel(null); }}>
            {ATALHOS_JANELA[atalho]}</button>;
        })}
        <button type="button" data-testid="analise-janela-escolher" className="analise-botao-secundario" onClick={() => abrirPainel("janela")}>Outra</button>
      </div>);
      partes.push(<div key="visao" role="group" aria-label="Visão da tendência" className="analise-segmentos">
        {(["mudanca", "classes", "series"] as Visao[]).map(visao => <button key={visao} type="button" data-testid={"analise-visao-" + visao}
          aria-pressed={def.visao === visao} disabled={visao !== "mudanca" && def.janela.length > 0 && def.janela.length < MINIMO_TENDENCIA}
          title={visao !== "mudanca" && def.janela.length < MINIMO_TENDENCIA ? "A tendência exige pelo menos " + MINIMO_TENDENCIA + " competências." : undefined}
          onClick={() => { mudar({ visao }); setFiltroClasse(null); }}>{NOMES_VISOES[visao]}</button>)}
      </div>);
      if (cometa) partes.push(<div key="vista" className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Competência mostrada">
        {(["inicial", "final"] as const).map(qual => <button key={qual} type="button" data-testid={"analise-vista-" + qual} aria-pressed={vista === qual}
          disabled={fase !== "parado"} className="analise-botao-secundario" onClick={() => setVista(qual)}>
          {qual === "inicial" ? "Primeira (" + exibirCompetencia(resposta?.competencia_inicial) + ")" : "Última (" + exibirCompetencia(resposta?.competencia) + ")"}</button>)}
        <button type="button" data-testid="analise-reproduzir" className="analise-botao-secundario" disabled={fase !== "parado"} onClick={reproduzir}>
          {fase !== "parado" ? <Pause size={14} aria-hidden="true"/> : <Play size={14} aria-hidden="true"/>}
          {movimentoReduzido || plotaveis.length > LIMITE_LEVE ? "Ir para a última" : "Reproduzir"}</button>
      </div>);
    }
    if (def.familia === "rotatividade" && dispAtual.disponivel) {
      const ordenadas = cronologica(periodos);
      partes.push(<div key="rot" className="flex flex-wrap items-end gap-1.5">
        <label className="analise-rotulo-campo">Período inicial da coorte
          <select data-testid="analise-rot-inicial" value={def.rotatividade?.inicial ?? ""} className="analise-campo"
            onChange={event => mudar({ rotatividade: { inicial: event.target.value, final: def.rotatividade?.final ?? "" } })}>
            <option value="">Escolha</option>{ordenadas.slice(0, -1).map(c => <option key={c} value={c}>{exibirCompetencia(c)}</option>)}
          </select>
        </label>
        <label className="analise-rotulo-campo">Período final
          <select data-testid="analise-rot-final" value={def.rotatividade?.final ?? ""} className="analise-campo"
            onChange={event => mudar({ rotatividade: { inicial: def.rotatividade?.inicial ?? "", final: event.target.value } })}>
            <option value="">Escolha</option>{ordenadas.filter(c => !def.rotatividade?.inicial || c > def.rotatividade.inicial).map(c =>
              <option key={c} value={c}>{exibirCompetencia(c)}</option>)}
          </select>
        </label>
      </div>);
    }
    return partes;
  })();

  const motivoFamilia = motivoAberto ? disponivelDe(motivoAberto) : null;

  return <section id="area-de-analise" data-testid="area-de-analise" data-estado={estadoTela} data-familia={def.familia} data-nivel={def.nivel}
    aria-labelledby="analise-titulo" className="analise">
    {/* Famílias: abas (roláveis no celular). Clicar antes dos dados registra a intenção. */}
    <div role="tablist" aria-label="Análises" className="analise-familias analise-nao-imprimir">
      {FAMILIAS.map((familia, indice) => {
        const disponivel = disponivelDe(familia);
        const ativa = (fonte ? def.familia : intencao ?? "distribuicao") === familia;
        return <button key={familia} id={"analise-familia-" + familia} type="button" role="tab" data-testid={"analise-familia-" + familia}
          aria-selected={ativa} aria-disabled={!disponivel.disponivel || undefined} aria-controls="analise-centro" tabIndex={ativa ? 0 : -1}
          title={!disponivel.disponivel ? disponivel.motivo : undefined}
          className={"analise-familia" + (!disponivel.disponivel ? " analise-familia-indisponivel" : "")}
          onClick={() => escolherFamilia(familia)} onKeyDown={event => teclasFamilias(event, indice)}>
          <span className="analise-familia-nome">{NOMES_FAMILIAS[familia]}</span>
          <span className="analise-familia-apoio">{!disponivel.disponivel ? (disponivel.enviarDados ? "Só com dados enviados" : "Indisponível nesta fonte")
            : apoioDaFamilia(familia, rotulos)}</span>
        </button>;
      })}
    </div>
    {motivoFamilia && !motivoFamilia.disponivel && <p data-testid="analise-familia-motivo" role="status" className="analise-motivo">
      <strong className="text-ink">{NOMES_FAMILIAS[motivoAberto!]}:</strong> {motivoFamilia.motivo}
      {motivoFamilia.enviarDados && <button type="button" data-testid="analise-enviar-dados" className="analise-botao-secundario ml-2"
        onClick={() => props.onEscolherFonte("arquivo")}><Upload size={14} aria-hidden="true"/>Enviar meus dados</button>}
      <button type="button" className="analise-icone ml-1" aria-label="Fechar o motivo" onClick={() => setMotivoAberto(null)}><X size={14} aria-hidden="true"/></button>
    </p>}

    {pronto && <div className="analise-opcoes analise-nao-imprimir">
      <div role="radiogroup" aria-label="Indicador" className="analise-segmentos">
        {(["densidade", "quantidade"] as const).map(valor => <button key={valor} type="button" role="radio" aria-checked={def.indicador === valor}
          data-testid={"analise-indicador-" + valor} onClick={() => { mudar({ indicador: valor }); setCorte(null); }}>{INDICADORES[valor].rotulo}</button>)}
      </div>
      {(def.familia === "distribuicao" || def.familia === "espacial" || def.nivel === "estados" || !dispAtual.disponivel) && <label className="analise-rotulo-campo">Competência
        <select data-testid="analise-competencia" value={def.competencia} onChange={event => mudarCompetencia(event.target.value)} className="analise-campo">
          {cronologica(periodos).reverse().map(periodo => <option key={periodo} value={periodo}>{exibirCompetencia(periodo)}</option>)}
        </select>
      </label>}
      {categorias.length > 1 && <label className="analise-rotulo-campo">Categoria
        <select data-testid="analise-categoria" value={def.categoria} onChange={event => mudar({ categoria: event.target.value })} className="analise-campo">
          {categorias.map(valor => <option key={valor} value={valor}>{valor}</option>)}
        </select>
      </label>}
      {opcoesDaFamilia}
      {familiaDesenho !== "rotatividade" && !series && <label className="analise-rotulo-campo">Escala
        <select data-testid="analise-escala" value={logPossivel ? escala : "linear"} onChange={event => setEscala(event.target.value as Escala)} className="analise-campo">
          <option value="linear">Linear (a partir do zero)</option>
          <option value="logaritmica" disabled={!logPossivel}>Logarítmica{logPossivel ? "" : " (exige valores positivos)"}</option>
        </select>
      </label>}
    </div>}

    <header className="analise-cabecalho">
      {trilha.length > 0 && <nav aria-label="Onde estou" data-testid="analise-trilha" className="analise-trilha analise-nao-imprimir">
        <ol>{trilha.map((passo, indice) => <li key={indice}>
          {indice > 0 && <ChevronRight size={13} aria-hidden="true" className="text-slate-400"/>}
          {passo.acao ? <button type="button" data-testid="analise-trilha-item" data-acao={passo.acao.tipo} className="analise-link" onClick={() => acaoDaTrilha(passo)}>
            {passo.rotulo}</button>
            : <span data-testid="analise-trilha-atual" aria-current="location">{passo.rotulo}</span>}
        </li>)}</ol>
      </nav>}
      <h2 id="analise-titulo" tabIndex={-1} data-testid="analise-titulo" className="analise-titulo">{titulo}</h2>
      <p data-testid="analise-subtitulo" className="analise-subtitulo">{subtitulo}</p>
    </header>

    <div className={"analise-corpo" + (!fonte ? " analise-corpo-abertura" : "") + (painel ? " analise-corpo-com-painel" : "")}>
      {pronto && <div className="analise-coluna-territorios analise-nao-imprimir">
        <PainelTerritorios rotulos={rotulos} brasil={tipo === "brasil"} grupos={grupos} comBolhasDeGrupo={comBolhasDeGrupo} unidades={municipios}
          total={niveis?.municipios.total ?? municipios.filter(item => !item.selection_reason).length} nivel={def.nivel} base={def.base} aberto={aberto}
          desabilitado={false} onGrupos={irParaGrupos} onTodas={todasAsUnidades} onVer={verGrupo} onFechar={() => setAberto(null)} onBase={mudarBase}/>
      </div>}

      <div id="analise-centro" className="analise-centro">
        {fonte && pronto && <div className="analise-funcoes analise-nao-imprimir">
          <button type="button" data-testid="analise-ferramentas" className="analise-ferramentas-botao" aria-expanded={ferramentas}
            aria-controls="analise-funcoes-lista" onClick={() => setFerramentas(valor => !valor)}><Wrench size={15} aria-hidden="true"/>Ferramentas</button>
          <div id="analise-funcoes-lista" role="toolbar" aria-label="Funções" className={"analise-funcoes-lista" + (ferramentas ? " analise-funcoes-abertas" : "")}>
            {FUNCOES.map(funcao => {
              const motivo = funcaoDesabilitada(funcao.chave);
              const rotulo = funcao.chave === "municipios" ? "Territórios" : funcao.rotulo;
              return <button key={funcao.chave} type="button" data-testid={"analise-funcao-" + funcao.chave} disabled={!!motivo} title={motivo ?? undefined}
                aria-expanded={funcao.chave === "municipios" ? undefined : painel === funcao.chave} aria-controls={funcao.chave === "municipios" ? undefined : "analise-painel"}
                className="analise-funcao" onClick={() => funcao.chave === "municipios" ? irParaTerritorios()
                  : painel === funcao.chave ? fecharPainel() : abrirPainel(funcao.chave as FuncaoPainel)}>
                {funcao.icone}{rotulo}{funcao.chave === "comparar" && selecao.length ? " (" + selecao.length + ")" : ""}</button>;
            })}
          </div>
        </div>}

        <div className="analise-avisos">
          {carregando && resposta && <p role="status" data-testid="analise-atualizando" className="analise-status"><LoaderCircle size={15} className="animate-spin" aria-hidden="true"/>
            Atualizando o gráfico no motor…</p>}
          {erro && <div role="alert" data-testid="analise-erro" className="analise-erro">
            <p>O motor não calculou o gráfico com a última mudança: {erro.mensagem}</p>
            {erro.pendencia && <div data-testid="analise-pendencia" className="mt-2 space-y-1.5">
              <p className="font-semibold">{erro.pendencia.texto || "O motor pede uma escolha antes de calcular."}</p>
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
          {avisoFamilia && fonte && <p data-testid="analise-aviso-familia" role="status" className="analise-aviso-familia">
            <SlidersHorizontal size={14} aria-hidden="true"/>{avisoFamilia}</p>}
          {resposta?.nivel === "estados" && def.nivel === "estados" && <p data-testid="analise-instrucao" className="analise-instrucao">
            <Scale size={14} aria-hidden="true"/>{textoInstrucaoGrupos(rotulos)}</p>}
        </div>

        {contagemClasses}
        <div className="analise-quadro">{desenho}</div>
        {distanciaNaTela && <p data-testid="analise-nota-distancia" className="analise-nota">{NOTA_TPL11} (TPL-11)</p>}
      </div>

      {painel && conteudoPainel && <aside id="analise-painel" data-testid="analise-painel" data-painel={painel} aria-labelledby="analise-painel-titulo"
        className="analise-painel analise-nao-imprimir" onKeyDown={event => { if (event.key === "Escape") { event.stopPropagation(); fecharPainel(); } }}>
        <div className="analise-painel-cabecalho">
          <h3 id="analise-painel-titulo" ref={tituloPainelRef} tabIndex={-1} className="text-sm font-bold text-ink outline-none">{TITULOS_PAINEL[painel]}</h3>
          <button type="button" data-testid="analise-painel-fechar" className="analise-icone" aria-label={"Fechar " + TITULOS_PAINEL[painel]} onClick={fecharPainel}>
            <X size={16} aria-hidden="true"/></button>
        </div>
        <div className="analise-painel-corpo">{conteudoPainel}</div>
      </aside>}
    </div>

    {resposta && fonte && pronto && !semUnidades && <PainelDetalhes resposta={resposta} itens={visiveis} fora={fora} familia={familiaDesenho} indicador={indicador}
      distancia={distanciaNaTela} variacao={exibicao.variacao} tendencia={exibicao.tendencia} rotulos={rotulos} selecionados={selecao}
      limiares={limiares} corteAtivo={corteAtivo(corte, dominio)} onAlternar={alternar}/>}
    <p aria-live="polite" className="sr-only" data-testid="analise-aviso">{aviso}</p>
  </section>;
}

