// Cliente das rotas do painel integrado de bolhas (/api/painel e /api/painel/referencias), com os nomes de campos do motor
// (backend/painel.py; Docs/PAINEL_INTEGRADO.md). Todo número vem do backend; a tela só posiciona, filtra (estado visual) e
// desenha. As opções são estritas: o motor recusa chave desconhecida (422). O formulário segue o padrão de
// appendSource/readApiResponse (App.tsx), sempre na base Brasil oficial, com o mapeamento do perfil oficial ("{}").
import { contextRevision, sessionFetch as fetch } from "./conversationSession";

export type PainelIndicador = "densidade" | "quantidade";
export type PainelAtributo = "densidade" | "quantidade" | "populacao";
export type PainelOrdem = "desc" | "asc";
/** Universo dos municípios, na mesma forma de `options.abrangencia.municipios`. */
export type PainelMunicipios = { todos: boolean; estados: string[]; ids: string[] };
export type PainelUniverso = { municipios: PainelMunicipios };
export type PainelCriterio = { atributo: PainelAtributo; ordem: PainelOrdem };
/** Conjunto agregado: id com letras, números, _ ou - (até 64), rótulo de até 120 caracteres, ao menos dois membros. */
export type PainelConjuntoPedido = { id: string; rotulo: string; membros: string[] };
/** Um membro: a referência é um município; dois ou mais: conjunto de referência (distância até o membro mais próximo). O
 * critério só registra a origem; com o universo visto na lista, a origem cita a posição exata nele. */
export type PainelReferenciaPedido = { membros: string[]; criterio: PainelCriterio & { universo?: PainelUniverso } };

/** Opções de /api/painel: só estas chaves. */
export type PainelOpcoes = {
  competencia: string;
  competencia_inicial?: string;
  categoria: string;
  base: PainelUniverso;
  conjuntos?: PainelConjuntoPedido[];
  referencia?: PainelReferenciaPedido;
};

/** Valores de uma competência; null quando não há valor avaliável (nunca zero no lugar da falta). */
export type PainelValores = { populacao: number | null; quantidade: number | null; densidade: number | null };
/** distancia e variacao: null quando não foram pedidas; false quando foram pedidas e não são avaliáveis. */
export type PainelAvaliavel = { densidade: boolean; distancia: boolean | null; variacao: boolean | null };
export type PainelItem = {
  id: string;
  tipo: "municipio" | "conjunto";
  rotulo: string;
  uf: string | null;
  /** Conjunto: identificadores dos municípios agregados, na ordem do pedido. */
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
  /** Valores na competência inicial (todos null sem competência inicial). */
  inicial: PainelValores;
  /** (v2 − v1) / v1 × 100 por CAP-TMP-01; null quando não avaliável, com o motivo. */
  variacao_percentual: PainelValores;
  avaliavel: PainelAvaliavel;
  /** Textos em português, cada um terminado pelo código entre parênteses. */
  motivos: string[];
  /** Membro da referência (distância 0) ou conjunto igual à referência. */
  referencia: boolean;
};
export type PainelDominio = [number, number];
export type PainelReferenciaResposta = { tipo: "municipio" | "conjunto"; membros: { id: string; rotulo: string }[]; origem: string };
export type PainelResposta = {
  competencia: string;
  competencia_inicial: string | null;
  categoria: string;
  versao_base: string | null;
  chave_execucao: string;
  referencia: PainelReferenciaResposta | null;
  itens: PainelItem[];
  /** [mínimo, máximo] dos valores avaliáveis devolvidos (densidade, quantidade, populacao, distancia_km e as variações), ou null.
   * Os domínios dos indicadores já incluem os valores iniciais; o da distância, a do membro mais distante dos conjuntos. */
  dominios: Partial<Record<string, PainelDominio | null>>;
  /** Textos de método e premissas. */
  notas: string[];
  /** Códigos de limitação (SOMA_COM_POSSIVEL_DUPLA_CONTAGEM, AGREGADO_PARCIAL, DISTANCIA_GEODESICA_DIRETA…). */
  limitacoes: string[];
};

/** Opções de /api/painel/referencias: só estas chaves (o critério aqui não leva universo). */
export type ReferenciasOpcoes = { competencia: string; categoria: string; universo: PainelUniverso; criterio: PainelCriterio };
/** Candidato na ordem do motor (CAP-SUB-02), com empates na mesma posição (1, 2, 2, 4). */
export type ReferenciaCandidato = { id: string; rotulo: string; uf: string | null; valor: number | null; posicao: number | null };
export type ReferenciaNaoAvaliavel = { id: string; rotulo: string; uf: string | null; motivos: string[] };
export type ReferenciasResposta = { criterio: PainelCriterio; competencia: string; categoria: string;
  candidatos: ReferenciaCandidato[]; nao_avaliaveis: ReferenciaNaoAvaliavel[] };

/** Base oficial do Brasil (o painel não usa arquivos importados nesta entrega). */
export type PainelFonte = { apiBase: string; datasetVersion: string; sheet: string };

function formulario(fonte: PainelFonte, opcoes: object): FormData {
  const form = new FormData();
  form.append("context_revision", String(contextRevision()));
  form.append("dataset", "brazil");
  form.append("scope", "municipal");
  form.append("dataset_version", fonte.datasetVersion);
  form.append("sheet", fonte.sheet);
  form.append("mapping", "{}");  // perfil oficial da base Brasil, exigido pelo painel
  form.append("options", JSON.stringify(opcoes));
  return form;
}

/** Mesma leitura de readApiResponse: corpo JSON ou erro com a mensagem do backend (em português) e o código HTTP. */
async function lerResposta<T>(response: Response): Promise<T> {
  const raw = await response.text();
  let body: unknown;
  try { body = JSON.parse(raw); }
  catch {
    throw new Error("Não foi possível interpretar a resposta do serviço (HTTP " + response.status + "). Tente novamente ou procure suporte.");
  }
  if (!response.ok) {
    const detail = body && typeof body === "object" ? (body as { detail?: unknown }).detail : undefined;
    throw new Error((typeof detail === "string" ? detail : "Falha no processamento da solicitação.") + " (HTTP " + response.status + ")");
  }
  return body as T;
}

export async function pedirPainel(fonte: PainelFonte, opcoes: PainelOpcoes, signal?: AbortSignal): Promise<PainelResposta> {
  const response = await fetch(fonte.apiBase + "/api/painel", { method: "POST", body: formulario(fonte, opcoes), signal });
  const body = await lerResposta<PainelResposta>(response);
  if (!body || !Array.isArray(body.itens)) throw new Error("A resposta do painel não segue o contrato (itens ausentes).");
  return body;
}

export async function pedirReferencias(fonte: PainelFonte, opcoes: ReferenciasOpcoes, signal?: AbortSignal): Promise<ReferenciasResposta> {
  const response = await fetch(fonte.apiBase + "/api/painel/referencias", { method: "POST", body: formulario(fonte, opcoes), signal });
  const body = await lerResposta<ReferenciasResposta>(response);
  if (!body || !Array.isArray(body.candidatos)) throw new Error("A resposta das referências não segue o contrato (candidatos ausentes).");
  return body;
}
