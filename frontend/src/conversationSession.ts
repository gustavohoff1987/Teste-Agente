// Sessão temporária: nenhum resultado, token ou histórico em armazenamento persistente.
const API = import.meta.env.VITE_API_BASE_URL || "";
let token = "";
let creating: Promise<string> | null = null;
let revision = 0;
let ending = false;

function ended(reason: "unavailable" | "closed" = "unavailable") {
  if (ending) return;
  ending = true;
  token = "";
  try {
    sessionStorage.removeItem("adt:privacy-accepted:v1");
    // Somente um motivo de descarte, sem token, dados, IDs ou histórico persistidos.
    sessionStorage.setItem("adt:session-ended", reason);
  } catch { /* sem armazenamento */ }
  window.location.reload(); // descarta também arquivos, resultados e histórico em memória da aba
}

async function ensureSession() {
  if (token) return token;
  if (!creating) creating = fetch(API + "/api/session", {method:"POST"}).then(async response => {
    if (!response.ok) throw new Error("Não foi possível iniciar a sessão temporária.");
    token = (await response.json()).token;
    return token;
  }).finally(() => { creating = null; });
  return creating;
}

export function contextRevision() { return revision; }

export function updateContextRevision() {
  revision += 1;
  if (token) void fetch(API + "/api/session/revision", {method:"POST",
    headers:{"Content-Type":"application/json", "X-ADT-Session":token},
    body:JSON.stringify({revision})}).then(response => {if (response.status === 410) ended();}).catch(() => {});
}

export async function sessionFetch(url: string, init?: RequestInit) {
  if (!/\/api\/(?:llm\/interpret|exploration\/interpret|analyze)/.test(url)) return fetch(url, init);
  const session = await ensureSession();
  const headers = new Headers(init?.headers);
  headers.set("X-ADT-Session", session);
  const response = await fetch(url, {...init, headers});
  if (response.status === 410) ended();
  return response;
}

export async function endSession() {
  if (token) {
    const response = await fetch(API + "/api/session/close", {method:"POST", headers:{"X-ADT-Session":token}});
    if (!response.ok) throw new Error("Não foi possível encerrar a sessão no servidor. Tente novamente.");
  }
  ended("closed");
}

export function trackSession() {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let disposed = false;
  async function status(expiring = false) {
    if (disposed || !token) return;
    try {
      const response = await fetch(API + "/api/session", {headers:{"X-ADT-Session":token}});
      if (response.status === 410) { ended(); return; }
      if (response.ok) {
        const state = await response.json();
        clearTimeout(timer);
        // Uma requisição pode ter renovado a sessão desde a última consulta.
        timer = setTimeout(() => { void status(true); }, Math.max(0, state.expires_in * 1000));
      }
    } catch { if (expiring) ended(); /* não renova prazo por indisponibilidade da rede */ }
  }
  function interaction(event: Event) {
    if (!event.isTrusted) return;
    const target = event.target as HTMLElement;
    if (event.type === "click" && !target.closest("button, summary, a")) return;
    if (event.type === "change" && !target.closest("input, select")) return;
    const kind = event.type === "change" ? "MUDANCA_PARAMETRO" : "NAVEGACAO_CONTROLE_EFETIVO";
    void ensureSession().then(session => fetch(API + "/api/session/interact", {method:"POST",
      headers:{"Content-Type":"application/json","X-ADT-Session":session},body:JSON.stringify({kind})}))
      .then(response => { if(response.status === 410) ended(); else void status(); }).catch(() => {});
  }
  document.addEventListener("click", interaction);
  document.addEventListener("change", interaction);
  const poll = setInterval(() => { void status(); }, 30000); // consultar não renova a sessão
  return () => {disposed=true; clearInterval(poll); clearTimeout(timer);
    document.removeEventListener("click", interaction); document.removeEventListener("change", interaction);};
}
