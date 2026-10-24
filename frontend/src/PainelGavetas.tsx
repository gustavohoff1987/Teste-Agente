import { useEffect, useMemo, useState } from "react";
import { Download, FileText, LoaderCircle, Plus, Printer, Trash2, X } from "lucide-react";
import {
  pedirReferencias, type AtributoCondicao, type AtributoOrdenacao, type CondicaoPedido, type FonteDoMotor, type OperadorCondicao,
  type OrdenarPedido, type PainelAtributo, type PainelConjuntoPedido, type PainelCriterio, type PainelIndicador, type PainelItem,
  type PainelMunicipios,
  type PainelOrdem, type PainelReferenciaPedido, type PainelResposta, type PainelUniverso, type Premissas, type ReferenciaCandidato,
  type ReferenciasResposta, type SituacaoCondicao,
} from "./painelApi";
import {
  ATRIBUTOS, INDICADORES, MAX_CONJUNTOS, NOTA_TPL11, OPERADORES, ORDENS, SIMBOLOS,
  artigo, baseVazia, escreverLimites, exibirCompetencia, formatarIndicador, formatarNumero, formatarVariacao, generoDe,
  lerLimites, maiuscula, normalizarBase, numero, ordemNeutra, primeirosColocados, quantos, textoDaContagem, todosOs, umA, variacaoDe,
  type RotulosTerritoriais, type UnidadeDoCatalogo,
} from "./painelModel";

// Painéis laterais das funções e das opções das análises. Os valores, as posições, as contagens e as comparações vêm do motor;
// a tela só lista, marca e pede. Cada painel é um formulário curto: o pedido sai só no botão de aplicar.

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const TODOS: PainelUniverso = { municipios: { todos: true, estados: [], ids: [] } };

function valorDoCandidato(valor: number | null, atributo: PainelAtributo): string {
  if (valor === null) return "Não avaliável";
  return atributo === "populacao" ? formatarNumero(valor, true) + " habitantes" : formatarIndicador(valor, atributo);
}

// ------------------------------------------------------------------------------------------------ referência (espacial)
type ReferenciaProps = {
  fonte: FonteDoMotor; competencia: string; categoria: string; base: PainelMunicipios; conjuntos: PainelConjuntoPedido[];
  pedida: PainelReferenciaPedido | null; ativa: PainelResposta["referencia"]; nomes: Map<string, string>; rotulos: RotulosTerritoriais;
  catalogo: UnidadeDoCatalogo[]; premissas: Premissas; faixas: number[];
  /** Critério pedido na conversa ("a de maior densidade como referência"): a lista abre nessa ordem, e a escolha é da pessoa. */
  criterioInicial?: PainelCriterio | null;
  onAplicar: (referencia: PainelReferenciaPedido) => void; onRemover: () => void; onFaixas: (limites: number[]) => void;
};

/** Referência por critério (densidade, quantidade ou população, na ordem do motor, CAP-SUB-02), pelo nome ou pelos membros de um
 * conjunto. Com várias, a distância vai até o membro mais próximo (CAP-ESP-02). Faixas de distância opcionais (CAP-ESP-03). */
export function GavetaReferencia(p: ReferenciaProps) {
  const semBase = baseVazia(p.base);
  const [atributo, setAtributo] = useState<PainelAtributo>(p.criterioInicial?.atributo ?? "densidade");
  const [ordem, setOrdem] = useState<PainelOrdem>(p.criterioInicial?.ordem ?? "desc");
  const [universo, setUniverso] = useState<"base" | "todos">(semBase ? "todos" : "base");
  const [lista, setLista] = useState<{ resposta: ReferenciasResposta; universo: PainelUniverso } | null>(null);
  const [marcados, setMarcados] = useState<string[]>([]);
  const [empate, setEmpate] = useState<string[] | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [consulta, setConsulta] = useState("");
  const [faixas, setFaixas] = useState(escreverLimites(p.faixas));
  const procurarEm = semBase ? "todos" : universo;
  useEffect(() => { setLista(null); setMarcados([]); setEmpate(null); setErro(""); }, [atributo, ordem, procurarEm, p.competencia, p.categoria,
    JSON.stringify(p.base)]);
  useEffect(() => setFaixas(escreverLimites(p.faixas)), [p.faixas]);
  // Critério pedido na conversa: o mesmo critério nos seletores e a lista de candidatos já aberta, nessa ordem.
  const criterioPedido = p.criterioInicial ? p.criterioInicial.atributo + ":" + p.criterioInicial.ordem : "";
  const [listarPedido, setListarPedido] = useState(false);
  useEffect(() => {
    if (!p.criterioInicial) return;
    setAtributo(p.criterioInicial.atributo); setOrdem(p.criterioInicial.ordem); setListarPedido(true);
  }, [criterioPedido]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!listarPedido || !p.criterioInicial || atributo !== p.criterioInicial.atributo || ordem !== p.criterioInicial.ordem) return;
    setListarPedido(false);
    void listar();
  }, [listarPedido, atributo, ordem]);  // eslint-disable-line react-hooks/exhaustive-deps
  const unidade = p.rotulos.unidade;

  async function listar() {
    setCarregando(true); setErro(""); setEmpate(null); setMarcados([]);
    const escolhido: PainelUniverso = procurarEm === "todos" ? TODOS : { municipios: normalizarBase(p.base) };
    try {
      const resposta = await pedirReferencias(p.fonte, { competencia: p.competencia, categoria: p.categoria, universo: escolhido,
        criterio: { atributo, ordem }, ...(Object.keys(p.premissas).length ? { premissas: p.premissas } : {}) });
      setLista({ resposta, universo: escolhido });
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Não foi possível listar os candidatos.");
    } finally {
      setCarregando(false);
    }
  }
  function aplicar(membros: string[]) {
    if (!membros.length) return;
    // Pela lista do critério, a origem cita a posição vista; escolhidos só pelo nome, a origem é a lista explícita.
    const daLista = lista && membros.every(id => lista.resposta.candidatos.some(item => item.id === id));
    if (daLista) {
      const { atributo: usado, ordem: sentido } = lista!.resposta.criterio;
      p.onAplicar({ membros, criterio: { atributo: usado, ordem: sentido, universo: lista!.universo } });
    } else p.onAplicar({ membros });
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
  const achados = useMemo(() => {
    const termo = sem(consulta.trim());
    if (!termo) return [];
    return p.catalogo.filter(item => !item.selection_reason && sem(item.name + " " + item.code + " " + item.label).includes(termo)).slice(0, 12);
  }, [p.catalogo, consulta]);

  return <section data-testid="analise-referencia" aria-label="Referência da distância" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">Com {umA(unidade)}, a distância é até {generoDe(unidade) === "f" ? "ela" : "ele"}; com vários, eles formam um
      conjunto de referência, e a distância vai até o membro mais próximo.</p>
    {p.pedida && <div data-testid="analise-ref-ativa" className="rounded-xl border border-line bg-slate-50 p-3 text-xs leading-5 text-slate-700">
      {p.ativa ? <>
        <p><strong className="text-ink">Referência atual:</strong> {p.ativa.membros.map(membro => membro.rotulo).join(", ")}
          {p.ativa.tipo === "conjunto" ? " (conjunto de referência)" : ""}.</p>
        {p.ativa.origem && <p>{p.ativa.origem}.</p>}
      </> : <p><strong className="text-ink">Referência pedida:</strong> {p.pedida.membros.map(id => p.nomes.get(id) || id).join(", ")}. O
        gráfico com a distância ainda não foi calculado (veja a mensagem acima do gráfico).</p>}
      <button type="button" data-testid="analise-ref-remover" onClick={p.onRemover} className="analise-botao-secundario mt-2">Remover a referência</button>
    </div>}
    <fieldset className="space-y-2">
      <legend className="text-xs font-semibold text-ink">Por critério</legend>
      <div className="grid gap-2 sm:grid-cols-3">
        <label className="analise-rotulo-campo">Critério
          <select data-testid="analise-ref-criterio" value={atributo} onChange={event => setAtributo(event.target.value as PainelAtributo)} className="analise-campo">
            <option value="densidade">Densidade</option><option value="quantidade">Quantidade</option><option value="populacao">População</option>
          </select>
        </label>
        <label className="analise-rotulo-campo">Ordem
          <select data-testid="analise-ref-ordem" value={ordem} onChange={event => setOrdem(event.target.value as PainelOrdem)} className="analise-campo">
            <option value="desc">Da maior para a menor</option><option value="asc">Da menor para a maior</option>
          </select>
        </label>
        <label className="analise-rotulo-campo">Procurar em
          <select data-testid="analise-ref-universo" value={procurarEm} onChange={event => setUniverso(event.target.value as "base" | "todos")} className="analise-campo">
            <option value="base" disabled={semBase}>Os do gráfico</option><option value="todos">{maiuscula(todosOs(unidade))}</option>
          </select>
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" data-testid="analise-ref-listar" onClick={() => void listar()} disabled={carregando || !p.competencia} className="analise-botao-secundario">
          {carregando && <LoaderCircle size={14} className="animate-spin" aria-hidden="true"/>}Listar candidatos</button>
        <button type="button" data-testid="analise-ref-primeiro" onClick={usarPrimeiro} disabled={!primeirosColocados(todosCandidatos).length}
          className="analise-botao-secundario">Usar o primeiro</button>
      </div>
    </fieldset>
    {erro && <p role="alert" className="text-xs text-rose-800">{erro}</p>}
    {empate && <p role="status" data-testid="analise-ref-empate" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
      Há empate na 1ª posição. Escolha entre os empatados abaixo e use Aplicar referência.</p>}
    {lista && <div className="space-y-2">
      <p className="text-xs text-slate-600">Ordem do motor por {ATRIBUTOS[lista.resposta.criterio.atributo]}, {ORDENS[lista.resposta.criterio.ordem]}, em{" "}
        {exibirCompetencia(lista.resposta.competencia)}; empates ficam na mesma posição.</p>
      {p.conjuntos.length > 0 && <p className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600">Marcar os membros de um conjunto:
        {p.conjuntos.map(conjunto => <button key={conjunto.id} type="button" className="analise-chip"
          onClick={() => setMarcados(conjunto.membros.filter(id => candidatos.some(item => item.id === id)))}>{conjunto.rotulo}</button>)}</p>}
      <ol data-testid="analise-ref-candidatos" aria-label="Candidatos a referência" className="analise-lista-rolavel">
        {candidatos.map(item => <li key={item.id} data-testid="analise-ref-candidato" data-id={item.id} data-posicao={item.posicao ?? ""}>
          <label className="analise-caixa">
            <input type="checkbox" checked={marcados.includes(item.id)} onChange={() => alternar(item.id)}/>
            <span className="w-9 shrink-0 tabular-nums text-slate-600">{item.posicao !== null ? item.posicao + "º" : "—"}</span>
            <span className="min-w-0 flex-1 truncate">{item.rotulo}</span>
            <span className="shrink-0 tabular-nums text-slate-700">{valorDoCandidato(item.valor, atributoDaLista)}</span>
          </label>
        </li>)}
      </ol>
      {naoAvaliaveis.length > 0 && !empate && <details className="text-xs text-slate-600">
        <summary className="cursor-pointer">Não avaliáveis para o critério (sem posição)</summary>
        <ul className="mt-1 space-y-0.5">{naoAvaliaveis.map(item => <li key={item.id}>{item.rotulo}{item.motivos.length ? ": " + item.motivos.join("; ") : ""}</li>)}</ul>
      </details>}
    </div>}
    <fieldset className="space-y-2">
      <legend className="text-xs font-semibold text-ink">Pelo nome</legend>
      <input type="search" data-testid="analise-ref-busca" value={consulta} onChange={event => setConsulta(event.target.value)}
        placeholder={"Nome ou código " + (generoDe(unidade) === "f" ? "da " : "do ") + unidade.singular} className="analise-campo"/>
      {achados.length > 0 && <ul className="space-y-0.5">{achados.map(item => <li key={item.id} data-testid="analise-ref-achado" data-id={item.id}>
        <label className="analise-caixa">
          <input type="checkbox" checked={marcados.includes(item.id)} onChange={() => alternar(item.id)}/>
          <span className="min-w-0 flex-1">{item.name ? item.name + (item.state ? " (" + item.state + ")" : "") : item.label}</span>
        </label>
      </li>)}</ul>}
    </fieldset>
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" data-testid="analise-ref-aplicar" onClick={() => aplicar(marcados)} disabled={!marcados.length} className="analise-botao-primario">
        Aplicar referência</button>
      {marcados.length > 0 && <span className="text-xs text-slate-600">{marcados.length === 1 ? "1 marcado" : marcados.length + " marcados: conjunto de referência"}</span>}
    </div>
    <fieldset className="space-y-2 border-t border-line pt-3">
      <legend className="text-xs font-semibold text-ink">Faixas de distância (opcional)</legend>
      <p className="text-[11px] leading-4 text-slate-600">Limites em km, separados por ponto e vírgula (por exemplo, 0; 100; 300). O motor conta quantos ficam
        em cada faixa (CAP-ESP-03).</p>
      <div className="flex flex-wrap gap-2">
        <input data-testid="analise-faixas-distancia" value={faixas} onChange={event => setFaixas(event.target.value)} inputMode="decimal"
          className="analise-campo w-40" aria-label="Limites das faixas de distância (km)"/>
        <button type="button" data-testid="analise-faixas-distancia-aplicar" className="analise-botao-secundario"
          disabled={lerLimites(faixas).length < 2 && !!faixas.trim()} onClick={() => p.onFaixas(lerLimites(faixas))}>
          {faixas.trim() ? "Aplicar faixas" : "Sem faixas"}</button>
      </div>
    </fieldset>
    <p data-testid="analise-nota-tpl11" className="text-[11px] leading-4 text-slate-600">{NOTA_TPL11}</p>
  </section>;
}

// ------------------------------------------------------------------------------------------------ condições
type Rascunho = { atributo: AtributoCondicao; operador: OperadorCondicao; valor: string };
type CondicoesProps = { condicoes: CondicaoPedido[]; espacial: boolean; resposta: PainelResposta | null; rotulos: RotulosTerritoriais;
  soAtende: boolean; onSoAtende: (valor: boolean) => void; onAplicar: (condicoes: CondicaoPedido[]) => void };
const UNIDADES: Record<AtributoCondicao, string> = { densidade: "por 1.000 habitantes", quantidade: "profissionais", populacao: "habitantes", distancia_km: "km" };
const lerNumero = (texto: string) => { const valor = Number(texto.trim().replace(/\./g, "").replace(",", ".")); return texto.trim() && Number.isFinite(valor) ? valor : null; };
/** Condições (CAP-SUB-01, o antigo "critérios combinados"): separa quem atende a todas as condições, quem não atende e quem não
 * tem dado para avaliar. Combinação "e". As contagens vêm do motor. */
export function GavetaCondicoes(p: CondicoesProps) {
  const paraRascunho = (c: CondicaoPedido): Rascunho => ({ atributo: c.atributo, operador: c.operador, valor: String(c.valor).replace(".", ",") });
  const [linhas, setLinhas] = useState<Rascunho[]>(() => p.condicoes.length ? p.condicoes.map(paraRascunho) : [{ atributo: "densidade", operador: "<", valor: "" }]);
  useEffect(() => { if (p.condicoes.length) setLinhas(p.condicoes.map(paraRascunho)); }, [JSON.stringify(p.condicoes)]);
  const validas = linhas.map(linha => ({ ...linha, numero: lerNumero(linha.valor) }));
  const prontas = validas.every(linha => linha.numero !== null) && validas.length > 0;
  const contagens = p.resposta?.condicoes?.contagens;
  const unidade = p.rotulos.unidade;
  const mudar = (indice: number, parte: Partial<Rascunho>) => setLinhas(atual => atual.map((linha, i) => i === indice ? { ...linha, ...parte } : linha));
  const NOMES: Record<SituacaoCondicao, string> = { ATENDE: "Atendem a todas", NAO_ATENDE: "Não atendem", NAO_AVALIAVEL: "Sem dado para avaliar" };
  return <section data-testid="analise-condicoes" aria-label="Seleção por condições" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">Separa {artigo(unidade, true)} {unidade.plural} que atendem a todas as condições escolhidas, os que não atendem
      e os que não têm dado para avaliar. Por exemplo: menos de 1 profissional por 1.000 habitantes e mais de 150 km da referência.</p>
    <ol className="space-y-2">
      {linhas.map((linha, indice) => <li key={indice} data-testid="analise-condicao" className="flex flex-wrap items-end gap-1.5">
        <label className="analise-rotulo-campo min-w-[8rem] flex-1">Indicador
          <select data-testid="analise-condicao-atributo" value={linha.atributo} onChange={event => mudar(indice, { atributo: event.target.value as AtributoCondicao })} className="analise-campo">
            <option value="densidade">Densidade</option><option value="quantidade">Quantidade</option><option value="populacao">População</option>
            <option value="distancia_km" disabled={!p.espacial}>Distância até a referência (km){p.espacial ? "" : " · só na análise espacial"}</option>
          </select>
        </label>
        <label className="analise-rotulo-campo w-28">Condição
          <select data-testid="analise-condicao-operador" value={linha.operador} onChange={event => mudar(indice, { operador: event.target.value as OperadorCondicao })} className="analise-campo">
            {(Object.keys(OPERADORES) as OperadorCondicao[]).map(op => <option key={op} value={op}>{SIMBOLOS[op]} {OPERADORES[op]}</option>)}
          </select>
        </label>
        <label className="analise-rotulo-campo w-28">Valor ({UNIDADES[linha.atributo]})
          <input data-testid="analise-condicao-valor" inputMode="decimal" value={linha.valor} onChange={event => mudar(indice, { valor: event.target.value })}
            className="analise-campo" aria-invalid={!!linha.valor.trim() && lerNumero(linha.valor) === null}/>
        </label>
        {linhas.length > 1 && <button type="button" className="analise-icone" aria-label={"Tirar a condição " + (indice + 1)}
          onClick={() => setLinhas(atual => atual.filter((_, i) => i !== indice))}><Trash2 size={14} aria-hidden="true"/></button>}
      </li>)}
    </ol>
    <div className="flex flex-wrap gap-2">
      <button type="button" data-testid="analise-condicao-mais" className="analise-botao-secundario" disabled={linhas.length >= 5}
        onClick={() => setLinhas(atual => [...atual, { atributo: "densidade", operador: ">", valor: "" }])}><Plus size={14} aria-hidden="true"/>Condição</button>
      <button type="button" data-testid="analise-condicoes-aplicar" className="analise-botao-primario" disabled={!prontas}
        onClick={() => p.onAplicar(validas.map(linha => ({ atributo: linha.atributo, operador: linha.operador, valor: linha.numero as number })))}>
        Aplicar condições</button>
      {p.condicoes.length > 0 && <button type="button" data-testid="analise-condicoes-limpar" className="analise-botao-secundario"
        onClick={() => { p.onAplicar([]); p.onSoAtende(false); }}>Limpar</button>}
    </div>
    {contagens && p.condicoes.length > 0 && <div className="space-y-2">
      <ul className="flex flex-wrap gap-1.5" aria-label="Contagens do motor">
        {(["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"] as SituacaoCondicao[]).map(situacao => <li key={situacao} data-testid="analise-condicoes-contagem"
          data-situacao={situacao} data-contagem={contagens[situacao] ?? ""} className="analise-contagem">
          <strong className="tabular-nums text-ink">{contagens[situacao] ?? "—"}</strong> {NOMES[situacao].toLowerCase()}</li>)}
      </ul>
      <label className="analise-caixa">
        <input type="checkbox" data-testid="analise-condicoes-so-atende" checked={p.soAtende} onChange={event => p.onSoAtende(event.target.checked)}/>
        <span>Mostrar no gráfico só quem atende (filtro visual, sem novo cálculo)</span>
      </label>
      {(p.resposta?.condicoes?.textos || []).map(texto => <p key={texto} className="text-[11px] text-slate-600">{texto}</p>)}
    </div>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ ordenar
type OrdenarProps = { ordenar: OrdenarPedido | null; espacial: boolean; mudanca: boolean; resposta: PainelResposta | null;
  indicador: PainelIndicador; onAplicar: (ordenar: OrdenarPedido | null) => void };
/** Ordenar (CAP-SUB-02 e CAP-SUB-03): a ordem e as posições do motor, com empates na mesma posição, e os N primeiros. */
export function GavetaOrdenar(p: OrdenarProps) {
  const [atributo, setAtributo] = useState<AtributoOrdenacao>(p.ordenar?.atributo ?? p.indicador);
  const [ordem, setOrdem] = useState<PainelOrdem>(p.ordenar?.ordem ?? "desc");
  const [primeiros, setPrimeiros] = useState(p.ordenar?.primeiros ? String(p.ordenar.primeiros) : "10");
  const n = Number(primeiros);
  const valido = !primeiros.trim() || (Number.isInteger(n) && n > 0);
  const ordenacao = p.resposta?.ordenacao;
  const posicionados = useMemo(() => (p.resposta?.itens || []).filter(item => item.ordem?.posicao !== null && item.ordem?.posicao !== undefined)
    .sort((a, b) => (a.ordem!.posicao as number) - (b.ordem!.posicao as number) || ordemNeutra(a, b)), [p.resposta]);
  const limite = ordenacao?.primeiros ?? null;
  const mostrados = limite !== null ? posicionados.filter(item => (item.ordem!.posicao as number) <= limite) : posicionados.slice(0, 20);
  const valorDe = (item: PainelItem) => {
    const a = ordenacao?.atributo || atributo;
    if (a === "variacao") return formatarVariacao(variacaoDe(item, p.indicador));
    if (a === "distancia_km") return numero(item.distancia_km) === null ? "Não avaliável" : formatarNumero(item.distancia_km as number) + " km";
    if (a === "populacao") return numero(item.populacao) === null ? "Não avaliável" : formatarNumero(item.populacao as number, true) + " habitantes";
    if (a === "quantidade" || a === "densidade") return formatarIndicador(numero(item[a]), a);
    return "";
  };
  return <section data-testid="analise-ordenar" aria-label="Ordenar" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">O motor ordena pelo indicador e no sentido que você escolher; empates ficam na mesma posição (1, 2, 2, 4).
      "Os N primeiros" mostra só as posições até N, com todos os empatados no corte.</p>
    <div className="grid gap-2 sm:grid-cols-3">
      <label className="analise-rotulo-campo">Indicador
        <select data-testid="analise-ordenar-atributo" value={atributo} onChange={event => setAtributo(event.target.value as AtributoOrdenacao)} className="analise-campo">
          <option value="densidade">Densidade</option><option value="quantidade">Quantidade</option><option value="populacao">População</option>
          <option value="distancia_km" disabled={!p.espacial}>Distância (km){p.espacial ? "" : " · só na análise espacial"}</option>
          <option value="variacao" disabled={!p.mudanca}>Variação (%){p.mudanca ? "" : " · só na mudança"}</option>
        </select>
      </label>
      <label className="analise-rotulo-campo">Ordem
        <select data-testid="analise-ordenar-ordem" value={ordem} onChange={event => setOrdem(event.target.value as PainelOrdem)} className="analise-campo">
          <option value="desc">Da maior para a menor</option><option value="asc">Da menor para a maior</option>
        </select>
      </label>
      <label className="analise-rotulo-campo">Os N primeiros
        <input data-testid="analise-ordenar-primeiros" inputMode="numeric" value={primeiros} onChange={event => setPrimeiros(event.target.value)}
          className="analise-campo" aria-invalid={!valido} placeholder="todos"/>
      </label>
    </div>
    <div className="flex flex-wrap gap-2">
      <button type="button" data-testid="analise-ordenar-aplicar" className="analise-botao-primario" disabled={!valido}
        onClick={() => p.onAplicar({ atributo, ordem, ...(primeiros.trim() ? { primeiros: n } : {}) })}>Ordenar</button>
      {p.ordenar && <button type="button" data-testid="analise-ordenar-limpar" className="analise-botao-secundario" onClick={() => p.onAplicar(null)}>Limpar</button>}
    </div>
    {ordenacao && p.ordenar && <div className="space-y-1.5">
      <p className="text-xs text-slate-700">{ordenacao.texto || "Ordem do motor por " + (ATRIBUTOS[ordenacao.atributo] || ordenacao.atributo) + ", " +
        (ORDENS[ordenacao.ordem as PainelOrdem] || ordenacao.ordem) + "."}{ordenacao.empatesNoCorte ? " Há empate no corte: os empatados entram juntos." : ""}</p>
      <ol data-testid="analise-ordenar-lista" className="analise-lista-rolavel">
        {mostrados.map(item => <li key={item.id} data-id={item.id} data-posicao={item.ordem!.posicao ?? ""} className="flex items-center gap-2 px-2 py-1 text-xs">
          <span className="w-9 shrink-0 tabular-nums text-slate-600">{item.ordem!.posicao}º</span>
          <span className="min-w-0 flex-1 truncate text-ink">{item.rotulo}</span>
          <span className="shrink-0 tabular-nums text-slate-700">{valorDe(item)}</span>
        </li>)}
      </ol>
      {limite === null && posicionados.length > 20 && <p className="text-[11px] text-slate-600">Os 20 primeiros; a ordem completa fica na tabela (coluna Posição).</p>}
    </div>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ comparar
type CompararProps = { itens: PainelItem[]; selecionados: string[]; pedidos: string[]; resposta: PainelResposta | null;
  indicador: PainelIndicador; distancia: boolean; variacao: boolean; competenciaInicial: string | null; nomes: Map<string, string>;
  onAlternar: (id: string) => void; onLimpar: () => void; onComparar: (ids: string[]) => void };
/** Comparar (CAP-CMP-01): 2 ou 3 itens lado a lado, com maior, menor e diferença vindos do motor. */
export function GavetaComparar(p: CompararProps) {
  const escolhidos = p.selecionados.map(id => p.itens.find(item => item.id === id)).filter((item): item is PainelItem => !!item);
  const especie = INDICADORES[p.indicador];
  const comparacao = p.resposta?.comparacao;
  const atual = p.pedidos.length >= 2 && [...p.pedidos].sort().join() === [...p.selecionados].sort().join();
  const nome = (id: string) => p.nomes.get(id) || id;
  const valorComparado = (atributo: string, valor: number | null) => valor === null ? "Não avaliável"
    : atributo === "densidade" || atributo === "quantidade" ? formatarIndicador(valor, atributo)
    : atributo === "populacao" ? formatarNumero(valor, true) + " habitantes" : atributo === "distancia_km" ? formatarNumero(valor) + " km"
    : atributo.startsWith("variacao") ? formatarVariacao(valor) : formatarNumero(valor);
  return <section data-testid="analise-comparar" aria-label="Comparar" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">Clique nas bolhas (ou marque na tabela) para escolher dois ou três itens; os demais esmaecem. O motor
      diz qual é o maior, o menor e a diferença.</p>
    {escolhidos.length > 0 ? <ul className="flex flex-wrap gap-1.5" aria-label="Itens escolhidos">
      {escolhidos.map(item => <li key={item.id} data-testid="analise-comparar-item" data-id={item.id} className="analise-etiqueta">
        {item.rotulo}
        <button type="button" aria-label={"Tirar " + item.rotulo} onClick={() => p.onAlternar(item.id)} className="analise-icone"><X size={13} aria-hidden="true"/></button>
      </li>)}
      <li><button type="button" onClick={p.onLimpar} className="analise-link text-xs">Limpar a escolha</button></li>
    </ul> : <p className="text-xs text-slate-600">Nenhum item escolhido.</p>}
    {escolhidos.length > 3 && <p className="text-xs text-amber-900">Para comparar lado a lado, deixe até três itens. Com mais, use Juntar.</p>}
    <button type="button" data-testid="analise-comparar-calcular" className="analise-botao-primario"
      disabled={escolhidos.length < 2 || escolhidos.length > 3 || atual} onClick={() => p.onComparar(escolhidos.map(item => item.id))}>
      {atual ? "Comparação em exibição" : "Comparar"}</button>
    {escolhidos.length > 0 && escolhidos.length <= 3 && <div className="grid gap-2 sm:grid-cols-3">
      {escolhidos.map(item => <article key={item.id} className="min-w-0 rounded-xl border border-line bg-slate-50 p-3 text-xs">
        <h4 className="truncate font-semibold text-ink" title={item.rotulo}>{item.rotulo}</h4>
        {item.tipo === "conjunto" && <p className="text-[11px] text-slate-600">{textoDaContagem(item.contagem)}</p>}
        <dl className="mt-1 grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-0.5 text-slate-700">
          <dt className="text-slate-500">{especie.rotulo}</dt><dd className="font-semibold text-ink">{formatarIndicador(numero(item[p.indicador]), p.indicador)}</dd>
          <dt className="text-slate-500">População</dt><dd>{numero(item.populacao) === null ? "Não avaliável" : formatarNumero(item.populacao as number, true)}</dd>
          {p.distancia && <><dt className="text-slate-500">Distância</dt><dd>{numero(item.distancia_km) === null ? "Não avaliável" : formatarNumero(item.distancia_km as number) + " km"}</dd></>}
          {p.variacao && <><dt className="text-slate-500">Variação</dt><dd>{formatarVariacao(variacaoDe(item, p.indicador))}
            {p.competenciaInicial ? <span className="text-slate-500"> desde {exibirCompetencia(p.competenciaInicial)}</span> : null}</dd></>}
        </dl>
      </article>)}
    </div>}
    {atual && comparacao && <section data-testid="analise-comparacao" aria-label="Comparação do motor" className="space-y-2 rounded-xl border border-line bg-white p-3 text-xs">
      <h4 className="font-bold text-ink">Comparação do motor</h4>
      {comparacao.linhas.map(linha => <div key={linha.atributo} data-testid="analise-comparacao-linha" data-atributo={linha.atributo} className="space-y-0.5">
        {linha.atributo && <p className="font-semibold text-ink">{maiuscula(ATRIBUTOS[linha.atributo] || linha.atributo)}</p>}
        {linha.maior.length > 0 && <p>Maior: {linha.maior.map(item => item.rotulo + " (" + valorComparado(linha.atributo, item.valor) + ")").join(" e ")}
          {linha.maior.length > 1 ? " (empate)" : ""}</p>}
        {linha.menor.length > 0 && <p>Menor: {linha.menor.map(item => item.rotulo + " (" + valorComparado(linha.atributo, item.valor) + ")").join(" e ")}
          {linha.menor.length > 1 ? " (empate)" : ""}</p>}
        {linha.diferencas.map((dif, indice) => <p key={indice}>Diferença{dif.entre.length === 2 ? " entre " + nome(dif.entre[0]) + " e " + nome(dif.entre[1]) : ""}:{" "}
          {dif.texto || valorComparado(linha.atributo, dif.valor)}</p>)}
      </div>)}
      {comparacao.textos.map(texto => <p key={texto} className="text-slate-600">{texto}</p>)}
    </section>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ juntar
type JuntarProps = { itens: PainelItem[]; selecionados: string[]; conjuntos: PainelConjuntoPedido[]; rotulos: RotulosTerritoriais;
  nivelGrupos: boolean; onJuntar: (rotulo: string) => void; onDesfazer: (id: string) => void };
/** Juntar (CAP-AGR-01): as unidades escolhidas viram uma bolha agregada pelo motor, com a soma das contagens dos componentes e
 * possível dupla contagem (RQ-REP-14). Estados e municípios nunca se somam: na visão dos grupos, Juntar fica desligado. */
export function GavetaJuntar(p: JuntarProps) {
  const [nome, setNome] = useState("");
  const unidades = p.selecionados.map(id => p.itens.find(item => item.id === id)).filter((item): item is PainelItem => !!item && item.tipo === "municipio");
  const unidade = p.rotulos.unidade;
  return <section data-testid="analise-juntar" aria-label="Juntar" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">Escolha {generoDe(unidade) === "f" ? "duas" : "dois"} ou mais {unidade.plural} no gráfico ou na tabela. O motor devolve uma bolha com a soma
      das populações e das contagens dos membros: soma das contagens dos componentes, com possível dupla contagem.</p>
    {p.nivelGrupos ? <p className="text-xs text-amber-900">Na visão dos {(p.rotulos.grupo?.plural || "grupos")}, Juntar fica desligado: {p.rotulos.grupo?.plural || "grupos"} e{" "}
      {unidade.plural} nunca se somam aqui. Abra {unidade.plural} para juntar.</p> : <>
      <p className="text-xs text-slate-700">{unidades.length ? "Escolhidos: " + unidades.map(item => item.rotulo).join(", ") + "." : "Nenhum escolhido."}</p>
      <div className="flex flex-wrap items-end gap-2">
        <label className="analise-rotulo-campo min-w-[12rem] flex-1">Nome do conjunto
          <input data-testid="analise-juntar-nome" value={nome} onChange={event => setNome(event.target.value)} maxLength={60}
            placeholder={"Conjunto " + (p.conjuntos.length + 1)} className="analise-campo"/>
        </label>
        <button type="button" data-testid="analise-juntar-criar" disabled={unidades.length < 2 || p.conjuntos.length >= MAX_CONJUNTOS}
          onClick={() => { p.onJuntar(nome); setNome(""); }} className="analise-botao-primario">Juntar escolhidos</button>
      </div>
    </>}
    {p.conjuntos.length >= MAX_CONJUNTOS && <p className="text-[11px] text-amber-900">O gráfico aceita até {MAX_CONJUNTOS} conjuntos.</p>}
    {p.conjuntos.length > 0 && <ul className="space-y-1" aria-label="Conjuntos">
      {p.conjuntos.map(conjunto => <li key={conjunto.id} data-testid="analise-conjunto" data-id={conjunto.id}
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-white px-3 py-2 text-xs">
        <span className="min-w-0"><strong className="text-ink">{conjunto.rotulo}</strong> · {quantos(conjunto.membros.length, unidade)} · soma das contagens dos
          componentes, com possível dupla contagem</span>
        <button type="button" onClick={() => p.onDesfazer(conjunto.id)} className="analise-link">Desfazer</button>
      </li>)}
    </ul>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ exportar
type ExportarProps = { pronto: boolean; onCsv: () => void; onImprimir: () => void; onMetodo: () => void };
/** Exportar (CAP-REP-05/06): CSV com precisão integral, avaliabilidade e motivo; Imprimir/PDF; método e parâmetros. */
export function GavetaExportar({ pronto, onCsv, onImprimir, onMetodo }: ExportarProps) {
  return <section data-testid="analise-exportar" aria-label="Exportar" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">O CSV traz todos os itens do resultado (com ou sem a régua), com os valores do motor em precisão integral,
      a avaliabilidade e o motivo de cada um. Imprimir / PDF leva o título, o gráfico, as legendas e os detalhes.</p>
    <div className="flex flex-col gap-2">
      <button type="button" data-testid="analise-exportar-csv" disabled={!pronto} onClick={onCsv} className="analise-botao-primario justify-start">
        <Download size={15} aria-hidden="true"/>Baixar CSV (precisão integral)</button>
      <button type="button" data-testid="analise-exportar-imprimir" disabled={!pronto} onClick={onImprimir} className="analise-botao-secundario justify-start">
        <Printer size={15} aria-hidden="true"/>Imprimir / PDF</button>
      <button type="button" data-testid="analise-exportar-metodo" disabled={!pronto} onClick={onMetodo} className="analise-botao-secundario justify-start">
        <FileText size={15} aria-hidden="true"/>Baixar método e parâmetros (TXT)</button>
    </div>
    <p className="text-[11px] leading-4 text-slate-600">A sessão é temporária: para guardar a análise, exporte agora ou use o Histórico.</p>
  </section>;
}

