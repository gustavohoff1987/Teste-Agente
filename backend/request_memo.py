"""Memorização restrita a uma requisição HTTP, para funções puras sobre o mesmo quadro.

Fora de uma requisição (testes, scripts, instalador) nada é memorizado. Cada entrada guarda
o próprio quadro, de modo que seu identificador não pode ser reaproveitado por outro objeto
enquanto a requisição durar. Resultados memorizados são compartilhados entre os chamadores
da mesma requisição e tratados como somente leitura.
"""
import contextvars
import functools
import json

_MEMO = contextvars.ContextVar("adt_request_memo", default=None)


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
