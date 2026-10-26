// Histórico da conversa na caixa flutuante (Frente VI, 26/10/2026): a conversa inteira à vista, em ordem, com as mensagens da
// pessoa exatamente como ela escreveu e as respostas do agente. Modelo puro (sem React), testado em
// tests/historicoConversa.test.mjs. O histórico visual e o contexto enviado ao Gemini são responsabilidades distintas: a tela
// guarda e mostra tudo; ao backend vai só a janela das mensagens mais recentes (turnosParaEnvio), que ele ainda tria antes do
// provedor. Nenhuma chamada ao Gemini é feita para mostrar ou guardar o histórico.

export type Papel = "usuario" | "agente" | "aviso";
/** Uma mensagem do histórico. `aviso` é a comunicação cordial de indisponibilidade da conversa (título e texto), como resposta
 * do sistema no mesmo histórico, na ordem em que aconteceu. */
export type Mensagem = { id: string; papel: Papel; texto: string; titulo?: string; origem?: string };
export type Turno = { papel: "usuario" | "agente"; texto: string };
export type Aviso = { tipo: "cota" | "indisponivel" | "entrada"; titulo?: string; texto: string };

/** Textos da comunicação cordial (seção 11.4 da missão de 26/10/2026), os mesmos do backend (llm_bridge.py). */
export const TITULO_INDISPONIVEL = "Assistente conversacional temporariamente indisponível";
export const TEXTO_COTA = "O limite de consultas ao assistente conversacional foi atingido neste momento. Você pode continuar " +
  "utilizando normalmente as análises e funcionalidades disponíveis por meio dos botões e controles da plataforma. O recurso " +
  "de conversa poderá ser utilizado novamente quando o serviço estiver disponível.";
export const TEXTO_INDISPONIVEL = "O recurso de conversa não está disponível neste momento. Você pode continuar utilizando as " +
  "funcionalidades e análises disponíveis por meio dos botões e controles da plataforma.";
export const MAX_TURNOS_ENVIADOS = 8;
export const MAX_CARACTERES_POR_TURNO = 700;
/** Distância do fim (px) em que a pessoa ainda está "acompanhando o final" da conversa. */
export const MARGEM_DO_FIM = 48;

let contador = 0;
/** Identificador único da mensagem na sessão da tela (chave de renderização e proteção contra duplicação). */
export function novoId(papel: Papel): string {
  contador += 1;
  return papel + "-" + Date.now().toString(36) + "-" + contador.toString(36);
}

/** Acrescenta a mensagem no fim; uma mensagem com o mesmo id (renderização repetida, reenvio do mesmo estado) substitui a
 * anterior no lugar dela, sem duplicar. */
export function acrescentar(lista: readonly Mensagem[], mensagem: Mensagem): Mensagem[] {
  const indice = lista.findIndex(item => item.id === mensagem.id);
  if (indice < 0) return [...lista, mensagem];
  const nova = [...lista];
  nova[indice] = mensagem;
  return nova;
}

/** A última resposta do agente (ou o último aviso), para quem lê só o fim. */
export function ultimaResposta(lista: readonly Mensagem[]): Mensagem | undefined {
  for (let i = lista.length - 1; i >= 0; i -= 1) if (lista[i].papel !== "usuario") return lista[i];
  return undefined;
}

/** A janela da conversa que vai ao backend: as mensagens mais recentes da pessoa e do agente, sem os avisos de
 * indisponibilidade, cada uma cortada no limite. O histórico da tela continua inteiro. */
export function turnosParaEnvio(lista: readonly Mensagem[], limite = MAX_TURNOS_ENVIADOS): Turno[] {
  return lista.filter(item => item.papel !== "aviso" && item.texto.trim())
    .slice(-limite)
    .map(item => ({ papel: item.papel === "usuario" ? "usuario" : "agente", texto: item.texto.slice(0, MAX_CARACTERES_POR_TURNO) }));
}

/** A pessoa está no fim da conversa (acompanhando o final): só então a chegada de uma resposta rola até ela. */
export function estaNoFim(scrollTop: number, scrollHeight: number, clientHeight: number, margem = MARGEM_DO_FIM): boolean {
  return scrollHeight - scrollTop - clientHeight <= margem;
}

/** O aviso cordial para uma falha da conversa, sem código HTTP nem mensagem técnica: limite de consultas só quando o serviço
 * confirmou (429); pedido inválido (422) com a orientação do próprio backend, sem o código; o resto, indisponibilidade. */
export function avisoDeFalha(status: number | null, detalhe?: unknown): Aviso {
  if (status === 429) return { tipo: "cota", titulo: TITULO_INDISPONIVEL, texto: TEXTO_COTA };
  if ((status === 422 || status === 409) && typeof detalhe === "string" && detalhe.trim() &&
      !/HTTP|Traceback|Error|Exception|RESOURCE_EXHAUSTED|quota|rate limit/i.test(detalhe))
    return { tipo: "entrada", texto: detalhe.trim() };
  return { tipo: "indisponivel", titulo: TITULO_INDISPONIVEL, texto: TEXTO_INDISPONIVEL };
}

/** O aviso que a própria resposta do backend traz (campo `indisponibilidade`), quando a conversa ficou sem o Gemini. */
export function avisoDaResposta(corpo: unknown): Aviso | null {
  const bruto = (corpo as { indisponibilidade?: { tipo?: unknown; titulo?: unknown; texto?: unknown } } | null)?.indisponibilidade;
  if (!bruto || typeof bruto.texto !== "string") return null;
  return { tipo: bruto.tipo === "cota" ? "cota" : "indisponivel",
    titulo: typeof bruto.titulo === "string" ? bruto.titulo : TITULO_INDISPONIVEL, texto: bruto.texto };
}

/** A mensagem de aviso no histórico (pedido inválido vira resposta comum do agente, sem título). */
export function mensagemDeAviso(aviso: Aviso): Mensagem {
  return aviso.tipo === "entrada" ? { id: novoId("agente"), papel: "agente", texto: aviso.texto }
    : { id: novoId("aviso"), papel: "aviso", titulo: aviso.titulo ?? TITULO_INDISPONIVEL, texto: aviso.texto };
}
