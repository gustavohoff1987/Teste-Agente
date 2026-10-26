"""Resposta da conversa redigida pelo Gemini e conferida antes da exibição (Frente III; RQ-SIN-01 a RQ-SIN-10; Adendo
PAR-20261026 da SPEC), 26/10/2026.

Gemini conversa, motor decide. Para cada pergunta de conversa (sobre o resultado em exibição, um conceito, a tela, uma
verificação, o funcionamento do agente), o gestor de diálogo e o catálogo produzem primeiro a resposta verificada, que é
também a reserva; o Gemini recebe o cartão do contexto (contexto_conversa.py), com essa resposta e as fichas de método, e
redige a resposta com as palavras dele. O texto só aparece se passar na conferência de fidelidade (fidelidade.py); com
violação, nova tentativa com a lista das violações, até 2 regenerações (RQ-SIN-05); persistindo, aparece a reserva
verificada, com a mensagem fixa de TPL-08. Sem o provedor (sem chave, em espera de cota, fora do ar), aparece a reserva,
sem chamada. Os comandos do gráfico, as decisões de autorização, os cálculos e as validações continuam determinísticos.

Uma chamada por pergunta, em geral: quando a interpretação já veio do Gemini com o campo `resposta` (contrato unificado),
esse texto é conferido primeiro e só uma violação leva a nova chamada. ADT_CONVERSA_GEMINI=0 desliga a redação.
"""
from __future__ import annotations

import json
import logging
import os

import fidelidade
import llm_bridge
from document_catalog import DocumentationError, materialize

TENTATIVAS = 3  # a primeira e até 2 regenerações (RQ-SIN-05, DA-26)
REGISTROS = ("objetivo", "simples", "didatico", "tecnico")


def ativa() -> bool:
    """A redação pelo Gemini está ligada e o provedor pode ser chamado agora (chave e nenhuma espera de cota)."""
    return os.getenv("ADT_CONVERSA_GEMINI", "1").strip() != "0" and llm_bridge.disponivel()


def _tpl08() -> str:
    try:
        return materialize("DOC:TPL-08", form="mensagem", evidence="REGENERACAO_ESGOTADA")["text"]
    except DocumentationError:
        return ""


def _entradas(mensagem_preparada: str, contexto: dict, registro: str, violacoes: list[str]) -> list[str]:
    entradas = ["CONTEXTO_DA_CONVERSA: " + json.dumps({**contexto["cartao"], "conversa_recente": contexto["conversa_recente"]},
                                                      ensure_ascii=False),
                "REGISTRO_PEDIDO: " + (registro if registro in REGISTROS else "objetivo")]
    if violacoes:
        entradas.append("VIOLACOES_DA_TENTATIVA_ANTERIOR: " + "; ".join(violacoes[:8]))
    entradas.append("MENSAGEM: " + mensagem_preparada)
    return entradas


def _aceita(texto: str, refs: fidelidade.Referencias, tentativas: int) -> dict:
    return {"texto": fidelidade.texto_para_exibir(texto, refs), "origem": "GEMINI_VALIDADO", "tentativas": tentativas}


async def redigir(*, contexto: dict, refs: fidelidade.Referencias, reserva: str, registro: str = "objetivo",
                  rascunho: str | None = None) -> dict:
    """O texto da resposta: o do Gemini, conferido, ou a reserva verificada. Devolve texto, origem
    (GEMINI_VALIDADO ou DETERMINISTICA), tentativas e, na reserva, o motivo (conferência ou a causa da indisponibilidade).
    `rascunho` é o campo `resposta` que já veio com a interpretação (conferido sem nova chamada)."""
    tentativas, violacoes = 0, []
    if rascunho and rascunho.strip():
        tentativas = 1
        violacoes = fidelidade.conferir(rascunho, refs)
        if not violacoes:
            return _aceita(rascunho, refs, tentativas)
        llm_bridge.contar("regeneracao")
    while tentativas < TENTATIVAS:
        if not ativa():
            return {"texto": reserva, "origem": "DETERMINISTICA", "tentativas": tentativas,
                    "motivo": "indisponivel" if tentativas == 0 else "conferencia"}
        tentativas += 1
        try:
            saida = await llm_bridge.generate_structured(llm_bridge.SISTEMA_DA_RESPOSTA,
                                                         _entradas(contexto["mensagem"], contexto, registro, violacoes),
                                                         llm_bridge.ESQUEMA_DA_RESPOSTA)
        except llm_bridge.LLMError as exc:
            if exc.causa == "contrato":
                violacoes = ["a resposta não veio no JSON do esquema"]
                if tentativas < TENTATIVAS:
                    llm_bridge.contar("regeneracao")
                continue
            # Cota, rede ou configuração: a reserva verificada responde, sem nova tentativa.
            return {"texto": reserva, "origem": "DETERMINISTICA", "tentativas": tentativas, "motivo": exc.causa}
        texto = saida.get("resposta") if isinstance(saida, dict) else None
        violacoes = fidelidade.conferir(texto if isinstance(texto, str) else "", refs)
        if not violacoes:
            return _aceita(texto, refs, tentativas)
        logging.getLogger(__name__).info("Redação do Gemini recusada na conferência: %s", "; ".join(violacoes)[:400])
        if tentativas < TENTATIVAS:
            llm_bridge.contar("regeneracao")
    llm_bridge.contar("contrato")
    aviso = _tpl08()
    return {"texto": reserva + ("\n\n" + aviso if aviso else ""), "origem": "DETERMINISTICA", "tentativas": tentativas,
            "motivo": "conferencia", "violacoes": violacoes}
