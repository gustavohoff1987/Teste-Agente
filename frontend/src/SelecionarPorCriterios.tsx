import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, Search, Trash2, X } from "lucide-react";
import {
  pedirCriterios, type CriteriosOpcoes, type FiltroDoCriterio, type FonteDoMotor, type PainelMunicipios, type Premissas, type RespostaCriterios,
  type RotulosTerritoriais,
} from "./painelApi";
import {
  OPERADORES, SIMBOLOS, competenciaAbreviada, formatarNumero, maiuscula, nomeDaUnidade, quantos, type UnidadeDoCatalogo,
} from "./painelModel";

// Selecionar por critérios (07/11/2026, item 6 do comando de 06/11/2026; decisão 4 do responsável), na Seleção de Territórios: a
// pessoa diz onde procurar (o todo, o lugar em uso ou a seleção atual), a competência, os critérios (indicador, comparação e valor,
// vários valendo juntos: o mesmo construtor das Condições, CAP-SUB-01), a distância opcional "a até X km de {território}" e, se
// quiser, "Agrupar os que ficam a até X km uns dos outros" (grupos por proximidade, em cadeia, RQ-CAP-13). O sistema não sugere nem
// preenche valores. A prévia é toda do motor (POST /api/painel/criterios): quantos atendem, os grupos e os isolados, cada grupo com
// as unidades, os estados e a extensão de ponta a ponta, e um mapa pequeno. Só "Como seleção" ou "Cada grupo como território
// agregado" muda a análise.

type Onde = "todo" | "lugar" | "selecao";
type Rascunho = { atributo: FiltroDoCriterio["indicador"]; operador: FiltroDoCriterio["operador"]; valor: string };
/** O que a pessoa pediu: os critérios, o agrupamento e, com "a seleção atual", a seleção em que procurou (para reaplicar nela,
 * mesmo depois de a seleção virar a do resultado). */
export type PedidoDosCriterios = { criterios: CriteriosOpcoes["criterios"]; agrupar: { km: number } | null; base?: PainelMunicipios };
type Props = {
  fonte: FonteDoMotor;
  rotulos: RotulosTerritoriais;
  nomeDoTodo: string;
  unidades: UnidadeDoCatalogo[];
  competencia: string;
  periodos: string[];
  categoria: string;
  premissas?: Premissas;
  /** A seleção em uso (para "a seleção atual"); sem nada marcado, null. */
  base: PainelMunicipios | null;
  /** O lugar em uso na trilha (um grupo ou um grupo de cima), como onde procurar; sem ele, null. */
  lugar: { rotulo: string; partirDe: CriteriosOpcoes["criterios"]["partir_de"] } | null;
  /** Onde a regra a reaplicar procurou (um grupo ou mais, pelo nome), quando não é o lugar em uso: no lugar dele. */
  lugarDoPedido?: { rotulo: string; partirDe: CriteriosOpcoes["criterios"]["partir_de"] } | null;
  /** A regra a reaplicar (outra competência) ou o pedido da conversa, já preenchidos. */
  inicial?: PedidoDosCriterios | null;
  /** Aberto pela conversa (07/11/2026, item 6.9): a prévia sai sozinha, uma vez, com o que a pessoa disse. */
  previaAoAbrir?: boolean;
  onComoSelecao: (previa: RespostaCriterios, pedido: PedidoDosCriterios) => void;
  onComoGrupos: (previa: RespostaCriterios, pedido: PedidoDosCriterios) => void;
  onCancelar: () => void;
};

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const lerNumero = (texto: string) => {
  const valor = Number(texto.trim().replace(/\./g, "").replace(",", "."));
  return texto.trim() && Number.isFinite(valor) ? valor : null;
};
const UNIDADE_DO_VALOR: Record<Rascunho["atributo"], string> = { densidade: "por 1.000 habitantes", quantidade: "profissionais", populacao: "habitantes" };
const CORES = ["#0f766e", "#b45309", "#7c3aed", "#be123c", "#1d4ed8", "#4d7c0f", "#a21caf", "#0e7490"];
const valorDe = (numero: number) => String(numero).replace(".", ",");

export default function SelecionarPorCriterios(p: Props) {
  const unidade = p.rotulos.unidade, feminino = (unidade.genero ?? "m") === "f";
  const inicial = p.inicial?.criterios;
  // Onde procurar: o lugar da regra a reaplicar, quando ela procurou noutro lugar; a seleção em que ela procurou, quando foi na
  // seleção (a seleção em uso pode já ser a do resultado).
  const lugarOpcao = p.lugarDoPedido ?? p.lugar;
  const baseDaRegra = p.inicial?.base ?? null;
  const baseDaBusca = baseDaRegra ?? p.base;
  const [onde, setOnde] = useState<Onde>(() => inicial?.partir_de.tipo === "selecao" && baseDaBusca ? "selecao"
    : inicial && inicial.partir_de.tipo !== "pais" && inicial.partir_de.tipo !== "selecao" && lugarOpcao ? "lugar" : "todo");
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
  const controle = useRef<AbortController | null>(null);
  const porId = useMemo(() => new Map(p.unidades.map(item => [item.id, item])), [p.unidades]);
  const termo = sem(consulta.trim());
  const resultados = useMemo(() => termo.length < 2 ? [] : p.unidades.filter(item => !item.selection_reason &&
    sem(nomeDaUnidade(item)).includes(termo)).slice(0, 8), [p.unidades, termo]);
  const mudar = (indice: number, parte: Partial<Rascunho>) => setLinhas(atual => atual.map((linha, i) => i === indice ? { ...linha, ...parte } : linha));

  // O pedido só sai com tudo dito pela pessoa: cada critério com o valor; a distância com o território e os km; o agrupamento com os km.
  const filtros = linhas.filter(linha => linha.valor.trim()).map(linha => ({ indicador: linha.atributo, operador: linha.operador,
    valor: lerNumero(linha.valor) }));
  const filtrosValidos = filtros.every(filtro => filtro.valor !== null);
  const kmDistancia = lerNumero(km), kmDoAgrupamento = lerNumero(kmAgrupar);
  const distancia = comDistancia && de && kmDistancia !== null && kmDistancia > 0 ? { de, km: kmDistancia } : null;
  const partirDe: CriteriosOpcoes["criterios"]["partir_de"] = onde === "selecao" ? { tipo: "selecao" }
    : onde === "lugar" && lugarOpcao ? lugarOpcao.partirDe : { tipo: "pais" };
  const pedido: PedidoDosCriterios = { criterios: { partir_de: partirDe, filtros: filtros.map(filtro => ({ ...filtro, valor: filtro.valor as number })),
    ...(distancia ? { distancia } : {}) }, agrupar: agrupar && kmDoAgrupamento !== null && kmDoAgrupamento > 0 ? { km: kmDoAgrupamento } : null,
    ...(onde === "selecao" && baseDaBusca ? { base: baseDaBusca } : {}) };
  const pronto = filtrosValidos && (filtros.length > 0 || !!distancia) && (!comDistancia || !!distancia) &&
    (!agrupar || !!pedido.agrupar) && (onde !== "selecao" || !!baseDaBusca) && !!competencia;
  const chave = JSON.stringify([competencia, pedido]);
  const atual = previa && previa.chave === chave ? previa.dados : null;

  async function verPrevia() {
    if (!pronto) return;
    controle.current?.abort();
    const meu = new AbortController();
    controle.current = meu;
    setCarregando(true); setErro("");
    const opcoes: CriteriosOpcoes = { competencia, categoria: p.categoria, criterios: pedido.criterios, ...(pedido.agrupar ? { agrupar: pedido.agrupar } : {}),
      ...(onde === "selecao" && baseDaBusca ? { base: { municipios: baseDaBusca } } : {}), ...(p.premissas && Object.keys(p.premissas).length ? { premissas: p.premissas } : {}),
      ...(p.fonte.tipo === "arquivo" ? { rotulos: p.rotulos } : {}) };
    try {
      const dados = await pedirCriterios(p.fonte, opcoes, meu.signal);
      if (controle.current === meu) setPrevia({ chave, dados });
    } catch (falha) {
      if (controle.current === meu && !(falha instanceof DOMException && falha.name === "AbortError"))
        setErro(falha instanceof Error ? falha.message : "Não foi possível calcular a prévia.");
    } finally {
      if (controle.current === meu) setCarregando(false);
    }
  }

  // Aberto pela conversa: a prévia do pedido, uma vez, ao abrir (o painel abre de novo a cada pedido).
  useEffect(() => { if (p.previaAoAbrir && pronto) void verPrevia(); }, []);

  // O mapa pequeno: os pontos do motor numa projeção simples (só para desenhar), coloridos pelo grupo; os isolados, vazados.
  const mapa = useMemo(() => {
    const pontos = atual?.pontos ?? [];
    if (!pontos.length) return null;
    const lats = pontos.map(ponto => ponto.lat), lons = pontos.map(ponto => ponto.lon);
    const [minLat, maxLat, minLon, maxLon] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
    const largura = 220, altura = 150, margem = 8;
    const escala = Math.min((largura - 2 * margem) / Math.max(maxLon - minLon, 1e-6), (altura - 2 * margem) / Math.max(maxLat - minLat, 1e-6));
    const indice = new Map((atual?.grupos ?? []).map((grupo, i) => [grupo.id, i]));
    return { largura, altura, pontos: pontos.map(ponto => ({ ...ponto, x: margem + (ponto.lon - minLon) * escala, y: altura - margem - (ponto.lat - minLat) * escala,
      cor: ponto.grupo ? CORES[(indice.get(ponto.grupo) ?? 0) % CORES.length] : null })) };
  }, [atual]);
  const nomeDe = (id: string) => { const item = porId.get(id); return item ? nomeDaUnidade(item) : id; };
  const grupos = atual?.grupos ?? null, isolados = atual?.isolados ?? [];

  return <section data-testid="analise-criterios" aria-labelledby="analise-criterios-titulo" className="analise-agregar analise-criterios">
    <h4 id="analise-criterios-titulo" className="analise-agregar-titulo">Selecionar por critérios</h4>
    <p className="analise-agregar-apoio">Você diz os critérios, os valores e a distância; nada é sugerido. A prévia mostra quantos atendem
      antes de mudar a análise.</p>
    <fieldset className="analise-criterios-bloco">
      <legend>Onde procurar</legend>
      <label className="analise-caixa"><input type="radio" name="analise-criterios-onde" data-testid="analise-criterios-onde-todo"
        checked={onde === "todo"} onChange={() => setOnde("todo")}/><span>{p.nomeDoTodo}</span></label>
      {lugarOpcao && <label className="analise-caixa"><input type="radio" name="analise-criterios-onde" data-testid="analise-criterios-onde-lugar"
        checked={onde === "lugar"} onChange={() => setOnde("lugar")}/>
        <span>{p.lugarDoPedido ? p.lugarDoPedido.rotulo : "O lugar em uso: " + lugarOpcao.rotulo}</span></label>}
      {baseDaBusca && <label className="analise-caixa"><input type="radio" name="analise-criterios-onde" data-testid="analise-criterios-onde-selecao"
        checked={onde === "selecao"} onChange={() => setOnde("selecao")}/>
        <span>{baseDaRegra ? "A seleção em que a regra procurou" : "A seleção atual"}</span></label>}
    </fieldset>
    <label className="analise-rotulo-campo">Competência dos critérios
      <select data-testid="analise-criterios-competencia" value={competencia} onChange={event => setCompetencia(event.target.value)} className="analise-campo">
        {p.periodos.map(periodo => <option key={periodo} value={periodo}>{competenciaAbreviada(periodo)}</option>)}
      </select>
    </label>
    <fieldset className="analise-criterios-bloco">
      <legend>Critérios (valem juntos)</legend>
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
    </fieldset>
    <label className="analise-caixa">
      <input type="checkbox" data-testid="analise-criterios-agrupar" checked={agrupar} onChange={event => setAgrupar(event.target.checked)}/>
      <span>Agrupar {feminino ? "as" : "os"} que ficam a até</span>
      <input aria-label="Distância do agrupamento (km)" data-testid="analise-criterios-agrupar-km" inputMode="decimal" value={kmAgrupar}
        disabled={!agrupar} onChange={event => setKmAgrupar(event.target.value)} className="analise-campo analise-criterios-km"/>
      <span>km {feminino ? "umas das outras" : "uns dos outros"} (grupos por proximidade, em cadeia)</span>
    </label>
    <div className="analise-agregar-acoes">
      <button type="button" data-testid="analise-criterios-previa" className="analise-botao-primario" disabled={!pronto || carregando} onClick={verPrevia}>
        {carregando ? "Calculando a prévia…" : "Ver a prévia"}</button>
      <button type="button" data-testid="analise-criterios-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
    </div>
    {erro && <p role="alert" className="analise-faixa-erro">{erro}</p>}
    {atual && <div data-testid="analise-criterios-resultado-previa" className="analise-criterios-previa" aria-live="polite">
      <p data-testid="analise-criterios-atendem"><strong>{quantos(atual.atendem, unidade)}</strong> atende{atual.atendem === 1 ? "" : "m"} aos critérios
        ({atual.regra.texto} em {competenciaAbreviada(atual.competencia)}){atual.naoAvaliaveis ? "; " + quantos(atual.naoAvaliaveis, unidade) +
        " sem o dado para avaliar" : ""}.</p>
      {grupos && <p data-testid="analise-criterios-resumo">{quantos(grupos.length, { singular: "grupo", plural: "grupos" })} e {isolados.length}{" "}
        {isolados.length === 1 ? (feminino ? "isolada" : "isolado") : (feminino ? "isoladas" : "isolados")}.</p>}
      {grupos && grupos.length > 0 && <ol className="analise-criterios-grupos" aria-label="Grupos por proximidade">
        {grupos.map((grupo, i) => <li key={grupo.id} data-testid="analise-criterios-grupo" data-id={grupo.id}>
          <span className="analise-criterios-cor" style={{ background: CORES[i % CORES.length] }} aria-hidden="true"/>
          <strong>{grupo.rotulo}</strong> · {quantos(grupo.membros.length, unidade)} · {grupo.gruposTerritoriais.map(t => t.rotulo + " " + t.unidades).join(", ")}
          {" · "}{formatarNumero(Math.round(grupo.extensaoKm), true)} km de ponta a ponta</li>)}
      </ol>}
      {mapa && <svg data-testid="analise-criterios-mapa" viewBox={"0 0 " + mapa.largura + " " + mapa.altura} width={mapa.largura} height={mapa.altura}
        role="img" aria-label={"Mapa pequeno: " + quantos(mapa.pontos.length, unidade) + (grupos ? ", coloridos pelo grupo; os isolados, vazados" : "")}
        className="analise-criterios-mapinha">
        {mapa.pontos.map(ponto => <circle key={ponto.id} data-testid="analise-criterios-ponto" data-grupo={ponto.grupo ?? ""} cx={ponto.x} cy={ponto.y} r={3}
          fill={ponto.cor ?? "none"} stroke={ponto.cor ?? "currentColor"} strokeWidth={1.2}><title>{nomeDe(ponto.id)}</title></circle>)}
      </svg>}
      <div className="analise-agregar-acoes">
        <button type="button" data-testid="analise-criterios-como-selecao" className="analise-botao-primario" disabled={!atual.atendem}
          onClick={() => p.onComoSelecao(atual, pedido)}>Como seleção ({atual.atendem.toLocaleString("pt-BR")})</button>
        {grupos && grupos.length > 0 && <button type="button" data-testid="analise-criterios-como-grupos" className="analise-botao-secundario"
          onClick={() => p.onComoGrupos(atual, pedido)}>Cada grupo como território agregado</button>}
      </div>
      {atual.notas.length > 0 && <ul className="analise-criterios-notas">{atual.notas.map(nota => <li key={nota}>{nota}</li>)}</ul>}
    </div>}
  </section>;
}
