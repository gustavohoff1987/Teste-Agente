import { useCallback, useEffect, useMemo, useState } from "react";
import { Calculator, Layers3, LayoutGrid, LoaderCircle, MapPinned, RefreshCw, TrendingUp, UsersRound } from "lucide-react";
import type { Operation } from "./analysisCatalog";
import {
  pedirPainel, type PainelConjuntoPedido, type PainelFonte, type PainelIndicador, type PainelMunicipios, type PainelReferenciaPedido,
  type PainelResposta,
} from "./painelApi";
import {
  INDICADORES, LIMITE_LEVE, MAX_CONJUNTOS, avisosDe, baseInicial, cronologica, exibirCompetencia, formatarIndicador, formatarNumero,
  formatarVariacao, inicialDe, limiteDaVariacao, maisRecente, montarOpcoes, noCorte, normalizarBase, novoConjunto, numero, ordenarTabela, prefixoDe,
  semPedido, separarItens, textoDaContagem, textoDaLimitacao, variacaoDe, type ColunaTabela, type Corte, type DefinicaoPainel, type Escala,
  type NaoAvaliavel, type Ordenacao, type Vista,
} from "./painelModel";
import type { Levels } from "./territorialScope";
import type { Territory } from "./TerritorialSelection";
import PainelBase, { nomeDoMunicipio } from "./PainelBase";
import PainelChart, { type FaseAnimacao } from "./PainelChart";
import PainelRuler from "./PainelRuler";
import { GavetaComparar, GavetaCrescimento, GavetaReferencia } from "./PainelGavetas";

// Painel integrado de bolhas (21/10/2026): a experiência analítica acontece dentro de um gráfico grande. Densidade e Quantidade
// escolhem o indicador do eixo (estado visual); Distância, Crescimento e os conjuntos pedem ao motor (/api/painel) os valores que
// faltam. A régua, o destaque, a dica, a tabela e a vista do crescimento são só estado visual. Todo número vem do motor.

type Props = {
  fonte: PainelFonte;
  /** Competências da base municipal. */
  periodos: string[];
  categoria: string;
  categorias: string[];
  niveis: Levels;
  /** Municípios da base oficial (busca, lista e arrastar). */
  municipios: Territory[];
  /** Abrangência clássica no momento da abertura: vira o universo inicial dos municípios base. */
  escopoInicial: { todos: boolean; grupos: string[]; ids: string[] };
  /** Volta à preparação clássica; com uma análise, abre a preparação dela. */
  onClassica: (operacao?: Operation) => void;
};
type Gaveta = "distancia" | "crescimento" | "comparar";

const CLASSICAS: [Operation, string][] = [["distribution", "Distribuição"], ["ranking", "Rankings"], ["criteria", "Critérios combinados"],
  ["rotation", "Rotatividade"], ["report", "Relatórios"]];
const ASPECTOS: Record<NaoAvaliavel["aspecto"], string> = {
  indicador: "Sem valor do indicador na competência", distancia: "Sem distância até a referência", variacao: "Variação não avaliável",
};
/** Linhas da tabela equivalente por página: com milhares de municípios, a tabela inteira pesaria na tela. */
const POR_PAGINA = 100;
const BOTAO = "inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition disabled:opacity-40";

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

export default function PainelIntegrado({ fonte, periodos, categoria: categoriaInicial, categorias, niveis, municipios, escopoInicial, onClassica }: Props) {
  const [indicador, setIndicador] = useState<PainelIndicador>("densidade");
  // null: escala automática (linear, ou logarítmica com milhares de municípios e valores muito desiguais); a escolha da pessoa vale depois.
  const [escala, setEscala] = useState<Escala | null>(null);
  const [competencia, setCompetencia] = useState(() => maisRecente(periodos));
  const [categoria, setCategoria] = useState(categoriaInicial);
  const [base, setBase] = useState<PainelMunicipios>(() => baseInicial({ todos: escopoInicial.todos, grupos: escopoInicial.grupos },
    escopoInicial.ids, niveis.municipios.total));
  const [conjuntos, setConjuntos] = useState<PainelConjuntoPedido[]>([]);
  const [referencia, setReferencia] = useState<PainelReferenciaPedido | null>(null);
  const [competenciaInicial, setCompetenciaInicial] = useState("");
  const [vista, setVista] = useState<Vista>("final");
  const [fase, setFase] = useState<FaseAnimacao>("parado");
  const [corte, setCorte] = useState<Corte | null>(null);
  const [selecionados, setSelecionados] = useState<string[]>([]);
  const [gaveta, setGaveta] = useState<Gaveta | null>(null);
  const [ordenacao, setOrdenacao] = useState<Ordenacao>(null);
  const [pagina, setPagina] = useState(0);
  const [resposta, setResposta] = useState<PainelResposta | null>(null);
  // Definição que produziu a resposta em exibição: depois de uma recusa do motor, dá para voltar a ela sem novo pedido.
  const [calculado, setCalculado] = useState<{ chave: string; definicao: DefinicaoPainel } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [tentativa, setTentativa] = useState(0);
  const [aviso, setAviso] = useState("");
  const movimentoReduzido = useMovimentoReduzido();

  // Pedido ao motor: universo, competências, categoria, conjuntos e referência. Densidade e Quantidade não pedem nada novo.
  const definicao: DefinicaoPainel = useMemo(() => ({ competencia, competenciaInicial, categoria, base, conjuntos, referencia }),
    [competencia, competenciaInicial, categoria, base, conjuntos, referencia]);
  const opcoes = useMemo(() => montarOpcoes(definicao), [definicao]);
  const chave = JSON.stringify(opcoes);
  useEffect(() => {
    // Base e conjuntos vazios: o motor não tem o que calcular (ele aceita base vazia só com conjunto).
    if (semPedido(base, conjuntos) || !competencia) { setResposta(null); setCalculado(null); setErro(""); setCarregando(false); return; }
    if (calculado?.chave === chave) { setErro(""); setCarregando(false); return; }  // de volta ao painel em exibição
    const controle = new AbortController(), pedido = definicao;
    setCarregando(true);
    setErro("");
    const timer = window.setTimeout(() => {
      pedirPainel(fonte, opcoes, controle.signal)
        .then(corpo => { if (!controle.signal.aborted) { setResposta(corpo); setCalculado({ chave, definicao: pedido }); } })
        .catch((exc: unknown) => { if (!controle.signal.aborted) setErro(exc instanceof Error ? exc.message : "Não foi possível montar o gráfico."); })
        .finally(() => { if (!controle.signal.aborted) setCarregando(false); });
    }, 120);
    return () => { controle.abort(); window.clearTimeout(timer); };
  }, [chave, tentativa, fonte.datasetVersion]);
  /** Depois de uma recusa do motor, volta à definição do painel em exibição (universo, conjuntos, referência e competências). */
  function voltarAoCalculado() {
    if (!calculado) return;
    const anterior = calculado.definicao;
    setCompetencia(anterior.competencia); setCompetenciaInicial(anterior.competenciaInicial); setCategoria(anterior.categoria);
    setBase(anterior.base); setConjuntos(anterior.conjuntos); setReferencia(anterior.referencia);
    setAviso("De volta ao último gráfico calculado.");
  }

  // Reproduzir do inicial ao final: um quadro na competência inicial sem transição, depois o movimento até a final.
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

  const itens = useMemo(() => resposta?.itens ?? [], [resposta]);
  const comDistancia = !!referencia && !!resposta?.referencia;
  const comCrescimento = !!competenciaInicial && !!resposta?.competencia_inicial;
  const { plotaveis, fora } = useMemo(() => separarItens(itens, indicador, comDistancia, comCrescimento),
    [itens, indicador, comDistancia, comCrescimento]);
  const dominio = resposta?.dominios[indicador] ?? null;
  const logPossivel = !!dominio && dominio[0] > 0;
  // Com milhares de municípios e um valor 100 vezes maior que outro, o eixo linear espremeria quase todos num canto: o eixo
  // começa na escala logarítmica, que a pessoa pode trocar.
  const escalaAutomatica: Escala = plotaveis.length > LIMITE_LEVE && logPossivel && dominio![1] >= 100 * dominio![0] ? "logaritmica" : "linear";
  const escalaEfetiva: Escala = logPossivel ? escala ?? escalaAutomatica : "linear";
  const visiveis = useMemo(() => plotaveis.filter(item => noCorte(item, indicador, corte)), [plotaveis, indicador, corte]);
  // Com muitas bolhas (modo leve do gráfico), não há animação: "Reproduzir" vira "Ir para a competência final".
  const semAnimacao = movimentoReduzido || plotaveis.length > LIMITE_LEVE;
  const limiares = useMemo(() => corte ? [corte.minimo, corte.maximo] : [], [corte]);
  const nomes = useMemo(() => new Map<string, string>([...municipios.map(item => [item.id, nomeDoMunicipio(item)] as [string, string]),
    ...itens.map(item => [item.id, item.rotulo] as [string, string])]), [municipios, itens]);
  const selecao = useMemo(() => selecionados.filter(id => itens.some(item => item.id === id)), [selecionados, itens]);
  const limite = useMemo(() => resposta ? limiteDaVariacao(resposta, indicador, plotaveis) : 0, [resposta, indicador, plotaveis]);
  const linhas = useMemo(() => ordenarTabela(visiveis, ordenacao, indicador), [visiveis, ordenacao, indicador]);
  // Outra ordem ou outro corte: a tabela volta à primeira página.
  useEffect(() => setPagina(0), [linhas]);
  const paginas = Math.max(1, Math.ceil(linhas.length / POR_PAGINA)), paginaAtual = Math.min(pagina, paginas - 1);
  const linhasDaPagina = linhas.slice(paginaAtual * POR_PAGINA, (paginaAtual + 1) * POR_PAGINA);
  const rotuloDistancia = (referencia?.membros.length ?? 0) > 1 ? "Distância até o membro mais próximo da referência (km)"
    : "Distância até a referência (km)";

  const alternar = useCallback((id: string) =>
    setSelecionados(atual => atual.includes(id) ? atual.filter(item => item !== id) : [...atual, id]), []);
  // Um estado inteiro absorve os municípios avulsos dele, e "Todos" absorve tudo: as etiquetas mostram o universo pedido.
  function mudarBase(proxima: PainelMunicipios) { setBase(normalizarBase(proxima)); setCorte(null); }
  function acrescentar(id: string) {
    const nome = nomes.get(id) || id;
    if (base.todos || base.estados.includes(prefixoDe(id))) { setAviso(nome + " já está entre os municípios base."); return; }
    if (base.ids.includes(id)) { setAviso(nome + " já foi acrescentado."); return; }
    setBase(atual => ({ ...atual, ids: [...atual.ids, id] }));
    setAviso(nome + " acrescentado ao gráfico.");
  }
  function agregar(rotulo: string) {
    const membros = selecao.filter(id => itens.find(item => item.id === id)?.tipo === "municipio");
    if (membros.length < 2 || conjuntos.length >= MAX_CONJUNTOS) return;
    const conjunto = novoConjunto(conjuntos, membros, rotulo);
    setConjuntos(atual => [...atual, conjunto]);
    setSelecionados([conjunto.id]);
    setAviso("Conjunto " + conjunto.rotulo + " criado. O motor devolve a bolha com a soma das contagens dos componentes.");
  }
  function aplicarReferencia(pedida: PainelReferenciaPedido) {
    if (!pedida.membros.length) return;
    setReferencia({ ...pedida, membros: [...new Set(pedida.membros)] });
    setAviso("Referência pedida ao motor: com ela, o eixo horizontal passa a ser a distância.");
  }
  function mudarCompetencia(valor: string) {
    setCompetencia(valor);
    setCorte(null);
    if (competenciaInicial && competenciaInicial.localeCompare(valor, "pt-BR", { numeric: true }) >= 0) setCompetenciaInicial("");
  }
  function reproduzir() {
    if (!comCrescimento) return;
    if (semAnimacao) { setVista("final"); return; }
    setVista("inicial");
    setFase("preparar");
  }
  const ordenar = (coluna: ColunaTabela) => setOrdenacao(atual => !atual || atual.coluna !== coluna ? { coluna, sentido: "desc" }
    : atual.sentido === "desc" ? { coluna, sentido: "asc" } : null);
  const ordemDe = (coluna: ColunaTabela): "ascending" | "descending" | "none" => !ordenacao || ordenacao.coluna !== coluna ? "none"
    : ordenacao.sentido === "asc" ? "ascending" : "descending";

  const especie = INDICADORES[indicador];
  const botaoAcao = (ativo: boolean, aberto: boolean) => BOTAO + (aberto ? " bg-ink text-white" : ativo
    ? " border-2 border-ink bg-white text-ink" : " border border-line bg-white text-ink hover:bg-slate-50");
  const cabecalho = (coluna: ColunaTabela, rotulo: string) => <th scope="col" aria-sort={ordemDe(coluna)}>
    <button type="button" onClick={() => ordenar(coluna)} className="inline-flex items-center gap-1 font-semibold uppercase hover:text-ink">
      {rotulo}{ordemDe(coluna) === "ascending" ? " ↑" : ordemDe(coluna) === "descending" ? " ↓" : ""}</button></th>;
  const grupos = (["indicador", "distancia", "variacao"] as const).map(aspecto => ({ aspecto, itens: fora.filter(item => item.aspecto === aspecto) }))
    .filter(grupo => grupo.itens.length > 0);

  return <section id="painel-integrado" data-testid="painel-integrado" aria-labelledby="painel-titulo" className="painel section-anchor">
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 id="painel-titulo" tabIndex={-1} className="text-xl font-semibold tracking-tight text-ink outline-none sm:text-2xl">Municípios em bolhas</h2>
        <p className="mt-1 text-xs leading-5 text-slate-600">Dados do Brasil · {categoria} · {exibirCompetencia(competencia)}. Cada bolha é um
          município ou conjunto: o tamanho é a população, e a posição, os valores do motor. Acrescente municípios, escolha o indicador e
          use as análises acima do gráfico.</p>
      </div>
      <button type="button" data-testid="painel-voltar" onClick={() => onClassica()}
        className={BOTAO + " border border-teal bg-white text-teal hover:bg-cyan-50"}><LayoutGrid size={16} aria-hidden="true"/>Todas as análises</button>
    </header>

    <div className="painel-barra" role="group" aria-label="Análises">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Indicador do eixo">
        <button type="button" data-testid="painel-indicador-densidade" aria-pressed={indicador === "densidade"}
          onClick={() => { setIndicador("densidade"); setCorte(null); }} className={botaoAcao(false, indicador === "densidade")}>
          <Calculator size={16} aria-hidden="true"/>Densidade</button>
        <button type="button" data-testid="painel-indicador-quantidade" aria-pressed={indicador === "quantidade"}
          onClick={() => { setIndicador("quantidade"); setCorte(null); }} className={botaoAcao(false, indicador === "quantidade")}>
          <UsersRound size={16} aria-hidden="true"/>Quantidade</button>
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" data-testid="painel-acao-distancia" aria-expanded={gaveta === "distancia"} aria-controls="painel-gaveta"
          onClick={() => setGaveta(atual => atual === "distancia" ? null : "distancia")} className={botaoAcao(comDistancia, gaveta === "distancia")}>
          <MapPinned size={16} aria-hidden="true"/>Distância{comDistancia ? " · ativa" : ""}</button>
        <button type="button" data-testid="painel-acao-crescimento" aria-expanded={gaveta === "crescimento"} aria-controls="painel-gaveta"
          onClick={() => setGaveta(atual => atual === "crescimento" ? null : "crescimento")} className={botaoAcao(comCrescimento, gaveta === "crescimento")}>
          <TrendingUp size={16} aria-hidden="true"/>Crescimento{comCrescimento ? " · ativo" : ""}</button>
        <button type="button" data-testid="painel-acao-comparar" aria-expanded={gaveta === "comparar"} aria-controls="painel-gaveta"
          onClick={() => setGaveta(atual => atual === "comparar" ? null : "comparar")} className={botaoAcao(selecao.length > 0 || conjuntos.length > 0, gaveta === "comparar")}>
          <Layers3 size={16} aria-hidden="true"/>Comparar / Conjuntos</button>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-xs" role="group" aria-label="Outras análises">
        <span className="text-slate-600">Outras análises:</span>
        {CLASSICAS.map(([operacao, rotulo]) => <button key={operacao} type="button" data-testid={"painel-classica-" + operacao}
          onClick={() => onClassica(operacao)} className="min-h-9 rounded-lg border border-line bg-white px-2.5 py-1.5 font-semibold text-teal hover:bg-cyan-50">
          {rotulo}</button>)}
      </div>
    </div>

    <div className="flex flex-wrap items-end gap-3 text-xs text-slate-700">
      <label>Competência
        <select data-testid="painel-competencia" value={competencia} onChange={event => mudarCompetencia(event.target.value)}
          className="mt-1 block rounded-lg border border-line bg-white px-2 py-2 text-sm text-ink">
          {cronologica(periodos).reverse().map(periodo => <option key={periodo} value={periodo}>{exibirCompetencia(periodo)}</option>)}
        </select>
      </label>
      {categorias.length > 1 && <label>Categoria
        <select value={categoria} onChange={event => setCategoria(event.target.value)} className="mt-1 block rounded-lg border border-line bg-white px-2 py-2 text-sm text-ink">
          {categorias.map(valor => <option key={valor} value={valor}>{valor}</option>)}
        </select>
      </label>}
      <label>Escala do eixo de {especie.rotulo.toLowerCase()}
        <select data-testid="painel-escala" value={escalaEfetiva} onChange={event => setEscala(event.target.value as Escala)}
          className="mt-1 block rounded-lg border border-line bg-white px-2 py-2 text-sm text-ink">
          <option value="linear">Linear (a partir do zero)</option>
          <option value="logaritmica" disabled={!logPossivel}>Logarítmica{logPossivel ? "" : " (exige valores positivos)"}</option>
        </select>
        {escala === null && escalaEfetiva === "logaritmica" && <span data-testid="painel-escala-automatica" className="mt-1 block max-w-xs text-[11px] leading-4 text-slate-500">
          Logarítmica porque há milhares de municípios com valores muito desiguais; troque se preferir.</span>}
      </label>
      <p role="status" className="flex min-h-9 items-center gap-2 text-teal">{carregando && <><LoaderCircle size={15} className="animate-spin" aria-hidden="true"/>
        Atualizando o gráfico no motor…</>}</p>
    </div>

    {gaveta && <div id="painel-gaveta" className="painel-gaveta">
      {gaveta === "distancia" ? <GavetaReferencia fonte={fonte} competencia={competencia} categoria={categoria} base={base} conjuntos={conjuntos}
        pedida={referencia} ativa={comDistancia ? resposta?.referencia ?? null : null} nomes={nomes} onAplicar={aplicarReferencia}
        onRemover={() => { setReferencia(null); setAviso("Distância removida: volta o eixo único."); }}/>
      : gaveta === "crescimento" ? <GavetaCrescimento periodos={periodos} competencia={competencia} ativa={competenciaInicial} vista={vista}
        reproduzindo={fase !== "parado"} movimentoReduzido={semAnimacao} indicador={indicador} limite={limite}
        onMostrar={inicial => { setCompetenciaInicial(inicial); setVista("final"); }}
        onRemover={() => { setCompetenciaInicial(""); setVista("final"); }} onVista={setVista} onReproduzir={reproduzir}/>
      : <GavetaComparar itens={itens} selecionados={selecao} conjuntos={conjuntos} indicador={indicador} distancia={comDistancia}
        crescimento={comCrescimento} competenciaInicial={competenciaInicial} onAlternar={alternar} onLimpar={() => setSelecionados([])}
        onAgregar={agregar} onRemoverConjunto={id => { setConjuntos(atual => atual.filter(item => item.id !== id)); setSelecionados(atual => atual.filter(item => item !== id)); }}/>}
    </div>}

    <div className="painel-corpo">
      <PainelBase niveis={niveis} municipios={municipios} base={base} nomes={nomes} onBase={mudarBase} onAcrescentar={acrescentar} desabilitado={false}/>
      <div className="min-w-0 space-y-3">
        {resposta && <PainelRuler indicador={indicador} dominio={dominio} escala={escalaEfetiva} corte={corte} onCorte={setCorte}/>}
        <div className="painel-quadro">
          {erro && <div role="alert" data-testid="painel-erro" className="mb-3 space-y-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">
            <p>O motor não calculou o gráfico com a última mudança: {erro}</p>
            <div className="flex flex-wrap gap-3">
              {calculado && <button type="button" data-testid="painel-desfazer" onClick={voltarAoCalculado}
                className="font-semibold underline">Voltar ao último gráfico calculado</button>}
              <button type="button" onClick={() => setTentativa(valor => valor + 1)} className="inline-flex items-center gap-1 font-semibold underline">
                <RefreshCw size={13} aria-hidden="true"/>Tentar novamente</button>
            </div>
          </div>}
          {semPedido(base, conjuntos) ? <p data-testid="painel-vazio" className="px-2 py-16 text-center text-sm leading-6 text-slate-600">Escolha os
            municípios base: marque Todos os municípios, acrescente um estado inteiro ou procure municípios ao lado e arraste-os para cá.</p>
          : !resposta ? <p role="status" className="flex items-center justify-center gap-2 px-2 py-16 text-sm text-teal">
            {!erro && <><LoaderCircle size={18} className="animate-spin" aria-hidden="true"/>Pedindo os valores ao motor…</>}</p>
          : <PainelChart resposta={resposta} itens={visiveis} todos={plotaveis} indicador={indicador} escala={escalaEfetiva} distancia={comDistancia}
            crescimento={comCrescimento} vista={vista} fase={fase} selecionados={selecao} limiares={limiares} nomes={nomes}
            carregando={carregando} rotuloDistancia={rotuloDistancia} onAlternar={alternar} onSoltar={acrescentar}/>}
        </div>
      </div>
    </div>

    {resposta && <>
      <section data-testid="painel-nao-avaliaveis" aria-label="Não avaliáveis" className="rounded-2xl border border-line bg-white p-4">
        <h3 className="text-sm font-bold text-ink">Não avaliáveis</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">Não avaliável não é zero: sem o valor, o item fica fora do gráfico (na variação,
          a bolha fica vazada, com contorno tracejado) e aparece aqui com o motivo do motor.</p>
        {grupos.length ? grupos.map(grupo => <div key={grupo.aspecto} className="mt-2">
          <p className="text-xs font-semibold text-ink">{ASPECTOS[grupo.aspecto]}{grupo.aspecto === "indicador" ? " (" + especie.rotulo.toLowerCase() + ")" : ""}</p>
          <ul className="mt-1 space-y-0.5 text-xs text-slate-700">
            {grupo.itens.map(item => <li key={grupo.aspecto + item.id} data-testid="painel-nao-avaliavel" data-id={item.id} data-aspecto={item.aspecto}>
              <strong className="font-semibold text-ink">{item.rotulo}</strong>: {item.motivo}</li>)}
          </ul>
        </div>) : <p className="mt-2 text-xs text-slate-600">Nenhum item sem valor no estado atual do gráfico.</p>}
      </section>

      <section data-testid="painel-table" aria-label="Tabela equivalente ao gráfico" className="rounded-2xl border border-line bg-white p-4">
        <h3 className="text-sm font-bold text-ink">Tabela equivalente</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">Os mesmos itens do gráfico, com os valores do motor em {exibirCompetencia(resposta.competencia)}.
          A ordem padrão é a do código territorial; clicar num cabeçalho só reordena a tabela, sem criar posições.{corte ? " Itens fora do corte da régua não aparecem." : ""}
          {paginas > 1 ? " Com muitos itens, a tabela mostra " + POR_PAGINA + " linhas por vez." : ""}</p>
        <div className="mt-2 overflow-x-auto">
          <table className="data-table painel-tabela min-w-full">
            <thead><tr>
              <th scope="col"><span className="sr-only">Destacar</span></th>
              {cabecalho("territorio", "Território")}
              {cabecalho("populacao", "População")}
              {cabecalho("quantidade", "Profissionais")}
              {cabecalho("densidade", "Densidade")}
              {comDistancia && cabecalho("distancia", "Distância (km)")}
              {comCrescimento && cabecalho("variacao", "Variação (" + especie.rotulo.toLowerCase() + ")")}
              <th scope="col">Observação</th>
            </tr></thead>
            <tbody>{linhasDaPagina.map(item => {
              const variacao = variacaoDe(item, indicador), inicial = inicialDe(item, indicador);
              const observacao = [item.tipo === "conjunto" ? textoDaContagem(item.contagem) : "",
                item.referencia ? (item.tipo === "conjunto" ? "Conjunto igual à referência" : "Membro da referência") : "",
                ...avisosDe(item)].filter(Boolean).join(". ");
              return <tr key={item.id} data-testid="painel-row" data-id={item.id} data-tipo={item.tipo}>
                <td><input type="checkbox" className="h-4 w-4 accent-teal" checked={selecao.includes(item.id)} onChange={() => alternar(item.id)}
                  aria-label={"Destacar " + item.rotulo}/></td>
                <td className="font-semibold text-ink">{item.rotulo}</td>
                <td className="tabular-nums">{numero(item.populacao) === null ? "Não avaliável" : formatarNumero(item.populacao as number, true)}</td>
                <td className="tabular-nums">{numero(item.quantidade) === null ? "Não avaliável"
                  : formatarNumero(item.quantidade as number, true, indicador === "quantidade" ? limiares : [])}</td>
                <td className="tabular-nums">{formatarIndicador(numero(item.densidade), "densidade", indicador === "densidade" ? limiares : [])}</td>
                {comDistancia && <td className="tabular-nums">{numero(item.distancia_km) === null ? "Não avaliável" : formatarNumero(item.distancia_km as number) +
                  (item.tipo === "conjunto" && numero(item.distancia_km_max) !== null ? " a " + formatarNumero(item.distancia_km_max as number) : "")}</td>}
                {comCrescimento && <td className="tabular-nums" data-variacao={variacao ?? ""}>{formatarVariacao(variacao)}
                  {inicial !== null && <span className="block text-[11px] text-slate-500">em {exibirCompetencia(resposta.competencia_inicial)}:{" "}
                    {formatarNumero(inicial, especie.contagem)}</span>}</td>}
                <td className="whitespace-normal text-xs text-slate-600">{observacao}</td>
              </tr>;
            })}</tbody>
          </table>
        </div>
        {paginas > 1 && <div data-testid="painel-tabela-paginas" className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <span role="status">Linhas {formatarNumero(paginaAtual * POR_PAGINA + 1, true)} a {formatarNumero(Math.min(linhas.length,
            (paginaAtual + 1) * POR_PAGINA), true)} de {formatarNumero(linhas.length, true)}</span>
          <button type="button" data-testid="painel-tabela-anterior" disabled={paginaAtual === 0} onClick={() => setPagina(paginaAtual - 1)}
            className="rounded-lg border border-line bg-white px-3 py-1.5 font-semibold text-teal hover:bg-cyan-50 disabled:opacity-40">Anteriores</button>
          <button type="button" data-testid="painel-tabela-proxima" disabled={paginaAtual >= paginas - 1} onClick={() => setPagina(paginaAtual + 1)}
            className="rounded-lg border border-line bg-white px-3 py-1.5 font-semibold text-teal hover:bg-cyan-50 disabled:opacity-40">Próximas</button>
        </div>}
      </section>

      <section data-testid="painel-procedencia" aria-label="Notas, limitações e procedência" className="rounded-2xl border border-cyan-100 bg-cyan-50/60 p-4 text-xs leading-5 text-slate-700">
        <h3 className="text-sm font-bold text-ink">Notas, limitações e procedência</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {resposta.referencia?.origem && comDistancia && <li>Referência: {resposta.referencia.origem}.</li>}
          {(resposta.notas || []).map(nota => <li key={"n" + nota}>{nota}</li>)}
          {(resposta.limitacoes || []).map(codigo => <li key={"l" + codigo} data-limitacao={codigo}>{textoDaLimitacao(codigo)}</li>)}
          <li>Na tela, os valores aparecem arredondados (duas casas nas medidas contínuas); a precisão integral fica no motor.</li>
        </ul>
        <p className="mt-2 text-[11px] text-slate-600">Competência {exibirCompetencia(resposta.competencia)}{resposta.competencia_inicial
          ? " · competência inicial " + exibirCompetencia(resposta.competencia_inicial) : ""} · categoria {resposta.categoria} · versão da base{" "}
          {String(resposta.versao_base || "").slice(0, 12)} · chave de execução {String(resposta.chave_execucao || "").slice(0, 12)}</p>
      </section>
    </>}
    <p aria-live="polite" className="sr-only" data-testid="painel-aviso">{aviso}</p>
  </section>;
}
