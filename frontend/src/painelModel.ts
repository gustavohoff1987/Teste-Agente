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
  PainelResposta, Posicao, Premissas, Rotulo, RotulosTerritoriais,
  SituacaoCondicao, TendenciaItem, TendenciaTopo, TipoGrupos,
} from "./painelApi";
import type { PinturaDoMapa, TamanhoDoMapa, VistaDesenho } from "./mapaContrato";
import type { EsquemaDeCor } from "./esquemaDeCor";

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
  /** Explicação pedida na conversa (26/10/2026): abre "Entenda esta análise" na aba, com os termos (códigos das classes)
   * destacados. Estado visual: nada é recalculado. */
  explicar?: { aba: Familia; termos: string[] } | null;
  /** A Escolha dos territórios completa pedida na conversa (28/10/2026: "o de menor densidade e o mais próximo dele com
   * densidade de no mínimo 1,5"): a base, a referência e de onde cada uma parte, conferidas por lerConsulta. */
  consulta?: object | null;
};
/** O que está na tela, para a estrutura da página e a conversa. */
export type ContextoDoGrafico = {
  familia: Familia; indicador: PainelIndicador; nivel: PainelNivel; municipios: PainelMunicipios; idsNaTela: string[];
  competencia: string; janela: string[]; referencia: string[]; titulo: string;
  /** Os estados escolhidos no nível estados (24/10/2026). */
  estados?: string[];
  /** Vista em exibição e a frase-resumo do motor (verificada), para a conversa responder "o que o gráfico mostra?". */
  vista?: "grafico" | "mapa" | "lado"; resumo?: string | null;
  /** Se o mapa pode ser mostrado agora e, se não, o motivo (estados sem ponto, planilha sem coordenadas, visão Séries). */
  mapaDisponivel?: boolean; motivoSemMapa?: string | null;
  /** Os itens da comparação aberta (2 ou 3 ids), para a conversa trocar a ordem, incluir, tirar e voltar a ela. */
  comparar?: string[];
  /** A Escolha dos territórios da Análise Espacial em exibição (28/10/2026), para a conversa trocar só o que a pessoa pedir
   * ("e em todo o país?"). Fica no backend local, como as demais chaves painel_*. */
  consulta?: ConsultaTerritorios | null;
};
/** Estado salvo no Histórico: reabre sem recalcular. `definicao` é o objeto de `salvarEstado`. */
export type EstadoSalvo = { titulo: string; definicao: object; resposta: object | null; quando: string };
/** Estado de uma UF na base do Brasil (bloco "niveis" da inspeção). Basta esta forma (compatível com territorialScope.Levels). */
export type NivelEstado = { prefixo: string; sigla: string; nome: string; rotulo?: string; rotulo_grupo?: string; municipios: number };
export type NiveisDaBase = { estados: NivelEstado[]; municipios: { total: number };
  fonte_estadual?: { disponivel: boolean; motivo: string; periodos?: string[] } };
/** Unidade do catálogo para a escolha (forma de TerritorialSelection.Territory). */
export type UnidadeDoCatalogo = { id: string; name: string; code: string; label: string; state: string; state_name: string;
  state_code?: string; selection_reason?: string;
  /** Numa planilha com a coluna-mãe (grupo_territorial), o valor do grupo de cada unidade (a província de um distrito), do
   * catálogo do pré-exame. */
  parents?: string[] };

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
/** Nomes padronizados das análises (23/10/2026), na navegação, nos títulos e nos avisos. */
export const NOMES_FAMILIAS: Record<Familia, string> = { distribuicao: "Análise de Distribuição", espacial: "Análise Espacial",
  tendencia: "Análise de Tendência", rotatividade: "Análise de Rotatividade" };
/** Abas da área: a Seleção de Territórios (o conjunto analisado, compartilhado por todas as análises) e as quatro análises. */
export type Aba = "territorios" | Familia;
export const ABAS: Aba[] = ["territorios", "distribuicao", "espacial", "tendencia", "rotatividade"];
export const NOME_SELECAO = "Seleção de Territórios";
export const nomeDaAba = (aba: Aba) => aba === "territorios" ? NOME_SELECAO : NOMES_FAMILIAS[aba];
/** Visões da Análise de Tendência (24/10/2026), nesta ordem: Tendência (as classes, no quadro de setas), Trajetória (a mudança
 * entre o primeiro e o último período, com os períodos do meio) e Série temporal (a série histórica, no intervalo escolhido). Os
 * códigos internos (classes, mudanca, series) continuam os de antes. */
export const NOMES_VISOES: Record<Visao, string> = { classes: "Tendência", mudanca: "Trajetória", series: "Série temporal" };
export const ORDEM_DAS_VISOES: Visao[] = ["classes", "mudanca", "series"];

export type Disponivel = { disponivel: boolean; motivo: string; pendente: boolean; enviarDados: boolean };
/** Se a família pode ser usada agora. "pendente": registra a intenção e pede um passo antes (escolher os dados, escolher
 * municípios). Os motivos de indisponibilidade vêm do motor (`disponibilidade`); sem eles, a regra da fonte. Nos níveis Brasil e
 * estados (24/10/2026, matriz D3), valem a distribuição e a tendência; a distância é medida entre municípios, e a análise
 * espacial espera que a pessoa escolha municípios. */
export function disponibilidadeDaFamilia(familia: Familia, c: { fonte: "brasil" | "arquivo" | null; nivel: PainelNivel;
  disponibilidade: PainelResposta["disponibilidade"] | null; temIdentificador: boolean; rotulos: RotulosTerritoriais }): Disponivel {
  const ok: Disponivel = { disponivel: true, motivo: "", pendente: false, enviarDados: false };
  if (!c.fonte) return { ...ok, pendente: familia !== "distribuicao", motivo: "Escolha os dados para começar." };
  if (familia === "distribuicao") return ok;
  const motor = c.disponibilidade?.[familia];
  if (familia === "rotatividade") {
    if (motor && !motor.disponivel) return { disponivel: false, motivo: motor.motivo, pendente: false, enviarDados: c.fonte === "brasil" };
    if (c.fonte === "brasil") return { disponivel: false, pendente: false, enviarDados: true,
      motivo: "A base do Brasil tem contagens, não pessoas: a rotatividade exige dados enviados com o identificador individual." };
    if (!motor && !c.temIdentificador) return { disponivel: false, pendente: false, enviarDados: false,
      motivo: "A planilha não tem a coluna do identificador individual: a rotatividade acompanha pessoas da coorte inicial." };
    return ok;
  }
  if (familia === "espacial" && c.nivel !== "municipios") {
    const grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!, unidades = c.rotulos.unidade.plural;
    return { ...ok, pendente: true, motivo: "A distância é medida entre " + unidades + ": " + (c.nivel === "brasil"
      ? "o Brasil, como unidade, não tem um ponto no mapa." : artigo(grupo, true) + " " + grupo.plural + " não têm um ponto no mapa.") +
      " Para usar esta análise, escolha " + unidades + " na Seleção de Territórios." };
  }
  if (motor && !motor.disponivel) return { disponivel: false, motivo: motor.motivo, pendente: false, enviarDados: false };
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
/** "no Amazonas", "na Bahia", "em Santa Catarina": a preposição do nome do grupo pela gramática do motor ("Municípios do
 * Amazonas"); sem ela (numa planilha), "em <nome>". */
function emGrupo(g: GrupoInfo | undefined, id: string): string {
  const achado = /^(do|da|dos|das|de)\s+(.+)$/.exec(g?.rotuloGrupo ? g.rotuloGrupo.split(" ").slice(1).join(" ") : "");
  if (achado) return ({ do: "no", da: "na", dos: "nos", das: "nas", de: "em" } as Record<string, string>)[achado[1]] + " " + achado[2];
  return "em " + (g?.nome || id);
}
const emLista = (nomes: string[]) => nomes.length <= 1 ? nomes.join("") : nomes.slice(0, -1).join(", ") + " e " + nomes[nomes.length - 1];
/** Uma ou duas unidades marcadas uma a uma (sem grupo inteiro): os nomes delas ("PORTO ALEGRE (RS)"); senão, null. */
function poucasPeloNome(base: PainelMunicipios, avulsas: string[], nomes?: Map<string, string>): string | null {
  if (!nomes || base.todos || base.estados.length || !avulsas.length || avulsas.length > 2 || !avulsas.every(id => nomes.has(id))) return null;
  return emLista(avulsas.map(id => nomes.get(id)!));
}
/** Onde: "nos municípios do Amazonas" / "Amazonas"; "nos estados" / "Brasil"; "na Bahia e em Santa Catarina" (os estados como
 * unidades); "no Brasil" (o país como unidade); "em 3 municípios do Amazonas". */
export function lugarDoUniverso(c: { nivel: PainelNivel; base: PainelMunicipios; conjuntos: number; grupos: GrupoInfo[];
  rotulos: RotulosTerritoriais; brasil: boolean; grupoDe: (id: string) => string; estados?: string[];
  /** Nomes das unidades ("PORTO ALEGRE (RS)"): com uma ou duas marcadas, o título diz quais (24/10/2026). */
  nomes?: Map<string, string> }): Lugar {
  const unidade = c.rotulos.unidade, grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const origem = c.brasil ? "Brasil" : "Toda a planilha";
  if (c.nivel === "brasil") return { lugar: "no Brasil", curto: "Brasil" };
  if (c.nivel === "estados") {
    const escolhidos = c.estados ?? c.grupos.map(item => item.id);
    if (!escolhidos.length) return { lugar: "", curto: origem };
    if (escolhidos.length >= c.grupos.length) return { lugar: emOs(grupo) + " " + grupo.plural, curto: origem };
    const info = (id: string) => c.grupos.find(item => item.id === id);
    if (escolhidos.length <= 2) return { lugar: escolhidos.map(id => emGrupo(info(id), id)).join(" e "),
      curto: emLista(escolhidos.map(id => info(id)?.nome || id)) };
    const n = quantos(escolhidos.length, grupo);
    return { lugar: "em " + n, curto: n };
  }
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
  const poucas = poucasPeloNome(c.base, avulsas, c.nomes);
  if (poucas) return { lugar: "em " + poucas, curto: poucas };
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

/** O que está na análise, em poucas palavras (24/10/2026, no lugar da trilha "Brasil › Amazonas", que voltava aos estados
 * trocando a seleção): na aba Seleção de Territórios e nas análises. "Brasil (total nacional)", "Todos os estados (27)", "Bahia e
 * Santa Catarina", "Amazonas (62 municípios)", "3 municípios da Bahia", "12 municípios de 2 estados", "Nenhum município marcado". */
export function resumoDoUniverso(c: { nivel: PainelNivel; base: PainelMunicipios; estados: string[]; conjuntos: number; grupos: GrupoInfo[];
  rotulos: RotulosTerritoriais; total: number; grupoDe: (id: string) => string; nomes?: Map<string, string> }): string {
  const unidade = c.rotulos.unidade, grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const nenhum = (rotulo: Rotulo) => "Nenhum" + (fem(rotulo) ? "a " : " ") + rotulo.singular + " marcad" + (fem(rotulo) ? "a" : "o");
  const nome = (id: string) => c.grupos.find(item => item.id === id)?.nome || id;
  if (c.nivel === "brasil") return "Brasil (total nacional)";
  if (c.nivel === "estados") {
    if (!c.estados.length) return nenhum(grupo);
    if (c.estados.length >= c.grupos.length) return textoTodosOsGrupos(c.rotulos, c.grupos.length);
    return c.estados.length <= 3 ? emLista(c.estados.map(nome)) : quantos(c.estados.length, grupo);
  }
  if (c.base.todos) return maiuscula(todosOs(unidade)) + (c.total ? " (" + inteiro.format(c.total) + ")" : "");
  const avulsas = c.base.ids.filter(id => !c.base.estados.includes(c.grupoDe(id)));
  const gruposDasAvulsas = [...new Set(avulsas.map(c.grupoDe))].filter(Boolean);
  const n = unidadesNoUniverso(c.base, c.grupos, c.total, c.grupoDe);
  const conjuntos = c.conjuntos ? " e " + c.conjuntos + (c.conjuntos === 1 ? " conjunto" : " conjuntos") : "";
  const poucas = poucasPeloNome(c.base, avulsas, c.nomes);
  if (poucas) return poucas + conjuntos;
  if (baseVazia(c.base)) return c.conjuntos ? maiuscula(c.conjuntos + (c.conjuntos === 1 ? " conjunto" : " conjuntos")) : nenhum(unidade);
  if (c.base.estados.length && !avulsas.length)
    return (c.base.estados.length <= 3 ? emLista(c.base.estados.map(nome)) : quantos(c.base.estados.length, grupo)) +
      " (" + quantos(n, unidade) + ")" + conjuntos;
  if (!c.base.estados.length && gruposDasAvulsas.length === 1) {
    const g = c.grupos.find(item => item.id === gruposDasAvulsas[0]);
    return quantos(avulsas.length, unidade) + " " + (g?.rotuloGrupo ? g.rotuloGrupo.split(" ").slice(1).join(" ") : "de " + nome(gruposDasAvulsas[0])) + conjuntos;
  }
  const gruposTodos = new Set([...c.base.estados, ...gruposDasAvulsas]);
  return quantos(n, unidade) + (gruposTodos.size > 1 ? " de " + quantos(gruposTodos.size, grupo) : "") + conjuntos;
}

/** O que está marcado no nível dos municípios, grupo a grupo, para a Seleção mostrar o que entra na análise: quantas
 * unidades de cada grupo (do total dele) e, quando são poucas, os nomes. Sem grupos (planilha sem a coluna-mãe), um item só,
 * com id "". Só conta o que já está na escolha; nada é calculado. */
export type MarcadasDoGrupo = { grupo: string; nome: string; marcadas: number; total: number; inteiro: boolean; nomes: string[];
  /** As unidades marcadas uma a uma (fora de um grupo inteiro), na ordem do nome: cada uma pode ser tirada sozinha (24/10/2026). */
  ids: string[] };
export function marcadasPorGrupo(base: PainelMunicipios, c: { grupos: GrupoInfo[]; unidadesDoGrupo: (grupo: string) => string[];
  nomes: Map<string, string>; grupoDe: (id: string) => string; todas?: string[]; nomesAte?: number }): MarcadasDoGrupo[] {
  const ate = c.nomesAte ?? 6;
  const nomesDe = (ids: string[]) => ids.length <= ate ? ids.map(id => c.nomes.get(id) || id).sort(comparar) : [];
  const porNome = (ids: string[]) => [...ids].sort((a, b) => comparar(c.nomes.get(a) || a, c.nomes.get(b) || b));
  if (!c.grupos.length) {
    const todas = c.todas ?? [];
    const ids = base.todos ? todas : base.ids;
    return ids.length ? [{ grupo: "", nome: "", marcadas: ids.length, total: todas.length || ids.length, inteiro: base.todos, nomes: nomesDe(ids),
      ids: base.todos ? [] : porNome(ids) }] : [];
  }
  const porGrupo = c.grupos.flatMap((g): MarcadasDoGrupo[] => {
    const unidades = c.unidadesDoGrupo(g.id), total = g.unidades || unidades.length;
    if (base.todos || base.estados.includes(g.id)) return [{ grupo: g.id, nome: g.nome, marcadas: total, total, inteiro: true, nomes: [], ids: [] }];
    const ids = base.ids.filter(id => c.grupoDe(id) === g.id);
    return ids.length ? [{ grupo: g.id, nome: g.nome, marcadas: ids.length, total, inteiro: false, nomes: nomesDe(ids), ids: porNome(ids) }] : [];
  });
  // Unidades marcadas sem um grupo da lista (numa planilha, uma linha sem o valor da coluna-mãe; um id vindo da conversa): um
  // item à parte, com id "", para nada marcado ficar fora do que a Seleção mostra.
  const conhecidos = new Set(c.grupos.map(g => g.id));
  const outras = base.todos ? [] : base.ids.filter(id => !conhecidos.has(c.grupoDe(id)));
  if (outras.length) porGrupo.push({ grupo: "", nome: "", marcadas: outras.length, total: c.unidadesDoGrupo("").length || outras.length,
    inteiro: false, nomes: nomesDe(outras), ids: porNome(outras) });
  return porGrupo;
}

/** Grupos da escolha: os estados da base do Brasil (bloco "niveis") ou os valores da coluna-mãe do catálogo da planilha. */
export function gruposDaFonte(niveis: NiveisDaBase | null | undefined, catalogo: UnidadeDoCatalogo[]): GrupoInfo[] {
  if (niveis?.estados?.length) return niveis.estados.map(item => ({ id: item.prefixo, nome: item.nome, sigla: item.sigla,
    rotuloGrupo: item.rotulo_grupo || "", unidades: item.municipios }));
  const contagem = new Map<string, { nome: string; unidades: number }>();
  for (const item of catalogo) {
    if (item.selection_reason) continue;
    const id = grupoDaUnidade(item);
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
/** Grupo da unidade: o estado (pelo código IBGE) na base do Brasil; numa planilha com a coluna-mãe, o valor dela (23/10/2026). */
export const grupoDaUnidade = (item: UnidadeDoCatalogo) => item.state_code || item.state || item.parents?.[0] || "";
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
export const textoDaLimitacao = (codigo: string) => LIMITACOES[codigo] || "Limitação registrada no cálculo: " + codigo + ".";
/** Nota TPL-11 da distância (sempre junto da análise espacial). Desde 24/10/2026, sem nomes de bastidor ("calculada pelo
 * motor"): a interface fala do fenômeno e do resultado. */
export const NOTA_TPL11 = "Distância geográfica direta em linha reta entre as unidades (km). Não representa " +
  "estrada, tempo de viagem nem facilidade de chegada.";

export type NaoAvaliavel = { id: string; rotulo: string; tipo: PainelItem["tipo"]; aspecto: Aspecto; motivo: string };
export type Exibicao = { distancia: boolean; variacao: boolean; tendencia: boolean; condicoes: boolean; rotatividade: boolean;
  /** Com o mapa à vista: as unidades que o motor devolveu sem coordenada válida (id → motivo do motor, DadosDoMapa.semCoordenada). */
  semCoordenada: Map<string, string> | null };
const MOTIVO_PADRAO: Record<Aspecto, (indicador: PainelIndicador) => string> = {
  indicador: indicador => "Sem " + INDICADORES[indicador].rotulo.toLowerCase() + " avaliável na competência.",
  distancia: () => "Sem coordenada válida para medir a distância até a referência.",
  variacao: () => "Variação não avaliável (valor inicial zero ou ausente).",
  tendencia: () => "Tendência não avaliável nestes períodos.",
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
    if (exibicao.tendencia && (!item.tendencia || !item.tendencia.avaliavel)) registrar(item, "tendencia",
      explicacaoDaTendencia(item.tendencia) || item.tendencia?.rotulo);
    if (exibicao.condicoes && item.condicoes?.situacao === "NAO_AVALIAVEL") registrar(item, "condicoes", item.condicoes.motivo ||
      item.condicoes.porCondicao.filter(c => c.situacao === "NAO_AVALIAVEL").map(c => c.texto).filter(Boolean).join("; "));
  }
  return { plotaveis, fora };
}

/** Aspectos que tiram o item do desenho: falta o valor que o posiciona (o indicador; na análise espacial, a distância até a
 * referência; na rotatividade, a coorte). Nos demais (variação, tendência, condições, mapa), a bolha fica, vazada quando falta. */
export const ASPECTOS_FORA_DO_DESENHO: readonly Aspecto[] = ["indicador", "distancia", "rotatividade"];

/** Itens do mapa (25/10/2026): todas as unidades em análise, no lugar delas, também as que o gráfico deixa de fora por falta do
 * valor que as posiciona (o indicador, a distância até a referência mais próxima, a coorte). Nenhum território escolhido some do
 * mapa por isso; só quem não tem coordenada válida fica fora dele, com o motivo do motor. Os estados não têm ponto, e os conjuntos
 * dão o anel aos membros. Na ordem neutra, a do gráfico. */
export const itensParaOMapa = (itens: PainelItem[]) => [...itens].filter(item => item.tipo !== "estado").sort(ordemNeutra);

/** Filtros visuais da área (estado visual, RQ-REP-06): a régua do indicador, "Mostrar só quem atende" das condições e a classe
 * escolhida na tendência. No gráfico, separam as bolhas à vista; no mapa, quem fica fora deles esmaece, sem sumir. */
export type FiltrosVisuais = { indicador: PainelIndicador; corte: Corte | null; soAtende: boolean; condicoes: boolean;
  filtroClasse: string | null; tendencia: boolean };
export const dentroDosFiltros = (item: PainelItem, f: FiltrosVisuais) => noCorte(item, f.indicador, f.corte) &&
  (!f.soAtende || !f.condicoes || item.condicoes?.situacao === "ATENDE") &&
  (!f.filtroClasse || !f.tendencia || (f.filtroClasse === "NAO_AVALIAVEL" ? !item.tendencia?.avaliavel : item.tendencia?.classe === f.filtroClasse));

const FALTA_NO_DESENHO: Partial<Record<Aspecto, string>> = { indicador: "sem valor do indicador na competência",
  distancia: "sem distância até a referência", rotatividade: "sem coorte inicial avaliável" };
/** O que fica fora do gráfico (25/10/2026), dito junto dele: os itens sem o valor que os posiciona, pelo que falta, com os nomes
 * (até `limite` por motivo) e as contagens. O motivo de cada um continua em Não avaliáveis; com o mapa, as unidades aparecem nele,
 * no lugar delas. Null quando nada fica de fora. */
export function textoForaDoDesenho(fora: NaoAvaliavel[], c: { rotulos: RotulosTerritoriais; mapa: boolean; limite?: number }): string | null {
  const limite = c.limite ?? 5, unidade = c.rotulos.unidade, f = fem(unidade);
  const deFora = fora.filter(item => ASPECTOS_FORA_DO_DESENHO.includes(item.aspecto));
  if (!deFora.length) return null;
  const frases = ASPECTOS_FORA_DO_DESENHO.map(aspecto => {
    const itens = deFora.filter(item => item.aspecto === aspecto);
    if (!itens.length) return null;
    const nomes = itens.slice(0, limite).map(item => item.rotulo), resto = itens.length - nomes.length;
    return FALTA_NO_DESENHO[aspecto] + (itens.length > 1 ? " (" + inteiro.format(itens.length) + ")" : "") + ": " +
      emLista(resto ? [...nomes, "mais " + inteiro.format(resto)] : nomes) + ".";
  }).filter((frase): frase is string => !!frase);
  const unidades = deFora.filter(item => item.tipo !== "conjunto" && item.tipo !== "estado" && item.tipo !== "brasil").length;
  const noMapa = !c.mapa || !unidades ? "" : "; no mapa, " + (unidades === 1
    ? artigo(unidade, false) + " " + unidade.singular + " aparece no lugar " + (f ? "dela" : "dele")
    : artigo(unidade, true) + " " + unidade.plural + " aparecem no lugar " + (f ? "delas" : "deles"));
  return "Fora do gráfico, " + frases.map((frase, indice) => indice ? maiuscula(frase) : frase).join(" ") + " O motivo " +
    (deFora.length > 1 ? "de " + (f ? "cada uma " : "cada um ") : "") + "está em Não avaliáveis, nos Detalhes" + noMapa + ".";
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
/** Valores da legenda de tamanho: três referências em números redondos (1, 2 ou 5 × 10ⁿ) abaixo do máximo, todas na proporção
 * exata (25/10/2026). Uma referência abaixo de `minimo` (o valor do raio mínimo visível) seria desenhada maior do que a área
 * dela; no lugar, entra o menor número redondo que já alcança o mínimo, ou nada, se ele não ficar abaixo da referência anterior. */
export function valoresDaLegendaDeTamanho(topo: number, minimo: number): number[] {
  const abaixo = (valor: number) => limpo(([5, 2, 1].find(fator => fator * potencia(valor) <= valor * (1 + 1e-9)) ?? 1) * potencia(valor));
  const acima = (valor: number) => limpo(([1, 2, 5, 10].find(fator => fator * potencia(valor) >= valor * (1 - 1e-9)) ?? 10) * potencia(valor));
  const maior = abaixo(topo);
  const valores: number[] = [];
  for (const candidato of [maior, abaixo(maior / 4), abaixo(maior / 25)]) {
    const valor = candidato >= minimo * (1 - 1e-9) ? candidato : acima(minimo);
    if (valor > 0 && valor <= topo && (!valores.length || valor < valores[valores.length - 1])) valores.push(valor);
  }
  return valores;
}
/** Três tamanhos de referência abaixo da maior população, na proporção exata: legenda de escala, não dado. */
export function legendaDeTamanhos(maxima: number | null | undefined, raioMax: number): TamanhoLegenda[] {
  const topo = numero(maxima);
  if (topo === null || topo <= 0) return [];
  return valoresDaLegendaDeTamanho(topo, topo * (RAIO_MINIMO / raioMax) ** 2)
    .map(valor => ({ valor, raio: raioDaPopulacao(valor, topo, raioMax), texto: compacto(valor) + " hab." }));
}

// ================================================================================================ cor
/** Série única: azul-petróleo da identidade, com croma e contraste validados. As constantes desta seção são as do modo claro;
 * o modo escuro usa PALETA_ESCURA (abaixo), pela paletaDoGrafico. */
export const COR_BOLHA = "#008b9e";
export const COR_NEUTRA = "#c9c7bf";
export const COR_NAO_AVALIAVEL = "#898781";
/** Família da classe de tendência (CAP-TEN-01; Adendo BOL aprovado em 22/10/2026): crescimento azul, declínio laranja, sem
 * classificação verde-água. Os três primeiros tons da paleta categórica, conferidos em todos os pares (bolhas). */
export const CORES_TENDENCIA: Record<FamiliaTendencia, string> = { CRESCIMENTO: "#2a78d6", DECLINIO: "#eb6834", NENHUMA: "#1baf7a" };
export const NOMES_FAMILIA_TENDENCIA: Record<FamiliaTendencia, string> = { CRESCIMENTO: "Família do crescimento",
  DECLINIO: "Família do declínio", NENHUMA: "Sem classificação" };
/** Ordem do enum CategoriaTendencia (SPEC L415): a ordem da legenda e das contagens, não um ranking. Rótulos de DA-15, com "de
 * declínio" nos dois do declínio (divergência aprovada pelo responsável em 24/10/2026; os mesmos do motor). */
export const CLASSES_TENDENCIA: { codigo: string; rotulo: string; familia: FamiliaTendencia }[] = [
  { codigo: "CRESCIMENTO", rotulo: "Crescimento", familia: "CRESCIMENTO" },
  { codigo: "CRESCIMENTO_ACELERADO", rotulo: "Aceleração do crescimento", familia: "CRESCIMENTO" },
  { codigo: "CRESCIMENTO_DESACELERADO", rotulo: "Desaceleração do crescimento", familia: "CRESCIMENTO" },
  { codigo: "DECLINIO", rotulo: "Declínio", familia: "DECLINIO" },
  { codigo: "DECLINIO_ACELERADO", rotulo: "Aceleração de declínio", familia: "DECLINIO" },
  { codigo: "DECLINIO_DESACELERADO", rotulo: "Desaceleração de declínio", familia: "DECLINIO" },
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
/** Mudança entre duas competências (CAP-TMP-01): divergente contínuo, aumento em azul, redução em laranja, zero em cinza. */
export const RAMPA_AUMENTO = ["#9cc2ee", "#2a78d6", "#184f95"];
export const RAMPA_REDUCAO = ["#f2ad8c", "#eb6834", "#a8431b"];

/** Paleta do gráfico num esquema de cor: superfície e tintas do desenho, cores de dado e rampas. Os nomes valem nos dois
 * esquemas; só os valores mudam. */
export type PaletaDoGrafico = {
  /** Superfície do desenho, anel de 2 px das bolhas e halo dos rótulos. */
  superficie: string;
  /** Tinta: rótulos, anel da seleção, do conjunto, mira da referência e limites da régua. */
  tinta: string;
  /** Tinta secundária: linha do Brasil, traço do conjunto, círculos da legenda de tamanho. */
  tinta2: string;
  /** Textos leves (rótulos das linhas de corte). */
  muda: string;
  /** Grade recessiva e linha de base dos eixos. */
  grade: string;
  eixo: string;
  /** Série única (sem camada de cor), "atendem", "os primeiros". */
  bolha: string;
  /** Neutro: "não atendem", "demais", "fora das faixas" e "saíram" (rotatividade). */
  neutra: string;
  /** Ponto médio do divergente da variação (sem mudança). */
  zero: string;
  /** Anel tracejado do valor não avaliável (bolha vazada). */
  naoAvaliavel: string;
  /** Preenchimento da bolha vazada. */
  vazia: string;
  /** Fundo da dica desenhada dentro do SVG (visão Séries). */
  dica: string;
  tendencia: Record<FamiliaTendencia, string>;
  /** Grupos e faixas (de 1 a 5 tons): do menor ao maior grupo. */
  ordinais: Record<number, string[]>;
  /** Braços do divergente da variação: do perto de zero ao limite. */
  aumento: string[];
  reducao: string[];
};
/** Modo claro: as constantes acima, conferidas no validador da skill de visualização (superfície #fcfcfb). */
export const PALETA_CLARA: PaletaDoGrafico = {
  superficie: "#fcfcfb", tinta: "#0b0b0b", tinta2: "#52514e", muda: "#898781", grade: "#e1e0d9", eixo: "#c3c2b7",
  bolha: COR_BOLHA, neutra: COR_NEUTRA, zero: COR_NEUTRA, naoAvaliavel: COR_NAO_AVALIAVEL, vazia: "#ffffff", dica: "#ffffff",
  tendencia: CORES_TENDENCIA, ordinais: RAMPAS_ORDINAIS, aumento: RAMPA_AUMENTO, reducao: RAMPA_REDUCAO,
};
/** Modo escuro (23/10/2026): os mesmos matizes, em passos escolhidos para a superfície escura #1a1a19 (não é inversão
 * automática), conferidos no validador da skill (validate_palette.js --mode dark --surface "#1a1a19"):
 * - tendência #3987e5, #d95926 e #199e70: todos os pares (--pairs all), pior CVD ΔE 9,4, visão normal 20,9, todas ≥ 3:1;
 * - série única #1ba3b5: PASS (5,77:1);
 * - grupos e faixas (--ordinal) do escuro (menor) ao claro (maior), sem ir além do passo 600 (#184f95, 2,15:1): PASS de 2 a 5;
 * - divergente: cada braço (--ordinal) PASS, do perto de zero (#1c5cab, 2,63:1; #a8431b, 2,89:1) ao limite (#9ec5f4, #f2ad8c);
 *   entre os braços, CVD ΔE 21,8 nos começos e 14,3 nas pontas; o zero (#45443f, 1,78:1, como o #c9c7bf no claro, 1,65:1) fica
 *   abaixo dos dois começos em luminosidade (ΔL OKLCH ≥ 0,09);
 * - neutro #5f5e5a (2,68:1): ao lado da série única, CVD ΔE 18,1 e visão normal 20,8 (no claro, 21,4 e 26,7); cinza de
 *   propósito, como no claro, com o alívio da legenda com as contagens e da tabela;
 * - tintas da tabela "Chart chrome & ink" da skill: #f0efec (15,2:1), #c3c2b7 (9,7:1), muda #898781 (4,85:1), grade #2c2c2a e
 *   eixo #383835; o anel do não avaliável é o mesmo #898781 nos dois esquemas. */
export const PALETA_ESCURA: PaletaDoGrafico = {
  superficie: "#1a1a19", tinta: "#f0efec", tinta2: "#c3c2b7", muda: "#898781", grade: "#2c2c2a", eixo: "#383835",
  bolha: "#1ba3b5", neutra: "#5f5e5a", zero: "#45443f", naoAvaliavel: "#898781", vazia: "#1a1a19", dica: "#232321",
  tendencia: { CRESCIMENTO: "#3987e5", DECLINIO: "#d95926", NENHUMA: "#199e70" },
  ordinais: {
    1: ["#3987e5"], 2: ["#1c5cab", "#86b6ef"], 3: ["#1c5cab", "#3987e5", "#9ec5f4"],
    4: ["#184f95", "#2a78d6", "#5598e7", "#9ec5f4"], 5: ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"],
  },
  aumento: ["#1c5cab", "#3987e5", "#9ec5f4"],
  reducao: ["#a8431b", "#d95926", "#f2ad8c"],
};
/** A paleta do esquema de cor em uso (useEsquemaDeCor). */
export const paletaDoGrafico = (esquema: EsquemaDeCor): PaletaDoGrafico => esquema === "escuro" ? PALETA_ESCURA : PALETA_CLARA;

/** Cor do grupo ou faixa (índice a partir de 1) entre `total`; null com mais de 5 (só linhas de corte). */
export const corOrdinal = (indice: number, total: number, paleta: PaletaDoGrafico = PALETA_CLARA): string | null =>
  paleta.ordinais[total]?.[indice - 1] ?? null;

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
export function corDaVariacao(valor: number, limite: number, paleta: PaletaDoGrafico = PALETA_CLARA): string {
  if (valor === 0 || !Number.isFinite(valor)) return paleta.zero;
  const t = limite > 0 ? Math.sqrt(Math.min(1, Math.abs(valor) / limite)) : 1;
  const rampa = valor > 0 ? paleta.aumento : paleta.reducao;
  const posicao = t * (rampa.length - 1), indice = Math.min(rampa.length - 2, Math.floor(posicao));
  return misturar(rampa[indice], rampa[indice + 1], posicao - indice);
}
/** Gradiente da legenda da variação (a mesma rampa do desenho): redução à esquerda, o zero no meio, aumento à direita. */
export const gradienteDaVariacao = (paleta: PaletaDoGrafico = PALETA_CLARA) => "linear-gradient(to right, " +
  [...paleta.reducao].reverse().join(", ") + " 48%, " + paleta.zero + " 48% 52%, " +
  paleta.aumento.map((cor, indice) => cor + (indice === 0 ? " 52%" : "")).join(", ") + ")";
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
  totalFaixas: number; primeiros: number | null;
  /** Paleta do esquema de cor em uso; sem ela, a do modo claro. */
  paleta?: PaletaDoGrafico };
/** Cor de cada bolha pela camada em uso. Só traduz o que o motor devolveu (variação, classe, grupo, faixa, situação, posição). */
export function pintar(item: PainelItem, p: ParametrosPintura): Pintura {
  const paleta = p.paleta ?? PALETA_CLARA;
  const vazia: Pintura = { cor: paleta.vazia, vazada: true, apagada: false };
  switch (p.camada) {
    case "variacao": {
      const valor = variacaoDe(item, p.indicador);
      return valor === null ? vazia : { cor: corDaVariacao(valor, p.limiteVariacao, paleta), vazada: false, apagada: false };
    }
    case "classes": {
      const familia = item.tendencia?.avaliavel ? item.tendencia.familia ?? familiaDaClasse(item.tendencia.classe) : null;
      return familia ? { cor: paleta.tendencia[familia], vazada: false, apagada: false } : vazia;
    }
    case "grupos": {
      if (!item.grupo) return vazia;
      return { cor: corOrdinal(item.grupo.indice, p.totalGrupos, paleta) ?? paleta.bolha, vazada: false, apagada: false };
    }
    case "faixas": {
      if (!item.faixa) return vazia;
      if (item.faixa === "fora") return { cor: paleta.neutra, vazada: false, apagada: false };
      return { cor: corOrdinal(item.faixa.indice, p.totalFaixas, paleta) ?? paleta.bolha, vazada: false, apagada: false };
    }
    case "condicoes": {
      const situacao = item.condicoes?.situacao;
      if (!situacao || situacao === "NAO_AVALIAVEL") return vazia;
      return situacao === "ATENDE" ? { cor: paleta.bolha, vazada: false, apagada: false } : { cor: paleta.neutra, vazada: false, apagada: true };
    }
    case "ordem": {
      const posicao = item.ordem?.posicao ?? null;
      const dentro = posicao !== null && (p.primeiros === null || posicao <= p.primeiros);
      return dentro ? { cor: paleta.bolha, vazada: false, apagada: false } : posicao === null ? vazia : { cor: paleta.neutra, vazada: false, apagada: true };
    }
    default:
      // A cor única não codifica nada; a unidade sem o valor do indicador (que o mapa mostra no lugar dela, 25/10/2026) fica
      // vazada, como todo valor não avaliável, nunca preenchida como se tivesse valor.
      return valorDe(item, p.indicador) === null ? vazia : { cor: paleta.bolha, vazada: false, apagada: false };
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
  /** Visão Trajetória: os valores observados nos períodos do meio da janela, relativos ao centro da bolha (na ordem do tempo). */
  trajeto: { competencia: string; valor: number; dx: number; dy: number }[] | null;
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
  /** Cometa da competência inicial à atual (visão Trajetória). */
  cometa: boolean;
  /** Visão Trajetória (24/10/2026): os períodos do meio da janela, valores observados do motor, como pontos no caminho do
   * cometa. */
  trajetoria?: boolean;
  vista: Vista; largura: number; rotuloDistancia: string;
  pintura: (item: PainelItem) => Pintura;
  /** Valores que o eixo precisa mostrar além dos itens (a linha de contexto do Brasil, as referências da base). */
  extras?: number[];
  /** Populações que a escala de tamanho precisa cobrir além dos itens (as referências da base, 25/10/2026). */
  extrasPopulacao?: number[];
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
  // Na Trajetória, os valores dos períodos do meio também cabem no eixo (o domínio das observações da tendência, do motor).
  const meio = p.trajetoria ? dominioDo("tendencia") ?? [] : [];
  const valores = [...(dominioDo(p.indicador) || p.itens.map(item => valorDe(item, p.indicador)).filter(ehNumero)),
    ...p.itens.filter(comRastro).map(item => inicialDe(item, p.indicador)).filter(ehNumero), ...meio, ...(p.extras || [])];
  const escala = escalaPossivel(valores, p.escala);
  const dominioIndicador = enquadrar(valores, escala);
  const populacoes = [...(dominioDo("populacao") ? [dominioDo("populacao")![1]] : p.itens.map(item => numero(item.populacao)).filter(ehNumero)),
    ...(p.cometa ? p.itens.map(item => inicialDe(item, "populacao")).filter(ehNumero) : []), ...(p.extrasPopulacao || [])];
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
  // Trajetória (24/10/2026): os períodos do meio da janela, como o motor os observou (sem imputar o que falta), só com o rastro
  // (sem a variação do motor, como num conjunto incomparável, não há caminho: RQ-REP-15).
  const trajetoDe = (d: typeof base[number], yFinal: number, yDe: (valor: number) => number): BolhaDesenho["trajeto"] => {
    if (!p.trajetoria || naVistaInicial || d.inicial === null) return null;
    const observacoes = (d.item.tendencia?.observacoes || []).slice(1, -1)
      .filter((obs): obs is { competencia: string; valor: number } => obs.valor !== null && Number.isFinite(obs.valor));
    return observacoes.length ? observacoes.map(obs => ({ competencia: obs.competencia, valor: obs.valor, dx: 0, dy: yDe(obs.valor) - yFinal })) : null;
  };
  const bolha = (d: typeof base[number], x: number, yFinal: number, yInicial: number | null, xInicial: number | null,
    yDe?: (valor: number) => number): BolhaDesenho => {
    const naInicial = naVistaInicial && yInicial !== null;
    const dx = xInicial !== null ? xInicial - x : 0, dy = yInicial !== null ? yInicial - yFinal : 0;
    return { id: d.item.id, tipo: d.item.tipo, item: d.item, x: naInicial && xInicial !== null ? xInicial : x, y: naInicial ? yInicial! : yFinal,
      r: naInicial ? d.rInicial : d.rFinal, visivel: d.visivel, valor: d.valor, inicial: d.inicial, variacao: d.variacao,
      referencia: !!d.item.referencia, rastro: !naVistaInicial && yInicial !== null && Math.hypot(dx, dy) >= 1 ? { dx, dy } : null,
      trajeto: yDe ? trajetoDe(d, yFinal, yDe) : null,
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
      return bolha(d, x, y(d.valor), d.inicial !== null ? y(d.inicial) : null, d.inicial !== null ? x : null, y);
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

/** Opacidade da bolha no gráfico: oculta quando não tem posição na vista; a pintura apagada (não atende, fora dos primeiros), mais
 * clara; as demais, inteiras. Marcar bolhas não esmaece as outras (25/10/2026): o anel escuro e o nome destacam as marcadas, como
 * no mapa. */
export const opacidadeDaBolha = (bolha: Pick<BolhaDesenho, "visivel" | "apagada">) => !bolha.visivel ? 0 : bolha.apagada ? 0.45 : 1;

/** Destaque da análise (26/10/2026, pedido do responsável): com uma comparação em exibição (2 ou 3 itens no gráfico), os
 * comparados. As demais bolhas esmaecem (opacidadeComDestaque) para a análise em foco não se misturar com o resto da seleção;
 * marcar, sozinho, continua sem esmaecer (25/10/2026). Vazio: nada esmaece. Na Análise Espacial, desde a Escolha dos territórios
 * (27/10/2026), toda bolha é da base: não há territórios base escolhidos um a um para destacar. Só estado visual: nada vai ao
 * motor. */
export function destaqueDaAnalise(comparar: readonly string[], noGrafico: ReadonlySet<string>): string[] {
  const comparados = comparar.filter(id => noGrafico.has(id));
  return comparados.length >= 2 ? [...new Set(comparados)] : [];
}
/** Opacidade das bolhas fora do destaque da análise. */
export const OPACIDADE_FORA_DO_DESTAQUE = 0.25;
/** Opacidade com o destaque da análise: fora dele, a bolha esmaece, sem nunca ficar mais forte que a pintura dela. */
export const opacidadeComDestaque = (bolha: Pick<BolhaDesenho, "id" | "visivel" | "apagada">, destaque: ReadonlySet<string> | null) => {
  const inteira = opacidadeDaBolha(bolha);
  return destaque && destaque.size > 0 && !destaque.has(bolha.id) ? Math.min(inteira, OPACIDADE_FORA_DO_DESTAQUE) : inteira;
};

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
  altura = 16): Map<string, Rotulo2> {
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
/** Largura aproximada de um texto de 12,5 px (Inter, o rótulo das bolhas desde a escala tipográfica de 28/10/2026), só para
 * afastar rótulos. */
export const larguraDoTexto = (texto: string, tamanho = 12.5) => Math.ceil(texto.length * tamanho * 0.56) + 4;

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
type Observacoes = (item: PainelItem) => { competencia: string; valor: number | null }[];
const observacoesDaTendencia: Observacoes = item => item.tendencia?.observacoes || [];
/** Domínio das séries: os valores observados do motor, enquadrados (só para desenhar). Por padrão, as observações da tendência;
 * na Série temporal (24/10/2026), as da série do intervalo (`observacoesDe`). */
export function dominioDasSeries(itens: PainelItem[], observacoesDe: Observacoes = observacoesDaTendencia): PainelDominio {
  const valores = itens.flatMap(item => observacoesDe(item).map(obs => obs.valor)).filter(ehNumero);
  return enquadrar(valores, "linear");
}
export type PontoSerie = { competencia: string; x: number; y: number; valor: number };
export type SerieDesenho = { id: string; rotulo: string; cor: string; familia: FamiliaTendencia | null; classe: string;
  pontos: PontoSerie[]; caminhos: string[]; fim: PontoSerie | null;
  /** Os pontos estão ligados por linha (falso no conjunto não comparável da Série temporal: só os pontos, RQ-REP-15). */
  ligada: boolean };
/** Linhas por competência: um ponto por observação; lacunas não são ligadas (sem imputar), sem reta ajustada. Na Série temporal
 * (24/10/2026): as observações do intervalo (`observacoesDe`), a cor única do gráfico (`corUnica`, sem classe) e, sem
 * comparabilidade (`ligar` falso), só os pontos. */
export function montarSeries(p: { itens: PainelItem[]; janela: string[]; dominio: PainelDominio; x0: number; x1: number; y0: number; y1: number;
  paleta?: PaletaDoGrafico; observacoesDe?: Observacoes; corUnica?: string; ligar?: (item: PainelItem) => boolean }):
  { series: SerieDesenho[]; marcasX: { competencia: string; x: number }[] } {
  const paleta = p.paleta ?? PALETA_CLARA;
  const observacoesDe = p.observacoesDe ?? observacoesDaTendencia;
  const tempos = posicoesTemporais(p.janela);
  const maximo = Math.max(1, ...tempos.values());
  const x = (c: string) => p.x0 + (p.x1 - p.x0) * ((tempos.get(c) ?? 0) / maximo);
  const y = (valor: number) => entre(fracao(valor, p.dominio, "linear"), p.y1, p.y0);
  const series = p.itens.map(item => {
    const tendencia = item.tendencia;
    const familia = !p.corUnica && tendencia?.avaliavel ? tendencia.familia ?? familiaDaClasse(tendencia.classe) : null;
    const ligada = p.ligar ? p.ligar(item) : true;
    const porCompetencia = new Map(observacoesDe(item).map(obs => [obs.competencia, obs.valor]));
    const pontos: PontoSerie[] = [], caminhos: string[] = [];
    let atual: PontoSerie[] = [];
    for (const competencia of [...tempos.keys()]) {
      const valor = porCompetencia.get(competencia);
      if (valor === null || valor === undefined) { if (atual.length > 1 && ligada) caminhos.push(caminho(atual)); atual = []; continue; }
      const ponto = { competencia, x: x(competencia), y: y(valor), valor };
      pontos.push(ponto); atual.push(ponto);
    }
    if (atual.length > 1 && ligada) caminhos.push(caminho(atual));
    return { id: item.id, rotulo: item.rotulo, cor: p.corUnica ?? (familia ? paleta.tendencia[familia] : paleta.naoAvaliavel), familia,
      classe: tendencia?.rotulo || "Não avaliável", pontos, caminhos, fim: pontos.at(-1) ?? null, ligada };
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

// ================================================================================================ tendência: quadro de setas
/** Avanço de um período para o seguinte pelo sinal da velocidade do motor (CAP-TEN-01): alta, queda ou pausa. Só lê o sinal; a
 * classe continua a do motor. */
export type SinalDoAvanco = "alta" | "queda" | "pausa";
export const sinalDoAvanco = (valor: number): SinalDoAvanco => valor > 0 ? "alta" : valor < 0 ? "queda" : "pausa";
export type PontoDaSeta = { competencia: string; valor: number; x: number; y: number };
export type SetaDoAvanco = { de: string; ate: string; valor: number; sinal: SinalDoAvanco; x1: number; y1: number; x2: number; y2: number;
  /** Ponta da seta, no meio do avanço, e o ângulo dele em graus (no sentido do tempo). */
  meioX: number; meioY: number; angulo: number };
/** Desenho de uma linha do quadro de setas (24/10/2026): um ponto por observação do motor (sem imputar o período sem valor) e uma
 * seta por velocidade do motor, ligando as duas observações que ela usou. X é a posição no tempo dentro da janela; Y, a escala
 * própria da linha (o desenho mostra a forma, e o valor fica ao lado e na dica), com amplitude mínima de 5% do maior valor, para
 * uma variação ínfima não parecer um salto. Só posiciona. */
export function montarSetas(t: TendenciaItem | null | undefined, janela: string[], caixa: { x0: number; x1: number; y0: number; y1: number }):
  { pontos: PontoDaSeta[]; setas: SetaDoAvanco[] } {
  if (!t) return { pontos: [], setas: [] };
  const tempos = posicoesTemporais(janela.length ? janela : t.observacoes.map(obs => obs.competencia));
  const fim = Math.max(1, ...tempos.values());
  const validas = t.observacoes.filter((obs): obs is { competencia: string; valor: number } => obs.valor !== null && Number.isFinite(obs.valor) &&
    tempos.has(obs.competencia));
  if (!validas.length) return { pontos: [], setas: [] };
  const valores = validas.map(obs => obs.valor);
  const minimo = Math.min(...valores), maximo = Math.max(...valores);
  const amplitude = Math.max(maximo - minimo, Math.max(Math.abs(minimo), Math.abs(maximo)) * 0.05, 1e-9);
  const piso = (minimo + maximo) / 2 - amplitude / 2;
  const x = (c: string) => caixa.x0 + (caixa.x1 - caixa.x0) * (tempos.get(c)! / fim);
  const y = (valor: number) => caixa.y1 - (caixa.y1 - caixa.y0) * ((valor - piso) / amplitude);
  const pontos = validas.map(obs => ({ competencia: obs.competencia, valor: obs.valor, x: x(obs.competencia), y: y(obs.valor) }));
  const porCompetencia = new Map(pontos.map(ponto => [ponto.competencia, ponto]));
  const setas = t.velocidades.flatMap(v => {
    const a = porCompetencia.get(v.de), b = porCompetencia.get(v.ate);
    return a && b ? [{ de: v.de, ate: v.ate, valor: v.valor, sinal: sinalDoAvanco(v.valor), x1: a.x, y1: a.y, x2: b.x, y2: b.y,
      meioX: (a.x + b.x) / 2, meioY: (a.y + b.y) / 2, angulo: Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI }] : [];
  });
  return { pontos, setas };
}
/** Ordem das linhas do quadro: a posição do motor quando a ordenação está em uso; senão, a classe na ordem da SPEC (os não
 * avaliáveis no fim) e, dentro dela, a variação entre o primeiro e o último período, da maior para a menor (sem valor no fim);
 * no empate, o nome. Não é ranking de classe: só agrupa. */
export function ordemDoQuadro(itens: PainelItem[], indicador: PainelIndicador, pelaPosicao: boolean): PainelItem[] {
  const indiceDaClasse = (item: PainelItem) => {
    const indice = item.tendencia?.avaliavel ? CLASSES_TENDENCIA.findIndex(classe => classe.codigo === item.tendencia!.classe) : -1;
    return indice < 0 ? CLASSES_TENDENCIA.length : indice;
  };
  const porNome = (a: PainelItem, b: PainelItem) => a.rotulo.localeCompare(b.rotulo, "pt-BR");
  if (pelaPosicao) return [...itens].sort((a, b) => (a.ordem?.posicao ?? Infinity) - (b.ordem?.posicao ?? Infinity) || porNome(a, b));
  return [...itens].sort((a, b) => {
    const va = variacaoDe(a, indicador), vb = variacaoDe(b, indicador);
    return indiceDaClasse(a) - indiceDaClasse(b) || (va === null ? 1 : 0) - (vb === null ? 1 : 0) || (vb ?? 0) - (va ?? 0) || porNome(a, b);
  });
}
/** O que a linha diz, para os leitores de tela: a classe do motor e cada período com o valor e o avanço até ele. */
export function descricaoDasSetas(item: PainelItem, indicador: PainelIndicador): string {
  const t = item.tendencia;
  if (!t) return item.rotulo + ": sem tendência.";
  const contagem = INDICADORES[indicador].contagem;
  const sinalAte = new Map(t.velocidades.map(v => [v.ate, sinalDoAvanco(v.valor)]));
  const periodos = t.observacoes.map(obs => exibirCompetencia(obs.competencia) + ": " + (obs.valor === null ? "sem valor"
    : formatarNumero(obs.valor, contagem) + (sinalAte.has(obs.competencia) ? ", " + sinalAte.get(obs.competencia) : "")));
  return item.rotulo + ": " + (t.avaliavel ? t.rotulo : "Não avaliável") + ". " + periodos.join("; ") + ".";
}

/** CAP-TEN-01 exige ao menos quatro competências; a mudança (CAP-TMP-01), duas. */
export const MINIMO_TENDENCIA = 4;
/** Período da tendência (24/10/2026, pedido do responsável): o ritmo, anual ou semestral, e a janela são os últimos 4 períodos
 * desse ritmo, contados da competência mais recente: o mínimo de DA-15 (4 períodos, 3 avanços). A análise abre no anual
 * (janelaPadrao), à vista no campo Período, e a pessoa pode trocar. O ritmo só escolhe as competências; o método é o mesmo
 * (CAP-TEN-01). */
export type RitmoTendencia = "anual" | "semestral";
export const RITMOS_TENDENCIA: { ritmo: RitmoTendencia; rotulo: string; plural: string; meses: number; passo: string }[] = [
  { ritmo: "anual", rotulo: "Anual", plural: "anuais", meses: 12, passo: "um por ano" },
  { ritmo: "semestral", rotulo: "Semestral", plural: "semestrais", meses: 6, passo: "um a cada seis meses, mais ou menos" },
];
/** Folga, em meses, entre um período e o seguinte: janeiro e junho ficam a 5 e 7 meses e contam como semestrais. */
const FOLGA_DO_RITMO = 2;
/** Posição em meses de uma competência AAAAMM ou de um ano AAAA (só o ritmo anual cabe nos anos). */
function mesDoPeriodo(c: string): number | null {
  if (ehAaaamm(c)) return Number(c.slice(0, 4)) * 12 + Number(c.slice(4)) - 1;
  return /^\d{4}$/.test(c) ? Number(c) * 12 : null;
}
/** Os últimos 4 períodos de um ritmo: da competência mais recente para trás, a cada passo a competência mais perto de 12 (ou 6)
 * meses antes, com folga de 2 meses (no empate, a mais recente). Sem 4 períodos assim, nenhum ([]): o ritmo fica indisponível. */
export function janelaDoRitmo(ritmo: RitmoTendencia, periodos: string[]): string[] {
  const passo = RITMOS_TENDENCIA.find(item => item.ritmo === ritmo)!.meses;
  const comMes = cronologica(periodos).map(c => ({ c, mes: mesDoPeriodo(c) })).filter((item): item is { c: string; mes: number } => item.mes !== null);
  const janela: string[] = [];
  let atual = comMes.at(-1);
  while (atual && janela.length < MINIMO_TENDENCIA) {
    janela.unshift(atual.c);
    const alvo = atual.mes - passo, antes: { c: string; mes: number } = atual;
    atual = comMes.filter(item => item.mes < antes.mes && Math.abs(item.mes - alvo) <= FOLGA_DO_RITMO)
      .sort((a, b) => Math.abs(a.mes - alvo) - Math.abs(b.mes - alvo) || b.mes - a.mes)[0];
  }
  return janela.length === MINIMO_TENDENCIA ? janela : [];
}
/** O ritmo de uma janela: o que dá exatamente estas competências nesta base; senão (nenhuma janela escolhida), nenhum. */
export function ritmoDaJanela(janela: string[], periodos: string[]): RitmoTendencia | null {
  if (janela.length !== MINIMO_TENDENCIA) return null;
  return RITMOS_TENDENCIA.find(item => janelaDoRitmo(item.ritmo, periodos).join() === janela.join())?.ritmo ?? null;
}
/** Cada ritmo na base: a janela e, quando não há 4 períodos nesse ritmo até a competência mais recente, o motivo. */
export function ritmosDaBase(periodos: string[]): { ritmo: RitmoTendencia; rotulo: string; janela: string[]; motivo: string | null }[] {
  return RITMOS_TENDENCIA.map(item => {
    const janela = janelaDoRitmo(item.ritmo, periodos);
    return { ritmo: item.ritmo, rotulo: item.rotulo, janela,
      motivo: janela.length ? null : "Esta base não tem 4 períodos " + item.plural + " seguidos (" + item.passo + ") até a competência mais recente." };
  });
}
/** O ritmo pelos intervalos de uma janela: cerca de 12 meses entre as competências é o anual; cerca de 6, o semestral (com a
 * mesma folga de 2 meses); senão, nenhum. Para a janela que chega da conversa ou de outra rota. */
export function ritmoDosIntervalos(janela: string[]): RitmoTendencia | null {
  const meses = cronologica(janela).map(mesDoPeriodo);
  if (meses.length < 2 || meses.some(mes => mes === null)) return null;
  const passos = meses.slice(1).map((mes, indice) => (mes as number) - (meses[indice] as number));
  return RITMOS_TENDENCIA.find(item => passos.every(passo => Math.abs(passo - item.meses) <= FOLGA_DO_RITMO))?.ritmo ?? null;
}
/** "06/2021, 06/2022, 06/2023 e 06/2024": as competências da janela, para o campo Período. */
export const listaDeCompetencias = (janela: string[]) => janela.length <= 1 ? janela.map(exibirCompetencia).join("")
  : janela.slice(0, -1).map(exibirCompetencia).join(", ") + " e " + exibirCompetencia(janela[janela.length - 1]);
export const TEXTO_ESCOLHA_DO_PERIODO = "Escolha o período da tendência, anual ou semestral: a análise usa os últimos 4 períodos.";
/** A janela que chega de fora do campo Período (a conversa ou outra rota). Não há janela longa (24/10/2026): vale o ritmo dos
 * intervalos dela, e a janela passa a ser os últimos 4 períodos desse ritmo; sem ritmo, ou sem 4 períodos nele, nenhuma
 * janela, e a mensagem diz por quê. Competências fora da base ficam de fora. */
export function janelaPeloRitmo(pedida: unknown[], periodos: string[]): { janela: string[]; mensagem: string | null } {
  const daBase = new Set(periodos);
  const lida = cronologica(pedida.filter((p): p is string => typeof p === "string" && daBase.has(p)));
  const ritmo = ritmoDosIntervalos(lida);
  const item = RITMOS_TENDENCIA.find(r => r.ritmo === ritmo);
  if (!item) return { janela: [], mensagem: TEXTO_ESCOLHA_DO_PERIODO };
  const janela = janelaDoRitmo(item.ritmo, periodos);
  if (!janela.length) return { janela, mensagem: "Esta base não tem 4 períodos " + item.plural + " seguidos até a competência mais recente." };
  return { janela, mensagem: janela.join() === lida.join() ? null
    : "A tendência usa os últimos 4 períodos " + item.plural + ": " + listaDeCompetencias(janela) + "." };
}
export const TEXTO_MINIMO_TENDENCIA = "A análise de tendência exige quatro observações válidas.";

// ================================================================================================ dica
export type LinhaDica = { rotulo: string; valor: string };
export type Dica = { titulo: string; subtitulo: string; linhas: LinhaDica[]; notas: string[]; acao: string | null };
export type ContextoDica = { indicador: PainelIndicador; competencia: string; competenciaInicial: string | null; distancia: boolean;
  variacao: boolean; tendencia: boolean; nomes: Map<string, string>; limiares?: number[]; rotulos: RotulosTerritoriais;
  /** Unidades de um grupo (para a ação "Ver os N municípios" na bolha do grupo). */
  unidadesDoGrupo?: (id: string) => number | null;
  /** Com a Escolha dos territórios (27/10/2026), a referência é a mais próxima de cada item. */
  porItem?: boolean;
  /** Visão Trajetória: cada período da janela com o valor observado. */
  trajetoria?: boolean };

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
    const porItem = !!contexto.porItem;
    linhas.push({ rotulo: item.referencia ? "Distância (membro da referência)" : conjunto && !porItem ? "Distância (membro mais próximo)"
      : porItem ? "Distância até a referência mais próxima" : "Distância até a referência",
      valor: distancia === null ? "Não avaliável" : formatarNumero(distancia) + " km" });
    if (conjunto && maxima !== null) linhas.push({ rotulo: "Distância (membro mais distante)", valor: formatarNumero(maxima) + " km" });
    if (item.referenciaDoItem?.length && !item.referencia)
      linhas.push({ rotulo: porItem ? "Referência mais próxima" + (item.referenciaDoItem.length > 1 ? " (empate)" : "")
        : item.referenciaDoItem.length > 1 ? "Membros da referência mais próximos (empate)" : "Membro da referência mais próximo",
        valor: item.referenciaDoItem.map(ref => ref.rotulo).join(", ") });
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
    // Trajetória (24/10/2026): o valor observado em cada período do meio da janela, com o sinal do avanço desde o anterior.
    if (contexto.trajetoria && item.tendencia) {
      const observacoes = item.tendencia.observacoes;
      observacoes.slice(1, -1).forEach((obs, indice) => {
        const anterior = observacoes[indice].valor;
        const sinal = obs.valor === null || anterior === null ? "" : obs.valor > anterior ? " ▲" : obs.valor < anterior ? " ▼" : " ►";
        linhas.push({ rotulo: especie.rotulo + " em " + exibirCompetencia(obs.competencia),
          valor: obs.valor === null ? "sem valor" : formatarNumero(obs.valor, especie.contagem) + sinal });
      });
    }
    if (variacao === null) notas.push(motivosDe(item, "variacao")[0] || MOTIVO_PADRAO.variacao(contexto.indicador));
  }
  if (contexto.tendencia && item.tendencia) {
    linhas.push({ rotulo: "Tendência", valor: item.tendencia.rotulo });
    const explicacao = explicacaoDaTendencia(item.tendencia);
    if (explicacao) notas.push(explicacao);
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

// ================================================================================================ competências
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
/** Tudo o que a pessoa escolheu e que vai ao motor (o que é só estado visual fica no componente). A Seleção de Territórios
 * (24/10/2026) tem três níveis, um em análise por vez (`nivel`, RQ-DAD-30: nenhum nível é somado a outro), e cada um guarda a
 * sua escolha: `base` (os municípios, cumulativos entre os estados), `estados` (os estados como unidades) e o Brasil, que é uma
 * unidade só. Trocar de nível não apaga a escolha dos outros. */
export type DefinicaoAnalise = {
  familia: Familia; indicador: PainelIndicador; nivel: PainelNivel; base: PainelMunicipios; estados: string[]; competencia: string;
  categoria: string; conjuntos: PainelConjuntoPedido[];
  /** A Escolha dos territórios da Análise Espacial (27/10/2026): a consulta calculada (null até o primeiro "Calcular"). O
   * rascunho fica na janela; aqui, só o que vai ao motor. */
  consulta: ConsultaTerritorios | null; faixasDistancia: number[];
  janela: string[]; visao: Visao; agrupar: Agrupar; condicoes: CondicaoPedido[]; ordenar: OrdenarPedido | null;
  comparar: string[]; rotatividade: { inicial: string; final: string } | null; premissas: Premissas;
  /** Intervalo da Série temporal (24/10/2026): as competências escolhidas, em ordem; vazio = a extensão inteira da base (do
   * primeiro ao último período que ela tem, lidos dos dados a cada pedido). */
  serie?: string[];
};
/** Estado inicial da análise: em qualquer fonte, nenhum território marcado (23/10/2026); a área espera a escolha na Seleção de
 * Territórios ou na conversa. Na planilha sem população, o indicador começa na quantidade (o motor recusa a densidade sem
 * população), e as premissas escolhidas no painel Colunas vão em todo pedido. */
export function definicaoInicial(p: { tipo: "brasil" | "arquivo" | null; periodos: string[]; categoria: string; familia?: Familia;
  temGrupos: boolean; temPopulacao?: boolean; premissas?: Premissas }): DefinicaoAnalise {
  return { familia: p.familia ?? "distribuicao", indicador: p.temPopulacao === false ? "quantidade" : "densidade",
    // Sem seleção automática (23/10/2026): a base carregada abre sem territórios marcados, no nível dos municípios; a pessoa
    // escolhe na Seleção de Territórios (o Brasil, os estados ou os municípios) ou pela conversa.
    nivel: "municipios", base: { ...BASE_VAZIA }, estados: [], competencia: maisRecente(p.periodos),
    categoria: p.categoria, conjuntos: [], consulta: null, faixasDistancia: [],
    janela: [], visao: "classes", agrupar: { tipo: "nenhum", faixas: [] }, condicoes: [], ordenar: null, comparar: [], rotatividade: null,
    premissas: p.tipo === "arquivo" ? { ...(p.premissas ?? {}) } : {}, serie: [] };
}
/** O período com que a Análise de Tendência abre (24/10/2026, pedido do responsável, no lugar de "sem ritmo padrão"): o anual,
 * quando a base tem 4 períodos anuais até a competência mais recente; senão, o único ritmo que a base tem (RQ-GOV-14: um só valor
 * aplicável resolve o parâmetro); senão, nenhum, e o aviso pede a escolha. A escolha fica à vista no campo Período, que lista as 4
 * competências, e a pessoa pode trocar pelo semestral. */
export function janelaPadrao(periodos: string[]): string[] {
  const ritmos = ritmosDaBase(periodos).filter(item => item.janela.length);
  return (ritmos.find(item => item.ritmo === "anual") ?? (ritmos.length === 1 ? ritmos[0] : undefined))?.janela ?? [];
}
/** As competências da Série temporal: as escolhidas ou, sem escolha, todas as da base, em ordem cronológica. */
export const intervaloDaSerie = (def: Pick<DefinicaoAnalise, "serie">, periodos: string[]) =>
  def.serie?.length ? cronologica(def.serie) : cronologica(periodos);
/** O intervalo da Série temporal entre duas competências da base (inclusive): o que a pessoa escolhe nos campos De e Até. Do
 * primeiro ao último período da base, o intervalo vazio (toda a série). */
export function intervaloEntre(periodos: string[], inicio: string, fim: string): string[] {
  const todas = cronologica(periodos);
  const [a, b] = comparar(inicio, fim) <= 0 ? [inicio, fim] : [fim, inicio];
  const escolhidas = todas.filter(c => comparar(c, a) >= 0 && comparar(c, b) <= 0);
  return escolhidas.length === todas.length ? [] : escolhidas;
}
/** "Maior" ou "menor" pedidos na conversa (decisão 4, 25/10/2026): a ordem do critério vira o operador do filtro da Referência
 * na Escolha dos territórios ("maior densidade" é Densidade "acima de"; "menos populosos", População "abaixo de"). O valor continua
 * com a pessoa: nada é escolhido pela posição na ordem (CAP-REF-01 pede uma condição, CAP-SUB-01). */
export const operadorDoCriterio = (criterio: PainelCriterio | null | undefined): ">" | "<" | null =>
  criterio ? (criterio.ordem === "desc" ? ">" : "<") : null;
/** As Grandes Regiões da base do Brasil, pelo primeiro dígito do código IBGE do estado (a regra do motor e da conversa). */
export const REGIOES_DO_BRASIL: { id: string; nome: string }[] = [
  { id: "1", nome: "Norte" }, { id: "2", nome: "Nordeste" }, { id: "3", nome: "Sudeste" }, { id: "4", nome: "Sul" }, { id: "5", nome: "Centro-Oeste" }];
export const regiaoDoEstado = (prefixo: string) => REGIOES_DO_BRASIL.find(regiao => regiao.id === prefixo.charAt(0))?.nome ?? null;

// ================================================================================================ escolha dos territórios
/** Escolha dos territórios (27/10/2026, comando Seleção de Territórios, no lugar do território de referência por elegibilidade):
 * base e referência escolhidas do mesmo jeito, em três etapas (de onde partir, filtros por indicador combinados por E e a escolha
 * de todos ou só dos marcados), num objeto de consulta serializável. Ele é a fonte de verdade da janela: os controles leem e
 * escrevem nele, a frase-resumo sai dele (por modelo, nunca pelo LLM) e o motor o recebe (`consulta` de /api/painel e de
 * /api/painel/territorios). Toda seleção, contagem e distância vem do motor; aqui ficam só o objeto, o que falta completar e a
 * frase. Os municípios são identificados como na base (code:<código IBGE>); as regiões, pelo nome; os estados, pelo prefixo do
 * código (numa planilha, pelo valor da coluna-mãe, como em base.estados). A distância é sempre a geodésica até a referência mais
 * próxima de cada município da base e aparece no eixo X do resultado; o filtro de distância da base saiu no mesmo dia, a pedido do
 * responsável (para filtrar por ela, as Condições). */
export type TipoPartida = "pais" | "regioes" | "ufs" | "selecao_previa" | "mesma_uf_da_base" | "mesma_regiao_da_base";
export type PartirDe = { tipo: TipoPartida; regioes: string[]; ufs: string[] };
export type IndicadorDoFiltro = "densidade" | "populacao" | "quantidade";
export type OperadorDoFiltro = "<" | "<=" | ">" | ">=";
export type FiltroDaConsulta = { indicador: IndicadorDoFiltro; operador: OperadorDoFiltro; valor: number | null };
export type EscolhaDaConsulta = { modo: "todos" | "marcados"; municipios: string[] };
export type LadoDaConsulta = { partir_de: PartirDe; filtros: FiltroDaConsulta[]; escolha: EscolhaDaConsulta };
export type DistanciaDaConsulta = { medida: "geodesica"; ate: "referencia_mais_proxima" };
export type ConsultaTerritorios = { base: LadoDaConsulta; referencia: LadoDaConsulta; distancia: DistanciaDaConsulta };
export type Lado = "base" | "referencia";
export const LADOS: Lado[] = ["base", "referencia"];
export const NOMES_DOS_LADOS: Record<Lado, string> = { base: "Base", referencia: "Referência" };
export const MAX_FILTROS = 12;
const DISTANCIA_DA_CONSULTA: DistanciaDaConsulta = { medida: "geodesica", ate: "referencia_mais_proxima" };
export const OPERADORES_DO_FILTRO: OperadorDoFiltro[] = ["<", "<=", ">", ">="];
export const TEXTO_DOS_OPERADORES: Record<OperadorDoFiltro, string> = { "<": "abaixo de", "<=": "até", ">": "acima de", ">=": "a partir de" };
export const NOMES_DOS_FILTROS: Record<IndicadorDoFiltro, string> = { densidade: "Densidade", populacao: "População", quantidade: "Quantidade" };
export const UNIDADES_DOS_FILTROS: Record<IndicadorDoFiltro, string> = { densidade: "por 1.000 hab.", populacao: "habitantes",
  quantidade: "profissionais" };
/** O texto de apoio dos filtros (o comando pede que diga onde ficam OU e NÃO). */
export const TEXTO_DE_APOIO_DOS_FILTROS = "Densidade é profissionais por 1.000 habitantes. Os filtros valem juntos (E); OU e NÃO ficam em " +
  "Critérios combinados.";
/** A nota da aba Referência. */
export const notaDaDistanciaDaConsulta = (rotulos: RotulosTerritoriais) => "Distância em linha reta (geodésica) até a referência mais " +
  "próxima de cada " + rotulos.unidade.singular + " da base.";

const ladoInicial = (tipo: TipoPartida): LadoDaConsulta => ({ partir_de: { tipo, regioes: [], ufs: [] }, filtros: [],
  escolha: { modo: "todos", municipios: [] } });
/** A consulta com que a janela abre: a base parte da seleção prévia (os territórios já selecionados; sem eles, do país inteiro), e
 * a referência, do país inteiro, sem filtros. Nada é calculado até "Calcular". */
export const consultaInicial = (c: { comSelecao: boolean }): ConsultaTerritorios => ({
  base: ladoInicial(c.comSelecao ? "selecao_previa" : "pais"), referencia: ladoInicial("pais"), distancia: { ...DISTANCIA_DA_CONSULTA } });

const TIPOS_DA_BASE = new Set<string>(["pais", "regioes", "ufs", "selecao_previa"]);
const TIPOS_DA_REFERENCIA = new Set<string>([...TIPOS_DA_BASE, "mesma_uf_da_base", "mesma_regiao_da_base"]);
const comoObjeto = (bruto: unknown) => bruto && typeof bruto === "object" && !Array.isArray(bruto) ? bruto as Record<string, unknown> : null;
const listaDeTextos = (bruto: unknown) => bruto === undefined ? [] : Array.isArray(bruto) && bruto.every(valor => typeof valor === "string")
  ? [...bruto] as string[] : null;
function lerLado(bruto: unknown, lado: Lado): LadoDaConsulta | null {
  const o = comoObjeto(bruto), partir = comoObjeto(o?.partir_de);
  if (!o || !partir || typeof partir.tipo !== "string" || !(lado === "base" ? TIPOS_DA_BASE : TIPOS_DA_REFERENCIA).has(partir.tipo)) return null;
  const regioes = listaDeTextos(partir.regioes), ufs = listaDeTextos(partir.ufs);
  const brutos = o.filtros === undefined ? [] : o.filtros;
  if (!regioes || !ufs || !Array.isArray(brutos) || brutos.length > MAX_FILTROS) return null;
  const filtros: FiltroDaConsulta[] = [];
  for (const bruto of brutos) {
    const f = comoObjeto(bruto);
    if (!f || typeof f.indicador !== "string" || typeof f.operador !== "string") return null;
    const indicador = f.indicador as IndicadorDoFiltro, operador = f.operador as OperadorDoFiltro;
    const valido = ["densidade", "populacao", "quantidade"].includes(indicador) && OPERADORES_DO_FILTRO.includes(operador);
    if (!valido || (f.valor !== null && (typeof f.valor !== "number" || !Number.isFinite(f.valor) || f.valor < 0))) return null;
    filtros.push({ indicador, operador, valor: f.valor as number | null });
  }
  const escolha = o.escolha === undefined ? { modo: "todos" } : comoObjeto(o.escolha);
  const municipios = listaDeTextos(escolha?.municipios);
  if (!escolha || (escolha.modo !== "todos" && escolha.modo !== "marcados") || !municipios) return null;
  return { partir_de: { tipo: partir.tipo as TipoPartida, regioes, ufs }, filtros, escolha: { modo: escolha.modo, municipios } };
}
/** Lê uma consulta (estado salvo, pedido futuro da conversa): devolve a mesma consulta, campo a campo, ou null quando a forma não
 * confere. Serializar e ler de novo não perde nada (critério 18 do comando). */
export function lerConsulta(bruto: unknown): ConsultaTerritorios | null {
  const o = comoObjeto(bruto);
  if (!o) return null;
  const base = lerLado(o.base, "base"), referencia = lerLado(o.referencia, "referencia"), distancia = comoObjeto(o.distancia);
  if (!base || !referencia) return null;
  if (o.distancia !== undefined && (!distancia || distancia.medida !== "geodesica" || distancia.ate !== "referencia_mais_proxima")) return null;
  return { base, referencia, distancia: { ...DISTANCIA_DA_CONSULTA } };
}
const ordemDasRegioes = (nome: string) => REGIOES_DO_BRASIL.findIndex(regiao => regiao.nome === nome);
function ladoParaOMotor(lado: LadoDaConsulta): LadoDaConsulta {
  const { tipo } = lado.partir_de;
  return { partir_de: { tipo, regioes: tipo === "regioes" ? [...new Set(lado.partir_de.regioes)].sort((a, b) => ordemDasRegioes(a) - ordemDasRegioes(b)) : [],
      ufs: tipo === "ufs" ? [...new Set(lado.partir_de.ufs)].sort(comparar) : [] },
    filtros: lado.filtros.map(filtro => ({ ...filtro })),
    escolha: { modo: lado.escolha.modo, municipios: lado.escolha.modo === "marcados" ? [...new Set(lado.escolha.municipios)].sort(comparar) : [] } };
}
/** A consulta como o motor a recebe: só o que vale para cada escolha (as regiões com "regiões", os estados com "estados", os
 * marcados com "Só os que eu marcar"), em ordem. A janela guarda o resto no rascunho, para a troca de opção não perder o que foi
 * marcado. */
export const consultaParaOMotor = (c: ConsultaTerritorios): ConsultaTerritorios => ({ base: ladoParaOMotor(c.base),
  referencia: ladoParaOMotor(c.referencia), distancia: { ...DISTANCIA_DA_CONSULTA } });
/** A mesma consulta para o motor: "A consulta mudou" só quando muda o que ele calcula. */
export const mesmaConsulta = (a: ConsultaTerritorios | null | undefined, b: ConsultaTerritorios | null | undefined) =>
  !!a && !!b && JSON.stringify(consultaParaOMotor(a)) === JSON.stringify(consultaParaOMotor(b));
/** O que falta completar em cada lado, na ordem das etapas, com os textos do comando (os mesmos do motor): desativam "Calcular" e
 * aparecem no rodapé e no status da aba. Filtro sem valor não corta nada até ser preenchido. */
export function pendenciasDoLado(c: ConsultaTerritorios, lado: Lado, rotulos: RotulosTerritoriais): string[] {
  const unidade = rotulos.unidade, grupo = rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const { partir_de: partir, filtros, escolha } = c[lado];
  const faltas: string[] = [];
  if (partir.tipo === "regioes" && !partir.regioes.length) faltas.push("escolha ao menos uma região");
  if (partir.tipo === "ufs" && !partir.ufs.length) faltas.push("escolha ao menos " + (fem(grupo) ? "uma " : "um ") + grupo.singular);
  if (filtros.some(filtro => filtro.valor === null)) faltas.push("preencha o valor do filtro");
  if (escolha.modo === "marcados" && !escolha.municipios.length) faltas.push("marque ao menos " + (fem(unidade) ? "uma " : "um ") + unidade.singular);
  return faltas;
}
export const pendenciasDaConsulta = (c: ConsultaTerritorios, rotulos: RotulosTerritoriais): Record<Lado, string[]> =>
  ({ base: pendenciasDoLado(c, "base", rotulos), referencia: pendenciasDoLado(c, "referencia", rotulos) });
/** "Base incompleta: escolha ao menos uma região." */
export const textoDaPendencia = (lado: Lado, falta: string) => NOMES_DOS_LADOS[lado] + " incompleta: " + falta + ".";
/** O valor digitado num filtro: na população e na quantidade, inteiros; na densidade, decimais. */
export const lerValorDoFiltro = (texto: string, indicador: IndicadorDoFiltro) => lerValorDeCorte(texto, indicador);
export const escreverValorDoFiltro = (valor: number | null) => valor === null ? "" : ate(6).format(valor);

/** Um trecho da frase-resumo: o texto e se o lado está incompleto (o trecho vira "base incompleta" ou "referência incompleta"). */
export type TrechoDaFrase = { texto: string; incompleta: boolean };
export type ContextoDaFrase = { rotulos: RotulosTerritoriais; brasil: boolean; grupos: GrupoInfo[]; nomes: Map<string, string> };
const NOMES_NA_FRASE = 3;
/** "MANAUS (AM), TEFE (AM), BELEM (PA) e mais 2". */
function nomesNaFrase(ids: string[], nomes: Map<string, string>): string {
  const lista = ids.slice(0, NOMES_NA_FRASE).map(id => nomes.get(id) || id);
  return ids.length > NOMES_NA_FRASE ? lista.join(", ") + " e mais " + (ids.length - NOMES_NA_FRASE) : emLista(lista);
}
/** De onde o lado parte, com a preposição: "de todo o país", "do Norte e do Nordeste", "do Acre", "da seleção prévia". */
function deOnde(partir: PartirDe, c: ContextoDaFrase): string {
  const grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  if (partir.tipo === "pais") return c.brasil ? "de todo o país" : "de toda a planilha";
  if (partir.tipo === "selecao_previa") return "da seleção prévia";
  if (partir.tipo === "regioes") return emLista(ladoParaOMotor({ partir_de: partir, filtros: [], escolha: { modo: "todos", municipios: [] } })
    .partir_de.regioes.map(nome => "do " + nome));
  const ufs = [...partir.ufs].sort(comparar);
  const de = (id: string) => {
    const g = c.grupos.find(item => item.id === id);
    return g?.rotuloGrupo ? g.rotuloGrupo.split(" ").slice(1).join(" ") : "de " + (g?.nome || id);
  };
  if (ufs.length > NOMES_NA_FRASE) return ufs.slice(0, NOMES_NA_FRASE).map(de).join(", ") + " e de mais " + quantos(ufs.length - NOMES_NA_FRASE, grupo);
  return emLista(ufs.map(de));
}
/** Os filtros na frase, com o mesmo indicador junto para a faixa: "densidade a partir de 0,5 e abaixo de 1". */
function filtrosNaFrase(filtros: FiltroDaConsulta[]): string[] {
  const porIndicador = new Map<IndicadorDoFiltro, string[]>();
  for (const filtro of filtros)
    porIndicador.set(filtro.indicador, [...porIndicador.get(filtro.indicador) ?? [],
      TEXTO_DOS_OPERADORES[filtro.operador] + " " + escreverValorDoFiltro(filtro.valor)]);
  return [...porIndicador.entries()].map(([indicador, partes]) => NOMES_DOS_FILTROS[indicador].toLocaleLowerCase("pt-BR") + " " + partes.join(" e "));
}
/** A base na frase: "Municípios do Norte com densidade abaixo de 0,5 e população acima de 20.000"; sem filtro, "Municípios do
 * Norte"; no modo marcados, os nomes (até três; depois, "e mais N"). */
function fraseDaBase(lado: LadoDaConsulta, c: ContextoDaFrase): string {
  if (lado.escolha.modo === "marcados") return nomesNaFrase(lado.escolha.municipios, c.nomes);
  const indicadores = filtrosNaFrase(lado.filtros);
  return maiuscula(c.rotulos.unidade.plural) + " " + deOnde(lado.partir_de, c) + (indicadores.length ? " com " + emLista(indicadores) : "");
}
/** O recorte da referência conforme a base, na frase: "do mesmo estado" (numa planilha, "da mesma província"), "da mesma região";
 * com `em`, "no mesmo estado", "na mesma região". Null quando a referência não depende de cada território da base. */
function recorteDaReferencia(tipo: TipoPartida, c: ContextoDaFrase, em = false): string | null {
  const grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const feminino = tipo === "mesma_regiao_da_base" || (tipo === "mesma_uf_da_base" && !c.brasil && fem(grupo));
  const nome = tipo === "mesma_uf_da_base" ? (c.brasil ? "estado" : grupo.singular) : tipo === "mesma_regiao_da_base" ? "região" : null;
  return nome && (em ? "n" : "d") + (feminino ? "a mesma " : "o mesmo ") + nome;
}
/** A referência na frase (27/10/2026, pedido do responsável: "o mais próximo da Bahia" parecia o mais próximo do estado, e não de
 * cada município da base): "o mais próximo de cada um, entre os municípios do Acre com densidade acima de 2"; "… entre os
 * municípios de todo o país …"; conforme a base, "… entre os municípios do mesmo estado …" (ou "da mesma região"); com um só
 * marcado, o nome dele ("MANAUS (AM)"); com vários, "o mais próximo de cada um, entre MANAUS (AM) e BELEM (PA)". */
function fraseDaReferencia(lado: LadoDaConsulta, c: ContextoDaFrase): string {
  const unidade = c.rotulos.unidade, f = fem(unidade), tipo = lado.partir_de.tipo;
  const deCadaUm = (f ? "a mais próxima de cada uma" : "o mais próximo de cada um") + ", entre ";
  if (lado.escolha.modo === "marcados") {
    // Os marcados são fixos: o recorte só diz algo quando é o de cada território da base (mesma UF ou mesma região).
    const marcados = lado.escolha.municipios, recorte = recorteDaReferencia(tipo, c), noRecorte = recorteDaReferencia(tipo, c, true);
    return marcados.length === 1 ? nomesNaFrase(marcados, c.nomes) + (recorte ? ", para " + artigo(unidade, true) + " " + unidade.plural + " " + recorte : "")
      : deCadaUm + nomesNaFrase(marcados, c.nomes) + (noRecorte ? ", " + noRecorte : "");
  }
  const indicadores = filtrosNaFrase(lado.filtros);
  return deCadaUm + artigo(unidade, true) + " " + unidade.plural + " " + (recorteDaReferencia(tipo, c) ?? deOnde(lado.partir_de, c)) +
    (indicadores.length ? " com " + emLista(indicadores) : "");
}
/** A frase-resumo da janela, no formato "{Base} → referência: {Referência}", montada por modelo a partir da consulta (nunca pelo
 * LLM). Lado incompleto vira "base incompleta" ou "referência incompleta", destacado na tela. */
export function fraseDaConsulta(consulta: ConsultaTerritorios, c: ContextoDaFrase): Record<Lado, TrechoDaFrase> {
  const pendencias = pendenciasDaConsulta(consulta, c.rotulos);
  return {
    base: pendencias.base.length ? { texto: "base incompleta", incompleta: true } : { texto: fraseDaBase(consulta.base, c), incompleta: false },
    referencia: pendencias.referencia.length ? { texto: "referência incompleta", incompleta: true }
      : { texto: fraseDaReferencia(consulta.referencia, c), incompleta: false },
  };
}
export const textoDaFraseDaConsulta = (frase: Record<Lado, TrechoDaFrase>) => frase.base.texto + " → referência: " + frase.referencia.texto;
/** Os candidatos à referência (27/10/2026, pedido do responsável: "175 municípios" na aba Referência parecia a referência, quando
 * só o mais próximo de cada território da base é usado): o conjunto de referências (CAP-REF-01) dito como candidatos, "175
 * candidatos" (numa unidade feminina, "candidatas"). */
export const quantosCandidatos = (n: number, unidade: Rotulo) => inteiro.format(n) + (fem(unidade) ? " candidata" : " candidato") + (n === 1 ? "" : "s");
/** As referências usadas, na aba Referência (27/10/2026). Sem o resultado em dia (`usadas` null), a regra: "Para cada município da
 * base, só o candidato mais próximo fica como referência." (conforme a base, ", entre os do mesmo estado"). Com ele, as que o motor
 * usou (`referencia.membros`) entre os candidatos: "Ficou como referência 1 dos 175 candidatos: ITAGUACU DA BAHIA (BA), o mais
 * próximo de PILAO ARCADO (BA)."; "Ficaram como referência 2 dos 3 candidatos: CRUZEIRO DO SUL (AC) e RIO BRANCO (AC), cada um o
 * mais próximo de algum município da base." */
export function textoDasReferenciasUsadas(c: { rotulos: RotulosTerritoriais; brasil: boolean; grupos?: GrupoInfo[]; tipo: TipoPartida;
  candidatos: number | null; usadas: { referencias: string[]; base: string | null } | null }): string {
  const unidade = c.rotulos.unidade, f = fem(unidade);
  const contexto = { rotulos: c.rotulos, brasil: c.brasil, grupos: c.grupos ?? [], nomes: new Map<string, string>() };
  const recorte = recorteDaReferencia(c.tipo, contexto), noRecorte = recorteDaReferencia(c.tipo, contexto, true);
  if (!c.usadas) return "Para cada " + unidade.singular + " da base, só " + (f ? "a candidata mais próxima" : "o candidato mais próximo") +
    " fica como referência" + (recorte ? ", entre " + (f ? "as " : "os ") + recorte : "") + ".";
  const { referencias, base } = c.usadas, total = c.candidatos;
  if (total === 0) return "Sem " + (f ? "candidatas" : "candidatos") + ", " + (f ? "nenhuma " : "nenhum ") + unidade.singular + " da base tem referência.";
  if (!referencias.length) return (f ? "Nenhuma " : "Nenhum ") + (total === null ? (f ? "candidata" : "candidato")
    : (f ? "das " : "dos ") + quantosCandidatos(total, unidade)) + " ficou como referência de " + umA(unidade) + " da base.";
  const nomes = referencias.slice(0, NOMES_NA_FRASE), resto = referencias.length - nomes.length;
  const lista = resto > 0 ? nomes.join(", ") + " e mais " + inteiro.format(resto) : emLista(nomes);
  const dos = total === null ? quantosCandidatos(referencias.length, unidade) : total === 1 ? (f ? "a única candidata" : "o único candidato")
    : inteiro.format(referencias.length) + (f ? " das " : " dos ") + quantosCandidatos(total, unidade);
  const proximo = f ? "a mais próxima" : "o mais próximo";
  const de = referencias.length > 1 ? ", " + (f ? "cada uma " : "cada um ") + proximo + " de " + (f ? "alguma " : "algum ") + unidade.singular + " da base"
    : ", " + proximo + " " + (base ? "de " + base : "d" + artigo(unidade, true) + " " + unidade.plural + " da base");
  return (referencias.length === 1 ? "Ficou" : "Ficaram") + " como referência " + dos + ": " + lista + de + (noRecorte ? " " + noRecorte : "") + ".";
}
/** A referência pelo nome pedida na conversa ("distância até Manaus"): os membros viram os marcados da referência, a partir do país;
 * a base continua a da consulta (sem consulta, a inicial). */
export function consultaComReferenciaMarcada(atual: ConsultaTerritorios | null, membros: string[], comSelecao: boolean): ConsultaTerritorios {
  const consulta = atual ?? consultaInicial({ comSelecao });
  return { ...consulta, referencia: { partir_de: { tipo: "pais", regioes: [], ufs: [] }, filtros: [], escolha: { modo: "marcados", municipios: [...membros] } } };
}
/** O lugar do título na Análise Espacial: o da base da consulta ("Norte", "Acre e Amazonas", "Brasil"; com filtros, ", com
 * filtros"; no modo marcados, quantos são); com a seleção prévia, o da Seleção de Territórios. */
export function lugarDaConsulta(consulta: ConsultaTerritorios, c: ContextoDaFrase & { selecao: Lugar }): Lugar {
  const { partir_de: partir, filtros, escolha } = consulta.base;
  const grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  let curto: string;
  if (escolha.modo === "marcados") curto = escolha.municipios.length <= 2 ? emLista(escolha.municipios.map(id => c.nomes.get(id) || id))
    : quantos(escolha.municipios.length, c.rotulos.unidade);
  else if (partir.tipo === "pais") curto = c.brasil ? "Brasil" : "Toda a planilha";
  else if (partir.tipo === "selecao_previa") curto = c.selecao.curto;
  else if (partir.tipo === "regioes") curto = partir.regioes.length <= 2 ? emLista(partir.regioes) : partir.regioes.length + " regiões";
  else curto = partir.ufs.length <= 2 ? emLista(partir.ufs.map(id => c.grupos.find(item => item.id === id)?.nome || id)) : quantos(partir.ufs.length, grupo);
  if (escolha.modo !== "marcados" && filtros.length) curto += ", com filtros";
  return { lugar: "", curto };
}
/** A referência de um estado salvo de antes da Escolha dos territórios (a referência por elegibilidade ou pelos membros, com os
 * territórios base), na consulta equivalente; o "mais distante" saiu (27/10/2026) e não tem equivalente: fica sem consulta. */
export function consultaDeAntes(referencia: unknown, territoriosBase: unknown): ConsultaTerritorios | null {
  const ref = comoObjeto(referencia);
  if (!ref) return null;
  const bases = Array.isArray(territoriosBase) ? territoriosBase.filter((id): id is string => typeof id === "string") : null;
  const base: LadoDaConsulta = { ...ladoInicial("selecao_previa"), ...(bases?.length ? { escolha: { modo: "marcados", municipios: bases } } : {}) };
  const membros = listaDeTextos(ref.membros);
  if (membros && membros.length) return { ...consultaComReferenciaMarcada(null, membros, true), base };
  const delimitacao = comoObjeto(ref.delimitacao), condicao = comoObjeto(ref.condicao);
  if (ref.relacao !== "mais_proxima" || !delimitacao || !condicao) return null;
  const valores = listaDeTextos(delimitacao.valores) ?? [];
  const partir: PartirDe | null = delimitacao.tipo === "todos" ? { tipo: "pais", regioes: [], ufs: [] }
    : delimitacao.tipo === "mesmo_grupo" ? { tipo: "mesma_uf_da_base", regioes: [], ufs: [] }
    : delimitacao.tipo === "mesma_regiao" ? { tipo: "mesma_regiao_da_base", regioes: [], ufs: [] }
    : delimitacao.tipo === "grupos" ? { tipo: "ufs", regioes: [], ufs: valores }
    : delimitacao.tipo === "regioes" ? { tipo: "regioes", regioes: valores, ufs: [] } : null;
  if (!partir) return null;
  return lerConsulta({ base, referencia: { partir_de: partir, filtros: [{ indicador: condicao.atributo, operador: condicao.operador, valor: condicao.valor }],
    escolha: { modo: "todos", municipios: [] } } });
}
/** O valor de corte digitado (vírgula ou ponto decimal; sem separador de milhar ambíguo): número não negativo ou null. Na
 * quantidade e na população, só inteiros (pessoas e habitantes); na densidade, o valor por 1.000 habitantes. */
export function lerValorDeCorte(texto: string, atributo: PainelAtributo): number | null {
  const limpo = texto.trim().replace(/\s/g, "");
  if (!limpo) return null;
  const normal = /,/.test(limpo) ? limpo.replace(/\./g, "").replace(",", ".") : /^\d{1,3}(\.\d{3})+$/.test(limpo) ? limpo.replace(/\./g, "") : limpo;
  if (!/^\d+(\.\d+)?$/.test(normal)) return null;
  const valor = Number(normal);
  if (!Number.isFinite(valor) || valor < 0) return null;
  return atributo !== "densidade" && !Number.isInteger(valor) ? null : valor;
}
/** Unidade e orientação do valor de corte, pelo atributo escolhido. */
export const UNIDADES_DO_CORTE: Record<PainelAtributo, { unidade: string; dica: string }> = {
  densidade: { unidade: "profissionais por 1.000 habitantes", dica: "Por exemplo, 2,36 (a densidade usa a mesma escala da análise)." },
  quantidade: { unidade: "profissionais", dica: "Um número inteiro de profissionais, por exemplo, 500." },
  populacao: { unidade: "habitantes", dica: "Um número inteiro de habitantes, por exemplo, 50.000." },
};
/** Nada escolhido no nível em análise: municípios sem nenhum marcado nem conjunto, ou estados sem nenhum marcado. O Brasil é
 * uma unidade só: escolher o nível já o seleciona. */
export const semSelecao = (def: Pick<DefinicaoAnalise, "nivel" | "base" | "estados" | "conjuntos">) =>
  def.nivel === "brasil" ? false : def.nivel === "estados" ? !def.estados.length : baseVazia(def.base) && !def.conjuntos.length;
/** A Análise Espacial com a Escolha dos territórios calculada (27/10/2026): a base vem da consulta (o país, uma região, um
 * estado...), e a seleção prévia é só uma das opções; sem territórios selecionados, a análise continua. */
export const consultaEmUso = (def: Pick<DefinicaoAnalise, "familia" | "nivel" | "consulta">) =>
  def.familia === "espacial" && def.nivel === "municipios" && !!def.consulta;
/** Nada a analisar: sem seleção no nível em uso e sem a Escolha dos territórios em uso. */
export const semTerritorios = (def: Pick<DefinicaoAnalise, "familia" | "nivel" | "base" | "estados" | "conjuntos" | "consulta">) =>
  semSelecao(def) && !consultaEmUso(def);
/** Limpar seleção (decisão 5, 25/10/2026): tira só os territórios do nível em uso, porque cada nível guarda a sua escolha (em
 * Municípios, os municípios e os conjuntos; em Estados, os estados). No nível Brasil, o país é a própria unidade e não há o que
 * limpar; sem nada marcado no nível em uso, também não. Nos dois casos, null. */
export function limparNivel<E extends Pick<DefinicaoAnalise, "nivel" | "base" | "estados" | "conjuntos">>(escolha: E): E | null {
  if (escolha.nivel === "brasil" || semSelecao(escolha)) return null;
  return escolha.nivel === "estados" ? { ...escolha, estados: [] } : { ...escolha, base: { ...BASE_VAZIA }, conjuntos: [] };
}
/** A comparação (CAP-CMP) vale para itens que estão na análise: depois de uma mudança na Seleção de Territórios, ela continua só se
 * o nível é o mesmo e todos os itens dela continuam escolhidos (o motor recusa itens fora do gráfico). Senão, sai. */
export function comparacaoQueContinua(antes: Pick<DefinicaoAnalise, "nivel" | "comparar">,
  depois: Pick<DefinicaoAnalise, "nivel" | "base" | "estados" | "conjuntos">, grupoDe: (id: string) => string = prefixoDe): string[] {
  if (!antes.comparar.length || antes.nivel !== depois.nivel) return [];
  const continua = (id: string) => depois.nivel === "estados" ? depois.estados.includes(id.replace(/^(?:uf|estado):/, ""))
    : depois.nivel === "municipios" ? (/^c\d+$/.test(id) ? depois.conjuntos.some(conjunto => conjunto.id === id)
      : unidadeMarcada(depois.base, id, grupoDe(id))) : false;
  return antes.comparar.every(continua) ? antes.comparar : [];
}
/** Os estados escolhidos, na ordem do código, sem repetir e só os que a fonte tem. */
export const normalizarEstados = (estados: string[], todos: string[]) => {
  const conhecidos = new Set(todos);
  return [...new Set(estados)].filter(id => conhecidos.has(id)).sort(comparar);
};

export const tendenciaPossivel = (def: DefinicaoAnalise) => def.janela.length >= MINIMO_TENDENCIA;
/** Visão da tendência que de fato aparece: a Tendência (classes) só com quatro competências ou mais; senão, a Trajetória. A
 * Série temporal (24/10/2026) tem o próprio intervalo e não depende da janela. */
export const visaoEfetiva = (def: DefinicaoAnalise): Visao => def.visao === "classes" && !tendenciaPossivel(def) ? "mudanca" : def.visao;

/** A base carregada sem territórios escolhidos: nada é pedido ao motor até a seleção. */
export const TEXTO_SEM_SELECAO = "Selecione os territórios que deseja analisar.";
/** A abertura (24/10/2026): a identificação do sistema e a chamada para a escolha dos dados, no alto e ao centro. O nome é o da
 * plataforma (o da SPEC e do cabeçalho): "na Saúde". */
export const TITULO_DO_SISTEMA = "Diagnóstico Territorial da Força de Trabalho na Saúde";
export const TEXTO_ESCOLHA_DOS_DADOS = "Escolha seus dados para começar";
export const TEXTO_DAS_FONTES = "Use os dados do Brasil, já preparados, ou envie a sua planilha em CSV ou Excel.";
/** O que impede o pedido ao motor (null quando ele pode sair): sem dados, sem competência ou nada escolhido no nível. */
export function bloqueioDoPedido(def: DefinicaoAnalise, c: { fonte: "brasil" | "arquivo" | null; rotulos: RotulosTerritoriais }): string | null {
  if (!c.fonte) return "Escolha os dados para começar.";
  if (!def.competencia) return "Escolha a competência.";
  if (semTerritorios(def)) return TEXTO_SEM_SELECAO;
  return null;
}
/** O que falta para a família escolhida aparecer (o gráfico continua com a distribuição enquanto isso). */
export function avisoDaFamilia(def: DefinicaoAnalise, disponivel: Disponivel): string | null {
  if (!disponivel.disponivel || disponivel.pendente) return def.familia === "distribuicao" ? null : disponivel.motivo || null;
  // A Série temporal tem o próprio intervalo (toda a série, sem escolha): não espera o período da tendência.
  if (def.familia === "tendencia" && def.visao === "series") return null;
  if (def.familia === "tendencia" && def.janela.length < 2) return TEXTO_ESCOLHA_DO_PERIODO;
  if (def.familia === "tendencia" && def.visao === "classes" && def.janela.length < MINIMO_TENDENCIA)
    return TEXTO_MINIMO_TENDENCIA + " Com " + def.janela.length + " competências, aparece a trajetória entre a primeira e a última.";
  if (def.familia === "rotatividade" && (!def.rotatividade?.inicial || !def.rotatividade?.final))
    return "Escolha os períodos inicial e final da coorte.";
  if (def.familia === "espacial" && !def.consulta) return TEXTO_ESCOLHA_DA_REFERENCIA;
  return null;
}
/** O que falta na Análise Espacial sem a Escolha dos territórios calculada (27/10/2026). */
export const TEXTO_ESCOLHA_DA_REFERENCIA = "Faça a escolha dos territórios: a base e a referência. A distância vai de cada território da " +
  "base até a referência mais próxima.";

/** Família que o pedido de fato calcula: a escolhida quando disponível e possível no nível; senão, a distribuição. */
export function familiaCalculada(def: DefinicaoAnalise, disponivel: boolean): Familia {
  if (!disponivel) return "distribuicao";
  if (def.familia === "espacial" && (!def.consulta || def.nivel !== "municipios")) return "distribuicao";
  if (def.familia === "tendencia" && def.visao !== "series" && def.janela.length < 2) return "distribuicao";
  if (def.familia === "rotatividade" && (!def.rotatividade?.inicial || !def.rotatividade?.final || def.nivel !== "municipios")) return "distribuicao";
  return def.familia;
}

/** Opções de /api/painel com as chaves do contrato (seção 3), só as que o estado pede. Cada nível leva só a sua escolha: os
 * municípios, a base (com os conjuntos e a referência da distância); os estados, a lista `estados` quando não são todos (sem
 * ela, o motor usa todos os da fonte estadual); o Brasil, nada além do nível. Com o Brasil, uma unidade só, ficam de fora os
 * grupos, as faixas, as condições, a ordenação e a comparação, que valem para vários territórios (matriz D3). */
export function montarOpcoes(def: DefinicaoAnalise, familia: Familia, grupoDe: (id: string) => string = prefixoDe,
  c: { quintisDoMapa?: boolean; todosOsEstados?: string[]; rotulos?: RotulosTerritoriais;
    /** As competências da base: a Série temporal sem intervalo escolhido usa todas (24/10/2026). */
    periodos?: string[] } = {}): PainelOpcoes {
  const tendencia = familia === "tendencia";
  // Série temporal (24/10/2026): os valores de cada competência do intervalo (toda a série, sem escolha), sem classificação; a
  // competência do pedido é a última do intervalo.
  const serie = tendencia && def.visao === "series" ? intervaloDaSerie(def, c.periodos ?? def.serie ?? []) : null;
  const competencia = serie?.length ? serie[serie.length - 1] : tendencia ? def.janela.at(-1) ?? def.competencia
    : familia === "rotatividade" && def.rotatividade ? def.rotatividade.final : def.competencia;
  const opcoes: PainelOpcoes = { competencia, categoria: def.categoria, nivel: def.nivel, indicador: def.indicador };
  const varios = def.nivel !== "brasil";
  if (def.nivel === "municipios") {
    opcoes.base = { municipios: normalizarBase(def.base, grupoDe) };
    if (def.conjuntos.length) opcoes.conjuntos = def.conjuntos;
    // A Escolha dos territórios (27/10/2026): `base` continua indo como a seleção prévia, lida pela consulta.
    if (familia === "espacial" && def.consulta) {
      opcoes.consulta = consultaParaOMotor(def.consulta);
      if (def.faixasDistancia.length >= 2) opcoes.faixas_distancia = def.faixasDistancia;
    }
    if (familia === "rotatividade" && def.rotatividade) opcoes.rotatividade = def.rotatividade;
  }
  if (def.nivel === "estados") {
    const todos = c.todosOsEstados ?? [];
    const escolhidos = todos.length ? normalizarEstados(def.estados, todos) : [...new Set(def.estados)].sort(comparar);
    if (!todos.length || escolhidos.length < todos.length) opcoes.estados = escolhidos;
  }
  // Entre a Tendência e a Trajetória, a visão é só estado visual: com quatro competências ou mais, a tendência vai junto e a troca
  // não pede nada novo. A Série temporal pede os valores do intervalo dela (`serie`), sem a tendência nem a variação.
  if (serie) {
    if (serie.length >= 2) opcoes.serie = { competencias: serie };
  } else if (tendencia && def.janela.length >= 2) {
    opcoes.competencia_inicial = def.janela[0];
    if (def.janela.length >= MINIMO_TENDENCIA) opcoes.tendencia = { competencias: def.janela };
  }
  if (varios && familia === "distribuicao" && def.agrupar.tipo !== "nenhum") {
    if (def.agrupar.tipo === "faixas") { if (def.agrupar.faixas.length >= 2) opcoes.faixas = def.agrupar.faixas; }
    else opcoes.grupos = { tipo: def.agrupar.tipo };
  }
  if (varios && familia !== "rotatividade") {
    if (def.condicoes.length) opcoes.condicoes = def.condicoes.filter(c => c.atributo !== "distancia_km" || familia === "espacial");
    if (!opcoes.condicoes?.length) delete opcoes.condicoes;
    if (def.ordenar && (def.ordenar.atributo !== "distancia_km" || familia === "espacial") && (def.ordenar.atributo !== "variacao" || tendencia))
      opcoes.ordenar = def.ordenar;
    if (def.comparar.length >= 2 && def.comparar.length <= 3) opcoes.comparar = def.comparar;
  }
  // A cor do mapa sem cor própria da análise: os quintis do motor vêm junto com a análise (23/10/2026), e trocar de vista
  // continua sem pedir nada novo (RQ-REP-06).
  if (c.quintisDoMapa) opcoes.grupos_mapa = { tipo: "quintis" };
  if (Object.keys(def.premissas).length) opcoes.premissas = def.premissas;
  // Nas planilhas, os nomes confirmados vão em todo pedido (24/10/2026), como no do mapa: a resposta fala deles.
  if (c.rotulos) opcoes.rotulos = c.rotulos;
  return opcoes;
}

/** O indicador muda a resposta do motor? Só com grupos (também os do mapa), faixas, tendência, comparação ou ordenação pela
 * variação; nos demais pedidos, cada item traz população, quantidade e densidade, e o indicador é só estado visual. */
export const pedidoDependeDoIndicador = (opcoes: PainelOpcoes) =>
  !!(opcoes.grupos || opcoes.grupos_mapa || opcoes.faixas || opcoes.tendencia || opcoes.serie || opcoes.comparar ||
    opcoes.ordenar?.atributo === "variacao");

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
  if (familia === "tendencia") return visao === "mudanca" ? "variacao" : visao === "series" ? "unica" : "classes";
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

export type FuncaoPainel = "regua" | "condicoes" | "ordenar" | "comparar" | "juntar" | "exportar" | "referencia";
/** `criterio`: a referência pedida por critério (sem membros): a Escolha dos territórios abre na aba Referência com um filtro do
 * atributo e do operador do pedido (operadorDoCriterio), e o valor é da pessoa.
 * `vista`: a vista do desenho pedida ("ver no mapa", "volte ao gráfico"), só quando ela pode aparecer; estado visual. */
export type ResultadoPedido = { definicao: DefinicaoAnalise; abrir: FuncaoPainel | null; selecao: string[] | null; mensagens: string[];
  criterio: PainelCriterio | null; vista: "grafico" | "mapa" | null };
/** Aplica o comando da conversa ao estado do gráfico. Valida cada campo; o que não vale vira mensagem, nunca erro. A vista do
 * mapa é conferida na definição que resulta do pedido (`mapa`): "mostre os municípios do Amazonas no mapa" abre o mapa; nos
 * estados, a mensagem diz o motivo. */
export function aplicarPedido(def: DefinicaoAnalise, pedido: PedidoDoChat, c: { periodos: string[]; nomes: Map<string, string>;
  temGrupos: boolean; disponivel: (familia: Familia) => Disponivel; grupoDe?: (id: string) => string;
  mapa?: (definicao: DefinicaoAnalise) => { disponivel: boolean; motivo: string | null };
  /** Os estados da fonte: "todos os estados" na conversa marca todos (a escolha de estados da Seleção é trocada por ela). */
  todosOsEstados?: string[];
  /** A base do Brasil, com o país como unidade (nível Brasil). */
  temBrasil?: boolean }): ResultadoPedido {
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
    if (c.temGrupos) proxima = { ...proxima, nivel: "estados", estados: c.todosOsEstados?.length ? [...c.todosOsEstados] : proxima.estados };
    else mensagens.push("Esta fonte não tem a visão por grupos.");
  } else if (pedido.nivel === "brasil") {
    if (c.temBrasil) proxima.nivel = "brasil";
    else mensagens.push("O Brasil como unidade existe só nos dados do Brasil.");
  } else if (pedido.nivel === "municipios") proxima.nivel = "municipios";
  if (typeof pedido.competencia === "string") {
    if (periodos.has(pedido.competencia)) proxima.competencia = pedido.competencia;
    else mensagens.push("A competência " + exibirCompetencia(pedido.competencia) + " não existe nesta base.");
  }
  // Tendência (24/10/2026): a janela são sempre os últimos 4 períodos do ritmo, anual ou semestral. A janela que vem da conversa
  // (ou de outra rota) vale pelo ritmo dos intervalos dela (janelaPeloRitmo); sem ritmo, a janela não muda, e a mensagem pede a
  // escolha. A janela só vale para a tendência: as outras famílias usam uma competência (a rotatividade, os períodos da coorte,
  // que ficam nos ajustes dela).
  const paraTendencia = pedido.familia ? pedido.familia === "tendencia" : def.familia !== "rotatividade";
  if (Array.isArray(pedido.janela) && paraTendencia) {
    const { janela, mensagem } = janelaPeloRitmo(pedido.janela, c.periodos);
    if (janela.length) proxima = { ...proxima, janela, familia: "tendencia" };
    if (mensagem) mensagens.push(mensagem);
  }
  if (pedido.visaoTendencia === "mudanca" || pedido.visaoTendencia === "classes" || pedido.visaoTendencia === "series")
    proxima = { ...proxima, visao: pedido.visaoTendencia, familia: pedido.familia ?? "tendencia" };
  let criterioPedido: PainelCriterio | null = null;
  if (pedido.referencia && Array.isArray(pedido.referencia.membros)) {
    const membros = [...new Set(pedido.referencia.membros.filter((m): m is string => typeof m === "string"))];
    const criterio = pedido.referencia.criterio as Record<string, unknown> | undefined;
    const valido = criterio && ["densidade", "quantidade", "populacao"].includes(String(criterio.atributo)) && ["desc", "asc"].includes(String(criterio.ordem));
    if (membros.length) {
      // A referência pelo nome (27/10/2026): os membros viram os marcados da Referência na Escolha dos territórios, a partir do
      // país, e a base continua a da consulta (sem ela, a seleção prévia).
      proxima = { ...proxima, familia: pedido.familia ?? "espacial", nivel: "municipios",
        consulta: consultaComReferenciaMarcada(proxima.consulta, membros, !semSelecao({ ...proxima, nivel: "municipios" })) };
    } else if (valido) {
      // Referência por critério: abre a Escolha dos territórios com o filtro do atributo e do operador do pedido (CAP-SUB-01); o
      // valor é da pessoa, sem valor sugerido e sem escolher pela posição na ordem.
      criterioPedido = { atributo: criterio!.atributo as PainelAtributo, ordem: criterio!.ordem as PainelOrdem };
      proxima = { ...proxima, familia: pedido.familia ?? "espacial", nivel: "municipios" };
      abrir = "referencia";
    }
  }
  // A Escolha dos territórios pedida na conversa (28/10/2026): vale como se a pessoa a tivesse feito na janela, na Análise Espacial.
  if (pedido.consulta) {
    const consulta = lerConsulta(pedido.consulta);
    if (consulta) {
      if (LADOS.some(lado => consulta[lado].partir_de.tipo === "selecao_previa") && semSelecao({ ...proxima, nivel: "municipios" }))
        mensagens.push("A Escolha dos territórios parte da seleção prévia: escolha os territórios na Seleção de Territórios.");
      // A base passa a ser a da consulta: a comparação de antes sai (o motor recusa itens da comparação fora do gráfico).
      proxima = { ...proxima, familia: "espacial", nivel: "municipios", consulta, comparar: [] };
    } else mensagens.push("A Escolha dos territórios pedida não foi reconhecida.");
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
export function contextoDoGrafico(def: DefinicaoAnalise, idsNaTela: string[], titulo: string, grupoDe: (id: string) => string = prefixoDe,
  /** Com a Escolha dos territórios, os territórios que ficaram como referência mais próxima de algum item (da resposta). */
  referenciasDaResposta: string[] = []): ContextoDoGrafico {
  const referencia = def.familia !== "espacial" || !def.consulta ? [] : referenciasDaResposta;
  return { familia: def.familia, indicador: def.indicador, nivel: def.nivel, municipios: normalizarBase(def.base, grupoDe), estados: def.estados, idsNaTela,
    competencia: def.familia === "tendencia" ? def.janela.at(-1) ?? def.competencia : def.competencia, janela: def.janela,
    referencia, titulo, consulta: consultaEmUso(def) ? consultaParaOMotor(def.consulta!) : null };
}

// ================================================================================================ título
/** Frase que diz o que está na tela (decisão 8): o indicador, onde e quando; o subtítulo explica a leitura. */
export function tituloDaAnalise(p: { fonte: "brasil" | "arquivo" | null; familia: Familia; visao: Visao; indicador: PainelIndicador;
  nivel: PainelNivel; categoria: string; competencia: string; janela: string[]; rotatividade: { inicial: string; final: string } | null;
  lugar: Lugar; rotulos: RotulosTerritoriais;
  /** As competências da Série temporal (24/10/2026), quando é a visão em uso. */
  serie?: string[] }): { titulo: string; subtitulo: string } {
  if (!p.fonte) return { titulo: TITULO_DO_SISTEMA, subtitulo: TEXTO_ESCOLHA_DOS_DADOS };
  const especie = INDICADORES[p.indicador].rotulo;
  const quem = profissionaisDe(p.categoria);
  const rotuloBolha = p.nivel === "estados" ? p.rotulos.grupo ?? ROTULOS_GENERICOS.grupo! : p.rotulos.unidade;
  // O Brasil como unidade (24/10/2026): uma bolha, uma linha, o total nacional.
  const cadaBolha = p.nivel === "brasil" ? "A bolha é o Brasil inteiro, com o total nacional de profissionais. O tamanho mostra a população."
    : textoCadaBolha(rotuloBolha);
  const cadaLinha = p.nivel === "brasil" ? "A linha é o Brasil inteiro" : "Cada linha é " + umA(rotuloBolha);
  const onde = p.lugar.lugar ? " " + p.lugar.lugar : "";
  const periodo = (a: string, b: string) => competenciaPorExtenso(a) + " a " + competenciaPorExtenso(b);
  // Análise Espacial com a Escolha dos territórios (27/10/2026): a distância é sempre até a referência mais próxima de cada um.
  if (p.familia === "espacial" && p.nivel === "municipios")
    return { titulo: especie + " de " + quem + " e distância até a referência mais próxima · " + p.lugar.curto + " · " +
      competenciaPorExtenso(p.competencia),
      subtitulo: cadaBolha + " A posição horizontal é a distância até a referência mais próxima de cada " + rotuloBolha.singular + "." };
  if (p.familia === "tendencia" && p.visao === "series" && (p.serie?.length ?? 0) >= 2) {
    const serie = p.serie!;
    return { titulo: "Série temporal da " + especie.toLowerCase() + " de " + quem + " · " + p.lugar.curto + " · " +
      periodo(serie[0], serie[serie.length - 1]),
      subtitulo: cadaLinha + ", com o valor observado em cada competência do intervalo." };
  }
  if (p.familia === "tendencia" && p.janela.length >= 2) {
    const janela = periodo(p.janela[0], p.janela[p.janela.length - 1]);
    const trajetoria = p.visao !== "classes" || p.janela.length < MINIMO_TENDENCIA;
    return { titulo: (trajetoria ? "Trajetória da " : "Tendência da ") + especie.toLowerCase() + " de " + quem + " · " + p.lugar.curto + " · " + janela,
      subtitulo: trajetoria ? cadaBolha + " O rastro sai do valor no primeiro período; os pontos pequenos são os períodos do meio."
        : cadaLinha + ": as setas mostram a alta, a queda ou a pausa de um período para o seguinte." };
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
  const lida = salvo.definicao as DefinicaoAnalise;
  if (!FAMILIAS_VALIDAS.has(lida.familia) || !lida.base || !Array.isArray(lida.janela)) return null;
  // Os estados escolhidos entraram em 24/10/2026: uma definição sem eles abre sem estados marcados; sem o intervalo da Série
  // temporal (24/10/2026), toda a série. A Escolha dos territórios (27/10/2026): a consulta guardada ou, de antes dela, a
  // equivalente da referência e dos territórios base de então (consultaDeAntes); o "mais distante" não tem equivalente.
  const { territorioBase: unicaBase, territoriosBase, referencia, ...resto } = lida as DefinicaoAnalise & { territorioBase?: unknown;
    territoriosBase?: unknown; referencia?: unknown };
  const consulta = "consulta" in lida ? lerConsulta(lida.consulta)
    : consultaDeAntes(referencia, typeof unicaBase === "string" ? [unicaBase] : territoriosBase);
  const def: DefinicaoAnalise = { ...resto, estados: Array.isArray(lida.estados) ? lida.estados.filter(id => typeof id === "string") : [],
    serie: Array.isArray(lida.serie) ? lida.serie.filter(c => typeof c === "string") : [], consulta };
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
 * avaliabilidade e o motivo (CAP-REP-06). Separador ";" e BOM, como a exportação de sempre. A coluna do grupo (28/10/2026): "UF"
 * na base do Brasil; numa planilha, o nome do grupo dela ("Condado"), com o valor da coluna-mãe que o motor devolve
 * (`grupo_territorial`), e nenhuma coluna sem grupo. */
export function montarCsv(resposta: PainelResposta, c: { familia: Familia; indicador: PainelIndicador; rotulos: RotulosTerritoriais;
  brasil?: boolean }): string {
  const itens = [...resposta.itens].sort(ordemNeutra);
  const brasil = c.brasil ?? c.rotulos.unidade.singular === "município";
  const distancia = itens.some(item => item.distancia_km !== null || item.avaliavel.distancia !== null);
  const variacao = !!resposta.competencia_inicial;
  const tendencia = itens.some(item => item.tendencia);
  const grupo = itens.some(item => item.grupo), faixa = itens.some(item => item.faixa), faixaDistancia = itens.some(item => item.faixa_distancia);
  const condicoes = itens.some(item => item.condicoes), ordem = itens.some(item => item.ordem), rotatividade = itens.some(item => item.rotatividade);
  const tipoTexto = (tipo: PainelItem["tipo"]) => tipo === "conjunto" ? "conjunto" : tipo === "brasil" ? "país" : tipo === "estado"
    ? (c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!).singular : c.rotulos.unidade.singular;
  // O nome do grupo não repete outro cabeçalho (29/10/2026): com os nomes sugeridos pelo modelo de planilha, unidade e grupo
  // se chamam "território", e o CSV tinha duas colunas "Território".
  const fixos = ["Identificador", "Tipo", "Território", "Competência", "Categoria", "População", "Quantidade"].map(sem);
  const nomeDoGrupo = c.rotulos.grupo ? maiuscula(c.rotulos.grupo.singular) : "";
  const cabecalhoDoGrupo = fixos.includes(sem(nomeDoGrupo)) ? nomeDoGrupo + " (grupo)" : nomeDoGrupo;
  const colunas: [string, (item: PainelItem) => unknown][] = [
    ["Identificador", item => item.id], ["Tipo", item => tipoTexto(item.tipo)], ["Território", item => item.rotulo],
    ...(brasil ? [["UF", item => item.uf] as [string, (item: PainelItem) => unknown]]
      : c.rotulos.grupo ? [[cabecalhoDoGrupo, item => item.grupoTerritorial] as [string, (item: PainelItem) => unknown]] : []),
    ["Competência", () => resposta.competencia], ["Categoria", () => resposta.categoria],
    ["População", item => item.populacao], ["Quantidade", item => item.quantidade], ["Densidade por 1.000 habitantes", item => item.densidade],
    ["Tipo de contagem", item => item.tipo === "conjunto" ? textoDaContagem(item.contagem) : ""],
  ];
  // Com a Escolha dos territórios (27/10/2026), a referência mais próxima é de cada item: a coluna diz qual é.
  const porItem = resposta.referencia?.tipo === "consulta";
  if (distancia && porItem) colunas.push(["Distância até a referência mais próxima (km)", item => item.distancia_km],
    ["Referência mais próxima", item => (item.referenciaDoItem || []).map(ref => ref.rotulo).join(" | ")]);
  else if (distancia) colunas.push(["Distância até a referência (km)", item => item.distancia_km], ["Distância do membro mais distante (km)", item => item.distancia_km_max ?? null],
    ["Membro da referência mais próximo", item => (item.referenciaDoItem || []).map(ref => ref.rotulo).join(" | ")],
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
  // Série temporal (24/10/2026): uma coluna por competência do intervalo, com o valor observado em precisão integral (vazia sem
  // valor, nunca zero).
  const serie = resposta.serie?.competencias ?? [];
  if (serie.length && itens.some(item => item.serie)) {
    const rotulo = INDICADORES[c.indicador].rotulo;
    for (const competencia of serie) colunas.push([rotulo + " em " + exibirCompetencia(competencia),
      item => item.serie?.observacoes.find(obs => obs.competencia === competencia)?.valor ?? null]);
    colunas.push(["Série comparável", item => item.serie ? (item.serie.comparavel ? "sim" : "não") : ""]);
  }
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
 * enviado ao motor, as notas, as limitações e a procedência. Numa planilha (28/10/2026), uma linha antes dos parâmetros diz que
 * as chaves deles são as do contrato da API ("municipios", "estados") e o que elas são nesta planilha. */
export function textoDoMetodo(resposta: PainelResposta, titulo: string, opcoes: PainelOpcoes | null,
  resumo: string | null = resposta.resumo?.texto ?? null, c?: { rotulos: RotulosTerritoriais; brasil: boolean }): string {
  const linhas = [titulo, ...(resumo ? [resumo] : []), "", "Procedência", "- Competência: " + exibirCompetencia(resposta.competencia) +
    (resposta.competencia_inicial ? " (inicial: " + exibirCompetencia(resposta.competencia_inicial) + ")" : ""),
    "- Categoria: " + resposta.categoria, "- Versão da base: " + (resposta.versao_base || "não informada"),
    "- Chave de execução: " + (resposta.chave_execucao || "não informada")];
  if (resposta.referencia?.origem) linhas.push("- Referência: " + resposta.referencia.origem);
  if (resposta.tendencia?.janela.length) linhas.push("- Janela da tendência: " + resposta.tendencia.janela.map(exibirCompetencia).join(", "));
  if (resposta.serie) linhas.push("- Série temporal: " + exibirCompetencia(resposta.serie.inicio) + " a " + exibirCompetencia(resposta.serie.fim) +
    " (" + resposta.serie.competencias.length + " competências)");
  linhas.push("", "Notas do método", ...resposta.notas.map(nota => "- " + nota));
  if (resposta.limitacoes.length) linhas.push("", "Limitações", ...resposta.limitacoes.map(codigo => "- " + textoDaLimitacao(codigo)));
  if (opcoes) linhas.push("", "Parâmetros da análise", ...(c && !c.brasil ? [notaDasChaves(c.rotulos)] : []), JSON.stringify(opcoes, null, 2));
  linhas.push("", "Os valores do CSV estão em precisão integral; na tela, aparecem arredondados.");
  return linhas.join("\n");
}

/** As chaves dos parâmetros são as do contrato da API, iguais em toda fonte: numa planilha, "municipios" são as unidades dela e
 * "estados", os grupos. */
function notaDasChaves(rotulos: RotulosTerritoriais): string {
  return "Os nomes das chaves abaixo são os do contrato da API, iguais em toda fonte: nesta planilha, “municipios” são " +
    artigo(rotulos.unidade, true) + " " + rotulos.unidade.plural + (rotulos.grupo ? ", e “estados”, " + artigo(rotulos.grupo, true) + " " +
    rotulos.grupo.plural : "") + ".";
}

// ================================================================================================ ajustes, vista do desenho e mapa
/** Ajustes dentro da análise escolhida (23/10/2026): o painel colado na aba mostra só o que vale para ela. O indicador é o
 * mesmo em todas as abas (fica na definição) e fica à vista; a categoria, com mais de uma, vem logo depois dele; a rotatividade
 * não tem indicador. Nos estados (E1) e com a família indisponível, o desenho é a distribuição, e valem os ajustes dela. */
export type Ajuste = "indicador" | "categoria" | "competencia" | "agrupar" | "referencia" | "janela" | "visao" | "periodos" | "serie";
export function ajustesDaAnalise(c: { familia: Familia; nivel: PainelNivel; disponivel: boolean; categorias: number; visao?: Visao }): Ajuste[] {
  const categoria: Ajuste[] = c.categorias > 1 ? ["categoria"] : [];
  // Nos estados e no Brasil (24/10/2026), a distância espera municípios: valem os ajustes da distribuição. Com o Brasil, uma
  // unidade só, não há grupos nem faixas.
  const familia = !c.disponivel || (c.nivel !== "municipios" && (c.familia === "espacial" || c.familia === "rotatividade")) ? "distribuicao" : c.familia;
  if (familia === "espacial") return ["indicador", ...categoria, "competencia", "referencia"];
  // Na tendência, o Período (anual ou semestral) orienta a Tendência e a Trajetória; a Série temporal tem o intervalo dela.
  if (familia === "tendencia") return ["indicador", ...categoria, c.visao === "series" ? "serie" : "janela", "visao"];
  if (familia === "rotatividade") return ["periodos", ...categoria];
  return ["indicador", ...categoria, "competencia", ...(c.nivel === "brasil" ? [] : ["agrupar" as const])];
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
  if (c.nivel === "brasil") return { disponivel: false, atalho: null,
    motivo: "O Brasil, como unidade, não tem um ponto no mapa: cada ponto do mapa é " + umA(unidade) + "." };
  if (!c.temCoordenadas) return { disponivel: false, atalho: null, motivo: c.rotatividade
    ? "Sem latitude e longitude na planilha, a rotatividade fica nas barras: o mapa precisa das coordenadas de cada " + unidade.singular + "."
    : "A planilha não tem as colunas de latitude e longitude: o mapa precisa das coordenadas de cada " + unidade.singular + ". A tabela continua." };
  if (c.series) return { disponivel: false, atalho: null,
    motivo: "Na visão Série temporal, cada " + unidade.singular + " é uma linha no tempo: o mapa fica com Tendência e Trajetória." };
  return { disponivel: true, motivo: null, atalho: null };
}

/** Como o mapa pinta (PinturaDoMapa do contrato; 23/10/2026, sem a pergunta "Como pintar o mapa?"): a camada do gráfico quando
 * há uma (grupos, faixas, condições, ordem, classes ou variação); na rotatividade, a permanência da coorte inicial em cor
 * contínua; sem cor própria da análise, os 5 grupos iguais (quintis) que o motor devolve em `grupos_mapa`; e, sem eles (uma
 * análise guardada antes), a cor única do gráfico. Nunca a escala logarítmica. */
export function pinturaDoMapa(c: { camada: CamadaDeCor; rotatividade: boolean; gruposDoMapa: boolean }): PinturaDoMapa {
  if (c.rotatividade) return "continua";
  if (c.camada !== "unica") return "camada";
  return c.gruposDoMapa ? "quintis" : "camada";
}
/** O pedido leva os quintis do mapa (`grupos_mapa`) quando a análise não tem cor própria: a distribuição sem grupos nem faixas
 * aplicadas e a análise espacial, sem condições nem ordenação, com o mapa disponível (unidades com coordenadas). */
export function precisaQuintisDoMapa(def: DefinicaoAnalise, familia: Familia, mapaDisponivel: boolean): boolean {
  if (!mapaDisponivel || def.nivel !== "municipios" || def.condicoes.length || def.ordenar) return false;
  if (familia === "espacial") return true;
  return familia === "distribuicao" && (def.agrupar.tipo === "nenhum" || (def.agrupar.tipo === "faixas" && def.agrupar.faixas.length < 2));
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
    if (!item || item.tipo !== "municipio" || item.referencia || !item.referenciaDoItem?.length) continue;
    ligacoes.push({ de: item.id, para: item.referenciaDoItem.map(ref => ref.id) });
    if (ligacoes.length >= MAX_LIGACOES) break;
  }
  return ligacoes;
}

// ================================================================================================ base e referência
/** A referência de um território da base, com os valores do motor: com a Escolha dos territórios, os de `referencia.membros`;
 * pelos membros escolhidos (o contrato de antes), os do próprio item (o membro entra na análise a distância zero). */
export type ReferenciaDaBase = { id: string; rotulo: string; uf: string | null; populacao: number | null; quantidade: number | null;
  densidade: number | null;
  /** A referência já é desenhada no gráfico com a mira (membro escolhido, a distância zero): a ligação vai até ela. */
  noGrafico: boolean;
  /** A referência também está na base (com a sua própria distância). */
  emAnalise: boolean };
/** Um território da base e a referência mais próxima dele: no empate, todas as empatadas (CAP-ESP-02), a primeira antes. */
export type ParDaBase = { base: PainelItem; referencias: ReferenciaDaBase[]; distancia: number | null;
  /** Sem referência: o motivo do motor (Não avaliáveis). */
  motivo: string | null };
/** Uma referência que o gráfico desenha como contexto (fora das bolhas da base), uma vez só, com os territórios da base ligados a
 * ela e a distância de cada um, na ordem dos pares. */
export type ReferenciaDeContexto = { referencia: ReferenciaDaBase; bases: { base: PainelItem; distancia: number | null }[] };

/** Os territórios da base na resposta: as unidades, sem estados nem conjuntos, na ordem dos nomes; com a referência pelo nome (o
 * contrato de antes), sem os membros dela (eles são a referência). */
export const basesPossiveis = (itens: PainelItem[]) => itens.filter(item => item.tipo === "municipio" && !item.referencia)
  .map(item => ({ id: item.id, rotulo: item.rotulo })).sort((a, b) => comparar(a.rotulo, b.rotulo) || comparar(a.id, b.id));

function referenciaDaBase(resposta: Pick<PainelResposta, "itens" | "referencia">, ref: { id: string; rotulo: string }): ReferenciaDaBase {
  const comoItem = resposta.itens.find(candidato => candidato.id === ref.id && candidato.tipo === "municipio") ?? null;
  const membro = resposta.referencia?.membros.find(candidato => candidato.id === ref.id);
  const noGrafico = !!comoItem?.referencia;
  const fonte = noGrafico || !membro ? comoItem : membro;
  return { id: ref.id, rotulo: ref.rotulo, uf: fonte?.uf ?? null, populacao: numero(fonte?.populacao), quantidade: numero(fonte?.quantidade),
    densidade: numero(fonte?.densidade), noGrafico, emAnalise: !!comoItem && !noGrafico };
}
/** Um território da base da Análise Espacial com a referência mais próxima dele (25/10/2026, pedido do responsável): a tela
 * mostra a referência no gráfico (bolha de contexto com a mira, no início do eixo, ligada à base) e no mapa. Só estado visual
 * (RQ-REP-06): todo número vem do motor, e nada é calculado entre os dois (CAP-REF-01). Nulo sem base ou com a base fora da
 * resposta. */
export function parDaBase(resposta: Pick<PainelResposta, "itens" | "referencia"> | null, base: string | null | undefined): ParDaBase | null {
  if (!resposta || !base) return null;
  const item = resposta.itens.find(candidato => candidato.id === base && candidato.tipo === "municipio");
  if (!item) return null;
  const referencias = item.referencia ? [] : item.referenciaDoItem ?? [];
  if (!referencias.length) return { base: item, referencias: [], distancia: null, motivo: motivosDe(item, "distancia")[0] ?? null };
  return { base: item, referencias: referencias.map(ref => referenciaDaBase(resposta, ref)), distancia: numero(item.distancia_km), motivo: null };
}
/** Os pares dos territórios da base, na ordem deles. */
export const paresDasBases = (resposta: Pick<PainelResposta, "itens" | "referencia"> | null, bases: string[]) =>
  bases.map(base => parDaBase(resposta, base)).filter((par): par is ParDaBase => !!par);
/** As referências de contexto do gráfico: as dos pares que o gráfico não desenha como bolha, uma vez cada. */
export function referenciasDeContexto(pares: ParDaBase[]): ReferenciaDeContexto[] {
  const porId = new Map<string, ReferenciaDeContexto>();
  for (const par of pares) for (const referencia of par.referencias) {
    if (referencia.noGrafico) continue;
    const contexto = porId.get(referencia.id) ?? { referencia, bases: [] };
    contexto.bases.push({ base: par.base, distancia: par.distancia });
    porId.set(referencia.id, contexto);
  }
  return [...porId.values()];
}

const comE = (nomes: string[]) => nomes.length < 2 ? nomes.join("") : nomes.slice(0, -1).join(", ") + " e " + nomes[nomes.length - 1];

/** O texto de um território da base só: ele, a referência mais próxima e a distância do motor, ou o motivo sem referência. */
export function textoDoParDaBase(par: ParDaBase): string {
  const [primeira, ...empate] = par.referencias;
  if (!primeira) return "Base: " + par.base.rotulo + ". " +
    (par.motivo ?? "Sem referência no recorte (o motivo está em Não avaliáveis, nos Detalhes).");
  return "Base: " + par.base.rotulo + " · referência mais próxima: " + primeira.rotulo +
    (empate.length ? " (empate com " + comE(empate.map(ref => ref.rotulo)) + ")" : "") +
    (par.distancia !== null ? ", a " + formatarNumero(par.distancia) + " km em linha reta" : "") + ".";
}
/** Quantos pares a linha acima do desenho escreve; os outros ficam nas dicas e na tabela. */
const PARES_NO_TEXTO = 4;
const parCurto = (par: ParDaBase) => !par.referencias.length ? par.base.rotulo + ": sem referência"
  : par.base.rotulo + " → " + par.referencias.map(ref => ref.rotulo).join(" ou ") + (par.referencias.length > 1 ? " (empate)" : "") +
    (par.distancia !== null ? ", " + formatarNumero(par.distancia) + " km" : "");
/** A linha acima do desenho (`analise-par-base`): com um território na base, o par dele; com mais, quantos são e os primeiros pares
 * (base → referência mais próxima, distância do motor); quando o gráfico liga menos do que os pares com referência, quantas
 * ligações desenha. Concorda com o gênero da unidade (28/10/2026: "cada uma ligada" nas comunas de uma planilha). */
export function textoDosTerritoriosBase(c: { pares: ParDaBase[]; ligados: number; rotulos?: RotulosTerritoriais }): string {
  const { pares, ligados } = c;
  const cadaUm = c.rotulos && fem(c.rotulos.unidade) ? "cada uma ligada" : "cada um ligado";
  if (!pares.length) return "Nenhum território na base: o gráfico e o mapa não mostram as ligações até a referência.";
  const comReferencia = pares.filter(par => par.referencias.length).length;
  const ligacoes = ligados >= comReferencia ? "" : !ligados ? " Nenhuma ligação à vista no gráfico: " + (comReferencia === 1
    ? "a bolha da base está fora" : "as bolhas da base estão fora") + " da régua ou dos filtros."
    : " O gráfico desenha " + ligados + " dessas ligações: no máximo " + MAX_LIGACOES + ", e só das bolhas à vista.";
  if (pares.length === 1) return textoDoParDaBase(pares[0]) + ligacoes;
  const resto = pares.length - PARES_NO_TEXTO;
  return "Base: " + inteiro.format(pares.length) + " · " + cadaUm + " à sua referência mais próxima por linha tracejada: " +
    pares.slice(0, PARES_NO_TEXTO).map(parCurto).join("; ") + (resto > 0 ? "; e mais " + inteiro.format(resto) + " (nas dicas e na tabela)" : "") +
    "." + ligacoes;
}

/** Quantas distâncias a dica de uma referência de contexto lista; as outras ficam na tabela. */
const DISTANCIAS_NA_DICA = 4;
/** A dica da bolha de contexto de uma referência: os valores do motor e a distância até cada território da base ligado a ela. */
export function dicaDaReferenciaDeContexto(contexto: ReferenciaDeContexto): Dica {
  const { referencia: ref, bases } = contexto;
  const nomes = bases.map(item => item.base.rotulo);
  return { titulo: ref.rotulo, subtitulo: "Referência mais próxima de " +
      (nomes.length > 3 ? nomes.slice(0, 3).join(", ") + " e mais " + (nomes.length - 3) : comE(nomes)),
    linhas: [
      { rotulo: "População", valor: ref.populacao === null ? "Não avaliável" : formatarNumero(ref.populacao, true) + " habitantes" },
      { rotulo: "Profissionais", valor: ref.quantidade === null ? "Não avaliável" : formatarNumero(ref.quantidade, true) },
      { rotulo: "Densidade", valor: formatarIndicador(ref.densidade, "densidade") },
      ...bases.slice(0, DISTANCIAS_NA_DICA).map(item => ({ rotulo: "Distância até " + item.base.rotulo,
        valor: item.distancia === null ? "Não avaliável" : formatarNumero(item.distancia) + " km" }))],
    notas: [...(bases.length > DISTANCIAS_NA_DICA ? ["E mais " + (bases.length - DISTANCIAS_NA_DICA) + " territórios da base ligados a esta " +
        "referência (as distâncias estão na tabela)."] : []),
      ref.emAnalise ? "Também está na base: a outra bolha com este nome mostra a distância até a sua própria referência."
        : "Fora da base: aparece só como referência, no início do eixo (0 km)."], acao: null };
}

// ================================================================================================ apresentação das abas e da tendência
/** Apresentação de cada aba: o que a aba faz, em linguagem simples, só com o que a área faz de fato. Nas análises (24/10/2026),
 * ela fica em "Entenda esta análise", que começa recolhido (25/10/2026); a da Seleção de Territórios é curta e fica à
 * vista. Os nomes territoriais vêm dos rótulos da fonte (municípios e estados na base do Brasil; distritos, províncias e outros
 * nas planilhas). */
export type Apresentacao = { titulo: string; paragrafos: string[]; itens?: { termo: string; texto: string }[]; nota?: string };
/** A orientação da Seleção de Territórios (24/10/2026): curta, sem instruções de uso das caixas. */
export const TEXTO_DA_SELECAO = "Escolha os territórios que entram nas análises. A seleção vale para todas elas e pode ser mudada a " +
  "qualquer momento.";

/** O que cada classe de tendência quer dizer (CAP-TEN-01, DA-15), para quem não é da estatística (24/10/2026): o que aconteceu
 * com o indicador nos 4 períodos, com um exemplo curto. De um período para o seguinte há uma alta, uma queda ou uma pausa; a
 * classe sai da direção delas e de o tamanho delas crescer ou diminuir (comparado por mês). Só descreve a regra do motor; não
 * cria classe nem critério. */
export const DESCRICAO_DAS_CLASSES: Record<string, string> = {
  CRESCIMENTO: "o indicador subiu e não caiu em nenhum período, mas sem ganhar nem perder ritmo de forma contínua: houve uma " +
    "pausa, ou as altas foram do mesmo tamanho, ou ora maiores, ora menores. Exemplo: 10, 12, 12 e 15.",
  CRESCIMENTO_ACELERADO: "o indicador subiu em todos os períodos, e cada alta foi do mesmo tamanho ou maior que a anterior, com " +
    "pelo menos uma maior: o crescimento ganhou ritmo. Exemplo: 10, 11, 13 e 16 (altas de 1, 2 e 3).",
  CRESCIMENTO_DESACELERADO: "o indicador subiu em todos os períodos, mas cada alta foi do mesmo tamanho ou menor que a anterior, " +
    "com pelo menos uma menor: continua subindo, em ritmo menor. Exemplo: 10, 13, 15 e 16 (altas de 3, 2 e 1).",
  DECLINIO: "o indicador caiu e não subiu em nenhum período, mas sem ganhar nem perder ritmo de forma contínua: houve uma pausa, " +
    "ou as quedas foram do mesmo tamanho, ou ora maiores, ora menores. Exemplo: 15, 12, 12 e 10.",
  DECLINIO_ACELERADO: "o indicador caiu em todos os períodos, e cada queda foi do mesmo tamanho ou maior que a anterior, com pelo " +
    "menos uma maior: a queda ganhou ritmo. Exemplo: 16, 15, 13 e 10 (quedas de 1, 2 e 3).",
  DECLINIO_DESACELERADO: "o indicador caiu em todos os períodos, mas cada queda foi do mesmo tamanho ou menor que a anterior, com " +
    "pelo menos uma menor: continua caindo, em ritmo menor. Exemplo: 16, 13, 11 e 10 (quedas de 3, 2 e 1).",
  SEM_CLASSIFICACAO: "o indicador subiu num período e caiu em outro (mudou de direção), ou ficou igual em todos. Exemplos: 10, 12, " +
    "11 e 13; 10, 10, 10 e 10.",
};
/** O "não avaliável" da tendência, na mesma linguagem das classes. */
export const DESCRICAO_NAO_AVALIAVEL = "falta o valor do indicador em algum dos 4 períodos (a classificação precisa dos quatro), ou os " +
  "valores não são comparáveis entre os períodos.";
/** O que a classe atribuída quer dizer, numa frase, junto do resultado de um território só (24/10/2026): "Aceleração do
 * crescimento: o indicador subiu em todos os períodos…". Sem o exemplo, que fica na explicação da análise. Null sem classe. */
export function significadoDaClasse(t: TendenciaItem | null | undefined): string | null {
  if (!t) return null;
  if (!t.avaliavel) return "Não avaliável: " + DESCRICAO_NAO_AVALIAVEL;
  const descricao = t.classe ? DESCRICAO_DAS_CLASSES[t.classe] : undefined;
  if (!descricao) return null;
  return t.rotulo + ": " + descricao.replace(/\s*Exemplos?:.*$/, "");
}

export function apresentacaoDaAba(aba: Aba, c: { rotulos: RotulosTerritoriais; brasil: boolean; comGrupos: boolean; semDados?: boolean }):
  Apresentacao {
  const unidade = c.rotulos.unidade, grupo = c.rotulos.grupo ?? ROTULOS_GENERICOS.grupo!;
  const os = artigo(unidade, true), us = unidade.plural;
  // O que se analisa: na base do Brasil, o Brasil, os estados ou os municípios; numa planilha, as unidades dela, com o gênero
  // delas ("cada comuna escolhida", "Cada bolha é uma comuna").
  const territorio = c.brasil && c.comGrupos ? "território" : unidade.singular;
  const territorios = c.brasil && c.comGrupos ? "territórios" : us;
  const f = !(c.brasil && c.comGrupos) && fem(unidade);
  const escolhido = f ? "escolhida" : "escolhido", um = f ? "uma" : "um";
  if (aba === "territorios") return { titulo: NOME_SELECAO, paragrafos: [c.semDados
    ? "Depois de escolher os dados, a lista de territórios aparece aqui." : TEXTO_DA_SELECAO] };
  if (aba === "distribuicao") return { titulo: NOMES_FAMILIAS.distribuicao, paragrafos: [
    "Mostra o indicador de cada " + territorio + " " + escolhido + " na competência que você escolhe: a densidade (profissionais por " +
      "1.000 habitantes) ou a quantidade de profissionais. Cada bolha é " + um + " " + territorio + ": a altura mostra o valor, e o " +
      "tamanho, a população.",
    "Com vári" + (f ? "as " : "os ") + territorios + ", você pode dividi-l" + (f ? "as" : "os") + " em grupos do mesmo tamanho " +
      "(quartis, quintis ou decis) ou em faixas de " +
      "valores e usar as Ferramentas: Régua, Condições, Ordenar, Comparar e Juntar. No mapa, os pontos aparecem em 5 grupos " +
      "iguais (quintis) do indicador."] };
  if (aba === "espacial") return { titulo: NOMES_FAMILIAS.espacial, paragrafos: [
    "Mede a distância em linha reta entre cada " + unidade.singular + " da base e a referência mais próxima " + (fem(unidade) ? "dela" : "dele") +
      ". Na Escolha dos territórios, a base e a referência são escolhidas do mesmo jeito, em três etapas: de onde partir (" +
      (c.brasil ? "o país, uma ou mais regiões, um ou mais estados" : c.comGrupos ? "a planilha inteira, " + (fem(grupo) ? "uma ou mais " : "um ou mais ") +
        grupo.plural : "a planilha inteira") + " ou a seleção prévia), filtros por densidade, população ou quantidade e a escolha de " +
      (fem(unidade) ? "todas as que atendem ou só das marcadas" : "todos os que atendem ou só dos marcados") + "." +
      (c.brasil || c.comGrupos ? " A referência também pode ser procurada n" + (c.brasil ? "o mesmo estado ou na mesma região" : (fem(grupo) ? "a mesma " : "o mesmo ") +
        grupo.singular) + " de cada " + unidade.singular + " da base." : "") + " " + maiuscula(artigo(unidade, false)) + " própri" +
      (fem(unidade) ? "a" : "o") + " " + unidade.singular + " nunca é a sua referência. O eixo horizontal mostra a distância, e o vertical, " +
      "o indicador.",
    "A distância é medida sobre a superfície da Terra, a partir das coordenadas de cada " + unidade.singular +
      (c.brasil ? " (a sede municipal)" : "") + ", e não é um trajeto por estradas." +
      (c.comGrupos && c.brasil ? " Esta análise usa " + us + ": " + artigo(grupo, true) + " " + grupo.plural + " e o Brasil não têm " +
        "um ponto no mapa." : "")] };
  if (aba === "tendencia") return { titulo: NOMES_FAMILIAS.tendencia, paragrafos: [
    "Mostra como o indicador mudou nos últimos 4 períodos, anuais ou semestrais (você escolhe no campo Período), e classifica o " +
      "comportamento de cada " + territorio + ". De um período para o seguinte, o indicador sobe (alta), cai (queda) ou fica igual " +
      "(pausa). A classe depende da direção dessas mudanças e de o tamanho delas aumentar ou diminuir."],
    itens: [...CLASSES_TENDENCIA.map(classe => ({ termo: classe.rotulo, texto: DESCRICAO_DAS_CLASSES[classe.codigo] })),
      { termo: "Não avaliável", texto: DESCRICAO_NAO_AVALIAVEL }],
    nota: "Quando os períodos não têm a mesma distância (de janeiro a junho são 5 meses; de junho a janeiro, 7), o tamanho de cada " +
      "alta ou queda é comparado por mês. Na visão Tendência, o quadro de setas mostra a classe de cada " + territorio + ": a seta para " +
      "cima é alta; para baixo, queda; para o lado, pausa. A visão Trajetória mostra a variação entre o primeiro e o último período, " +
      "com os períodos do meio no caminho, e a visão Série temporal, a linha de cada " + territorio + " " + escolhido + " em toda a " +
      "série da base (ou no intervalo que você escolher), sem classificação. A referência do método fica em Detalhes, na aba Método e " +
      "procedência." };
  return { titulo: NOMES_FAMILIAS.rotatividade, paragrafos: [
    "Acompanha os profissionais presentes no período inicial (a coorte inicial) e mostra, para cada " + unidade.singular +
      ", quantos continuaram e quantos saíram até o período final, em barras de 100%.",
    "Para isso, os dados precisam identificar a mesma pessoa nos dois períodos, numa coluna de identificador individual." +
      (c.brasil ? " Os dados do Brasil têm contagens de profissionais, e não pessoas identificadas: para usar esta análise, envie " +
        "uma planilha com o identificador individual." : "")] };
}

/** O motivo de uma tendência sem classe, em palavras e sem o código (23/10/2026; linguagem de 24/10/2026); para as
 * classificadas, o que a classe quer dizer (significadoDaClasse). Usa o motivo que o motor devolveu (MotivoSemClassificacao e o
 * motivo de não avaliável). */
export function explicacaoDaTendencia(t: TendenciaItem | null | undefined): string | null {
  if (!t) return null;
  if (!t.avaliavel) {
    if (t.motivoCodigo === "SERIE_INSUFICIENTE")
      return "Não avaliável: falta o valor do indicador em algum dos períodos" + (t.motivoTexto ? " (" + t.motivoTexto + ")" : "") + ".";
    if (t.motivoCodigo === "INCOMPARABILIDADE")
      return "Não avaliável: os valores não são comparáveis entre os períodos" + (t.motivoTexto ? " (" + t.motivoTexto + ")" : "") + ".";
    if (t.motivoTexto) return "Não avaliável: " + t.motivoTexto + ".";
    // Sem o código nem o texto do motivo (uma resposta de antes), o rótulo do motor, que já diz o motivo.
    return t.rotulo && t.rotulo !== "Não avaliável" ? t.rotulo : "Não avaliável.";
  }
  if (t.classe === "SEM_CLASSIFICACAO") {
    if (t.motivoCodigo === "MUDANCA_DE_DIRECAO") return "Sem classificação: o indicador subiu num período e caiu em outro (mudou de direção).";
    if (t.motivoCodigo === "SERIE_ESTAVEL") return "Sem classificação: o indicador ficou igual em todos os períodos.";
    // Sem o código (uma resposta de antes), o texto do motivo, sem o código entre parênteses.
    const motivo = t.motivoTexto || (t.motivo ? t.motivo.replace(/\s*\([A-Z_]+\)\s*$/, "").trim() : "");
    return "Sem classificação" + (motivo ? ": " + minuscula(motivo) : "") + ".";
  }
  return significadoDaClasse(t);
}

/** Nota abaixo das contagens quando há unidades sem classificação: quantas por motivo, do motor; se nenhuma unidade avaliável
 * recebeu classe, a explicação da regra (uma mudança de direção basta). Não muda o método. */
export function notaSemClassificacao(topo: TendenciaTopo | null, c: { rotulos: RotulosTerritoriais; brasil: boolean }): string | null {
  if (!topo) return null;
  const sem = topo.contagens.SEM_CLASSIFICACAO ?? 0;
  if (!sem) return null;
  const unidade = c.rotulos.unidade;
  const direcao = topo.semClassificacaoPorMotivo.MUDANCA_DE_DIRECAO ?? 0, estavel = topo.semClassificacaoPorMotivo.SERIE_ESTAVEL ?? 0;
  const partes = [direcao ? quantos(direcao, unidade) + (direcao === 1 ? " mudou" : " mudaram") + " de direção (o indicador subiu num " +
      "período e caiu em outro)" : "",
    estavel ? quantos(estavel, unidade) + (estavel === 1 ? " ficou igual" : " ficaram iguais") + " em todos os períodos" : ""].filter(Boolean);
  const classificadas = CLASSES_TENDENCIA.filter(classe => classe.codigo !== "SEM_CLASSIFICACAO")
    .reduce((soma, classe) => soma + (topo.contagens[classe.codigo] ?? 0), 0);
  const motivos = partes.length ? "Sem classificação: " + partes.join("; ") + "." : "";
  if (classificadas) return motivos || null;
  return (motivos ? motivos + " " : "") + "Nenhum" + (fem(unidade) ? "a " : " ") + unidade.singular + " recebeu classe nestes períodos: " +
    "para ter classe, o indicador precisa ir na mesma direção em todos os períodos, e basta subir num e cair em outro para ficar " +
    "sem classificação. É o resultado do método, não falta de dados.";
}

// ================================================================================================ Desfazer: o histórico da interação
/** Desfazer (24/10/2026, pedido do responsável; até 25/10/2026, "Voltar"): um desfazer sequencial, como o Ctrl+Z, da interação na
 * área. Cada ação reversível (marcar ou desmarcar territórios, trocar o nível, abrir a lista de um estado, Limpar seleção, trocar de
 * aba, mudar um ajuste, um filtro ou a vista) guarda o estado de antes; Desfazer devolve o último guardado, um passo por vez. Passos
 * seguidos do mesmo tipo contínuo (o arraste da régua) em menos de PASSO_CONTINUO_MS viram um só, com o estado de antes do
 * primeiro. O histórico não é o do navegador e não sai da área: recomeça com outra fonte de dados ou com Nova análise. */
export type PassoDaInteracao<T> = { rotulo: string; tipo: string; quando: number; estado: T };
export const MAX_PASSOS = 80;
export const PASSO_CONTINUO_MS = 900;
export function empilharPasso<T>(pilha: PassoDaInteracao<T>[], passo: PassoDaInteracao<T>): PassoDaInteracao<T>[] {
  const topo = pilha.at(-1);
  if (topo && passo.tipo.startsWith("continuo:") && topo.tipo === passo.tipo && passo.quando - topo.quando < PASSO_CONTINUO_MS)
    return [...pilha.slice(0, -1), { ...topo, quando: passo.quando }];
  return [...pilha, passo].slice(-MAX_PASSOS);
}
/** O texto do botão Desfazer (no `title` e no rótulo acessível): o que o próximo Desfazer desfaz, ou que não há o que desfazer. */
export const textoDoDesfazer = (passo: { rotulo: string } | null | undefined) =>
  passo ? "Desfazer: " + minuscula(passo.rotulo.replace(/\.$/, "")) : "Nada para desfazer ainda";
/** O aviso depois de um Desfazer: o passo que foi desfeito. */
export const textoDoDesfeito = (passo: { rotulo: string }) => "Desfeito: " + minuscula(passo.rotulo.replace(/\.$/, "")) + ".";
