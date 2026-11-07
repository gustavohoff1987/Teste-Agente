"""Referência em processo dentro da imagem do contêiner (job "conteiner" do CI; medir_conteiner.py, desde 07/11/2026).

Roda com `docker run` da própria imagem medida (comparar_respostas.comando_da_referencia_na_imagem), com o commit montado só
para leitura em /src. O código e os dados vêm de /src, e o Python, as bibliotecas e a libm são os da imagem. A resposta do
contêiner pelo HTTP deve ser idêntica, bit a bit, à desta referência.

Lê da entrada padrão {"inspecao": formulário do exame da base, "pedidos": [...]} (comparar_respostas.pedidos_para_json).
Escreve na saída padrão, numa só linha JSON, o ambiente, a resposta do exame e a de cada pedido, na ordem. O que o backend
imprimir vai para a saída de erros. Não chama o Gemini (chave vazia, sem rede) e não grava nada.
"""
import json
import os
import sys
from pathlib import Path

saida = sys.stdout
sys.stdout = sys.stderr  # a saída padrão leva só o JSON do fim

AQUI = Path(__file__).resolve().parent
sys.path[:0] = [str(AQUI.parents[1] / "backend"), str(AQUI)]
os.environ["GEMINI_API_KEY"] = ""
os.environ["ADT_AQUECIMENTO"] = "0"

import comparar_respostas as C  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

if not C.codigo_do_commit(main.__file__):
    raise SystemExit(f"a referência importou {main.__file__}, e não o código do commit em {C.RAIZ_NA_IMAGEM}/backend")

entrada = json.loads(sys.stdin.buffer.read().decode("utf-8"))  # UTF-8 qualquer que seja a localidade da imagem
cliente = TestClient(main.app)


def responder(rota: str, formulario: dict, arquivos=None) -> dict:
    resposta = cliente.post(rota, data=formulario, files=C.arquivos_de_json(arquivos))
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = None
    return {"status": resposta.status_code, "json": corpo, "texto": None if corpo is not None else resposta.text[:300]}


resultado = {"ambiente": C.ambiente(main.__file__), "inspecao": responder("/api/inspect", entrada["inspecao"]),
             "respostas": [responder(pedido["rota"], pedido["formulario"], pedido["arquivos"])
                           for pedido in entrada["pedidos"]]}
saida.buffer.write(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))
saida.flush()
