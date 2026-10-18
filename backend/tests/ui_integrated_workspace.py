"""Sessões, análise independente e composição no fluxo horizontal; motor e API reais."""
import csv
import io
import json
import os
from decimal import Decimal
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
from ui_support import workspace, URL, offline, select

OUTPUT = Path(__file__).resolve().parents[2] / '.local/ui-validation'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv('ADT_BROWSER_CHANNEL', 'chrome'))
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True,
                                      reduced_motion='reduce')
        offline(context)
        page = context.new_page()
        page.set_default_timeout(20000)
        errors, requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: requests.append(request) if request.url.endswith('/api/analyze') else None)
        page.goto(URL)
        page.get_by_role('button', name='Li e concordo', exact=True).click()
        navigation = page.get_by_test_id('main-navigation')
        expect(navigation.locator(':scope > button')).to_have_count(4)
        assert navigation.locator(':scope > button').all_text_contents() == ['Início', 'Nova sessão', 'Nova análise', 'Resultados']
        expect(navigation.locator('summary')).to_contain_text('Histórico')
        expect(page.locator('aside')).to_have_count(0)
        expect(page.get_by_test_id('investigation-overview')).to_have_count(0)
        page.get_by_test_id('nav-new-analysis').click()
        expect(page.get_by_test_id('new-analysis-confirmation')).to_have_count(0)
        expect(page.get_by_test_id('analysis-catalog')).to_be_visible()
        page.get_by_role('button', name='Usar dados do Brasil', exact=False).click()
        expect(page.get_by_test_id('current-source')).to_be_visible(timeout=90000)

        def send(message):
            page.locator('#assistant-input').fill(message)
            page.get_by_role('button', name='Enviar mensagem', exact=True).click()
            expect(page.locator('#assistant-input')).to_be_enabled(timeout=90000)

        def calculate():
            button = page.locator('#preparacao-conversacional').get_by_role('button', name='Calcular e mostrar resultado', exact=True)
            expect(button).to_be_enabled(timeout=90000)
            with page.expect_response(lambda r: r.url.endswith('/api/analyze'), timeout=120000) as event:
                button.click()
            assert event.value.status == 200, event.value.text()
            result = event.value.json()
            expect(page.get_by_test_id('result-title')).to_have_text(result['title'])
            return result

        def choose_mode(mode):
            page.get_by_test_id('nav-new-analysis').click()
            expect(page.get_by_test_id('new-analysis-confirmation')).to_be_visible()
            page.get_by_test_id(mode).click()
            expect(page.get_by_test_id('new-analysis-confirmation')).to_have_count(0)

        send('Mostre a densidade médica dos municípios do Amazonas em junho de 2024.')
        first = calculate()
        old_token = requests[0].headers['x-adt-session']
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('Análise independente 1')
        page.get_by_test_id('nav-home').click()
        expect(page.locator('#welcome-title')).to_be_visible()
        expect(page.get_by_test_id('result-title')).to_have_text(first['title'])
        assert len(requests) == 1

        # Diálogo nativo: Escape e foco retornam à navegação sem alterar a análise.
        page.get_by_test_id('nav-new-analysis').click()
        page.keyboard.press('Escape')
        expect(page.get_by_test_id('nav-new-analysis')).to_be_focused()
        expect(page.get_by_test_id('result-title')).to_have_text(first['title'])
        choose_mode('confirm-new-analysis')
        expect(page.get_by_test_id('result-title')).to_have_count(0)
        expect(page.locator('#resultados')).to_have_count(0)
        select(page, 'Quantitativos')
        second = calculate()
        expect(page.get_by_test_id('investigation-card')).to_have_count(1)
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('Análise independente 2')
        choose_mode('append-diagnostic')
        select(page, 'Distribuição')
        page.locator('#preparacao-conversacional').get_by_label('Indicador', exact=True).select_option('density')
        third = calculate()
        expect(page.get_by_test_id('investigation-card')).to_have_count(2)
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('Diagnóstico 2 · 2 componentes')
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('não soma nem harmoniza valores')

        history = page.get_by_test_id('analysis-history-menu')
        history.locator('summary').click()
        expect(history.get_by_role('button')).to_have_count(3)
        expect(history).to_contain_text('Análise independente 1')
        expect(history).to_contain_text('Diagnóstico 2 · 2 componentes')
        page.keyboard.press('Escape')
        expect(history).not_to_have_attribute('open', '')
        expect(history.locator('summary')).to_be_focused()
        history.locator('summary').click()
        history.get_by_role('button', name='Abrir análise: ' + first['title'], exact=True).click()
        expect(page.get_by_test_id('result-title')).to_have_text(first['title'])
        expect(page.get_by_test_id('investigation-card')).to_have_count(1)
        assert len(requests) == 3
        page.get_by_test_id('nav-results').click()
        expect(page.get_by_test_id('preparation-context')).not_to_be_visible()
        expect(page.locator('#assistant-input')).to_be_visible()
        page.get_by_role('button', name='2. Preparação', exact=True).click()
        expect(page.get_by_test_id('preparation-context')).to_be_visible()

        # Exportação permanece do resultado selecionado, com identidade e números originais.
        page.get_by_test_id('nav-new-session').click()
        dialog = page.get_by_test_id('new-session-confirmation')
        expect(dialog).to_contain_text('somente a análise em exibição')
        page.keyboard.press('Shift+Tab')
        assert dialog.evaluate('el => el.contains(document.activeElement)')
        page.emulate_media(media='print')
        expect(dialog).not_to_be_visible()
        expect(page.get_by_test_id('result-title')).to_be_visible()
        expect(navigation).not_to_be_visible()
        page.emulate_media(media='screen')
        with page.expect_download() as download:
            dialog.get_by_test_id('session-export-csv').click()
        exported = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig')), delimiter=';'))
        assert len(exported) == len(first['rows'])
        for expected, actual in zip(first['rows'], exported):
            assert actual.keys() == expected.keys()
            for key, value in expected.items():
                if isinstance(value, (float, int)):
                    assert Decimal(actual[key]) == Decimal(str(value))
                else:
                    assert actual[key] == ('' if value is None else str(value))
        page.get_by_test_id('cancel-new-session').click()
        expect(page.get_by_test_id('result-title')).to_have_text(first['title'])
        workspace(page, 'results')
        page.get_by_test_id('advanced-technical-export').locator('summary').click()
        with page.expect_download() as download:
            page.get_by_role('button', name='Baixar registro técnico (JSON)', exact=True).click()
        technical = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
        assert technical['result_id'] == first['result_id']
        assert technical['mapping'] == first['metadata']['mapping']
        assert technical['options'] == first['metadata']['options']
        assert technical['organizacao_na_sessao'][0]['componentes'] == [first['result_id']]

        # Intenção explícita na conversa prepara e calcula sem perguntar novamente o destino.
        send('Faça uma análise independente da densidade médica dos municípios do Amazonas em janeiro de 2024.')
        fourth = calculate()
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('Análise independente 3')
        assert fourth['metadata']['periods'] == ['202401'], (fourth['metadata']['periods'], fourth['metadata']['operation'], page.get_by_test_id('latest-reply').inner_text())
        send('Acrescente ao diagnóstico atual a densidade médica dos municípios do Amazonas em junho de 2023.')
        fifth = calculate()
        assert fifth['metadata']['periods'] == ['202306']
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('Diagnóstico 3 · 2 componentes')
        expect(page.get_by_test_id('new-analysis-confirmation')).to_have_count(0)
        history.locator('summary').click()
        history.get_by_role('button', name='Abrir análise: ' + first['title'], exact=True).filter(has_text='Análise independente 1').click()
        expect(page.get_by_test_id('result-title')).to_have_text(first['title'])

        # Um resultado idêntico pode pertencer a outro diagnóstico sem novo cálculo.
        page.get_by_role('button', name='Retomar parâmetros deste resultado', exact=True).click()
        choose_mode('confirm-new-analysis')
        select(page, 'Densidade')
        button = page.locator('#preparacao-conversacional').get_by_role('button', name='Calcular e mostrar resultado', exact=True)
        expect(button).to_be_enabled(timeout=90000)
        button.click()
        expect(page.get_by_text('Resultado existente recuperado, sem recalcular.', exact=True)).to_be_visible()
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('Análise independente 4')
        history.locator('summary').click()
        expect(history).to_contain_text('5 análises nesta sessão')
        original = history.get_by_role('button', name='Abrir análise: ' + first['title'], exact=True).filter(has_text='Análise independente 1')
        expect(original).to_be_enabled()
        original.click()
        expect(page.get_by_test_id('investigation-overview')).to_contain_text('Análise independente 1')

        for width in (1440, 1024, 768, 390):
            page.set_viewport_size({'width': width, 'height': 900})
            page.get_by_test_id('nav-results').click()
            expect(page.get_by_test_id('result-title')).to_be_in_viewport()
            page.wait_for_function("document.querySelector('[data-testid=result-title]').getBoundingClientRect().bottom < document.querySelector('[data-testid=conversation-dock]').getBoundingClientRect().top")
            expect(page.locator('#assistant-input')).to_be_in_viewport()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), page.evaluate("""() => ({
                viewport: innerWidth,
                scrollWidth: document.documentElement.scrollWidth,
                overflowing: [...document.querySelectorAll('body *')].filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && (r.right > innerWidth + 2 || r.left < -2);
                }).slice(0, 20).map(el => ({
                    tag: el.tagName, id: el.id, className: typeof el.className === 'string' ? el.className.slice(0, 120) : '',
                    text: (el.textContent || '').trim().slice(0, 70),
                    left: Math.round(el.getBoundingClientRect().left),
                    right: Math.round(el.getBoundingClientRect().right),
                    scrollWidth: el.scrollWidth, clientWidth: el.clientWidth
                }))
            })""")
            assert page.get_by_test_id('analysis-pane').bounding_box()['width'] >= width - 80
            page.screenshot(path=str(OUTPUT / f'interface-integrada-{width}.png'))
        assert len(requests) == 5 and not errors, errors

        page.get_by_test_id('nav-new-session').click()
        # Falha ao encerrar mantém resultados e deixa a decisão recuperável.
        page.route('**/api/session/close', lambda route: route.fulfill(status=503, body='indisponível'), times=1)
        page.get_by_test_id('confirm-new-session').click()
        expect(dialog.get_by_role('alert')).to_contain_text('Não foi possível encerrar')
        expect(page.get_by_test_id('result-title')).to_have_text(first['title'])
        with page.expect_response(lambda r: r.url.endswith('/api/session/close')) as closed:
            page.get_by_test_id('confirm-new-session').click()
        assert closed.value.status == 200
        expect(page.get_by_role('button', name='Li e concordo', exact=True)).to_be_visible()
        expect(page.get_by_test_id('session-ended-notice')).to_contain_text('A sessão anterior foi encerrada')
        assert context.request.get(URL.rstrip('/') + '/api/session', headers={'X-ADT-Session': old_token}).status == 410
        page.get_by_role('button', name='Li e concordo', exact=True).click()
        page.get_by_test_id('nav-results').click()
        expect(page.get_by_test_id('result-title')).to_have_count(0)
        expect(page.get_by_test_id('investigation-card')).to_have_count(0)
        page.get_by_test_id('analysis-history-menu').locator('summary').click()
        expect(page.get_by_test_id('analysis-history-menu').get_by_role('button')).to_have_count(0)
        expect(page.get_by_test_id('conversation-history')).to_have_count(0)
        expect(page.get_by_test_id('latest-reply')).to_have_count(0)
        assert not errors, errors
        browser.close()
    print('INTERFACE INTEGRADA PASS: cinco ações, teclado, análise independente, composição, reabertura sem recálculo, CSV/JSON, quatro larguras, falha de encerramento e revogação real da sessão.')


if __name__ == '__main__':
    main()
