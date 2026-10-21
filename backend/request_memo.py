"""Memorização restrita a uma requisição HTTP, para funções puras sobre o mesmo quadro.

Fora de uma requisição (testes, scripts, instalador) nada é memorizado. Cada entrada guarda
o próprio quadro, de modo que seu identificador não pode ser reaproveitado por outro objeto
enquanto a requisição durar. Resultados memorizados são compartilhados entre os chamadores
da mesma requisição e tratados como somente leitura.

Única exceção à duração da requisição: a cópia íntegra de uma fonte imutável (a base Brasil verificada
pelo manifesto, marcada com mark_source). Sobre ela, as funções @per_source reaproveitam o resultado de
requisições anteriores da mesma versão; cada requisição recebe a sua cópia. Arquivos importados nunca
são marcados: nada deles persiste além da requisição.
"""
from collections import OrderedDict
import contextvars
import functools
import json
import pickle
import threading

_MEMO = contextvars.ContextVar("adt_request_memo", default=None)
_SHARED: OrderedDict = OrderedDict()  # chave -> (forma guardada, bytes)
_SHARED_LOCK = threading.Lock()
SHARED_LIMIT_BYTES = 96 * 1024 * 1024  # resultados guardados entre requisições; os menos usados saem primeiro
_shared_bytes = 0
_MISSING = object()


class RequestMemoMiddleware:
    """Abre um espaço de memorização novo por requisição e o descarta ao final."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = _MEMO.set({})
        try:
            await self.app(scope, receive, send)
        finally:
            _MEMO.reset(token)


def per_request(function):
    @functools.wraps(function)
    def wrapper(frame, *args, **kwargs):
        memo = _MEMO.get()
        if memo is None:
            return function(frame, *args, **kwargs)
        key = (function.__qualname__, id(frame), json.dumps([args, kwargs], sort_keys=True, default=str))
        hit = memo.get(key)
        if hit is not None and hit[0] is frame:
            return hit[1]
        value = function(frame, *args, **kwargs)  # exceções não são memorizadas
        memo[key] = (frame, value)
        return value
    return wrapper


def request_value(key, compute, anchor=None):
    """Valor calculado uma vez por requisição e lido por todos os chamadores; fora dela, recalculado.

    anchor é o objeto cujo id compõe a chave (ex.: o quadro): fica guardado com o valor para que o id
    não seja reaproveitado por outro objeto durante a requisição."""
    memo = _MEMO.get()
    if memo is None:
        return compute()
    hit = memo.get(key)
    if hit is not None and hit[0] is anchor:
        return hit[1]
    value = compute()  # exceções não são memorizadas
    memo[key] = (anchor, value)
    return value


def mark_source(frame, identity):
    """Nesta requisição, frame é a cópia íntegra da fonte imutável identity (arquivo e versão SHA-256).

    Só o próprio objeto vale: recortes e cópias derivadas dele não são a fonte e seguem a memória da requisição."""
    memo = _MEMO.get()
    if memo is not None:
        memo[("source", id(frame))] = (frame, identity)


def _source(memo, frame):
    hit = memo.get(("source", id(frame))) if memo is not None else None
    return hit[1] if hit is not None and hit[0] is frame else None


_IMMUTABLE = (str, int, float, bool, type(None), frozenset, bytes)


def _store(value):
    """Forma guardada: o próprio valor imutável ou sua serialização (desserializar é mais rápido que deepcopy)."""
    return (False, value) if isinstance(value, _IMMUTABLE) else (True, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))


def _size(stored):
    serialized, value = stored
    if serialized or isinstance(value, (str, bytes)):
        return len(value)
    if isinstance(value, frozenset):
        return sum(len(item) if isinstance(item, (str, bytes)) else 64 for item in value)
    return 64


def clear_shared():
    """Esvazia a memória entre requisições (isolamento dos testes)."""
    global _shared_bytes
    with _SHARED_LOCK:
        _SHARED.clear()
        _shared_bytes = 0


def _private(stored):
    """Cópia própria de quem pede, a partir da forma guardada."""
    serialized, value = stored
    return pickle.loads(value) if serialized else value


def per_source(extra=None, shared=False):
    """Sobre a cópia íntegra de uma fonte imutável, o resultado vale entre requisições; nos demais quadros, nada muda.

    extra() devolve as demais entradas versionadas lidas pela função (ex.: a camada de coordenadas), que
    entram na chave. Argumentos que não são JSON dispensam a memória. Cada chamada recebe cópia própria do
    resultado guardado; com shared=True (funções já @per_request, de resultado só lido), as chamadas da mesma
    requisição compartilham o mesmo objeto, como antes."""
    def decorate(function):
        fallback = per_request(function) if shared else function

        @functools.wraps(function)
        def wrapper(frame, *args, **kwargs):
            memo = _MEMO.get()
            identity = _source(memo, frame)
            if identity is None:
                return fallback(frame, *args, **kwargs)
            try:
                arguments = json.dumps([args, kwargs], sort_keys=True)
            except TypeError:
                return fallback(frame, *args, **kwargs)
            key = (function.__module__, function.__qualname__, identity, extra() if extra else None, arguments)
            hit = memo.get(key) if shared else None
            if hit is not None and hit[0] is frame:
                return hit[1]  # mesma requisição: o mesmo objeto, como em per_request
            global _shared_bytes
            with _SHARED_LOCK:
                entry = _SHARED.get(key, _MISSING)
                if entry is not _MISSING:
                    _SHARED.move_to_end(key)
            if entry is _MISSING:
                value = function(frame, *args, **kwargs)  # exceções não são memorizadas
                try:
                    stored = _store(value)
                except (pickle.PicklingError, TypeError, AttributeError):
                    stored = None  # resultado que não se serializa: entregue sem guardar, como antes
                size = _size(stored) if stored is not None else SHARED_LIMIT_BYTES + 1
                if size <= SHARED_LIMIT_BYTES:
                    with _SHARED_LOCK:
                        if key not in _SHARED:
                            _SHARED[key] = (stored, size)
                            _shared_bytes += size
                        while _shared_bytes > SHARED_LIMIT_BYTES and _SHARED:
                            _shared_bytes -= _SHARED.popitem(last=False)[1][1]
            else:
                value = _private(entry[0])
            if shared:
                memo[key] = (frame, value)
            return value
        return wrapper
    return decorate
