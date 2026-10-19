"""Estabilização: UI e motor reais, catálogo sintético e somente transporte Gemini simulado."""
import os
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline, execute_analysis, workspace, select
from ui_block1_smoke import exported_rows, assert_same_rows

OUTPUT = Path(__file__).resolve().parents[2] / '.local/ui-validation'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv('ADT_BROWSER_CHANNEL', 'chrome'))
        context = browser.new_context(viewport={'width':1440, 'height':1000}, accept_downloads=True, reduced_motion='reduce')
        offline(context)
        page = context.new_page()
        errors, analyses, llm = [], [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: analyses.append(request) if request.url.endswith('/api/analyze') else None)
        page.on('request', lambda request: llm.append(request) if '/api/llm/interpret' in request.url else None)
        page.goto(URL)
        page.get_by_role('button', name='Li e concordo', exact=True).click()
        inline = page.locator('#preparacao-conversacional')
        board = page.locator('#resultados')

        def send(message):
            print('Pedido: ' + message, flush=True)
            before = len(analyses)
            page.locator('#assistant-input').fill(message)
            page.get_by_role('button', name='Enviar mensagem', exact=True).click()
            expect(page.locator('#assistant-input')).to_be_enabled(timeout=90000)
            assert len(analyses) == before, 'mensagem prepara, mas não autoriza execução'

        def prepared():
            expect(page.get_by_role('button', name='1. Preparação', exact=True)).to_have_attribute('aria-current', 'step')
            expect(inline).to_be_visible()
            expect(board).not_to_be_visible()

        def calculate():
            prepared()
            button = inline.get_by_role('button', name='Calcular e mostrar resultado', exact=True)
            expect(button).to_be_enabled(timeout=90000)
            with page.expect_response(lambda r: r.url.endswith('/api/analyze'), timeout=120000) as event:
                execute_analysis(page, button)
            assert event.value.status == 200, event.value.text()
            body = event.value.json()
            print('Resultado: ' + body['title'], flush=True)
            expect(board.get_by_test_id('result-title')).to_be_visible()
            expect(inline).not_to_be_visible()
            return body

        def open_periods():
            summary = inline.get_by_label('Escolher períodos da análise')
            if not summary.locator('..').evaluate('el => el.open'):
                summary.click()

        send('Usar dados do Brasil.')
        expect(page.get_by_test_id('current-source')).to_contain_text('Dados do Brasil', timeout=90000)
        assert not llm, 'escolha de fonte é local'
        send('Quantos médicos existem no Brasil?')
        prepared()
        expect(inline.get_by_role('button', name='Confirmar correspondências')).to_have_count(0)
        open_periods()
        inline.get_by_role('button', name='junho de 2024', exact=True).click()
        national = calculate()
        assert national['metadata']['source']['scope'] == 'national'
        assert national['metadata']['periods'] == ['202406']
        assert national['rows'][0]['Quantidade'] == 105  # fixture declarada, não valor do Brasil real

        send('Quero analisar vários períodos.')
        prepared()
        open_periods()
        expect(inline.get_by_role('button', name='junho de 2024', exact=True)).to_have_attribute('aria-pressed', 'true')
        inline.get_by_role('button', name='janeiro de 2024', exact=True).click()
        workspace(page, 'territories')
        workspace(page, 'preparation')
        for month in ('junho de 2024', 'janeiro de 2024'):
            expect(inline.get_by_role('button', name=month, exact=True)).to_have_attribute('aria-pressed', 'true')
            inline.get_by_role('button', name=month, exact=True).click()
        expect(inline.get_by_label('Escolher períodos da análise')).to_contain_text('Escolher períodos')
        expect(inline.get_by_role('button', name='Avançar', exact=True)).to_have_count(0)
        for month in ('janeiro de 2024', 'junho de 2024'):
            inline.get_by_role('button', name=month, exact=True).click()
        # Intervalo contínuo pelos seletores de início e fim, sem clicar competência por competência.
        inline.get_by_role('button', name='Limpar', exact=True).click()
        expect(inline.get_by_label('Escolher períodos da análise')).to_contain_text('Escolher períodos')
        inline.get_by_label('Início do intervalo').select_option('202401')
        inline.get_by_label('Fim do intervalo').select_option('202406')
        expect(inline.get_by_test_id('period-range-summary')).to_contain_text('2 competências, de janeiro de 2024 a junho de 2024')
        for month in ('janeiro de 2024', 'junho de 2024'):
            expect(inline.get_by_role('button', name=month, exact=True)).to_have_attribute('aria-pressed', 'true')
        inline.get_by_role('button', name='Avançar', exact=True).click()
        expect(inline.get_by_test_id('period-summary')).to_contain_text('de janeiro de 2024 a junho de 2024')
        multiple = calculate()
        assert {row['Período']:row['Quantidade'] for row in multiple['rows']} == {'202401':103, '202406':105}
        with page.expect_download() as download:
            board.get_by_test_id('export-results-csv').click()
        assert_same_rows(exported_rows(download), multiple['rows'])
        calls = len(analyses)
        workspace(page, 'preparation')
        history = page.get_by_test_id('analysis-history-menu')
        history.locator('summary').click()
        history.get_by_role('button', name='Abrir análise: '+multiple['title'], exact=True).first.click()
        expect(board.get_by_test_id('result-title')).to_be_visible()
        assert len(analyses) == calls, 'reabrir o mesmo resultado deve apenas navegar'
        workspace(page, 'preparation')
        inline.get_by_role('button', name='Voltar à escolha do período', exact=True).click()
        inline.get_by_role('button', name='Escolher apenas um', exact=True).click()
        expect(inline.get_by_test_id('period-summary')).to_contain_text('janeiro de 2024')
        expect(inline.get_by_test_id('period-summary')).not_to_contain_text('junho de 2024')
        # Condições avançadas continuam disponíveis mesmo com a preparação validada.
        expect(inline.get_by_text('Ver outras condições da análise', exact=True)).to_be_visible()

        send('Mostre a densidade médica dos municípios do Amazonas em junho de 2024.')
        density = calculate()
        assert density['total_rows'] == 3
        send('Compare Manaus e Tefé.')
        pair = calculate()
        assert pair['total_rows'] == 1
        cards = board.get_by_test_id('comparison-territory-row')
        expect(cards).to_have_count(2)
        for index, side in enumerate(('A','B')):
            expect(cards.nth(index)).to_contain_text(pair['rows'][0]['Objeto '+side])
            expect(cards.nth(index).locator('[title="Valor integral: '+str(pair['rows'][0]['Valor '+side]).removesuffix('.0')+'"]')).to_have_count(1)
        expect(board.get_by_test_id('comparison-pair-summary')).to_contain_text('Diferença A − B')
        board.get_by_text('Filtrar e ordenar a comparação', exact=True).click()
        board.get_by_label('Filtrar Objeto A', exact=True).fill('inexistente')
        expect(cards).to_have_count(0)
        board.get_by_role('button', name='Limpar filtros da tabela', exact=True).click()
        expect(cards).to_have_count(2)
        with page.expect_download() as download:
            board.get_by_test_id('export-results-csv').click()
        assert_same_rows(exported_rows(download), pair['rows'])

        send('Inclua Parintins.')
        triple = calculate()
        assert triple['total_rows'] == 3
        expect(cards).to_have_count(3)
        send('Mostre a evolução dos municípios selecionados.')
        prepared()
        # Base oficial: as premissas de comparabilidade são internas; nenhuma declaração é pedida.
        expect(inline.get_by_label('Confirmo que os quantitativos e os períodos são comparáveis.')).to_have_count(0)
        expect(inline.get_by_label('Os territórios correspondem às mesmas unidades ao longo do tempo.')).to_have_count(0)
        temporal = calculate()
        assert len(temporal['detail_rows']) == 12
        assert any('premissa governada' in note for note in temporal['notes'])
        assert not any('pelo usuário para esta execução' in note for note in temporal['notes'])
        send('Volte para a seleção de territórios.')
        # Territórios ficam na preparação: o comando abre o bloco de seleção expandido.
        expect(page.get_by_role('button', name='1. Preparação', exact=True)).to_have_attribute('aria-current', 'step')
        expect(page.get_by_test_id('territory-toggle')).to_have_attribute('aria-expanded', 'true')
        expect(page.get_by_role('region', name='Seleção territorial compartilhada')).to_contain_text('3 selecionados')
        expect(board).not_to_be_visible()
        # Duas famílias de fontes e quatro larguras: não depender da métrica da fonte Windows.
        for width in (1440, 1024, 768, 390):
            page.set_viewport_size({'width':width, 'height':900})
            for stage in ('territories', 'preparation', 'results'):
                workspace(page, stage)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), (width, stage)
                page.locator('#assistant-input').scroll_into_view_if_needed()
                expect(page.locator('#assistant-input')).to_be_in_viewport()
            page.screenshot(path=str(OUTPUT/f'estabilizacao-{width}.png'))
        page.add_style_tag(content='body,button,input,textarea,select {font-family: "DejaVu Sans", sans-serif !important;}')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')

        # Troca de análise com troca de recorte (abrangência automática): o período único da densidade não é
        # imposto à evolução temporal, e a preparação não volta à escolha da fonte durante o carregamento.
        fresh = context.new_page()
        fresh.on('pageerror', lambda error: errors.append(str(error)))
        fresh.goto(URL)
        fresh.get_by_role('button', name='Li e concordo', exact=True).click()
        fresh.get_by_role('button', name='Usar dados do Brasil').click()
        expect(fresh.get_by_test_id('current-source')).to_contain_text('Dados do Brasil', timeout=90000)
        select(fresh, 'Densidade')
        steps = fresh.locator('#preparacao-conversacional')
        expect(steps.get_by_test_id('scope-info')).to_contain_text('municípios brasileiros', timeout=90000)
        steps.get_by_label('Escolher períodos da análise').click()
        steps.get_by_role('button', name='junho de 2024', exact=True).click()
        expect(steps.get_by_test_id('period-summary')).to_have_text('junho de 2024', timeout=90000)
        # Enquanto o recorte nacional carrega, a lista de períodos fica bloqueada: a escolha seria descartada.
        held, released = [], []
        fresh.route('**/api/inspect', lambda route: route.continue_() if released else held.append(route))
        select(fresh, 'Evolução temporal')
        steps.get_by_role('button', name='Voltar à escolha do período', exact=True).click()
        chooser = steps.get_by_label('Escolher períodos da análise')
        if not chooser.locator('..').evaluate('el => el.open'):
            chooser.click()
        expect(steps.get_by_role('button', name='janeiro de 2023', exact=True)).to_be_disabled()
        released.append(True)
        for route in held:
            route.continue_()
        expect(steps.get_by_role('button', name='janeiro de 2023', exact=True)).to_be_enabled(timeout=90000)
        fresh.unroute('**/api/inspect')
        steps.get_by_role('button', name='Avançar', exact=True).click()
        national = steps.get_by_role('radio', name='Brasil (total nacional)', exact=True)
        expect(national).to_be_checked(timeout=90000)
        expect(national).to_be_enabled(timeout=90000)
        expect(steps.get_by_test_id('period-summary')).to_contain_text('todas as 4 competências', timeout=90000)
        # Voltar ao recorte municipal reabre o rascunho desse recorte sem impor o período único da densidade.
        municipal = steps.get_by_role('radio', name='Municípios', exact=True)
        municipal.check()
        expect(municipal).to_be_checked(timeout=90000)
        expect(municipal).to_be_enabled(timeout=90000)
        expect(steps.get_by_test_id('period-summary')).to_contain_text('todas as 4 competências', timeout=90000)
        # Orientação do vídeo (06:04): com todas as competências incluídas por padrão, clicar nelas as escolhe.
        steps.get_by_role('button', name='Voltar à escolha do período', exact=True).click()
        chooser = steps.get_by_label('Escolher períodos da análise')
        if not chooser.locator('..').evaluate('el => el.open'):
            chooser.click()
        expect(steps.get_by_role('button', name='janeiro de 2023', exact=True)).to_have_attribute('aria-pressed', 'false')
        for month in ('janeiro de 2023', 'junho de 2024'):
            steps.get_by_role('button', name=month, exact=True).click()
        for month, pressed in (('janeiro de 2023', 'true'), ('junho de 2023', 'false'), ('janeiro de 2024', 'false'),
                               ('junho de 2024', 'true')):
            expect(steps.get_by_role('button', name=month, exact=True)).to_have_attribute('aria-pressed', pressed)
        steps.get_by_role('button', name='Avançar', exact=True).click()
        expect(steps.get_by_test_id('period-summary')).to_have_text('janeiro de 2023 e junho de 2024')
        fresh.close()

        # Importação: múltiplos períodos não dispensam confirmação da unidade e da FTS.
        imported = context.new_page()
        imported.on('pageerror', lambda error: errors.append(str(error)))
        imported.goto(URL)
        imported.get_by_role('button', name='Li e concordo', exact=True).click()
        imported.get_by_label('Importar arquivo de dados').set_input_files({'name':'competencias.csv', 'mimeType':'text/csv',
            'buffer': b'territorio_analise;periodo;categoria_profissional;quantidade\nALFA;202401;MEDICINA;10\nALFA;202406;MEDICINA;12\n'})
        expect(imported.get_by_test_id('current-source')).to_contain_text('competencias.csv')
        select(imported, 'Quantitativos')
        preparation = imported.locator('#preparacao-conversacional')
        preparation.get_by_label('Unidade de contagem', exact=True).select_option('pessoas')
        preparation.get_by_label('Confirmo que os dados selecionados correspondem à força de trabalho em saúde.').check()
        preparation.get_by_role('button', name='Selecionar vários períodos', exact=True).click()
        preparation.get_by_label('Escolher períodos da análise').click()
        # Todos os períodos vêm incluídos por padrão: o primeiro clique escolhe só a competência clicada.
        january = preparation.get_by_role('button', name='janeiro de 2024', exact=True)
        january.click()
        expect(january).to_have_attribute('aria-pressed', 'true')
        expect(preparation.get_by_role('button', name='junho de 2024', exact=True)).to_have_attribute('aria-pressed', 'false')
        # Retirada a única escolhida, nenhum período fica selecionado e a confirmação continua bloqueada.
        january.click()
        expect(preparation.get_by_role('button', name='Confirmar correspondências', exact=True)).to_be_disabled()
        preparation.get_by_role('button', name='Todos os períodos disponíveis', exact=True).click()
        preparation.get_by_role('button', name='Confirmar correspondências', exact=True).click()
        execute = preparation.get_by_role('button', name='Executar análise', exact=True)
        expect(execute).to_be_enabled(timeout=30000)
        with imported.expect_response(lambda r: r.url.endswith('/api/analyze')) as event:
            execute.click()
        assert event.value.status == 200, event.value.text()
        assert {row['Período']:row['Quantidade'] for row in event.value.json()['rows']} == {'202401':10, '202406':12}
        expect(imported.locator('#resultados').get_by_test_id('result-title')).to_be_visible()
        assert not errors, errors
        browser.close()
        print('ESTABILIZAÇÃO PASS: comandos, etapas, fonte governada, períodos individuais, comparações separadas, CSV e quatro larguras; Gemini simulado.')


if __name__ == '__main__':
    main()
