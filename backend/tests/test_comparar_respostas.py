"""A comparação das análises no job "conteiner" do CI (.github/scripts/comparar_respostas.py, desde 07/11/2026), conferida
sem Docker, sem rede e sem a base:
- a referência na imagem é exata: 1 ULP de diferença num número já distingue as respostas, e só os campos voláteis
  (identificador do resultado e hora de criação) não contam;
- a referência no runner precisa ser equivalente: exata em chaves, textos, inteiros, booleanos, nulos, ordem, tamanhos e
  empates; nos números decimais, aceita só a diferença relativa de até 1e-9, como a das distâncias da execução 488;
- a referência roda na mesma imagem, sem rede e sem a chave do Gemini, com o commit montado só para leitura em /src, e
  recusa o código da imagem (/app);
- os arquivos enviados chegam à referência na imagem byte a byte;
- o medir_conteiner.py usa as duas referências.
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".github" / "scripts"
especificacao = importlib.util.spec_from_file_location("comparar_respostas", SCRIPTS / "comparar_respostas.py")
comparacao = importlib.util.module_from_spec(especificacao)
especificacao.loader.exec_module(comparacao)

# A linha 2898 da família "espacial" (MOJUI DOS CAMPOS [150475] -> ALTINHO [260080]) na execução 488 do CI: no contêiner
# (glibc genérica do Debian trixie) e na referência no runner (Ubuntu 26.04, glibc amd64v3).
NO_CONTEINER = 2155.734755000499
NO_RUNNER_2604 = 2155.7347550004965


def resposta(distancia, identificador="r1", hora="2026-11-07T12:59:45Z"):
    return {"rows": [{"Território": "ALTINHO [260080]", "Distância (km)": distancia}], "result_id": identificador,
            "metadata": {"created_at": hora, "geodesicas_calculadas": 5570, "ids": ["150475", "260080"]}}


def test_referencia_na_imagem_e_exata_ate_o_ultimo_bit():
    assert comparacao.identicas(resposta(NO_CONTEINER), resposta(NO_CONTEINER))
    assert not comparacao.identicas(resposta(NO_CONTEINER), resposta(NO_RUNNER_2604))
    assert not comparacao.identicas(resposta(1.0), resposta(math.nextafter(1.0, 2.0)))  # 1 ULP
    assert comparacao.identicas(resposta(NO_CONTEINER, "r1", "agora"), resposta(NO_CONTEINER, "r2", "depois"))


def test_equivalencia_com_o_runner_aceita_so_a_diferenca_da_libm_nos_decimais():
    assert abs(NO_CONTEINER - NO_RUNNER_2604) == 5 * math.ulp(NO_CONTEINER)  # 2,3e-12 km, cerca de 2 nanômetros
    da_488 = comparacao.comparar_com_tolerancia(resposta(NO_CONTEINER), resposta(NO_RUNNER_2604))
    assert da_488["equivalente"] and da_488["numeros_diferentes"] == 1
    assert 1e-16 < da_488["maior_diferenca_relativa"] < 1e-14
    iguais = comparacao.comparar_com_tolerancia(resposta(NO_CONTEINER), resposta(NO_CONTEINER))
    assert iguais["equivalente"] and iguais["numeros_diferentes"] == 0 and iguais["maior_diferenca_relativa"] == 0
    fora = comparacao.comparar_com_tolerancia(resposta(1000.0), resposta(1000.0 * (1 + 2e-9)))
    assert not fora["equivalente"] and fora["fora_da_tolerancia_total"] == 1
    assert fora["fora_da_tolerancia"][0].startswith("$.rows[0].Distância (km)")
    no_limite = comparacao.comparar_com_tolerancia({"x": 1.0}, {"x": 1.0 + 5e-10})
    assert no_limite["equivalente"] and no_limite["numeros_diferentes"] == 1


@pytest.mark.parametrize("caso,a,b", [
    ("texto", {"t": "ALTINHO"}, {"t": "ALTINHO "}),
    ("inteiro", {"atendem": 89}, {"atendem": 90}),
    ("booleano", {"ok": True}, {"ok": False}),
    ("nulo", {"d": None}, {"d": 0.0}),
    ("ordem", {"ids": ["150475", "260080"]}, {"ids": ["260080", "150475"]}),
    ("tamanho", {"ids": ["150475", "260080"]}, {"ids": ["150475"]}),
    ("chave", {"a": 1}, {"b": 1}),
    ("tipo", {"n": 1}, {"n": True}),
    ("empate", {"empates": [3, 7]}, {"empates": [3]}),
    ("infinito", {"x": 1.0}, {"x": math.inf}),
])
def test_equivalencia_com_o_runner_e_exata_fora_dos_decimais(caso, a, b):
    resultado = comparacao.comparar_com_tolerancia(a, b)
    assert not resultado["equivalente"], caso
    assert resultado["outras_diferencas_total"] >= 1 and resultado["outras_diferencas"], caso


def test_exemplos_limitados_e_contagem_completa():
    a = {"ids": [str(i) for i in range(50)]}
    b = {"ids": [str(i + 1) for i in range(50)]}
    resultado = comparacao.comparar_com_tolerancia(a, b)
    assert resultado["outras_diferencas_total"] == 50 and len(resultado["outras_diferencas"]) == comparacao.EXEMPLOS


def test_referencia_roda_na_mesma_imagem_sem_rede_com_o_commit_so_para_leitura():
    raiz = "/home/runner/work/Teste-Agente/Teste-Agente"
    comando = comparacao.comando_da_referencia_na_imagem("adt:ci", raiz)
    assert comando[:3] == ["docker", "run", "--rm"]
    assert comando[comando.index("--network") + 1] == "none"
    assert comando[comando.index("-v") + 1] == raiz + ":/src:ro"
    assert "GEMINI_API_KEY=" in comando and "ADT_AQUECIMENTO=0" in comando
    assert comando[-2:] == ["adt:ci", "/src/.github/scripts/referencia_na_imagem.py"]
    assert comparacao.codigo_do_commit("/src/backend/main.py")
    assert not comparacao.codigo_do_commit("/app/backend/main.py")
    assert not comparacao.codigo_do_commit("/src/backend/tests/main.py")
    script = (SCRIPTS / "referencia_na_imagem.py").read_text(encoding="utf-8")
    assert "codigo_do_commit(main.__file__)" in script and "sys.stdout = sys.stderr" in script


def test_arquivos_chegam_a_referencia_byte_a_byte():
    conteudo = "distrito;ano\nAlto Rio;2023\n".encode() + bytes(range(256))
    pedidos = [("rotatividade", "/api/analyze", {"operation": "rotation"}, {"file": ("pessoas.csv", conteudo)}, False),
               ("densidade", "/api/analyze", {"operation": "density"}, None, False)]
    recebidos = json.loads(json.dumps(comparacao.pedidos_para_json(pedidos)))
    assert [p["familia"] for p in recebidos] == ["rotatividade", "densidade"]
    assert comparacao.arquivos_de_json(recebidos[0]["arquivos"]) == {"file": ("pessoas.csv", conteudo)}
    assert comparacao.arquivos_de_json(recebidos[1]["arquivos"]) is None


def test_medir_conteiner_usa_as_duas_referencias():
    texto = (SCRIPTS / "medir_conteiner.py").read_text(encoding="utf-8")
    analises = texto.split("def medir_analises(", 1)[1].split("\ndef ", 1)[0]
    assert "referencia_na_imagem(c.imagem" in analises
    assert "comparacao.identicas(" in analises and "comparacao.comparar_com_tolerancia(" in analises
    assert "TestClient(main.app)" in analises  # a referência no runner continua
