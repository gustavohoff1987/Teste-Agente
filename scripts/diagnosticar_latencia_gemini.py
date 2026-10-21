"""Medição manual de latência, com chamadas reais explicitamente solicitadas.

Não é teste nem roda no CI. Usa uma frase sintética fixa, sem base ou sessão do usuário.
Faz seis chamadas sequenciais ao Gemini, alternando a presença dos exemplos recuperados.
Não grava credenciais, corpos de pedidos/respostas nem informações do transporte.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import httpx  # noqa: E402
import conversation_library  # noqa: E402
import llm_bridge  # noqa: E402

MESSAGE = "Quero comparar a quantidade de profissionais entre dois períodos."
HTTP_CLIENT = httpx.AsyncClient


async def measure_pair_request(examples: str, trace: dict | None, pair: int, position: int) -> dict:
    metrics = {"par": pair, "posicao": position, "biblioteca": bool(examples),
               "exemplos": len((trace or {}).get("exemplos", [])) if examples else 0,
               "caracteres_exemplos": len(examples)}
    events = {}

    async def timing(event, info):
        # O conteúdo de info pode conter dados sensíveis; só o nome do evento é usado.
        events[event] = perf_counter()

    class MeasuredClient(HTTP_CLIENT):
        async def post(self, url, **kwargs):
            body = kwargs["json"]
            metrics["bytes_corpo_utf8"] = len(json.dumps(
                body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            response = await super().post(url, extensions={"trace": timing}, **kwargs)
            metrics["http"] = response.status_code
            if response.status_code == 200:
                data = response.json()
                usage = data.get("usageMetadata", {})
                metrics["tokens"] = {key: usage[key] for key in (
                    "promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount",
                    "totalTokenCount", "cachedContentTokenCount") if key in usage}
                metrics["termino"] = [c.get("finishReason") for c in data.get("candidates", [])]
            return response

    token = llm_bridge._EXAMPLES.set(examples)
    llm_bridge.httpx.AsyncClient = MeasuredClient
    started = perf_counter()
    try:
        llm_bridge._reserve_request()
        await llm_bridge._call_gemini(
            [llm_bridge._sanitize(MESSAGE)], llm_bridge._configured_model(),
            os.environ["GEMINI_API_KEY"].strip())
        metrics["resultado"] = "concluido"
    except llm_bridge.LLMError as error:
        metrics["resultado"] = "falha"
        metrics["status_aplicacao"] = error.status
        metrics["tipo_causa"] = type(error.__cause__).__name__
    finally:
        metrics["total_s"] = round(perf_counter() - started, 4)
        llm_bridge.httpx.AsyncClient = HTTP_CLIENT
        llm_bridge._EXAMPLES.reset(token)
    for label, event in (
        ("tcp_s", "connection.connect_tcp"), ("tls_s", "connection.start_tls"),
        ("envio_corpo_s", "http11.send_request_body"),
        ("espera_cabecalhos_s", "http11.receive_response_headers"),
        ("leitura_corpo_s", "http11.receive_response_body"),
    ):
        if event + ".started" in events and event + ".complete" in events:
            metrics[label] = round(events[event + ".complete"] - events[event + ".started"], 4)
    return metrics


async def main() -> int:
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        print("Gemini não configurado; nenhuma chamada realizada.")
        return 1
    if not conversation_library.enabled():
        print("A biblioteca precisa estar habilitada neste processo para a comparação.")
        return 1
    request = llm_bridge.ChatRequest(message=MESSAGE)
    started = perf_counter()
    block, trace = llm_bridge._library_examples(request, None, None, with_base=False)
    cold_ms = (perf_counter() - started) * 1000
    if not block:
        print("Nenhum exemplo recuperado; comparação cancelada sem chamadas.")
        return 1
    warm = []
    for _ in range(30):
        started = perf_counter()
        llm_bridge._library_examples(request, None, None, with_base=False)
        warm.append((perf_counter() - started) * 1000)
    print(json.dumps({
        "tipo": "preparacao", "data": datetime.now(timezone(timedelta(hours=-3))).isoformat(),
        "modelo": llm_bridge._configured_model(), "mensagem_sintetica": MESSAGE,
        "biblioteca": trace, "limite_exemplos": conversation_library.examples_per_request(),
        "caracteres_exemplos": len(block), "carga_selecao_mascara_ms": round(cold_ms, 3),
        "selecao_mascara_aquecida_mediana_ms": round(statistics.median(warm), 3),
        "selecao_mascara_aquecida_max_ms": round(max(warm), 3), "amostras_locais": len(warm),
    }, ensure_ascii=False), flush=True)
    for pair in range(1, 4):
        order = (False, True) if pair % 2 else (True, False)
        for position, enabled in enumerate(order, 1):
            result = await measure_pair_request(block if enabled else "", trace, pair, position)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if result.get("http") in (401, 403, 429) or result.get("status_aplicacao") == 429:
                return 1  # Não insiste em credencial recusada ou cota esgotada.
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
