"""Teste de navegador real. Servidores locais devem estar ativos.

py -m pip install -r backend/requirements-ui.txt
$env:ADT_REAL_DATA_DIR='C:\\Users\\User\\Desktop\\Dados_Brasil'
py backend/tests/ui_smoke.py
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
from decimal import Decimal

from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[2]
output = root / ".local" / "ui-validation"
output.mkdir(parents=True, exist_ok=True)
data_dir = Path(os.environ["ADT_REAL_DATA_DIR"])
source = next(p for p in data_dir.iterdir() if p.suffix.lower() == ".csv")
digest = hashlib.sha256(source.read_bytes()).hexdigest()

with sync_playwright() as p:
    expect.set_options(timeout=120000)
    browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    page = context.new_page()
    page.set_default_timeout(60000)
    errors = []
    analyzed = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: analyzed.append(request.url) if request.url.endswith("/api/analyze") else None)
    page.goto("http://127.0.0.1:5173/")
    page.get_by_role("button", name="Li e concordo", exact=True).click()
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    page.locator('input[type="file"]').set_input_files(source)
    expect(page.get_by_role("heading", name="Configuração da análise", exact=True)).to_be_visible()
    territory = page.locator("#associacoes select").nth(0)
    expect(territory).to_have_value("municipio")
    expect(page.locator("#associacoes select").nth(2)).to_have_value("categoria_profisional")
    territory.select_option("municipio")
    page.locator("#associacoes select").nth(1).select_option("Período")
    page.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
    page.get_by_role("button", name="Selecionar análise: Densidade", exact=True).click()
    execute = page.get_by_role("button", name="Executar análise", exact=True)
    expect(execute).to_be_disabled()
    expect(page.get_by_text(re.compile(r"11.528 registros em 5.324 grupos"))).to_be_visible()
    assert not analyzed, "Selecionar um cartão não pode executar a análise"
    page.screenshot(path=str(output / "multiplicity.png"), full_page=True)
    page.get_by_role("button", name="Confirmar que o código identifica cada unidade territorial", exact=True).click()
    page.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
    page.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True).check()
    expect(execute).to_be_enabled()
    expect(territory).to_have_value("municipio")
    assert not analyzed
    with page.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=120000) as response:
        execute.click()
    assert response.value.status == 200
    result = response.value.json()
    assert result["total_rows"] == 122534
    expect(page.locator(".data-table tbody tr")).to_have_count(150)
    expect(page.get_by_role("heading", name="Densidade de profissionais", exact=True)).to_be_visible()
    assert result["metadata"]["mapping"]["territory"] == "municipio"
    assert result["metadata"]["options"]["count_unit"] == "pessoas"
    assert not result["metadata"]["options"].get("no_overlap_confirmed")
    with page.expect_download() as event:
        page.get_by_role("button", name="CSV", exact=True).click()
    # Lê o arquivo temporário do navegador: nenhum registro brasileiro vai para o Git.
    rows = list(csv.DictReader(Path(event.value.path()).read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    assert len(rows) == 122534
    try:
        original_text = source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        original_text = source.read_text(encoding="latin-1")
    dialect = csv.Sniffer().sniff(original_text[:16384], delimiters=",;")
    original = list(csv.DictReader(io.StringIO(original_text), dialect=dialect))
    mapping = result["metadata"]["mapping"]
    expected = {(r[mapping["territory"]] + " [" + r[mapping["territory_id"]] + "]", r[mapping["period"]], r[mapping["category"]]):
                (Decimal(r[mapping["count"]]), Decimal(r[mapping["population"]])) for r in original}
    max_error = Decimal(0)
    assert len(expected) == len(rows)
    for row in rows:
        quantity, population = expected[(row["Território"], row["Período"], row["Categoria"])]
        assert Decimal(row["Quantidade"]) == quantity and Decimal(row["População"]) == population
        deviation = abs(Decimal(row["Densidade por 1.000"]) - quantity * 1000 / population)
        max_error = max(max_error, deviation)
        assert deviation < Decimal("1e-10")
    with page.expect_download() as event:
        page.get_by_role("button", name="Método e parâmetros", exact=True).click()
    method = json.loads(Path(event.value.path()).read_text(encoding="utf-8"))
    assert method["operation"] == "density" and len(method["data_sha256"]) == 64
    page.screenshot(path=str(output / "density.png"), full_page=True)
    page.get_by_label("Filtrar por período", exact=True).select_option("202406")
    expect(page.get_by_role("button", name="CSV", exact=True)).to_be_disabled()
    expect(execute).to_be_enabled()
    with page.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=120000) as response:
        execute.click()
    assert response.value.status == 200
    selected = response.value.json()
    assert all(row["Período"] == "202406" for row in selected["rows"])
    assert not errors, errors
    # Responsividade e preservação dos dez cartões em tela estreita.
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(output / "mobile.png"), full_page=True)
    assert page.locator("#analises .analysis-card").count() == 1
    assert page.locator("#analises .carousel-progress > span").count() == 10
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
    evidence = {"gate": "Densidade ponta a ponta", "status": "PASS", "source_sha256": digest,
        "territory": "municipio", "territory_id": "ibge", "count_unit": "pessoas distintas no recorte",
        "ui_execution_http_status": 200, "exported_rows": len(rows), "independently_checked_rows": len(rows),
        "maximum_decimal_error": str(max_error), "filtered_rows": len(selected["rows"]),
        "page_errors": errors, "mobile_width": 390, "original_preserved": True}
    # Falha simulada do exame: uma habilitação anterior jamais pode ser reutilizada.
    page.route("**/api/preflight", lambda route: route.fulfill(status=503, content_type="application/json", body='{"detail":"Falha simulada de teste"}'))
    page.get_by_label("Filtrar por período", exact=True).select_option("202401")
    expect(page.get_by_text("Verificação não concluída", exact=True)).to_be_visible()
    expect(execute).to_be_disabled()
    expect(page.get_by_role("button", name="CSV", exact=True)).to_be_disabled()
    page.unroute("**/api/preflight")
    browser.close()

assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
(output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
print("DENSITY UI PASS: real upload, Municipality preserved, multiplicity resolved, explicit execution, 122534 CSV rows independently checked against the original using Decimal, metadata, filters, mobile, no page errors; source unchanged.")
