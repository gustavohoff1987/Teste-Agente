// Estados da conexão com o serviço de análise (hospedagem no GitHub Pages + Cloud Run, 01/11/2026). A interface abre pelo
// Pages mesmo com o serviço fora do ar; o navegador chama o serviço por HTTPS em outro endereço. As respostas da própria
// plataforma (serviço suspenso, sem instância, erro sem CORS) chegam ao navegador como falha de rede e não se distinguem
// entre si: antes de declarar a indisponibilidade, uma nova tentativa curta.
// - verificando: a abertura, nos primeiros segundos (nada aparece);
// - iniciando (B): a verificação demora ou a primeira falhou, e a tentativa curta está em curso (partida a frio);
// - online: o serviço respondeu;
// - ocupado (C): o próprio serviço respondeu que está no limite (resposta legível, com `ocupado`): aviso, sem a mensagem de
//   indisponibilidade total. Sai com a resposta de uma rota com limite (ROTAS_COM_LIMITE) ou sozinho; a saúde e a sessão
//   respondem mesmo com o serviço no limite e não o tiram;
// - indisponivel (A): a tentativa curta também falhou. Novas tentativas automáticas, com intervalo progressivo e teto, em
//   pausa enquanto a aba está oculta, e o botão "Tentar novamente" (G).
// A conversa sem o Gemini (D), a sessão expirada (E) e os erros de validação (F) têm o tratamento próprio de cada tela e
// nunca passam por aqui como indisponibilidade. A consulta da sessão a cada 30 s não muda (conversationSession.ts).
// Desde 19/11/2026 (PA-02), a página espera o serviço ligar, no observador dos pedidos (observarRespostas):
// - com o monitor em "verificando" ou "iniciando", os pedidos esperam o serviço responder antes de sair (com o aviso de partida
//   de sempre), até o prazo da verificação; se o monitor for para "indisponivel", eles saem e falham como antes;
// - o pedido que só lê ou calcula e falha por rede espera o serviço responder de novo e se repete, até 2 vezes (REPETIVEIS e as
//   leituras); depois, o erro aparece como antes;
// - nunca se repetem sozinhos a conversa, os eventos da sessão, o pré-exame de planilha e qualquer envio de arquivo
//   (NUNCA_SE_REPETEM), nem os pedidos cancelados pela própria página e as respostas legíveis do serviço, inclusive o ocupado;
// - a consulta da sessão e os eventos dela saem na hora, como antes (nem esperam nem se repetem).
// Sem dependências: os testes (tests/conexao.test.mjs) rodam o módulo com um relógio simulado.

export type Fase = "verificando" | "iniciando" | "online" | "ocupado" | "indisponivel";
export type EstadoDaConexao = {
  fase: Fase;
  /** Novas tentativas automáticas já feitas desde que o serviço ficou indisponível. */
  tentativas: number;
  /** As tentativas automáticas chegaram ao teto: só o botão tenta de novo. */
  esgotadas: boolean;
  /** Aba oculta: as tentativas automáticas esperam a aba voltar. */
  pausada: boolean;
  textoOcupado: string;
  /** O serviço voltou depois de uma indisponibilidade (aviso breve). */
  restabelecida: boolean;
};

export const NOME_OFICIAL = "Agente Diagnóstico Territorial da Força de Trabalho na Saúde";
export const TITULO_INDISPONIVEL = "Serviço temporariamente indisponível";
export const TEXTO_INDISPONIVEL = "O Agente Diagnóstico Territorial da Força de Trabalho na Saúde está temporariamente " +
  "indisponível. Por favor, tente acessar novamente mais tarde. Agradecemos sua compreensão.";
export const TEXTO_INICIANDO = "O serviço está iniciando. Depois de um período sem uso, o primeiro acesso pode levar alguns " +
  "segundos.";
export const TEXTO_OCUPADO = "O Agente Diagnóstico Territorial da Força de Trabalho na Saúde está atendendo muitas " +
  "solicitações neste momento. Aguarde alguns segundos e tente novamente; a sua sessão e as suas análises continuam.";
export const TEXTO_RESTABELECIDA = "Conexão restabelecida.";

/** Sem resposta da verificação depois disso, o aviso de partida (B). */
export const AVISO_DE_PARTIDA_MS = 3000;
/** A verificação desiste depois disso (a partida a frio medida no CI fica bem abaixo; ver Docs/implantacao). */
export const PRAZO_DA_VERIFICACAO_MS = 90000;
/** A tentativa curta, antes de declarar a indisponibilidade. */
export const TENTATIVA_CURTA_MS = 2000;
/** Intervalos das novas tentativas automáticas; depois da última, só o botão. */
export const INTERVALOS_MS = [5000, 10000, 20000, 40000, 60000, 120000];
/** O aviso de ocupado sai sozinho depois disso, se nenhuma outra resposta de ocupado chegar. */
export const DURACAO_DO_OCUPADO_MS = 20000;
export const DURACAO_DO_RESTABELECIMENTO_MS = 6000;
/** As rotas que esperam vaga ou contam nos pedidos da sessão (backend/carga.py, PESADAS e CONVERSA; test_hospedagem.py
 * confere a lista): só a resposta de uma delas mostra que o serviço deixou de estar no limite. */
export const ROTAS_COM_LIMITE: ReadonlySet<string> = new Set(["/api/inspect", "/api/preflight", "/api/analyze", "/api/painel",
  "/api/painel/referencias", "/api/painel/territorios", "/api/painel/mapa", "/api/painel/lugar", "/api/brazil/description",
  "/api/detector", "/api/simulador", "/api/llm/interpret",
  "/api/llm/interpret-context", "/api/exploration/interpret"]);

/** No máximo, quantas vezes um pedido que só lê ou calcula se repete sozinho depois de uma falha de rede (PA-02). */
export const REPETICOES_DEPOIS_DA_FALHA = 2;
/** Os pedidos (POST) que só leem ou calculam e se repetem sozinhos depois de uma falha de rede, sem arquivo: a criação da sessão, o
 * exame da base do Brasil, a análise, o painel, o Detector e o Simulador. As leituras (GET) também, menos a consulta da sessão. */
export const REPETIVEIS: ReadonlySet<string> = new Set(["/api/session", "/api/inspect", "/api/analyze", "/api/painel",
  "/api/painel/referencias", "/api/painel/territorios", "/api/painel/criterios", "/api/painel/lugar", "/api/painel/mapa",
  "/api/detector", "/api/simulador"]);
/** Nunca se repetem sozinhos: a conversa (cada repetição gastaria cota do Gemini e poderia duplicar a mensagem), os eventos da
 * sessão e o pré-exame de planilha. Qualquer envio de arquivo também não. */
export const NUNCA_SE_REPETEM: ReadonlySet<string> = new Set(["/api/llm/interpret", "/api/llm/interpret-context",
  "/api/exploration/interpret", "/api/session/interact", "/api/session/revision", "/api/session/close", "/api/preflight"]);
/** Os eventos da sessão saem na hora, como antes (conversationSession.ts não muda), e a consulta dela (GET /api/session) também. */
const EVENTOS_DA_SESSAO: ReadonlySet<string> = new Set(["/api/session/interact", "/api/session/revision", "/api/session/close"]);

/** O fim de uma espera pelo serviço: ele respondeu, ficou indisponível, o prazo passou ou a própria página cancelou o pedido. */
export type Desfecho = "online" | "indisponivel" | "prazo" | "abortado";
export type OpcoesDaEspera = {
  sinal?: AbortSignal | null;
  /** O limite da espera; por padrão, o prazo da verificação. */
  prazoMs?: number;
  /** Só uma resposta do serviço depois deste marco conta (a repetição depois de uma falha); sem ele, a fase online ou ocupado. */
  depoisDe?: number;
};

export type Relogio = { agendar: (acao: () => void, ms: number) => unknown; cancelar: (id: unknown) => void };
const RELOGIO_DO_NAVEGADOR: Relogio = { agendar: (acao, ms) => setTimeout(acao, ms), cancelar: id => clearTimeout(id as number) };

export type OpcoesDoMonitor = {
  /** Verifica o serviço (GET /api/health); true quando ele respondeu que está no ar. */
  verificar: (sinal: AbortSignal) => Promise<boolean>;
  aoMudar: (estado: EstadoDaConexao) => void;
  relogio?: Relogio;
  /** A aba está à vista (document.visibilityState). */
  visivel?: () => boolean;
};

export type Monitor = {
  iniciar: () => void;
  /** Um pedido da tela ao serviço falhou sem resposta (falha de rede, CORS ou plataforma). */
  falhaDeRede: () => void;
  /** O serviço respondeu que está no limite (503 com `ocupado`). */
  ocupado: (texto?: string) => void;
  /** O serviço respondeu (qualquer resposta legível que não seja de ocupado); `comLimite`: a rota é de ROTAS_COM_LIMITE. */
  respondeu: (comLimite: boolean) => void;
  /** O botão "Tentar novamente". */
  tentarAgora: () => void;
  /** A aba ficou oculta ou voltou à vista. */
  visibilidade: (visivel: boolean) => void;
  estado: () => EstadoDaConexao;
  /** Espera o serviço (PA-02): "online" quando ele responde, "indisponivel" quando a fase vai para indisponível, "prazo" depois
   * do limite (ou com o monitor encerrado) e "abortado" quando a página cancela o pedido. */
  aguardar: (opcoes?: OpcoesDaEspera) => Promise<Desfecho>;
  /** Quantas vezes o serviço respondeu até agora: a verificação com sucesso, uma resposta legível ou o ocupado. */
  marco: () => number;
  encerrar: () => void;
};

type Motivo = "abertura" | "falha" | "curta" | "automatica" | "manual";

export function criarMonitor({ verificar, aoMudar, relogio = RELOGIO_DO_NAVEGADOR, visivel = () => true }: OpcoesDoMonitor): Monitor {
  let estado: EstadoDaConexao = { fase: "verificando", tentativas: 0, esgotadas: false, pausada: !visivel(), textoOcupado: "",
    restabelecida: false };
  let emCurso = false, encerrado = false, devidaNaVolta = false, marco = 0;
  let proxima: unknown = null, partida: unknown = null, prazo: unknown = null, fimDoOcupado: unknown = null,
    fimDoAviso: unknown = null;
  /** As esperas em curso (aguardar): cada uma confere a própria condição a cada mudança. */
  const esperas = new Set<() => void>();
  function avisarEsperas() { for (const conferir of [...esperas]) conferir(); }

  function mudar(parcial: Partial<EstadoDaConexao>) {
    estado = { ...estado, ...parcial };
    if (!encerrado) aoMudar(estado);
    avisarEsperas();
  }
  /** O serviço respondeu: uma verificação com sucesso, uma resposta legível ou o ocupado. */
  function respondeuOServico() { marco += 1; avisarEsperas(); }

  function aguardar({ sinal = null, prazoMs = PRAZO_DA_VERIFICACAO_MS, depoisDe }: OpcoesDaEspera = {}): Promise<Desfecho> {
    return new Promise<Desfecho>(resolver => {
      let feito = false, limite: unknown = null;
      const terminar = (desfecho: Desfecho) => {
        if (feito) return;
        feito = true;
        esperas.delete(conferir);
        cancelar(limite);
        sinal?.removeEventListener("abort", aoAbortar);
        resolver(desfecho);
      };
      const aoAbortar = () => terminar("abortado");
      function conferir() {
        if (encerrado) terminar("prazo");
        else if (estado.fase === "indisponivel") terminar("indisponivel");
        else if (depoisDe !== undefined ? marco > depoisDe : estado.fase === "online" || estado.fase === "ocupado") terminar("online");
      }
      if (sinal?.aborted) { terminar("abortado"); return; }
      sinal?.addEventListener("abort", aoAbortar, { once: true });
      esperas.add(conferir);
      limite = relogio.agendar(() => { limite = null; terminar("prazo"); }, prazoMs);
      conferir();
    });
  }
  function cancelar(id: unknown) { if (id !== null) relogio.cancelar(id); }
  function cancelarProxima() { cancelar(proxima); proxima = null; }

  function agendar(motivo: Motivo, ms: number) {
    cancelarProxima();
    proxima = relogio.agendar(() => {
      proxima = null;
      if (motivo === "automatica" && estado.pausada) { devidaNaVolta = true; return; }
      void verificarAgora(motivo);
    }, ms);
  }

  function online() {
    cancelarProxima();
    cancelar(fimDoOcupado); fimDoOcupado = null;
    const voltou = estado.fase === "indisponivel";
    devidaNaVolta = false;
    mudar({ fase: "online", tentativas: 0, esgotadas: false, textoOcupado: "", restabelecida: voltou || estado.restabelecida });
    if (voltou) {
      cancelar(fimDoAviso);
      fimDoAviso = relogio.agendar(() => { fimDoAviso = null; mudar({ restabelecida: false }); }, DURACAO_DO_RESTABELECIMENTO_MS);
    }
  }

  function indisponivel(tentativas: number) {
    const esgotadas = tentativas >= INTERVALOS_MS.length;
    mudar({ fase: "indisponivel", tentativas, esgotadas, textoOcupado: "", restabelecida: false });
    if (!esgotadas) agendar("automatica", INTERVALOS_MS[tentativas]);
  }

  async function verificarAgora(motivo: Motivo) {
    if (emCurso || encerrado) return;
    emCurso = true;
    const controle = new AbortController();
    if (motivo === "abertura" || motivo === "curta")
      partida = relogio.agendar(() => { partida = null; if (estado.fase === "verificando") mudar({ fase: "iniciando" }); },
        motivo === "abertura" ? AVISO_DE_PARTIDA_MS : 0);
    prazo = relogio.agendar(() => { prazo = null; controle.abort(); }, PRAZO_DA_VERIFICACAO_MS);
    let ok = false;
    try { ok = await verificar(controle.signal); } catch { ok = false; }
    cancelar(partida); partida = null;
    cancelar(prazo); prazo = null;
    emCurso = false;
    if (encerrado) return;
    if (ok) { online(); respondeuOServico(); return; }
    if (motivo === "abertura" || motivo === "falha") {
      // Primeira falha: a tentativa curta, com o aviso de partida (na abertura) ou sem mudar a tela (durante o uso).
      if (motivo === "abertura") mudar({ fase: "iniciando" });
      agendar("curta", TENTATIVA_CURTA_MS);
      return;
    }
    if (motivo === "automatica") { indisponivel(estado.tentativas + 1); return; }
    indisponivel(0);  // a tentativa curta ou o botão: o ciclo das automáticas recomeça
  }

  return {
    iniciar: () => { void verificarAgora("abertura"); },
    falhaDeRede: () => {
      if ((estado.fase === "online" || estado.fase === "ocupado") && !emCurso && proxima === null) void verificarAgora("falha");
    },
    ocupado: (texto?: string) => {
      cancelarProxima();
      cancelar(fimDoOcupado);
      mudar({ fase: "ocupado", tentativas: 0, esgotadas: false, textoOcupado: texto?.trim() || TEXTO_OCUPADO });
      fimDoOcupado = relogio.agendar(() => { fimDoOcupado = null; if (estado.fase === "ocupado") online(); }, DURACAO_DO_OCUPADO_MS);
      respondeuOServico();
    },
    respondeu: (comLimite: boolean) => {
      if (!(estado.fase === "online" || (estado.fase === "ocupado" && !comLimite))) online();
      respondeuOServico();
    },
    tentarAgora: () => { cancelarProxima(); void verificarAgora("manual"); },
    visibilidade: (agora: boolean) => {
      if (agora === !estado.pausada) return;
      mudar({ pausada: !agora });
      if (agora && devidaNaVolta && estado.fase === "indisponivel") {
        devidaNaVolta = false;
        void verificarAgora("automatica");
      }
    },
    estado: () => estado,
    aguardar,
    marco: () => marco,
    encerrar: () => {
      encerrado = true;
      for (const id of [proxima, partida, prazo, fimDoOcupado, fimDoAviso]) cancelar(id);
      avisarEsperas();  // as esperas em curso terminam: os pedidos saem como antes
    },
  };
}

/** A URL de um pedido do fetch (texto, URL ou Request). */
function urlDe(entrada: unknown): string {
  if (typeof entrada === "string") return entrada;
  if (entrada && typeof entrada === "object" && "href" in entrada) return String((entrada as URL).href);
  if (entrada && typeof entrada === "object" && "url" in entrada) return String((entrada as Request).url);
  return "";
}

/** O caminho a partir de `/api/`, sem a consulta, de uma URL absoluta ou relativa. */
function caminhoDe(url: string): string {
  let caminho = url.split(/[?#]/)[0];
  try { caminho = new URL(url, "http://local").pathname; } catch { /* fica o texto sem a consulta */ }
  const inicio = caminho.indexOf("/api/");
  return inicio < 0 ? caminho : caminho.slice(inicio);
}

function abortado(erro: unknown): boolean {
  return !!erro && typeof erro === "object" && (erro as { name?: unknown }).name === "AbortError";
}

/** O método do pedido (do `init`, do `Request` ou GET). */
function metodoDe(entrada: unknown, init?: RequestInit): string {
  if (init?.method) return init.method.toUpperCase();
  const metodo = entrada && typeof entrada === "object" ? (entrada as { method?: unknown }).method : undefined;
  return typeof metodo === "string" ? metodo.toUpperCase() : "GET";
}

/** O sinal de cancelamento do pedido (do `init` ou do `Request`). */
function sinalDe(entrada: unknown, init?: RequestInit): AbortSignal | null {
  if (init?.signal) return init.signal;
  const sinal = entrada && typeof entrada === "object" ? (entrada as { signal?: AbortSignal | null }).signal : undefined;
  return sinal ?? null;
}

/** O pedido leva um arquivo (ou um corpo que não se reenvia): nunca se repete sozinho. */
function levaArquivo(entrada: unknown, init?: RequestInit): boolean {
  if (entrada && typeof entrada === "object" && (entrada as { body?: unknown }).body) return true;  // o corpo já está num Request
  const corpo = init?.body;
  if (corpo === undefined || corpo === null || typeof corpo === "string" || corpo instanceof URLSearchParams) return false;
  if (typeof FormData !== "undefined" && corpo instanceof FormData) {
    let arquivo = false;
    corpo.forEach(valor => { if (typeof valor !== "string") arquivo = true; });
    return arquivo;
  }
  return true;
}

/** O pedido só lê ou calcula e pode se repetir sozinho depois de uma falha de rede. */
function seRepete(metodo: string, caminho: string, entrada: unknown, init?: RequestInit): boolean {
  if (NUNCA_SE_REPETEM.has(caminho) || levaArquivo(entrada, init)) return false;
  if (metodo === "GET" || metodo === "HEAD") return caminho !== "/api/session";  // a consulta da sessão: como antes
  return metodo === "POST" && REPETIVEIS.has(caminho);
}

/** O pedido espera o serviço ligar antes de sair: todos, menos a consulta e os eventos da sessão, que saem na hora. */
function esperaAPartida(metodo: string, caminho: string): boolean {
  return !EVENTOS_DA_SESSAO.has(caminho) && !(caminho === "/api/session" && metodo === "GET");
}

/** O mesmo erro que o fetch dá quando a página cancela o pedido. */
function erroDeCancelamento(sinal: AbortSignal | null): unknown {
  return sinal?.reason ?? new DOMException("The operation was aborted.", "AbortError");
}

/** Observa as respostas dos pedidos da tela ao serviço (`/api/` em `apiBase`): falha de rede, ocupado e resposta, sem mudar o
 * resultado de nenhum pedido. Desde 19/11/2026 (PA-02), também a espera do serviço na partida e a repetição, até 2 vezes, dos
 * pedidos que só leem ou calculam e falham por rede (ver o cabeçalho). Devolve a função que desfaz a observação. O pedido
 * abortado pela própria tela não é falha. */
export function observarRespostas(monitor: Monitor, apiBase: string,
  alvo: { fetch: typeof fetch } = globalThis as unknown as { fetch: typeof fetch }): () => void {
  const anterior = alvo.fetch;
  const original = anterior.bind(alvo);  // o fetch do navegador exige o próprio objeto global como `this`
  const observado = async (entrada: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = urlDe(entrada);
    if (!url.includes("/api/") || (apiBase && !url.startsWith(apiBase))) return original(entrada, init);
    const caminho = caminhoDe(url), metodo = metodoDe(entrada, init), sinal = sinalDe(entrada, init);
    const fase = monitor.estado().fase;
    if ((fase === "verificando" || fase === "iniciando") && !sinal?.aborted && esperaAPartida(metodo, caminho)) {
      // Na partida, o pedido espera o serviço responder, com o aviso de partida de sempre. Indisponível ou fora do prazo, ele
      // sai mesmo assim e falha (ou responde) como antes.
      if (await monitor.aguardar({ sinal }) === "abortado") throw erroDeCancelamento(sinal);
    }
    const repetivel = seRepete(metodo, caminho, entrada, init);
    for (let repeticoes = 0; ; repeticoes += 1) {
      let resposta: Response;
      try {
        resposta = await original(entrada, init);
      } catch (erro) {
        if (abortado(erro)) throw erro;
        const antes = monitor.marco();
        monitor.falhaDeRede();
        if (!repetivel || repeticoes >= REPETICOES_DEPOIS_DA_FALHA) throw erro;
        // Só lê ou calcula: espera o serviço responder de novo (a verificação que a falha dispara) e repete o mesmo pedido.
        const desfecho = await monitor.aguardar({ sinal, depoisDe: antes });
        if (desfecho === "abortado") throw erroDeCancelamento(sinal);
        if (desfecho !== "online") throw erro;
        continue;
      }
      if (resposta.status === 503) {
        try {
          const corpo = await resposta.clone().json() as { ocupado?: unknown; detail?: unknown };
          if (corpo?.ocupado === true) { monitor.ocupado(typeof corpo.detail === "string" ? corpo.detail : undefined); return resposta; }
        } catch { /* corpo que não é JSON: uma resposta comum */ }
      }
      monitor.respondeu(ROTAS_COM_LIMITE.has(caminho));
      return resposta;
    }
  };
  alvo.fetch = observado as typeof fetch;
  return () => { if (alvo.fetch === observado) alvo.fetch = anterior; };
}
