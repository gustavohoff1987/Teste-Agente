import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, Search, Trash2, X } from "lucide-react";
import MapaDosConjuntos from "./MapaDosConjuntos";
import {
  pedirCriterios, type CriteriosOpcoes, type FiltroDoCriterio, type FonteDoMotor, type PainelMunicipios, type Premissas, type RespostaCriterios,
  type RotulosTerritoriais,
} from "./painelApi";
import {
  OPERADORES, SIMBOLOS, artigo, competenciaAbreviada, cronologica, grupoDaUnidade, maiuscula, nomeDaUnidade, quantos, unidadeMarcada,
  type GrupoInfo, type UnidadeDoCatalogo,
} from "./painelModel";
import { comNomesAnteriores } from "./painelModel";

// "Aplicar critérios de seleção" (comando V22, 9/11/2026, seção 4; antes, o modo "Por critérios" da coluna da esquerda, de 07/11/2026),
// aberto pela ação do painel direito da Seleção, com a árvore à vista. Passos numerados, abaixo do mini mapa: 1. Onde procurar (abre
// em "o país todo", decisão 5; continuam as regiões, os estados e os marcados, sempre com os nomes da base); 2. Critérios (indicador,
// comparação e valor, valendo juntos, CAP-SUB-01, com a competência, em ordem de data, e a distância opcional "a até X km de"). O
// agrupamento por proximidade saiu daqui e foi para "Agrupar territórios selecionados" (seção 5): um pedido com agrupamento (da
// conversa ou de uma regra de antes) usa os que atendem como seleção e abre o agrupamento com a distância. A prévia é toda do motor
// (POST /api/painel/criterios) e se atualiza sozinha a cada ajuste; o mini mapa mostra o resultado e, enquanto falta algo, o último
// válido, esmaecido. O rodapé reúne a linha de estado e as saídas: "Usar como seleção (N)", no lugar da seleção atual (o padrão) ou
// junto com ela, com o que sai e o que fica de fora dito antes, e "Cancelar". Nada é sugerido; a tela não calcula.

type Onde = "todo" | "regioes" | "estados" | "marcados";
type Rascunho = { atributo: FiltroDoCriterio["indicador"]; operador: FiltroDoCriterio["operador"]; valor: string };
/** O que a pessoa pediu: os critérios, o agrupamento e, com os marcados, a seleção em que procurou (para reaplicar nela). */
export type PedidoDosCriterios = { criterios: CriteriosOpcoes["criterios"]; agrupar: { km: number } | null; base?: PainelMunicipios };
/** A escolha do rodapé: no lugar da seleção atual ou junto com ela (desde o comando V22, sem conjuntos: o agrupamento foi para "Agrupar
 * territórios selecionados"; `conjuntos`, `levarSemConjunto` e `nomes` ficam pelo contrato, sempre vazios). */
export type UsoDosCriterios = { conjuntos: boolean; junto: boolean; levarSemConjunto: boolean; nomes: Record<string, string> };
type Props = {
  fonte: FonteDoMotor;
  rotulos: RotulosTerritoriais;
  nomeDoTodo: string;
  unidades: UnidadeDoCatalogo[];
  competencia: string;
  periodos: string[];
  categoria: string;
  premissas?: Premissas;
  /** Os grupos da base (os estados) e os grupos de cima (as regiões), com o grupo de cima de cada grupo. */
  grupos: GrupoInfo[];
  regioes: GrupoInfo[];
  regiaoDoGrupo?: (grupo: string) => string;
  /** Os marcados na lista: a base (unidades) ou, vendo por grupo, os grupos marcados. */
  marcados: { base: PainelMunicipios | null; grupos: string[]; vendoPorGrupo: boolean };
  /** O lugar em uso na trilha. Desde o comando V22 (decisão 5), "Onde procurar" abre sempre em "o país todo"; o lugar fica só como
   * referência do contrato. */
  lugar?: { tipo: "regioes" | "estados"; ids: string[] } | null;
  /** Junto com a seleção atual (comando V22, seção 4): os municípios dos estados como unidade não entram, nem os membros de um
   * conjunto da seleção; a tela diz quantos ficam de fora e por quê. No lugar dela, o que sai da seleção. */
  naSelecao?: { estados: string[]; membrosDeConjuntos: string[]; conjuntos: number; grupoDe: (id: string) => string };
  /** A regra a reaplicar, o pedido da conversa ou o das Condições, já preenchidos. */
  inicial?: PedidoDosCriterios | null;
  aviso?: string;
  /** Coordenadas autorizadas para o mini mapa (do motor), só para desenhar. */
  coordenadas: Map<string, [number, number]> | null;
  /** Os conjuntos que já estão na análise (os nomes contam para as letras e para a unicidade) e se a análise tem algo. */
  conjuntosNaAnalise: { id: string; rotulo: string }[];
  algoNaAnalise: boolean;
  onUsar: (previa: RespostaCriterios, pedido: PedidoDosCriterios, uso: UsoDosCriterios) => void;
  /** Sem uso desde o comando V22 (a árvore fica sempre à vista); fica pelo contrato. */
  onMarcarNaLista?: () => void;
  onCancelar: () => void;
};

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const lerNumero = (texto: string) => {
  const limpo = texto.trim();
  if (!limpo || /[,.]$/.test(limpo)) return null;
  const valor = Number(limpo.replace(/\./g, "").replace(",", "."));
  return Number.isFinite(valor) ? valor : null;
};
const UNIDADE_DO_VALOR: Record<Rascunho["atributo"], string> = { densidade: "por 1.000 habitantes", quantidade: "profissionais", populacao: "habitantes" };
const valorDe = (numero: number) => String(numero).replace(".", ",");
const ESPERA_DA_PREVIA = 300;

export default function SelecionarPorCriterios(p: Props) {
  const unidade = p.rotulos.unidade, feminino = (unidade.genero ?? "m") === "f";
  const grupoRotulo = p.rotulos.grupo ?? { singular: "estado", plural: "estados" };
  const superior = p.rotulos.grupo_superior ?? { singular: "região", plural: "regiões" };
  const grupoF = artigo(grupoRotulo, false) === "a", superiorF = artigo(superior, false) === "a";
  const inicial = p.inicial?.criterios;
  const baseDaRegra = p.inicial?.base ?? null;
  // "Onde procurar" abre em "o país todo" (comando V22, decisão 5); uma regra ou um pedido já preenchido abre como veio.
  const [onde, setOnde] = useState<Onde>(() => inicial?.partir_de.tipo === "selecao" ? "marcados"
    : inicial?.partir_de.tipo === "ufs" ? "estados" : inicial?.partir_de.tipo === "regioes" ? "regioes" : "todo");
  const [regioesEscolhidas, setRegioesEscolhidas] = useState<string[]>(() => inicial?.partir_de.tipo === "regioes" ? inicial.partir_de.regioes ?? [] : []);
  const [estadosEscolhidos, setEstadosEscolhidos] = useState<string[]>(() => inicial?.partir_de.tipo === "ufs" ? inicial.partir_de.ufs ?? [] : []);
  const [competencia, setCompetencia] = useState(p.competencia);
  const [linhas, setLinhas] = useState<Rascunho[]>(() => inicial?.filtros.length
    ? inicial.filtros.map(filtro => ({ atributo: filtro.indicador, operador: filtro.operador, valor: valorDe(filtro.valor) }))
    : [{ atributo: "densidade", operador: "<", valor: "" }]);
  const [comDistancia, setComDistancia] = useState(!!inicial?.distancia);
  const [de, setDe] = useState<string | null>(inicial?.distancia?.de ?? null);
  const [km, setKm] = useState(inicial?.distancia ? valorDe(inicial.distancia.km) : "");
  const [consulta, setConsulta] = useState("");
  // O agrupamento de um pedido de antes (da conversa ou de uma regra): fica para "Agrupar territórios selecionados", depois de usar.
  const agruparDepois = p.inicial?.agrupar ?? null;
  const [previa, setPrevia] = useState<{ chave: string; dados: RespostaCriterios } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [junto, setJunto] = useState(false);
  const periodos = useMemo(() => cronologica(p.periodos), [p.periodos]);
  const controle = useRef<AbortController | null>(null);
  const porId = useMemo(() => new Map(p.unidades.map(item => [item.id, item])), [p.unidades]);
  const validas = useMemo(() => p.unidades.filter(item => !item.selection_reason), [p.unidades]);
  const termo = sem(consulta.trim());
  const resultados = useMemo(() => termo.length < 2 ? [] : validas.filter(item => sem(comNomesAnteriores(nomeDaUnidade(item), item.former_names)).includes(termo)).slice(0, 8),
    [validas, termo]);
  const mudar = (indice: number, parte: Partial<Rascunho>) => setLinhas(atual => atual.map((linha, i) => i === indice ? { ...linha, ...parte } : linha));
  const nomeDe = (id: string) => { const item = porId.get(id); return item ? nomeDaUnidade(item) : id; };
  const marcadosBase = baseDaRegra ?? p.marcados.base;
  const quantosMarcados = useMemo(() => p.marcados.vendoPorGrupo ? p.marcados.grupos.length
    : marcadosBase ? validas.filter(item => unidadeMarcada(marcadosBase, item.id, grupoDaUnidade(item))).length : 0,
  [p.marcados, marcadosBase, validas]);

  // ---------------------------------------------------------------------------------------------- o pedido e o que falta
  const filtros = linhas.filter(linha => linha.valor.trim()).map(linha => ({ indicador: linha.atributo, operador: linha.operador,
    valor: lerNumero(linha.valor) }));
  const kmDistancia = lerNumero(km);
  const distancia = comDistancia && de && kmDistancia !== null && kmDistancia > 0 ? { de, km: kmDistancia } : null;
  const gruposDasRegioes = (ids: string[]) => p.grupos.filter(grupo => ids.includes(p.regiaoDoGrupo?.(grupo.id) ?? "")).map(grupo => grupo.id);
  // Uma região vira os grupos dela (como o lugar em uso já fazia); os marcados, vendo por grupo, os grupos marcados.
  const partirDe: CriteriosOpcoes["criterios"]["partir_de"] = onde === "regioes" ? { tipo: "ufs", ufs: gruposDasRegioes(regioesEscolhidas) }
    : onde === "estados" ? { tipo: "ufs", ufs: estadosEscolhidos }
      : onde === "marcados" ? (p.marcados.vendoPorGrupo && !baseDaRegra ? { tipo: "ufs", ufs: p.marcados.grupos } : { tipo: "selecao" })
        : { tipo: "pais" };
  const pedido: PedidoDosCriterios = { criterios: { partir_de: partirDe, filtros: filtros.filter(filtro => filtro.valor !== null)
    .map(filtro => ({ ...filtro, valor: filtro.valor as number })), ...(distancia ? { distancia } : {}) },
  agrupar: null, ...(partirDe.tipo === "selecao" && marcadosBase ? { base: marcadosBase } : {}) };
  // O que falta (item 7.4), na ordem dos passos.
  const falta = (() => {
    if (onde === "regioes" && !regioesEscolhidas.length) return "Escolha ao menos " + (superiorF ? "uma " : "um ") + superior.singular + ".";
    if (onde === "estados" && !estadosEscolhidos.length) return "Escolha ao menos " + (grupoF ? "uma " : "um ") + grupoRotulo.singular + ".";
    if (onde === "marcados" && !quantosMarcados) return "Marque " + unidade.plural + " na lista para procurar entre " + (feminino ? "elas." : "eles.");
    const invalido = linhas.findIndex(linha => linha.valor.trim() && lerNumero(linha.valor) === null);
    if (invalido >= 0) return "Falta o valor do critério " + (invalido + 1) + ".";
    if (comDistancia && !de) return "Falta " + (feminino ? "a " : "o ") + unidade.singular + " da distância.";
    if (comDistancia && !distancia) return "Falta a distância dos critérios, em km.";
    if (!pedido.criterios.filtros.length && !distancia && !agruparDepois) return "Falta o valor do critério 1.";
    if (!competencia) return "Escolha a competência.";
    return "";
  })();
  const pronto = !falta;
  const chave = JSON.stringify([competencia, pedido]);
  const atual = previa && previa.chave === chave ? previa.dados : null;
  const resultado = previa?.dados ?? null;
  const esmaecido = !atual;

  // ---------------------------------------------------------------------------------------------- a prévia, sozinha (item 7.2)
  useEffect(() => {
    if (!pronto) return;
    controle.current?.abort();
    const meu = new AbortController();
    controle.current = meu;
    const espera = setTimeout(() => {
      setCarregando(true); setErro("");
      const soOAgrupamento = !pedido.criterios.filtros.length && !pedido.criterios.distancia && !!agruparDepois;
      const opcoes: CriteriosOpcoes = { competencia, categoria: p.categoria, criterios: pedido.criterios,
        ...(soOAgrupamento ? { agrupar: agruparDepois } : {}),
        ...(pedido.base ? { base: { municipios: pedido.base } } : {}), ...(p.premissas && Object.keys(p.premissas).length ? { premissas: p.premissas } : {}),
        ...(p.fonte.tipo === "arquivo" ? { rotulos: p.rotulos } : {}) };
      pedirCriterios(p.fonte, opcoes, meu.signal)
        .then(dados => { if (controle.current === meu) setPrevia({ chave, dados }); })
        .catch(falha => {
          if (controle.current === meu && !(falha instanceof DOMException && falha.name === "AbortError"))
            setErro(falha instanceof Error ? falha.message : "Não foi possível calcular a prévia.");
        })
        .finally(() => { if (controle.current === meu) setCarregando(false); });
    }, ESPERA_DA_PREVIA);
    return () => { clearTimeout(espera); meu.abort(); };
  }, [chave, pronto]);

  // ---------------------------------------------------------------------------------------------- o que sai e o que fica de fora
  // Junto com a seleção atual (comando V22, seção 4): os municípios de um estado como unidade e os membros de um conjunto da seleção
  // não entram; no lugar dela, o que sai é dito antes de usar.
  const foraJunto = useMemo(() => {
    if (!atual || !junto || !p.naSelecao) return { doEstado: 0, doConjunto: 0 };
    const estados = new Set(p.naSelecao.estados), membros = new Set(p.naSelecao.membrosDeConjuntos);
    let doEstado = 0, doConjunto = 0;
    for (const id of atual.ids) {
      if (estados.has(p.naSelecao.grupoDe(id))) doEstado += 1;
      else if (membros.has(id)) doConjunto += 1;
    }
    return { doEstado, doConjunto };
  }, [atual, junto, p.naSelecao]);
  const textoDoUso = (() => {
    if (!p.algoNaAnalise || !p.naSelecao) return "";
    if (!junto) {
      const saem = [p.naSelecao.estados.length ? quantos(p.naSelecao.estados.length, grupoRotulo) + " como unidade" : "",
        p.naSelecao.conjuntos ? quantos(p.naSelecao.conjuntos, { singular: "conjunto", plural: "conjuntos" }) : ""].filter(Boolean);
      return saem.length ? "No lugar da seleção atual, saem também " + saem.join(" e ") + "." : "";
    }
    const partes = [foraJunto.doEstado ? quantos(foraJunto.doEstado, unidade) + " de " + (grupoF ? "uma " : "um ") + grupoRotulo.singular +
      " que já está como unidade" : "", foraJunto.doConjunto ? quantos(foraJunto.doConjunto, unidade) + " que já " +
      (foraJunto.doConjunto === 1 ? "está" : "estão") + " num conjunto da seleção" : ""].filter(Boolean);
    return partes.length ? "Ficam de fora " + partes.join(" e ") + ": não são somad" + (feminino ? "as" : "os") + " duas vezes." : "";
  })();

  // ---------------------------------------------------------------------------------------------- o mini mapa (itens 7.1 a 7.4)
  const fundo = useMemo(() => {
    const doGrupo = (ids: string[]) => validas.filter(item => ids.includes(grupoDaUnidade(item))).map(item => item.id);
    if (onde === "regioes") return doGrupo(gruposDasRegioes(regioesEscolhidas));
    if (onde === "estados") return doGrupo(estadosEscolhidos);
    if (onde === "marcados") return p.marcados.vendoPorGrupo && !baseDaRegra ? doGrupo(p.marcados.grupos)
      : marcadosBase ? validas.filter(item => unidadeMarcada(marcadosBase, item.id, grupoDaUnidade(item))).map(item => item.id) : [];
    return validas.map(item => item.id);
  }, [onde, regioesEscolhidas, estadosEscolhidos, p.marcados, marcadosBase, validas, p.grupos]);
  const coordenadas = useMemo(() => {
    if (p.coordenadas?.size) return p.coordenadas;
    return new Map((resultado?.pontos ?? []).map(ponto => [ponto.id, [ponto.lat, ponto.lon] as [number, number]]));
  }, [p.coordenadas, resultado]);
  const resumo = resultado ? resultado.atendem.toLocaleString("pt-BR") + " atende" + (resultado.atendem === 1 ? "" : "m") : "";

  const usar = () => {
    if (!atual) return;
    p.onUsar(atual, { ...pedido, agrupar: agruparDepois }, { conjuntos: false, junto, levarSemConjunto: false, nomes: {} });
  };
  const caixaDeGrupo = (grupo: GrupoInfo, escolhidos: string[], definir: (ids: string[]) => void, testid: string) =>
    <label key={grupo.id} className="analise-caixa"><input type="checkbox" data-testid={testid} data-id={grupo.id} checked={escolhidos.includes(grupo.id)}
      onChange={() => definir(escolhidos.includes(grupo.id) ? escolhidos.filter(id => id !== grupo.id) : [...escolhidos, grupo.id])}/>
      <span>{grupo.nome}{grupo.sigla ? " (" + grupo.sigla + ")" : ""}</span></label>;

  return <section data-testid="analise-criterios" aria-labelledby="analise-criterios-titulo" className="analise-agregar analise-criterios">
    <h4 id="analise-criterios-titulo" className="analise-agregar-titulo">Aplicar critérios de seleção</h4>
    <div className="analise-criterios-alto">
      <p data-testid="analise-criterios-resumo" className="analise-criterios-resumo" aria-live="polite">{resumo || "A prévia aparece aqui."}</p>
      <MapaDosConjuntos coordenadas={coordenadas} fundo={fundo} destaque={resultado?.ids ?? []} conjuntos={[]}
        nomeDe={nomeDe} esmaecido={esmaecido && !!resultado} rotulo={"Mini mapa: " + (resumo || "onde procurar")}
        vazio="O mapa aparece com onde procurar escolhido." legenda="pontos cheios: atendem aos critérios"/>
    </div>
    {p.aviso && <p role="status" data-testid="analise-criterios-aviso" className="analise-agregar-apoio">{p.aviso}</p>}
    {agruparDepois && <p role="status" data-testid="analise-criterios-agrupar-depois" className="analise-agregar-apoio">O agrupamento por proximidade
      (a até {valorDe(agruparDepois.km)} km) fica em “Agrupar territórios selecionados”: ao usar como seleção, ele abre com essa distância.</p>}
    <ol className="analise-criterios-passos">
      <li><fieldset className="analise-criterios-bloco">
        <legend>1. Onde procurar</legend>
        <label className="analise-caixa"><input type="radio" name="analise-criterios-onde" data-testid="analise-criterios-onde-todo"
          checked={onde === "todo"} onChange={() => setOnde("todo")}/><span>{p.nomeDoTodo}</span></label>
        {p.regioes.length > 0 && <label className="analise-caixa"><input type="radio" name="analise-criterios-onde" data-testid="analise-criterios-onde-regioes"
          checked={onde === "regioes"} onChange={() => setOnde("regioes")}/><span>{maiuscula(superior.plural)}</span></label>}
        {onde === "regioes" && <div className="analise-criterios-escolhas" role="group" aria-label={maiuscula(superior.plural)}>
          {p.regioes.map(regiao => caixaDeGrupo(regiao, regioesEscolhidas, setRegioesEscolhidas, "analise-criterios-onde-regiao"))}</div>}
        {p.grupos.length > 0 && <label className="analise-caixa"><input type="radio" name="analise-criterios-onde" data-testid="analise-criterios-onde-estados"
          checked={onde === "estados"} onChange={() => setOnde("estados")}/><span>{maiuscula(grupoRotulo.plural)}</span></label>}
        {onde === "estados" && <div className="analise-criterios-escolhas analise-criterios-escolhas-longa" role="group" aria-label={maiuscula(grupoRotulo.plural)}>
          {p.grupos.map(grupo => caixaDeGrupo(grupo, estadosEscolhidos, setEstadosEscolhidos, "analise-criterios-onde-estado"))}</div>}
        <label className="analise-caixa"><input type="radio" name="analise-criterios-onde" data-testid="analise-criterios-onde-marcados"
          checked={onde === "marcados"} disabled={!quantosMarcados} onChange={() => setOnde("marcados")}/>
          <span>{baseDaRegra ? "A seleção em que a regra procurou" : "Os marcados na lista"} ({quantosMarcados.toLocaleString("pt-BR")})</span></label>
        {!quantosMarcados && <p className="analise-agregar-apoio" data-testid="analise-criterios-sem-marcados">Nenhum{feminino ? "a" : ""} {unidade.singular}
          {" "}marcad{feminino ? "a" : "o"} na lista à esquerda.</p>}
      </fieldset></li>
      <li><fieldset className="analise-criterios-bloco">
        <legend>2. Critérios (valem juntos)</legend>
        <label className="analise-rotulo-campo">Competência dos critérios
          <select data-testid="analise-criterios-competencia" value={competencia} onChange={event => setCompetencia(event.target.value)} className="analise-campo">
            {periodos.map(periodo => <option key={periodo} value={periodo}>{competenciaAbreviada(periodo)}</option>)}
          </select>
        </label>
        <ol className="space-y-2">
          {linhas.map((linha, indice) => <li key={indice} data-testid="analise-criterio" className="flex flex-wrap items-end gap-1.5">
            <label className="analise-rotulo-campo basis-full">Indicador
              <select data-testid="analise-criterio-atributo" value={linha.atributo} className="analise-campo"
                onChange={event => mudar(indice, { atributo: event.target.value as Rascunho["atributo"] })}>
                <option value="densidade">Densidade</option><option value="quantidade">Quantidade</option><option value="populacao">População</option>
              </select>
            </label>
            <label className="analise-rotulo-campo min-w-[7rem] flex-1">Comparação
              <select data-testid="analise-criterio-operador" value={linha.operador} className="analise-campo"
                onChange={event => mudar(indice, { operador: event.target.value as Rascunho["operador"] })}>
                {(Object.keys(OPERADORES) as Rascunho["operador"][]).map(op => <option key={op} value={op}>{SIMBOLOS[op]} {OPERADORES[op]}</option>)}
              </select>
            </label>
            <label className="analise-rotulo-campo min-w-[7rem] flex-1">Valor ({UNIDADE_DO_VALOR[linha.atributo]})
              <input data-testid="analise-criterio-valor" inputMode="decimal" value={linha.valor} className="analise-campo"
                aria-invalid={!!linha.valor.trim() && lerNumero(linha.valor) === null} onChange={event => mudar(indice, { valor: event.target.value })}/>
            </label>
            {linhas.length > 1 && <button type="button" className="analise-icone" aria-label={"Tirar o critério " + (indice + 1)}
              onClick={() => setLinhas(lista => lista.filter((_, i) => i !== indice))}><Trash2 size={14} aria-hidden="true"/></button>}
          </li>)}
        </ol>
        <button type="button" data-testid="analise-criterio-mais" className="analise-botao-secundario" disabled={linhas.length >= 5}
          onClick={() => setLinhas(lista => [...lista, { atributo: "densidade", operador: ">", valor: "" }])}><Plus size={14} aria-hidden="true"/>Critério</button>
        <label className="analise-caixa">
          <input type="checkbox" data-testid="analise-criterios-com-distancia" checked={comDistancia} onChange={event => setComDistancia(event.target.checked)}/>
          <span>Só {feminino ? "as" : "os"} que ficam a até uma distância de {feminino ? "uma" : "um"} {unidade.singular} (em linha reta)</span>
        </label>
        {comDistancia && <div className="analise-criterios-distancia">
          <label className="analise-rotulo-campo">Distância (km)
            <input data-testid="analise-criterios-distancia-km" inputMode="decimal" value={km} onChange={event => setKm(event.target.value)} className="analise-campo"/>
          </label>
          {de ? <p className="analise-etiqueta" data-testid="analise-criterios-distancia-de">{nomeDe(de)}
            <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Trocar " + nomeDe(de)} onClick={() => setDe(null)}>
              <X size={13} aria-hidden="true"/></button></p>
            : <div className="analise-busca">
              <label className="sr-only" htmlFor="analise-criterios-busca">Buscar {unidade.singular} da distância</label>
              <Search size={16} aria-hidden="true" className="analise-busca-icone"/>
              <input id="analise-criterios-busca" type="search" data-testid="analise-criterios-busca" value={consulta} autoComplete="off"
                placeholder={"Buscar " + unidade.singular} onChange={event => setConsulta(event.target.value)} className="analise-campo analise-busca-campo"/>
            </div>}
          {!de && resultados.length > 0 && <ul className="analise-agregar-resultados" aria-label="Resultados da busca">
            {resultados.map(item => <li key={item.id}><button type="button" data-testid="analise-criterios-resultado" data-id={item.id}
              className="analise-botao-secundario" onClick={() => { setDe(item.id); setConsulta(""); }}>{nomeDaUnidade(item)}</button></li>)}
          </ul>}
        </div>}
      </fieldset></li>
    </ol>
    <div data-testid="analise-criterios-rodape" className="analise-criterios-rodape">
      <p data-testid="analise-criterios-estado" role="status" className={"analise-criterios-estado" + (erro ? " analise-faixa-erro" : "")}>
        {erro || falta || (carregando || esmaecido ? "Calculando a prévia…" : resultado ? quantos(resultado.atendem, unidade) + " atende" +
          (resultado.atendem === 1 ? "" : "m") + " aos critérios (" + resultado.regra.texto +
          " em " + competenciaAbreviada(resultado.competencia) + ")" + (resultado.naoAvaliaveis ? "; " + quantos(resultado.naoAvaliaveis, unidade) +
          " sem o dado para avaliar" : "") + "." : "")}</p>
      {p.algoNaAnalise && <div role="radiogroup" aria-label="O resultado na análise" className="analise-criterios-uso">
        <label className="analise-caixa"><input type="radio" name="analise-criterios-uso" data-testid="analise-criterios-no-lugar" checked={!junto}
          onChange={() => setJunto(false)}/><span>No lugar da seleção atual</span></label>
        <label className="analise-caixa"><input type="radio" name="analise-criterios-uso" data-testid="analise-criterios-junto" checked={junto}
          onChange={() => setJunto(true)}/><span>Junto com a seleção atual</span></label>
      </div>}
      {textoDoUso && <p data-testid="analise-criterios-uso-texto" role="status" className="analise-agregar-apoio">{textoDoUso}</p>}
      <div className="analise-agregar-acoes">
        <button type="button" data-testid="analise-criterios-como-selecao" className="analise-botao-primario" disabled={!atual || !atual.atendem}
          onClick={usar}>Usar como seleção ({(atual?.atendem ?? 0).toLocaleString("pt-BR")})</button>
        <button type="button" data-testid="analise-criterios-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
      </div>
      {resultado && resultado.notas.length > 0 && <details className="analise-criterios-notas"><summary>Notas do motor</summary>
        <ul>{resultado.notas.map(nota => <li key={nota}>{nota}</li>)}</ul></details>}
    </div>
  </section>;
}
