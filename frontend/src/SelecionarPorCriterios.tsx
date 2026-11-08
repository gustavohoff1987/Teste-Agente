import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, Search, Trash2, X } from "lucide-react";
import MapaDosConjuntos from "./MapaDosConjuntos";
import {
  pedirCriterios, type CriteriosOpcoes, type FiltroDoCriterio, type FonteDoMotor, type PainelMunicipios, type Premissas, type RespostaCriterios,
  type RotulosTerritoriais,
} from "./painelApi";
import {
  MAX_CONJUNTOS, OPERADORES, SIMBOLOS, artigo, competenciaAbreviada, formatarNumero, grupoDaUnidade, maiuscula, nomeDaUnidade, nomeRepetido,
  nomesLivresDeConjunto, quantos, unidadeMarcada, type GrupoInfo, type UnidadeDoCatalogo,
} from "./painelModel";

// "Por critérios" (07/11/2026, comando de 07/11/2026, itens 2, 4, 5, 7, 8 e 9.1; antes, o painel "Selecionar por critérios" do
// comando de 06/11/2026, decisão 4), um dos modos da Seleção de Territórios. Passos numerados, abaixo do mini mapa: 1. Onde procurar
// (o todo, regiões, estados ou os marcados na lista, sempre com os nomes da base); 2. Critérios (indicador, comparação e valor,
// valendo juntos, CAP-SUB-01, com a competência e a distância opcional "a até X km de"); 3. Agrupar por proximidade (opcional):
// os conjuntos todos a até X km entre si (RQ-CAP-13), com a distância dita pela pessoa; agrupando, os critérios de valor são
// opcionais. A prévia é toda do motor (POST /api/painel/criterios) e se atualiza sozinha a cada ajuste, com espera curta e o pedido
// anterior cancelado; o mini mapa, no alto, mostra o resultado e, enquanto falta algo, o último válido, esmaecido. O rodapé reúne a
// linha de estado e as saídas: "Usar como seleção (N)", "Usar cada conjunto como um território" (no lugar da seleção atual ou junto
// com ela; levando ou não os sem conjunto) e "Cancelar". Nada é sugerido; a tela não calcula.

type Onde = "todo" | "regioes" | "estados" | "marcados";
type Rascunho = { atributo: FiltroDoCriterio["indicador"]; operador: FiltroDoCriterio["operador"]; valor: string };
/** O que a pessoa pediu: os critérios, o agrupamento e, com os marcados, a seleção em que procurou (para reaplicar nela). */
export type PedidoDosCriterios = { criterios: CriteriosOpcoes["criterios"]; agrupar: { km: number } | null; base?: PainelMunicipios };
/** A escolha do rodapé, com os nomes finais dos conjuntos (item 8.3). */
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
  /** O lugar em uso na trilha (pré-escolhido): a região ou o estado dele. */
  lugar: { tipo: "regioes" | "estados"; ids: string[] } | null;
  /** A regra a reaplicar, o pedido da conversa ou o das Condições, já preenchidos. */
  inicial?: PedidoDosCriterios | null;
  aviso?: string;
  /** Coordenadas autorizadas para o mini mapa (do motor), só para desenhar. */
  coordenadas: Map<string, [number, number]> | null;
  /** Os conjuntos que já estão na análise (os nomes contam para as letras e para a unicidade) e se a análise tem algo. */
  conjuntosNaAnalise: { id: string; rotulo: string }[];
  algoNaAnalise: boolean;
  onUsar: (previa: RespostaCriterios, pedido: PedidoDosCriterios, uso: UsoDosCriterios) => void;
  /** Troca para "Marcar na lista" sem perder o rascunho. */
  onMarcarNaLista: () => void;
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
  const [onde, setOnde] = useState<Onde>(() => inicial?.partir_de.tipo === "selecao" ? "marcados"
    : inicial?.partir_de.tipo === "ufs" ? "estados" : inicial?.partir_de.tipo === "regioes" ? "regioes"
      : inicial ? "todo" : p.lugar?.tipo ?? "todo");
  const [regioesEscolhidas, setRegioesEscolhidas] = useState<string[]>(() => inicial?.partir_de.tipo === "regioes" ? inicial.partir_de.regioes ?? []
    : !inicial && p.lugar?.tipo === "regioes" ? p.lugar.ids : []);
  const [estadosEscolhidos, setEstadosEscolhidos] = useState<string[]>(() => inicial?.partir_de.tipo === "ufs" ? inicial.partir_de.ufs ?? []
    : !inicial && p.lugar?.tipo === "estados" ? p.lugar.ids : []);
  const [competencia, setCompetencia] = useState(p.competencia);
  const [linhas, setLinhas] = useState<Rascunho[]>(() => inicial?.filtros.length
    ? inicial.filtros.map(filtro => ({ atributo: filtro.indicador, operador: filtro.operador, valor: valorDe(filtro.valor) }))
    : [{ atributo: "densidade", operador: "<", valor: "" }]);
  const [comDistancia, setComDistancia] = useState(!!inicial?.distancia);
  const [de, setDe] = useState<string | null>(inicial?.distancia?.de ?? null);
  const [km, setKm] = useState(inicial?.distancia ? valorDe(inicial.distancia.km) : "");
  const [consulta, setConsulta] = useState("");
  const [agrupar, setAgrupar] = useState(!!p.inicial?.agrupar);
  const [kmAgrupar, setKmAgrupar] = useState(p.inicial?.agrupar ? valorDe(p.inicial.agrupar.km) : "");
  const [previa, setPrevia] = useState<{ chave: string; dados: RespostaCriterios } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [junto, setJunto] = useState(false);
  const [levarSemConjunto, setLevarSemConjunto] = useState(true);
  const [nomesEditados, setNomesEditados] = useState<Record<string, string>>({});
  const [listaAberta, setListaAberta] = useState(false);
  const controle = useRef<AbortController | null>(null);
  const porId = useMemo(() => new Map(p.unidades.map(item => [item.id, item])), [p.unidades]);
  const validas = useMemo(() => p.unidades.filter(item => !item.selection_reason), [p.unidades]);
  const termo = sem(consulta.trim());
  const resultados = useMemo(() => termo.length < 2 ? [] : validas.filter(item => sem(nomeDaUnidade(item)).includes(termo)).slice(0, 8),
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
  const kmDistancia = lerNumero(km), kmDoAgrupamento = lerNumero(kmAgrupar);
  const distancia = comDistancia && de && kmDistancia !== null && kmDistancia > 0 ? { de, km: kmDistancia } : null;
  const gruposDasRegioes = (ids: string[]) => p.grupos.filter(grupo => ids.includes(p.regiaoDoGrupo?.(grupo.id) ?? "")).map(grupo => grupo.id);
  // Uma região vira os grupos dela (como o lugar em uso já fazia); os marcados, vendo por grupo, os grupos marcados.
  const partirDe: CriteriosOpcoes["criterios"]["partir_de"] = onde === "regioes" ? { tipo: "ufs", ufs: gruposDasRegioes(regioesEscolhidas) }
    : onde === "estados" ? { tipo: "ufs", ufs: estadosEscolhidos }
      : onde === "marcados" ? (p.marcados.vendoPorGrupo && !baseDaRegra ? { tipo: "ufs", ufs: p.marcados.grupos } : { tipo: "selecao" })
        : { tipo: "pais" };
  const pedido: PedidoDosCriterios = { criterios: { partir_de: partirDe, filtros: filtros.filter(filtro => filtro.valor !== null)
    .map(filtro => ({ ...filtro, valor: filtro.valor as number })), ...(distancia ? { distancia } : {}) },
  agrupar: agrupar && kmDoAgrupamento !== null && kmDoAgrupamento > 0 ? { km: kmDoAgrupamento } : null,
  ...(partirDe.tipo === "selecao" && marcadosBase ? { base: marcadosBase } : {}) };
  // O que falta (item 7.4), na ordem dos passos.
  const falta = (() => {
    if (onde === "regioes" && !regioesEscolhidas.length) return "Escolha ao menos " + (superiorF ? "uma " : "um ") + superior.singular + ".";
    if (onde === "estados" && !estadosEscolhidos.length) return "Escolha ao menos " + (grupoF ? "uma " : "um ") + grupoRotulo.singular + ".";
    if (onde === "marcados" && !quantosMarcados) return "Marque " + unidade.plural + " na lista para procurar entre " + (feminino ? "elas." : "eles.");
    const invalido = linhas.findIndex(linha => linha.valor.trim() && lerNumero(linha.valor) === null);
    if (invalido >= 0) return "Falta o valor do critério " + (invalido + 1) + ".";
    if (comDistancia && !de) return "Falta " + (feminino ? "a " : "o ") + unidade.singular + " da distância.";
    if (comDistancia && !distancia) return "Falta a distância dos critérios, em km.";
    if (agrupar && !pedido.agrupar) return "Falta a distância do agrupamento.";
    if (!pedido.criterios.filtros.length && !distancia && !agrupar) return "Falta o valor do critério 1.";
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
      const opcoes: CriteriosOpcoes = { competencia, categoria: p.categoria, criterios: pedido.criterios, ...(pedido.agrupar ? { agrupar: pedido.agrupar } : {}),
        ...(pedido.base ? { base: { municipios: pedido.base } } : {}), ...(p.premissas && Object.keys(p.premissas).length ? { premissas: p.premissas } : {}),
        ...(p.fonte.tipo === "arquivo" ? { rotulos: p.rotulos } : {}) };
      pedirCriterios(p.fonte, opcoes, meu.signal)
        .then(dados => { if (controle.current === meu) { setPrevia({ chave, dados }); setNomesEditados({}); } })
        .catch(falha => {
          if (controle.current === meu && !(falha instanceof DOMException && falha.name === "AbortError"))
            setErro(falha instanceof Error ? falha.message : "Não foi possível calcular a prévia.");
        })
        .finally(() => { if (controle.current === meu) setCarregando(false); });
    }, ESPERA_DA_PREVIA);
    return () => { clearTimeout(espera); meu.abort(); };
  }, [chave, pronto]);

  // ---------------------------------------------------------------------------------------------- os conjuntos e os nomes
  const grupos = resultado?.grupos ?? null, isolados = resultado?.isolados ?? [], semPosicao = resultado?.semPosicao ?? [];
  const semConjunto = [...isolados, ...semPosicao];
  const existentes = p.conjuntosNaAnalise.map(conjunto => conjunto.rotulo);
  // As letras seguem a escolha do rodapé (item 8.2): no lugar da seleção atual, recomeçam em A; junto com ela, continuam da próxima
  // livre entre os conjuntos da análise.
  const sugeridos = useMemo(() => grupos ? (junto ? nomesLivresDeConjunto(existentes, grupos.length) : grupos.map(grupo => grupo.rotulo)) : [],
    [grupos, junto, existentes.join("|")]);
  const nomeFinal = (id: string, i: number) => (nomesEditados[id] ?? sugeridos[i] ?? "").trim();
  const nomesFinais = (grupos ?? []).map((grupo, i) => nomeFinal(grupo.id, i));
  const problemaDoNome = (i: number) => {
    const nome = nomesFinais[i];
    if (!nome) return "Dê um nome ao conjunto.";
    if (nomeRepetido(nome, [...nomesFinais.filter((_, j) => j !== i), ...(junto ? existentes : [])])) return "Já existe um conjunto com esse nome.";
    return "";
  };
  const nomesComProblema = (grupos ?? []).some((_, i) => !!problemaDoNome(i));
  const total = (grupos?.length ?? 0) + (junto ? p.conjuntosNaAnalise.length : 0);
  const acimaDoLimite = !!grupos && grupos.length > 0 && total > MAX_CONJUNTOS;
  const motivoDoLimite = acimaDoLimite ? "São " + grupos!.length + " conjuntos" + (junto && p.conjuntosNaAnalise.length ? ", mais os " +
    p.conjuntosNaAnalise.length + " que já estão na análise," : "") + " e a análise aceita até " + MAX_CONJUNTOS + ": refine os critérios ou " +
    "diminua a distância." : "";

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
  const conjuntosNoMapa = (grupos ?? []).map((grupo, i) => ({ id: grupo.id, nome: nomesFinais[i] || grupo.rotulo, membros: grupo.membros }));
  const resumo = resultado ? resultado.atendem.toLocaleString("pt-BR") + " atende" + (resultado.atendem === 1 ? "" : "m") +
    (grupos ? " · " + quantos(grupos.length, { singular: "conjunto", plural: "conjuntos" }) +
      (grupos.length ? " · o maior com " + formatarNumero(Math.round(grupos[0].extensaoKm), true) + " km" : "") +
      " · " + semConjunto.length + " sem conjunto" : "") : "";

  const usar = (conjuntos: boolean) => {
    if (!atual) return;
    p.onUsar(atual, pedido, { conjuntos, junto, levarSemConjunto, nomes: Object.fromEntries((grupos ?? []).map((grupo, i) => [grupo.id, nomesFinais[i]])) });
  };
  const caixaDeGrupo = (grupo: GrupoInfo, escolhidos: string[], definir: (ids: string[]) => void, testid: string) =>
    <label key={grupo.id} className="analise-caixa"><input type="checkbox" data-testid={testid} data-id={grupo.id} checked={escolhidos.includes(grupo.id)}
      onChange={() => definir(escolhidos.includes(grupo.id) ? escolhidos.filter(id => id !== grupo.id) : [...escolhidos, grupo.id])}/>
      <span>{grupo.nome}{grupo.sigla ? " (" + grupo.sigla + ")" : ""}</span></label>;

  return <section data-testid="analise-criterios" aria-labelledby="analise-criterios-titulo" className="analise-agregar analise-criterios">
    <h4 id="analise-criterios-titulo" className="sr-only">Por critérios</h4>
    <div className="analise-criterios-alto">
      <p data-testid="analise-criterios-resumo" className="analise-criterios-resumo" aria-live="polite">{resumo || "A prévia aparece aqui."}</p>
      <MapaDosConjuntos coordenadas={coordenadas} fundo={fundo} destaque={grupos ? [] : resultado?.ids ?? []} conjuntos={conjuntosNoMapa}
        semConjunto={grupos ? semConjunto.filter(id => !semPosicao.includes(id)) : []} nomeDe={nomeDe} escalaKm={agrupar ? kmDoAgrupamento : null}
        esmaecido={esmaecido && !!resultado} rotulo={"Mini mapa: " + (resumo || "onde procurar")}
        vazio="O mapa aparece com onde procurar escolhido."/>
    </div>
    {grupos && grupos.length > 0 && <div className="analise-criterios-lista">
      <button type="button" data-testid="analise-criterios-ver-conjuntos" className="analise-link" aria-expanded={listaAberta}
        onClick={() => setListaAberta(atual => !atual)}>{listaAberta ? "Fechar a lista dos conjuntos" : "Ver os " + grupos.length + " conjuntos"}</button>
      {listaAberta && <ol className="analise-criterios-grupos" aria-label="Conjuntos por proximidade">
        {grupos.map((grupo, i) => <li key={grupo.id} data-testid="analise-criterios-grupo" data-id={grupo.id}>
          <label className="analise-rotulo-campo">Nome do conjunto
            <input data-testid="analise-criterios-grupo-nome" value={nomesEditados[grupo.id] ?? sugeridos[i] ?? ""} maxLength={60} className="analise-campo"
              aria-invalid={!!problemaDoNome(i)} onChange={event => setNomesEditados(atual => ({ ...atual, [grupo.id]: event.target.value }))}/>
          </label>
          {problemaDoNome(i) && <p role="alert" className="analise-faixa-erro">{problemaDoNome(i)}</p>}
          <p className="analise-agregar-apoio">{quantos(grupo.membros.length, unidade)} · {formatarNumero(Math.round(grupo.extensaoKm), true)} km de
            ponta a ponta: {grupo.membros.map(nomeDe).join(", ")}</p>
        </li>)}
      </ol>}
    </div>}
    {p.aviso && <p role="status" data-testid="analise-criterios-aviso" className="analise-agregar-apoio">{p.aviso}</p>}
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
        {!quantosMarcados && <button type="button" data-testid="analise-criterios-ir-lista" className="analise-botao-secundario"
          onClick={p.onMarcarNaLista}>Marcar na lista</button>}
      </fieldset></li>
      <li><fieldset className="analise-criterios-bloco">
        <legend>2. Critérios{agrupar ? " (opcionais ao agrupar)" : " (valem juntos)"}</legend>
        <label className="analise-rotulo-campo">Competência dos critérios
          <select data-testid="analise-criterios-competencia" value={competencia} onChange={event => setCompetencia(event.target.value)} className="analise-campo">
            {p.periodos.map(periodo => <option key={periodo} value={periodo}>{competenciaAbreviada(periodo)}</option>)}
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
      <li><fieldset className="analise-criterios-bloco">
        <legend>3. Agrupar por proximidade (opcional)</legend>
        <label className="analise-caixa"><input type="radio" name="analise-criterios-agrupar" data-testid="analise-criterios-nao-agrupar"
          checked={!agrupar} onChange={() => setAgrupar(false)}/><span>Não agrupar</span></label>
        <label className="analise-caixa"><input type="radio" name="analise-criterios-agrupar" data-testid="analise-criterios-agrupar"
          checked={agrupar} onChange={() => setAgrupar(true)}/><span>Agrupar {feminino ? "as" : "os"} que ficam perto {feminino ? "umas das outras" : "uns dos outros"}</span></label>
        {agrupar && <div className="analise-criterios-distancia">
          <label className="analise-rotulo-campo" htmlFor="analise-criterios-agrupar-km">Distância máxima entre os membros do conjunto (km)</label>
          <input id="analise-criterios-agrupar-km" data-testid="analise-criterios-agrupar-km" inputMode="decimal" value={kmAgrupar}
            onChange={event => setKmAgrupar(event.target.value)} className="analise-campo"/>
          <p className="analise-agregar-apoio">Todos os territórios de um conjunto ficam a até essa distância uns dos outros.</p>
        </div>}
      </fieldset></li>
    </ol>
    <div data-testid="analise-criterios-rodape" className="analise-criterios-rodape">
      <p data-testid="analise-criterios-estado" role="status" className={"analise-criterios-estado" + (erro ? " analise-faixa-erro" : "")}>
        {erro || falta || (carregando || esmaecido ? "Calculando a prévia…" : resultado ? quantos(resultado.atendem, unidade) + " atende" +
          (resultado.atendem === 1 ? "" : "m") + " aos critérios (" + (grupos ? resultado.regra.textoAgrupado ?? resultado.regra.texto : resultado.regra.texto) +
          " em " + competenciaAbreviada(resultado.competencia) + ")" + (resultado.naoAvaliaveis ? "; " + quantos(resultado.naoAvaliaveis, unidade) +
          " sem o dado para avaliar" : "") + "." : "")}{motivoDoLimite ? " " + motivoDoLimite : ""}</p>
      {p.algoNaAnalise && <div role="radiogroup" aria-label="O resultado na análise" className="analise-criterios-uso">
        <label className="analise-caixa"><input type="radio" name="analise-criterios-uso" data-testid="analise-criterios-no-lugar" checked={!junto}
          onChange={() => setJunto(false)}/><span>No lugar da seleção atual</span></label>
        <label className="analise-caixa"><input type="radio" name="analise-criterios-uso" data-testid="analise-criterios-junto" checked={junto}
          onChange={() => setJunto(true)}/><span>Junto com a seleção atual</span></label>
      </div>}
      {grupos && grupos.length > 0 && <label className="analise-caixa">
        <input type="checkbox" data-testid="analise-criterios-sem-conjunto" checked={levarSemConjunto} onChange={event => setLevarSemConjunto(event.target.checked)}/>
        <span>Levar também {feminino ? "as" : "os"} {semConjunto.length} sem conjunto</span></label>}
      <div className="analise-agregar-acoes">
        <button type="button" data-testid="analise-criterios-como-selecao" className="analise-botao-primario" disabled={!atual || !atual.atendem}
          onClick={() => usar(false)}>Usar como seleção ({(atual?.atendem ?? 0).toLocaleString("pt-BR")})</button>
        {grupos && grupos.length > 0 && <button type="button" data-testid="analise-criterios-como-grupos" className="analise-botao-secundario"
          disabled={!atual || acimaDoLimite || nomesComProblema} title={motivoDoLimite || (nomesComProblema ? "Confira os nomes dos conjuntos." : undefined)}
          onClick={() => usar(true)}>Usar cada conjunto como um território</button>}
        <button type="button" data-testid="analise-criterios-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
      </div>
      {resultado && resultado.notas.length > 0 && <details className="analise-criterios-notas"><summary>Notas do motor</summary>
        <ul>{resultado.notas.map(nota => <li key={nota}>{nota}</li>)}</ul></details>}
    </div>
  </section>;
}
