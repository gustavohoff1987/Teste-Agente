// Cliente do motor da área de análise da página única (POST /api/painel e, desde 23/10/2026, POST /api/painel/mapa; a rota
// POST /api/painel/referencias continua no motor, mas a tela não a usa desde 24/10/2026), no contrato de 22/10/2026 (seção 3
// do contrato entre as frentes; Docs/PAINEL_INTEGRADO.md). É o
// ÚNICO lugar com os nomes de campos do motor: o formulário, as opções (montadas em painelModel.montarOpcoes com os tipos
// daqui), a leitura dos erros (422, com a pendência de premissa) e a normalização da resposta para os tipos da tela. Se o
// motor mudar um nome, ajuste só este arquivo. Todo número vem do motor; a tela só posiciona, filtra (estado visual) e
// desenha. Nada calcula aqui.
import { contextRevision, sessionFetch as fetch } from "./conversationSession";
import type { DadosDoMapa } from "./mapaContrato";
import type { ConsultaTerritorios } from "./painelModel";

// ------------------------------------------------------------------------------------------------ pedido
export type PainelIndicador = "densidade" | "quantidade";
export type PainelAtributo = "densidade" | "quantidade" | "populacao";
export type AtributoOrdenacao = PainelAtributo | "distancia_km" | "variacao";
export type AtributoCondicao = PainelAtributo | "distancia_km";
export type PainelOrdem = "desc" | "asc";
/** Nível do gráfico: os municípios (ou as unidades da planilha), os estados (ou os grupos da coluna-mãe da planilha) ou, desde
 * 24/10/2026, o Brasil inteiro como uma unidade (só na base do Brasil). Desde 07/11/2026 (item 1 do comando de 06/11/2026, até
 * dois níveis de grupo), "regioes": o nível de grupo de cima de uma planilha (a região acima do distrito), com os valores pelas
 * unidades de cada um. */
export type PainelNivel = "estados" | "municipios" | "brasil" | "regioes";
/** Premissas de uma planilha, com os nomes de /api/analyze: textos e, em `confirmed_roles`, os papéis escolhidos pela pessoa. */
export type Premissas = Record<string, string | string[]>;
/** Universo das unidades, na forma de `options.abrangencia.municipios`. Em planilhas, `estados` leva os valores do grupo
 * (coluna-mãe) e `ids` leva `code:<código>` ou `name:<nome>`. */
export type PainelMunicipios = { todos: boolean; estados: string[]; ids: string[] };
export type PainelUniverso = { municipios: PainelMunicipios };
export type PainelCriterio = { atributo: PainelAtributo; ordem: PainelOrdem };
/** Conjunto agregado (CAP-AGR-01): id com letras, números, _ ou - (até 64), rótulo de até 120 caracteres, dois ou mais membros. */
/** Um conjunto (o grupo de Agregar territórios, 06/11/2026). `substitui`, só da tela (não vai ao motor): o grupo ficou no lugar dos
 * membros, que saíram da seleção; desfazê-lo os devolve. */
/** Um conjunto (CAP-AGR-01). `substitui` e `retirados` são da tela e não vão ao motor (montarOpcoes): o grupo fica no lugar dos
 * membros, e `retirados` são os membros que estavam na seleção e saíram dela (os únicos que voltam ao desfazer o grupo). */
export type PainelConjuntoPedido = { id: string; rotulo: string; membros: string[]; substitui?: boolean; retirados?: string[] };
/** Um membro: referência município; dois ou mais: conjunto de referência (distância até o membro mais próximo). O critério só
 * registra a origem (CAP-REF-01); com o universo da lista, a origem cita a posição exata vista pela pessoa. É a forma que a
 * conversa usa ("use Manaus como referência"). */
export type ReferenciaPorMembros = { membros: string[]; criterio?: PainelCriterio & { universo?: PainelUniverso } };
export type OperadorCondicao = "<" | "<=" | ">" | ">=";
/** A referência pelos membros (contrato de 21/10). Na página única, a Análise Espacial manda a Escolha dos territórios
 * (`consulta`, 27/10/2026), e a referência pelo nome pedida na conversa vira os marcados da Referência. */
export type PainelReferenciaPedido = ReferenciaPorMembros;
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
  /** A Escolha dos territórios (27/10/2026): com ela, `base` é a seleção prévia, e os itens são os da base da consulta. */
  consulta?: ConsultaTerritorios;
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
 * Brasil, o motor recusa os dois). `grupos` (06/11/2026, só na base do Brasil): também o ponto de desenho de cada estado. */
export type MapaOpcoes = { competencia: string; categoria: string; premissas?: Premissas; rotulos?: RotulosTerritoriais; grupos?: boolean };

// ------------------------------------------------------------------------------------------------ resposta (normalizada)
/** Nomenclatura territorial: na base do Brasil, município e estado; nas planilhas, o que a pessoa confirmou ("distrito",
 * "província"…). `genero` é opcional; sem ele, a tela deduz pela terminação (concordância simples). */
export type Rotulo = { singular: string; plural: string; genero?: "m" | "f" };
/** O artigo que o nome do todo pede: "o Brasil", "a Solária", Portugal sem artigo ("de Portugal"). */
export type ArtigoDoTodo = "" | "o" | "a" | "os" | "as";
/** O nome do todo de uma planilha (07/11/2026, item 1 do comando de 06/11/2026, os nomes da base): o nome próprio que a pessoa
 * dá no painel Colunas e o artigo; sem ele, a tela diz "Toda a base". Na base do Brasil, o todo é o Brasil. */
export type TodoDaBase = { nome: string; artigo: ArtigoDoTodo };
/** `grupo_superior` (07/11/2026): o nível de grupo de cima de uma planilha com dois níveis (a região acima do distrito). */
export type RotulosTerritoriais = { unidade: Rotulo; grupo: Rotulo | null; todo?: TodoDaBase | null; grupo_superior?: Rotulo | null };

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
  /** O grupo da unidade, como o motor devolve (`grupo_territorial`): na base do Brasil, o prefixo da UF; numa planilha, o valor da
   * coluna-mãe ("Alto Vésper"). Vai na coluna do grupo do CSV (28/10/2026). */
  grupoTerritorial?: string | null;
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
  /** A referência do item: com membros escolhidos, o membro da referência mais próximo (`referencia_mais_proxima` do motor); com a
   * Escolha dos territórios, a referência mais próxima do item (`referencia_do_item`). Mais de um quando há empate (explícito). */
  referenciaDoItem: { id: string; rotulo: string }[] | null;
  condicoes: CondicoesItem | null;
  ordem: { posicao: number | null } | null;
  rotatividade: RotatividadeItem | null;
  serie: SerieItem | null;
};
/** Uma referência. Com a Escolha dos territórios, o motor manda também a UF e os valores dela na competência, para
 * a tela mostrar a referência de cada território da base; pelos membros escolhidos, os valores vêm no item (distância zero). */
export type MembroDaReferencia = { id: string; rotulo: string; uf?: string | null; populacao?: number | null; quantidade?: number | null;
  densidade?: number | null };
/** Quantos restam em cada etapa de um lado da consulta (do motor): de onde parte, depois dos filtros, no fim (null enquanto a
 * etapa está incompleta) e quantos ficaram de fora por um filtro não avaliável. */
export type ContagensDoLado = { partirDe: number | null; filtros: number | null; final: number | null; naoAvaliaveis: number | null };
/** A referência da resposta: um município ou um conjunto escolhidos (membros) ou, com a Escolha dos territórios, a consulta
 * calculada, a base e a referência em palavras (do motor), as contagens e os territórios que ficaram como referência mais próxima
 * de algum item. */
export type PainelReferenciaResposta = { tipo: "municipio" | "conjunto" | "consulta"; membros: MembroDaReferencia[]; origem: string;
  consulta?: ConsultaTerritorios | null; texto?: string; baseTexto?: string;
  contagens?: { base: ContagensDoLado; referencia: ContagensDoLado } };
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
export type ChaveDisponibilidade = "espacial" | "tendencia" | "rotatividade" | "estados" | "grupos" | "regioes";
export type Disponibilidade = Partial<Record<ChaveDisponibilidade, { disponivel: boolean; motivo: string }>>;
/** Total individualizado de um estado inteiro (fonte estadual, UF-CONTAGEM-ESTADUAL-1), na competência da análise. */
export type TotalDoEstado = { id: string; rotulo: string; competencia: string | null; quantidade: number | null; populacao: number | null;
  densidade: number | null; avaliabilidade: string; motivo: string | null };
export type AbrangenciaCompleta = { brasil: boolean; estados: TotalDoEstado[] };
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
  /** Contagens individualizadas da abrangência completa (05/11/2026; `contexto.brasil_completo` e `contexto.estados`): com o Brasil
   * inteiro na base, a contagem nacional é o total da abrangência; com estados inteiros, a contagem estadual de médicos únicos de
   * cada um, da fonte estadual. null na resposta de antes e fora da base do Brasil. */
  abrangenciaCompleta: AbrangenciaCompleta | null;
  disponibilidade: Disponibilidade;
  sessao: { registrado: boolean; resultId: string | null } | null;
  rotulos: RotulosTerritoriais | null;
  /** Indicador que o motor usou no cálculo (a frase-resumo fala dele); null na resposta de antes, que não o trazia. */
  indicador: PainelIndicador | null;
  /** Frase-resumo do motor (23/10/2026): só números conferidos do resultado, sem julgamento nem causa. A tela só a mostra. */
  resumo: { texto: string } | null;
  /** A ordem dos estados pelo indicador (06/11/2026, item 7 do comando de navegação por níveis; `ordem_do_indicador`): do maior
   * para o menor, com as posições de CAP-SUB-02 (empates na mesma posição; os não avaliáveis no fim, sem posição). A lista da
   * tela estreita e os destaques das bolhas seguem esta ordem; a tela não ordena. null fora do nível dos estados. */
  ordemDoIndicador: { atributo: string; itens: { id: string; posicao: number | null }[] } | null;
};

/** Pendência de premissa (ChoiceRequired): o motor pede uma escolha (referencial, formato de número…) antes de calcular. */
export type Pendencia = { chave: string; texto: string; opcoes: { valor: string; rotulo: string }[] };
export class ErroDoMotor extends Error {
  status: number;
  pendencia: Pendencia | null;
  /** O serviço respondeu que está no limite (503 com `ocupado`, 01/11/2026): a tela avisa e tenta de novo depois de `tenteEm` s. */
  ocupado: boolean;
  tenteEm: number | null;
  constructor(mensagem: string, status: number, pendencia: Pendencia | null, ocupado = false, tenteEm: number | null = null) {
    super(mensagem);
    this.status = status;
    this.pendencia = pendencia;
    this.ocupado = ocupado;
    this.tenteEm = tenteEm;
  }
}

/** A mensagem da falha de rede (o serviço não respondeu): sem o texto técnico do navegador. */
export const SEM_ACESSO_AO_SERVICO = "Não foi possível acessar o serviço de análise. Tente novamente em instantes.";

/** fetch dos pedidos ao motor: a falha de rede vira ErroDoMotor com a mensagem da tela; o pedido abortado continua abortado. */
async function buscar(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (exc) {
    if ((exc as { name?: unknown } | null)?.name === "AbortError") throw exc;
    throw new ErroDoMotor(SEM_ACESSO_AO_SERVICO, 0, null);
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

/** Mesma leitura de readApiResponse: corpo JSON ou erro com a mensagem do motor (em português), a pendência e, quando o
 * serviço está no limite, `ocupado`. O código HTTP fica no erro (status), fora da mensagem da tela (01/11/2026). */
async function lerResposta(response: Response): Promise<unknown> {
  const raw = await response.text();
  let body: unknown;
  try { body = JSON.parse(raw); }
  catch {
    throw new ErroDoMotor("Não foi possível interpretar a resposta do serviço. Tente novamente ou procure suporte.",
      response.status, null);
  }
  if (!response.ok) {
    const corpo = objeto(body);
    const detail = corpo?.detail;
    const detalhe = objeto(detail);
    const mensagem = typeof detail === "string" ? detail : texto(detalhe?.detail) ?? texto(detalhe?.mensagem) ?? "Falha no processamento da solicitação.";
    throw new ErroDoMotor(mensagem, response.status, lerPendencia(corpo?.pendencia ?? detalhe?.pendencia),
      corpo?.ocupado === true, num(corpo?.tente_em));
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
    id, tipo, rotulo: texto(o.rotulo) ?? id, uf: texto(o.uf), grupoTerritorial: texto(o.grupo_territorial),
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

/** As contagens de um lado da consulta como o motor as manda. */
function contagensDe(bruto: unknown): ContagensDoLado {
  const o = objeto(bruto);
  return { partirDe: num(o?.partir_de), filtros: num(o?.filtros), final: num(o?.final), naoAvaliaveis: num(o?.nao_avaliaveis) };
}
/** A consulta devolvida pelo motor (a normalizada), com as mesmas regras de forma da tela; o motor só devolve o que aceitou. */
function consultaDe(bruto: unknown): ConsultaTerritorios | null {
  const o = objeto(bruto);
  if (!o) return null;
  const lado = (valor: unknown) => {
    const l = objeto(valor), partir = objeto(l?.partir_de), escolha = objeto(l?.escolha);
    const textos = (v: unknown) => lista(v).filter((x): x is string => typeof x === "string");
    return { partir_de: { tipo: (texto(partir?.tipo) ?? "pais") as ConsultaTerritorios["base"]["partir_de"]["tipo"], regioes: textos(partir?.regioes),
      ufs: textos(partir?.ufs) },
      filtros: lista(l?.filtros).map(f => objeto(f)).filter(Boolean).map(f => ({
        indicador: texto(f!.indicador) as ConsultaTerritorios["base"]["filtros"][number]["indicador"],
        operador: texto(f!.operador) as ConsultaTerritorios["base"]["filtros"][number]["operador"],
        valor: typeof f!.valor === "string" ? Number(f!.valor) : num(f!.valor) })),
      escolha: { modo: escolha?.modo === "marcados" ? "marcados" as const : "todos" as const, municipios: textos(escolha?.municipios) } };
  };
  return { base: lado(o.base), referencia: lado(o.referencia), distancia: { medida: "geodesica", ate: "referencia_mais_proxima" } };
}
/** A referência da resposta, com a Escolha dos territórios quando ela vem (27/10/2026). */
function referenciaRespostaDe(bruto: unknown): PainelReferenciaResposta | null {
  const referencia = objeto(bruto);
  if (!referencia) return null;
  const origem = texto(referencia.origem) ?? "";
  if (referencia.tipo !== "consulta") {
    const membros = lista(referencia.membros).map(m => objeto(m)).filter(Boolean).map(m => ({ id: texto(m!.id) ?? "", rotulo: texto(m!.rotulo) ?? "" }));
    return { tipo: referencia.tipo === "conjunto" ? "conjunto" : "municipio", membros, origem };
  }
  const membros = lista(referencia.membros).map(m => objeto(m)).filter(Boolean).map(m => ({ id: texto(m!.id) ?? "", rotulo: texto(m!.rotulo) ?? "",
    uf: texto(m!.uf), populacao: num(m!.populacao), quantidade: num(m!.quantidade), densidade: num(m!.densidade) }));
  const contagens = objeto(referencia.contagens);
  return { tipo: "consulta", membros, origem, consulta: consultaDe(referencia.consulta), texto: texto(referencia.texto) ?? "",
    baseTexto: texto(referencia.base_texto) ?? "",
    contagens: { base: contagensDe(contagens?.base), referencia: contagensDe(contagens?.referencia) } };
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
export const ARTIGOS_DO_TODO: ArtigoDoTodo[] = ["", "o", "a", "os", "as"];
export function todoDe(bruto: unknown): TodoDaBase | null {
  const o = objeto(bruto);
  const nome = texto(o?.nome);
  if (!nome) return null;
  const artigo = ARTIGOS_DO_TODO.includes(o?.artigo as ArtigoDoTodo) ? o?.artigo as ArtigoDoTodo : "";
  return { nome, artigo };
}
export function rotulosDe(bruto: unknown): RotulosTerritoriais | null {
  const o = objeto(bruto);
  const unidade = rotuloDe(o?.unidade);
  if (!unidade) return null;
  const todo = todoDe(o?.todo), superior = rotuloDe(o?.grupo_superior);
  return { unidade, grupo: rotuloDe(o?.grupo), ...(todo ? { todo } : {}), ...(superior ? { grupo_superior: superior } : {}) };
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
  // A linha do todo: o Brasil (a fonte nacional) ou, numa planilha (07/11/2026, item 2.3 do comando), o todo pelas unidades.
  const contexto = objeto(objeto(o.contexto)?.brasil) ?? objeto(objeto(o.contexto)?.todo);
  const contextoTopo = objeto(o.contexto);
  const abrangenciaCompleta: AbrangenciaCompleta | null = contextoTopo && (typeof contextoTopo.brasil_completo === "boolean" ||
    Array.isArray(contextoTopo.estados)) ? { brasil: contextoTopo.brasil_completo === true,
      estados: lista(contextoTopo.estados).map(objeto).filter((e): e is Record<string, unknown> => !!e && !!texto(e.id)).map(e => ({
        id: texto(e.id)!, rotulo: texto(e.rotulo) ?? texto(e.id)!, competencia: texto(e.competencia), quantidade: num(e.quantidade),
        populacao: num(e.populacao), densidade: num(e.densidade), avaliabilidade: texto(e.avaliabilidade) ?? "NAO_AVALIAVEL",
        motivo: texto(e.motivo) })) } : null;
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
    abrangenciaCompleta,
    disponibilidade,
    sessao: sessao ? { registrado: sessao.registrado === true, resultId: texto(sessao.result_id) } : null,
    rotulos: rotulosDe(o.rotulos),
    indicador: o.indicador === "densidade" || o.indicador === "quantidade" ? o.indicador : null,
    resumo: resumoDe(o.resumo),
    ordemDoIndicador: ordemDoIndicadorDe(o.ordem_do_indicador),
  };
}

/** `ordem_do_indicador` do motor nos tipos da tela; sem a forma esperada (ou na resposta de antes), null. */
export function ordemDoIndicadorDe(bruto: unknown): PainelResposta["ordemDoIndicador"] {
  const o = objeto(bruto);
  if (!o || !Array.isArray(o.itens)) return null;
  const itens: { id: string; posicao: number | null }[] = [];
  for (const entrada of o.itens) {
    const e = objeto(entrada), id = texto(e?.id), posicao = num(e?.posicao);
    if (!id) return null;
    itens.push({ id, posicao: posicao !== null && Number.isInteger(posicao) && posicao > 0 ? posicao : null });
  }
  return { atributo: texto(o.atributo) ?? "", itens };
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
  // O ponto de desenho de cada estado (06/11/2026): a média das sedes dos municípios dele, do motor, só para desenhar.
  const grupos = new Map<string, [number, number]>();
  for (const item of lista(o.grupos)) {
    const g = objeto(item);
    const id = texto(g?.id), lat = num(g?.lat), lon = num(g?.lon);
    if (id && lat !== null && lon !== null && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) grupos.set(id, [lat, lon]);
  }
  return { competencia: texto(o.competencia) ?? "", referencial: texto(o.referencial) ?? "", pontos, semCoordenada,
    ...(Array.isArray(o.grupos) ? { grupos, notaDosGrupos: texto(o.nota_grupos) } : {}) };
}

// ------------------------------------------------------------------------------------------------ lugar em uso (06/11/2026)
/** Pedido de /api/painel/lugar: a competência e a categoria da análise, o grupo do lugar (o prefixo do estado), a competência
 * inicial da variação da faixa e, para as linhas de referência da Tendência, as competências da série. */
/** `regiao` (07/11/2026): o grupo de cima de uma planilha com dois níveis, pelas unidades dele. */
export type LugarOpcoes = { competencia: string; categoria: string; grupo?: string; regiao?: string; desde?: string; serie?: { competencias: string[] };
  /** Numa planilha (07/11/2026, item 1.4 do comando): as escolhas do painel Colunas, como no pedido do gráfico. */
  premissas?: Premissas; rotulos?: RotulosTerritoriais };
export type ValoresDaSerie = { competencia: string; quantidade: number | null; populacao: number | null; densidade: number | null };
/** Um nível do lugar em uso (o todo ou o grupo), com os números do motor: prontos na fonte (nacional ou estadual), nunca somados. */
export type NivelDoLugar = { id: string; nivel: "todo" | "grupo" | "regiao"; rotulo: string; nome: string | null; sigla: string | null; fonte: string;
  regra: string | null; competencia: string; quantidade: number | null; populacao: number | null; densidade: number | null;
  avaliabilidade: string; motivo: string | null; desde: string | null; inicial: PainelValores | null; variacaoPercentual: PainelValores | null;
  motivosVariacao: string[]; serie: ValoresDaSerie[] | null;
  /** Numa planilha (07/11/2026, item 1.4 do comando): de onde vem o total, "pessoas_unicas" (o identificador individual) ou
   * "soma" (a soma das unidades, com a limitação SOMA_COM_POSSIVEL_DUPLA_CONTAGEM); na base do Brasil, null (a fonte pronta). */
  origem: "pessoas_unicas" | "soma" | null; limitacoes: string[] };
export type RespostaLugar = { competencia: string; categoria: string; desde: string | null; todo: NivelDoLugar | null;
  grupo: NivelDoLugar | null; regiao?: NivelDoLugar | null; notas: string[] };
function nivelDoLugarDe(bruto: unknown): NivelDoLugar | null {
  const o = objeto(bruto);
  const id = texto(o?.id);
  if (!o || !id) return null;
  const serie = Array.isArray(o.serie) ? lista(o.serie).map(objeto).filter((s): s is Record<string, unknown> => !!s && !!texto(s.competencia))
    .map(s => ({ competencia: texto(s.competencia)!, quantidade: num(s.quantidade), populacao: num(s.populacao), densidade: num(s.densidade) })) : null;
  return { id, nivel: o.nivel === "grupo" ? "grupo" : o.nivel === "regiao" ? "regiao" : "todo", rotulo: texto(o.rotulo) ?? id, nome: texto(o.nome), sigla: texto(o.sigla),
    fonte: texto(o.fonte) ?? "", regra: texto(o.regra), competencia: texto(o.competencia) ?? "", quantidade: num(o.quantidade),
    populacao: num(o.populacao), densidade: num(o.densidade), avaliabilidade: texto(o.avaliabilidade) ?? "NAO_AVALIAVEL", motivo: texto(o.motivo),
    desde: texto(o.desde), inicial: objeto(o.inicial) ? valores3(o.inicial) : null,
    variacaoPercentual: objeto(o.variacao_percentual) ? valores3(o.variacao_percentual) : null,
    motivosVariacao: lista(o.motivos_variacao).filter((m): m is string => typeof m === "string"), serie,
    origem: o.origem === "pessoas_unicas" || o.origem === "soma" ? o.origem : null,
    limitacoes: lista(o.limitacoes).filter((m): m is string => typeof m === "string") };
}
/** Resposta de /api/painel/lugar nos tipos da tela; nada é calculado aqui. */
export function normalizarLugar(bruto: unknown): RespostaLugar {
  const o = objeto(bruto);
  if (!o) throw new ErroDoMotor("A resposta do lugar em uso não segue o contrato.", 200, null);
  return { competencia: texto(o.competencia) ?? "", categoria: texto(o.categoria) ?? "", desde: texto(o.desde),
    todo: nivelDoLugarDe(o.todo), grupo: nivelDoLugarDe(o.grupo), ...(o.regiao ? { regiao: nivelDoLugarDe(o.regiao) } : {}),
    notas: lista(o.notas).filter((n): n is string => typeof n === "string") };
}
/** Os números do lugar em uso (a faixa e as linhas do todo e do grupo), pedidos à parte do gráfico: trocar o "Ver por" não os pede
 * de novo. */
export async function pedirLugar(fonte: FonteDoMotor, opcoes: LugarOpcoes, signal?: AbortSignal): Promise<RespostaLugar> {
  const response = await buscar(fonte.apiBase + "/api/painel/lugar", { method: "POST", body: formulario(fonte, opcoes, false), signal });
  return normalizarLugar(await lerResposta(response));
}

// ------------------------------------------------------------------------------------------------ chamadas
export async function pedirPainel(fonte: FonteDoMotor, opcoes: PainelOpcoes, signal?: AbortSignal): Promise<PainelResposta> {
  const response = await buscar(fonte.apiBase + "/api/painel", { method: "POST",
    body: formulario(fonte, opcoes, !!opcoes.referencia || !!opcoes.consulta), signal });
  return normalizarResposta(await lerResposta(response), opcoes.nivel ?? "municipios");
}

// ------------------------------------------------------------------------------------------------ escolha dos territórios
/** Pedido de /api/painel/territorios (27/10/2026): a consulta em montagem, a seleção prévia (`base`, como no gráfico) e, quando a
 * janela mostra "Só os que eu marcar", a lista para marcar de um lado, pela busca no nome. */
export type TerritoriosOpcoes = { competencia: string; categoria: string; consulta: ConsultaTerritorios; base?: PainelUniverso;
  lista?: { lado: "base" | "referencia"; busca: string; limite: number }; premissas?: Premissas; rotulos?: RotulosTerritoriais };
/** Um município nas listas da janela: o nome com a UF, a UF e a densidade do motor; nos marcados, se passa pelas etapas 1 e 2. */
export type MunicipioDaLista = { id: string; rotulo: string; uf: string | null; densidade: number | null; passa?: boolean };
/** Um lado da janela segundo o motor: as contagens, o que falta completar, a prévia dos que entram (quantos e os primeiros nomes)
 * e os marcados. */
export type LadoDosTerritorios = { contagens: ContagensDoLado; pendencias: string[]; previa: { total: number; nomes: string[] } | null;
  marcados: MunicipioDaLista[] };
export type RespostaTerritorios = { competencia: string; categoria: string; selecaoPrevia: { total: number; nomes: string[] };
  base: LadoDosTerritorios; referencia: LadoDosTerritorios;
  lista: { lado: "base" | "referencia"; busca: string; total: number; limite: number; itens: MunicipioDaLista[] } | null };
const municipioDaLista = (bruto: unknown): MunicipioDaLista | null => {
  const o = objeto(bruto);
  const id = texto(o?.id);
  return o && id ? { id, rotulo: texto(o.rotulo) ?? id, uf: texto(o.uf), densidade: num(o.densidade),
    ...(typeof o.passa === "boolean" ? { passa: o.passa } : {}) } : null;
};
const ladoDosTerritorios = (bruto: unknown): LadoDosTerritorios => {
  const o = objeto(bruto), previa = objeto(o?.previa);
  return { contagens: contagensDe(o?.contagens), pendencias: lista(o?.pendencias).filter((p): p is string => typeof p === "string"),
    previa: previa ? { total: num(previa.total) ?? 0, nomes: lista(previa.nomes).filter((n): n is string => typeof n === "string") } : null,
    marcados: lista(o?.marcados).map(municipioDaLista).filter((m): m is MunicipioDaLista => !!m) };
};
/** Resposta de /api/painel/territorios nos tipos da tela; nada é calculado aqui: tudo vem do motor. */
export function normalizarTerritorios(bruto: unknown): RespostaTerritorios {
  const o = objeto(bruto);
  if (!o) throw new ErroDoMotor("A resposta da escolha dos territórios não segue o contrato.", 200, null);
  const previa = objeto(o.selecao_previa), listaBruta = objeto(o.lista);
  return { competencia: texto(o.competencia) ?? "", categoria: texto(o.categoria) ?? "",
    selecaoPrevia: { total: num(previa?.total) ?? 0, nomes: lista(previa?.nomes).filter((n): n is string => typeof n === "string") },
    base: ladoDosTerritorios(o.base), referencia: ladoDosTerritorios(o.referencia),
    lista: listaBruta ? { lado: listaBruta.lado === "referencia" ? "referencia" : "base", busca: texto(listaBruta.busca) ?? "",
      total: num(listaBruta.total) ?? 0, limite: num(listaBruta.limite) ?? 0,
      itens: lista(listaBruta.itens).map(municipioDaLista).filter((m): m is MunicipioDaLista => !!m) } : null };
}
/** As contagens da Escolha dos territórios, pedidas pela janela enquanto a consulta é montada (com a versão geográfica). */
export async function pedirTerritorios(fonte: FonteDoMotor, opcoes: TerritoriosOpcoes, signal?: AbortSignal): Promise<RespostaTerritorios> {
  const response = await buscar(fonte.apiBase + "/api/painel/territorios", { method: "POST", body: formulario(fonte, opcoes, true), signal });
  return normalizarTerritorios(await lerResposta(response));
}

/** Coordenadas autorizadas das unidades na competência (o mesmo formulário de /api/painel, com a versão geográfica): pedidas
 * só quando o mapa aparece ou o gráfico mostra unidades com o mapa disponível. */
export async function pedirMapa(fonte: FonteDoMotor, opcoes: MapaOpcoes, signal?: AbortSignal): Promise<DadosDoMapa> {
  const response = await buscar(fonte.apiBase + "/api/painel/mapa", { method: "POST", body: formulario(fonte, opcoes, true), signal });
  return normalizarMapa(await lerResposta(response));
}

