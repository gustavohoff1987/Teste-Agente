"""Estabilização: UI e motor reais, catálogo sintético e somente transporte Gemini simulado."""
import os
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline, execute_analysis, workspace, select, expand, TITLES
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
            expand(inline.get_by_label('Escolher períodos da análise'))

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
        expect(inline.get_by_test_id('period-done')).to_have_count(0)
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
        inline.get_by_test_id('period-done').click()
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
        open_periods()
        inline.get_by_role('button', name='Escolher apenas um', exact=True).click()
        expect(inline.get_by_test_id('period-summary')).to_contain_text('janeiro de 2024')
        expect(inline.get_by_test_id('period-summary')).not_to_contain_text('junho de 2024')
        # Base oficial: sem condições avançadas nem pedido de condições sobre a base, com a preparação validada ou não.
        expect(inline.get_by_text('Ver outras condições da análise', exact=True)).to_have_count(0)
        expect(inline.get_by_text('Ainda faltam condições específicas', exact=False)).to_have_count(0)

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
        # Continuidade (21/10/2026): "últimos 5 anos", sem citar territórios, usa os três municípios da conversa, e a
        # resposta diz quais, sem o provedor de IA. Na base sintética (2023 e 2024), as leituras até o último período da
        # base e até hoje (AT-34) dão os mesmos anos até 2027; depois disso, a conversa pergunta e a leitura até o último
        # período da base é escolhida pela alternativa.
        llm_before = len(llm)
        send('Quero fazer a comparação dos últimos 5 anos.')
        reply = page.get_by_test_id('latest-reply')
        expect(reply).to_contain_text('Mantive os 3 territórios já escolhidos na conversa')
        expect(reply).not_to_contain_text('Quais estados ou municípios')
        alternatives = page.locator('[aria-label="Alternativas de esclarecimento"]').get_by_role(
            'button', name='até o último período da base')
        if alternatives.count():
            alternatives.first.click()
            expect(page.locator('#assistant-input')).to_be_enabled(timeout=90000)
        else:
            expect(reply).to_contain_text('“Últimos 5 anos”: de 2023 a 2024')
        assert len(llm) == llm_before, 'a continuação é resolvida localmente, sem o provedor de IA'
        recent = calculate()
        assert recent['metadata']['operation'] == 'comparisons'
        assert sorted(recent['metadata']['options']['period_filters']) == ['202301', '202306', '202401', '202406']
        assert len(recent['detail_rows']) == 3
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
                # A aba ativa desce até o contorno que envolve todo o conteúdo da etapa (sobre a borda superior dele).
                tab = page.get_by_test_id('stage-tabs').locator('[aria-current="step"]').bounding_box()
                frame = page.get_by_test_id('stage-frame').bounding_box()
                assert frame['y'] < tab['y'] + tab['height'] <= frame['y'] + 3, (width, stage, tab, frame)
                assert frame['x'] - 1 <= tab['x'] and tab['x'] + tab['width'] <= frame['x'] + frame['width'], (width, stage)
                page.locator('#assistant-input').scroll_into_view_if_needed()
                expect(page.locator('#assistant-input')).to_be_in_viewport()
            page.screenshot(path=str(OUTPUT/f'estabilizacao-{width}.png'))
        page.add_style_tag(content='body,button,input,textarea,select {font-family: "DejaVu Sans", sans-serif !important;}')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')

        # Troca de análise sem troca de fonte (D3): a inspeção é sempre municipal e trocar de análise não recarrega a base;
        # o período único da densidade não é imposto à evolução temporal.
        fresh = context.new_page()
        fresh.on('pageerror', lambda error: errors.append(str(error)))
        inspections = []
        fresh.on('request', lambda request: inspections.append(request.url) if request.url.endswith('/api/inspect') else None)
        fresh.goto(URL)
        fresh.get_by_role('button', name='Li e concordo', exact=True).click()
        fresh.get_by_role('button', name='Usar dados do Brasil').click()
        expect(fresh.get_by_test_id('current-source')).to_contain_text('Dados do Brasil', timeout=90000)
        select(fresh, 'Densidade')
        steps = fresh.locator('#preparacao-conversacional')
        # Densidade: padrão "Todos os municípios", com selo e desmarcado; o Brasil e os estados também podem ser marcados.
        expect(steps.get_by_test_id('scope-summary')).to_have_text('Todos os municípios', timeout=90000)
        expand(steps.get_by_test_id('territory-toggle'))
        expect(steps.get_by_test_id('scope-info')).to_have_text('Marque o Brasil, estados e municípios; cada nível aparece em um '
                                                                'bloco separado no resultado.')
        national = steps.get_by_role('checkbox', name='Brasil (total nacional)', exact=True)
        expect(national).to_be_enabled()
        expect(national).not_to_be_checked()
        every = steps.get_by_role('checkbox', name='Todos os municípios', exact=True)
        expect(every).not_to_be_checked()
        expect(steps.get_by_test_id('territory-badge-padrao')).to_have_count(1)
        steps.get_by_test_id('scope-done').click()
        steps.get_by_label('Escolher períodos da análise').click()
        steps.get_by_role('button', name='junho de 2024', exact=True).click()
        expect(steps.get_by_test_id('period-summary')).to_have_text('junho de 2024', timeout=90000)
        # Trocar de análise não chama /api/inspect: a lista de competências continua habilitada, sem espera.
        loaded = len(inspections)
        select(fresh, 'Evolução temporal')
        expand(steps.get_by_label('Escolher períodos da análise'))
        expect(steps.get_by_role('button', name='janeiro de 2023', exact=True)).to_be_enabled()
        steps.get_by_test_id('period-done').click()
        # Evolução temporal: o padrão é o Brasil (total nacional), com selo e desmarcado.
        expect(steps.get_by_test_id('scope-summary')).to_have_text('Brasil (total nacional)', timeout=90000)
        expand(steps.get_by_test_id('territory-toggle'))
        expect(national).not_to_be_checked()
        expect(national).to_be_enabled(timeout=90000)
        # A densidade do Brasil existe (população de junho, regra governada do backend): o indicador fica disponível.
        density = steps.get_by_role('combobox', name='Indicador', exact=True).locator('option[value="density"]')
        expect(density).to_have_js_property('disabled', False)
        expect(steps.get_by_test_id('period-summary')).to_contain_text('todas as 4 competências', timeout=90000)
        # Marcar "Todos os municípios" substitui o padrão, sem recarregar a base nem mudar as competências.
        every.check()
        expect(every).to_be_checked(timeout=90000)
        expect(steps.get_by_test_id('period-summary')).to_contain_text('todas as 4 competências', timeout=90000)
        expect(steps.get_by_test_id('scope-summary')).to_have_text('Todos os municípios')
        expect(density).to_have_js_property('disabled', False)
        assert len(inspections) == loaded, 'trocar de análise ou de abrangência não recarrega a base'
        # Orientação do vídeo (06:04): com todas as competências incluídas por padrão, clicar nelas as escolhe.
        expand(steps.get_by_label('Escolher períodos da análise'))
        expect(steps.get_by_role('button', name='janeiro de 2023', exact=True)).to_have_attribute('aria-pressed', 'false')
        for month in ('janeiro de 2023', 'junho de 2024'):
            steps.get_by_role('button', name=month, exact=True).click()
        for month, pressed in (('janeiro de 2023', 'true'), ('junho de 2023', 'false'), ('janeiro de 2024', 'false'),
                               ('junho de 2024', 'true')):
            expect(steps.get_by_role('button', name=month, exact=True)).to_have_attribute('aria-pressed', pressed)
        steps.get_by_test_id('period-done').click()
        expect(steps.get_by_test_id('period-summary')).to_have_text('janeiro de 2023 e junho de 2024')
        # Todas as análises mostram as mesmas quatro caixas das configurações; sem escolha entre quantidade e densidade,
        # o Indicador é o da própria análise (orientação de 19/10/2026), e a análise espacial pede uma competência.
        own = {'Agregações': 'Quantidade e densidade por 1.000 habitantes', 'Análise espacial': 'Distância geodésica (km)',
               'Recortes e rankings': 'Densidade por 1.000 habitantes', 'Rotatividade': 'Permanência e rotatividade da coorte (%)',
               'Referência mais próxima': 'Distância à referência mais próxima (km)', 'Critérios combinados': 'Definido nos critérios'}
        for title in TITLES:
            select(fresh, title)
            boxes = steps.get_by_test_id('analysis-summary')
            for label in ('Categoria', 'Período', 'Abrangência territorial', 'Indicador'):
                expect(boxes.get_by_text(label, exact=True)).to_be_visible(timeout=90000)
            if title in own:
                expect(steps.get_by_role('combobox', name='Indicador', exact=True)).to_have_value(own[title])
            if title == 'Análise espacial':
                # Uma competência por vez: as coordenadas de um município podem mudar entre competências.
                expect(steps.get_by_test_id('period-summary')).to_have_text('Escolher período')
            if title == 'Rotatividade':
                # A coorte vai da primeira à última competência, salvo escolha na própria caixa Período.
                expect(steps.get_by_test_id('period-summary')).to_have_text('de janeiro de 2023 a junho de 2024')
                expand(steps.get_by_label('Escolher os períodos da coorte'))
                steps.get_by_label('Período inicial', exact=True).select_option('202306')
                expect(steps.get_by_test_id('period-summary')).to_have_text('de junho de 2023 a junho de 2024')
                steps.get_by_test_id('period-done').click()
        fresh.close()

        # Importação: múltiplos períodos não dispensam a escolha da unidade; a categoria MEDICINA é reconhecida pelo catálogo
        # (D1: sem caixa de declaração da força de trabalho em saúde nem botão de confirmação).
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
        expect(preparation.get_by_text('Confirmo', exact=False)).to_have_count(0)
        preparation.get_by_role('button', name='Selecionar vários períodos', exact=True).click()
        preparation.get_by_label('Escolher períodos da análise').click()
        # Todos os períodos vêm incluídos por padrão: o primeiro clique escolhe só a competência clicada.
        january = preparation.get_by_role('button', name='janeiro de 2024', exact=True)
        january.click()
        expect(january).to_have_attribute('aria-pressed', 'true')
        expect(preparation.get_by_role('button', name='junho de 2024', exact=True)).to_have_attribute('aria-pressed', 'false')
        # Retirada a única escolhida, nenhum período fica selecionado e a execução continua bloqueada.
        january.click()
        execute = preparation.get_by_role('button', name='Executar análise', exact=True)
        expect(execute).to_be_disabled()
        expect(preparation.get_by_role('button', name='Confirmar correspondências', exact=True)).to_have_count(0)
        preparation.get_by_role('button', name='Todos os períodos disponíveis', exact=True).click()
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
