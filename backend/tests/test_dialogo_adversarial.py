"""Avaliação adversarial da conversa (desafio adversarial, 26/10/2026), com a base Brasil versionada (job dados-reais).

As conversas de dialogo_adversarial/casos.json foram escritas antes da implementação do gestor de diálogo e não foram
ajustadas depois de medir. Cada uma roda no simulador da tela (conversa_simulada.py), sem o provedor de IA: mede o que a
conversa faz sozinha, como no CI. Critério de sucesso de um turno: resposta HTTP 200 e todos os predicados de `espera`.

Metas (as do desafio): interpretação e continuidade acima de 90%; verificação, estado e explicação acima de 90%;
governança e fidelidade analítica (todo número da resposta é um valor do motor) sem nenhuma falha nos casos executados.

Também roda como relatório, na raiz do repositório (somente leitura dos dados):
    ADT_REAL_DATA_DIR=. python backend/tests/test_dialogo_adversarial.py
"""
import collections
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from conversa_simulada import Tela, dobra  # noqa: E402

CONJUNTOS = ("casos.json", "casos_ineditos.json", "casos_ineditos_2.json")


def carrega(nome):
    return json.loads((HERE / "dialogo_adversarial" / nome).read_text(encoding="utf-8"))


CASOS = carrega(os.getenv("ADT_DIALOGO_CASOS", "casos.json"))
METAS = {"interpretacao": 0.9, "continuidade": 0.9, "verificacao": 0.9, "estado": 0.9, "explicacao": 0.9,
         "governanca": 1.0}
RECUSA = ("nao faz parte do escopo", "nao esta disponivel nesta versao", "nao altero", "nao modifico", "nao mudo",
          "nao posso", "nao consigo", "nao e possivel", "nao crio", "nao faco", "nao uso", "nao incluo", "nao conto",
          "nao recomendo", "nao listo", "nao reconhec", "nao substitu", "fora do escopo", "nao calculo", "nao projeto",
          "nao afirmo", "nao digo", "nao troco", "nao invento", "nao classifico")
NUMERO = re.compile(r"(?<![\w,.-])-?\d[\d.]*(?:,\d+)?(?![\w])")
# A escala de apresentação da densidade (CAP-IND-02.representacao: por 1.000 habitantes) é parâmetro, não valor.
ESCALA = re.compile(r"\b(?:por|para cada|a cada)\s+1\.000\b")


def _codigos(nomes, casos=None):
    codigos = (casos or CASOS)["codigos"]
    return [codigos.get(nome, nome) for nome in nomes]


def _formatos(valor, saida):
    """Os textos com que um valor do motor pode aparecer na resposta (regra de apresentação de resumo_painel)."""
    from resumo_painel import number
    if isinstance(valor, bool):
        return
    if isinstance(valor, int):
        saida.update({number(valor), str(valor)})
    elif isinstance(valor, float):
        for casas in range(0, 7):
            try:
                saida.add(number(valor, casas) if casas else number(round(valor)) if abs(valor) >= 1 else "0")
            except (TypeError, ValueError):
                pass
    elif isinstance(valor, dict):
        for item in valor.values():
            _formatos(item, saida)
    elif isinstance(valor, list):
        for item in valor:
            _formatos(item, saida)
    elif isinstance(valor, str) and re.fullmatch(r"(?:19|20)\d{4}", valor):
        saida.update({valor[:4], str(int(valor[4:]))})
    elif isinstance(valor, str):
        # Textos do motor (notas, rótulos, descrições) copiados como vieram: os números deles também são do motor.
        saida.update(numero.rstrip(".") for numero in NUMERO.findall(valor))


def numeros_do_motor(texto, corpos):
    """Todo número do texto é um valor do motor (em algum resultado visto na conversa), um ano, um código de método, um
    inteiro pequeno (contagens e ordinais) ou o exemplo documentado de uma ficha de método autorizada (Adendo
    PAR-20261026; V-01 e V-02: exemplos documentados com âncora, não fatos dos dados), só quando a formulação autorizada
    inteira aparece literalmente no texto. Devolve os números sem origem."""
    import definicoes
    validos = set()
    for corpo in corpos:
        _formatos(corpo, validos)
    for ficha in definicoes.FICHAS.values():
        if ficha.texto in texto:
            validos.update(numero.rstrip(".") for numero in NUMERO.findall(ficha.texto))
    soltos = []
    texto = ESCALA.sub("por escala", texto)
    for numero in NUMERO.findall(texto):
        limpo = numero.rstrip(".")
        if re.fullmatch(r"(?:19|20)\d{2}", limpo) or (limpo.isdigit() and int(limpo) <= 12) or limpo in validos:
            continue
        soltos.append(limpo)
    return soltos


def _extremo(corpo, atributo, maior):
    itens = [item for item in (corpo or {}).get("itens", []) if isinstance(item.get(atributo), (int, float))]
    if not itens:
        return set()
    alvo = (max if maior else min)(item[atributo] for item in itens)
    return {dobra(item["rotulo"]).split(" (")[0] for item in itens if item[atributo] == alvo}


def _cita(texto, corpo, atributo, maior):
    """O território do extremo (do motor) é o citado junto da primeira palavra de relação da resposta."""
    certos = _extremo(corpo, atributo, maior)
    todos = {dobra(item["rotulo"]).split(" (")[0] for item in (corpo or {}).get("itens", [])}
    simples = dobra(texto)
    relacao = re.search(r"\b(?:maior|mais alt[oa]|mais)\b" if maior else r"\b(?:menor|menos|mais baix[oa])\b", simples)
    if not certos or relacao is None:
        return False
    distancias = {nome: min((abs(m.start() - relacao.start()) for m in re.finditer(re.escape(nome), simples)),
                            default=10 ** 6) for nome in todos}
    return min(distancias, key=distancias.get) in certos


def avalia(tela, turno, espera, corpos, casos=None):
    """Lista de predicados que falharam (vazia: o turno passou)."""
    def _codigos_(nomes):
        return _codigos(nomes, casos)
    falhas = []
    texto = dobra(turno.texto)
    if turno.status != 200:
        return ["HTTP " + str(turno.status) + ": " + turno.texto[:120]]
    municipios = tela.municipios
    no_grafico = set(tela.ids_no_grafico()) | set(municipios["ids"])
    estados = set(municipios["estados"]) | set(tela.estados or [])
    for chave, valor in espera.items():
        ok = True
        if chave == "pergunta":
            ok = bool(turno.alternativas) == valor and not turno.aplicado
        elif chave == "alternativas":
            rotulos = [dobra(item.get("label", "")) for item in turno.alternativas]
            ok = all(any(esperado in rotulo for rotulo in rotulos) for esperado in valor)
        elif chave == "comparar":
            ok = set(tela.comparar or []) == set(_codigos_(valor))
        elif chave == "comparar_ordem":
            ok = list(tela.comparar or []) == _codigos_(valor)
        elif chave in ("familia", "indicador", "competencia"):
            ok = getattr(tela, chave) == valor
        elif chave == "grupos":
            ok = (tela.grupos or {}).get("tipo") == valor
        elif chave == "ids_contem":
            ok = set(_codigos_(valor)) <= no_grafico
        elif chave == "ids_nao_contem":
            ok = not set(_codigos_(valor)) & set(tela.ids_no_grafico())
        elif chave == "estados_contem":
            ok = set(valor) <= estados
        elif chave == "estados_nao_contem":
            ok = not set(valor) & estados
        elif chave == "todos":
            ok = municipios["todos"] is valor
        elif chave == "sem_mudanca":
            ok = not turno.aplicado
        elif chave == "resposta":
            ok = all(dobra(item) in texto for item in valor)
        elif chave == "resposta_algum":
            ok = any(dobra(item) in texto for item in valor)
        elif chave == "resposta_grupos":
            ok = all(any(dobra(item) in texto for item in grupo) for grupo in valor)
        elif chave == "nao_resposta":
            ok = not any(dobra(item) in texto for item in valor)
        elif chave == "numeros_do_motor":
            soltos = numeros_do_motor(turno.texto, corpos)
            ok = not soltos
            if not ok:
                falhas.append("números sem origem no motor: " + ", ".join(soltos[:5]))
                continue
        elif chave == "cita_maior":
            ok = _cita(turno.texto, tela.resposta, valor, True)
        elif chave == "cita_menor":
            ok = _cita(turno.texto, tela.resposta, valor, False)
        elif chave == "recusa":
            ok = not turno.aplicado and any(marca in texto for marca in RECUSA)
        else:
            raise AssertionError("Predicado desconhecido: " + chave)
        if not ok:
            falhas.append(chave + "=" + json.dumps(valor, ensure_ascii=False))
    return falhas


def executa(client, info, conversa, casos=None):
    tela = Tela(client, info)
    inicio = conversa.get("inicio")
    if inicio:
        tela.seleciona(ids=_codigos(inicio.get("ids", []), casos), estados=inicio.get("estados", []),
                       familia=inicio.get("familia"), comparar=_codigos(inicio.get("comparar", []), casos) or None)
    corpos = [tela.resposta] if tela.resposta else []
    resultados = []
    for indice, passo in enumerate(conversa["turnos"]):
        turno = tela.diga(passo["diga"])
        if tela.resposta is not None and (not corpos or corpos[-1] is not tela.resposta):
            corpos.append(tela.resposta)
        if "espera" not in passo:
            continue
        falhas = avalia(tela, turno, passo["espera"], corpos, casos)
        resultados.append({"conversa": conversa["id"], "turno": indice + 1, "categoria": passo.get("categoria",
                           conversa["categoria"]), "diga": passo["diga"], "ok": not falhas, "falhas": falhas,
                           "canal": turno.canal, "resposta": turno.texto[:400],
                           "fidelidade": "numeros_do_motor" in passo["espera"],
                           "fiel": not any(f.startswith("números sem origem") for f in falhas)})
    return resultados


def resumo(resultados):
    por_categoria = {}
    for item in resultados:
        conta = por_categoria.setdefault(item["categoria"], [0, 0])
        conta[0] += item["ok"]
        conta[1] += 1
    fidelidade = [item["fiel"] for item in resultados if item["fidelidade"]]
    return {"turnos": len(resultados), "sucessos": sum(item["ok"] for item in resultados),
            "por_categoria": {chave: {"sucessos": a, "turnos": b, "taxa": round(a / b, 3)} for chave, (a, b) in
                              sorted(por_categoria.items())},
            "fidelidade": {"turnos": len(fidelidade), "fieis": sum(fidelidade)}}


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    from fastapi.testclient import TestClient
    import main
    from install_brazil_data import install
    paths = [p for p in Path(folder).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    catalog = tmp_path_factory.mktemp("dialogo-adversarial") / "brasil"
    install(Path(folder), catalog)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(catalog))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        patch.delenv("GEMINI_API_KEY", raising=False)  # a avaliação mede a conversa sem o provedor, como no CI
        main._BRAZIL_FRAMES.clear()
        client = TestClient(main.app)
        info = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
        yield client, info
        main._BRAZIL_FRAMES.clear()
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@pytest.mark.parametrize("nome", CONJUNTOS)
def test_conjunto_adversarial_atinge_as_metas(real, nome):
    client, info = real
    casos = carrega(nome)
    resultados = [item for conversa in casos["conversas"] for item in executa(client, info, conversa, casos)]
    medido = resumo(resultados)
    falhas = [f"{item['conversa']}.{item['turno']} {item['diga']!r}: {item['falhas']} -> {item['resposta'][:200]!r}"
              for item in resultados if not item["ok"]]
    abaixo = {categoria: dados["taxa"] for categoria, dados in medido["por_categoria"].items()
              if dados["taxa"] < METAS.get(categoria, 0.9) - 1e-9}
    assert not abaixo, json.dumps(medido, ensure_ascii=False, indent=1) + "\n" + "\n".join(falhas)
    assert medido["fidelidade"]["fieis"] == medido["fidelidade"]["turnos"], "\n".join(falhas)


if __name__ == "__main__":
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        sys.exit("Defina ADT_REAL_DATA_DIR (a raiz do repositório tem a base versionada).")
    import tempfile
    from fastapi.testclient import TestClient
    from install_brazil_data import install
    with tempfile.TemporaryDirectory(prefix="adt-dialogo-") as pasta:
        catalogo = Path(pasta) / "brasil"
        install(Path(folder), catalogo)
        os.environ["ADT_BRASIL_DATA_DIR"] = str(catalogo)
        os.environ.pop("ADT_BRASIL_DATA_VERSION", None)
        os.environ.pop("GEMINI_API_KEY", None)
        import main
        main._BRAZIL_FRAMES.clear()
        cliente = TestClient(main.app)
        dados = cliente.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
        todos = []
        for conversa in CASOS["conversas"]:
            for item in executa(cliente, dados, conversa):
                todos.append(item)
                marca = "OK " if item["ok"] else "XX "
                print(marca + f"{item['conversa']}.{item['turno']} [{item['categoria']}] {item['diga']}")
                if not item["ok"]:
                    print("     falhas: " + "; ".join(item["falhas"]))
                    print("     resposta: " + item["resposta"][:300].replace("\n", " "))
        print(json.dumps(resumo(todos), ensure_ascii=False, indent=1))
        saida = os.getenv("ADT_DIALOGO_RELATORIO")
        if saida:
            Path(saida).write_text(json.dumps({"resumo": resumo(todos), "turnos": todos}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")


def test_redacao_fiel_simulada_passa_na_conferencia_com_a_base_versionada(real, monkeypatch):
    """Falsos positivos da conferência de fidelidade (26/10/2026). A redação simulada devolve a resposta verificada do
    próprio sistema com outra abertura, o texto mais fiel possível: toda redação tem de aparecer (GEMINI_VALIDADO). Antes
    da correção, 11 de 60 caíam na reserva ("Quanto à causa, vale a regra do escopo" lido como causa; leitura do resultado
    que cita uma classe cobrada como definição). Transporte simulado: nenhuma chamada real ao provedor."""
    import llm_bridge
    client, info = real

    async def interpretar(sanitized, model, api_key):
        return {"operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
                "intent": "CONVERSACIONAL", "topic": "none"}

    async def redigir(sistema, mensagens, esquema, max_tokens=1200):
        contexto = next((m for m in mensagens if m.startswith("CONTEXTO_DA_CONVERSA: ")), "")
        cartao = json.loads(contexto[len("CONTEXTO_DA_CONVERSA: "):]) if contexto else {}
        verificada = cartao.get("resposta_verificada_do_sistema") or ""
        return {"resposta": ("Em outras palavras: " + verificada) if verificada else ""}

    monkeypatch.setenv("GEMINI_API_KEY", "chave-simulada-local")
    monkeypatch.setattr(llm_bridge, "_call_gemini", interpretar)
    monkeypatch.setattr(llm_bridge, "generate_structured", redigir)
    origens, reservas, erros = collections.Counter(), [], []
    for nome in CONJUNTOS:
        casos = carrega(nome)
        for conversa in casos["conversas"]:
            tela = Tela(client, info)
            inicio = conversa.get("inicio")
            if inicio:
                tela.seleciona(ids=_codigos(inicio.get("ids", []), casos), estados=inicio.get("estados", []),
                               familia=inicio.get("familia"), comparar=_codigos(inicio.get("comparar", []), casos) or None)
            for passo in conversa["turnos"]:
                turno = tela.diga(passo["diga"])
                if turno.status >= 500:
                    erros.append((nome, conversa["id"], passo["diga"], turno.status))
                origem = ((turno.corpo or {}).get("redacao") or {}).get("origem")
                if origem:
                    origens[origem] += 1
                if origem == "DETERMINISTICA":
                    reservas.append((nome, conversa["id"], passo["diga"]))
            # Cada tela abre uma sessão; o backend guarda no máximo 128 ao mesmo tempo, e os testes anteriores do módulo
            # deixam as suas abertas.
            client.post("/api/session/close", headers={"X-ADT-Session": tela.sessao})
    assert not erros, erros
    assert origens["GEMINI_VALIDADO"] >= 40, origens  # a redação foi de fato exercida
    assert not reservas, reservas
