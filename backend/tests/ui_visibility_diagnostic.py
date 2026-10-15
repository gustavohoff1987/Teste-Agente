"""Diagnóstico E2E: distinguir implementação visual de descobribilidade, sem alterar produto.

Executar contra serve_ui_offline.py e Chromium. Dados totalmente sintéticos.
Verifica densidade e distribuição em universo acima do limite de 40 barras.
"""
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
COUNT = 60


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
        control.click()
    assert event.value.status == 200, event.value.text()[:1200]
    result = event.value.json()
    assert result["metadata"]["representacao"]["geometria"]["pendencia"] == "REFERENCIAL_GEODESICO"
    assert result["metadata"]["representacao"]["geometria"]["estado"] == "INDISPONIVEL"
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="adt-ui-visibility-") as tmp, sync_playwright() as p:
        csv_path = Path(tmp) / "dados_sinteticos_60.csv"
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
        expect(board.get_by_text("Selecione até 40 territórios", exact=False)).to_be_visible()
        assert board.locator("section[aria-label='Exploração visual'] figure").count() == 0
        density_page.screenshot(path=str(OUTPUT / "diagnostico_visibilidade_densidade_sem_selecao.png"), full_page=True)

        board.locator("#tabela-resultado tbody tr").first.click()
        expect(board.get_by_role("figure", name="Densidade", exact=False)).to_be_visible()
        assert board.locator("section[aria-label='Exploração visual'] figure").count() >= 1
        density_page.screenshot(path=str(OUTPUT / "diagnostico_visibilidade_densidade_com_selecao.png"), full_page=True)

        board.get_by_role("tab", name="Mapa (indisponível)").click()
        expect(board.get_by_text("Mapa indisponível (BLQ-DAD)", exact=True)).to_be_visible()
        board.get_by_label("Referencial geodésico para o mapa").select_option("SIRGAS2000")
        board.get_by_label("Separador decimal das coordenadas para o mapa").select_option("decimal_point")
        board.get_by_role("button", name="Aplicar à preparação").click()
        expect(density_inline.get_by_role("button", name="Executar análise")).to_be_enabled(timeout=60000)
        with density_page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=120000) as event:
            density_inline.get_by_role("button", name="Executar análise").click()
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
        assert dist_board.locator("section[aria-label='Exploração visual'] figure").count() == 0
        expect(dist_board.get_by_text("Selecione até 40 territórios", exact=False)).to_be_visible()
        # O gráfico de frequências é real, mas está fora da aba Gráficos.
        expect(dist_board.get_by_text("Quantas unidades pertencem a cada quintil?", exact=True)).to_be_visible()
        assert dist_board.locator("#tabela-resultado tbody tr").count() == COUNT
        distribution_page.screenshot(path=str(OUTPUT / "diagnostico_visibilidade_distribuicao.png"), full_page=True)

        assert not errors, errors
        report = {
            "status": "PASS",
            "source": "synthetic 60 municipalities, two periods, explicitly selected 202406",
            "density": {"rows": COUNT, "default_view": "graficos",
                        "no_territorial_bars_before_selection": True,
                        "territorial_bars_after_selection": True,
                        "map_requires_explicit_crs": True,
                        "map_available_after_declaring_crs_and_rerunning": True},
            "distribution": {"classes": 5, "detail_rows": COUNT,
                             "no_territorial_bars_before_selection": True,
                             "frequency_chart_exists_outside_graphs_tab": True},
            "page_errors": errors,
        }
        (OUTPUT / "diagnostico_visibilidade.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        browser.close()
        print("VISUALIZATION VISIBILITY DIAGNOSTIC PASS:", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
