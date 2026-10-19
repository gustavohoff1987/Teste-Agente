"""Jornada da referência mais próxima (Bloco 2, Etapa 1) na interface conversacional.

Servidor serve_ui_offline.py com o catálogo sintético do Bloco 1; nunca chama Gemini.
Percorre a base Brasil (critério de densidade, comando conversacional, exportações,
reutilização e retomada) e uma base importada sintética (lista explícita, vírgula
decimal, referência e alvos sem coordenada válida, coordenada que muda entre
competências). As distâncias são conferidas com pyproj, independentemente da API.
Nenhum dado real é usado; capturas ficam em .local/ui-validation/, ignorada pelo Git.
"""
import csv
import io
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from pyproj import Geod
from ui_support import workspace, execute_analysis, URL, offline, choose

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
GEOD = Geod(ellps="GRS80")
# Base importada fictícia: nome, código, coordenadas por competência (texto com vírgula decimal).
UPLOAD = [("ALFA", "1001", ("-3,10", "-60,02"), ("-3,10", "-60,02")),
          ("BETA", "1002", ("-3,35", "-64,71"), ("-3,35", "-64,71")),
          ("GAMA", "1003", ("-2,63", "-56,74"), ("-2,60", "-56,70")),  # muda entre 202401 e 202406
          ("DELTA", "1004", ("-2,44", "-54,71"), ("-2,44", "-54,71")),
          ("EPSILON", "1005", ("95,0", "-60,0"), ("95,0", "-60,0")),  # latitude fora do intervalo
          ("ZETA", "1006", ("", ""), ("", ""))]  # sem coordenadas


def exported_rows(download):
    return list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))


def assert_same_rows(exported, rows):
    """CSV baixado no navegador × linhas do motor, em precisão integral (sem arredondamento)."""
    assert len(exported) == len(rows)
    for line, row in zip(exported, rows):
        assert list(line) == list(row)
        for key, value in row.items():
            if value is None:
                assert line[key] == "", (key, line[key])
            elif isinstance(value, (int, float)):
                assert float(line[key]) == value, (key, line[key], value)
            else:
                assert line[key] == str(value), (key, line[key], value)


def km(a, b):
    """Geodésica GRS80 entre dois pares (lat, lon) em texto com vírgula, calculada fora da API."""
    (lat1, lon1), (lat2, lon2) = [[float(v.replace(",", ".")) for v in point] for point in (a, b)]
    return GEOD.inv(lon1, lat1, lon2, lat2)[2] / 1000


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p, tempfile.TemporaryDirectory(prefix="adt-nearest-ui-") as folder:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        failures, llm_calls, analyses = [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: analyses.append(request.url) if request.url.endswith("/api/analyze") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        chat = page.locator("#assistente")
        inline = page.locator("#preparacao-conversacional")
        board = page.locator("#resultados")

        def send(message):
            chat.locator("#assistant-input").fill(message)
            chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
            expect(chat.locator("#assistant-input")).to_be_enabled(timeout=60000)

        def execute(name="Calcular e mostrar resultado", double=False):
            button = inline.get_by_role("button", name=name, exact=True)
            expect(button).to_be_enabled(timeout=60000)
            before = len(analyses)
            with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=120000) as event:
                execute_analysis(page, button, double)
            assert event.value.status == 200, event.value.text()[:500]
            expect(board.locator("h3", has_text="Referência mais próxima").first).to_be_visible()
            page.wait_for_timeout(400)
            assert len(analyses) == before + 1, "uma execução por pedido, mesmo com clique duplo"
            return event.value.json()

        def reveal(summary):
            details = board.locator("details", has=page.locator("summary", has_text=summary))
            if not details.evaluate("element => element.open"):
                details.locator("summary").click()

        # 1. Base Brasil; o comando conversacional prepara só a operação e os alvos citados.
        send("Olá")
        chat.get_by_role("button", name="Usar dados do Brasil").click()
        expect(chat.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=60000)
        send("Calcule a referência mais próxima de Manaus, Tefe e Parintins.")
        expect(chat.get_by_test_id("latest-reply")).to_contain_text("nenhuma referência foi escolhida e nada foi calculado")
        workspace(page, "territories")
        targets = page.get_by_role("region", name="Seleção territorial compartilhada")
        expect(targets.get_by_role("heading", name="Municípios-alvo")).to_be_visible()
        expect(targets.get_by_text("3 selecionados", exact=True)).to_be_visible()
        workspace(page, "preparation")
        setup = inline.get_by_role("group", name="Definição das referências")
        expect(setup.get_by_role("radio", checked=True)).to_have_count(0)  # nenhum modo nem referência por padrão
        assert not analyses and not llm_calls
        # 2-5. Critério simples, período e referencial confirmados explicitamente.
        inline.get_by_label("Escolher períodos da análise").click()
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        setup.get_by_label("Critério simples de densidade").check()
        setup.get_by_label("Operador do critério").select_option(">=")
        setup.get_by_label("Valor do critério").fill("10")
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)).to_be_disabled()
        inline.get_by_label("Referencial geodésico").select_option("SIRGAS2000")
        # 6-7. Execução única, mesmo com clique duplo; resultado com referência, distância e cobertura.
        criterion = execute(double=True)
        structured = criterion["metadata"]["nearest_reference"]
        refs = structured["conjunto_referencias"]
        assert refs["forma"] == "CRITERIO" and refs["origem"] == "CRITERIO_AUTORIZADO_APLICADO_AOS_DADOS"
        assert refs["criterio"]["operador"] == ">=" and refs["criterio"]["valor"] == "10" and refs["criterio"]["periodo"] == "202406"
        # Fixture: MANAUS 15/1.000 e FORA 105/9.000 atendem; TEFE 10/2.000 e PARINTINS 12/4.000 não.
        assert {m["id"] for m in refs["membros"]} == {"code:130260", "code:350010"}
        assert set(criterion["metadata"]["options"]["territory_ids"]) == {"code:130260", "code:130420", "code:130340"}
        rows = {row["Código do alvo"]: row for row in criterion["rows"]}
        assert set(rows) == {"130260", "130420", "130340"}
        # Todas as unidades da fixture estão no mesmo ponto: distância zero e empate explícito, sem tolerância.
        assert all(row["Distância (km)"] == 0 and row["Empate"] == "Sim (2 referências)" for row in rows.values())
        assert rows["130260"]["Alvo também é referência"] == "Sim" and rows["130420"]["Alvo também é referência"] == "Não"
        assert structured["cobertura"] == {"n_universo": 3, "n_minimo_completo": 3, "n_somente_entre_avaliaveis": 0,
                                           "n_nao_avaliaveis_por_motivo": {}}
        assert structured["desfecho"] == "RES-LIM" and structured["limitacoes"][0]["tipo"] == "DISTANCIA_GEODESICA_DIRETA"
        expect(board.locator(".data-table tbody tr")).to_have_count(3)
        expect(board.get_by_role("listitem").filter(has_text="Não representa distância viária")).to_be_visible()
        page.screenshot(path=str(OUTPUT / "nearest-01-criterio.png"), full_page=True)
        # 9. Exportação da tabela e dos metadados, integral e sem arredondamento.
        with page.expect_download() as download:
            board.get_by_role("button", name="CSV", exact=True).click()
        assert_same_rows(exported_rows(download), criterion["rows"])
        with page.expect_download() as download:
            board.get_by_text("Opções técnicas avançadas", exact=True).click()
            board.get_by_role("button", name="Baixar registro técnico (JSON)", exact=True).click()
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert exported["nearest_reference"] == structured and exported["result_id"] == criterion["result_id"]
        # 8. Reutilização: as referências do critério viram lista explícita, por decisão do usuário.
        reveal("Reutilizar as referências deste resultado")
        board.get_by_role("button", name="Usar como lista de referências", exact=True).click()
        expect(setup.get_by_label("Lista de municípios por nome ou código")).to_be_checked()
        chosen = inline.get_by_role("region", name="Seleção de referências")
        expect(chosen.get_by_text("2 selecionados", exact=True)).to_be_visible()
        listed = execute()
        assert listed["metadata"]["nearest_reference"]["conjunto_referencias"]["forma"] == "LISTA_EXPLICITA"
        assert set(listed["metadata"]["options"]["reference_ids"]) == {"code:130260", "code:350010"}
        assert [r["Distância (km)"] for r in listed["rows"]] == [r["Distância (km)"] for r in criterion["rows"]]
        # Retomada do resultado atual: a lista explícita volta e o cálculo idêntico é reaproveitado.
        board.get_by_role("button", name="Retomar parâmetros deste resultado", exact=True).click()
        expect(setup.get_by_label("Lista de municípios por nome ou código")).to_be_checked()
        expect(chosen.get_by_text("2 selecionados", exact=True)).to_be_visible()
        calls = len(analyses)
        button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
        expect(button).to_be_enabled(timeout=60000)
        execute_analysis(page, button)
        expect(page.get_by_text("Resultado existente recuperado, sem recalcular.", exact=True)).to_be_visible()
        assert len(analyses) == calls
        # Reutilizar como alvos troca só a seleção de alvos; o resultado calculado permanece.
        reveal("Reutilizar as referências deste resultado")
        board.get_by_role("button", name="Usar como municípios-alvo", exact=True).click()
        expect(targets.get_by_text("2 selecionados", exact=True)).to_be_visible()
        expect(board.locator(".data-table tbody tr")).to_have_count(3)

        # Base importada fictícia: lista explícita, vírgula decimal e cobertura parcial. O arquivo
        # permanece no disco durante a jornada, porque cada pré-exame e execução o reenvia.
        lines = ["municipio;codigo_territorial;periodo;categoria;quantidade;populacao;latitude;longitude"]
        for period, index in (("202401", 2), ("202406", 3)):
            for row in UPLOAD:
                lat, lon = row[index]
                lines.append(f"{row[0]};{row[1]};{period};MEDICINA;10;1000;{lat};{lon}")
        source = Path(folder) / "base_ficticia.csv"
        source.write_text("\n".join(lines) + "\n", encoding="utf-8")
        chat.get_by_text("Trocar fonte de dados", exact=True).click()
        page.get_by_label("Importar arquivo de dados").set_input_files(str(source))
        expect(chat.get_by_test_id("current-source")).to_contain_text(source.name, timeout=60000)
        expect(inline.get_by_role("group", name="Definição das referências")).to_be_visible()  # a análise segue ativa
        inline.get_by_label("Filtrar por período").select_option("202406")
        # D1: o código territorial é escolhido no seletor (sem botão "Confirmar correspondências").
        assert inline.get_by_role("button", name="Confirmar correspondências", exact=True).count() == 0
        choose(inline, "Identificador territorial", "codigo_territorial")
        inline.get_by_label("Referencial geodésico").select_option("SIRGAS2000")
        setup.get_by_label("Lista de municípios por nome ou código").check()
        chosen = inline.get_by_role("region", name="Seleção de referências")
        for code in ("1001", "1003", "1005"):
            chosen.get_by_role("searchbox").fill(code)
            expect(chosen.get_by_role("checkbox")).to_have_count(1)
            chosen.get_by_role("checkbox").check()
        expect(chosen.get_by_text("3 selecionados", exact=True)).to_be_visible()
        # Vírgula nas coordenadas: o separador é verificado nos dados (coordenadas com vírgula; quantidades e populações
        # sem vírgula) e registrado em nota; o seletor só aparece quando o formato é misto.
        imported = execute("Executar análise")
        expect(setup.get_by_label("Separador decimal das coordenadas")).to_have_count(0)
        assert any(note.startswith("Separador decimal das coordenadas: vírgula, verificada nos dados") for note in imported["notes"])
        structured = imported["metadata"]["nearest_reference"]
        assert structured["periodo_geometria"] == "202406"
        assert [item["id"] for item in structured["referencias_nao_avaliaveis"]] == ["code:1005"]
        assert structured["cobertura"]["n_universo"] == 6 and structured["cobertura"]["n_minimo_completo"] == 0
        assert structured["cobertura"]["n_nao_avaliaveis_por_motivo"] == {"COORDENADA_INVALIDA": 1, "SEM_INFORMACAO_ESPACIAL": 1}
        assert {item["tipo"] for item in structured["limitacoes"]} >= {"COBERTURA_PARCIAL", "UNIDADES_NAO_AVALIAVEIS"}
        rows = {row["Código do alvo"]: row for row in imported["rows"]}
        june = {code: june for _, code, _, june in UPLOAD}
        for code in ("1001", "1002", "1003", "1004"):
            assert rows[code]["Distância (km)"] == min(km(june[code], june["1001"]), km(june[code], june["1003"])), code
            assert rows[code]["Alcance"] == "Entre as referências avaliáveis"
        # DELTA tem GAMA como mais próxima, na coordenada de junho; a de janeiro daria outra distância.
        assert rows["1004"]["Referência mais próxima"] == "GAMA" and rows["1003"]["Distância (km)"] == 0
        assert rows["1004"]["Distância (km)"] != km(june["1004"], UPLOAD[2][2])
        assert rows["1005"]["Distância (km)"] is None and rows["1006"]["Distância (km)"] is None  # ausência não vira zero
        assert "SEM_INFORMACAO_ESPACIAL" in rows["1006"]["Condição"] and "COORDENADA_INVALIDA" in rows["1005"]["Condição"]
        with page.expect_download() as download:
            board.get_by_role("button", name="CSV", exact=True).click()
        assert_same_rows(exported_rows(download), imported["rows"])
        page.screenshot(path=str(OUTPUT / "nearest-02-base-importada.png"), full_page=True)

        workspace(page, "preparation")
        # Tela estreita: controles de alvos e referências acessíveis, sem rolagem horizontal da página.
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 844})
            expect(setup).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), width
        page.screenshot(path=str(OUTPUT / "nearest-03-mobile.png"), full_page=True)
        assert not failures, failures
        assert not llm_calls, "a jornada não usa o canal do LLM"
        browser.close()
    print("Jornada da referência mais próxima: OK")


if __name__ == "__main__":
    main()
