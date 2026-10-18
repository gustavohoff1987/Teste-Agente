"""Regressão E2E da exploração visual, filtros, paginação e configuração da origem.

Executar contra serve_ui_offline.py e Chromium. Dados totalmente sintéticos.
Verifica densidade e distribuição com todos os territórios acessíveis.
"""
import csv
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import execute_analysis, URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
COUNT = 180


def dataset() -> str:
    lines = ["municipio;cod_ibge;periodo;categoria;quantidade;populacao;latitude;longitude"]
    for period in ("202401", "202406"):
        for i in range(COUNT):
            # Distribuição diversa, coordenadas fictícias geograficamente válidas.
            value = 3 + (i % 41) + (1 if period == "202406" else 0)
            row = [f"TERRITORIO {i+1:02}", f"{600000+i}", period, "MEDICINA",
                   str(value), str(950 + 7*i), f"{-3.0-i*0.08:.5f}", f"{-60.0-i*0.07:.5f}"]
            lines.append(";".join(row))
    return "\n".join(lines) + "\n"


def start(page, source: Path, operation: str):
    page.goto(URL)
    page.get_by_role("button", name="Li e concordo", exact=True).click()
    chat = page.locator("#assistente")
    page.get_by_label("Importar arquivo de dados").set_input_files(str(source))
    expect(chat.get_by_text("Recebi sua base", exact=False)).to_be_visible(timeout=60000)
    if operation == "Distribuição":
        # O carrossel mostra um card por vez: Densidade → Quantitativos → Distribuição.
        for _ in range(2):
            chat.get_by_role("button", name="Próxima análise", exact=True).click()
    chat.get_by_role("button", name="Selecionar análise: " + operation, exact=True).click()
    inline = chat.locator("#preparacao-conversacional")
    inline.get_by_role("combobox", name="Unidade de contagem").select_option("pessoas")
    inline.get_by_label("Filtrar por período").select_option("202406")
    if operation == "Distribuição":
        # A confirmação do denominador só aparece após selecionar densidade.
        inline.get_by_role("combobox", name="Indicador", exact=True).select_option("density")
    inline.get_by_label("Confirmo que os dados selecionados correspondem à força de trabalho em saúde.").check()
    inline.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados.").check()
    inline.get_by_role("button", name="Confirmar correspondências").click()
    return inline


def execute(page, inline):
    control = inline.get_by_role("button", name="Executar análise", exact=True)
    expect(control).to_be_enabled(timeout=60000)
    with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=120000) as event:
        execute_analysis(page, control)
    assert event.value.status == 200, event.value.text()[:1200]
    result = event.value.json()
    assert result["metadata"]["representacao"]["geometria"]["pendencia"] == "REFERENCIAL_GEODESICO"
    assert result["metadata"]["representacao"]["geometria"]["estado"] == "INDISPONIVEL"
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="adt-ui-visibility-") as tmp, sync_playwright() as p:
        csv_path = Path(tmp) / "dados_sinteticos_180.csv"
        csv_path.write_text(dataset(), encoding="utf-8")
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1365, "height": 900}, accept_downloads=True)
        offline(context)
        errors = []
        context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))

        density_page = context.new_page()
        density_inline = start(density_page, csv_path, "Densidade")
        density_result = execute(density_page, density_inline)
        assert density_result["total_rows"] == COUNT
        board = density_page.locator("#resultados")
        tab = board.get_by_role("tab", name="Gráficos", exact=True)
        expect(tab).to_have_attribute("aria-selected", "true")
        bars = board.get_by_test_id("scrollable-bars")
        expect(bars).to_have_attribute("data-total", str(COUNT))
        expect(bars.get_by_role("button").first).to_contain_text("TERRITORIO 01")
        board.get_by_label("Indicador das barras", exact=True).select_option("Quantidade")
        expect(bars).to_have_accessible_name("Quantitativo (profissionais) · todos os territórios do resultado")
        expect(bars.get_by_role("button").first).to_have_attribute("title", "TERRITORIO 01 [600000]: 4 profissionais")
        bars.get_by_role("region", name="Barras por território", exact=True).evaluate("el => el.scrollTop = el.scrollHeight")
        expect(bars.get_by_role("button").last).to_contain_text(f"TERRITORIO {COUNT:02}")

        table = board.get_by_test_id("result-table")
        expect(table.locator("tbody tr")).to_have_count(150)
        table.get_by_role("button", name="Próxima página", exact=True).click()
        expect(table.locator("tbody tr")).to_have_count(COUNT - 150)
        table.get_by_role("button", name="Página anterior", exact=True).click()
        table.get_by_label("Filtrar Quantidade", exact=True).fill(">= 30")
        expected = [row for row in density_result["rows"] if row["Quantidade"] >= 30]
        expect(table.locator("tbody tr")).to_have_count(len(expected))
        table.get_by_label("Filtrar Território", exact=True).fill("territorio 01")
        expected_text = [row for row in expected if "TERRITORIO 01" in row["Território"]]
        expect(table.locator("tbody tr")).to_have_count(len(expected_text))
        table.get_by_label("Filtrar Território", exact=True).fill("")
        table.get_by_role("button", name="Ordenar tabela por Quantidade", exact=True).click()
        table.get_by_role("button", name="Ordenar tabela por Quantidade", exact=True).click()
        with density_page.expect_download() as event:
            table.get_by_role("button", name="Exportar tabela filtrada (CSV)", exact=True).click()
        with Path(event.value.path()).open(encoding="utf-8-sig", newline="") as stream:
            exported = list(csv.DictReader(stream, delimiter=";"))
        assert len(exported) == len(expected) and all(float(row["Quantidade"]) >= 30 for row in exported)
        assert [float(row["Quantidade"]) for row in exported] == sorted((row["Quantidade"] for row in expected), reverse=True)
        with density_page.expect_download() as event:
            board.get_by_text("Opções técnicas avançadas", exact=True).click()
            board.get_by_role("button", name="Baixar registro técnico (JSON)", exact=True).click()
        method = json.loads(Path(event.value.path()).read_text(encoding="utf-8"))
        applied = method["representacao_aplicada"]["tabela"]
        assert applied["filtros"]["Quantidade"] == ">= 30" and applied["total_filtrado"] == len(expected)
        assert applied["ordenacao"] == {"key": "Quantidade", "ascending": False}
        table.get_by_role("button", name="Limpar filtros da tabela", exact=True).click()
        expect(table.locator("tbody tr")).to_have_count(150)
        for removed in ("Consultar solicitação e parâmetros", "Selecionar territórios deste resultado", "Imagem dos gráficos (PNG)"):
            expect(board.get_by_text(removed, exact=True)).to_have_count(0)
        density_page.screenshot(path=str(OUTPUT / "diagnostico_visibilidade_densidade_sem_selecao.png"), full_page=True)

        table.locator("tbody tr").first.click()
        expect(board.get_by_role("figure", name="Quantitativo (profissionais) · territórios selecionados", exact=True)).to_be_visible()
        density_page.screenshot(path=str(OUTPUT / "diagnostico_visibilidade_densidade_com_selecao.png"), full_page=True)

        board.get_by_role("tab", name="Mapa (indisponível)", exact=True).click()
        expect(board.get_by_text("Mapa indisponível para este resultado", exact=True)).to_be_visible()
        expect(board.get_by_label("Referencial geodésico para o mapa")).to_have_count(0)
        density_page.get_by_role("button", name="2. Preparação").click()
        density_inline.get_by_text("Ver outras condições da análise", exact=True).click()
        density_inline.get_by_label("Referencial das coordenadas importadas", exact=True).select_option("SIRGAS2000")
        density_inline.get_by_label("Separador decimal das coordenadas importadas", exact=True).select_option("decimal_point")
        confirmation = density_inline.get_by_role("button", name="Confirmar correspondências", exact=True)
        if confirmation.count():
            confirmation.click()
        expect(density_inline.get_by_role("button", name="Executar análise", exact=True)).to_be_enabled(timeout=60000)
        with density_page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=120000) as event:
            execute_analysis(density_page, density_inline.get_by_role("button", name="Executar análise", exact=True))
        assert event.value.status == 200, event.value.text()[:1000]
        geometry = event.value.json()["metadata"]["representacao"]["geometria"]
        assert geometry["estado"] == "DISPONIVEL" and len(geometry["ids"]) == COUNT
        expect(board.get_by_test_id("territory-map")).to_be_visible()
        density_page.screenshot(path=str(OUTPUT / "diagnostico_visibilidade_mapa_disponivel.png"), full_page=True)

        distribution_page = context.new_page()
        dist_inline = start(distribution_page, csv_path, "Distribuição")
        distribution = execute(distribution_page, dist_inline)
        assert distribution["total_rows"] == 5
        assert len(distribution["detail_rows"]) == COUNT
        dist_board = distribution_page.locator("#resultados")
        expect(dist_board.get_by_role("tab", name="Gráficos", exact=True)).to_have_attribute("aria-selected", "true")
        expect(dist_board.get_by_role("figure", name="Territórios por grupo da distribuição", exact=True)).to_be_visible()
        expect(dist_board.get_by_test_id("scrollable-bars")).to_have_attribute("data-total", str(COUNT))
        expect(dist_board.get_by_text("Quantas unidades pertencem a cada quintil?", exact=True)).to_be_visible()
        expect(dist_board.locator("#tabela-resultado tbody tr")).to_have_count(150)
        group = distribution["detail_rows"][0]["Quintil"]
        detail_table = dist_board.get_by_test_id("result-table")
        detail_table.get_by_label("Filtrar Quintil", exact=True).fill(group)
        expect(detail_table.locator("tbody tr")).to_have_count(sum(row["Quintil"] == group for row in distribution["detail_rows"]))
        distribution_page.screenshot(path=str(OUTPUT / "diagnostico_visibilidade_distribuicao.png"), full_page=True)

        # Linhas: mais de oito territórios permanecem acessíveis por páginas sem misturar competências.
        density_inline.get_by_label("Filtrar por período", exact=True).select_option("")
        confirmation = density_inline.get_by_role("button", name="Confirmar correspondências", exact=True)
        if confirmation.count():
            confirmation.click()
        with density_page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=120000) as event:
            execute_analysis(density_page, density_inline.get_by_role("button", name="Executar análise", exact=True))
        assert event.value.status == 200, event.value.text()[:1000]
        assert event.value.json()["metadata"]["representacao"]["serie"]
        board.get_by_role("tab", name="Gráficos", exact=True).click()
        series = board.get_by_role("navigation", name="Territórios das séries", exact=True)
        expect(series).to_contain_text(f"Territórios 1 a 8 de {COUNT}")
        series.get_by_role("button", name="Próximos territórios", exact=True).click()
        expect(series).to_contain_text(f"Territórios 9 a 16 de {COUNT}")
        expect(board.locator(".recharts-line")).to_have_count(8)

        # Selecionar um território após paginar as séries retorna à primeira página.
        board.get_by_test_id("result-table").locator("tbody tr").first.click()
        expect(series).to_have_count(0)
        expect(board.locator(".recharts-line")).to_have_count(1)
        board.get_by_role("button", name="Limpar seleção", exact=True).click()
        expect(series).to_contain_text(f"Territórios 1 a 8 de {COUNT}")
        visual_filter = board.get_by_role("radiogroup", name="Filtro visual dos territórios", exact=True)
        visual_filter.get_by_text("Minha seleção (0)", exact=True).click()
        expect(board.locator(".recharts-line")).to_have_count(0)
        expect(board.get_by_text("Nenhum território selecionado possui série temporal neste resultado.", exact=True)).to_be_visible()
        visual_filter.get_by_text("Todos", exact=True).click()
        expect(board.locator(".recharts-line")).to_have_count(8)

        assert not errors, errors
        report = {"status": "PASS", "territorios_sinteticos": COUNT,
                  "barras_iniciais_e_ultimo_territorio": True, "indicador_profissionais": True,
                  "tabela_filtros_ordenacao_paginacao_csv": True, "mapa_importado_sem_premissa_automatica": True,
                  "mapa_apos_configurar_origem": True, "distribuicao_grupos_e_barras": True,
                  "series_com_paginacao": True, "page_errors": errors}

        (OUTPUT / "diagnostico_visibilidade.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        browser.close()
        print("VISUALIZATION VISIBILITY DIAGNOSTIC PASS:", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
