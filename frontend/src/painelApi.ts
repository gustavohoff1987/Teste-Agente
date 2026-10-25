// Cliente do motor da área de análise da página única (POST /api/painel e, desde 23/10/2026, POST /api/painel/mapa; a rota
// POST /api/painel/referencias continua no motor, mas a tela não a usa desde 24/10/2026), no contrato de 22/10/2026 (seção 3
// do contrato entre as frentes; Docs/PAINEL_INTEGRADO.md). É o
// ÚNICO lugar com os nomes de campos do motor: o formulário, as opções (montadas em painelModel.montarOpcoes com os tipos
// daqui), a leitura dos erros (422, com a pendência de premissa) e a normalização da resposta para os tipos da tela. Se o
// motor mudar um nome, ajuste só este arquivo. Todo número vem do motor; a tela só posiciona, filtra (estado visual) e
// desenha. Nada calcula aqui.
import { contextRevision, sessionFetch as fetch } from "./conversationSession";
import type { DadosDoMapa } from "./mapaContrato";

// ------------------------------------------------------------------------------------------------ pedido
export type PainelIndicador = "densidade" | "quantidade";
export type PainelAtributo = "densidade" | "quantidade" | "populacao";
export type AtributoOrdenacao = PainelAtributo | "distancia_km" | "variacao";
export type AtributoCondicao = PainelAtributo | "distancia_km";
export type PainelOrdem = "desc" | "asc";
/** Nível do gráfico: os municípios (ou as unidades da planilha), os estados ou, desde 24/10/2026, o Brasil inteiro como uma
 * unidade (só na base do Brasil). */
export type PainelNivel = "estados" | "municipios" | "brasil";
/** Premissas de uma planilha, com os nomes de /api/analyze: textos e, em `confirmed_roles`, os papéis escolhidos pela pessoa. */
export type Premissas = Record<string, string | string[]>;
/** Universo das unidades, na forma de `options.abrangencia.municipios`. Em planilhas, `estados` leva os valores do grupo
 * (coluna-mãe) e `ids` leva `code:<código>` ou `name:<nome>`. */
export type PainelMunicipios = { todos: boolean; estados: string[]; ids: string[] };
export type PainelUniverso = { municipios: PainelMunicipios };
export type PainelCriterio = { atributo: PainelAtributo; ordem: PainelOrdem };
/** Conjunto agregado (CAP-AGR-01): id com letras, números, _ ou - (até 64), rótulo de até 120 caracteres, dois ou mais membros. */
export type PainelConjuntoPedido = { id: string; rotulo: string; membros: string[] };
/** Um membro: referência município; dois ou mais: conjunto de referência (distância até o membro mais próximo). O critério só
 * registra a origem (CAP-REF-01); com o universo da lista, a origem cita a posição exata vista pela pessoa. É a forma que a
 * conversa usa ("use Manaus como referência"). */
export type ReferenciaPorMembros = { membros: string[]; criterio?: PainelCriterio & { universo?: PainelUniverso } };
export type OperadorCondicao = "<" | "<=" | ">" | ">=";
/** Território de referência (24/10/2026): primeiro os elegíveis (a delimitação e a condição), depois, para cada território, o
 * mais próximo ou o mais distante deles, sem ele mesmo. "grupos" e "regioes" levam os valores escolhidos (os prefixos IBGE dos
 * estados, os nomes das regiões, os valores do grupo da planilha); as regiões existem só na base do Brasil. */
export type RelacaoEspacial = "mais_proxima" | "mais_distante";
export type TipoDelimitacao = "todos" | "mesmo_grupo" | "grupos" | "mesma_regiao" | "regioes";
export type ReferenciaElegivel = { relacao: RelacaoEspacial; delimitacao: { tipo: TipoDelimitacao; valores?: string[] };
  condicao: { atributo: PainelAtributo; operador: OperadorCondicao; valor: number } };
export type PainelReferenciaPedido = ReferenciaPorMembros | ReferenciaElegivel;
export type CondicaoPedido = { atributo: AtributoCondicao; operador: OperadorCondicao; valor: number };
export type OrdenarPedido = { atributo: AtributoOrdenacao; ordem: PainelOrdem; primeiros?: number };
export type TipoGrupos = "quartis" | "quintis" | "decis";

/** Opções de /api/painel no formato da página única (chaves estritas no motor: chave desconhecida dá 422). `nivel` e
 * `indicador` vão em todo pedido: sem `nivel`, o motor responde no contrato de 21/10, que não conhece as chaves da página
 * única; o `indicador` governa grupos, faixas, tendência, comparação e a ordenação pela variação. `premissas` só nas
 * planilhas (na base do Brasil, o motor recusa). */
export type PainelOpcoes = {
  nivel: PainelNivel;
  indicador: PainelIndicador;
  competencia: string;
  categoria: string;
  base?: PainelUniverso;
  /** Nível estados: os estados escolhidos (prefixos IBGE); sem a lista, todos (24/10/2026). */
  estados?: string[];
  conjuntos?: PainelConjuntoPedido[];
  referencia?: PainelReferenciaPedido;
  faixas_distancia?: number[];
  competencia_inicial?: string;
  tendencia?: { competencias: string[] };
  /** Série temporal (24/10/2026): as competências do intervalo, com os valores observados, sem classificação. */
  serie?: { competencias: string[] };
  grupos?: { tipo: TipoGrupos };
  /** Grupos por posição só para a cor do mapa (23/10/2026): os quintis do motor (CAP-DIS-02, a mesma conta de `grupos`) quando a
   * análise não tem cor própria. Não mudam o gráfico, a frase-resumo, a tabela nem o CSV. */
  grupos_mapa?: { tipo: TipoGrupos };
  faixas?: number[];
  condicoes?: CondicaoPedido[];
  ordenar?: OrdenarPedido;
  comparar?: string[];
  rotatividade?: { inicial: string; final: string };
  premissas?: Premissas;
  /** Só nas planilhas (24/10/2026): os nomes da unidade e do grupo que a pessoa confirmou, para a resposta (os rótulos, a
   * frase-resumo) falar deles; sem eles, o motor responde com "unidades". Na base do Brasil, o motor recusa. */
  rotulos?: RotulosTerritoriais;
};

/** Opções de /api/painel/mapa: a competência e a categoria do gráfico; nas planilhas, as premissas e os rótulos (na base do
 * Brasil, o motor recusa os dois). */
export type MapaOpcoes = { competencia: string; categoria: string; premissas?: Premissas; rotulos?: RotulosTerritoriais };

// ------------------------------------------------------------------------------------------------ resposta (normalizada)
/** Nomenclatura territorial: na base do Brasil, município e estado; nas planilhas, o que a pessoa confirmou ("distrito",
 * "província"…). `genero` é opcional; sem ele, a tela deduz pela terminação (concordância simples). */
export type Rotulo = { singular: string; plural: string; genero?: "m" | "f" };
export type RotulosTerritoriais = { unidade: Rotulo; grupo: Rotulo | null };

export type PainelValores = { populacao: number | null; quantidade: number | null; densidade: number | null };
/** distancia e variacao: null quando não foram pedidas; false quando foram pedidas e não são avaliáveis. */
export type PainelAvaliavel = { densidade: boolean; distancia: boolean | null; variacao: boolean | null };
export type PainelDominio = [number, number];
export type Posicao = { indice: number; rotulo: string };
export type FamiliaTendencia = "CRESCIMENTO" | "DECLINIO" | "NENHUMA";
/** Tendência de um item (CAP-TEN-01, DA-15): classe e rótulo oficiais, motivo, observações e velocidades do motor. */
export type TendenciaItem = {
  classe: string | null; rotulo: string; motivo: string | null; familia: FamiliaTendencia | null; avaliavel: boolean;
  /** Código do motivo (MUDANCA_DE_DIRECAO, SERIE_ESTAVEL, SERIE_INSUFICIENTE, INCOMPARABILIDADE) e o texto do motor, à parte: a
   * tela explica o motivo em palavras, sem o código (23/10/2026); `motivo`, com o código entre parênteses, segue no CSV. */
  motivoCodigo: string | null; motivoTexto: string | null;
  observacoes: { competencia: string; valor: number | null }[];
  /** Velocidade entre duas observações vizinhas, na unidade do indicador por unidade de tempo (mês nas competências AAAAMM). */
  velocidades: { de: string; ate: string; valor: number }[];
};
export type SituacaoCondicao = "ATENDE" | "NAO_ATENDE" | "NAO_AVALIAVEL";
export type CondicoesItem = { situacao: SituacaoCondicao; porCondicao: { texto: string; situacao: SituacaoCondicao | null }[];
  motivo: string | null };
/** Série temporal de um item (24/10/2026): o valor observado em cada competência do intervalo (null sem valor, nunca zero). Um
 * conjunto com membros diferentes no intervalo vem com `comparavel` falso e o motivo: os pontos não são ligados (RQ-REP-15). */
export type SerieItem = { observacoes: { competencia: string; valor: number | null }[]; comparavel: boolean; motivo: string | null };
/** Rotatividade (CAP-ROT-01): contagens e percentuais do motor, sempre da coorte inicial. A tela não divide nada. */
export type RotatividadeItem = { coorteInicial: number | null; permaneceram: number | null; sairam: number | null;
  permanencia: number | null; saida: number | null; avaliavel: boolean; motivo: string | null };

export type PainelItem = {
  id: string;
  tipo: "municipio" | "estado" | "conjunto" | "brasil";
  rotulo: string;
  uf: string | null;
  /** Conjunto: identificadores das unidades agregadas, na ordem do pedido. */
  membros?: string[];
  populacao: number | null;
  quantidade: number | null;
  /** Profissionais por 1.000 habitantes, em precisão integral (a tela arredonda só para exibir). */
  densidade: number | null;
  /** Conjunto: "SOMA_DOS_COMPONENTES" (RQ-REP-14). */
  contagem?: string;
  distancia_km: number | null;
  /** Conjunto: distância do membro mais distante (a do mais próximo fica em distancia_km). */
  distancia_km_max?: number | null;
  inicial: PainelValores;
  /** (v2 − v1) / v1 × 100 por CAP-TMP-01; null quando não avaliável, com o motivo. */
  variacao_percentual: PainelValores;
  avaliavel: PainelAvaliavel;
  /** Textos em português, cada um terminado pelo código entre parênteses. */
  motivos: string[];
  /** Membro da referência (distância 0) ou conjunto igual à referência. */
  referencia: boolean;
  tendencia: TendenciaItem | null;
  grupo: Posicao | null;
  /** Grupo do item nos grupos do mapa (`grupos_mapa`), só para a cor do mapa. */
  grupoMapa: Posicao | null;
  faixa: Posicao | "fora" | null;
  faixa_distancia: Posicao | "fora" | null;
  /** A referência do item: com membros escolhidos, o membro da referência mais próximo (`referencia_mais_proxima` do motor); com o
   * território de referência por elegibilidade, o mais próximo ou o mais distante dos elegíveis (`referencia_do_item`). Mais de um
   * quando há empate (explícito). */
  referenciaDoItem: { id: string; rotulo: string }[] | null;
  condicoes: CondicoesItem | null;
  ordem: { posicao: number | null } | null;
  rotatividade: RotatividadeItem | null;
  serie: SerieItem | null;
};
/** A referência da resposta: um município ou um conjunto escolhidos (membros) ou, por elegibilidade, a definição (relação,
 * delimitação e condição, com os textos do motor), as contagens da condição e os territórios que ficaram como referência. */
export type PainelReferenciaResposta = { tipo: "municipio" | "conjunto" | "elegiveis"; membros: { id: string; rotulo: string }[]; origem: string;
  relacao?: RelacaoEspacial; delimitacao?: { tipo: TipoDelimitacao; valores: string[]; texto: string };
  condicao?: { atributo: PainelAtributo; operador: OperadorCondicao; valor: string; texto: string };
  elegiveis?: { universo: number; atende: number; naoAtende: number; naoAvaliaveis: number } };
export type Contagens = Record<string, number>;
export type TendenciaTopo = { janela: string[]; contagens: Contagens; familias: Contagens; naoAvaliaveis: number | null;
  bloqueio: string | null; unidadeTempo: string | null;
  /** Unidades sem classificação por motivo, do motor (MUDANCA_DE_DIRECAO e SERIE_ESTAVEL). */
  semClassificacaoPorMotivo: Contagens };
export type GruposTopo = { tipo: string; cortes: number[]; contagens: number[]; rotulos: string[] };
export type FaixasTopo = { limites: number[]; rotulos: string[]; contagens: number[]; fora: number | null; naoAvaliaveis: number | null };
export type CondicoesTopo = { contagens: Partial<Record<SituacaoCondicao, number>>; textos: string[] };
export type OrdenacaoTopo = { atributo: string; ordem: string; primeiros: number | null; empatesNoCorte: boolean | null; texto: string | null };
export type ValorComparado = { id: string; rotulo: string; valor: number | null };
export type LinhaComparacao = { atributo: string; maior: ValorComparado[]; menor: ValorComparado[];
  diferencas: { entre: string[]; valor: number | null; texto: string | null }[] };
export type ComparacaoTopo = { itens: string[]; linhas: LinhaComparacao[]; textos: string[] };
export type ChaveDisponibilidade = "espacial" | "tendencia" | "rotatividade" | "estados" | "grupos";
export type Disponibilidade = Partial<Record<ChaveDisponibilidade, { disponivel: boolean; motivo: string }>>;
export type ContextoBrasil = { densidade: number | null; quantidade: number | null; populacao: number | null; competencia: string | null };
/** A série temporal do topo: o intervalo pedido (do primeiro ao último período) e a unidade dos valores. */
export type SerieTopo = { competencias: string[]; inicio: string; fim: string; unidadeValor: string | null };

export type PainelResposta = {
  competencia: string;
  competencia_inicial: string | null;
  categoria: string;
  versao_base: string | null;
  chave_execucao: string;
  nivel: PainelNivel;
  referencia: PainelReferenciaResposta | null;
  itens: PainelItem[];
  /** [mínimo, máximo] dos valores avaliáveis devolvidos (densidade, quantidade, populacao, distancia_km e as variações). */
  dominios: Partial<Record<string, PainelDominio | null>>;
  notas: string[];
  /** Códigos de limitação (SOMA_COM_POSSIVEL_DUPLA_CONTAGEM, AGREGADO_PARCIAL, DISTANCIA_GEODESICA_DIRETA…). */
  limitacoes: string[];
  tendencia: TendenciaTopo | null;
  serie: SerieTopo | null;
  grupos: GruposTopo | null;
  /** Os grupos do mapa (`grupos_mapa`), na mesma forma de `grupos`. */
  gruposMapa: GruposTopo | null;
  faixas: FaixasTopo | null;
  faixasDistancia: FaixasTopo | null;
  condicoes: CondicoesTopo | null;
  ordenacao: OrdenacaoTopo | null;
  comparacao: ComparacaoTopo | null;
  contextoBrasil: ContextoBrasil | null;
  disponibilidade: Disponibilidade;
  sessao: { registrado: boolean; resultId: string | null } | null;
  rotulos: RotulosTerritoriais | null;
  /** Indicador que o motor usou no cálculo (a frase-resumo fala dele); null na resposta de antes, que não o trazia. */
  indicador: PainelIndicador | null;
  /** Frase-resumo do motor (23/10/2026): só números conferidos do resultado, sem julgamento nem causa. A tela só a mostra. */
  resumo: { texto: string } | null;
};

/** Pendência de premissa (ChoiceRequired): o motor pede uma escolha (referencial, formato de número…) antes de calcular. */
export type Pendencia = { chave: string; texto: string; opcoes: { valor: string; rotulo: string }[] };
export class ErroDoMotor extends Error {
  status: number;
  pendencia: Pendencia | null;
  constructor(mensagem: string, status: number, pendencia: Pendencia | null) {
    super(mensagem);
    this.status = status;
    this.pendencia = pendencia;
  }
}

// ------------------------------------------------------------------------------------------------ fonte e formulário
/** Fonte do pedido: a base do Brasil (oficial) ou a planilha enviada, com o mapeamento confirmado na tela. */
export type FonteDoMotor = { tipo: "brasil" | "arquivo"; apiBase: string; datasetVersion: string; sheet: string;
  mapping: Record<string, string>; arquivo: File | null; geoVersion?: string };

function formulario(fonte: FonteDoMotor, opcoes: object, comGeo: boolean): FormData {
  const form = new FormData();
  form.append("context_revision", String(contextRevision()));
  if (fonte.tipo === "brasil") {
    form.append("dataset", "brazil");
    form.append("scope", "municipal");
    form.append("dataset_version", fonte.datasetVersion);
  } else {
    if (fonte.arquivo) form.append("file", fonte.arquivo);
    if (fonte.datasetVersion) form.append("dataset_version", fonte.datasetVersion);
  }
  form.append("sheet", fonte.sheet || "");
  // Base do Brasil: o perfil oficial ("{}" vale o perfil); planilha: o mapeamento confirmado (o de /api/inspect).
  form.append("mapping", JSON.stringify(fonte.mapping || {}));
  form.append("options", JSON.stringify(opcoes));
  if (comGeo && fonte.geoVersion) form.append("geo_version", fonte.geoVersion);
  return form;
}

const texto = (valor: unknown): string | null => typeof valor === "string" && valor.trim() ? valor.trim() : null;
const num = (valor: unknown): number | null => typeof valor === "number" && Number.isFinite(valor) ? valor : null;
const lista = (valor: unknown): unknown[] => Array.isArray(valor) ? valor : [];
const objeto = (valor: unknown): Record<string, unknown> | null =>
  valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : null;

function lerPendencia(bruto: unknown): Pendencia | null {
  const p = objeto(bruto);
  if (!p) return null;
  const chave = texto(p.chave);
  if (!chave) return null;
  const opcoes = lista(p.opcoes).map(item => {
    if (typeof item === "string") return { valor: item, rotulo: item };
    const o = objeto(item);
    const valor = texto(o?.valor) ?? texto(o?.id);
    return valor ? { valor, rotulo: texto(o?.rotulo) ?? texto(o?.texto) ?? valor } : null;
  }).filter((item): item is { valor: string; rotulo: string } => !!item);
  return { chave, texto: texto(p.texto) ?? "", opcoes };
}

/** Mesma leitura de readApiResponse: corpo JSON ou erro com a mensagem do motor (em português), o código HTTP e a pendência. */
async function lerResposta(response: Response): Promise<unknown> {
  const raw = await response.text();
  let body: unknown;
  try { body = JSON.parse(raw); }
  catch {
    throw new ErroDoMotor("Não foi possível interpretar a resposta do serviço (HTTP " + response.status + "). Tente novamente ou " +
      "procure suporte.", response.status, null);
  }
  if (!response.ok) {
    const corpo = objeto(body);
    const detail = corpo?.detail;
    const detalhe = objeto(detail);
    const mensagem = typeof detail === "string" ? detail : texto(detalhe?.detail) ?? texto(detalhe?.mensagem) ?? "Falha no processamento da solicitação.";
    throw new ErroDoMotor(mensagem + " (HTTP " + response.status + ")", response.status,
      lerPendencia(corpo?.pendencia ?? detalhe?.pendencia));
  }
  return body;
}

// ------------------------------------------------------------------------------------------------ normalização
const VAZIO3: PainelValores = { populacao: null, quantidade: null, densidade: null };
const valores3 = (bruto: unknown): PainelValores => {
  const o = objeto(bruto);
  return o ? { populacao: num(o.populacao), quantidade: num(o.quantidade), densidade: num(o.densidade) } : { ...VAZIO3 };
};
function posicao(bruto: unknown): Posicao | null {
  const o = objeto(bruto);
  if (!o) return null;
  const indice = num(o.indice);
  return indice === null ? null : { indice, rotulo: texto(o.rotulo) ?? String(indice) };
}
const faixaDe = (bruto: unknown): Posicao | "fora" | null => bruto === "fora" ? "fora" : posicao(bruto);
const FAMILIAS_TENDENCIA: Record<string, FamiliaTendencia> = {
  CRESCIMENTO: "CRESCIMENTO", CRESCIMENTO_ACELERADO: "CRESCIMENTO", CRESCIMENTO_DESACELERADO: "CRESCIMENTO",
  DECLINIO: "DECLINIO", DECLINIO_ACELERADO: "DECLINIO", DECLINIO_DESACELERADO: "DECLINIO", SEM_CLASSIFICACAO: "NENHUMA",
};

function tendenciaDe(bruto: unknown): TendenciaItem | null {
  const o = objeto(bruto);
  if (!o) return null;
  const observacoes = lista(o.observacoes).map(item => {
    const obs = objeto(item);
    const competencia = texto(obs?.competencia) ?? texto(obs?.periodo);
    return competencia ? { competencia, valor: num(obs?.valor) } : null;
  }).filter((item): item is { competencia: string; valor: number | null } => !!item);
  // Velocidades: lista de números (entre observações vizinhas, na ordem) ou de objetos com as competências.
  const observadas = observacoes.filter(item => item.valor !== null).map(item => item.competencia);
  const velocidades = lista(o.velocidades).map((item, indice) => {
    if (typeof item === "number" && Number.isFinite(item))
      return observadas[indice] && observadas[indice + 1] ? { de: observadas[indice], ate: observadas[indice + 1], valor: item } : null;
    const v = objeto(item);
    const valor = num(v?.valor) ?? num(v?.velocidade);
    const de = texto(v?.de) ?? texto(v?.inicio), ate = texto(v?.ate) ?? texto(v?.fim);
    return valor !== null && de && ate ? { de, ate, valor } : null;
  }).filter((item): item is { de: string; ate: string; valor: number } => !!item);
  const classe = texto(o.classe) ?? texto(o.codigo);
  const familiaBruta = texto(o.familia);
  const familia = familiaBruta && ["CRESCIMENTO", "DECLINIO", "NENHUMA"].includes(familiaBruta) ? familiaBruta as FamiliaTendencia
    : classe ? FAMILIAS_TENDENCIA[classe] ?? null : null;
  const avaliavel = typeof o.avaliavel === "boolean" ? o.avaliavel : !!classe;
  // Motivo em texto com o código entre parênteses ("Mudança de direção (MUDANCA_DE_DIRECAO)"), como os demais motivos.
  const codigo = texto(o.motivo), explicacao = texto(o.motivo_texto);
  const motivo = explicacao && codigo && explicacao !== codigo ? explicacao + " (" + codigo + ")" : explicacao ?? codigo;
  return { classe: avaliavel ? classe : null, rotulo: texto(o.rotulo) ?? (classe ? classe : "Não avaliável"), motivo,
    motivoCodigo: codigo, motivoTexto: explicacao, familia: avaliavel ? familia : null, avaliavel, observacoes, velocidades };
}

const SITUACOES: SituacaoCondicao[] = ["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"];
const situacaoDe = (bruto: unknown): SituacaoCondicao | null =>
  typeof bruto === "string" && (SITUACOES as string[]).includes(bruto) ? bruto as SituacaoCondicao : null;
function condicoesDe(bruto: unknown): CondicoesItem | null {
  const o = objeto(bruto);
  const situacao = situacaoDe(o?.situacao);
  if (!o || !situacao) return null;
  const porCondicao = lista(o.por_condicao).map(item => {
    const c = objeto(item);
    return { texto: texto(c?.condicao) ?? texto(c?.texto) ?? texto(c?.rotulo) ?? "", situacao: situacaoDe(c?.situacao ?? c?.estado) };
  });
  return { situacao, porCondicao, motivo: texto(o.motivo) };
}

function rotatividadeDe(bruto: unknown): RotatividadeItem | null {
  const o = objeto(bruto);
  if (!o) return null;
  const percentuais = objeto(o.percentuais);
  const permanencia = num(percentuais?.permanencia) ?? num(o.permanencia_percentual) ?? num(o.permanencia_pct);
  const saida = num(percentuais?.saida) ?? num(percentuais?.rotatividade) ?? num(o.saida_percentual) ?? num(o.rotatividade_percentual);
  return { coorteInicial: num(o.coorte_inicial), permaneceram: num(o.permanecem) ?? num(o.permaneceram) ?? num(o.permanencia),
    sairam: num(o.sairam) ?? num(o.saida), permanencia, saida,
    avaliavel: typeof o.avaliavel === "boolean" ? o.avaliavel : permanencia !== null,
    motivo: texto(o.motivo) ?? texto(o.condicao) };
}

function serieDe(bruto: unknown): SerieItem | null {
  const o = objeto(bruto);
  if (!o) return null;
  const observacoes = lista(o.observacoes).map(item => {
    const obs = objeto(item);
    const competencia = texto(obs?.competencia);
    return competencia ? { competencia, valor: num(obs?.valor) } : null;
  }).filter((item): item is { competencia: string; valor: number | null } => !!item);
  return { observacoes, comparavel: o.comparavel !== false, motivo: texto(o.motivo) };
}

function referenciaProximaDe(bruto: unknown): { id: string; rotulo: string }[] | null {
  const itens = Array.isArray(bruto) ? bruto : bruto ? [bruto] : [];
  const saida = itens.flatMap(item => {
    const o = objeto(item);
    const id = texto(o?.id);
    const proprio = id ? [{ id, rotulo: texto(o?.rotulo) ?? id }] : [];
    // Empate explícito: o motor manda `empate` com todos os membros à mesma menor distância (o primeiro incluído).
    const empates = [...lista(o?.empate), ...lista(o?.empates)].map(e => objeto(e)).filter(Boolean)
      .map(e => ({ id: texto(e!.id) ?? "", rotulo: texto(e!.rotulo) ?? texto(e!.id) ?? "" })).filter(e => e.id);
    return [...proprio, ...empates];
  });
  const unicos = saida.filter((item, indice) => saida.findIndex(outro => outro.id === item.id) === indice);
  return unicos.length ? unicos : null;
}

function itemDe(bruto: unknown): PainelItem | null {
  const o = objeto(bruto);
  const id = texto(o?.id);
  if (!o || !id) return null;
  const tipo = o.tipo === "conjunto" || o.tipo === "estado" || o.tipo === "brasil" ? o.tipo : "municipio";
  const avaliavel = objeto(o.avaliavel);
  const ordem = objeto(o.ordem);
  return {
    id, tipo, rotulo: texto(o.rotulo) ?? id, uf: texto(o.uf),
    membros: Array.isArray(o.membros) ? o.membros.filter((m): m is string => typeof m === "string") : undefined,
    populacao: num(o.populacao), quantidade: num(o.quantidade), densidade: num(o.densidade),
    contagem: texto(o.contagem) ?? undefined,
    distancia_km: num(o.distancia_km), distancia_km_max: num(o.distancia_km_max),
    inicial: valores3(o.inicial), variacao_percentual: valores3(o.variacao_percentual),
    avaliavel: { densidade: avaliavel?.densidade !== false, distancia: typeof avaliavel?.distancia === "boolean" ? avaliavel.distancia : null,
      variacao: typeof avaliavel?.variacao === "boolean" ? avaliavel.variacao : null },
    motivos: lista(o.motivos).filter((m): m is string => typeof m === "string"),
    referencia: o.referencia === true,
    tendencia: tendenciaDe(o.tendencia), grupo: posicao(o.grupo), grupoMapa: posicao(o.grupo_mapa), faixa: faixaDe(o.faixa), faixa_distancia: faixaDe(o.faixa_distancia),
    referenciaDoItem: referenciaProximaDe(o.referencia_do_item ?? o.referencia_mais_proxima), condicoes: condicoesDe(o.condicoes),
    ordem: ordem ? { posicao: num(ordem.posicao) } : null, rotatividade: rotatividadeDe(o.rotatividade), serie: serieDe(o.serie),
  };
}

const RELACOES = new Set<string>(["mais_proxima", "mais_distante"]);
const DELIMITACOES = new Set<string>(["todos", "mesmo_grupo", "grupos", "mesma_regiao", "regioes"]);
/** A referência da resposta, com a definição por elegibilidade quando ela vem (24/10/2026). */
function referenciaRespostaDe(bruto: unknown): PainelReferenciaResposta | null {
  const referencia = objeto(bruto);
  if (!referencia) return null;
  const membros = lista(referencia.membros).map(m => objeto(m)).filter(Boolean).map(m => ({ id: texto(m!.id) ?? "", rotulo: texto(m!.rotulo) ?? "" }));
  const origem = texto(referencia.origem) ?? "";
  if (referencia.tipo !== "elegiveis") return { tipo: referencia.tipo === "conjunto" ? "conjunto" : "municipio", membros, origem };
  const delimitacao = objeto(referencia.delimitacao), condicao = objeto(referencia.condicao), elegiveis = objeto(referencia.elegiveis);
  const relacao = texto(referencia.relacao);
  const tipo = texto(delimitacao?.tipo);
  const atributo = texto(condicao?.atributo), operador = texto(condicao?.operador);
  return { tipo: "elegiveis", membros, origem,
    relacao: relacao && RELACOES.has(relacao) ? relacao as RelacaoEspacial : undefined,
    delimitacao: tipo && DELIMITACOES.has(tipo) ? { tipo: tipo as TipoDelimitacao,
      valores: lista(delimitacao?.valores).filter((v): v is string => typeof v === "string"), texto: texto(delimitacao?.texto) ?? "" } : undefined,
    condicao: atributo && operador ? { atributo: atributo as PainelAtributo, operador: operador as OperadorCondicao,
      valor: texto(condicao?.valor) ?? String(num(condicao?.valor) ?? ""), texto: texto(condicao?.texto) ?? "" } : undefined,
    elegiveis: elegiveis ? { universo: num(elegiveis.universo) ?? 0, atende: num(elegiveis.atende) ?? 0,
      naoAtende: num(elegiveis.nao_atende) ?? 0, naoAvaliaveis: num(elegiveis.nao_avaliaveis) ?? 0 } : undefined };
}

/** A série temporal do topo (`serie`): as competências do intervalo; sem elas, nada. */
function serieTopoDe(bruto: unknown): SerieTopo | null {
  const o = objeto(bruto);
  if (!o) return null;
  const janela = objeto(o.janela);
  const competencias = lista(janela?.competencias ?? o.competencias).filter((c): c is string => typeof c === "string");
  if (!competencias.length) return null;
  return { competencias, inicio: texto(janela?.inicio) ?? competencias[0], fim: texto(janela?.fim) ?? competencias[competencias.length - 1],
    unidadeValor: texto(o.unidade_valor) };
}

/** Contagens como lista alinhada aos índices 1..k: aceita lista, objeto {"1": n} ou {"Q1": n} e lista de {indice, contagem}. */
function contagensPorIndice(bruto: unknown, total: number): number[] {
  if (Array.isArray(bruto)) {
    if (bruto.every(item => typeof item === "number")) return bruto as number[];
    const saida: number[] = Array(total).fill(0);
    for (const item of bruto) {
      const o = objeto(item);
      const indice = num(o?.indice), contagem = num(o?.contagem) ?? num(o?.unidades);
      if (indice !== null && contagem !== null && indice >= 1) saida[indice - 1] = contagem;
    }
    return saida;
  }
  const o = objeto(bruto);
  if (!o) return [];
  const saida: number[] = Array(total).fill(0);
  for (const [chave, valor] of Object.entries(o)) {
    const indice = Number((/(\d+)$/.exec(chave) || [])[1]);
    if (indice >= 1 && typeof valor === "number") saida[indice - 1] = valor;
  }
  return saida;
}

/** Número do motor: número ou texto decimal com ponto ("100.5"), sem arredondar. */
const decimal = (valor: unknown): number | null =>
  typeof valor === "string" && /^-?\d+(?:\.\d+)?$/.test(valor.trim()) ? Number(valor) : num(valor);

function faixasTopoDe(bruto: unknown, limites: number[]): FaixasTopo | null {
  const o = objeto(bruto);
  if (!o) return null;
  const rotulos = lista(o.rotulos).filter((r): r is string => typeof r === "string");
  const doMotor = lista(o.limites).map(decimal).filter((l): l is number => l !== null);
  return { limites: doMotor.length ? doMotor : limites,
    rotulos, contagens: contagensPorIndice(o.contagens, rotulos.length), fora: num(o.fora), naoAvaliaveis: num(o.nao_avaliaveis) };
}

function comparacaoDe(bruto: unknown): ComparacaoTopo | null {
  const o = objeto(bruto);
  if (!o) return null;
  const itens = lista(o.itens).map(item => typeof item === "string" ? item : texto(objeto(item)?.id)).filter((i): i is string => !!i);
  const comparados = new Map<string, ValorComparado>();
  for (const item of lista(o.itens)) {
    const c = objeto(item);
    const id = texto(c?.id);
    if (id) comparados.set(id, { id, rotulo: texto(c?.rotulo) ?? id, valor: num(c?.valor) });
  }
  const valorComparado = (v: unknown): ValorComparado[] => {
    const lista2 = Array.isArray(v) ? v : v ? [v] : [];
    return lista2.map(item => {
      if (typeof item === "string") return comparados.get(item) ?? { id: item, rotulo: item, valor: null };
      const c = objeto(item);
      const id = texto(c?.id);
      return id ? { id, rotulo: texto(c?.rotulo) ?? id, valor: num(c?.valor) } : null;
    }).filter((item): item is ValorComparado => !!item);
  };
  const atributoDoTopo = texto(o.indicador) ?? "";
  const linhas = new Map<string, LinhaComparacao>();
  const linha = (atributo: string) => {
    if (!linhas.has(atributo)) linhas.set(atributo, { atributo, maior: [], menor: [], diferencas: [] });
    return linhas.get(atributo)!;
  };
  // maior/menor: um objeto {id, rotulo, valor, atributo}, uma lista deles ou um objeto por atributo.
  for (const chave of ["maior", "menor"] as const) {
    const bruta = o[chave];
    const porAtributo = objeto(bruta);
    if (porAtributo && !("id" in porAtributo)) {
      for (const [atributo, valor] of Object.entries(porAtributo)) linha(atributo)[chave].push(...valorComparado(valor));
    } else {
      for (const item of Array.isArray(bruta) ? bruta : bruta ? [bruta] : []) {
        const c = objeto(item);
        linha(texto(c?.atributo) ?? texto(c?.indicador) ?? atributoDoTopo)[chave].push(...valorComparado(item));
      }
    }
  }
  const diferenca = (item: unknown, atributoPadrao: string) => {
    const d = objeto(item);
    if (!d) return;
    const entre = lista(d.entre).filter((e): e is string => typeof e === "string");
    const de = texto(d.de) ?? texto(d.a), para = texto(d.para) ?? texto(d.b);
    linha(texto(d.atributo) ?? texto(d.indicador) ?? atributoPadrao).diferencas.push({
      entre: entre.length ? entre : [de, para].filter((e): e is string => !!e),
      valor: num(d.valor) ?? num(d.diferenca) ?? num(d.absoluta), texto: texto(d.texto) });
  };
  const difs = o.diferencas;
  const porAtributo = objeto(difs);
  if (porAtributo) for (const [atributo, valor] of Object.entries(porAtributo)) for (const item of lista(valor)) diferenca(item, atributo);
  else for (const item of lista(difs)) diferenca(item, atributoDoTopo);
  const textos = [...lista(o.textos), ...lista(o.notas), texto(o.texto)].filter((t): t is string => typeof t === "string" && !!t);
  return { itens, linhas: [...linhas.values()], textos };
}

function rotuloDe(bruto: unknown): Rotulo | null {
  const o = objeto(bruto);
  const singular = texto(o?.singular), plural = texto(o?.plural);
  if (!singular || !plural) return null;
  const genero = o?.genero === "f" || o?.genero === "m" ? o.genero : undefined;
  return genero ? { singular, plural, genero } : { singular, plural };
}
export function rotulosDe(bruto: unknown): RotulosTerritoriais | null {
  const o = objeto(bruto);
  const unidade = rotuloDe(o?.unidade);
  return unidade ? { unidade, grupo: rotuloDe(o?.grupo) } : null;
}

/** Frase-resumo do motor: `{texto}` (ou o texto direto); vazia ou ausente vira null (a resposta de antes continua legível). */
export function resumoDe(bruto: unknown): { texto: string } | null {
  const frase = typeof bruto === "string" ? texto(bruto) : texto(objeto(bruto)?.texto);
  return frase ? { texto: frase } : null;
}

/** Resposta do motor nos tipos da tela. Campos ausentes viram null (o motor de antes, sem as extensões, continua legível). */
/** Grupos por posição do topo (`grupos` ou `grupos_mapa`): tipo, cortes, contagens por índice e rótulos (do topo ou, sem eles,
 * os dos itens). */
function gruposTopoDe(bruto: unknown, posicoes: (Posicao | null)[]): GruposTopo | null {
  const grupos = objeto(bruto);
  if (!grupos) return null;
  const contagens = contagensPorIndice(grupos.contagens, ({ quartis: 4, quintis: 5, decis: 10 } as Record<string, number>)[String(grupos.tipo)] ?? 0);
  const dosItens: string[] = [];
  for (const posicaoDoItem of posicoes) if (posicaoDoItem && !dosItens[posicaoDoItem.indice - 1]) dosItens[posicaoDoItem.indice - 1] = posicaoDoItem.rotulo;
  const doTopo = lista(grupos.rotulos).filter((r): r is string => typeof r === "string");
  return { tipo: texto(grupos.tipo) ?? "", cortes: lista(grupos.cortes).filter((c): c is number => typeof c === "number"), contagens,
    rotulos: doTopo.length ? doTopo : dosItens };
}

export function normalizarResposta(bruto: unknown, nivelPedido: PainelNivel = "municipios"): PainelResposta {
  const o = objeto(bruto);
  if (!o || !Array.isArray(o.itens)) throw new ErroDoMotor("A resposta do cálculo não segue o contrato (itens ausentes).", 200, null);
  const itens = o.itens.map(itemDe).filter((item): item is PainelItem => !!item);
  const tendencia = objeto(o.tendencia);
  const janelaBruta = tendencia ? (Array.isArray(tendencia.janela) ? tendencia.janela : lista(objeto(tendencia.janela)?.competencias)
    .concat(lista(objeto(tendencia.janela)?.periodos))) : [];
  const condicoes = objeto(o.condicoes);
  // O texto de cada condição de um item vem da definição do topo, na mesma ordem.
  const definicaoDasCondicoes = lista(condicoes?.definicao).map(t => texto(objeto(t)?.texto) ?? "");
  for (const item of itens) item.condicoes?.porCondicao.forEach((c, i) => { if (!c.texto) c.texto = definicaoDasCondicoes[i] ?? ""; });
  const ordenacao = objeto(o.ordenacao);
  const contexto = objeto(objeto(o.contexto)?.brasil);
  const disponibilidade: Disponibilidade = {};
  for (const [chave, valor] of Object.entries(objeto(o.disponibilidade) || {})) {
    const d = objeto(valor);
    if (d && typeof d.disponivel === "boolean") disponibilidade[chave as ChaveDisponibilidade] = { disponivel: d.disponivel, motivo: texto(d.motivo) ?? "" };
  }
  const sessao = objeto(o.sessao);
  const dominios: PainelResposta["dominios"] = {};
  for (const [chave, valor] of Object.entries(objeto(o.dominios) || {}))
    dominios[chave] = Array.isArray(valor) && valor.length === 2 && valor.every(v => typeof v === "number" && Number.isFinite(v))
      ? [valor[0] as number, valor[1] as number] : null;
  return {
    competencia: texto(o.competencia) ?? "", competencia_inicial: texto(o.competencia_inicial), categoria: texto(o.categoria) ?? "",
    versao_base: texto(o.versao_base), chave_execucao: texto(o.chave_execucao) ?? "",
    nivel: o.nivel === "estados" || o.nivel === "municipios" || o.nivel === "brasil" ? o.nivel
      : itens.some(item => item.tipo === "estado") ? "estados" : nivelPedido,
    referencia: referenciaRespostaDe(o.referencia),
    itens, dominios,
    notas: lista(o.notas).filter((n): n is string => typeof n === "string"),
    limitacoes: lista(o.limitacoes).filter((n): n is string => typeof n === "string"),
    tendencia: tendencia ? { janela: janelaBruta.filter((c): c is string => typeof c === "string"),
      contagens: Object.fromEntries(Object.entries(objeto(tendencia.contagens) || {}).filter(([, v]) => typeof v === "number")) as Contagens,
      familias: Object.fromEntries(Object.entries(objeto(tendencia.familias) || {}).filter(([, v]) => typeof v === "number")) as Contagens,
      naoAvaliaveis: num(tendencia.nao_avaliaveis), bloqueio: texto(tendencia.bloqueio) ?? texto(objeto(tendencia.bloqueio)?.texto),
      unidadeTempo: texto(tendencia.unidade_tempo),
      semClassificacaoPorMotivo: Object.fromEntries(Object.entries(objeto(tendencia.sem_classificacao_por_motivo) || {})
        .filter(([, v]) => typeof v === "number")) as Contagens } : null,
    serie: serieTopoDe(o.serie),
    grupos: gruposTopoDe(o.grupos, itens.map(item => item.grupo)),
    gruposMapa: gruposTopoDe(o.grupos_mapa, itens.map(item => item.grupoMapa)),
    faixas: faixasTopoDe(o.faixas, []),
    faixasDistancia: faixasTopoDe(o.faixas_distancia, []),
    condicoes: condicoes ? { contagens: Object.fromEntries(SITUACOES.map(s => [s, num(objeto(condicoes.contagens)?.[s])])
      .filter(([, v]) => v !== null)) as Partial<Record<SituacaoCondicao, number>>,
      textos: lista(condicoes.textos ?? condicoes.condicoes ?? condicoes.definicao).map(t => typeof t === "string" ? t
        : texto(objeto(t)?.texto) ?? texto(objeto(t)?.condicao)).filter((t): t is string => !!t) } : null,
    ordenacao: ordenacao ? { atributo: texto(ordenacao.atributo) ?? "", ordem: texto(ordenacao.ordem) ?? "", primeiros: num(ordenacao.primeiros),
      empatesNoCorte: typeof ordenacao.empates_no_corte === "boolean" ? ordenacao.empates_no_corte
        : Array.isArray(ordenacao.empates_no_corte) ? ordenacao.empates_no_corte.length > 0 : num(ordenacao.empates_no_corte) !== null
          ? (num(ordenacao.empates_no_corte) as number) > 0 : null,
      texto: texto(ordenacao.texto) } : null,
    comparacao: comparacaoDe(o.comparacao),
    contextoBrasil: contexto ? { densidade: num(contexto.densidade), quantidade: num(contexto.quantidade), populacao: num(contexto.populacao),
      competencia: texto(contexto.competencia) } : null,
    disponibilidade,
    sessao: sessao ? { registrado: sessao.registrado === true, resultId: texto(sessao.result_id) } : null,
    rotulos: rotulosDe(o.rotulos),
    indicador: o.indicador === "densidade" || o.indicador === "quantidade" ? o.indicador : null,
    resumo: resumoDe(o.resumo),
  };
}

/** Resposta de /api/painel/mapa nos tipos da tela (DadosDoMapa do contrato): `pontos` [{id, lat, lon}] vira um Map id →
 * [latitude, longitude]; ponto sem id ou com coordenada que não é número finito no intervalo fica de fora. `sem_coordenada`
 * traz as unidades sem coordenada válida, com o motivo do motor (vão para Não avaliáveis). Nada é calculado: o mapa só desenha. */
export function normalizarMapa(bruto: unknown): DadosDoMapa {
  const o = objeto(bruto);
  if (!o || !Array.isArray(o.pontos)) throw new ErroDoMotor("A resposta do mapa não segue o contrato (pontos ausentes).", 200, null);
  const pontos = new Map<string, [number, number]>();
  for (const item of o.pontos) {
    const p = objeto(item);
    const id = texto(p?.id), lat = num(p?.lat) ?? num(p?.latitude), lon = num(p?.lon) ?? num(p?.longitude);
    if (id && lat !== null && lon !== null && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) pontos.set(id, [lat, lon]);
  }
  const semCoordenada = lista(o.sem_coordenada).map(item => {
    const s = objeto(item);
    const id = texto(s?.id);
    return id ? { id, rotulo: texto(s?.rotulo) ?? id, motivo: texto(s?.motivo) ?? "" } : null;
  }).filter((item): item is { id: string; rotulo: string; motivo: string } => !!item);
  return { competencia: texto(o.competencia) ?? "", referencial: texto(o.referencial) ?? "", pontos, semCoordenada };
}

// ------------------------------------------------------------------------------------------------ chamadas
export async function pedirPainel(fonte: FonteDoMotor, opcoes: PainelOpcoes, signal?: AbortSignal): Promise<PainelResposta> {
  const response = await fetch(fonte.apiBase + "/api/painel", { method: "POST", body: formulario(fonte, opcoes, !!opcoes.referencia), signal });
  return normalizarResposta(await lerResposta(response), opcoes.nivel ?? "municipios");
}

/** Coordenadas autorizadas das unidades na competência (o mesmo formulário de /api/painel, com a versão geográfica): pedidas
 * só quando o mapa aparece ou o gráfico mostra unidades com o mapa disponível. */
export async function pedirMapa(fonte: FonteDoMotor, opcoes: MapaOpcoes, signal?: AbortSignal): Promise<DadosDoMapa> {
  const response = await fetch(fonte.apiBase + "/api/painel/mapa", { method: "POST", body: formulario(fonte, opcoes, true), signal });
  return normalizarMapa(await lerResposta(response));
}

