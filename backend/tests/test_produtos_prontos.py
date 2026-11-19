"""Os produtos prontos da imagem (PA-01, 19/11/2026; backend/produtos_prontos.py e Docs/OTIMIZACAO_LATENCIA.md, U12).

- catálogo sintético (job backend): gerados e carregados, as mesmas respostas pelo caminho pronto (sem interpretar as fontes,
  sem os perfis das colunas, sem montar a base das séries e sem a retroprojeção); sem a pasta, com outra chave (a base, a
  camada de coordenadas, o código ou as bibliotecas), com o arquivo alterado e com ADT_BRASIL_CACHE_MAX_MB=0, nada é carregado
  e tudo é calculado como antes; o limite dos quadros continua valendo; a carga não grava nada; o aquecimento carrega os
  produtos antes da inspeção, com a linha de sempre no log (a que .github/scripts/medir_conteiner.py lê);
- base versionada (job dados-reais, ADT_REAL_DATA_DIR, somente leitura): com e sem os produtos, os mesmos resultados, com a
  régua de decimais do CI (.github/scripts/comparar_respostas.py), no exame da base, no Detector com todos os municípios em
  jun/2024 e em jun/2021, nos casos do Simulador da seção S do relatório de implantação (Agrolândia, Abelardo Luz e o Pará como
  unidade) e em dois gráficos do painel; as matrizes de somente leitura continuam assim; com outra chave, o cálculo de sempre.
"""
import hashlib
import importlib.util
import json
import logging
import os
import re
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import detector
import main
import produtos_prontos
import semantic_bridge
import series_brasil
import simulador
from catalog_support import use_external_catalog
from install_brazil_data import install
from prepare_block1_catalog import prepare

RAIZ = Path(__file__).resolve().parents[2]
_especificacao = importlib.util.spec_from_file_location("comparar_respostas", RAIZ / ".github" / "scripts" / "comparar_respostas.py")
comparacao = importlib.util.module_from_spec(_especificacao)
_especificacao.loader.exec_module(comparacao)

INSPECAO = {"dataset": "brazil", "scope": "auto", "operation": "", "sheet": ""}
C1, M0 = {"id": "c1", "nome": "Cenário 1", "metodo": "padrao"}, {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"}
TODOS = {"base": {"municipios": {"todos": True}}}
# Os primeiros usos na base sintética (o Simulador com Manaus, que existe nela; na imagem, Agrolândia).
SINTETICOS = (("/api/detector", {**TODOS, "perfil": True}), ("/api/detector", TODOS),
              ("/api/simulador", {"base": {"municipios": {"todos": False, "estados": [], "ids": ["code:130260"]}},
                                  "horizonte": "202606", "cenarios": [C1, M0]}))
# O que os produtos evitam calcular: com eles carregados, nada disto roda (a calibração, conferida pela identidade dos objetos
# guardados, em GUARDADOS_DAS_FERRAMENTAS).
CALCULOS = ((main, "read_dataset"), (semantic_bridge, "_proposals"), (series_brasil, "_montar"), (simulador, "_casos"))
GUARDADOS_DAS_FERRAMENTAS = ((series_brasil, "_BASES"), (detector, "_CALIBRACOES"), (detector, "_CALIBRACOES_DOS_ESTADOS"),
                             (simulador, "_RETROS"))
LINHA_DO_AQUECIMENTO = re.compile(r"Aquecimento concluído em ([\d.]+) s \(base do Brasil ([\d.]+) s; biblioteca conversacional "
                                  r"([\d.]+) s\)")


def ferramenta(**opcoes):
    return {"dataset": "brazil", "scope": "municipal", "dataset_version": "", "context_revision": "0", "sheet": "",
            "mapping": "{}", "options": json.dumps(opcoes)}


def pedir(cliente, rota, dados):
    resposta = cliente.post(rota, data=dados)
    assert resposta.status_code == 200, (rota, resposta.status_code, resposta.text[:300])
    return resposta.json()


def sinteticas(cliente) -> dict:
    respostas = {"exame": pedir(cliente, "/api/inspect", INSPECAO)}
    for numero, (rota, opcoes) in enumerate(SINTETICOS):
        respostas[f"{rota} {numero}"] = pedir(cliente, rota, ferramenta(**opcoes))
    return respostas


def vigiar(monkeypatch) -> list:
    """Os cálculos que os produtos evitam, contados a cada chamada."""
    chamados = []
    for modulo, nome in CALCULOS:
        original = getattr(modulo, nome)
        monkeypatch.setattr(modulo, nome, lambda *a, _nome=nome, _original=original, **k: chamados.append(_nome) or
                            _original(*a, **k))
    return chamados


def objetos_das_ferramentas() -> dict:
    """Os objetos guardados da base das séries, das calibrações e das retroprojeções: recalculados, seriam outros."""
    return {(modulo.__name__, nome, chave_): id(valor) for modulo, nome in GUARDADOS_DAS_FERRAMENTAS
            for chave_, valor in getattr(modulo, nome).items()}


def vazios() -> bool:
    return all(not getattr(produtos_prontos._modulo(modulo), nome) for modulo, nome, _ in produtos_prontos.GUARDADOS)


@pytest.fixture
def catalogo(tmp_path, monkeypatch):
    pasta = tmp_path / "catalogo"
    prepare(pasta)
    use_external_catalog(monkeypatch, pasta)
    monkeypatch.delenv("ADT_BRASIL_CACHE_MAX_MB", raising=False)
    produtos_prontos.limpar()
    yield pasta
    produtos_prontos.limpar()


@pytest.fixture
def prontos(catalogo, tmp_path):
    """Os produtos da base sintética, gerados como na imagem, e as respostas calculadas sem eles."""
    esperadas = sinteticas(TestClient(main.app))
    produtos_prontos.limpar()
    pasta = tmp_path / "prontos"
    feito = produtos_prontos.gerar(pasta, SINTETICOS)
    produtos_prontos.limpar()
    return pasta, feito, esperadas


def test_gerados_e_carregados_as_mesmas_respostas_pelo_caminho_pronto(prontos, monkeypatch):
    pasta, feito, esperadas = prontos
    registro = json.loads((pasta / produtos_prontos.ARQUIVO_DA_CHAVE).read_text(encoding="utf-8"))
    conteudo = (pasta / produtos_prontos.ARQUIVO_DOS_PRODUTOS).read_bytes()
    assert registro["sha256"] == hashlib.sha256(conteudo).hexdigest() and registro["bytes"] == len(conteudo)
    assert set(registro["chave"]) == {"formato", "base", "integridade", "camada_de_coordenadas", "codigo", "bibliotecas"}
    assert registro["chave"]["integridade"] == "verificada" and set(registro["matrizes"]) <= {"0", "1"}
    assert all(registro["guardados"][nome] for nome in ("main._BRAZIL_FRAMES", "request_memo._SHARED", "series_brasil._BASES",
                                                         "detector._CALIBRACOES", "simulador._RETROS"))
    assert vazios()
    desfecho = produtos_prontos.carregar(pasta)
    assert desfecho["estado"] == "carregados" and desfecho["guardados"] == registro["guardados"], desfecho
    chamados, objetos = vigiar(monkeypatch), objetos_das_ferramentas()
    assert sinteticas(TestClient(main.app)) == esperadas
    assert chamados == [], "com os produtos, o exame e o primeiro uso das ferramentas não calculam de novo"
    assert objetos_das_ferramentas() == objetos and len(objetos) >= 4
    calibracao = next(iter(detector._CALIBRACOES.values()))
    assert not calibracao.pico.flags.writeable and not calibracao.c_perda.flags.writeable  # somente leitura, como calculada


def alterar_a_chave(pasta, campo):
    arquivo = pasta / produtos_prontos.ARQUIVO_DA_CHAVE
    registro = json.loads(arquivo.read_text(encoding="utf-8"))
    registro["chave"][campo] = "outra"
    arquivo.write_text(json.dumps(registro), encoding="utf-8")


def alterar_um_byte(pasta):
    arquivo = pasta / produtos_prontos.ARQUIVO_DOS_PRODUTOS
    conteudo = bytearray(arquivo.read_bytes())
    conteudo[len(conteudo) // 2] ^= 0xFF
    arquivo.write_bytes(bytes(conteudo))


@pytest.mark.parametrize("caso, estado", [
    ("sem a pasta", "ausentes"), ("outra versão da base", "chave_diferente"), ("outra camada de coordenadas", "chave_diferente"),
    ("outro código", "chave_diferente"), ("outras bibliotecas", "chave_diferente"), ("arquivo alterado", "arquivo_diferente"),
    ("arquivo cortado", "arquivo_diferente"), ("ADT_BRASIL_CACHE_MAX_MB=0", "desligados")])
def test_sem_os_produtos_validos_tudo_e_calculado_como_antes(prontos, monkeypatch, caso, estado):
    pasta, _, esperadas = prontos
    campos = {"outra versão da base": "base", "outra camada de coordenadas": "camada_de_coordenadas", "outro código": "codigo",
              "outras bibliotecas": "bibliotecas"}
    if caso == "sem a pasta":
        pasta = pasta.parent / "nenhuma"
    elif caso in campos:
        alterar_a_chave(pasta, campos[caso])
    elif caso == "arquivo alterado":
        alterar_um_byte(pasta)
    elif caso == "arquivo cortado":
        arquivo = pasta / produtos_prontos.ARQUIVO_DOS_PRODUTOS
        arquivo.write_bytes(arquivo.read_bytes()[:-10])
    else:
        monkeypatch.setenv("ADT_BRASIL_CACHE_MAX_MB", "0")
    # O arquivo dos produtos só é lido com a chave e o SHA-256 conferidos: aqui, nunca (só durante a carga: a memória entre
    # requisições também usa o pickle).
    with monkeypatch.context() as durante_a_carga:
        durante_a_carga.setattr(produtos_prontos.pickle, "loads", lambda *a, **k: pytest.fail("leu os produtos sem a chave certa"))
        desfecho = produtos_prontos.carregar(pasta)
    assert desfecho["estado"] == estado, desfecho
    if caso in campos:
        assert desfecho["diferencas"] == [campos[caso]]
    assert vazios()
    chamados = vigiar(monkeypatch)
    assert sinteticas(TestClient(main.app)) == esperadas
    assert {"_proposals", "_montar", "_casos"} <= set(chamados), "o cálculo de sempre"


def test_o_limite_dos_quadros_continua_valendo(prontos, monkeypatch):
    pasta, _, esperadas = prontos
    desfecho = produtos_prontos.carregar(pasta, limite_dos_quadros=1)  # nenhum quadro cabe: nenhum é reaproveitado
    assert desfecho["estado"] == "carregados" and not main._BRAZIL_FRAMES
    chamados = vigiar(monkeypatch)
    assert sinteticas(TestClient(main.app)) == esperadas
    assert "read_dataset" in chamados


def test_a_carga_nao_grava_nada(prontos):
    pasta, _, _ = prontos

    def retrato():
        return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                      for p in pasta.iterdir())
    antes = retrato()
    modos = {p: p.stat().st_mode for p in [pasta, *pasta.iterdir()]}
    try:
        for p in pasta.iterdir():
            os.chmod(p, stat.S_IREAD)
        os.chmod(pasta, stat.S_IREAD | stat.S_IEXEC)   # como na imagem: a pasta e os arquivos só de leitura
        assert produtos_prontos.carregar(pasta)["estado"] == "carregados"
    finally:
        for p, modo in modos.items():
            os.chmod(p, modo)
    assert retrato() == antes


def test_o_aquecimento_carrega_os_produtos_antes_da_inspecao(prontos, monkeypatch, caplog):
    pasta, _, esperadas = prontos
    monkeypatch.setattr(produtos_prontos, "PASTA", pasta)
    monkeypatch.setenv("ADT_AQUECIMENTO", "1")
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    chamados = vigiar(monkeypatch)
    try:
        with TestClient(main.app) as cliente:   # a partida do servidor: o aquecimento antes de atender
            assert main._WARM_DONE.is_set() and main.PARTIDA["produtos"] == "carregados"
            assert main.PARTIDA["total_s"] >= main.PARTIDA["base_s"] >= main.PARTIDA["produtos_s"] >= 0
            assert chamados == [], "o exame do aquecimento usou os produtos"
            assert pedir(cliente, "/api/inspect", INSPECAO) == esperadas["exame"]
    finally:
        main._WARM_DONE.set()
    texto = caplog.text
    assert "Produtos prontos da imagem carregados em" in texto
    assert LINHA_DO_AQUECIMENTO.search(texto), "a linha que medir_conteiner.py lê"


def test_sem_os_produtos_o_aquecimento_diz_isso_e_calcula_como_antes(catalogo, tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(produtos_prontos, "PASTA", tmp_path / "nenhuma")
    monkeypatch.setenv("ADT_AQUECIMENTO", "1")
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    try:
        with TestClient(main.app):
            assert main.PARTIDA["produtos"] == "ausentes" and main._BRAZIL_FRAMES   # o exame calculou e guardou, como antes
    finally:
        main._WARM_DONE.set()
    assert "Produtos prontos da imagem não usados (ausentes): a base é calculada como antes." in caplog.text
    assert LINHA_DO_AQUECIMENTO.search(caplog.text)


# --------------------------------------------------------------------------------------------- base versionada
@pytest.fixture(scope="module")
def base_real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    pasta = os.getenv("ADT_REAL_DATA_DIR")
    if not pasta:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    arquivos = [p for p in Path(pasta).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    antes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}
    destino = tmp_path_factory.mktemp("produtos-real") / "brasil"
    install(Path(pasta), destino)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(destino))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        patch.delenv("ADT_BRASIL_CACHE_MAX_MB", raising=False)
        produtos_prontos.limpar()
        yield destino
        produtos_prontos.limpar()
    assert antes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}


def so(codigo):
    return {"municipios": {"todos": False, "estados": [], "ids": [codigo]}}


def reais(cliente) -> dict:
    """Os pedidos do comando, sem o painel: o exame, o Detector em duas datas e os casos do Simulador da seção S."""
    return {
        "exame da base": pedir(cliente, "/api/inspect", INSPECAO),
        "Detector, todos os municípios, jun/2024": pedir(cliente, "/api/detector", ferramenta(**TODOS)),
        "Detector, todos os municípios, jun/2021": pedir(cliente, "/api/detector", ferramenta(**TODOS, janela={"fim": "202106"})),
        "Simulador, Agrolândia, 2 anos": pedir(cliente, "/api/simulador", ferramenta(base=so("code:420020"), horizonte="202606",
                                                                                     cenarios=[C1, M0])),
        "Simulador, Abelardo Luz, Simular recuperação": pedir(cliente, "/api/simulador", ferramenta(
            base=so("code:420010"), horizonte="202606",
            cenarios=[{**C1, "planejamento": {"meta": {"tipo": "patamar", "valor": 78.25}, "em": "202506"}}, M0])),
        "Simulador, Pará como unidade": pedir(cliente, "/api/simulador", ferramenta(estados_unidade=["15"], horizonte="202606",
                                                                                    cenarios=[C1, M0])),
    }


def do_painel(cliente) -> dict:
    """Dois gráficos do painel (os estados e todos os municípios), que usam os quadros e as derivações da versão."""
    painel = {"dataset": "brazil", "scope": "municipal", "dataset_version": "", "context_revision": "0", "mapping": "{}"}
    return {
        "painel, estados": pedir(cliente, "/api/painel", {**painel, "options": json.dumps(
            {"nivel": "estados", "indicador": "densidade", "competencia": "202406"})}),
        "painel, todos os municípios": pedir(cliente, "/api/painel", {**painel, "options": json.dumps(
            {"nivel": "municipios", "indicador": "densidade", "competencia": "202406", **TODOS})}),
    }


def test_real_com_e_sem_os_produtos_prontos_os_mesmos_resultados(base_real, tmp_path, monkeypatch):
    produtos_prontos.limpar()
    cliente = TestClient(main.app)
    sem = {**reais(cliente), **do_painel(cliente)}   # tudo calculado, como antes do PA-01
    assert sem["Detector, todos os municípios, jun/2024"]["resumo"]["niveis"]["critico"] == 40   # seção S do relatório
    pasta = tmp_path / "prontos"
    produtos_prontos.gerar(pasta)       # os primeiros usos da imagem (PRIMEIROS_USOS)
    produtos_prontos.limpar()
    desfecho = produtos_prontos.carregar(pasta)
    assert desfecho["estado"] == "carregados", desfecho
    chamados, objetos = vigiar(monkeypatch), objetos_das_ferramentas()
    cliente = TestClient(main.app)
    com = reais(cliente)
    assert chamados == [], "pelo caminho pronto: nem as fontes, nem os perfis, nem a base das séries, nem a retroprojeção"
    assert objetos_das_ferramentas() == objetos, "as calibrações e as retroprojeções carregadas, e não calculadas de novo"
    com.update(do_painel(cliente))
    assert "read_dataset" not in chamados, "o painel usa os quadros carregados"
    for nome, resposta in sem.items():
        assert comparacao.comparar_com_tolerancia(resposta, com[nome])["equivalente"], nome
    calibracao = next(iter(detector._CALIBRACOES.values()))
    assert not calibracao.pico.flags.writeable and not calibracao.c_instabilidade.flags.writeable
    # Com outra chave (outro código), nada é carregado e o exame calcula como antes, com o mesmo resultado.
    produtos_prontos.limpar()
    alterar_a_chave(pasta, "codigo")
    desfecho = produtos_prontos.carregar(pasta)
    assert desfecho["estado"] == "chave_diferente" and desfecho["diferencas"] == ["codigo"] and vazios()
    exame = pedir(TestClient(main.app), "/api/inspect", INSPECAO)
    assert comparacao.comparar_com_tolerancia(sem["exame da base"], exame)["equivalente"] and "_proposals" in chamados
