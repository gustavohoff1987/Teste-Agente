// Cliente do motor da área de análise da página única (POST /api/painel e POST /api/painel/referencias), no contrato de
// 22/10/2026 (seção 3 do contrato entre as frentes; Docs/PAINEL_INTEGRADO.md). É o ÚNICO lugar com os nomes de campos do
// motor: o formulário, as opções (montadas em painelModel.montarOpcoes com os tipos daqui), a leitura dos erros (422, com a
// pendência de premissa) e a normalização da resposta para os tipos da tela. Se o motor mudar um nome, ajuste só este
// arquivo. Todo número vem do motor; a tela só posiciona, filtra (estado visual) e desenha. Nada calcula aqui.
import { contextRevision, sessionFetch as fetch } from "./conversationSession";

// ------------------------------------------------------------------------------------------------ pedido
export type PainelIndicador = "densidade" | "quantidade";
export type PainelAtributo = "densidade" | "quantidade" | "populacao";
export type AtributoOrdenacao = PainelAtributo | "distancia_km" | "variacao";
export type AtributoCondicao = PainelAtributo | "distancia_km";
export type PainelOrdem = "desc" | "asc";
export type PainelNivel = "estados" | "municipios";
/** Universo das unidades, na forma de `options.abrangencia.municipios`. Em planilhas, `estados` leva os valores do grupo
 * (coluna-mãe) e `ids` leva `code:<código>` ou `name:<nome>`. */
export type PainelMunicipios = { todos: boolean; estados: string[]; ids: string[] };
export type PainelUniverso = { municipios: PainelMunicipios };
export type PainelCriterio = { atributo: PainelAtributo; ordem: PainelOrdem };
/** Conjunto agregado (CAP-AGR-01): id com letras, números, _ ou - (até 64), rótulo de até 120 caracteres, dois ou mais membros. */
export type PainelConjuntoPedido = { id: string; rotulo: string; membros: string[] };
/** Um membro: referência município; dois ou mais: conjunto de referência (distância até o membro mais próximo). O critério só
 * registra a origem (CAP-REF-01); com o universo da lista, a origem cita a posição exata vista pela pessoa. */
export type PainelReferenciaPedido = { membros: string[]; criterio?: PainelCriterio & { universo?: PainelUniverso } };
export type OperadorCondicao = "<" | "<=" | ">" | ">=";
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
  conjuntos?: PainelConjuntoPedido[];
  referencia?: PainelReferenciaPedido;
  faixas_distancia?: number[];
  competencia_inicial?: string;
  tendencia?: { competencias: string[] };
  grupos?: { tipo: TipoGrupos };
  faixas?: number[];
  condicoes?: CondicaoPedido[];
  ordenar?: OrdenarPedido;
  comparar?: string[];
  rotatividade?: { inicial: string; final: string };
  premissas?: Record<string, string>;
};

/** Opções de /api/painel/referencias (o critério aqui não leva universo). */
export type ReferenciasOpcoes = { competencia: string; categoria: string; universo: PainelUniverso; criterio: PainelCriterio;
  premissas?: Record<string, string> };

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
  observacoes: { competencia: string; valor: number | null }[];
  /** Velocidade entre duas observações vizinhas, na unidade do indicador por unidade de tempo (mês nas competências AAAAMM). */
  velocidades: { de: string; ate: string; valor: number }[];
};
export type SituacaoCondicao = "ATENDE" | "NAO_ATENDE" | "NAO_AVALIAVEL";
export type CondicoesItem = { situacao: SituacaoCondicao; porCondicao: { texto: string; situacao: SituacaoCondicao | null }[];
  motivo: string | null };
/** Rotatividade (CAP-ROT-01): contagens e percentuais do motor, sempre da coorte inicial. A tela não divide nada. */
export type RotatividadeItem = { coorteInicial: number | null; permaneceram: number | null; sairam: number | null;
  permanencia: number | null; saida: number | null; avaliavel: boolean; motivo: string | null };

export type PainelItem = {
  id: string;
  tipo: "municipio" | "estado" | "conjunto";
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
  faixa: Posicao | "fora" | null;
  faixa_distancia: Posicao | "fora" | null;
  /** Membro da referência mais próximo; mais de um quando há empate (explícito). */
  referencia_mais_proxima: { id: string; rotulo: string }[] | null;
  condicoes: CondicoesItem | null;
  ordem: { posicao: number | null } | null;
  rotatividade: RotatividadeItem | null;
};
export type PainelReferenciaResposta = { tipo: "municipio" | "conjunto"; membros: { id: string; rotulo: string }[]; origem: string };
export type Contagens = Record<string, number>;
export type TendenciaTopo = { janela: string[]; contagens: Contagens; familias: Contagens; naoAvaliaveis: number | null;
  bloqueio: string | null; unidadeTempo: string | null };
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
  grupos: GruposTopo | null;
  faixas: FaixasTopo | null;
  faixasDistancia: FaixasTopo | null;
  condicoes: CondicoesTopo | null;
  ordenacao: OrdenacaoTopo | null;
  comparacao: ComparacaoTopo | null;
  contextoBrasil: ContextoBrasil | null;
  disponibilidade: Disponibilidade;
  sessao: { registrado: boolean; resultId: string | null } | null;
  rotulos: RotulosTerritoriais | null;
};

export type ReferenciaCandidato = { id: string; rotulo: string; uf: string | null; valor: number | null; posicao: number | null };
export type ReferenciaNaoAvaliavel = { id: string; rotulo: string; uf: string | null; motivos: string[] };
export type ReferenciasResposta = { criterio: PainelCriterio; competencia: string; categoria: string;
  candidatos: ReferenciaCandidato[]; nao_avaliaveis: ReferenciaNaoAvaliavel[] };

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
    familia: avaliavel ? familia : null, avaliavel, observacoes, velocidades };
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
  const tipo = o.tipo === "conjunto" || o.tipo === "estado" ? o.tipo : "municipio";
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
    tendencia: tendenciaDe(o.tendencia), grupo: posicao(o.grupo), faixa: faixaDe(o.faixa), faixa_distancia: faixaDe(o.faixa_distancia),
    referencia_mais_proxima: referenciaProximaDe(o.referencia_mais_proxima), condicoes: condicoesDe(o.condicoes),
    ordem: ordem ? { posicao: num(ordem.posicao) } : null, rotatividade: rotatividadeDe(o.rotatividade),
  };
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

/** Resposta do motor nos tipos da tela. Campos ausentes viram null (o motor de antes, sem as extensões, continua legível). */
export function normalizarResposta(bruto: unknown, nivelPedido: PainelNivel = "municipios"): PainelResposta {
  const o = objeto(bruto);
  if (!o || !Array.isArray(o.itens)) throw new ErroDoMotor("A resposta do motor não segue o contrato (itens ausentes).", 200, null);
  const itens = o.itens.map(itemDe).filter((item): item is PainelItem => !!item);
  const referencia = objeto(o.referencia);
  const tendencia = objeto(o.tendencia);
  const janelaBruta = tendencia ? (Array.isArray(tendencia.janela) ? tendencia.janela : lista(objeto(tendencia.janela)?.competencias)
    .concat(lista(objeto(tendencia.janela)?.periodos))) : [];
  const grupos = objeto(o.grupos);
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
  const contagensGrupo = grupos ? contagensPorIndice(grupos.contagens, ({ quartis: 4, quintis: 5, decis: 10 } as Record<string, number>)[String(grupos.tipo)] ?? 0) : [];
  const rotulosGrupos: string[] = [];
  for (const item of itens) if (item.grupo && !rotulosGrupos[item.grupo.indice - 1]) rotulosGrupos[item.grupo.indice - 1] = item.grupo.rotulo;
  const dominios: PainelResposta["dominios"] = {};
  for (const [chave, valor] of Object.entries(objeto(o.dominios) || {}))
    dominios[chave] = Array.isArray(valor) && valor.length === 2 && valor.every(v => typeof v === "number" && Number.isFinite(v))
      ? [valor[0] as number, valor[1] as number] : null;
  return {
    competencia: texto(o.competencia) ?? "", competencia_inicial: texto(o.competencia_inicial), categoria: texto(o.categoria) ?? "",
    versao_base: texto(o.versao_base), chave_execucao: texto(o.chave_execucao) ?? "",
    nivel: o.nivel === "estados" || o.nivel === "municipios" ? o.nivel : itens.some(item => item.tipo === "estado") ? "estados" : nivelPedido,
    referencia: referencia ? { tipo: referencia.tipo === "conjunto" ? "conjunto" : "municipio",
      membros: lista(referencia.membros).map(m => objeto(m)).filter(Boolean).map(m => ({ id: texto(m!.id) ?? "", rotulo: texto(m!.rotulo) ?? "" })),
      origem: texto(referencia.origem) ?? "" } : null,
    itens, dominios,
    notas: lista(o.notas).filter((n): n is string => typeof n === "string"),
    limitacoes: lista(o.limitacoes).filter((n): n is string => typeof n === "string"),
    tendencia: tendencia ? { janela: janelaBruta.filter((c): c is string => typeof c === "string"),
      contagens: Object.fromEntries(Object.entries(objeto(tendencia.contagens) || {}).filter(([, v]) => typeof v === "number")) as Contagens,
      familias: Object.fromEntries(Object.entries(objeto(tendencia.familias) || {}).filter(([, v]) => typeof v === "number")) as Contagens,
      naoAvaliaveis: num(tendencia.nao_avaliaveis), bloqueio: texto(tendencia.bloqueio) ?? texto(objeto(tendencia.bloqueio)?.texto),
      unidadeTempo: texto(tendencia.unidade_tempo) } : null,
    grupos: grupos ? { tipo: texto(grupos.tipo) ?? "", cortes: lista(grupos.cortes).filter((c): c is number => typeof c === "number"),
      contagens: contagensGrupo, rotulos: lista(grupos.rotulos).filter((r): r is string => typeof r === "string").length
        ? lista(grupos.rotulos).filter((r): r is string => typeof r === "string") : rotulosGrupos } : null,
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
  };
}

// ------------------------------------------------------------------------------------------------ chamadas
export async function pedirPainel(fonte: FonteDoMotor, opcoes: PainelOpcoes, signal?: AbortSignal): Promise<PainelResposta> {
  const response = await fetch(fonte.apiBase + "/api/painel", { method: "POST", body: formulario(fonte, opcoes, !!opcoes.referencia), signal });
  return normalizarResposta(await lerResposta(response), opcoes.nivel ?? "municipios");
}

export async function pedirReferencias(fonte: FonteDoMotor, opcoes: ReferenciasOpcoes, signal?: AbortSignal): Promise<ReferenciasResposta> {
  const response = await fetch(fonte.apiBase + "/api/painel/referencias", { method: "POST", body: formulario(fonte, opcoes, false), signal });
  const body = objeto(await lerResposta(response));
  if (!body || !Array.isArray(body.candidatos)) throw new ErroDoMotor("A resposta das referências não segue o contrato (candidatos ausentes).", 200, null);
  return body as unknown as ReferenciasResposta;
}
