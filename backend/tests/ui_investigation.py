"""Investigação progressiva pela interface e API reais; sem chamadas ao provedor.

Roda com catálogo sintético e base versionada (somente leitura). Nenhum resultado é
fabricado: todos os resultados usados na jornada vêm de /api/analyze.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline, select

OUTPUT = Path(__file__).resolve().parents[2] / '.local/ui-validation'


def main():
    real = os.getenv('ADT_BLOCK1_REAL') == '1'
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv('ADT_BROWSER_CHANNEL', 'chrome'))
        context = browser.new_context(viewport={'width': 1360, 'height': 900}, accept_downloads=True)
        offline(context)
        context.add_init_script('window.__ADT_TEST__ = true')
        page = context.new_page()
        page.set_default_timeout(15000)
        errors, requests, results = [], [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda r: requests.append(r) if r.url.endswith('/api/analyze') else None)
        page.goto(URL)
        page.get_by_role('button', name='Li e concordo', exact=True).click()
        chat = page.locator('#assistente')
        board = page.locator('#resultados')
        overview = page.get_by_test_id('investigation-overview')
        inline = page.locator('#preparacao-conversacional')

        def send(message, response=False):
            print('Pedido: ' + message, flush=True)
            page.locator('#assistant-input').fill(message)
            if response:
                with page.expect_response(lambda r: r.url.endswith('/api/llm/interpret-context'), timeout=90000) as event:
                    chat.get_by_role('button', name='Enviar mensagem', exact=True).click()
                assert event.value.status == 200, event.value.text()
                answer = event.value.json()
            else:
                chat.get_by_role('button', name='Enviar mensagem', exact=True).click()
                answer = None
            expect(page.locator('#assistant-input')).to_be_enabled(timeout=90000)
            return answer

        def calculate():
            print('Executando etapa ' + str(len(results) + 1), flush=True)
            button = inline.get_by_role('button', name='Calcular e mostrar resultado', exact=True)
            expect(button).to_be_enabled(timeout=90000)
            with page.expect_response(lambda r: r.url.endswith('/api/analyze'), timeout=120000) as event:
                button.click()
            assert event.value.status == 200, event.value.text()
            result = event.value.json()
            results.append(result)
            print('Resultado recebido: ' + result['title'], flush=True)
            expect(board.get_by_test_id('result-title')).to_have_text(result['title'])
            expect(overview.get_by_test_id('investigation-card')).to_have_count(min(6, len(results)))
            return result

        def open_stage(index):
            print('Reabrindo etapa ' + str(index + 1), flush=True)
            button = overview.get_by_test_id('open-investigation-' + str(index))
            expect(button).to_be_enabled(timeout=90000)
            button.click()
            expect(board.get_by_test_id('result-title')).to_have_text(results[index]['title'])

        def method():
            with page.expect_download() as download:
                board.get_by_role('button', name='Método e parâmetros', exact=True).click()
            return json.loads(Path(download.value.path()).read_text(encoding='utf-8'))

        send('Olá')
        expect(overview).to_contain_text('0 resultados disponíveis')
        chat.get_by_role('button', name='Usar dados do Brasil', exact=False).click()
        expect(page.get_by_test_id('current-source')).to_be_visible(timeout=90000)
        send('Mostre a densidade médica dos municípios do Amazonas em junho de 2024.')
        first = calculate()
        assert first['total_rows'] == (62 if real else 3)
        rows = board.locator('#tabela-resultado tbody tr')
        rows.nth(0).click()
        rows.nth(1).click()
        selected = method()['representacao_aplicada']['selecao_visual']
        assert len(selected) == 2
        board.get_by_label('Filtrar Território', exact=True).fill(first['rows'][0]['Território'])
        expect(rows).to_have_count(1)
        board.get_by_role('button', name='Recolher análise', exact=True).click()
        expect(board.get_by_test_id('result-title')).not_to_be_visible()
        page.emulate_media(media='print')
        expect(board.get_by_test_id('result-title')).to_be_visible()
        page.emulate_media(media='screen')
        board.get_by_role('button', name='Expandir análise', exact=True).click()
        expect(rows).to_have_count(1)

        # Escolha direta mantém a preparação explícita e não depende de inferência do chat.
        chat.get_by_text('Escolher outra análise', exact=True).click()
        select(page, 'Distribuição')
        inline.get_by_role('combobox', name='Indicador', exact=True).select_option('density')
        second = calculate()
        assert second['metadata']['operation'] == 'distribution'
        assert second['metadata']['options']['quantile_count'] == 5
        open_stage(0)
        expect(rows).to_have_count(1)
        assert method()['representacao_aplicada']['selecao_visual'] == selected
        expect(overview.get_by_test_id('transfer-selection-1')).to_be_enabled()
        overview.get_by_test_id('transfer-selection-1').click()
        expect(board.get_by_test_id('result-title')).to_have_text(second['title'])
        assert method()['representacao_aplicada']['selecao_visual'] == selected
        # Classes e valores permanecem os do motor; a seleção não modifica a preparação.
        expect(board.get_by_role('region', name='Territórios selecionados')).to_be_visible()
        assert len(requests) == 2
        if real:
            board.get_by_role('tab', name='Mapa', exact=True).click()
            expect(board.get_by_test_id('territory-map')).to_be_visible()
            assert page.evaluate('window.__adtMapModel.selected') == selected

        open_stage(0)
        answer = send('O que esse resultado significa?', response=True)
        assert answer['result_reference']['result_id'] == first['result_id']
        assert answer['result_reference']['origin'] == 'BACKEND_VERIFIED_RESULT'
        assert not answer['executed'] and len(requests) == 2
        board.get_by_role('button', name='Limpar filtros da tabela', exact=True).click()
        expect(rows).to_have_count(first['total_rows'])
        board.get_by_role('button', name='Usar seleção na próxima análise', exact=True).click()
        send('Compare os selecionados.')
        inline.get_by_label('As medidas, unidades e populações são comparáveis entre os territórios.').check()
        compared = calculate()
        assert set(compared['metadata']['options']['territory_ids']) == set(selected)
        open_stage(0)
        expect(overview.get_by_test_id('transfer-selection-2')).to_be_disabled()
        expect(overview.get_by_test_id('investigation-card').nth(2)).to_contain_text('Recortes territoriais diferentes')
        assert len(requests) == 3

        # Parâmetros atuais não alteram os três resultados já calculados.
        send('Mostre a densidade médica dos municípios do Amazonas em janeiro de 2024.')
        expect(board.get_by_test_id('result-title')).to_have_text(first['title'])
        assert method()['result_id'] == first['result_id'] and len(requests) == 3
        fourth = calculate()
        assert fourth['metadata']['periods'] == ['202401']
        open_stage(0)
        expect(overview.get_by_test_id('transfer-selection-3')).to_be_disabled()
        expect(overview.get_by_test_id('investigation-card').nth(3)).to_contain_text('Períodos diferentes')

        for width in (1360, 768, 390):
            page.set_viewport_size({'width': width, 'height': 900})
            overview.scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.screenshot(path=str(OUTPUT / f'investigacao-{real}-{width}.png'))
        assert len(requests) == 4 and not errors, errors
        # O histórico antigo continua acessível; os novos controles não o substituem.
        history = page.get_by_role('region', name='Histórico de análises')
        history.locator('summary').click()
        expect(history.get_by_role('button')).to_have_count(4)
        page.get_by_test_id('end-session').click()
        expect(page.get_by_role('button', name='Li e concordo', exact=True)).to_be_visible(timeout=15000)
        page.get_by_role('button', name='Li e concordo', exact=True).click()
        send('Olá')
        expect(overview).to_contain_text('0 resultados disponíveis')
        assert not errors, errors
        browser.close()
    print(f'INVESTIGAÇÃO PASS: quatro operações reais, reabertura, filtros preservados, destaque compatível, recorte/período incompatíveis, conversa ancorada, exportação, responsividade e encerramento. Base real={real}', flush=True)


if __name__ == '__main__':
    main()
