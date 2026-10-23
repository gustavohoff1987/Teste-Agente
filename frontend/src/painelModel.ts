// Área de análise da página única (22/10/2026): modelo puro de desenho e de estado. Só posiciona, filtra (estado visual),
// formata e monta textos e pedidos a partir do que o motor entregou em /api/painel (normalizado em painelApi.ts). Valores,
// variações, distâncias, domínios, grupos, faixas, classes de tendência, posições, condições, comparações e percentuais da
// rotatividade vêm da resposta: nada aqui soma, conta, calcula média, classifica ou cria posição. A ordem padrão é a do código
// territorial (RQ-REP-03); reordenar a tabela é estado visual pedido pela pessoa, sem posições. Nenhum texto fixa "município"
// ou "estado": a nomenclatura territorial vem dos rótulos da fonte ou do motor. Sem importações de outros módulos em tempo de
// execução (testes em Node): só tipos.
import type {
  AtributoCondicao, AtributoOrdenacao, CondicaoPedido, FamiliaTendencia, OperadorCondicao, OrdenarPedido, PainelAtributo,
  PainelConjuntoPedido, PainelCriterio, PainelDominio, PainelIndicador, PainelItem, PainelMunicipios, PainelNivel, PainelOpcoes, PainelOrdem,
  PainelReferenciaPedido, PainelResposta, Posicao, Premissas, ReferenciaCandidato, Rotulo, RotulosTerritoriais, SituacaoCondicao,
  TipoGrupos,
} from "./painelApi";
import type { EscolhaDePintura, PinturaDoMapa, TamanhoDoMapa, VistaDesenho } from "./mapaContrato";

export type { Rotulo, RotulosTerritoriais } from "./painelApi";

const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
const limpo = (valor: number) => Number(valor.toPrecision(12));  // sem resíduo binário (0,30000000000000004)
const ehNumero = (valor: number | null): valor is number => valor !== null;
export const numero = (valor: unknown): number | null => typeof valor === "number" && Number.isFinite(valor) ? valor : null;
const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

// ================================================================================================ tipos da área (props)
export type Familia = "distribuicao" | "espacial" | "tendencia" | "rotatividade";
export type Visao = "mudanca" | "classes" | "series";
/** Fonte de dados da área: a base do Brasil ou a planilha enviada, com a nomenclatura territorial confirmada. */
export type FonteDados = {
  tipo: "brasil" | "arquivo"; apiBase: string; datasetVersion: string; sheet: string; mapping: Record<string, string>;
  arquivo: File | null; nome: string; geoVersion?: string; premissas?: Premissas; rotulos?: RotulosTerritoriais;
};
/** Comando da conversa para o gráfico (campo `painel` das rotas da conversa). Cada id novo é aplicado uma vez. */
export type PedidoDoChat = {
  familia?: Familia | null; indicador?: PainelIndicador | null; nivel?: PainelNivel | null;
  municipios?: PainelMunicipios | null; competencia?: string | null; janela?: string[] | null;
  visaoTendencia?: Visao | null; referencia?: { membros: string[]; criterio?: object } | null;
  funcao?: "comparar" | "juntar" | "condicoes" | "ordenar" | "exportar" | null; selecao?: string[] | null;
  ordenar?: object | null; condicoes?: object[] | null;
  /** Grupos por posição da distribuição (quartis, quintis, decis) ou "nenhum" para tirá-los. */
  grupos?: { tipo: string } | null;
  /** Vista do desenho pedida na conversa ("ver no mapa", "volte ao gráfico"): estado visual, não recalcula. */
  vista?: "grafico" | "mapa" | null;
};
/** O que está na tela, para a estrutura da página e a conversa. */
export type ContextoDoGrafico = {
  familia: Familia; indicador: PainelIndicador; nivel: PainelNivel; municipios: PainelMunicipios; idsNaTela: string[];
  competencia: string; janela: string[]; referencia: string[]; titulo: string;
  /** Vista em exibição e a frase-resumo do motor (verificada), para a conversa responder "o que o gráfico mostra?". */
  vista?: "grafico" | "mapa" | "lado"; resumo?: string | null;
  /** Se o mapa pode ser mostrado agora e, se não, o motivo (estados sem ponto, planilha sem coordenadas, visão Séries). */
  mapaDisponivel?: boolean; motivoSemMapa?: string | null;
};
/** Estado salvo no Histórico: reabre sem recalcular. `definicao` é o objeto de `salvarEstado`. */
export type EstadoSalvo = { titulo: string; definicao: object; resposta: object | null; quando: string };
/** Estado de uma UF na base do Brasil (bloco "niveis" da inspeção). Basta esta forma (compatível com territorialScope.Levels). */
export type NivelEstado = { prefixo: string; sigla: string; nome: string; rotulo?: string; rotulo_grupo?: string; municipios: number };
export type NiveisDaBase = { estados: NivelEstado[]; municipios: { total: number };
  fonte_estadual?: { disponivel: boolean; motivo: string; periodos?: string[] } };
/** Unidade do catálogo para a escolha (forma de TerritorialSelection.Territory). */
export type UnidadeDoCatalogo = { id: string; name: string; code: string; label: string; state: string; state_name: string;
  state_code?: string; selection_reason?: string };

// ================================================================================================ números e textos
const casas = (digitos: number) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digitos, maximumFractionDigits: digitos });
const ate = (digitos: number) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: digitos });
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/** Arredondamento decimal convencional sobre o valor absoluto (RQ-REP-05), com a correção binária de representation.ts. */
export function arredondar(valor: number, digitos: number): number {
  const fator = 10 ** digitos;
  return Math.round(valor * fator + Number.EPSILON * fator * Math.max(1, valor)) / fator;
}
const mostrado = (valor: number, digitos: number) => Math.sign(valor) * arredondar(Math.abs(valor), digitos);

/** Duas casas; mais casas quando o arredondamento mostraria um valor não nulo como zero ou um valor igual a um limiar
 * diferente dele (relação com limiar, RQ-REP-05). */
function digitosPara(valor: number, limiares: number[] = []): number {
  let digitos = 2;
  while (digitos < 8 && ((valor !== 0 && mostrado(valor, digitos) === 0) ||
    limiares.some(limiar => limiar !== valor && mostrado(limiar, digitos) === mostrado(valor, digitos)))) digitos += 1;
  return digitos;
}

/** Medida contínua com duas casas (sinal preservado, com o sinal de menos tipográfico); contagem inteira. */
export function formatarNumero(valor: number, contagem = false, limiares: number[] = []): string {
  if (contagem) return (valor < 0 ? "−" : "") + inteiro.format(Math.abs(valor));
  const digitos = digitosPara(valor, limiares);
  return (valor < 0 ? "−" : "") + casas(digitos).format(arredondar(Math.abs(valor), digitos));
}

/** Variação percentual do motor (CAP-TMP-01) em pt-BR: "+12,40%", "−3,00%", "0,00%". Sem valor: "Não avaliável". */
export function formatarVariacao(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "Não avaliável";
  const digitos = digitosPara(valor);
  return (valor > 0 ? "+" : valor < 0 ? "−" : "") + casas(digitos).format(arredondar(Math.abs(valor), digitos)) + "%";
}

/** Percentual do motor sem sinal ("72,50%"), duas casas como toda medida contínua. */
export function formatarPercentual(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "Não avaliável";
  return formatarNumero(valor) + "%";
}

/** Rótulo curto de escala (legenda de tamanho e marcas grandes): "2 mi", "500 mil", "1,5 mil", "200". */
export function compacto(valor: number): string {
  const absoluto = Math.abs(valor);
  if (absoluto >= 1e6) return ate(1).format(valor / 1e6) + " mi";
  if (absoluto >= 1e3) return ate(1).format(valor / 1e3) + " mil";
  return inteiro.format(valor);
}

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const ehAaaamm = (valor: string) => /^\d{6}$/.test(valor) && Number(valor.slice(4)) >= 1 && Number(valor.slice(4)) <= 12;
/** Competência AAAAMM como mês/ano ("06/2024"). */
export function exibirCompetencia(valor: string | null | undefined): string {
  if (!valor) return "";
  return ehAaaamm(valor) ? valor.slice(4) + "/" + valor.slice(0, 4) : valor;
}
/** Competência por extenso ("junho de 2024"), como no título. */
export function competenciaPorExtenso(valor: string | null | undefined): string {
  if (!valor) return "";
  return ehAaaamm(valor) ? MESES[Number(valor.slice(4)) - 1] + " de " + valor.slice(0, 4) : valor;
}

// ================================================================================================ nomenclatura territorial
export const ROTULOS_BRASIL: RotulosTerritoriais = {
  unidade: { singular: "município", plural: "municípios", genero: "m" },
  grupo: { singular: "estado", plural: "estados", genero: "m" },
};
export const ROTULOS_GENERICOS: RotulosTerritoriais = {
  unidade: { singular: "unidade", plural: "unidades", genero: "f" },
  grupo: { singular: "grupo", plural: "grupos", genero: "m" },
};
/** Gênero para a concordância simples: o informado ou, sem ele, pela terminação (província, comuna, região, cidade: feminino;
 * distrito, condado, cantão, município: masculino). */
export function generoDe(rotulo: Rotulo): "m" | "f" {
  if (rotulo.genero) return rotulo.genero;
  const palavra = sem(rotulo.singular).split(/\s+/)[0] || "";
  return /(a|ade|cao|sao|giao|gem|ie)$/.test(palavra) && !/(dia|mapa|tema|sistema|problema|planeta)$/.test(palavra) ? "f" : "m";
}
const fem = (rotulo: Rotulo) => generoDe(rotulo) === "f";
/** "o", "a", "os", "as". */
export const artigo = (rotulo: Rotulo, plural: boolean) => (fem(rotulo) ? "a" : "o") + (plural ? "s" : "");
/** "todos os municípios", "todas as províncias". */
export const todosOs = (rotulo: Rotulo) => (fem(rotulo) ? "todas as " : "todos os ") + rotulo.plural;
/** "um município", "uma província". */
export const umA = (rotulo: Rotulo) => (fem(rotulo) ? "uma " : "um ") + rotulo.singular;
/** "nos municípios", "nas províncias" (singular: "no", "na"). */
export const emOs = (rotulo: Rotulo, plural = true) => (fem(rotulo) ? "na" : "no") + (plural ? "s" : "");
export const maiuscula = (texto: string) => texto ? texto.charAt(0).toLocaleUpperCase("pt-BR") + texto.slice(1) : texto;
const minuscula = (texto: string) => texto ? texto.charAt(0).toLocaleLowerCase("pt-BR") + texto.slice(1) : texto;
/** "1 município", "62 municípios", "5.570 municípios". */
export const quantos = (n: number, rotulo: Rotulo) => inteiro.format(n) + " " + (n === 1 ? rotulo.singular : rotulo.plural);

/** Os rótulos que valem: os do motor, senão os da fonte, senão os da base do Brasil (ou genéricos numa planilha). */
export function rotulosEfetivos(resposta: RotulosTerritoriais | null | undefined, fonte: RotulosTerritoriais | null | undefined,
  tipo: "brasil" | "arquivo" | null): RotulosTerritoriais {
  return resposta ?? fonte ?? (tipo === "arquivo" ? ROTULOS_GENERICOS : ROTULOS_BRASIL);
}

/** Grupo da escolha de territórios: um estado (base do Brasil) ou um valor da coluna-mãe (planilha). */
export type GrupoInfo = { id: string; nome: string; sigla: string; rotuloGrupo: string; unidades: number };

/** "Todos os estados (27)", "Todas as províncias (5)". */
export const textoTodosOsGrupos = (rotulos: RotulosTerritoriais, n: number) =>
  maiuscula(todosOs(rotulos.grupo ?? ROTULOS_GENERICOS.grupo!)) + " (" + inteiro.format(n) + ")";
/** "Todos os municípios do Brasil (5.570)"; numa planilha, "Todos os distritos da planilha (40)". */
export const textoTodasAsUnidades = (rotulos: RotulosTerritoriais, n: number, brasil: boolean) =>
  maiuscula(todosOs(rotulos.unidade)) + (brasil ? " do Brasil" : " da planilha") + " (" + inteiro.format(n) + ")";
/** "Ver os 62 municípios", "Ver as 12 comunas", "Ver o 1 distrito". */
export const textoVerUnidades = (rotulos: RotulosTerritoriais, n: number) =>
  "Ver " + artigo(rotulos.unidade, n !== 1) + " " + quantos(n, rotulos.unidade);
/** "Todos os municípios do Amazonas" (com a gramática do motor, "Municípios do Amazonas"); numa planilha, "Todos os distritos
 * de Buenos Aires". */
export function textoTodasAsUnidadesDoGrupo(rotulos: RotulosTerritoriais, grupo: Pick<GrupoInfo, "nome" | "rotuloGrupo">): string {
  if (grupo.rotuloGrupo) return maiuscula((fem(rotulos.unidade) ? "todas as " : "todos os ") + minuscula(grupo.rotuloGrupo));
  return maiuscula(todosOs(rotulos.unidade)) + " de " + grupo.nome;
}
/** "Clique num estado para ver os municípios dele.", "Clique numa província para ver os distritos dela." */
export function textoInstrucaoGrupos(rotulos: RotulosTerritoriais): string {
  const grupo = rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  return "Clique " + (fem(grupo) ? "numa " : "num ") + grupo.singular + " para ver " + artigo(rotulos.unidade, true) + " " +
    rotulos.unidade.plural + " " + (fem(grupo) ? "dela" : "dele") + ". Pelo teclado, use as setas e Enter.";
}
/** "Cada bolha é um município. O tamanho mostra a população." */
export const textoCadaBolha = (rotulo: Rotulo) => "Cada bolha é " + umA(rotulo) + ". O tamanho mostra a população.";

// ================================================================================================ indicadores e famílias
export const INDICADORES: Record<PainelIndicador, { rotulo: string; eixo: string; unidade: string; contagem: boolean }> = {
  densidade: { rotulo: "Densidade", eixo: "Densidade (profissionais por 1.000 habitantes)", unidade: "por 1.000 habitantes", contagem: false },
  quantidade: { rotulo: "Quantidade", eixo: "Quantidade de profissionais", unidade: "profissionais", contagem: true },
};
export const ATRIBUTOS: Record<string, string> = { densidade: "densidade", quantidade: "quantidade", populacao: "população",
  distancia_km: "distância (km)", variacao: "variação percentual" };
export const ORDENS: Record<PainelOrdem, string> = { desc: "da maior para a menor", asc: "da menor para a maior" };
export const OPERADORES: Record<OperadorCondicao, string> = { "<": "menor que", "<=": "até", ">": "maior que", ">=": "a partir de" };
export const SIMBOLOS: Record<OperadorCondicao, string> = { "<": "<", "<=": "≤", ">": ">", ">=": "≥" };

export const FAMILIAS: Familia[] = ["distribuicao", "espacial", "tendencia", "rotatividade"];
export const NOMES_FAMILIAS: Record<Familia, string> = { distribuicao: "Distribuição", espacial: "Análise espacial",
  tendencia: "Tendência", rotatividade: "Rotatividade" };
export function apoioDaFamilia(familia: Familia, rotulos: RotulosTerritoriais): string {
  if (familia === "distribuicao") return "Como " + artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + " se distribuem";
  if (familia === "espacial") return "Distância até uma referência";
  if (familia === "tendencia") return "Mudança e tendência no tempo";
  return "Permanência da coorte inicial";
}
export const NOMES_VISOES: Record<Visao, string> = { mudanca: "Mudança", classes: "Classes", series: "Séries" };

export type Disponivel = { disponivel: boolean; motivo: string; pendente: boolean; enviarDados: boolean };
/** Se a família pode ser usada agora. "pendente": registra a intenção e pede um passo antes (escolher os dados, abrir as
 * unidades). Os motivos de indisponibilidade vêm do motor (`disponibilidade`); sem eles, a regra da fonte. */
export function disponibilidadeDaFamilia(familia: Familia, c: { fonte: "brasil" | "arquivo" | null; nivel: PainelNivel;
  disponibilidade: PainelResposta["disponibilidade"] | null; temIdentificador: boolean; rotulos: RotulosTerritoriais }): Disponivel {
  const ok: Disponivel = { disponivel: true, motivo: "", pendente: false, enviarDados: false };
  if (!c.fonte) return { ...ok, pendente: familia !== "distribuicao", motivo: "Escolha os dados para começar." };
  if (familia === "distribuicao") return ok;
  const motor = c.disponibilidade?.[familia];
  if (familia === "rotatividade") {
    if (motor && !motor.disponivel) return { disponivel: false, motivo: motor.motivo, pendente: false, enviarDados: c.fonte === "brasil" };
    if (c.fonte === "brasil") return { disponivel: false, pendente: false, enviarDados: true,
      motivo: "A base do Brasil tem contagens, não pessoas: a rotatividade exige dados enviados com o identificador individual (CAP-ROT-01)." };
    if (!motor && !c.temIdentificador) return { disponivel: false, pendente: false, enviarDados: false,
      motivo: "A planilha não tem a coluna do identificador individual: a rotatividade acompanha pessoas da coorte inicial (CAP-ROT-01)." };
    return ok;
  }
  if (motor && !motor.disponivel) return { disponivel: false, motivo: motor.motivo, pendente: false, enviarDados: false };
  if (c.nivel === "estados") {
    const grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
    return { ...ok, pendente: true, motivo: (familia === "espacial"
      ? "A análise espacial mede a distância entre " + c.rotulos.unidade.plural + "; " + artigo(grupo, true) + " " + grupo.plural +
        " não têm coordenadas."
      : "A tendência, nesta fase, usa " + artigo(c.rotulos.unidade, true) + " " + c.rotulos.unidade.plural + ".") +
      " Abra " + umA(grupo) + " ou escolha " + c.rotulos.unidade.plural + " na lista." };
  }
  return ok;
}

/** "Médicos" sai da categoria da base (MEDICINA); com outra categoria, entra o nome informado. */
export function profissionaisDe(categoria: string): string {
  const chave = sem(categoria);
  if (!chave) return "profissionais";
  if (chave === "medicina" || chave === "medicos" || chave === "medico") return "médicos";
  return "profissionais de " + categoria.toLocaleLowerCase("pt-BR");
}

// ================================================================================================ universo e escolha
export const prefixoDe = (id: string) => id.startsWith("code:") ? id.slice(5, 7) : "";

/** Universo enviado ao motor: "todos" absorve o resto; um grupo inteiro absorve as suas unidades avulsas. */
export function normalizarBase(base: PainelMunicipios, grupoDe: (id: string) => string = prefixoDe): PainelMunicipios {
  if (base.todos) return { todos: true, estados: [], ids: [] };
  const estados = [...new Set(base.estados)].sort(comparar);
  return { todos: false, estados, ids: [...new Set(base.ids)].filter(id => !estados.includes(grupoDe(id))) };
}
export const baseVazia = (base: PainelMunicipios) => !base.todos && !base.estados.length && !base.ids.length;
export const BASE_VAZIA: PainelMunicipios = { todos: false, estados: [], ids: [] };
export const MAX_CONJUNTOS = 50;

/** A unidade está no universo (marcada na lista)? */
export const unidadeMarcada = (base: PainelMunicipios, id: string, grupo: string) =>
  base.todos || (!!grupo && base.estados.includes(grupo)) || base.ids.includes(id);
export const grupoInteiro = (base: PainelMunicipios, grupo: string) => base.todos || base.estados.includes(grupo);
/** Quantas unidades do grupo estão marcadas. */
export const marcadasNoGrupo = (base: PainelMunicipios, grupo: string, unidades: string[]) =>
  grupoInteiro(base, grupo) ? unidades.length : unidades.filter(id => base.ids.includes(id)).length;

/** Marca o grupo inteiro ("Todos os municípios do Amazonas"), sem desfazer os outros grupos e unidades. */
export function marcarGrupo(base: PainelMunicipios, grupo: string, unidades: string[]): PainelMunicipios {
  if (base.todos) return base;
  return { todos: false, estados: [...new Set([...base.estados, grupo])].sort(comparar), ids: base.ids.filter(id => !unidades.includes(id)) };
}
/** Desmarca o grupo inteiro; com "todos", ficam os demais grupos inteiros (ou as demais unidades, sem grupos). */
export function desmarcarGrupo(base: PainelMunicipios, grupo: string, unidades: string[], todosOsGrupos: string[],
  todasAsUnidades: string[] = []): PainelMunicipios {
  if (base.todos) return todosOsGrupos.length ? { todos: false, estados: todosOsGrupos.filter(g => g !== grupo).sort(comparar), ids: [] }
    : { todos: false, estados: [], ids: todasAsUnidades.filter(id => !unidades.includes(id)) };
  return { todos: false, estados: base.estados.filter(g => g !== grupo), ids: base.ids.filter(id => !unidades.includes(id)) };
}
/** Marca ou desmarca uma unidade. Desmarcar dentro de um grupo inteiro (ou de "todos") deixa as demais marcadas, uma a uma;
 * marcar a última que faltava devolve o grupo inteiro. */
export function alternarUnidade(base: PainelMunicipios, id: string, grupo: string, unidades: string[], todosOsGrupos: string[],
  todasAsUnidades: string[] = []): PainelMunicipios {
  if (unidadeMarcada(base, id, grupo)) {
    if (base.todos) {
      if (grupo && todosOsGrupos.length) return { todos: false, estados: todosOsGrupos.filter(g => g !== grupo).sort(comparar),
        ids: unidades.filter(item => item !== id) };
      return { todos: false, estados: [], ids: todasAsUnidades.filter(item => item !== id) };
    }
    if (grupo && base.estados.includes(grupo))
      return { todos: false, estados: base.estados.filter(g => g !== grupo), ids: [...base.ids, ...unidades.filter(item => item !== id)] };
    return { ...base, ids: base.ids.filter(item => item !== id) };
  }
  const ids = [...base.ids, id];
  if (grupo && unidades.length && unidades.every(item => ids.includes(item))) return marcarGrupo({ ...base, ids }, grupo, unidades);
  // Sem grupos (planilha sem coluna-mãe): marcar a última que faltava vale "todas".
  if (!grupo && todasAsUnidades.length && !base.estados.length && todasAsUnidades.every(item => ids.includes(item)))
    return { todos: true, estados: [], ids: [] };
  return { ...base, ids };
}

/** Quantas unidades o universo tem (para a trilha): grupos inteiros pelo tamanho informado na lista e unidades avulsas. */
export function unidadesNoUniverso(base: PainelMunicipios, grupos: GrupoInfo[], total: number, grupoDe: (id: string) => string): number {
  if (base.todos) return total;
  const tamanho = (grupo: string) => grupos.find(item => item.id === grupo)?.unidades ?? 0;
  return base.estados.reduce((soma, grupo) => soma + tamanho(grupo), 0) + base.ids.filter(id => !base.estados.includes(grupoDe(id))).length;
}

export type Lugar = { lugar: string; curto: string };
/** Onde: "nos municípios do Amazonas" / "Amazonas"; "nos estados" / "Brasil"; "em 3 municípios do Amazonas". */
export function lugarDoUniverso(c: { nivel: PainelNivel; base: PainelMunicipios; conjuntos: number; grupos: GrupoInfo[];
  rotulos: RotulosTerritoriais; brasil: boolean; grupoDe: (id: string) => string }): Lugar {
  const unidade = c.rotulos.unidade, grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const origem = c.brasil ? "Brasil" : "Planilha";
  if (c.nivel === "estados") return { lugar: emOs(grupo) + " " + grupo.plural, curto: origem };
  if (c.base.todos) return { lugar: emOs(unidade) + " " + unidade.plural + (c.brasil ? " do Brasil" : " da planilha"), curto: origem };
  const info = (id: string) => c.grupos.find(item => item.id === id);
  // "do Amazonas" a partir de "Municípios do Amazonas" (gramática do motor); na planilha, "de <grupo>".
  const deGrupo = (id: string) => {
    const g = info(id);
    if (g?.rotuloGrupo) return g.rotuloGrupo.split(" ").slice(1).join(" ");
    return "de " + (g?.nome || id);
  };
  const nomeGrupo = (id: string) => info(id)?.nome || id;
  const avulsas = c.base.ids.filter(id => !c.base.estados.includes(c.grupoDe(id)));
  const gruposDasAvulsas = [...new Set(avulsas.map(c.grupoDe))];
  if (c.base.estados.length && !avulsas.length) {
    if (c.base.estados.length <= 2) return { lugar: emOs(unidade) + " " + unidade.plural + " " + c.base.estados.map(deGrupo).join(" e "),
      curto: c.base.estados.map(nomeGrupo).join(" e ") };
    const n = c.base.estados.length + " " + grupo.plural;
    return { lugar: emOs(unidade) + " " + unidade.plural + " de " + n, curto: n };
  }
  if (!c.base.estados.length && avulsas.length) {
    const umGrupo = gruposDasAvulsas.length === 1 && gruposDasAvulsas[0] ? gruposDasAvulsas[0] : null;
    if (umGrupo) return { lugar: "em " + quantos(avulsas.length, unidade) + " " + deGrupo(umGrupo),
      curto: quantos(avulsas.length, unidade) + " " + deGrupo(umGrupo) };
    return { lugar: "em " + quantos(avulsas.length, unidade), curto: quantos(avulsas.length, unidade) };
  }
  if (c.base.estados.length && avulsas.length) {
    const grupos = c.base.estados.length <= 2 ? c.base.estados.map(deGrupo).join(" e ") : "de " + c.base.estados.length + " " + grupo.plural;
    return { lugar: emOs(unidade) + " " + unidade.plural + " " + grupos + " e em mais " + quantos(avulsas.length, unidade),
      curto: (c.base.estados.length <= 2 ? c.base.estados.map(nomeGrupo).join(" e ") : c.base.estados.length + " " + grupo.plural) +
        " e mais " + quantos(avulsas.length, unidade) };
  }
  return { lugar: c.conjuntos ? "nos conjuntos escolhidos" : "", curto: c.conjuntos ? "Conjuntos" : origem };
}

/** Trilha de volta: "Brasil › Amazonas › 3 municípios". Cada passo anterior tem a sua ação. */
export type PassoTrilha = { rotulo: string; acao: { tipo: "estados" } | { tipo: "todos" } | { tipo: "grupo"; id: string } | null };
export function trilhaDoUniverso(c: { nivel: PainelNivel; base: PainelMunicipios; grupos: GrupoInfo[]; rotulos: RotulosTerritoriais;
  brasil: boolean; temGrupos: boolean; total: number; grupoDe: (id: string) => string }): PassoTrilha[] {
  const unidade = c.rotulos.unidade, grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const raiz: PassoTrilha = { rotulo: c.brasil ? "Brasil" : "Planilha",
    acao: c.brasil && c.temGrupos ? { tipo: "estados" } : { tipo: "todos" } };
  if (c.nivel === "estados") return [{ ...raiz, acao: null }, { rotulo: textoTodosOsGrupos(c.rotulos, c.grupos.length), acao: null }];
  if (c.base.todos) return [raiz, { rotulo: maiuscula(todosOs(unidade)) + " (" + inteiro.format(c.total) + ")", acao: null }];
  const nome = (id: string) => c.grupos.find(item => item.id === id)?.nome || id;
  const avulsas = c.base.ids.filter(id => !c.base.estados.includes(c.grupoDe(id)));
  const gruposDasAvulsas = [...new Set(avulsas.map(c.grupoDe))].filter(Boolean);
  const n = unidadesNoUniverso(c.base, c.grupos, c.total, c.grupoDe);
  if (c.base.estados.length === 1 && !avulsas.length)
    return [raiz, { rotulo: nome(c.base.estados[0]) + " (" + quantos(n, unidade) + ")", acao: null }];
  if (!c.base.estados.length && avulsas.length && gruposDasAvulsas.length === 1)
    return [raiz, { rotulo: nome(gruposDasAvulsas[0]), acao: { tipo: "grupo", id: gruposDasAvulsas[0] } },
      { rotulo: quantos(avulsas.length, unidade), acao: null }];
  if (c.base.estados.length > 1 && !avulsas.length)
    return [raiz, { rotulo: (c.base.estados.length <= 3 ? c.base.estados.map(nome).join(", ") : c.base.estados.length + " " + grupo.plural) +
      " (" + quantos(n, unidade) + ")", acao: null }];
  if (baseVazia(c.base)) return [raiz, { rotulo: "Nenhum" + (fem(unidade) ? "a " : " ") + unidade.singular + " marcad" + (fem(unidade) ? "a" : "o"), acao: null }];
  return [raiz, { rotulo: quantos(n, unidade), acao: null }];
}

/** Grupos da escolha: os estados da base do Brasil (bloco "niveis") ou os valores da coluna-mãe do catálogo da planilha. */
export function gruposDaFonte(niveis: NiveisDaBase | null | undefined, catalogo: UnidadeDoCatalogo[]): GrupoInfo[] {
  if (niveis?.estados?.length) return niveis.estados.map(item => ({ id: item.prefixo, nome: item.nome, sigla: item.sigla,
    rotuloGrupo: item.rotulo_grupo || "", unidades: item.municipios }));
  const contagem = new Map<string, { nome: string; unidades: number }>();
  for (const item of catalogo) {
    if (item.selection_reason) continue;
    const id = item.state_code || item.state || "";
    if (!id) continue;
    const atual = contagem.get(id) || { nome: item.state_name || item.state || id, unidades: 0 };
    atual.unidades += 1;
    contagem.set(id, atual);
  }
  return [...contagem.entries()].map(([id, valor]) => ({ id, nome: valor.nome, sigla: "", rotuloGrupo: "", unidades: valor.unidades }))
    .sort((a, b) => comparar(a.nome, b.nome));
}
/** Grupo da lista que corresponde a uma bolha de grupo do motor: pelo identificador ("uf:13", "estado:13" ou "13"), senão pela
 * sigla ou pelo nome no rótulo. Só associa; null quando não acha. */
export function grupoDoItem(item: Pick<PainelItem, "id" | "uf" | "rotulo">, grupos: GrupoInfo[]): string | null {
  const chave = /^(?:uf|estado|state|grupo):(.+)$/.exec(item.id)?.[1] ?? item.id;
  if (grupos.some(grupo => grupo.id === chave)) return chave;
  const porSigla = grupos.find(grupo => grupo.sigla && (grupo.sigla === item.uf || item.rotulo.trim().endsWith("(" + grupo.sigla + ")")));
  if (porSigla) return porSigla.id;
  return grupos.find(grupo => sem(item.rotulo).startsWith(sem(grupo.nome)))?.id ?? null;
}
/** Grupo de uma unidade do catálogo (prefixo IBGE na base do Brasil; valor da coluna-mãe na planilha). */
export const grupoDaUnidade = (item: UnidadeDoCatalogo) => item.state_code || item.state || "";
/** Nome para listas: "MANAUS (AM)". */
export const nomeDaUnidade = (item: UnidadeDoCatalogo) => item.name ? item.name + (item.state ? " (" + item.state + ")" : "") : item.label;

// ================================================================================================ conjuntos (RQ-REP-14)
export const SOMA = "SOMA_DOS_COMPONENTES";
/** Tipo de contagem do agregado como texto: a soma nunca é rotulada como pessoas únicas ou profissionais distintos. */
export function textoDaContagem(contagem: string | null | undefined): string {
  if (!contagem || contagem === SOMA) return "soma das contagens dos componentes, com possível dupla contagem";
  if (contagem === "UNIDADES_DISTINTAS") return "unidades distintas, conforme premissa do usuário";
  return contagem.toLowerCase().replace(/_/g, " ");
}
export const NOTA_SOMA = "Soma das contagens dos componentes, com possível dupla contagem: quem atua em mais de uma unidade " +
  "do conjunto pode ser contado mais de uma vez. A população também é a soma dos membros.";

/** Novo conjunto (CAP-AGR-01 no motor): identificador c1, c2…; os membros são unidades, sem repetição. */
export function novoConjunto(existentes: PainelConjuntoPedido[], membros: string[], rotulo: string): PainelConjuntoPedido {
  const usados = existentes.map(conjunto => /^c(\d+)$/.exec(conjunto.id)).map(achado => achado ? Number(achado[1]) : 0);
  const proximo = Math.max(0, ...usados) + 1;
  return { id: "c" + proximo, rotulo: rotulo.trim().slice(0, 120) || "Conjunto " + proximo, membros: [...new Set(membros)] };
}

// ================================================================================================ ordem, motivos e não avaliáveis
/** Ordem neutra (RQ-REP-03): unidades pelo código territorial; depois os conjuntos, na ordem de criação. */
export function ordemNeutra(a: { id: string; tipo?: string }, b: { id: string; tipo?: string }): number {
  const grupoA = a.tipo === "conjunto" ? 1 : 0, grupoB = b.tipo === "conjunto" ? 1 : 0;
  return grupoA - grupoB || comparar(a.id, b.id);
}

export type Aspecto = "indicador" | "distancia" | "variacao" | "tendencia" | "condicoes" | "rotatividade" | "mapa";
/** Aspecto de um motivo do motor, pelo começo do texto (nunca pela posição na lista). */
export function aspectoDoMotivo(texto: string): "distancia" | "variacao" | "geral" {
  const inicio = sem(texto);
  if (inicio.startsWith("distancia nao avaliavel")) return "distancia";
  if (inicio.startsWith("variacao nao avaliavel") || inicio.startsWith("variacao percentual")) return "variacao";
  return "geral";
}
/** Agregado parcial: aviso (o valor existe, sobre os membros com registro), não motivo de valor não avaliável. */
export const ehAviso = (texto: string) => sem(texto).startsWith("agregado parcial");
const textosDe = (item: PainelItem) => [...new Set((item.motivos || []).filter((texto): texto is string =>
  typeof texto === "string" && !!texto.trim()).map(texto => texto.trim()))];
/** Motivos do motor para um aspecto: primeiro os do próprio aspecto, depois os gerais (sem o aviso de agregado parcial). */
export function motivosDe(item: PainelItem, aspecto?: "indicador" | "distancia" | "variacao"): string[] {
  const textos = textosDe(item);
  if (!aspecto) return textos;
  return [...textos.filter(texto => aspectoDoMotivo(texto) === aspecto),
    ...textos.filter(texto => aspectoDoMotivo(texto) === "geral" && !ehAviso(texto))];
}
export const avisosDe = (item: PainelItem) => textosDe(item).filter(ehAviso);

const LIMITACOES: Record<string, string> = {
  SOMA_COM_POSSIVEL_DUPLA_CONTAGEM: "Conjuntos: soma das contagens dos componentes, com possível dupla contagem.",
  AGREGADO_PARCIAL: "Agregado parcial: algum conjunto tem membro sem registro na competência, e o valor dele vale para os membros " +
    "com registro, não para o conjunto completo.",
  DISTANCIA_GEODESICA_DIRETA: "Distância geodésica direta entre as unidades, não o trajeto de deslocamento.",
  UNIDADES_NAO_AVALIAVEIS: "Há itens com valor não avaliável, listados à parte com o motivo.",
};
/** Código de limitação do motor em texto; código desconhecido aparece como está. */
export const textoDaLimitacao = (codigo: string) => LIMITACOES[codigo] || "Limitação registrada pelo motor: " + codigo + ".";
/** Nota TPL-11 da distância (sempre junto da análise espacial). */
export const NOTA_TPL11 = "Distância geográfica direta em linha reta entre as unidades (km), calculada pelo motor. Não representa " +
  "estrada, tempo de viagem nem facilidade de chegada.";

export type NaoAvaliavel = { id: string; rotulo: string; tipo: PainelItem["tipo"]; aspecto: Aspecto; motivo: string };
export type Exibicao = { distancia: boolean; variacao: boolean; tendencia: boolean; condicoes: boolean; rotatividade: boolean;
  /** Com o mapa à vista: as unidades que o motor devolveu sem coordenada válida (id → motivo do motor, DadosDoMapa.semCoordenada). */
  semCoordenada: Map<string, string> | null };
const MOTIVO_PADRAO: Record<Aspecto, (indicador: PainelIndicador) => string> = {
  indicador: indicador => "Sem " + INDICADORES[indicador].rotulo.toLowerCase() + " avaliável na competência.",
  distancia: () => "Sem coordenada válida para medir a distância até a referência.",
  variacao: () => "Variação não avaliável (valor inicial zero ou ausente).",
  tendencia: () => "Tendência não avaliável nesta janela.",
  condicoes: () => "Sem dado para avaliar as condições.",
  rotatividade: () => "Coorte não avaliável.",
  mapa: () => "Sem coordenada válida para o mapa.",
};

/** Itens desenháveis no estado da tela e não avaliáveis à parte (RQ-REP-04), na ordem neutra. Sem o indicador, o item não
 * vira bolha; com a distância à vista, também sem coordenada. Variação, tendência e condições não avaliáveis: a bolha fica
 * (vazada) e o item entra na lista com o motivo. Na rotatividade, a coorte sem valor sai das barras. Com o mapa à vista, a
 * unidade sem coordenada válida fica fora do mapa (no gráfico, continua) e entra na lista com o motivo do motor. */
export function separarItens(itens: PainelItem[], indicador: PainelIndicador, exibicao: Partial<Exibicao>):
  { plotaveis: PainelItem[]; fora: NaoAvaliavel[] } {
  const plotaveis: PainelItem[] = [], fora: NaoAvaliavel[] = [];
  const registrar = (item: PainelItem, aspecto: Aspecto, motivo?: string | null) => fora.push({ id: item.id, rotulo: item.rotulo,
    tipo: item.tipo, aspecto, motivo: motivo || (aspecto === "indicador" || aspecto === "distancia" || aspecto === "variacao"
      ? motivosDe(item, aspecto)[0] : aspecto === "mapa" ? null : textosDe(item).filter(t => !ehAviso(t))[0]) || MOTIVO_PADRAO[aspecto](indicador) });
  const semPonto = (item: PainelItem) => { if (exibicao.semCoordenada?.has(item.id)) registrar(item, "mapa", exibicao.semCoordenada.get(item.id)); };
  for (const item of [...itens].sort(ordemNeutra)) {
    if (exibicao.rotatividade) {
      if (!item.rotatividade || !item.rotatividade.avaliavel) registrar(item, "rotatividade", item.rotatividade?.motivo);
      else { plotaveis.push(item); semPonto(item); }
      continue;
    }
    if (numero(item[indicador]) === null) { registrar(item, "indicador"); continue; }
    if (exibicao.distancia && numero(item.distancia_km) === null) { registrar(item, "distancia"); continue; }
    plotaveis.push(item);
    semPonto(item);
    if (exibicao.variacao && numero(item.variacao_percentual?.[indicador]) === null) registrar(item, "variacao");
    if (exibicao.tendencia && (!item.tendencia || !item.tendencia.avaliavel)) registrar(item, "tendencia", item.tendencia?.motivo || item.tendencia?.rotulo);
    if (exibicao.condicoes && item.condicoes?.situacao === "NAO_AVALIAVEL") registrar(item, "condicoes", item.condicoes.motivo ||
      item.condicoes.porCondicao.filter(c => c.situacao === "NAO_AVALIAVEL").map(c => c.texto).filter(Boolean).join("; "));
  }
  return { plotaveis, fora };
}

export const valorDe = (item: PainelItem, indicador: PainelIndicador): number | null => numero(item[indicador]);
export const inicialDe = (item: PainelItem, campo: PainelIndicador | "populacao"): number | null => numero(item.inicial?.[campo]);
export const variacaoDe = (item: PainelItem, campo: PainelIndicador | "populacao"): number | null => numero(item.variacao_percentual?.[campo]);
export function formatarIndicador(valor: number | null, indicador: PainelIndicador, limiares: number[] = []): string {
  if (valor === null) return "Não avaliável";
  const spec = INDICADORES[indicador];
  return formatarNumero(valor, spec.contagem, limiares) + " " + spec.unidade;
}

// ================================================================================================ escalas
export type Escala = "linear" | "logaritmica";

/** Maior potência de 10 que não passa do valor (corrige o log10 inexato perto das potências exatas). */
function potencia(valor: number): number {
  let resultado = 10 ** Math.floor(Math.log10(valor));
  if (resultado * 10 <= valor * (1 + 1e-9)) resultado *= 10;
  if (resultado > valor * (1 + 1e-9)) resultado /= 10;
  return limpo(resultado);
}
function passoBonito(bruto: number, fatores = [1, 2, 2.5, 5, 10]): number {
  if (!(bruto > 0) || !Number.isFinite(bruto)) return 1;
  const base = potencia(bruto);
  return fatores.map(fator => limpo(fator * base)).find(candidato => candidato >= bruto * (1 - 1e-9)) ?? limpo(10 * base);
}

/** Escala do eixo do indicador: linear, ou logarítmica SÓ por escolha da pessoa e só com todos os valores positivos (Parte 13,
 * L1994: nada de mudança automática de escala). */
export function escalaPossivel(valores: number[], escolhida: Escala): Escala {
  return escolhida === "logaritmica" && valores.length > 0 && valores.every(valor => valor > 0) ? "logaritmica" : "linear";
}

/** Domínio de desenho em números redondos ao redor dos valores (só enquadra; linear a partir do zero). */
export function enquadrar(valores: number[], escala: Escala): PainelDominio {
  const validos = valores.filter(valor => Number.isFinite(valor));
  if (!validos.length) return [0, 1];
  let menor = Math.min(...validos), maior = Math.max(...validos);
  if (escala === "logaritmica" && menor > 0) {
    const baixo = limpo(([5, 2, 1].find(fator => fator * potencia(menor) <= menor * (1 + 1e-9)) ?? 1) * potencia(menor));
    const alto = limpo(([1, 2, 5, 10].find(fator => fator * potencia(maior) >= maior * (1 - 1e-9)) ?? 10) * potencia(maior));
    return alto > baixo ? [baixo, alto] : [baixo, limpo(baixo * 10)];
  }
  if (menor > 0) menor = 0;
  if (maior <= menor) maior = menor + (Math.abs(menor) * 0.1 || 1);
  const passo = passoBonito((maior - menor) / 5);
  const inicio = limpo(Math.floor(limpo(menor / passo)) * passo), fim = limpo(Math.ceil(limpo(maior / passo)) * passo);
  return [menor >= 0 && inicio < 0 ? 0 : inicio, fim > inicio ? fim : limpo(inicio + passo)];
}

/** Marcas do eixo: passos 1, 2, 2,5 ou 5 × 10ⁿ; na logarítmica, 1, 2 e 5 de cada década (só as potências de 10 se forem muitas). */
export function marcas(dominio: PainelDominio, escala: Escala, alvo = 5): number[] {
  const [a, b] = dominio;
  if (!(b > a)) return [a];
  if (escala === "logaritmica" && a > 0) {
    const saida: number[] = [];
    for (let k = Math.floor(Math.log10(a)); k <= Math.ceil(Math.log10(b)); k++)
      for (const fator of [1, 2, 5]) {
        const valor = limpo(fator * 10 ** k);
        if (valor >= a * (1 - 1e-9) && valor <= b * (1 + 1e-9)) saida.push(valor);
      }
    return saida.length > 7 ? saida.filter(valor => Number.isInteger(limpo(Math.log10(valor)))) : saida;
  }
  const passo = passoBonito((b - a) / Math.max(1, alvo - 1));
  const saida: number[] = [];
  for (let valor = limpo(Math.ceil(limpo(a / passo)) * passo); valor <= b + passo * 1e-9; valor = limpo(valor + passo)) saida.push(valor);
  return saida;
}
export const textoDaMarca = (valor: number) => Math.abs(valor) >= 10000 ? compacto(valor) : ate(3).format(valor);

/** Posição (0 a 1) de um valor no domínio; fora dele, presa às pontas. */
export function fracao(valor: number, dominio: PainelDominio, escala: Escala): number {
  const [a, b] = dominio;
  let posicao: number;
  if (escala === "logaritmica" && a > 0 && b > a) posicao = valor > 0 ? Math.log(valor / a) / Math.log(b / a) : 0;
  else posicao = b > a ? (valor - a) / (b - a) : 0.5;
  return Math.min(1, Math.max(0, posicao));
}
export function valorNaFracao(posicao: number, dominio: PainelDominio, escala: Escala): number {
  const [a, b] = dominio, t = Math.min(1, Math.max(0, posicao));
  if (escala === "logaritmica" && a > 0 && b > a) return a * (b / a) ** t;
  return a + (b - a) * t;
}

// ================================================================================================ tamanho (população)
export const RAIO_MINIMO = 4;
/** Maior raio conforme a largura do gráfico (celular a tela larga). */
export const raioMaximo = (largura: number) => Math.round(Math.min(34, Math.max(12, largura / 34)));

/** Área proporcional à população (raio pela raiz quadrada); populações muito pequenas ficam no tamanho mínimo visível. */
export function raioDaPopulacao(populacao: number | null | undefined, maxima: number | null | undefined, raioMax: number): number {
  const valor = numero(populacao), topo = numero(maxima);
  if (valor === null || valor <= 0 || topo === null || topo <= 0) return RAIO_MINIMO;
  return Math.max(RAIO_MINIMO, raioMax * Math.sqrt(Math.min(valor, topo) / topo));
}

export type TamanhoLegenda = { valor: number; raio: number; texto: string };
/** Três tamanhos de referência em números redondos (1, 2 ou 5 × 10ⁿ) abaixo da maior população: legenda de escala, não dado. */
export function legendaDeTamanhos(maxima: number | null | undefined, raioMax: number): TamanhoLegenda[] {
  const topo = numero(maxima);
  if (topo === null || topo <= 0) return [];
  const abaixo = (valor: number) => limpo(([5, 2, 1].find(fator => fator * potencia(valor) <= valor * (1 + 1e-9)) ?? 1) * potencia(valor));
  const maior = abaixo(topo);
  const valores = [maior, abaixo(maior / 4), abaixo(maior / 25)].filter((valor, indice, todos) => valor > 0 && todos.indexOf(valor) === indice);
  return valores.map(valor => ({ valor, raio: raioDaPopulacao(valor, topo, raioMax), texto: compacto(valor) + " hab." }));
}

// ================================================================================================ cor
/** Série única: azul-petróleo da identidade, com croma e contraste validados. */
export const COR_BOLHA = "#008b9e";
export const COR_NEUTRA = "#c9c7bf";
export const COR_NAO_AVALIAVEL = "#898781";
/** Família da classe de tendência (CAP-TEN-01; Adendo BOL aprovado em 22/10/2026): crescimento azul, declínio laranja, sem
 * classificação verde-água. Os três primeiros tons da paleta categórica, conferidos em todos os pares (bolhas). */
export const CORES_TENDENCIA: Record<FamiliaTendencia, string> = { CRESCIMENTO: "#2a78d6", DECLINIO: "#eb6834", NENHUMA: "#1baf7a" };
export const NOMES_FAMILIA_TENDENCIA: Record<FamiliaTendencia, string> = { CRESCIMENTO: "Família do crescimento",
  DECLINIO: "Família do declínio", NENHUMA: "Sem classificação" };
/** Ordem do enum CategoriaTendencia (SPEC L415): a ordem da legenda e das contagens, não um ranking. Rótulos de DA-15. */
export const CLASSES_TENDENCIA: { codigo: string; rotulo: string; familia: FamiliaTendencia }[] = [
  { codigo: "CRESCIMENTO", rotulo: "Crescimento", familia: "CRESCIMENTO" },
  { codigo: "CRESCIMENTO_ACELERADO", rotulo: "Aceleração do crescimento", familia: "CRESCIMENTO" },
  { codigo: "CRESCIMENTO_DESACELERADO", rotulo: "Desaceleração do crescimento", familia: "CRESCIMENTO" },
  { codigo: "DECLINIO", rotulo: "Declínio", familia: "DECLINIO" },
  { codigo: "DECLINIO_ACELERADO", rotulo: "Aceleração do declínio", familia: "DECLINIO" },
  { codigo: "DECLINIO_DESACELERADO", rotulo: "Desaceleração do declínio", familia: "DECLINIO" },
  { codigo: "SEM_CLASSIFICACAO", rotulo: "Sem classificação", familia: "NENHUMA" },
];
export function familiaDaClasse(classe: string | null | undefined): FamiliaTendencia | null {
  return CLASSES_TENDENCIA.find(item => item.codigo === classe)?.familia ?? null;
}
/** Grupos e faixas: rampa ordinal de um tom (claro ao escuro), conferida (--ordinal) do 2 ao 5; com mais, só as linhas de corte. */
export const RAMPAS_ORDINAIS: Record<number, string[]> = {
  1: ["#2a78d6"], 2: ["#86b6ef", "#1c5cab"], 3: ["#86b6ef", "#2a78d6", "#104281"],
  4: ["#86b6ef", "#3987e5", "#256abf", "#104281"], 5: ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"],
};
/** Cor do grupo ou faixa (índice a partir de 1) entre `total`; null com mais de 5 (só linhas de corte). */
export const corOrdinal = (indice: number, total: number): string | null => RAMPAS_ORDINAIS[total]?.[indice - 1] ?? null;
/** Mudança entre duas competências (CAP-TMP-01): divergente contínuo, aumento em azul, redução em laranja, zero em cinza. */
export const RAMPA_AUMENTO = ["#9cc2ee", "#2a78d6", "#184f95"];
export const RAMPA_REDUCAO = ["#f2ad8c", "#eb6834", "#a8431b"];

function rgb(hex: string): [number, number, number] {
  const valor = parseInt(hex.slice(1), 16);
  return [(valor >> 16) & 255, (valor >> 8) & 255, valor & 255];
}
function misturar(de: string, para: string, t: number): string {
  const [a, b] = [rgb(de), rgb(para)];
  return "#" + a.map((canal, i) => Math.round(canal + (b[i] - canal) * t).toString(16).padStart(2, "0")).join("");
}
/** Cor da variação: azul para aumento, laranja para redução. Intensidade contínua pela raiz quadrada de |variação| ÷ limite
 * (o meio de cada braço vale um quarto do limite). Escala contínua, sem classes (RQ-REP-02). */
export function corDaVariacao(valor: number, limite: number): string {
  if (valor === 0 || !Number.isFinite(valor)) return COR_NEUTRA;
  const t = limite > 0 ? Math.sqrt(Math.min(1, Math.abs(valor) / limite)) : 1;
  const rampa = valor > 0 ? RAMPA_AUMENTO : RAMPA_REDUCAO;
  const posicao = t * (rampa.length - 1), indice = Math.min(rampa.length - 2, Math.floor(posicao));
  return misturar(rampa[indice], rampa[indice + 1], posicao - indice);
}
/** Limite simétrico da escala de cor: o maior |valor| do domínio de variação do motor (ou dos valores, só para enquadrar). */
export function limiteDaVariacao(resposta: Pick<PainelResposta, "dominios">, indicador: PainelIndicador, itens: PainelItem[]): number {
  const dominio = resposta.dominios["variacao_" + indicador];
  const valores = dominio ? [dominio[0], dominio[1]] : itens.map(item => variacaoDe(item, indicador)).filter(ehNumero);
  return Math.max(0, ...valores.filter(valor => Number.isFinite(valor)).map(Math.abs));
}
/** "aumento", "redução" ou "sem mudança" (CAP-TMP-01, V-05), nunca "crescimento". */
export const direcaoDaVariacao = (valor: number | null) => valor === null ? "não avaliável" : valor > 0 ? "aumento" : valor < 0 ? "redução" : "sem mudança";

export type CamadaDeCor = "unica" | "variacao" | "classes" | "grupos" | "faixas" | "condicoes" | "ordem";
export type Pintura = { cor: string; vazada: boolean; apagada: boolean };
export type ParametrosPintura = { camada: CamadaDeCor; indicador: PainelIndicador; limiteVariacao: number; totalGrupos: number;
  totalFaixas: number; primeiros: number | null };
/** Cor de cada bolha pela camada em uso. Só traduz o que o motor devolveu (variação, classe, grupo, faixa, situação, posição). */
export function pintar(item: PainelItem, p: ParametrosPintura): Pintura {
  const vazia: Pintura = { cor: "#ffffff", vazada: true, apagada: false };
  switch (p.camada) {
    case "variacao": {
      const valor = variacaoDe(item, p.indicador);
      return valor === null ? vazia : { cor: corDaVariacao(valor, p.limiteVariacao), vazada: false, apagada: false };
    }
    case "classes": {
      const familia = item.tendencia?.avaliavel ? item.tendencia.familia ?? familiaDaClasse(item.tendencia.classe) : null;
      return familia ? { cor: CORES_TENDENCIA[familia], vazada: false, apagada: false } : vazia;
    }
    case "grupos": {
      if (!item.grupo) return vazia;
      return { cor: corOrdinal(item.grupo.indice, p.totalGrupos) ?? COR_BOLHA, vazada: false, apagada: false };
    }
    case "faixas": {
      if (!item.faixa) return vazia;
      if (item.faixa === "fora") return { cor: COR_NEUTRA, vazada: false, apagada: false };
      return { cor: corOrdinal(item.faixa.indice, p.totalFaixas) ?? COR_BOLHA, vazada: false, apagada: false };
    }
    case "condicoes": {
      const situacao = item.condicoes?.situacao;
      if (!situacao || situacao === "NAO_AVALIAVEL") return vazia;
      return situacao === "ATENDE" ? { cor: COR_BOLHA, vazada: false, apagada: false } : { cor: COR_NEUTRA, vazada: false, apagada: true };
    }
    case "ordem": {
      const posicao = item.ordem?.posicao ?? null;
      const dentro = posicao !== null && (p.primeiros === null || posicao <= p.primeiros);
      return dentro ? { cor: COR_BOLHA, vazada: false, apagada: false } : posicao === null ? vazia : { cor: COR_NEUTRA, vazada: false, apagada: true };
    }
    default:
      return { cor: COR_BOLHA, vazada: false, apagada: false };
  }
}

// ================================================================================================ régua (estado visual)
export type Corte = { minimo: number; maximo: number };
/** A régua filtra as unidades; conjuntos e membros da referência ficam sempre à vista. */
export const sujeitoARegua = (item: PainelItem) => item.tipo !== "conjunto" && !item.referencia;
/** Dentro do corte, com os limites incluídos. Sem corte, tudo aparece. */
export function noCorte(item: PainelItem, indicador: PainelIndicador, corte: Corte | null): boolean {
  if (!corte || !sujeitoARegua(item)) return true;
  const valor = valorDe(item, indicador);
  return valor !== null && valor >= corte.minimo && valor <= corte.maximo;
}
export const corteAtivo = (corte: Corte | null, dominio: PainelDominio | null) =>
  !!corte && !!dominio && (corte.minimo > dominio[0] || corte.maximo < dominio[1]);
/** Passo da régua: 1, 2 ou 5 × 10ⁿ perto de 1% do domínio; inteiro na contagem e de pelo menos 0,01 nas medidas contínuas. */
export function passoDaRegua(dominio: PainelDominio, contagem: boolean): number {
  const passo = passoBonito((dominio[1] - dominio[0]) / 100, [1, 2, 5, 10]);
  return contagem ? Math.max(1, Math.round(passo)) : Math.max(0.01, passo);
}
/** Valor de um cursor em número redondo; as pontas do domínio ficam exatas (todos à vista). */
export function ajustarValor(valor: number, dominio: PainelDominio, escala: Escala, contagem: boolean): number {
  const [a, b] = dominio;
  if (!(valor > a)) return a;
  if (!(valor < b)) return b;
  const passo = escala === "logaritmica" ? (contagem ? 1 : 0.01) : passoDaRegua(dominio, contagem);
  return Math.min(b, Math.max(a, limpo(Math.round(valor / passo) * passo)));
}
/** Um passo do cursor pelo teclado (setas: 1; Page Up/Down: 10), sempre saindo do valor atual quando há para onde ir. */
export function moverCursor(atual: number, sentido: 1 | -1, grande: boolean, dominio: PainelDominio, escala: Escala, contagem: boolean): number {
  const [a, b] = dominio, passos = grande ? 10 : 1;
  const minimo = escala === "logaritmica" ? (contagem ? 1 : 0.01) : passoDaRegua(dominio, contagem);
  const proximo = escala === "logaritmica" && a > 0
    ? (sentido > 0 ? Math.max(atual * 10 ** (passos / 50), atual + minimo) : Math.min(atual / 10 ** (passos / 50), atual - minimo))
    : atual + sentido * passos * minimo;
  const ajustado = ajustarValor(proximo, dominio, escala, contagem);
  if (ajustado !== atual || atual <= a || atual >= b) return ajustado;
  return ajustarValor(atual + sentido * minimo * 1.5, dominio, escala, contagem);
}

// ================================================================================================ arranjo (eixo único)
export type Capsula = { id: string; x0: number; x1: number; r: number };

/** Arranjo do eixo único, no eixo do valor: desloca cada bolha (ou cometa, do valor inicial ao atual) para o lado, o mínimo
 * possível a partir da linha central, sem sobreposição. O deslocamento não carrega valor. Determinístico. `x0`/`x1` são as
 * posições no eixo do valor (aqui, o vertical); a saída é o deslocamento perpendicular (aqui, o horizontal). */
export function arranjar(capsulas: Capsula[], folga = 1.5): Map<string, number> {
  const ordem = capsulas.map(capsula => ({ id: capsula.id, r: capsula.r, a: Math.min(capsula.x0, capsula.x1), b: Math.max(capsula.x0, capsula.x1) }))
    .sort((p, q) => p.a - q.a || q.r - p.r || comparar(p.id, q.id));
  const raioMaior = ordem.reduce((maior, item) => Math.max(maior, item.r), 0);
  let colocadas: { a: number; b: number; r: number; y: number }[] = [];
  const saida = new Map<string, number>();
  ordem.forEach((atual, indice) => {
    // Na ordem da posição, uma bolha já colocada que não alcança esta não alcança as seguintes: sai da conta.
    colocadas = colocadas.filter(outra => atual.a - outra.b < raioMaior + outra.r + folga);
    const lacuna = (outra: { a: number; b: number }) => Math.max(0, outra.a - atual.b, atual.a - outra.b);
    const vizinhas = colocadas.filter(outra => lacuna(outra) < atual.r + outra.r + folga);
    const candidatos = [0];
    for (const outra of vizinhas) {
      const alcance = atual.r + outra.r + folga, g = lacuna(outra), dy = Math.sqrt(alcance * alcance - g * g);
      candidatos.push(outra.y + dy, outra.y - dy);
    }
    const primeiroLado = indice % 2 === 0;  // alterna o lado nos empates, para o enxame ficar equilibrado
    candidatos.sort((u, v) => Math.abs(u) - Math.abs(v) || (primeiroLado ? u - v : v - u));
    const livre = candidatos.find(y => vizinhas.every(outra => {
      const alcance = atual.r + outra.r + folga, g = lacuna(outra);
      return Math.abs(y - outra.y) >= Math.sqrt(Math.max(0, alcance * alcance - g * g)) - 1e-6;
    }));
    const y = livre ?? 0;
    colocadas.push({ a: atual.a, b: atual.b, r: atual.r, y });
    saida.set(atual.id, y);
  });
  return saida;
}

/** Acima deste número de bolhas, o gráfico usa o modo leve: arranjo numa faixa limitada e desenho simplificado. */
export const LIMITE_LEVE = 400;

/** Arranjo do eixo único com muitas bolhas (modo leve): a mesma ideia de `arranjar`, numa faixa limitada (`meia` de cada lado
 * da linha central), com uma grade de ocupação de 2 px; sem lugar livre, fica o de menor sobreposição (as bolhas são
 * semitransparentes). As maiores entram primeiro. Determinístico. */
export function arranjarDenso(capsulas: Capsula[], meia: number, folga = 1): Map<string, number> {
  const CELULA = 2;
  const saida = new Map<string, number>();
  if (!capsulas.length) return saida;
  const ordem = capsulas.map(capsula => ({ id: capsula.id, r: capsula.r, a: Math.min(capsula.x0, capsula.x1), b: Math.max(capsula.x0, capsula.x1) }))
    .sort((p, q) => q.r - p.r || p.a - q.a || comparar(p.id, q.id));
  let menorX = Infinity, maiorX = -Infinity, raioMaior = 0;
  for (const item of ordem) {
    menorX = Math.min(menorX, item.a - item.r); maiorX = Math.max(maiorX, item.b + item.r); raioMaior = Math.max(raioMaior, item.r);
  }
  const origem = menorX - 2 * CELULA - folga;
  const colunas = Math.ceil((maiorX + 2 * CELULA + folga - origem) / CELULA) + 1;
  const centro = Math.max(Math.round(meia / CELULA), Math.ceil((raioMaior + folga) / CELULA));
  const linhas = 2 * centro + 1;
  const grade = new Uint16Array(colunas * linhas);
  ordem.forEach((item, indice) => {
    const metade = item.r + folga / 2, alcance = Math.ceil(metade / CELULA);
    const pegada: number[] = [];
    const c0 = Math.floor((item.a - metade - origem) / CELULA), c1 = Math.ceil((item.b + metade - origem) / CELULA);
    for (let coluna = c0; coluna <= c1; coluna++) {
      const xc = origem + (coluna + 0.5) * CELULA;
      const dx = xc < item.a ? item.a - xc : xc > item.b ? xc - item.b : 0;
      for (let linha = -alcance; linha <= alcance; linha++) {
        const dy = linha * CELULA;
        if (dx * dx + dy * dy <= metade * metade) pegada.push(coluna, linha);
      }
    }
    const limite = Math.max(0, centro - alcance), lado = indice % 2 === 0 ? 1 : -1;
    let melhor = 0, menor = Infinity;
    for (let passo = 0; passo <= 2 * limite; passo++) {
      const k = passo === 0 ? 0 : (passo % 2 === 1 ? lado : -lado) * Math.ceil(passo / 2);
      let ocupadas = 0;
      for (let i = 0; i < pegada.length && ocupadas < menor; i += 2) ocupadas += grade[(centro + k + pegada[i + 1]) * colunas + pegada[i]];
      if (ocupadas < menor) { menor = ocupadas; melhor = k; if (ocupadas === 0) break; }
    }
    for (let i = 0; i < pegada.length; i += 2) grade[(centro + melhor + pegada[i + 1]) * colunas + pegada[i]]++;
    saida.set(item.id, melhor * CELULA);
  });
  return saida;
}

// ================================================================================================ gráfico de bolhas
export type Vista = "final" | "inicial";
export type MarcaEixo = { valor: number; pos: number; texto: string };
export type EixoDesenho = { tipo: PainelIndicador | "distancia"; rotulo: string; dominio: PainelDominio; escala: Escala;
  de: number; ate: number; marcas: MarcaEixo[] };
export type BolhaDesenho = {
  id: string; tipo: PainelItem["tipo"]; item: PainelItem; x: number; y: number; r: number;
  /** Na vista da competência inicial, itens sem valor inicial não têm posição observada e ficam ocultos. */
  visivel: boolean;
  valor: number; inicial: number | null; variacao: number | null; referencia: boolean;
  /** Início do rastro (valor na competência inicial), relativo ao centro da bolha. */
  rastro: { dx: number; dy: number } | null;
  /** Conjunto com a distância à vista: do membro mais próximo (centro) ao mais distante, relativo ao centro. */
  faixa: { dx: number } | null;
  cor: string; vazada: boolean; apagada: boolean;
};
export type Grafico = { largura: number; altura: number; topo: number; base: number; esquerda: number; direita: number;
  eixoX: EixoDesenho | null; eixoY: EixoDesenho; bolhas: BolhaDesenho[]; raioMax: number; populacaoMaxima: number; escala: Escala;
  arranjo: "exato" | "leve" | "dados" };
export type ParametrosGrafico = {
  itens: PainelItem[]; dominios: PainelResposta["dominios"]; indicador: PainelIndicador; escala: Escala;
  /** Análise espacial: X = distância até a referência; sem ela, eixo único do indicador (Y). */
  distancia: boolean;
  /** Cometa da competência inicial à atual (Mudança e Classes). */
  cometa: boolean;
  vista: Vista; largura: number; rotuloDistancia: string;
  pintura: (item: PainelItem) => Pintura;
  /** Valores que o eixo precisa mostrar além dos itens (a linha de contexto do Brasil). */
  extras?: number[];
  /** Modo leve (muitas bolhas): arranjo numa faixa limitada (`arranjarDenso`). */
  denso?: boolean;
};

const entre = (t: number, inicio: number, fim: number) => inicio + (fim - inicio) * t;
export const posicaoNoEixo = (eixo: EixoDesenho, valor: number) => entre(fracao(valor, eixo.dominio, eixo.escala), eixo.de, eixo.ate);

/** Desenho no estado escolhido. O eixo Y é sempre o indicador. Sem distância, as bolhas se espalham na horizontal só como
 * arranjo (exato até LIMITE_LEVE, leve acima). Com distância, X = distância até a referência. Tamanho = população (área
 * proporcional). O cometa liga só os dois valores observados da mesma unidade (inicial e atual): sem reta de ajuste. */
export function montarGrafico(p: ParametrosGrafico): Grafico {
  const largura = Math.max(280, Math.round(p.largura));
  const raioMax = raioMaximo(largura);
  const dominioDo = (chave: string): PainelDominio | null => {
    const dominio = p.dominios[chave];
    return dominio && Number.isFinite(dominio[0]) && Number.isFinite(dominio[1]) ? dominio : null;
  };
  // Só com a variação do motor: sem ela (base zero, sem registro inicial, conjunto incomparável), não há rastro (RQ-REP-15).
  const comRastro = (item: PainelItem) => p.cometa && variacaoDe(item, p.indicador) !== null && inicialDe(item, p.indicador) !== null;
  const valores = [...(dominioDo(p.indicador) || p.itens.map(item => valorDe(item, p.indicador)).filter(ehNumero)),
    ...p.itens.filter(comRastro).map(item => inicialDe(item, p.indicador)).filter(ehNumero), ...(p.extras || [])];
  const escala = escalaPossivel(valores, p.escala);
  const dominioIndicador = enquadrar(valores, escala);
  const populacoes = [...(dominioDo("populacao") ? [dominioDo("populacao")![1]] : p.itens.map(item => numero(item.populacao)).filter(ehNumero)),
    ...(p.cometa ? p.itens.map(item => inicialDe(item, "populacao")).filter(ehNumero) : [])];
  const populacaoMaxima = populacoes.length ? Math.max(...populacoes) : 0;
  const esquerda = 64, direita = 18, topo = 14;
  const folga = Math.max(8, Math.round(raioMax * 0.6));
  const naVistaInicial = p.cometa && p.vista === "inicial";
  const especie = INDICADORES[p.indicador];

  const base = p.itens.map(item => {
    const valor = valorDe(item, p.indicador) as number;
    const inicial = comRastro(item) ? inicialDe(item, p.indicador) : null;
    const rFinal = raioDaPopulacao(item.populacao, populacaoMaxima, raioMax);
    const rInicial = inicial !== null ? raioDaPopulacao(inicialDe(item, "populacao") ?? item.populacao, populacaoMaxima, raioMax) : rFinal;
    return { item, valor, inicial, variacao: variacaoDe(item, p.indicador), rFinal, rInicial, pintura: p.pintura(item),
      visivel: !naVistaInicial || inicial !== null };
  });
  const eixoIndicador = (baixo: number, alto: number): EixoDesenho => ({ tipo: p.indicador, rotulo: especie.eixo, dominio: dominioIndicador,
    escala, de: baixo, ate: alto, marcas: marcas(dominioIndicador, escala).map(valor => ({ valor,
      pos: entre(fracao(valor, dominioIndicador, escala), baixo, alto), texto: textoDaMarca(valor) })) });
  const bolha = (d: typeof base[number], x: number, yFinal: number, yInicial: number | null, xInicial: number | null): BolhaDesenho => {
    const naInicial = naVistaInicial && yInicial !== null;
    const dx = xInicial !== null ? xInicial - x : 0, dy = yInicial !== null ? yInicial - yFinal : 0;
    return { id: d.item.id, tipo: d.item.tipo, item: d.item, x: naInicial && xInicial !== null ? xInicial : x, y: naInicial ? yInicial! : yFinal,
      r: naInicial ? d.rInicial : d.rFinal, visivel: d.visivel, valor: d.valor, inicial: d.inicial, variacao: d.variacao,
      referencia: !!d.item.referencia, rastro: !naVistaInicial && yInicial !== null && Math.hypot(dx, dy) >= 1 ? { dx, dy } : null,
      faixa: null, cor: d.pintura.cor, vazada: d.pintura.vazada, apagada: d.pintura.apagada };
  };

  if (!p.distancia) {
    const rodape = 12, meia = Math.max(60, (largura - esquerda - direita) / 2 - 6), centroX = esquerda + (largura - esquerda - direita) / 2;
    let alturaPlot = Math.round(Math.min(520, Math.max(300, largura * 0.52)));
    let arranjo: Map<string, number> = new Map(), modo: Grafico["arranjo"] = p.denso ? "leve" : "exato";
    let y = (valor: number) => valor;
    for (let tentativa = 0; tentativa < 3; tentativa++) {
      const baixo = topo + alturaPlot - folga, alto = topo + folga;
      y = (valor: number) => entre(fracao(valor, dominioIndicador, escala), baixo, alto);
      const capsulas = base.map(d => ({ id: d.item.id, x0: d.inicial !== null ? y(d.inicial) : y(d.valor), x1: y(d.valor),
        r: Math.max(d.rFinal, d.rInicial) }));
      if (p.denso) { arranjo = arranjarDenso(capsulas, Math.min(420, meia)); break; }
      arranjo = arranjar(capsulas);
      const extensao = base.reduce((maior, d) => Math.max(maior, Math.abs(arranjo.get(d.item.id) ?? 0) + Math.max(d.rFinal, d.rInicial)), 0);
      if (extensao <= meia) break;
      if (tentativa < 2) { alturaPlot = Math.min(900, Math.round(alturaPlot * 1.45)); continue; }
      // Não coube nem com o eixo mais alto: o arranjo leve, preso à largura (pode haver sobreposição, dita na nota).
      arranjo = arranjarDenso(capsulas, Math.min(420, meia)); modo = "leve";
    }
    const baixo = topo + alturaPlot - folga, alto = topo + folga;
    const bolhas = base.map(d => {
      const r = Math.max(d.rFinal, d.rInicial);
      const x = Math.min(largura - direita - r, Math.max(esquerda + r, centroX + (arranjo.get(d.item.id) ?? 0)));
      return bolha(d, x, y(d.valor), d.inicial !== null ? y(d.inicial) : null, d.inicial !== null ? x : null);
    });
    return { largura, altura: topo + alturaPlot + rodape, topo, base: topo + alturaPlot, esquerda, direita, eixoX: null,
      eixoY: eixoIndicador(baixo, alto), bolhas, raioMax, populacaoMaxima, escala, arranjo: modo };
  }

  const rodape = 50;
  const distancias = [0, ...(dominioDo("distancia_km") || []), ...p.itens.map(item => numero(item.distancia_km)).filter(ehNumero),
    ...p.itens.map(item => numero(item.distancia_km_max)).filter(ehNumero)];
  const dominioDistancia = enquadrar(distancias, "linear");
  const alturaPlot = Math.round(Math.min(540, Math.max(300, largura * 0.5)));
  const de = esquerda + folga, ateX = largura - direita - folga;
  const baixoY = topo + alturaPlot - folga, altoY = topo + folga;
  const x = (valor: number) => entre(fracao(valor, dominioDistancia, "linear"), de, ateX);
  const y = (valor: number) => entre(fracao(valor, dominioIndicador, escala), baixoY, altoY);
  const bolhas = base.map(d => {
    const distancia = numero(d.item.distancia_km) ?? 0, maxima = numero(d.item.distancia_km_max);
    const bx = x(distancia);
    const desenho = bolha(d, bx, y(d.valor), d.inicial !== null ? y(d.inicial) : null, d.inicial !== null ? bx : null);
    return { ...desenho, faixa: d.item.tipo === "conjunto" && maxima !== null && maxima > distancia ? { dx: x(maxima) - bx } : null };
  });
  const eixoX: EixoDesenho = { tipo: "distancia", rotulo: p.rotuloDistancia, dominio: dominioDistancia, escala: "linear", de, ate: ateX,
    marcas: marcas(dominioDistancia, "linear").map(valor => ({ valor, pos: x(valor), texto: textoDaMarca(valor) })) };
  return { largura, altura: topo + alturaPlot + rodape, topo, base: topo + alturaPlot, esquerda, direita, eixoX,
    eixoY: eixoIndicador(baixoY, altoY), bolhas, raioMax, populacaoMaxima, escala, arranjo: "dados" };
}

/** Cauda do cometa: triângulo do ponto da competência inicial (fino) até a bolha, em coordenadas relativas ao centro. */
export function caudaDoCometa(dx: number, dy: number, r: number): string {
  const comprimento = Math.hypot(dx, dy);
  if (comprimento < 1) return "";
  const meia = Math.min(r * 0.7, 6);
  const px = -dy / comprimento * meia, py = dx / comprimento * meia;
  const f = (valor: number) => String(Math.round(valor * 100) / 100);
  return f(dx) + "," + f(dy) + " " + f(px) + "," + f(py) + " " + f(-px) + "," + f(-py);
}

export type Rotulo2 = { dx: number; dy: number; ancora: "start" | "end" };
/** Rótulos diretos seletivos: à direita da bolha (à esquerda perto da borda), deslocados na vertical quando colidem. */
export function posicionarRotulos(itens: { id: string; x: number; y: number; r: number; largura: number }[], limite: number,
  altura = 15): Map<string, Rotulo2> {
  const ocupados: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const saida = new Map<string, Rotulo2>();
  for (const item of [...itens].sort((a, b) => a.y - b.y || a.x - b.x || comparar(a.id, b.id))) {
    const direita = item.x + item.r + 6 + item.largura <= limite;
    const x0 = direita ? item.x + item.r + 6 : item.x - item.r - 6 - item.largura, x1 = x0 + item.largura;
    const deslocamentos = [0, altura, -altura, 2 * altura, -2 * altura, 3 * altura, -3 * altura];
    const dy = deslocamentos.find(desvio => !ocupados.some(caixa => x0 < caixa.x1 && x1 > caixa.x0 &&
      item.y + desvio - altura / 2 < caixa.y1 && item.y + desvio + altura / 2 > caixa.y0)) ?? 0;
    ocupados.push({ x0, x1, y0: item.y + dy - altura / 2, y1: item.y + dy + altura / 2 });
    saida.set(item.id, { dx: direita ? item.r + 6 : -(item.r + 6), dy, ancora: direita ? "start" : "end" });
  }
  return saida;
}
/** Largura aproximada de um texto de 12 px (Inter), só para afastar rótulos. */
export const larguraDoTexto = (texto: string, tamanho = 12) => Math.ceil(texto.length * tamanho * 0.56) + 4;

// ================================================================================================ tendência: séries e velocidades
/** Posição no tempo de cada competência: meses desde a primeira (AAAAMM; janeiro e junho ficam a 5 e 7 meses, como são) ou a
 * ordem, para outros formatos. Só posiciona. */
export function posicoesTemporais(competencias: string[]): Map<string, number> {
  const ordenadas = [...new Set(competencias)].sort(comparar);
  const saida = new Map<string, number>();
  if (ordenadas.length && ordenadas.every(ehAaaamm)) {
    const meses = (c: string) => Number(c.slice(0, 4)) * 12 + Number(c.slice(4)) - 1;
    const inicio = meses(ordenadas[0]);
    for (const c of ordenadas) saida.set(c, meses(c) - inicio);
  } else ordenadas.forEach((c, indice) => saida.set(c, indice));
  return saida;
}
/** Domínio das séries: os valores observados do motor, enquadrados (só para desenhar). */
export function dominioDasSeries(itens: PainelItem[]): PainelDominio {
  const valores = itens.flatMap(item => (item.tendencia?.observacoes || []).map(obs => obs.valor)).filter(ehNumero);
  return enquadrar(valores, "linear");
}
export type PontoSerie = { competencia: string; x: number; y: number; valor: number };
export type SerieDesenho = { id: string; rotulo: string; cor: string; familia: FamiliaTendencia | null; classe: string;
  pontos: PontoSerie[]; caminhos: string[]; fim: PontoSerie | null };
/** Linhas por competência: um ponto por observação; lacunas não são ligadas (sem imputar), sem reta ajustada. */
export function montarSeries(p: { itens: PainelItem[]; janela: string[]; dominio: PainelDominio; x0: number; x1: number; y0: number; y1: number }):
  { series: SerieDesenho[]; marcasX: { competencia: string; x: number }[] } {
  const tempos = posicoesTemporais(p.janela);
  const maximo = Math.max(1, ...tempos.values());
  const x = (c: string) => p.x0 + (p.x1 - p.x0) * ((tempos.get(c) ?? 0) / maximo);
  const y = (valor: number) => entre(fracao(valor, p.dominio, "linear"), p.y1, p.y0);
  const series = p.itens.map(item => {
    const tendencia = item.tendencia;
    const familia = tendencia?.avaliavel ? tendencia.familia ?? familiaDaClasse(tendencia.classe) : null;
    const porCompetencia = new Map((tendencia?.observacoes || []).map(obs => [obs.competencia, obs.valor]));
    const pontos: PontoSerie[] = [], caminhos: string[] = [];
    let atual: PontoSerie[] = [];
    for (const competencia of [...tempos.keys()]) {
      const valor = porCompetencia.get(competencia);
      if (valor === null || valor === undefined) { if (atual.length > 1) caminhos.push(caminho(atual)); atual = []; continue; }
      const ponto = { competencia, x: x(competencia), y: y(valor), valor };
      pontos.push(ponto); atual.push(ponto);
    }
    if (atual.length > 1) caminhos.push(caminho(atual));
    return { id: item.id, rotulo: item.rotulo, cor: familia ? CORES_TENDENCIA[familia] : COR_NAO_AVALIAVEL, familia,
      classe: tendencia?.rotulo || "Não avaliável", pontos, caminhos, fim: pontos.at(-1) ?? null };
  });
  return { series, marcasX: [...tempos.keys()].map(c => ({ competencia: c, x: x(c) })) };
}
const caminho = (pontos: PontoSerie[]) => pontos.map((ponto, i) => (i ? "L" : "M") + ponto.x.toFixed(1) + " " + ponto.y.toFixed(1)).join(" ");

export type BarraVelocidade = { x: number; y: number; largura: number; altura: number; sinal: -1 | 0 | 1 };
/** Barras das velocidades do motor a partir do zero (mapeamento visual): escala pela maior magnitude; zero vira um traço. */
export function barrasDeVelocidade(valores: number[], largura: number, altura: number, margem = 2): { base: number; barras: BarraVelocidade[] } {
  if (!valores.length) return { base: altura / 2, barras: [] };
  const maior = Math.max(...valores.map(Math.abs)) || 1;
  const positivas = valores.every(valor => valor >= 0), negativas = valores.every(valor => valor <= 0);
  const base = positivas ? altura - margem : negativas ? margem : altura / 2;
  const espaco = positivas || negativas ? altura - margem * 2 : altura / 2 - margem;
  const passo = (largura - margem * 2) / valores.length, larguraBarra = Math.max(2, Math.min(24, passo - 4));
  return { base, barras: valores.map((valor, indice) => {
    const tamanho = valor === 0 ? 2 : Math.max(1, Math.abs(valor) / maior * espaco);
    const sinal = valor > 0 ? 1 : valor < 0 ? -1 : 0;
    return { x: margem + indice * passo + (passo - larguraBarra) / 2, largura: larguraBarra, sinal, altura: tamanho,
      y: sinal > 0 ? base - tamanho : sinal < 0 ? base : base - 1 };
  }) };
}

/** Janela: atalhos (decisão 5a do responsável: a pessoa escolhe; sem janela padrão). */
export type AtalhoJanela = "ultimos4junhos" | "anualjunho" | "todas";
export const ATALHOS_JANELA: Record<AtalhoJanela, string> = { ultimos4junhos: "Últimos 4 junhos", anualjunho: "Série anual de junho",
  todas: "Todas as competências" };
export function janelaDoAtalho(atalho: AtalhoJanela, periodos: string[]): string[] {
  const ordenadas = cronologica(periodos);
  const junhos = ordenadas.filter(c => ehAaaamm(c) && c.endsWith("06"));
  if (atalho === "ultimos4junhos") return junhos.length >= 4 ? junhos.slice(-4) : [];
  if (atalho === "anualjunho") return junhos.length >= 2 ? junhos : [];
  return ordenadas;
}
/** CAP-TEN-01 exige ao menos quatro competências; a mudança (CAP-TMP-01), duas. */
export const MINIMO_TENDENCIA = 4;
export const TEXTO_MINIMO_TENDENCIA = "A análise de tendência exige quatro observações válidas.";

// ================================================================================================ dica
export type LinhaDica = { rotulo: string; valor: string };
export type Dica = { titulo: string; subtitulo: string; linhas: LinhaDica[]; notas: string[]; acao: string | null };
export type ContextoDica = { indicador: PainelIndicador; competencia: string; competenciaInicial: string | null; distancia: boolean;
  variacao: boolean; tendencia: boolean; nomes: Map<string, string>; limiares?: number[]; rotulos: RotulosTerritoriais;
  /** Unidades de um grupo (para a ação "Ver os N municípios" na bolha do grupo). */
  unidadesDoGrupo?: (id: string) => number | null };

/** Conteúdo da dica (ao passar o mouse e ao focar), só com valores do motor; o valor vem primeiro, o rótulo depois. */
export function montarDica(item: PainelItem, contexto: ContextoDica): Dica {
  const conjunto = item.tipo === "conjunto", grupo = item.tipo === "estado";
  const limiares = (indicador: PainelIndicador) => contexto.indicador === indicador ? contexto.limiares || [] : [];
  const populacao = numero(item.populacao), quantidade = numero(item.quantidade);
  const linhas: LinhaDica[] = [
    { rotulo: conjunto ? "População (soma dos membros)" : "População", valor: populacao === null ? "Não avaliável" : formatarNumero(populacao, true) + " habitantes" },
    { rotulo: conjunto ? "Profissionais (soma das contagens dos componentes)" : "Profissionais",
      valor: quantidade === null ? "Não avaliável" : formatarNumero(quantidade, true, limiares("quantidade")) },
    { rotulo: "Densidade", valor: formatarIndicador(valorDe(item, "densidade"), "densidade", limiares("densidade")) },
  ];
  const notas: string[] = [];
  if (contexto.distancia) {
    const distancia = numero(item.distancia_km), maxima = numero(item.distancia_km_max);
    linhas.push({ rotulo: item.referencia ? "Distância (membro da referência)" : conjunto ? "Distância (membro mais próximo)" : "Distância até a referência",
      valor: distancia === null ? "Não avaliável" : formatarNumero(distancia) + " km" });
    if (conjunto && maxima !== null) linhas.push({ rotulo: "Distância (membro mais distante)", valor: formatarNumero(maxima) + " km" });
    if (item.referencia_mais_proxima?.length && !item.referencia)
      linhas.push({ rotulo: item.referencia_mais_proxima.length > 1 ? "Membros da referência mais próximos (empate)" : "Membro da referência mais próximo",
        valor: item.referencia_mais_proxima.map(ref => ref.rotulo).join(", ") });
    if (item.faixa_distancia) linhas.push({ rotulo: "Faixa de distância", valor: item.faixa_distancia === "fora" ? "fora das faixas" : item.faixa_distancia.rotulo });
    if (distancia === null) notas.push(...motivosDe(item, "distancia").slice(0, 1));
  }
  if (contexto.variacao) {
    const desde = exibirCompetencia(contexto.competenciaInicial);
    const especie = INDICADORES[contexto.indicador];
    const variacao = variacaoDe(item, contexto.indicador), inicial = inicialDe(item, contexto.indicador);
    linhas.push({ rotulo: "Variação da " + especie.rotulo.toLowerCase() + (desde ? " desde " + desde : "") + " (" + direcaoDaVariacao(variacao) + ")",
      valor: formatarVariacao(variacao) });
    if (inicial !== null) linhas.push({ rotulo: especie.rotulo + (desde ? " em " + desde : " na competência inicial"),
      valor: formatarIndicador(inicial, contexto.indicador) });
    if (variacao === null) notas.push(motivosDe(item, "variacao")[0] || MOTIVO_PADRAO.variacao(contexto.indicador));
  }
  if (contexto.tendencia && item.tendencia) {
    linhas.push({ rotulo: "Classe de tendência", valor: item.tendencia.rotulo });
    if (item.tendencia.motivo) notas.push(item.tendencia.motivo);
  }
  if (item.grupo) linhas.push({ rotulo: "Grupo por posição", valor: item.grupo.rotulo });
  if (item.faixa) linhas.push({ rotulo: "Faixa", valor: item.faixa === "fora" ? "fora das faixas" : item.faixa.rotulo });
  if (item.condicoes) linhas.push({ rotulo: "Condições", valor: item.condicoes.situacao === "ATENDE" ? "atende a todas"
    : item.condicoes.situacao === "NAO_ATENDE" ? "não atende" : "sem dado para avaliar" });
  if (item.ordem && item.ordem.posicao !== null) linhas.push({ rotulo: "Posição na ordenação", valor: item.ordem.posicao + "º" });
  // Rotatividade no mapa (a dica do ponto): a permanência e a coorte inicial do motor, sempre "da coorte inicial".
  if (item.rotatividade) {
    const r = item.rotatividade;
    linhas.push({ rotulo: "Permanência da coorte inicial", valor: formatarPercentual(r.permanencia) },
      { rotulo: "Coorte inicial", valor: r.coorteInicial === null ? "Não avaliável" : formatarNumero(r.coorteInicial, true) });
    if (!r.avaliavel && r.motivo) notas.push(r.motivo);
  }
  notas.push(...avisosDe(item));
  if (conjunto) {
    notas.push(NOTA_SOMA);
    const membros = (item.membros || []).map(id => contexto.nomes.get(id) || id);
    if (membros.length) notas.push("Membros: " + membros.join(", ") + ".");
  }
  if (item.referencia) notas.push("Membro da referência da distância.");
  const unidade = contexto.rotulos.unidade, grupoRotulo = contexto.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const n = grupo ? contexto.unidadesDoGrupo?.(item.id) ?? null : null;
  return {
    titulo: item.rotulo,
    subtitulo: conjunto ? "Conjunto de " + unidade.plural + " · " + textoDaContagem(item.contagem)
      : [maiuscula(grupo ? grupoRotulo.singular : unidade.singular), grupo ? "" : item.uf || ""].filter(Boolean).join(" · "),
    linhas, notas: [...new Set(notas)],
    acao: grupo ? (n !== null ? textoVerUnidades(contexto.rotulos, n) : "Ver " + artigo(unidade, true) + " " + unidade.plural) : null,
  };
}

// ================================================================================================ tabela
export type ColunaTabela = "territorio" | "populacao" | "quantidade" | "densidade" | "distancia" | "variacao" | "classe" | "grupo" |
  "faixa" | "condicao" | "posicao" | "coorte" | "permanencia";
export type Ordenacao = { coluna: ColunaTabela; sentido: "asc" | "desc" } | null;
/** Linhas da tabela: na ordem neutra ou, quando a pessoa clica num cabeçalho, pela coluna escolhida (estado visual, sem
 * posições; sem valor, no fim). */
export function ordenarTabela(itens: PainelItem[], ordenacao: Ordenacao, indicador: PainelIndicador): PainelItem[] {
  const neutra = [...itens].sort(ordemNeutra);
  if (!ordenacao) return neutra;
  const { coluna, sentido } = ordenacao;
  const chave = (item: PainelItem): number | string | null => {
    switch (coluna) {
      case "territorio": return item.rotulo;
      case "populacao": return numero(item.populacao);
      case "quantidade": return numero(item.quantidade);
      case "densidade": return numero(item.densidade);
      case "distancia": return numero(item.distancia_km);
      case "variacao": return variacaoDe(item, indicador);
      case "classe": return item.tendencia?.avaliavel ? item.tendencia.rotulo : null;
      case "grupo": return item.grupo?.indice ?? null;
      case "faixa": return item.faixa && item.faixa !== "fora" ? item.faixa.indice : null;
      case "condicao": return item.condicoes ? ["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"].indexOf(item.condicoes.situacao) : null;
      case "posicao": return item.ordem?.posicao ?? null;
      case "coorte": return item.rotatividade?.coorteInicial ?? null;
      case "permanencia": return item.rotatividade?.permanencia ?? null;
      default: return null;
    }
  };
  return neutra.sort((a, b) => {
    const va = chave(a), vb = chave(b);
    if (va === null || vb === null) return va === vb ? 0 : va === null ? 1 : -1;
    const diferenca = typeof va === "number" && typeof vb === "number" ? va - vb : comparar(String(va), String(vb));
    return sentido === "asc" ? diferenca : -diferenca;
  });
}
/** Linhas por página da tabela (com milhares de unidades, a tabela inteira pesaria na tela). */
export const POR_PAGINA = 100;
export function paginar<T>(linhas: T[], pagina: number, porPagina = POR_PAGINA): { linhas: T[]; pagina: number; paginas: number } {
  const paginas = Math.max(1, Math.ceil(linhas.length / porPagina)), atual = Math.min(Math.max(0, pagina), paginas - 1);
  return { linhas: linhas.slice(atual * porPagina, (atual + 1) * porPagina), pagina: atual, paginas };
}

// ================================================================================================ referência e competências
/** "Usar o primeiro" (CAP-SUB-03): os candidatos na 1ª posição do motor. Mais de um é empate, e a tela pede a escolha. */
export const primeirosColocados = (candidatos: ReferenciaCandidato[]) => candidatos.filter(candidato => candidato.posicao === 1);
export const cronologica = (valores: string[]) => [...new Set(valores)].sort(comparar);
export const maisRecente = (periodos: string[]) => cronologica(periodos).at(-1) ?? "";
export const anteriores = (periodos: string[], competencia: string) => cronologica(periodos).filter(periodo => comparar(periodo, competencia) < 0);
/** Limites digitados pela pessoa ("0; 1,5; 2" ou "0 1.5 2"): números distintos, em ordem crescente. */
export function lerLimites(texto: string): number[] {
  const partes = texto.split(/[;\s]+/).map(parte => parte.trim()).filter(Boolean)
    .map(parte => Number(/,/.test(parte) ? parte.replace(/\./g, "").replace(",", ".") : parte));
  return [...new Set(partes.filter(valor => Number.isFinite(valor)))].sort((a, b) => a - b);
}
export const escreverLimites = (limites: number[]) => limites.map(valor => ate(6).format(valor)).join("; ");

// ================================================================================================ definição, pedido e contexto
export type Agrupar = { tipo: "nenhum" | TipoGrupos | "faixas"; faixas: number[] };
/** Tudo o que a pessoa escolheu e que vai ao motor (o que é só estado visual fica no componente). */
export type DefinicaoAnalise = {
  familia: Familia; indicador: PainelIndicador; nivel: PainelNivel; base: PainelMunicipios; competencia: string; categoria: string;
  conjuntos: PainelConjuntoPedido[]; referencia: PainelReferenciaPedido | null; faixasDistancia: number[];
  janela: string[]; visao: Visao; agrupar: Agrupar; condicoes: CondicaoPedido[]; ordenar: OrdenarPedido | null;
  comparar: string[]; rotatividade: { inicial: string; final: string } | null; premissas: Premissas;
};
/** Abertura: base do Brasil com os grupos à vista (E1, os estados em bolhas); planilha com o gráfico limpo, à espera da escolha. */
/** Estado inicial da análise. Na base do Brasil, a porta de entrada são os estados; na planilha, que não tem bolhas de
 * grupo, todas as unidades (a lista continua à vista para restringir). Na planilha sem população, o indicador começa na
 * quantidade (o motor recusa a densidade sem população), e as premissas escolhidas no painel Colunas vão em todo pedido. */
export function definicaoInicial(p: { tipo: "brasil" | "arquivo" | null; periodos: string[]; categoria: string; familia?: Familia;
  temGrupos: boolean; temPopulacao?: boolean; premissas?: Premissas }): DefinicaoAnalise {
  return { familia: p.familia ?? "distribuicao", indicador: p.temPopulacao === false ? "quantidade" : "densidade",
    nivel: p.tipo === "brasil" && p.temGrupos ? "estados" : "municipios",
    base: p.tipo === "arquivo" ? { todos: true, estados: [], ids: [] } : { ...BASE_VAZIA }, competencia: maisRecente(p.periodos),
    categoria: p.categoria, conjuntos: [], referencia: null, faixasDistancia: [],
    janela: [], visao: "classes", agrupar: { tipo: "nenhum", faixas: [] }, condicoes: [], ordenar: null, comparar: [], rotatividade: null,
    premissas: p.tipo === "arquivo" ? { ...(p.premissas ?? {}) } : {} };
}

export const tendenciaPossivel = (def: DefinicaoAnalise) => def.janela.length >= MINIMO_TENDENCIA;
/** Visão da tendência que de fato aparece: Classes e Séries só com quatro competências ou mais; senão, a Mudança. */
export const visaoEfetiva = (def: DefinicaoAnalise): Visao => def.visao !== "mudanca" && !tendenciaPossivel(def) ? "mudanca" : def.visao;

/** O que impede o pedido ao motor (null quando ele pode sair): sem dados, sem competência ou sem nenhuma unidade marcada. */
export function bloqueioDoPedido(def: DefinicaoAnalise, c: { fonte: "brasil" | "arquivo" | null; rotulos: RotulosTerritoriais }): string | null {
  if (!c.fonte) return "Escolha os dados para começar.";
  if (!def.competencia) return "Escolha a competência.";
  const unidade = c.rotulos.unidade;
  if (def.nivel === "municipios" && baseVazia(def.base) && !def.conjuntos.length)
    return "Marque " + artigo(unidade, true) + " " + unidade.plural + " na lista de territórios para ver o gráfico.";
  return null;
}
/** O que falta para a família escolhida aparecer (o gráfico continua com a distribuição enquanto isso). */
export function avisoDaFamilia(def: DefinicaoAnalise, disponivel: Disponivel): string | null {
  if (!disponivel.disponivel || disponivel.pendente) return def.familia === "distribuicao" ? null : disponivel.motivo || null;
  if (def.nivel === "estados") return null;
  if (def.familia === "tendencia" && def.janela.length < 2)
    return "Escolha a janela da tendência: últimos 4 junhos, série anual de junho, todas as competências ou outra.";
  if (def.familia === "tendencia" && def.visao !== "mudanca" && def.janela.length < MINIMO_TENDENCIA)
    return TEXTO_MINIMO_TENDENCIA + " Com " + def.janela.length + " competências, aparece a mudança entre a primeira e a última.";
  if (def.familia === "rotatividade" && (!def.rotatividade?.inicial || !def.rotatividade?.final))
    return "Escolha os períodos inicial e final da coorte.";
  if (def.familia === "espacial" && !def.referencia) return "Escolha a referência da distância: por critério ou pelo nome.";
  return null;
}

/** Família que o pedido de fato calcula: a escolhida quando disponível e possível no nível; senão, a distribuição. */
export function familiaCalculada(def: DefinicaoAnalise, disponivel: boolean): Familia {
  if (!disponivel || def.nivel === "estados") return "distribuicao";
  if (def.familia === "espacial" && !def.referencia) return "distribuicao";
  if (def.familia === "tendencia" && def.janela.length < 2) return "distribuicao";
  if (def.familia === "rotatividade" && (!def.rotatividade?.inicial || !def.rotatividade?.final)) return "distribuicao";
  return def.familia;
}

/** Opções de /api/painel com as chaves do contrato (seção 3), só as que o estado pede. */
export function montarOpcoes(def: DefinicaoAnalise, familia: Familia, grupoDe: (id: string) => string = prefixoDe): PainelOpcoes {
  const tendencia = familia === "tendencia";
  const competencia = tendencia ? def.janela.at(-1) ?? def.competencia
    : familia === "rotatividade" && def.rotatividade ? def.rotatividade.final : def.competencia;
  const opcoes: PainelOpcoes = { competencia, categoria: def.categoria, nivel: def.nivel, indicador: def.indicador };
  if (def.nivel !== "estados") {
    opcoes.base = { municipios: normalizarBase(def.base, grupoDe) };
    if (def.conjuntos.length) opcoes.conjuntos = def.conjuntos;
    if (familia === "espacial" && def.referencia) {
      opcoes.referencia = def.referencia;
      if (def.faixasDistancia.length >= 2) opcoes.faixas_distancia = def.faixasDistancia;
    }
    // A visão (Mudança, Classes ou Séries) é só estado visual: com quatro competências ou mais, a tendência vai junto e a troca
    // de visão não pede nada novo ao motor.
    if (tendencia && def.janela.length >= 2) {
      opcoes.competencia_inicial = def.janela[0];
      if (def.janela.length >= MINIMO_TENDENCIA) opcoes.tendencia = { competencias: def.janela };
    }
    if (familia === "rotatividade" && def.rotatividade) opcoes.rotatividade = def.rotatividade;
  }
  if (familia === "distribuicao" && def.agrupar.tipo !== "nenhum") {
    if (def.agrupar.tipo === "faixas") { if (def.agrupar.faixas.length >= 2) opcoes.faixas = def.agrupar.faixas; }
    else opcoes.grupos = { tipo: def.agrupar.tipo };
  }
  if (familia !== "rotatividade") {
    if (def.condicoes.length) opcoes.condicoes = def.condicoes.filter(c => c.atributo !== "distancia_km" || familia === "espacial");
    if (!opcoes.condicoes?.length) delete opcoes.condicoes;
    if (def.ordenar && (def.ordenar.atributo !== "distancia_km" || familia === "espacial") && (def.ordenar.atributo !== "variacao" || tendencia))
      opcoes.ordenar = def.ordenar;
    if (def.comparar.length >= 2 && def.comparar.length <= 3) opcoes.comparar = def.comparar;
  }
  if (Object.keys(def.premissas).length) opcoes.premissas = def.premissas;
  return opcoes;
}

/** O indicador muda a resposta do motor? Só com grupos, faixas, tendência, comparação ou ordenação pela variação; nos demais
 * pedidos, cada item traz população, quantidade e densidade, e o indicador é só estado visual. */
export const pedidoDependeDoIndicador = (opcoes: PainelOpcoes) =>
  !!(opcoes.grupos || opcoes.faixas || opcoes.tendencia || opcoes.comparar || opcoes.ordenar?.atributo === "variacao");

/** Chave do pedido na memória da tela: sem dependência do indicador, ele fica de fora, e a troca não pede nada ao motor. O
 * pedido enviado continua com o indicador em exibição. */
export function chaveDoPedido(opcoes: PainelOpcoes): string {
  const { indicador, ...resto } = opcoes;
  return JSON.stringify(pedidoDependeDoIndicador(opcoes) ? opcoes : resto);
}

/** Camada de cor em uso (uma de cada vez): condições, depois ordenação, depois a da família. */
export function camadaDeCor(familia: Familia, visao: Visao, resposta: PainelResposta | null, def: DefinicaoAnalise): CamadaDeCor {
  if (!resposta) return "unica";
  if (resposta.condicoes && def.condicoes.length) return "condicoes";
  if (resposta.ordenacao && def.ordenar) return "ordem";
  if (familia === "tendencia") return visao === "mudanca" ? "variacao" : "classes";
  if (familia === "distribuicao" && resposta.grupos && def.agrupar.tipo !== "nenhum" && def.agrupar.tipo !== "faixas") return "grupos";
  if (familia === "distribuicao" && resposta.faixas && def.agrupar.tipo === "faixas") return "faixas";
  return "unica";
}

const FAMILIAS_VALIDAS = new Set<string>(FAMILIAS);
const ATRIBUTOS_ORDENAR = new Set<string>(["densidade", "quantidade", "populacao", "distancia_km", "variacao"]);
const ATRIBUTOS_CONDICAO = new Set<string>(["densidade", "quantidade", "populacao", "distancia_km"]);
const OPERADORES_VALIDOS = new Set<string>(["<", "<=", ">", ">="]);
function lerOrdenar(bruto: unknown): OrdenarPedido | null {
  const o = bruto && typeof bruto === "object" ? bruto as Record<string, unknown> : null;
  if (!o || typeof o.atributo !== "string" || !ATRIBUTOS_ORDENAR.has(o.atributo) || (o.ordem !== "desc" && o.ordem !== "asc")) return null;
  const primeiros = typeof o.primeiros === "number" && Number.isInteger(o.primeiros) && o.primeiros > 0 ? o.primeiros : undefined;
  return { atributo: o.atributo as AtributoOrdenacao, ordem: o.ordem, ...(primeiros ? { primeiros } : {}) };
}
function lerCondicao(bruto: unknown): CondicaoPedido | null {
  const o = bruto && typeof bruto === "object" ? bruto as Record<string, unknown> : null;
  if (!o || typeof o.atributo !== "string" || !ATRIBUTOS_CONDICAO.has(o.atributo) || typeof o.operador !== "string" ||
    !OPERADORES_VALIDOS.has(o.operador) || typeof o.valor !== "number" || !Number.isFinite(o.valor)) return null;
  return { atributo: o.atributo as AtributoCondicao, operador: o.operador as OperadorCondicao, valor: o.valor };
}

export type FuncaoPainel = "regua" | "condicoes" | "ordenar" | "comparar" | "juntar" | "exportar" | "referencia" | "janela";
/** `criterio`: a referência pedida por critério (sem membros): a lista de candidatos abre nessa ordem, e a escolha é da pessoa.
 * `vista`: a vista do desenho pedida ("ver no mapa", "volte ao gráfico"), só quando ela pode aparecer; estado visual. */
export type ResultadoPedido = { definicao: DefinicaoAnalise; abrir: FuncaoPainel | null; selecao: string[] | null; mensagens: string[];
  criterio: PainelCriterio | null; vista: "grafico" | "mapa" | null };
/** Aplica o comando da conversa ao estado do gráfico. Valida cada campo; o que não vale vira mensagem, nunca erro. A vista do
 * mapa é conferida na definição que resulta do pedido (`mapa`): "mostre os municípios do Amazonas no mapa" abre o mapa; nos
 * estados, a mensagem diz o motivo. */
export function aplicarPedido(def: DefinicaoAnalise, pedido: PedidoDoChat, c: { periodos: string[]; nomes: Map<string, string>;
  temGrupos: boolean; disponivel: (familia: Familia) => Disponivel; grupoDe?: (id: string) => string;
  mapa?: (definicao: DefinicaoAnalise) => { disponivel: boolean; motivo: string | null } }): ResultadoPedido {
  let proxima: DefinicaoAnalise = { ...def };
  const mensagens: string[] = [];
  let abrir: FuncaoPainel | null = null, selecao: string[] | null = null;
  const periodos = new Set(c.periodos);
  if (pedido.indicador === "densidade" || pedido.indicador === "quantidade") proxima.indicador = pedido.indicador;
  if (pedido.municipios && typeof pedido.municipios === "object") {
    const m = pedido.municipios;
    const base = { todos: m.todos === true, estados: Array.isArray(m.estados) ? m.estados.filter((e): e is string => typeof e === "string") : [],
      ids: Array.isArray(m.ids) ? m.ids.filter((i): i is string => typeof i === "string") : [] };
    proxima = { ...proxima, nivel: "municipios", base: normalizarBase(base, c.grupoDe) };
  }
  if (pedido.nivel === "estados") {
    if (c.temGrupos) proxima.nivel = "estados";
    else mensagens.push("Esta fonte não tem a visão por grupos.");
  } else if (pedido.nivel === "municipios") proxima.nivel = "municipios";
  if (typeof pedido.competencia === "string") {
    if (periodos.has(pedido.competencia)) proxima.competencia = pedido.competencia;
    else mensagens.push("A competência " + exibirCompetencia(pedido.competencia) + " não existe nesta base.");
  }
  if (Array.isArray(pedido.janela)) {
    const janela = cronologica(pedido.janela.filter((p): p is string => typeof p === "string" && periodos.has(p)));
    if (janela.length >= 2) proxima = { ...proxima, janela, familia: pedido.familia ?? "tendencia" };
    else mensagens.push("A janela pedida não tem duas competências desta base.");
  }
  if (pedido.visaoTendencia === "mudanca" || pedido.visaoTendencia === "classes" || pedido.visaoTendencia === "series")
    proxima = { ...proxima, visao: pedido.visaoTendencia, familia: pedido.familia ?? "tendencia" };
  let criterioPedido: PainelCriterio | null = null;
  if (pedido.referencia && Array.isArray(pedido.referencia.membros)) {
    const membros = [...new Set(pedido.referencia.membros.filter((m): m is string => typeof m === "string"))];
    const criterio = pedido.referencia.criterio as Record<string, unknown> | undefined;
    const valido = criterio && ["densidade", "quantidade", "populacao"].includes(String(criterio.atributo)) && ["desc", "asc"].includes(String(criterio.ordem));
    if (membros.length) {
      proxima = { ...proxima, familia: pedido.familia ?? "espacial", nivel: "municipios",
        referencia: { membros, ...(valido ? { criterio: { atributo: criterio!.atributo as PainelAtributo, ordem: criterio!.ordem as PainelOrdem } } : {}) } };
    } else if (valido) {
      // Referência por critério: a lista de candidatos abre nessa ordem (CAP-SUB-02); usar o primeiro ou outro é da pessoa.
      criterioPedido = { atributo: criterio!.atributo as PainelAtributo, ordem: criterio!.ordem as PainelOrdem };
      proxima = { ...proxima, familia: pedido.familia ?? "espacial", nivel: "municipios" };
      abrir = "referencia";
    }
  }
  if (pedido.grupos && typeof pedido.grupos === "object") {
    const tipo = (pedido.grupos as { tipo?: unknown }).tipo;
    if (tipo === "quartis" || tipo === "quintis" || tipo === "decis" || tipo === "nenhum")
      proxima = { ...proxima, agrupar: { tipo, faixas: [] }, ...(tipo !== "nenhum" ? { familia: pedido.familia ?? "distribuicao" } : {}) };
    else mensagens.push("Os grupos pedidos não foram reconhecidos.");
  }
  if (pedido.familia && FAMILIAS_VALIDAS.has(pedido.familia)) proxima.familia = pedido.familia;
  if (pedido.ordenar) {
    const ordenar = lerOrdenar(pedido.ordenar);
    if (ordenar) { proxima.ordenar = ordenar; abrir = "ordenar"; }
    else mensagens.push("A ordenação pedida não foi reconhecida.");
  }
  if (Array.isArray(pedido.condicoes)) {
    const condicoes = pedido.condicoes.map(lerCondicao).filter((item): item is CondicaoPedido => !!item);
    if (condicoes.length) {
      proxima.condicoes = condicoes; abrir = "condicoes";
      if (condicoes.some(item => item.atributo === "distancia_km") && proxima.familia !== "espacial") proxima.familia = "espacial";
    } else mensagens.push("As condições pedidas não foram reconhecidas.");
  }
  if (Array.isArray(pedido.selecao)) selecao = [...new Set(pedido.selecao.filter((s): s is string => typeof s === "string"))];
  if (pedido.funcao === "comparar") {
    abrir = "comparar";
    if (selecao && selecao.length >= 2 && selecao.length <= 3) proxima.comparar = selecao;
    else if (selecao) mensagens.push("Para comparar, escolha dois ou três itens.");
  } else if (pedido.funcao === "juntar") {
    abrir = "juntar";
    const membros = (selecao || []).filter(id => !/^c\d+$/.test(id));  // conjuntos não entram em outro conjunto
    if (membros.length >= 2 && proxima.conjuntos.length < MAX_CONJUNTOS) {
      const conjunto = novoConjunto(proxima.conjuntos, membros, membros.map(id => c.nomes.get(id) || id).join(", ").slice(0, 120));
      proxima = { ...proxima, nivel: "municipios", conjuntos: [...proxima.conjuntos, conjunto] };
      selecao = [conjunto.id];
    } else if (selecao) mensagens.push("Para juntar, escolha pelo menos duas unidades.");
  } else if (pedido.funcao === "exportar") abrir = "exportar";
  else if (pedido.funcao === "ordenar") abrir = "ordenar";
  else if (pedido.funcao === "condicoes") abrir = "condicoes";
  // A família pedida (ou implícita: referência, janela, condição de distância) só vale se a fonte permitir.
  if (proxima.familia !== def.familia) {
    const disponivel = c.disponivel(proxima.familia);
    if (!disponivel.disponivel) { mensagens.push(NOMES_FAMILIAS[proxima.familia] + ": " + disponivel.motivo); proxima.familia = def.familia; }
  }
  // Vista do desenho (estado visual): o gráfico sempre; o mapa só quando a análise que resulta do pedido tem pontos.
  let vista: ResultadoPedido["vista"] = null;
  if (pedido.vista === "grafico") vista = "grafico";
  else if (pedido.vista === "mapa") {
    const mapa = c.mapa ? c.mapa(proxima) : { disponivel: true, motivo: null };
    if (mapa.disponivel) vista = "mapa";
    else mensagens.push("Mapa: " + (mapa.motivo || "indisponível nesta análise."));
  }
  return { definicao: proxima, abrir, selecao, mensagens, criterio: criterioPedido, vista };
}

/** Contexto do gráfico para a estrutura da página e a conversa. */
export function contextoDoGrafico(def: DefinicaoAnalise, idsNaTela: string[], titulo: string, grupoDe: (id: string) => string = prefixoDe): ContextoDoGrafico {
  return { familia: def.familia, indicador: def.indicador, nivel: def.nivel, municipios: normalizarBase(def.base, grupoDe), idsNaTela,
    competencia: def.familia === "tendencia" ? def.janela.at(-1) ?? def.competencia : def.competencia, janela: def.janela,
    referencia: def.familia === "espacial" ? def.referencia?.membros ?? [] : [], titulo };
}

// ================================================================================================ título
/** Frase que diz o que está na tela (decisão 8): o indicador, onde e quando; o subtítulo explica a leitura. */
export function tituloDaAnalise(p: { fonte: "brasil" | "arquivo" | null; familia: Familia; visao: Visao; indicador: PainelIndicador;
  nivel: PainelNivel; categoria: string; competencia: string; janela: string[]; rotatividade: { inicial: string; final: string } | null;
  lugar: Lugar; referencia: string | null; rotulos: RotulosTerritoriais }): { titulo: string; subtitulo: string } {
  if (!p.fonte) return { titulo: "Diagnóstico territorial da força de trabalho em saúde", subtitulo: "Escolha os dados para começar." };
  const especie = INDICADORES[p.indicador].rotulo;
  const quem = profissionaisDe(p.categoria);
  const rotuloBolha = p.nivel === "estados" ? p.rotulos.grupo ?? ROTULOS_GENERICOS.grupo! : p.rotulos.unidade;
  const cadaBolha = textoCadaBolha(rotuloBolha);
  const onde = p.lugar.lugar ? " " + p.lugar.lugar : "";
  const periodo = (a: string, b: string) => competenciaPorExtenso(a) + " a " + competenciaPorExtenso(b);
  if (p.familia === "espacial" && p.nivel === "municipios")
    return { titulo: especie + " de " + quem + " e distância até " + (p.referencia || "a referência") + " · " + p.lugar.curto + " · " +
      competenciaPorExtenso(p.competencia), subtitulo: cadaBolha + " A posição horizontal é a distância até a referência." };
  if (p.familia === "tendencia" && p.nivel === "municipios") {
    const janela = p.janela.length >= 2 ? periodo(p.janela[0], p.janela[p.janela.length - 1]) : "escolha a janela";
    const mudanca = p.visao === "mudanca" || p.janela.length < MINIMO_TENDENCIA;
    return { titulo: (mudanca ? "Mudança da " : "Tendência da ") + especie.toLowerCase() + " de " + quem + " · " + p.lugar.curto + " · " + janela,
      subtitulo: p.visao === "series" && !mudanca ? "Cada linha é " + umA(p.rotulos.unidade) + ", nas competências da janela."
        : cadaBolha + (mudanca ? " O rastro sai do valor na primeira competência." : " A cor mostra a família da classe de tendência.") };
  }
  if (p.familia === "rotatividade" && p.nivel === "municipios" && p.rotatividade)
    return { titulo: "Rotatividade e permanência da coorte inicial · " + p.lugar.curto + " · " + periodo(p.rotatividade.inicial, p.rotatividade.final),
      subtitulo: "Cada barra é " + umA(p.rotulos.unidade) + ": permanência e saída da coorte inicial." };
  return { titulo: especie + " de " + quem + onde + " · " + competenciaPorExtenso(p.competencia), subtitulo: cadaBolha };
}

// ================================================================================================ estado salvo (Histórico)
/** Estado visual guardado com a análise. `vista` (gráfico, mapa ou lado a lado) e `corContinua` (a cor contínua escolhida para o
 * mapa) entraram em 23/10/2026: um estado de antes, sem os campos, reabre no gráfico e com o mapa ainda sem cor escolhida. */
export type Visual = { escala: Escala; corte: Corte | null; selecionados: string[]; vista?: VistaDesenho; corContinua?: boolean };
/** O que o Histórico guarda: a definição, a família que o motor calculou, a chave do pedido (para reabrir sem recalcular), o
 * pedido enviado e o estado visual. */
export type DefinicaoSalva = { versao: 1; chave: string; familia: Familia; opcoes: PainelOpcoes | null; definicao: DefinicaoAnalise; visual: Visual };
export function salvarEstado(titulo: string, salvo: Omit<DefinicaoSalva, "versao">, resposta: PainelResposta | null,
  quando = new Date().toISOString()): EstadoSalvo {
  const definicao: DefinicaoSalva = { versao: 1, ...salvo };
  return { titulo, definicao, resposta, quando };
}
const VISTAS_VALIDAS = new Set<string>(["grafico", "mapa", "lado"]);
/** Lê um estado salvo; o que não tiver a forma esperada é ignorado (null). Vista ou cor contínua com valor estranho ficam de fora. */
export function lerEstadoSalvo(estado: EstadoSalvo | null | undefined): (DefinicaoSalva & { resposta: PainelResposta | null }) | null {
  const salvo = estado?.definicao as Partial<DefinicaoSalva> | undefined;
  if (!salvo || salvo.versao !== 1 || typeof salvo.chave !== "string" || !salvo.definicao || typeof salvo.definicao !== "object") return null;
  const def = salvo.definicao as DefinicaoAnalise;
  if (!FAMILIAS_VALIDAS.has(def.familia) || !def.base || !Array.isArray(def.janela)) return null;
  const resposta = estado!.resposta as PainelResposta | null;
  const vista = salvo.visual?.vista, corContinua = salvo.visual?.corContinua;
  return { versao: 1, chave: salvo.chave, familia: salvo.familia && FAMILIAS_VALIDAS.has(salvo.familia) ? salvo.familia : "distribuicao",
    opcoes: salvo.opcoes ?? null, definicao: def,
    visual: { escala: salvo.visual?.escala === "logaritmica" ? "logaritmica" : "linear", corte: salvo.visual?.corte ?? null,
      selecionados: Array.isArray(salvo.visual?.selecionados) ? salvo.visual!.selecionados : [],
      ...(typeof vista === "string" && VISTAS_VALIDAS.has(vista) ? { vista } : {}),
      ...(typeof corContinua === "boolean" ? { corContinua } : {}) },
    resposta: resposta && Array.isArray(resposta.itens) ? resposta : null };
}

// ================================================================================================ exportação
/** Célula de CSV: aspas, com proteção contra fórmula; número em precisão integral (como veio do motor). */
function celula(valor: unknown): string {
  let texto = valor === null || valor === undefined ? "" : typeof valor === "number" ? String(valor) : String(valor);
  if (typeof valor === "string" && /^[\s]*[=+@\-]/.test(texto)) texto = "'" + texto;
  return '"' + texto.replace(/"/g, '""') + '"';
}
/** CSV da análise: todos os itens do resultado, na ordem neutra, com os valores do motor em precisão integral, a
 * avaliabilidade e o motivo (CAP-REP-06). Separador ";" e BOM, como a exportação de sempre. */
export function montarCsv(resposta: PainelResposta, c: { familia: Familia; indicador: PainelIndicador; rotulos: RotulosTerritoriais }): string {
  const itens = [...resposta.itens].sort(ordemNeutra);
  const distancia = itens.some(item => item.distancia_km !== null || item.avaliavel.distancia !== null);
  const variacao = !!resposta.competencia_inicial;
  const tendencia = itens.some(item => item.tendencia);
  const grupo = itens.some(item => item.grupo), faixa = itens.some(item => item.faixa), faixaDistancia = itens.some(item => item.faixa_distancia);
  const condicoes = itens.some(item => item.condicoes), ordem = itens.some(item => item.ordem), rotatividade = itens.some(item => item.rotatividade);
  const tipoTexto = (tipo: PainelItem["tipo"]) => tipo === "conjunto" ? "conjunto" : tipo === "estado"
    ? (c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular : c.rotulos.unidade.singular;
  const colunas: [string, (item: PainelItem) => unknown][] = [
    ["Identificador", item => item.id], ["Tipo", item => tipoTexto(item.tipo)], ["Território", item => item.rotulo], ["UF", item => item.uf],
    ["Competência", () => resposta.competencia], ["Categoria", () => resposta.categoria],
    ["População", item => item.populacao], ["Quantidade", item => item.quantidade], ["Densidade por 1.000 habitantes", item => item.densidade],
    ["Tipo de contagem", item => item.tipo === "conjunto" ? textoDaContagem(item.contagem) : ""],
  ];
  if (distancia) colunas.push(["Distância até a referência (km)", item => item.distancia_km], ["Distância do membro mais distante (km)", item => item.distancia_km_max ?? null],
    ["Membro da referência mais próximo", item => (item.referencia_mais_proxima || []).map(ref => ref.rotulo).join(" | ")],
    ["Membro da referência", item => item.referencia ? "sim" : "não"]);
  if (faixaDistancia) colunas.push(["Faixa de distância", item => item.faixa_distancia === "fora" ? "fora" : item.faixa_distancia?.rotulo ?? ""]);
  if (variacao) colunas.push(["Competência inicial", () => resposta.competencia_inicial],
    ["População inicial", item => item.inicial.populacao], ["Quantidade inicial", item => item.inicial.quantidade],
    ["Densidade inicial", item => item.inicial.densidade], ["Variação da população (%)", item => item.variacao_percentual.populacao],
    ["Variação da quantidade (%)", item => item.variacao_percentual.quantidade], ["Variação da densidade (%)", item => item.variacao_percentual.densidade]);
  if (tendencia) colunas.push(["Janela da tendência", () => (resposta.tendencia?.janela || []).join(" | ")],
    ["Classe de tendência", item => item.tendencia?.classe ?? ""], ["Rótulo da tendência", item => item.tendencia?.rotulo ?? ""],
    ["Motivo da tendência", item => item.tendencia?.motivo ?? ""],
    ["Velocidades", item => (item.tendencia?.velocidades || []).map(v => v.de + "-" + v.ate + ":" + String(v.valor)).join(" | ")]);
  if (grupo) colunas.push(["Grupo por posição", item => item.grupo?.rotulo ?? ""]);
  if (faixa) colunas.push(["Faixa", item => item.faixa === "fora" ? "fora" : item.faixa?.rotulo ?? ""]);
  if (condicoes) colunas.push(["Condições", item => item.condicoes?.situacao ?? ""]);
  if (ordem) colunas.push(["Posição na ordenação", item => item.ordem?.posicao ?? null]);
  if (rotatividade) colunas.push(["Coorte inicial", item => item.rotatividade?.coorteInicial ?? null],
    ["Permaneceram", item => item.rotatividade?.permaneceram ?? null], ["Saíram", item => item.rotatividade?.sairam ?? null],
    ["Permanência da coorte inicial (%)", item => item.rotatividade?.permanencia ?? null],
    ["Saída da coorte inicial (%)", item => item.rotatividade?.saida ?? null]);
  colunas.push(["Avaliável", item => item.avaliavel.densidade ? "sim" : "não"],
    ["Motivos", item => [...textosDe(item), item.tendencia?.avaliavel === false ? item.tendencia.motivo : null,
      item.rotatividade?.avaliavel === false ? item.rotatividade.motivo : null].filter(Boolean).join(" | ")]);
  const linhas = [colunas.map(([nome]) => celula(nome)).join(";"), ...itens.map(item => colunas.map(([, valor]) => celula(valor(item))).join(";"))];
  return "﻿" + linhas.join("\r\n");
}
/** Método e parâmetros em texto: o título, a frase-resumo do motor (a mesma da tela; sem ela, nada no lugar), o pedido
 * enviado ao motor, as notas, as limitações e a procedência. */
export function textoDoMetodo(resposta: PainelResposta, titulo: string, opcoes: PainelOpcoes | null,
  resumo: string | null = resposta.resumo?.texto ?? null): string {
  const linhas = [titulo, ...(resumo ? [resumo] : []), "", "Procedência", "- Competência: " + exibirCompetencia(resposta.competencia) +
    (resposta.competencia_inicial ? " (inicial: " + exibirCompetencia(resposta.competencia_inicial) + ")" : ""),
    "- Categoria: " + resposta.categoria, "- Versão da base: " + (resposta.versao_base || "não informada"),
    "- Chave de execução: " + (resposta.chave_execucao || "não informada")];
  if (resposta.referencia?.origem) linhas.push("- Referência: " + resposta.referencia.origem);
  if (resposta.tendencia?.janela.length) linhas.push("- Janela da tendência: " + resposta.tendencia.janela.map(exibirCompetencia).join(", "));
  linhas.push("", "Notas do método", ...resposta.notas.map(nota => "- " + nota));
  if (resposta.limitacoes.length) linhas.push("", "Limitações", ...resposta.limitacoes.map(codigo => "- " + textoDaLimitacao(codigo)));
  if (opcoes) linhas.push("", "Parâmetros enviados ao motor", JSON.stringify(opcoes, null, 2));
  linhas.push("", "Os valores do CSV estão em precisão integral; na tela, aparecem arredondados.");
  return linhas.join("\n");
}

// ================================================================================================ ajustes, vista do desenho e mapa
/** Ajustes dentro da análise escolhida (23/10/2026): o painel colado na aba mostra só o que vale para ela. O indicador é o
 * mesmo em todas as abas (fica na definição) e fica à vista; a categoria, com mais de uma, vem logo depois dele; a rotatividade
 * não tem indicador. Nos estados (E1) e com a família indisponível, o desenho é a distribuição, e valem os ajustes dela. */
export type Ajuste = "indicador" | "categoria" | "competencia" | "agrupar" | "referencia" | "janela" | "visao" | "periodos";
export function ajustesDaAnalise(c: { familia: Familia; nivel: PainelNivel; disponivel: boolean; categorias: number }): Ajuste[] {
  const categoria: Ajuste[] = c.categorias > 1 ? ["categoria"] : [];
  const familia = c.nivel === "estados" || !c.disponivel ? "distribuicao" : c.familia;
  if (familia === "espacial") return ["indicador", ...categoria, "competencia", "referencia"];
  if (familia === "tendencia") return ["indicador", ...categoria, "janela", "visao"];
  if (familia === "rotatividade") return ["periodos", ...categoria];
  return ["indicador", ...categoria, "competencia", "agrupar"];
}
/** Motivo do botão Densidade desligado numa planilha sem população (o motor recusa a densidade sem ela). */
export const TEXTO_SEM_POPULACAO = "Sem população na planilha: só a quantidade.";

/** Largura mínima da janela (px) para o gráfico e o mapa lado a lado; abaixo dela, a escolha volta ao mapa. */
export const LARGURA_LADO_A_LADO = 1600;
/** Ligações ilustrativas do mapa até a referência mais próxima: só dos selecionados, até este número. */
export const MAX_LIGACOES = 30;

export type MapaDisponivel = { disponivel: boolean; motivo: string | null; atalho: string | null };
/** Se o mapa pode aparecer na análise e, se não, o motivo (e o texto do atalho, nos estados). Os estados não têm um ponto (os
 * ladrilhos dos estados não foram aprovados: nada de mapa nesse nível); a planilha precisa das colunas de latitude e longitude;
 * a visão Séries é só do gráfico. Pendências do motor (o referencial de uma planilha) não desligam o mapa: aparecem nele. */
export function disponibilidadeDoMapa(c: { fonte: "brasil" | "arquivo" | null; temCoordenadas: boolean; nivel: PainelNivel;
  series: boolean; rotatividade: boolean; rotulos: RotulosTerritoriais }): MapaDisponivel {
  const unidade = c.rotulos.unidade, grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  if (!c.fonte) return { disponivel: false, motivo: "Escolha os dados para começar.", atalho: null };
  if (c.nivel === "estados") return { disponivel: false, atalho: "Ver " + artigo(unidade, true) + " " + unidade.plural + " no mapa",
    motivo: maiuscula(artigo(grupo, true)) + " " + grupo.plural + " não têm um ponto no mapa: cada ponto do mapa é " + umA(unidade) + "." };
  if (!c.temCoordenadas) return { disponivel: false, atalho: null, motivo: c.rotatividade
    ? "Sem latitude e longitude na planilha, a rotatividade fica nas barras: o mapa precisa das coordenadas de cada " + unidade.singular + "."
    : "A planilha não tem as colunas de latitude e longitude: o mapa precisa das coordenadas de cada " + unidade.singular + ". A tabela continua." };
  if (c.series) return { disponivel: false, atalho: null,
    motivo: "Na visão Séries, cada " + unidade.singular + " é uma linha no tempo: o mapa fica com Classes e Mudança." };
  return { disponivel: true, motivo: null, atalho: null };
}

/** Como o mapa pinta (PinturaDoMapa do contrato): a camada do gráfico quando há uma (grupos, faixas, condições, ordem, classes
 * ou variação); na rotatividade, a permanência da coorte inicial em cor contínua; senão, a cor contínua só se a pessoa a
 * escolheu; e, sem cor escolhida, a pergunta "Como pintar o mapa?" (decisão de 23/10/2026). Nunca a escala logarítmica. */
export function pinturaDoMapa(c: { camada: CamadaDeCor; rotatividade: boolean; corContinua: boolean }): PinturaDoMapa {
  if (c.rotatividade) return "continua";
  if (c.camada !== "unica") return "camada";
  return c.corContinua ? "continua" : "pergunta";
}
/** Opções da pergunta "Como pintar o mapa?" em cada análise: quintis e faixas vêm do motor (só na distribuição); a análise
 * espacial oferece a cor contínua e as Condições; tendência (a cor já é a da camada) e rotatividade não perguntam. */
export function opcoesDePintura(familia: Familia): EscolhaDePintura[] {
  if (familia === "distribuicao") return ["quintis", "faixas", "continua"];
  if (familia === "espacial") return ["continua", "condicoes"];
  return [];
}
/** Cor contínua do mapa: o indicador no domínio do motor ou, na rotatividade, a permanência da coorte inicial (0 a 100%). */
export function corContinuaDoMapa(c: { rotatividade: boolean; indicador: PainelIndicador; dominios: PainelResposta["dominios"] }):
  { valor: (item: PainelItem) => number | null; rotulo: string; dominio: PainelDominio | null } {
  if (c.rotatividade) return { valor: item => numero(item.rotatividade?.permanencia), rotulo: "Permanência da coorte inicial (%)", dominio: [0, 100] };
  const especie = INDICADORES[c.indicador];
  return { valor: item => valorDe(item, c.indicador), rotulo: especie.rotulo + " (" + especie.unidade + ")", dominio: c.dominios[c.indicador] ?? null };
}
/** Tamanho do ponto (área proporcional, TamanhoDoMapa do contrato): população na densidade, quantidade na quantidade e coorte
 * inicial na rotatividade; o máximo é o do domínio do motor, quando houver. */
export function tamanhoDoMapa(c: { rotatividade: boolean; indicador: PainelIndicador; dominios: PainelResposta["dominios"] }): TamanhoDoMapa {
  const maximo = (chave: string) => numero(c.dominios[chave]?.[1]);
  if (c.rotatividade) return { valor: item => numero(item.rotatividade?.coorteInicial), rotulo: "Coorte inicial", maximo: maximo("coorte_inicial") };
  if (c.indicador === "quantidade") return { valor: item => numero(item.quantidade), rotulo: "Quantidade de profissionais", maximo: maximo("quantidade") };
  return { valor: item => numero(item.populacao), rotulo: "População", maximo: maximo("populacao") };
}
/** Ligações ilustrativas do mapa (não são trajeto): de cada unidade selecionada até o membro (ou os membros, no empate) da
 * referência mais próximo, como o motor disse; só unidades, na ordem da seleção, até MAX_LIGACOES. */
export function ligacoesDoMapa(itens: PainelItem[], selecionados: string[]): { de: string; para: string[] }[] {
  const porId = new Map(itens.map(item => [item.id, item]));
  const ligacoes: { de: string; para: string[] }[] = [];
  for (const id of selecionados) {
    const item = porId.get(id);
    if (!item || item.tipo !== "municipio" || item.referencia || !item.referencia_mais_proxima?.length) continue;
    ligacoes.push({ de: item.id, para: item.referencia_mais_proxima.map(ref => ref.id) });
    if (ligacoes.length >= MAX_LIGACOES) break;
  }
  return ligacoes;
}
