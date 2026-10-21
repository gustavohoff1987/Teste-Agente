import { useEffect, useState } from "react";
import { LoaderCircle, Pause, Play, X } from "lucide-react";
import {
  pedirReferencias, type PainelAtributo, type PainelConjuntoPedido, type PainelFonte, type PainelIndicador, type PainelItem,
  type PainelMunicipios, type PainelOrdem, type PainelReferenciaPedido, type PainelReferenciaResposta, type PainelUniverso,
  type ReferenciaCandidato, type ReferenciasResposta,
} from "./painelApi";
import {
  ATRIBUTOS, INDICADORES, MAX_CONJUNTOS, ORDENS, RAMPA_CRESCIMENTO, RAMPA_QUEDA, COR_NEUTRA, anteriores, baseVazia, exibirCompetencia,
  formatarIndicador, formatarNumero, formatarVariacao, inicialSugerida, normalizarBase, numero, primeirosColocados, textoDaContagem,
  variacaoDe, type Vista,
} from "./painelModel";

// Gavetas das análises do painel integrado: a referência da distância por critério, o crescimento e a comparação com conjuntos.
// Os valores, as posições dos candidatos e as variações vêm do motor; a tela só lista, marca e pede.

const BOTAO = "inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-40";
const PRIMARIO = BOTAO + " bg-teal text-white hover:bg-[#0a6f78]";
const SECUNDARIO = BOTAO + " border border-line bg-white text-teal hover:bg-cyan-50";
const CAMPO = "mt-1 block w-full min-w-0 rounded-lg border border-line bg-white px-2 py-2 text-sm text-ink";
const TODOS: PainelUniverso = { municipios: { todos: true, estados: [], ids: [] } };

function valorDoCandidato(valor: number | null, atributo: PainelAtributo): string {
  if (valor === null) return "Não avaliável";
  return atributo === "populacao" ? formatarNumero(valor, true) + " habitantes" : formatarIndicador(valor, atributo);
}

// ------------------------------------------------------------------------------------------------ distância
type ReferenciaProps = {
  fonte: PainelFonte; competencia: string; categoria: string; base: PainelMunicipios; conjuntos: PainelConjuntoPedido[];
  /** Referência pedida ao motor (ainda que recusada) e a confirmada na resposta. */
  pedida: PainelReferenciaPedido | null; ativa: PainelReferenciaResposta | null; nomes: Map<string, string>;
  onAplicar: (referencia: PainelReferenciaPedido) => void; onRemover: () => void;
};

/** Distância: a referência é escolhida por critério (densidade, quantidade ou população), na ordem do motor (CAP-SUB-02). Um
 * município ou vários (conjunto de referência: a distância vai até o membro mais próximo). O critério e o universo da lista vão
 * junto, para a origem citar a posição exata vista aqui. */
export function GavetaReferencia({ fonte, competencia, categoria, base, conjuntos, pedida, ativa, nomes, onAplicar, onRemover }: ReferenciaProps) {
  const semBase = baseVazia(base);
  const [atributo, setAtributo] = useState<PainelAtributo>("densidade");
  const [ordem, setOrdem] = useState<PainelOrdem>("desc");
  const [universo, setUniverso] = useState<"base" | "todos">(semBase ? "todos" : "base");
  const [lista, setLista] = useState<{ resposta: ReferenciasResposta; universo: PainelUniverso } | null>(null);
  const [marcados, setMarcados] = useState<string[]>([]);
  const [empate, setEmpate] = useState<string[] | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const procurarEm = semBase ? "todos" : universo;
  // Outro critério, outra ordem ou outro universo: a lista anterior deixa de valer.
  useEffect(() => { setLista(null); setMarcados([]); setEmpate(null); setErro(""); }, [atributo, ordem, procurarEm, competencia, categoria,
    JSON.stringify(base)]);

  async function listar() {
    setCarregando(true); setErro(""); setEmpate(null); setMarcados([]);
    const escolhido: PainelUniverso = procurarEm === "todos" ? TODOS : { municipios: normalizarBase(base) };
    try {
      const resposta = await pedirReferencias(fonte, { competencia, categoria, universo: escolhido, criterio: { atributo, ordem } });
      setLista({ resposta, universo: escolhido });
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Não foi possível listar os candidatos.");
    } finally {
      setCarregando(false);
    }
  }
  function aplicar(membros: string[]) {
    if (!lista || !membros.length) return;
    const { atributo: usado, ordem: sentido } = lista.resposta.criterio;
    onAplicar({ membros, criterio: { atributo: usado, ordem: sentido, universo: lista.universo } });
  }
  function usarPrimeiro() {
    if (!lista) return;
    const primeiros = primeirosColocados(lista.resposta.candidatos);
    if (primeiros.length === 1) { setEmpate(null); aplicar([primeiros[0].id]); return; }
    if (primeiros.length > 1) { setEmpate(primeiros.map(item => item.id)); setMarcados([]); }
  }
  const alternar = (id: string) => setMarcados(atual => atual.includes(id) ? atual.filter(item => item !== id) : [...atual, id]);
  const todosCandidatos = lista?.resposta.candidatos ?? [];
  const candidatos: ReferenciaCandidato[] = empate ? todosCandidatos.filter(item => empate.includes(item.id)) : todosCandidatos;
  const atributoDaLista = lista?.resposta.criterio.atributo ?? atributo;
  const naoAvaliaveis = lista?.resposta.nao_avaliaveis ?? [];

  return <section data-testid="painel-reference" aria-label="Distância: referência por critério" className="space-y-3">
    <div>
      <h3 className="text-sm font-bold text-ink">Distância até uma referência</h3>
      <p className="mt-1 text-xs leading-5 text-slate-600">Escolha a referência por um critério. Com um município, a distância é até ele; com
        vários, eles formam um conjunto de referência, e a distância de cada município vai até o membro mais próximo. Distância geodésica do
        motor (SIRGAS 2000).</p>
    </div>
    {pedida && <div data-testid="painel-referencia-ativa" className="rounded-xl border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-700">
      {ativa ? <>
        <p><strong className="text-ink">Referência atual:</strong> {ativa.membros.map(membro => membro.rotulo).join(", ")}
          {ativa.tipo === "conjunto" ? " (conjunto de referência)" : ""}.</p>
        {ativa.origem && <p>{ativa.origem}.</p>}
      </> : <p><strong className="text-ink">Referência pedida:</strong> {pedida.membros.map(id => nomes.get(id) || id).join(", ")}. O
        painel com a distância ainda não foi calculado (veja a mensagem acima do gráfico).</p>}
      <button type="button" data-testid="painel-remover-referencia" onClick={onRemover} className={SECUNDARIO + " mt-2"}>Remover a distância</button>
    </div>}
    <div className="grid gap-2 sm:grid-cols-3">
      <label className="text-xs text-slate-700">Critério
        <select data-testid="painel-criterio" value={atributo} onChange={event => setAtributo(event.target.value as PainelAtributo)} className={CAMPO}>
          <option value="densidade">Densidade</option><option value="quantidade">Quantidade</option><option value="populacao">População</option>
        </select>
      </label>
      <label className="text-xs text-slate-700">Ordem
        <select data-testid="painel-ordem" value={ordem} onChange={event => setOrdem(event.target.value as PainelOrdem)} className={CAMPO}>
          <option value="desc">Da maior para a menor</option><option value="asc">Da menor para a maior</option>
        </select>
      </label>
      <label className="text-xs text-slate-700">Procurar em
        <select data-testid="painel-universo-referencia" value={procurarEm} onChange={event => setUniverso(event.target.value as "base" | "todos")} className={CAMPO}>
          <option value="base" disabled={semBase}>Municípios base</option><option value="todos">Todos os municípios</option>
        </select>
      </label>
    </div>
    <div className="flex flex-wrap gap-2">
      <button type="button" data-testid="painel-listar-candidatos" onClick={() => void listar()} disabled={carregando || !competencia} className={SECUNDARIO}>
        {carregando && <LoaderCircle size={14} className="animate-spin" aria-hidden="true"/>}Listar candidatos</button>
      <button type="button" data-testid="painel-usar-primeiro" onClick={usarPrimeiro} disabled={!primeirosColocados(todosCandidatos).length}
        className={SECUNDARIO}>Usar o primeiro</button>
      <button type="button" data-testid="painel-aplicar-referencia" onClick={() => aplicar(marcados)} disabled={!lista || !marcados.length}
        className={PRIMARIO}>Aplicar referência</button>
    </div>
    {erro && <p role="alert" className="text-xs text-rose-800">{erro}</p>}
    {empate && <p role="status" data-testid="painel-empate" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
      Há empate na 1ª posição. Escolha entre os empatados abaixo um ou mais municípios e use Aplicar referência.</p>}
    {lista && <div className="space-y-2">
      <p className="text-xs text-slate-600">Ordem do motor por {ATRIBUTOS[lista.resposta.criterio.atributo]}, {ORDENS[lista.resposta.criterio.ordem]}, em{" "}
        {exibirCompetencia(lista.resposta.competencia)}; empates ficam na mesma posição.</p>
      {conjuntos.length > 0 && <p className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600">Marcar os membros de um conjunto:
        {conjuntos.map(conjunto => <button key={conjunto.id} type="button" className="rounded-full border border-line bg-white px-2 py-0.5 font-semibold text-ink hover:border-teal"
          onClick={() => setMarcados(conjunto.membros.filter(id => candidatos.some(item => item.id === id)))}>{conjunto.rotulo}</button>)}</p>}
      <ol data-testid="painel-candidatos" aria-label="Candidatos a referência" className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-line bg-slate-50 p-1.5">
        {candidatos.map(item => <li key={item.id} data-testid="painel-candidato" data-id={item.id} data-posicao={item.posicao ?? ""}>
          <label className="flex min-h-9 cursor-pointer items-center gap-2 rounded-md bg-white px-2 py-1.5 text-xs text-ink hover:bg-cyan-50">
            <input type="checkbox" className="h-4 w-4 shrink-0 accent-teal" checked={marcados.includes(item.id)} onChange={() => alternar(item.id)}/>
            <span className="w-9 shrink-0 tabular-nums text-slate-600">{item.posicao !== null ? item.posicao + "º" : "—"}</span>
            <span className="min-w-0 flex-1 truncate">{item.rotulo}</span>
            <span className="shrink-0 tabular-nums text-slate-700">{valorDoCandidato(item.valor, atributoDaLista)}</span>
          </label>
        </li>)}
      </ol>
      {naoAvaliaveis.length > 0 && !empate && <details className="text-xs text-slate-600">
        <summary className="cursor-pointer">Não avaliáveis para o critério (sem posição)</summary>
        <ul data-testid="painel-candidatos-nao-avaliaveis" className="mt-1 space-y-0.5">
          {naoAvaliaveis.map(item => <li key={item.id}>{item.rotulo}{item.motivos.length ? ": " + item.motivos.join("; ") : ""}</li>)}
        </ul>
      </details>}
    </div>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ crescimento
type CrescimentoProps = {
  periodos: string[]; competencia: string; ativa: string; vista: Vista; reproduzindo: boolean; movimentoReduzido: boolean;
  indicador: PainelIndicador; limite: number;
  onMostrar: (inicial: string) => void; onRemover: () => void; onVista: (vista: Vista) => void; onReproduzir: () => void;
};

/** Crescimento: a competência inicial pedida ao motor (CAP-TMP-01) e o controle entre a competência inicial e a final. */
export function GavetaCrescimento({ periodos, competencia, ativa, vista, reproduzindo, movimentoReduzido, indicador, limite,
  onMostrar, onRemover, onVista, onReproduzir }: CrescimentoProps) {
  const opcoes = anteriores(periodos, competencia).reverse();
  const [escolha, setEscolha] = useState(() => ativa || inicialSugerida(periodos, competencia));
  useEffect(() => { if (!opcoes.includes(escolha)) setEscolha(ativa || inicialSugerida(periodos, competencia)); }, [competencia]);
  const especie = INDICADORES[indicador].rotulo.toLowerCase();
  const gradiente = "linear-gradient(to right, " + [...RAMPA_QUEDA].reverse().join(", ") + " 48%, " + COR_NEUTRA + " 48% 52%, " +
    RAMPA_CRESCIMENTO.map((cor, indice) => cor + (indice === 0 ? " 52%" : "")).join(", ") + ")";
  return <section data-testid="painel-growth" aria-label="Crescimento em percentual" className="space-y-3">
    <div>
      <h3 className="text-sm font-bold text-ink">Crescimento entre duas competências</h3>
      <p className="mt-1 text-xs leading-5 text-slate-600">O motor calcula a variação percentual de cada município e conjunto, (valor final − valor
        inicial) ÷ valor inicial × 100. No gráfico, cada bolha vira um cometa: a bolha fica no valor atual, e um rastro fino sai da posição na
        competência inicial (círculo vazado). Sem reta de ajuste, sem projeção e sem médias.</p>
    </div>
    {!opcoes.length ? <p className="text-xs text-slate-600">Não há competência anterior a {exibirCompetencia(competencia)} nesta base.</p> :
      <div className="flex flex-wrap items-end gap-2">
        <label className="min-w-[10rem] text-xs text-slate-700">Competência inicial
          <select data-testid="painel-competencia-inicial" value={escolha} onChange={event => setEscolha(event.target.value)} className={CAMPO}>
            {opcoes.map(periodo => <option key={periodo} value={periodo}>{exibirCompetencia(periodo)}</option>)}
          </select>
        </label>
        <button type="button" data-testid="painel-mostrar-crescimento" disabled={!escolha || escolha === ativa} onClick={() => onMostrar(escolha)}
          className={PRIMARIO}>Mostrar crescimento</button>
        {ativa && <button type="button" data-testid="painel-remover-crescimento" onClick={onRemover} className={SECUNDARIO}>Remover crescimento</button>}
      </div>}
    {ativa && <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Competência mostrada no gráfico">
        {(["inicial", "final"] as const).map(qual => <button key={qual} type="button" data-testid={"painel-vista-" + qual} aria-pressed={vista === qual}
          onClick={() => onVista(qual)} disabled={reproduzindo}
          className={BOTAO + (vista === qual ? " bg-ink text-white" : " border border-line bg-white text-ink hover:bg-slate-50")}>
          {qual === "inicial" ? "Competência inicial (" + exibirCompetencia(ativa) + ")" : "Competência final (" + exibirCompetencia(competencia) + ")"}</button>)}
        <button type="button" data-testid="painel-reproduzir" onClick={onReproduzir} disabled={reproduzindo} className={SECUNDARIO}>
          {reproduzindo ? <Pause size={14} aria-hidden="true"/> : <Play size={14} aria-hidden="true"/>}
          {movimentoReduzido ? "Ir para a competência final" : "Reproduzir do inicial ao final"}</button>
      </div>
      <figure data-testid="painel-growth-legend" aria-label={"Escala de cor da variação percentual da " + especie} className="m-0 max-w-md">
        <div className="h-2.5 rounded-full" style={{ background: gradiente }} aria-hidden="true"/>
        <div className="mt-1 flex justify-between text-[11px] tabular-nums text-slate-600">
          <span>{formatarVariacao(-limite)}</span><span>0,00%</span><span>{formatarVariacao(limite)}</span>
        </div>
        <figcaption className="mt-1 text-[11px] leading-4 text-slate-600">Cor: variação da {especie} entre {exibirCompetencia(ativa)} e{" "}
          {exibirCompetencia(competencia)}, do motor. Azul é crescimento; laranja, queda; cinza, sem variação. Bolha vazada com contorno
          tracejado: variação não avaliável (o motivo fica na lista de não avaliáveis). O percentual aparece nos itens destacados, na dica e na
          tabela.</figcaption>
      </figure>
    </div>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ comparar e conjuntos
type CompararProps = {
  itens: PainelItem[]; selecionados: string[]; conjuntos: PainelConjuntoPedido[]; indicador: PainelIndicador;
  distancia: boolean; crescimento: boolean; competenciaInicial: string;
  onAlternar: (id: string) => void; onLimpar: () => void; onAgregar: (rotulo: string) => void; onRemoverConjunto: (id: string) => void;
};

/** Comparar: dois ou três itens destacados (os demais esmaecem), lado a lado, só com valores do motor (sem diferenças nem razões).
 * Conjuntos: os municípios selecionados viram uma bolha agregada pelo motor (CAP-AGR-01), com a soma das contagens dos componentes. */
export function GavetaComparar({ itens, selecionados, conjuntos, indicador, distancia, crescimento, competenciaInicial,
  onAlternar, onLimpar, onAgregar, onRemoverConjunto }: CompararProps) {
  const [nome, setNome] = useState("");
  const escolhidos = selecionados.map(id => itens.find(item => item.id === id)).filter((item): item is PainelItem => !!item);
  const municipios = escolhidos.filter(item => item.tipo === "municipio");
  const especie = INDICADORES[indicador];
  return <section data-testid="painel-compare" aria-label="Comparar e criar conjuntos" className="space-y-3">
    <div>
      <h3 className="text-sm font-bold text-ink">Comparar e agregar</h3>
      <p className="mt-1 text-xs leading-5 text-slate-600">Clique nas bolhas (ou marque na tabela) para destacar dois ou três itens; os demais
        esmaecem. Com dois ou mais municípios selecionados, Agregar selecionados cria um conjunto: o motor devolve uma bolha com a soma das
        populações e das contagens dos membros, na mesma dinâmica dos municípios.</p>
    </div>
    {escolhidos.length > 0 ? <ul className="flex flex-wrap gap-1.5" aria-label="Itens selecionados">
      {escolhidos.map(item => <li key={item.id} className="inline-flex items-center gap-1 rounded-full border border-ink bg-white py-0.5 pl-2.5 pr-1 text-xs font-semibold text-ink">
        {item.rotulo}
        <button type="button" aria-label={"Tirar o destaque de " + item.rotulo} onClick={() => onAlternar(item.id)}
          className="inline-flex h-6 w-6 items-center justify-center rounded-full hover:bg-slate-100"><X size={13} aria-hidden="true"/></button>
      </li>)}
      <li><button type="button" onClick={onLimpar} className="min-h-7 px-2 text-xs font-semibold text-teal underline">Limpar seleção</button></li>
    </ul> : <p className="text-xs text-slate-600">Nenhum item selecionado.</p>}
    {escolhidos.length > 3 && <p className="text-xs text-amber-900">Para comparar lado a lado, deixe até três itens destacados. Com mais, use
      Agregar selecionados.</p>}
    {escolhidos.length > 0 && escolhidos.length <= 3 && <div className="grid gap-2 sm:grid-cols-3">
      {escolhidos.map(item => {
        const variacao = variacaoDe(item, indicador);
        return <article key={item.id} data-testid="painel-comparacao-item" data-id={item.id} className="min-w-0 rounded-xl border border-line bg-slate-50 p-3 text-xs">
          <h4 className="truncate font-semibold text-ink" title={item.rotulo}>{item.rotulo}</h4>
          {item.tipo === "conjunto" && <p className="text-[11px] text-slate-600">{textoDaContagem(item.contagem)}</p>}
          <dl className="mt-1 grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-0.5 text-slate-700">
            <dt className="text-slate-500">{especie.rotulo}</dt><dd className="font-semibold text-ink">{formatarIndicador(numero(item[indicador]), indicador)}</dd>
            <dt className="text-slate-500">População</dt><dd>{numero(item.populacao) === null ? "Não avaliável" : formatarNumero(item.populacao as number, true)}</dd>
            {distancia && <><dt className="text-slate-500">Distância</dt><dd>{numero(item.distancia_km) === null ? "Não avaliável"
              : formatarNumero(item.distancia_km as number) + " km"}</dd></>}
            {crescimento && <><dt className="text-slate-500">Variação</dt><dd>{formatarVariacao(variacao)}
              {competenciaInicial ? <span className="text-slate-500"> desde {exibirCompetencia(competenciaInicial)}</span> : null}</dd></>}
          </dl>
        </article>;
      })}
    </div>}
    <div className="flex flex-wrap items-end gap-2 border-t border-line pt-3">
      <label className="min-w-[12rem] flex-1 text-xs text-slate-700">Nome do conjunto
        <input data-testid="painel-nome-conjunto" value={nome} onChange={event => setNome(event.target.value)} maxLength={60}
          placeholder={"Conjunto " + (conjuntos.length + 1)} className={CAMPO}/>
      </label>
      <button type="button" data-testid="painel-agregar" disabled={municipios.length < 2 || conjuntos.length >= MAX_CONJUNTOS}
        onClick={() => { onAgregar(nome); setNome(""); }} className={PRIMARIO}>Agregar selecionados</button>
    </div>
    {municipios.length < 2 && <p className="text-[11px] text-slate-600">Selecione pelo menos dois municípios para agregar.</p>}
    {conjuntos.length >= MAX_CONJUNTOS && <p className="text-[11px] text-amber-900">O painel aceita até {MAX_CONJUNTOS} conjuntos. Desfaça
      um conjunto para criar outro.</p>}
    {conjuntos.length > 0 && <ul className="space-y-1" aria-label="Conjuntos do painel">
      {conjuntos.map(conjunto => <li key={conjunto.id} data-testid="painel-conjunto" data-id={conjunto.id}
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-white px-3 py-2 text-xs">
        <span className="min-w-0"><strong className="text-ink">{conjunto.rotulo}</strong> · soma das contagens dos componentes, com possível dupla contagem</span>
        <button type="button" onClick={() => onRemoverConjunto(conjunto.id)} className="font-semibold text-teal underline">Desfazer conjunto</button>
      </li>)}
    </ul>}
  </section>;
}
