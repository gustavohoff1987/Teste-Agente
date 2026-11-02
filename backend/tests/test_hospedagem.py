"""Hospedagem no Cloud Run com a interface no GitHub Pages (01/11/2026; Docs/implantacao/).

Confere: o limite de 15 MB (15.000.000 bytes) no backend, independente da tela; a recusa das planilhas malformadas e das com
expansão desproporcional; as vagas das operações pesadas, com a resposta de ocupado legível pelo navegador e o pedido
abandonado na fila; os pedidos por sessão, sem encerrar a sessão; o CORS restrito; a documentação da API desligável; o
aquecimento antes de a porta abrir; o endereço de teste do provedor só na própria máquina; e o provedor simulado por HTTP, no
formato real da API (cota por minuto e por dia, chave inválida e recusada, falha e saída fora do contrato).
"""
import asyncio
import io
import os
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import carga
import llm_bridge
import main
import serve_gemini_http

client = TestClient(main.app)
BACKEND = Path(main.__file__).resolve().parent
ORIGEM = "http://localhost:5173"
CABECALHO = "territorio;periodo;categoria;quantidade;observacao\n"


def csv_com(tamanho: int) -> bytes:
    """CSV de exatamente `tamanho` bytes, com poucas linhas longas (a leitura fica rápida)."""
    nota = "x" * 2000
    linhas, total, i = [CABECALHO], len(CABECALHO), 0
    while True:
        linha = f"T{i};2024;MEDICINA;{i % 50 + 1};{nota}\n"
        if total + len(linha) > tamanho:
            break
        linhas.append(linha)
        total += len(linha)
        i += 1
    linhas[-1] = linhas[-1][:-1] + "x" * (tamanho - total) + "\n"
    dados = "".join(linhas).encode("ascii")
    assert len(dados) == tamanho
    return dados


def inspecionar(nome, conteudo, **cabecalhos):
    return client.post("/api/inspect", files={"file": (nome, conteudo)}, headers=cabecalhos)


def xlsx_valido() -> bytes:
    livro = Workbook()
    livro.active.append(["territorio", "periodo", "quantidade"])
    livro.active.append(["Alfa", 2024, 10])
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def xlsx_expandido(megabytes: int) -> bytes:
    """Pacote XLSX pequeno cujo conteúdo, descompactado, tem `megabytes` MB."""
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr("[Content_Types].xml", "<Types/>")
        with pacote.open("xl/worksheets/sheet1.xml", "w") as folha:
            bloco = b"0" * (1024 * 1024)
            for _ in range(megabytes):
                folha.write(bloco)
    return saida.getvalue()


# ---------------------------------------------------------------------------------------------- 15 MB e planilhas

def test_o_limite_do_arquivo_e_15_mb_exatos_conferido_pelo_backend():
    assert carga.MAX_UPLOAD_BYTES == main.MAX_UPLOAD_BYTES == 15_000_000
    aceito = inspecionar("limite.csv", csv_com(15_000_000))
    assert aceito.status_code == 200, aceito.text[:500]
    assert aceito.json()["row_count"] > 7000
    recusado = inspecionar("limite.csv", csv_com(15_000_001))
    assert recusado.status_code == 413
    assert recusado.json()["detail"] == carga.TEXTO_ARQUIVO_GRANDE == "Arquivo acima do limite de 15 MB; nenhum dado foi analisado."
    # A leitura direta do arquivo aplica o mesmo limite; as fontes versionadas da base do Brasil têm o limite próprio.
    with pytest.raises(ValueError, match="limite de 15 MB"):
        main.read_dataset(csv_com(15_000_001), "direto.csv")


def test_pedido_maior_que_o_limite_e_recusado_antes_de_qualquer_leitura(monkeypatch):
    def proibido(*_args, **_kwargs):
        raise AssertionError("o arquivo grande não deveria ser lido")
    monkeypatch.setattr(main, "_dataset_do_pedido", proibido)
    grande = b"x" * (carga.LIMITE_DO_PEDIDO + 1)
    resposta = inspecionar("grande.csv", grande, Origin=ORIGEM)
    assert resposta.status_code == 413
    assert resposta.json() == {"detail": carga.TEXTO_ARQUIVO_GRANDE}
    assert resposta.headers["access-control-allow-origin"] == ORIGEM  # legível pelo navegador


def test_xlsx_com_expansao_desproporcional_e_recusado_antes_da_leitura_com_a_tpl_13():
    bomba = xlsx_expandido(20)
    assert len(bomba) < 200_000
    resposta = inspecionar("bomba.xlsx", bomba)
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert detalhe.startswith("A planilha cresce demais quando é aberta") and carga.TPL_13 in detalhe
    assert "20,0 MB" in detalhe or "21,0 MB" in detalhe
    carga.conferir_xlsx(xlsx_valido())  # a planilha comum passa
    assert inspecionar("comum.xlsx", xlsx_valido()).status_code == 200


@pytest.mark.parametrize("conteudo", [b"isto nao e uma planilha", b"PK\x03\x04quebrado", xlsx_valido()[:400]])
def test_xlsx_malformado_recebe_a_mensagem_de_arquivo_invalido(conteudo):
    resposta = inspecionar("quebrado.xlsx", conteudo)
    assert resposta.status_code == 422
    assert resposta.json()["detail"].startswith("Não foi possível interpretar este arquivo Excel.")


def test_csv_com_celulas_demais_e_recusado_inteiro(monkeypatch):
    monkeypatch.setattr(carga, "CSV_CELULAS_MAXIMAS", 100)
    linhas = "territorio;quantidade\n" + "".join(f"T{i};{i}\n" for i in range(60))
    resposta = inspecionar("celulas.csv", linhas.encode())
    assert resposta.status_code == 422
    assert resposta.json()["detail"].startswith("A planilha tem células demais para esta versão: mais de 100 células.")
    assert carga.TPL_13 in resposta.json()["detail"]
    pequeno = "territorio;quantidade\n" + "".join(f"T{i};{i}\n" for i in range(40))
    assert inspecionar("pequeno.csv", pequeno.encode()).status_code == 200


# ---------------------------------------------------------------------------------------------- vagas e ocupado

def test_vagas_em_ordem_de_chegada_com_fila_espera_e_desistencia():
    async def cenario():
        vagas = carga.Vagas(total=1, fila=1, espera=0.3)
        assert await vagas.entrar()
        segundo = asyncio.ensure_future(vagas.entrar())
        await asyncio.sleep(0.02)
        assert vagas.estado()["na_fila"] == 1
        assert await vagas.entrar() is False  # fila cheia: recusa na hora
        vagas.sair()
        assert await segundo is True  # a vaga liberada vai para quem esperava
        assert await vagas.entrar() is False  # espera esgotada sem vaga
        assert await vagas.entrar(desistiu=lambda: True) is False  # abandonado na fila
        estado = vagas.estado()
        assert (estado["recusas"], estado["abandonos"], estado["na_fila"], estado["em_uso"]) == (2, 1, 0, 1)
        vagas.sair()
        assert await vagas.entrar() is True
    asyncio.run(cenario())


def _pedido_retido(monkeypatch):
    """Faz o primeiro pedido do painel esperar até `liberar` (os seguintes seguem direto); devolve (entrou, liberar)."""
    entrou, liberar = threading.Event(), threading.Event()
    original = main._panel_request

    def retido(*args, **kwargs):
        if not entrou.is_set():
            entrou.set()
            liberar.wait(20)
        return original(*args, **kwargs)
    monkeypatch.setattr(main, "_panel_request", retido)
    return entrou, liberar


def test_sem_vaga_o_pedido_pesado_recebe_ocupado_legivel_e_a_saude_continua_respondendo(monkeypatch):
    monkeypatch.setattr(carga.VAGAS, "total", 1)
    monkeypatch.setattr(carga.VAGAS, "fila_maxima", 0)
    entrou, liberar = _pedido_retido(monkeypatch)
    resultado = {}
    tarefa = threading.Thread(target=lambda: resultado.update(primeiro=TestClient(main.app).post("/api/painel", data={})))
    tarefa.start()
    try:
        assert entrou.wait(20)
        segundo = client.post("/api/painel/mapa", data={}, headers={"Origin": ORIGEM})
        assert segundo.status_code == 503
        assert segundo.json() == {"detail": carga.TEXTO_OCUPADO, "ocupado": True, "tente_em": carga.TENTE_EM_SEGUNDOS}
        assert segundo.headers["access-control-allow-origin"] == ORIGEM
        assert segundo.headers["retry-after"] == str(carga.TENTE_EM_SEGUNDOS)
        # A operação pesada corre fora do laço de eventos: a saúde e a sessão respondem enquanto ela dura.
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.post("/api/session").status_code == 200
    finally:
        liberar.set()
        tarefa.join(30)
    assert resultado["primeiro"].status_code == 422  # o pedido retido seguiu normalmente, com a vaga dele


def test_pedidos_demais_da_mesma_sessao_recusam_so_o_novo_sem_encerrar_a_sessao(monkeypatch):
    monkeypatch.setattr(carga, "POR_SESSAO", 1)
    monkeypatch.setattr(carga.VAGAS, "total", 4)
    token = client.post("/api/session").json()["token"]
    entrou, liberar = _pedido_retido(monkeypatch)
    resultado = {}
    tarefa = threading.Thread(target=lambda: resultado.update(primeiro=TestClient(main.app).post(
        "/api/painel", data={}, headers={"X-ADT-Session": token})))
    tarefa.start()
    try:
        assert entrou.wait(20)
        mesma = client.post("/api/painel/territorios", data={}, headers={"X-ADT-Session": token, "Origin": ORIGEM})
        assert mesma.status_code == 503 and mesma.json()["ocupado"] is True
        assert mesma.json()["detail"] == carga.TEXTO_SESSAO_OCUPADA
        assert mesma.headers["access-control-allow-origin"] == ORIGEM
        outra = client.post("/api/session").json()["token"]
        assert client.post("/api/painel/territorios", data={}, headers={"X-ADT-Session": outra}).status_code == 422
        assert client.get("/api/session", headers={"X-ADT-Session": token}).status_code == 200  # a sessão continua
    finally:
        liberar.set()
        tarefa.join(30)
    assert resultado["primeiro"].status_code == 422
    assert client.post("/api/painel/territorios", data={}, headers={"X-ADT-Session": token}).status_code == 422


def test_pedido_abandonado_na_fila_sai_sem_calcular():
    async def cenario():
        chamadas, enviados = [], []

        async def app(scope, receive, send):
            chamadas.append(scope["path"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"{}"})
        vagas = carga.Vagas(total=1, fila=4, espera=5)
        assert await vagas.entrar()  # a vaga já está com outro pedido
        protecao = carga.ProtecaoDeCarga(app, vagas=vagas)
        mensagens = [{"type": "http.request", "body": b"a=1", "more_body": False}]
        desconectou = asyncio.Event()

        async def receive():
            if mensagens:
                return mensagens.pop(0)
            await desconectou.wait()
            return {"type": "http.disconnect"}

        async def send(mensagem):
            enviados.append(mensagem)
        escopo = {"type": "http", "path": "/api/painel", "method": "POST", "headers": [(b"content-length", b"3")]}
        tarefa = asyncio.ensure_future(protecao(escopo, receive, send))
        await asyncio.sleep(0.1)
        assert vagas.estado()["na_fila"] == 1
        desconectou.set()
        await asyncio.wait_for(tarefa, 2)
        assert chamadas == [] and enviados == []
        assert vagas.estado()["abandonos"] == 1 and vagas.estado()["na_fila"] == 0
    asyncio.run(cenario())


# ---------------------------------------------------------------------------------------------- CORS, documentação, partida

def test_cors_so_da_origem_autorizada_e_com_os_cabecalhos_da_interface():
    preverificacao = {"Origin": ORIGEM, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "x-adt-session"}
    permitido = client.options("/api/session", headers=preverificacao)
    assert permitido.status_code == 200
    assert permitido.headers["access-control-allow-origin"] == ORIGEM
    assert "x-adt-session" in permitido.headers["access-control-allow-headers"].lower()
    assert permitido.headers["access-control-max-age"] == "7200"
    assert client.options("/api/session", headers={**preverificacao, "Origin": "https://exemplo.invalid"}).status_code == 400
    assert client.options("/api/session", headers={**preverificacao, "Access-Control-Request-Headers": "x-outro"}).status_code == 400
    estranho = client.get("/api/health", headers={"Origin": "https://exemplo.invalid"})
    assert estranho.status_code == 200 and "access-control-allow-origin" not in estranho.headers


def test_origens_autorizadas_pela_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("ADT_ALLOWED_ORIGINS", " https://gustavohoff1987.github.io , ")
    assert main._origens_autorizadas() == ["https://gustavohoff1987.github.io"]
    monkeypatch.delenv("ADT_ALLOWED_ORIGINS")
    assert main._origens_autorizadas() == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_documentacao_da_api_desligada_na_producao_e_ligada_no_desenvolvimento():
    codigo = ("import os; os.environ['ADT_DOCUMENTACAO_DA_API'] = '0'; os.environ['ADT_AQUECIMENTO'] = '0'\n"
              "from fastapi.testclient import TestClient\nimport main\nc = TestClient(main.app)\n"
              "print(*[c.get(p).status_code for p in ('/docs', '/redoc', '/openapi.json', '/api/health')])")
    ambiente = {**os.environ, "GEMINI_API_KEY": "", "PYTHONPATH": str(BACKEND)}
    saida = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ambiente, capture_output=True, text=True,
                           timeout=180)
    assert saida.stdout.split() == ["404", "404", "404", "200"], saida.stderr[-3000:]
    assert client.get("/openapi.json").status_code == 200  # sem a variável, como no desenvolvimento


def test_endereco_de_teste_do_provedor_so_vale_na_propria_maquina(monkeypatch):
    padrao = llm_bridge.ENDERECO_DO_PROVEDOR
    assert padrao == "https://generativelanguage.googleapis.com"
    for valor, esperado in [("", padrao), ("http://127.0.0.1:18300", "http://127.0.0.1:18300"),
                            ("http://localhost:9/", "http://localhost:9"), ("https://127.0.0.1:1", padrao),
                            ("http://exemplo.com", padrao), ("http://127.0.0.1:1/outro", padrao),
                            ("http://127.0.0.1.exemplo.com", padrao), ("ftp://127.0.0.1", padrao)]:
        monkeypatch.setenv("ADT_GEMINI_ENDERECO_DE_TESTE", valor)
        assert llm_bridge._endereco() == esperado, valor


# ---------------------------------------------------------------------------------------------- provedor simulado por HTTP

@pytest.fixture
def gemini_http(monkeypatch):
    servidor = serve_gemini_http.iniciar(0)
    monkeypatch.setenv("ADT_GEMINI_ENDERECO_DE_TESTE", f"http://127.0.0.1:{servidor.server_address[1]}")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    yield servidor
    servidor.shutdown()
    servidor.server_close()


def _conversa(mensagem):
    return client.post("/api/llm/interpret", json={"message": mensagem})


def test_provedor_simulado_por_http_sucesso_e_contagem(gemini_http):
    resposta = _conversa("Analisar distribuição da densidade")
    assert resposta.status_code == 200 and resposta.json()["proposal"]["operation"] == "distribution"
    status = client.get("/api/llm/status").json()
    assert status["requests_used_today"] == 1 and status["disponivel"] is True and status["monitoramento"]["sucesso"] == 1
    assert "chave-de-teste" not in resposta.text + str(status)


@pytest.mark.parametrize("gatilho,causa,escopo,tipo", [
    ("simule cota minuto", "cota", "minuto", "cota"),
    ("simule cota dia", "cota", "dia", "cota"),
    ("simule chave invalida", "configuracao", "acesso", "indisponivel"),
    ("simule chave recusada", "configuracao", "acesso", "indisponivel"),
    ("simule erro 503", "indisponivel", "provedor", "indisponivel"),
])
def test_provedor_simulado_por_http_falhas_no_formato_real(gemini_http, gatilho, causa, escopo, tipo):
    resposta = _conversa(gatilho + " agora")
    assert resposta.status_code == 200
    assert resposta.json()["indisponibilidade"]["tipo"] == tipo
    assert not any(t in resposta.text for t in ("429", "RESOURCE_EXHAUSTED", "API_KEY_INVALID", "PERMISSION_DENIED", "chave-de-teste"))
    espera = client.get("/api/llm/status").json()["espera"]
    assert (espera["causa"], espera["escopo"]) == (causa, escopo)
    # Durante a espera, nenhuma chamada nova sai: o motor determinístico e os controles continuam.
    antes = client.get("/api/llm/status").json()["requests_used_today"]
    assert _conversa("Analisar distribuição da densidade").json()["indisponibilidade"]
    assert client.get("/api/llm/status").json()["requests_used_today"] == antes
    assert client.get("/api/health").json()["status"] == "ok"


def test_provedor_simulado_por_http_fora_do_contrato_regenera_e_usa_a_reserva(gemini_http):
    resposta = _conversa("simule fora do contrato agora")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo.get("reserva") is True and corpo["reply"] == main.RESERVA_DA_INTERPRETACAO
    assert client.get("/api/llm/status").json()["requests_used_today"] == llm_bridge.TENTATIVAS  # a primeira e 2 regenerações
