"""Jornada dos critérios combinados (Bloco 2, Etapa 2) na interface conversacional, em desktop e celular.

Servidor serve_ui_offline.py (nunca chama Gemini). Base importada fictícia com coordenadas variadas:
os cinco comandos pedidos (densidade, distância acrescentada com E, ordenação com esclarecimento da
direção, N primeiros e comparação com o conjunto anterior), régua com resultado não vigente até nova
execução, exportações, histórico e cliques repetidos. Um trecho curto usa o catálogo sintético do
Bloco 1 (resultado vazio). Nenhum dado real; capturas ficam em .local/ui-validation/ (ignorada pelo Git).
"""
import csv
import io
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from pyproj import Geod
from ui_support import URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
GEOD = Geod(ellps="GRS80")
# nome, código, latitude, longitude, quantidade, população (fictícios)
UNITS = [("ALFA", "2001", -3.0, -60.0, 10, 10000), ("BETA", "2002", -3.5, -61.0, 59, 25000),
         ("GAMA", "2003", -2.5, -56.7, 30, 10000), ("DELTA", "2004", -2.4, -54.7, 40, 10000),
         ("EPSILON", "2005", -4.0, -63.0, 5, 10000), ("ZETA", "2006", -6.0, -66.0, 15, 10000),
         ("ETA", "2007", 95.0, -60.0, 12, 10000), ("TETA", "2008", -7.0, -70.0, 8, 10000)]
POINT = {code: (lat, lon) for _, code, lat, lon, _, _ in UNITS}


def nearest_km(code, refs=("2003", "2004")):
    return min(GEOD.inv(POINT[code][1], POINT[code][0], POINT[r][1], POINT[r][0])[2] / 1000 for r in refs)


def exported(download):
    return list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))


def states(body):
    return {item["elemento"][5:]: item["estado"] for item in body["metadata"]["criterios"]["avaliacoes"]}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p, tempfile.TemporaryDirectory(prefix="adt-criteria-ui-") as folder:
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
        builder = inline.get_by_role("group", name="Critérios combinados")
        status = board.get_by_test_id("result-status")

        def send(message, expected):
            chat.locator("#assistant-input").fill(message)
            chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
            expect(chat.locator("#assistant-input")).to_be_enabled(timeout=60000)
            expect(chat.get_by_text(expected, exact=False).last).to_be_visible()

        def execute(name="Executar análise", double=False):
            button = inline.get_by_role("button", name=name, exact=True)
            expect(button).to_be_enabled(timeout=60000)
            before = len(analyses)
            with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=120000) as event:
                button.dblclick() if double else button.click()
            assert event.value.status == 200, event.value.text()[:500]
            expect(board.locator("h3", has_text="Critérios combinados").first).to_be_visible()
            page.wait_for_timeout(400)
            assert len(analyses) == before + 1, "uma execução por pedido, mesmo com clique duplo"
            return event.value.json()

        # Base importada fictícia (o arquivo fica no disco: cada pré-exame e execução o reenvia).
        lines = ["municipio;codigo_territorial;periodo;categoria;quantidade;populacao;latitude;longitude"]
        for period in ("202401", "202406"):
            lines += [f"{n};{c};{period};MEDICINA;{q};{pop};{lat};{lon}" for n, c, lat, lon, q, pop in UNITS]
        source = Path(folder) / "base_ficticia.csv"
        source.write_text("\n".join(lines) + "\n", encoding="utf-8")
        page.get_by_label("Importar arquivo de dados").set_input_files(str(source))
        expect(chat.get_by_text("Recebi sua base", exact=False)).to_be_visible(timeout=60000)

        # Ambiguidade material: quantidade ou densidade? Nada é presumido.
        send("Mostre os municípios com menos de 2 médicos.", "pode indicar a quantidade de profissionais ou a densidade")
        # 1. Critério de densidade com operador explícito.
        send("Mostre os municípios com menos de 2 médicos por mil habitantes.", "“menos de” → <")
        expect(builder).to_be_visible()
        expect(builder.get_by_label("Valor de c1")).to_have_value("2")
        expect(builder.get_by_label("Operador de c1")).to_have_value("<")
        assert not analyses and not llm_calls
        inline.get_by_label("Filtrar por período").select_option("202406")
        inline.get_by_label("Unidade de contagem").select_option("pessoas")
        inline.get_by_text("Confirmo que os dados selecionados correspondem à força de trabalho em saúde.").click()
        inline.get_by_text("Confirmo que a população corresponde aos territórios e períodos analisados.").click()
        inline.get_by_role("button", name="Confirmar correspondências", exact=True).click()
        first = execute(double=True)
        assert states(first) == {"2001": "ATENDE", "2002": "NAO_ATENDE", "2003": "NAO_ATENDE", "2004": "NAO_ATENDE",
                                 "2005": "ATENDE", "2006": "ATENDE", "2007": "ATENDE", "2008": "ATENDE"}
        results = board.get_by_role("region", name="Territórios classificados")
        expect(results.get_by_text("Atendem (5)", exact=True)).to_be_visible()
        expect(results.locator(".data-table tbody tr")).to_have_count(5)
        expect(board.get_by_role("listitem").filter(has_text="não constituem critério legal, sanitário ou científico")).to_be_visible()
        page.screenshot(path=str(OUTPUT / "criteria-01-densidade.png"), full_page=True)

        # 2. Distância acrescentada com E; referências definidas pelo usuário (critério ≥ 3).
        send("Agora considere também distância superior a 150 km.", "nenhuma referência foi escolhida pelo sistema")
        expect(builder.get_by_label("Combinação atual")).to_contain_text("E distância à referência mais próxima > 150 km")
        setup = builder.get_by_role("group", name="Definição das referências")
        expect(setup.get_by_role("radio", checked=True)).to_have_count(0)
        setup.get_by_label("Critério simples de densidade").check()
        setup.get_by_label("Operador do critério").select_option(">=")
        setup.get_by_label("Valor do critério").fill("3")
        inline.get_by_label("Referencial geodésico").select_option("SIRGAS2000")
        second = execute()
        result = states(second)
        for code in ("2001", "2005", "2006", "2008"):
            assert result[code] == ("ATENDE" if nearest_km(code) > 150 else "NAO_ATENDE"), code
        assert result["2007"] == "NAO_AVALIAVEL" and result["2002"] == "NAO_ATENDE"
        values = {item["elemento"][5:]: item["nos"]["c2"].get("valor") for item in second["metadata"]["criterios"]["avaliacoes"]}
        assert values["2001"] == nearest_km("2001") and values["2007"] is None  # ausência não vira zero
        results.get_by_text("Não avaliáveis (1)", exact=True).click()
        expect(results.locator(".data-table tbody tr")).to_have_count(1)
        expect(results.locator(".data-table tbody tr")).to_contain_text("DEPENDENCIA_NAO_AVALIAVEL ← c2: COORDENADA_INVALIDA")
        with page.expect_download() as download:
            results.get_by_role("button", name="Exportar este recorte (CSV)", exact=True).click()
        assert [row["Código"] for row in exported(download)] == ["2007"]

        # 3. Ordenação: a direção é perguntada, nunca presumida.
        send("Ordene esses municípios pela distância.", "do maior para o menor (decrescente) ou do menor para o maior")
        send("Decrescente.", "Ordenação por distância à referência mais próxima (decrescente)")
        third = execute()
        ranking = third["metadata"]["criterios"]["ordenacao"]
        expected = sorted(["2001", "2005", "2006", "2008"], key=lambda code: -nearest_km(code))
        assert [item["id"][5:] for item in ranking["posicoes"]] == expected
        assert [item["posicao"] for item in ranking["posicoes"]] == [1, 2, 3, 4]
        # 4. N primeiros.
        send("Mostre os 20 primeiros.", "Seleção dos 20 primeiros da ordenação")
        fourth = execute()
        assert len(fourth["metadata"]["criterios"]["selecao"]["membros"]) == 4  # menos de 20 avaliáveis no conjunto
        # 5. Comparação com o conjunto anterior compatível.
        send("Compare esse conjunto com o anterior.", "Comparação preparada com o resultado 3")
        fifth = execute()
        comparison = fifth["metadata"]["criterios"]["comparacao"]
        assert {item["id"][5:] for item in comparison["em_ambos"]} == set(expected)
        assert comparison["somente_atual"] == [] and comparison["somente_anterior"] == []
        expect(results.get_by_text("Comparação com resultado 3", exact=False)).to_be_visible()
        page.screenshot(path=str(OUTPUT / "criteria-02-comparacao.png"), full_page=True)

        # Exportações completas: todas as linhas e os metadados estruturados.
        with page.expect_download() as download:
            board.get_by_role("button", name="CSV", exact=True).click()
        assert len(exported(download)) == len(fifth["rows"]) == 8
        with page.expect_download() as download:
            board.get_by_role("button", name="Método e parâmetros", exact=True).click()
        method = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert method["criterios"] == fifth["metadata"]["criterios"] and method["result_id"] == fifth["result_id"]

        # Régua: mudar o valor torna o resultado não vigente até nova execução validada pelo motor.
        builder.get_by_label("Valor de c1").fill("1,3")
        expect(status).to_have_text("Resultado histórico válido · não vigente no contexto atual")
        sixth = execute()
        assert states(sixth)["2006"] == "NAO_ATENDE" and states(sixth)["2001"] == "ATENDE"  # ZETA tem densidade 1,5
        expect(status).to_have_text("Resultado válido e vigente no contexto atual")
        assert builder.get_by_label("Régua de c1").count() == 1  # faixa observada disponível após o resultado

        # Retomar o resultado atual restaura seus critérios e reaproveita o cálculo idêntico.
        details = board.locator("details", has=page.locator("summary", has_text="Consultar solicitação e parâmetros"))
        details.locator("summary").click()
        board.get_by_role("button", name="Retomar parâmetros deste resultado", exact=True).click()
        expect(builder.get_by_label("Valor de c1")).to_have_value("1,3")
        expect(builder.get_by_label("Valor de c2")).to_have_value("150")
        calls = len(analyses)
        inline.get_by_role("button", name="Executar análise", exact=True).click()
        expect(page.get_by_text("Resultado existente recuperado, sem recalcular.", exact=True)).to_be_visible()
        assert len(analyses) == calls

        # Reutilização: o conjunto que atende vira a seleção territorial (Bloco 1 e Bloco 2).
        matched = sixth["metadata"]["criterios"]["contagens"]["ATENDE"]
        board.get_by_role("button", name=f"Usar os que atendem como seleção territorial ({matched})", exact=True).click()
        selection = page.get_by_role("region", name="Seleção territorial compartilhada")
        expect(selection.get_by_text(f"{matched} selecionados", exact=True)).to_be_visible()

        # Celular: critérios e resultados acessíveis, sem rolagem horizontal da página.
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 844})
            expect(builder).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), width
        page.screenshot(path=str(OUTPUT / "criteria-03-mobile.png"), full_page=True)

        # Base Brasil sintética do Bloco 1. Com o recorte nacional escolhido, o comando volta ao recorte
        # municipal e só aplica a condição depois que ele está pronto (a preparação restaurada não a apaga).
        page.set_viewport_size({"width": 1280, "height": 900})
        chat.get_by_text("Trocar fonte de dados", exact=True).click()
        chat.get_by_role("button", name="Usar dados do Brasil").click()
        expect(chat.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=60000)
        inline.get_by_text("Alterar a abrangência territorial", exact=True).click()
        inline.get_by_label("Abrangência territorial").select_option("national")
        expect(inline.get_by_text("o conjunto do Brasil", exact=False)).to_be_visible(timeout=60000)
        send("Mostre os municípios com menos de 2 médicos por mil habitantes.", "“menos de” → <")
        expect(builder.get_by_label("Valor de c1")).to_have_value("2", timeout=60000)
        expect(inline.get_by_text("os municípios brasileiros", exact=False)).to_be_visible()
        # Jornada funcional no celular (390 px): nenhuma densidade abaixo de 2 → resultado vazio (RES-VAZ).
        page.set_viewport_size({"width": 390, "height": 844})
        inline.get_by_label("Escolher períodos da análise").click()
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        empty = execute("Calcular e mostrar resultado")
        assert empty["metadata"]["criterios"]["desfecho"] == "RES-VAZ"
        expect(board.get_by_role("listitem").filter(has_text="resultado vazio, RES-VAZ")).to_be_visible()
        expect(board.get_by_role("region", name="Territórios classificados").get_by_text("Atendem (0)", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        page.screenshot(path=str(OUTPUT / "criteria-04-mobile-brasil.png"), full_page=True)
        assert not failures, failures
        assert not llm_calls, "a jornada não usa o canal do LLM"
        browser.close()
    print("Jornada dos critérios combinados: OK")


if __name__ == "__main__":
    main()
