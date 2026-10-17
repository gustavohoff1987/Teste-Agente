"""Contexto temporário do processo; tokens opacos, origem local e descarte por inatividade."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import secrets
import threading
import time

from fastapi import HTTPException

TIMEOUT = 1800
INTERACTIONS = frozenset(("ENVIO_MENSAGEM", "UPLOAD", "ESCOLHA_ARQUIVO", "ESCOLHA_PLANILHA", "CONFIRMACAO",
    "ALTERACAO_FILTRO_ANALITICO", "ALTERACAO_SELECAO_ANALITICA", "MUDANCA_PARAMETRO", "NAVEGACAO_CONTROLE_EFETIVO",
    "REVELACAO_EXPLICITA", "SOLICITACAO_RELATORIO", "EXPORTACAO"))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


@dataclass
class Session:
    touched: float
    revision: int = 0
    context: dict = field(default_factory=dict)
    dialogue: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    events: list = field(default_factory=list)
    event_hash: str = ""
    size: int = 0


class SessionStore:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.sessions = {}

    def cleanup(self):
        with self.lock:
            for token in list(self.sessions):
                if self.clock() - self.sessions[token].touched >= TIMEOUT:
                    del self.sessions[token]

    def create(self):
        with self.lock:
            self.cleanup()
            if len(self.sessions) >= 128:
                raise HTTPException(503, "Limite de sessões temporárias atingido. Tente novamente mais tarde.")
            token = secrets.token_urlsafe(32)
            self.sessions[token] = Session(self.clock())
            return {"token": token, "expires_in": TIMEOUT, "snapshot": "SPEC-1.2.4/APT-20261016"}

    def _get(self, token):
        self.cleanup()
        if not token or token not in self.sessions:
            raise HTTPException(410, "A sessão terminou. Inicie uma nova sessão.")
        return self.sessions[token]

    def status(self, token):
        with self.lock:
            session = self._get(token)
            return {"expires_in": max(0, TIMEOUT - (self.clock() - session.touched)), "revision": session.revision}

    def close(self, token):
        with self.lock:
            self.sessions.pop(token, None)

    def event(self, token, kind):
        if not isinstance(kind, str) or kind not in INTERACTIONS:
            raise HTTPException(422, "Interação de sessão não autorizada.")
        with self.lock:
            session = self._get(token)
            session.touched = self.clock()
            self._audit(session, kind)
            return self.status(token)

    def _audit(self, session, kind):
        # Somente tipos/revisões; nunca mensagem, valor, campo, arquivo ou token.
        previous = session.event_hash
        event = {"kind": kind, "revision": session.revision, "previous": previous}
        event["hash"] = fingerprint(event)
        session.event_hash = event["hash"]
        session.events.append(event)
        # Encadeamento conservado pelo hash anterior; sem log persistente de dados.
        session.events[:] = session.events[-256:]

    def revision(self, token, revision):
        if type(revision) is not int or not 0 <= revision <= 2**53 - 1:
            raise HTTPException(422, "Revisão de contexto inválida.")
        with self.lock:
            session = self._get(token)
            session.revision = max(session.revision, revision)

    def capture(self, token, revision, context):
        with self.lock:
            self.revision(token, revision)
            session = self._get(token)
            if revision != session.revision:
                raise HTTPException(409, "A seleção mudou. Envie o pedido no contexto atual.")
            if session.context.get("source") != context.get("source"):
                session.dialogue.clear()
            session.context = deepcopy(context)
            self._audit(session, "EV-CAPTURA-SELECAO")
            return {"revision": revision, "context": deepcopy(context), "dialogue": deepcopy(session.dialogue)}

    def current(self, token, revision):
        with self.lock:
            session = self._get(token)
            if revision != session.revision:
                self._audit(session, "EV-RETORNO_TARDIO_DESCARTADO")
                raise HTTPException(409, "O contexto mudou durante a resposta. Envie novamente com a seleção atual.")

    def remember(self, token, revision, answer):
        with self.lock:
            self.current(token, revision)
            session = self._get(token)
            proposal = answer.get("proposal", {})
            if proposal.get("operation"):
                session.dialogue.update(operation=proposal["operation"], indicator=proposal.get("indicator"))
            docs = answer.get("documentation", [])
            if docs:
                session.dialogue["document"] = docs[0]["id_doc"]
                session.dialogue["referent"] = "document"
            if answer.get("result_reference"):
                session.dialogue["referent"] = "result"
            self._audit(session, "EV-VALIDACAO-SAIDA")

    def record_result(self, token, revision, result, context):
        with self.lock:
            self.current(token, revision)
            session = self._get(token)
            size = len(json.dumps(result, ensure_ascii=False, default=str).encode())
            # Falhar somente a referência conversacional; nunca perder o cálculo.
            if len(session.results) >= 64 or session.size + size > 32 * 1024 * 1024 or sum(
                    s.size for s in self.sessions.values()) + size > 256 * 1024 * 1024:
                return False
            session.results[result["result_id"]] = {"result": deepcopy(result), "context": deepcopy(context),
                                                   "integrity": fingerprint(result)}
            session.size += size
            self._audit(session, "RESULTADO_CALCULADO")
            return True

    def result(self, token, result_id):
        with self.lock:
            record = self._get(token).results.get(result_id)
            if record is None:
                raise HTTPException(404, "Resultado não encontrado nesta sessão. Nenhum valor do navegador foi utilizado.")
            if fingerprint(record["result"]) != record["integrity"]:
                raise HTTPException(409, "A integridade do resultado não pôde ser confirmada.")
            return deepcopy(record)


sessions = SessionStore()


@asynccontextmanager
async def lifespan(_app):
    async def expire():
        while True:
            await asyncio.sleep(15)
            sessions.cleanup()
    task = asyncio.create_task(expire())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        sessions.sessions.clear()
