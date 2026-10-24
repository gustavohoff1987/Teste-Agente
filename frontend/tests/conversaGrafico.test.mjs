import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// Conversa agindo no gráfico (22/10/2026): comandos reconhecidos na tela, campo `painel` → pedido para a área e contexto do
// gráfico → opções do intérprete. Desde 23/10/2026, também a vista do desenho (gráfico ou mapa) e o pedido de resumo. Os
// testes de normalizeCommand, viewCommand e previousResultCommand vieram de workspace.test.mjs (o módulo
// workspaceNavigation.ts saiu com a navegação clássica).
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const C = await source('conversaGrafico');

const CONTEXTO = {familia: 'distribuicao', indicador: 'densidade', nivel: 'municipios',
  municipios: {todos: false, estados: ['13'], ids: []}, idsNaTela: ['code:130260', 'c1', 'uf:13', 'code:130420', 'code:130260'],
  competencia: '202406', janela: [], referencia: [], titulo: 'Densidade de médicos nos municípios do Amazonas · junho de 2024'};

test('comandos aceitam acentos, pontuação e espaços; a escolha da fonte é a mensagem inteira', () => {
  assert.equal(C.normalizeCommand('  Usar  dados do Brasil. '), 'usar dados do brasil');
  assert.equal(C.comandoDeFonte('Usar dados do Brasil.'), 'brasil');
  assert.equal(C.comandoDeFonte('Dados do Brasil'), 'brasil');
  assert.equal(C.comandoDeFonte('quero usar a base do Brasil'), 'brasil');
  assert.equal(C.comandoDeFonte('Enviar meus dados'), 'arquivo');
  assert.equal(C.comandoDeFonte('importar arquivo'), 'arquivo');
  assert.equal(C.comandoDeFonte('Mostre o Brasil'), null);
  assert.equal(C.comandoDeFonte('Dados do Brasil em 2024'), null);
  assert.equal(C.comandoDeFonte('Compare Manaus e Tefé'), null);
});

test('pedidos de apresentação e de análise anterior só valem quando a mensagem não diz mais do que isso', () => {
  assert.equal(C.viewCommand('Mostra isso num gráfico'), 'graficos');
  assert.equal(C.viewCommand('agora a tabela, por favor'), 'tabela');
  assert.equal(C.viewCommand('Quero ver no mapa.'), 'mapa');
  assert.equal(C.viewCommand('mapa'), 'mapa');
  assert.equal(C.viewCommand('Não mostre o mapa'), null);
  assert.equal(C.viewCommand('Mostre o mapa da densidade de 2024'), null);
  assert.equal(C.viewCommand('Compare a tabela e o mapa'), null);
  assert.equal(C.previousResultCommand('Volta pro resultado anterior'), true);
  assert.equal(C.previousResultCommand('volte para a seleção anterior.'), true);
  assert.equal(C.previousResultCommand('Reabra a análise de antes'), true);
  assert.equal(C.previousResultCommand('O resultado anterior era maior?'), false);
  assert.equal(C.previousResultCommand('Compare com o resultado anterior'), false);
  assert.equal(C.previousResultCommand('Volte para a preparação'), false);
});

test('vista do desenho pela conversa: o mapa quando a área o tem, o motivo quando não tem, e a volta ao gráfico', () => {
  // As formas diretas são reconhecidas na tela.
  for (const pedido of ['ver no mapa', 'Mostre no mapa', 'abra o mapa', 'Agora o mapa.', 'volte para o mapa'])
    assert.equal(C.viewCommand(pedido), 'mapa', pedido);
  for (const pedido of ['volte ao gráfico', 'Voltar para o gráfico', 'mostre no gráfico', 'agora o gráfico', 'volta pro gráfico'])
    assert.equal(C.viewCommand(pedido), 'graficos', pedido);
  assert.equal(C.viewCommand('agora a tabela'), 'tabela');
  // Com outro pedido junto, a mensagem vai ao intérprete, que muda o recorte e a vista juntos; "Pará" (ou "o Para") é o
  // estado, não a preposição.
  for (const pedido of ['Mostre o Pará no mapa', 'mostre o Para no mapa', 'volte ao gráfico de antes',
    'onde ficam os municípios com menos de 1 médico por mil?'])
    assert.equal(C.viewCommand(pedido), null, pedido);

  // Com o mapa disponível, "ver no mapa" vira o pedido { vista: "mapa" } para a área; "volte ao gráfico" desfaz.
  const NO_GRAFICO = {...CONTEXTO, vista: 'grafico', mapaDisponivel: true, motivoSemMapa: null, resumo: 'Frase do motor.'};
  assert.deepEqual(C.respostaDaVista('mapa', NO_GRAFICO),
    {texto: 'Mostrei o mapa no lugar do gráfico. Para voltar, peça “volte ao gráfico”.', pedido: {vista: 'mapa'}});
  assert.deepEqual(C.respostaDaVista('graficos', {...NO_GRAFICO, vista: 'mapa'}),
    {texto: 'Voltei ao gráfico. Para ver de novo no mapa, peça “ver no mapa”.', pedido: {vista: 'grafico'}});
  assert.deepEqual(C.respostaDaVista('graficos', {...NO_GRAFICO, vista: 'lado'}).pedido, {vista: 'grafico'});
  // Já na vista pedida, nada muda.
  assert.deepEqual(C.respostaDaVista('mapa', {...NO_GRAFICO, vista: 'mapa'}),
    {texto: 'O mapa já está na tela. Para voltar, peça “volte ao gráfico”.', pedido: null});
  assert.equal(C.respostaDaVista('graficos', NO_GRAFICO).pedido, null);
  assert.match(C.respostaDaVista('graficos', NO_GRAFICO).texto, /O gráfico já está na tela/);
  // Sem o mapa (nos estados, numa planilha sem coordenadas), a resposta é o motivo da área, e nenhum pedido sai.
  const NOS_ESTADOS = {...NO_GRAFICO, nivel: 'estados', mapaDisponivel: false,
    motivoSemMapa: 'Os estados não têm um ponto no mapa: abra os municípios de um estado ou escolha todos os municípios.'};
  assert.deepEqual(C.respostaDaVista('mapa', NOS_ESTADOS),
    {texto: NOS_ESTADOS.motivoSemMapa + ' Nada mudou no gráfico.', pedido: null});
  assert.equal(C.respostaDaVista('mapa', {...NOS_ESTADOS, motivoSemMapa: 'Sem coordenadas na planilha'}).texto,
    'Sem coordenadas na planilha. Nada mudou no gráfico.');
  assert.equal(C.respostaDaVista('mapa', {...NOS_ESTADOS, motivoSemMapa: null}).texto,
    'O mapa não está disponível nesta análise. Nada mudou no gráfico.');
  // Sem a vista e a disponibilidade no contexto, o pedido vai assim mesmo, e a área decide; sem gráfico, nada a mostrar.
  assert.deepEqual(C.respostaDaVista('mapa', CONTEXTO).pedido, {vista: 'mapa'});
  assert.deepEqual(C.respostaDaVista('graficos', CONTEXTO).pedido, {vista: 'grafico'});
  assert.deepEqual(C.respostaDaVista('mapa', null),
    {texto: 'Ainda não há uma análise na tela para mostrar no mapa.', pedido: null});
  assert.equal(C.respostaDaVista('graficos', null).pedido, null);
  // A tabela continua nos Detalhes, abaixo do desenho em uso; nada é pedido à área.
  assert.deepEqual(C.respostaDaVista('tabela', NO_GRAFICO),
    {texto: 'A tabela fica em Detalhes, logo abaixo do gráfico, com os mesmos valores do motor.', pedido: null});
  assert.match(C.respostaDaVista('tabela', {...NO_GRAFICO, vista: 'mapa'}).texto, /logo abaixo do mapa/);
  assert.match(C.respostaDaVista('tabela', null).texto, /Detalhes, logo abaixo do gráfico/);
});

test('pedido de resumo: a frase-resumo do motor, como veio, sem o intérprete', () => {
  for (const pedido of ['O que esse gráfico mostra?', 'o que o mapa está mostrando?', 'Resuma o gráfico', 'resuma',
    'Explique o resultado.', 'me explica esse gráfico', 'O que estou vendo?', 'o que eu estou vendo aqui?',
    'Pode resumir o gráfico, por favor?', 'faça um resumo do resultado', 'o que mostra este mapa?',
    'E o que esses resultados significam?'])
    assert.equal(C.pedidoDeResumo(pedido), true, pedido);
  // Pedidos que mudam a análise, perguntas de método e outras perguntas seguem para a interpretação.
  for (const pedido of ['O que esse gráfico mostra em 2023?', 'Explique o resultado de Manaus', 'explique de forma mais simples',
    'explique o resultado de forma simples', 'o que significa densidade?', 'Mostre o gráfico', 'resuma o gráfico do Pará',
    'o que tem nos dados do Brasil?', 'Compare Manaus e Tefé', 'e agora?', 'Por que esse resultado apareceu?'])
    assert.equal(C.pedidoDeResumo(pedido), false, pedido);
  const frase = 'Nos 3 municípios do Amazonas, em junho de 2024, a densidade vai de 1,75 a 5 por 1.000 habitantes.';
  assert.equal(C.respostaDoResumo({...CONTEXTO, resumo: '  ' + frase + ' '}), frase);
  for (const contexto of [{...CONTEXTO, resumo: null}, {...CONTEXTO, resumo: ''}, CONTEXTO, null])
    assert.equal(C.respostaDoResumo(contexto), 'Ainda não há um gráfico calculado para resumir.');
});

test('campo painel → pedido para a área: só os campos válidos, sem os não citados', () => {
  assert.deepEqual(C.pedidoDoPainel({familia: 'espacial', indicador: 'densidade', nivel: 'municipios',
    municipios: {todos: false, estados: ['15'], ids: []}, competencia: '202406', janela: null, visao_tendencia: null,
    referencia: {membros: ['code:150140'], criterio: {atributo: 'densidade', ordem: 'desc'}}, funcao: null, selecao: null,
    ordenar: null, condicoes: null}),
  {familia: 'espacial', indicador: 'densidade', nivel: 'municipios', municipios: {todos: false, estados: ['15'], ids: []},
    competencia: '202406', referencia: {membros: ['code:150140'], criterio: {atributo: 'densidade', ordem: 'desc'}}});
  assert.deepEqual(C.pedidoDoPainel({familia: 'tendencia', janela: ['202106', '202206', '202206', 7], visao_tendencia: 'classes'}),
    {familia: 'tendencia', janela: ['202106', '202206'], visaoTendencia: 'classes'});
  assert.deepEqual(C.pedidoDoPainel({funcao: 'comparar', selecao: ['code:130260', 'code:130420']}),
    {funcao: 'comparar', selecao: ['code:130260', 'code:130420']});
  assert.deepEqual(C.pedidoDoPainel({funcao: 'ordenar', ordenar: {atributo: 'densidade', ordem: 'desc', primeiros: 5}}),
    {funcao: 'ordenar', ordenar: {atributo: 'densidade', ordem: 'desc', primeiros: 5}});
  assert.deepEqual(C.pedidoDoPainel({funcao: 'condicoes', condicoes: [{atributo: 'densidade', operador: '<', valor: 1}, 'x', null]}),
    {funcao: 'condicoes', condicoes: [{atributo: 'densidade', operador: '<', valor: 1}]});
  assert.deepEqual(C.pedidoDoPainel({nivel: 'estados', municipios: {todos: false, estados: [], ids: []}}), {nivel: 'estados'});
  assert.deepEqual(C.pedidoDoPainel({referencia: {membros: [], criterio: {atributo: 'densidade', ordem: 'desc'}}}),
    {referencia: {membros: [], criterio: {atributo: 'densidade', ordem: 'desc'}}});
  assert.deepEqual(C.pedidoDoPainel({municipios: {todos: true}}), {municipios: {todos: true, estados: [], ids: []}});
  // Grupos por posição (quartis, quintis, decis) ou "nenhum": outro tipo não vira pedido.
  assert.deepEqual(C.pedidoDoPainel({familia: 'distribuicao', grupos: {tipo: 'quintis'}}), {familia: 'distribuicao', grupos: {tipo: 'quintis'}});
  assert.deepEqual(C.pedidoDoPainel({grupos: {tipo: 'nenhum'}}), {grupos: {tipo: 'nenhum'}});
  assert.equal(C.pedidoDoPainel({grupos: {tipo: 'tercis'}}), null);
  // A vista do desenho pedida junto com o comando ("mostre o Pará no mapa", "a quantidade no gráfico"); "lado a lado" não
  // vem da conversa, e vista nula não vira pedido.
  assert.deepEqual(C.pedidoDoPainel({nivel: 'municipios', municipios: {todos: false, estados: ['15'], ids: []}, vista: 'mapa'}),
    {nivel: 'municipios', municipios: {todos: false, estados: ['15'], ids: []}, vista: 'mapa'});
  assert.deepEqual(C.pedidoDoPainel({indicador: 'quantidade', vista: 'grafico'}), {indicador: 'quantidade', vista: 'grafico'});
  assert.deepEqual(C.pedidoDoPainel({vista: 'mapa'}), {vista: 'mapa'});
  assert.equal(C.pedidoDoPainel({vista: 'lado'}), null);
  assert.deepEqual(C.pedidoDoPainel({funcao: 'condicoes', condicoes: [{atributo: 'densidade', operador: '<', valor: 1}], vista: null}),
    {funcao: 'condicoes', condicoes: [{atributo: 'densidade', operador: '<', valor: 1}]});
  // Valores fora do contrato e respostas sem nada a aplicar não viram pedido.
  assert.equal(C.pedidoDoPainel({familia: 'mapa', indicador: 'taxa', funcao: 'calcular'}), null);
  assert.equal(C.pedidoDoPainel({}), null);
  assert.equal(C.pedidoDoPainel(null), null);
  assert.equal(C.pedidoDoPainel([{familia: 'espacial'}]), null);
  assert.equal(C.pedidoDoPainel('espacial'), null);
});

test('escolha explícita entre alternativas sem o campo painel: a operação vira família ou função', () => {
  assert.deepEqual(C.pedidoDaOperacao('density'), {familia: 'distribuicao', indicador: 'densidade'});
  assert.deepEqual(C.pedidoDaOperacao('counts', 'density'), {familia: 'distribuicao', indicador: 'quantidade'});
  assert.deepEqual(C.pedidoDaOperacao('temporal', 'quantity'), {familia: 'tendencia', indicador: 'quantidade'});
  assert.deepEqual(C.pedidoDaOperacao('distribution'), {familia: 'distribuicao'});
  assert.deepEqual(C.pedidoDaOperacao('nearest'), {familia: 'espacial'});
  assert.deepEqual(C.pedidoDaOperacao('rotation'), {familia: 'rotatividade'});
  assert.deepEqual(C.pedidoDaOperacao('comparisons', 'quantity'), {funcao: 'comparar', indicador: 'quantidade'});
  assert.deepEqual(C.pedidoDaOperacao('aggregate'), {funcao: 'juntar'});
  assert.deepEqual(C.pedidoDaOperacao('ranking'), {funcao: 'ordenar'});
  assert.deepEqual(C.pedidoDaOperacao('criteria'), {funcao: 'condicoes'});
  assert.deepEqual(C.pedidoDaOperacao('report'), {funcao: 'exportar'});
  assert.equal(C.pedidoDaOperacao('none'), null);
  assert.equal(C.pedidoDaOperacao(null), null);
  assert.equal(C.rotuloDoPedido({familia: 'distribuicao', indicador: 'densidade'}), 'distribuição da densidade');
  assert.equal(C.rotuloDoPedido({funcao: 'comparar'}), 'comparação');
  assert.equal(C.rotuloDoPedido({familia: 'espacial', funcao: 'ordenar'}), 'análise espacial, com ordenação');
  assert.equal(C.rotuloDoPedido({nivel: 'estados'}), '');
  assert.equal(C.rotuloDoPedido(null), '');
});

test('contexto do gráfico → opções da conversa: unidades na tela, família, indicador e competência ou janela', () => {
  assert.deepEqual(C.opcoesDaConversa(null, '2026-10-22'), {conversation_today: '2026-10-22', painel_familia: null});
  assert.deepEqual(C.opcoesDaConversa(CONTEXTO, '2026-10-22'), {conversation_today: '2026-10-22',
    territory_ids: ['code:130260', 'code:130420'], exploration_operation: 'density', exploration_indicator: 'density',
    comparison_indicator: 'density', temporal_indicator: 'density', period_filter: '202406', period_filters: [],
    painel_familia: 'distribuicao', painel_indicador: 'densidade', painel_nivel: 'municipios',
    painel_municipios: {todos: false, estados: ['13'], ids: []}, painel_competencia: '202406'});
  // O estado do gráfico vai como está: nível estados, "Todos", a janela da tendência e a referência da análise espacial.
  const estados = C.opcoesDaConversa({...CONTEXTO, nivel: 'estados', idsNaTela: ['uf:13', 'uf:35']}, 'h');
  assert.deepEqual([estados.painel_nivel, estados.painel_municipios], ['estados', {todos: false, estados: ['13'], ids: []}]);
  assert.deepEqual(C.opcoesDaConversa({...CONTEXTO, municipios: {todos: true, estados: [], ids: []}}, 'h').painel_municipios,
    {todos: true, estados: [], ids: []});
  const comJanela = C.opcoesDaConversa({...CONTEXTO, familia: 'tendencia', janela: ['202306', '202406']}, 'h');
  assert.deepEqual(comJanela.painel_janela, ['202306', '202406']);
  assert.equal('painel_janela' in C.opcoesDaConversa(CONTEXTO, 'h'), false);
  assert.deepEqual(C.opcoesDaConversa({...CONTEXTO, familia: 'espacial', referencia: ['code:130260']}, 'h').painel_referencia,
    ['code:130260']);
  assert.equal('painel_referencia' in C.opcoesDaConversa(CONTEXTO, 'h'), false);
  const quantidade = C.opcoesDaConversa({...CONTEXTO, indicador: 'quantidade'}, '2026-10-22');
  assert.deepEqual([quantidade.exploration_operation, quantidade.exploration_indicator, quantidade.comparison_indicator],
    ['counts', 'quantity', 'quantity']);
  // "Todos" é a base inteira, e os estados não são territórios da seleção: nenhuma lista vai ao intérprete.
  assert.equal('territory_ids' in C.opcoesDaConversa({...CONTEXTO, municipios: {todos: true, estados: [], ids: []}}, 'h'), false);
  assert.equal('territory_ids' in C.opcoesDaConversa({...CONTEXTO, nivel: 'estados', idsNaTela: ['uf:13', 'uf:35']}, 'h'), false);
  assert.equal('territory_ids' in C.opcoesDaConversa({...CONTEXTO, idsNaTela: ['c1']}, 'h'), false);
  const tendencia = C.opcoesDaConversa({...CONTEXTO, familia: 'tendencia', janela: ['202106', '202206', '202306', '202406']}, 'h');
  assert.deepEqual([tendencia.exploration_operation, tendencia.period_filter, tendencia.period_filters, tendencia.painel_familia],
    ['temporal', '', ['202106', '202206', '202306', '202406'], 'tendencia']);
  assert.equal(C.opcoesDaConversa({...CONTEXTO, familia: 'espacial'}, 'h').exploration_operation, 'spatial');
  assert.equal(C.opcoesDaConversa({...CONTEXTO, familia: 'rotatividade'}, 'h').exploration_operation, 'rotation');
  // Planilha de outro país: os identificadores "name:" também são do catálogo territorial.
  assert.deepEqual(C.opcoesDaConversa({...CONTEXTO, idsNaTela: ['name:Alfa', 'name:Beta']}, 'h').territory_ids, ['name:Alfa', 'name:Beta']);
  // A vista em exibição, se o mapa está disponível e a frase-resumo do motor vão como a área informou; o backend as tira das
  // opções antes do pré-exame, do intérprete e do provedor de IA. O motivo sem o mapa fica na tela.
  const frase = 'Nos 3 municípios do Amazonas, em junho de 2024, a densidade vai de 1,75 a 5 por 1.000 habitantes.';
  const noMapa = C.opcoesDaConversa({...CONTEXTO, vista: 'mapa', mapaDisponivel: true, motivoSemMapa: null, resumo: frase}, 'h');
  assert.deepEqual([noMapa.painel_vista, noMapa.painel_mapa_disponivel, noMapa.painel_resumo], ['mapa', true, frase]);
  const nosEstados = C.opcoesDaConversa({...CONTEXTO, nivel: 'estados', vista: 'grafico', mapaDisponivel: false,
    motivoSemMapa: 'Os estados não têm um ponto no mapa.', resumo: null}, 'h');
  assert.deepEqual([nosEstados.painel_vista, nosEstados.painel_mapa_disponivel, 'painel_resumo' in nosEstados],
    ['grafico', false, false]);
  assert.equal(JSON.stringify(nosEstados).includes('não têm um ponto'), false);
  for (const chave of ['painel_vista', 'painel_mapa_disponivel', 'painel_resumo'])
    assert.equal(chave in C.opcoesDaConversa(CONTEXTO, 'h'), false, chave);
});

test('orientação da conversa: pergunta na abertura e, na planilha, usa os nomes escolhidos, nunca "município" fixo', () => {
  const DISTRITOS = {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}};
  const BRASIL = {unidade: {singular: 'município', plural: 'municípios'}, grupo: {singular: 'estado', plural: 'estados'}};
  // Na abertura, só as duas entradas dos dados (24/10/2026: o modelo de planilha fica na janela de envio).
  assert.equal(C.guiaDaConversa({tipo: null, pronta: false, colunasPendentes: false}, null, null),
    'O que você quer analisar? Prefere usar os dados do Brasil ou enviar os seus?');
  assert.equal(C.guiaDaConversa({tipo: 'brasil', pronta: false, colunasPendentes: false}, null, null),
    'Estou preparando os dados do Brasil. Em seguida, escolha os territórios que quer analisar.');
  // A base carregada abre sem seleção (23/10/2026): a conversa orienta a escolher os territórios, com os nomes da fonte.
  const semSelecao = {...CONTEXTO, municipios: {todos: false, estados: [], ids: []}};
  assert.equal(C.guiaDaConversa({tipo: 'brasil', pronta: true, colunasPendentes: false}, semSelecao, BRASIL),
    'Os dados estão prontos. Escolha os territórios na Seleção de Territórios ou me diga quais quer ver, por exemplo “mostre o Pará” ' +
    'ou “todos os estados”.');
  assert.equal(C.guiaDaConversa({tipo: 'arquivo', pronta: true, colunasPendentes: false}, semSelecao, DISTRITOS),
    'Os dados estão prontos. Escolha os territórios na Seleção de Territórios ou me diga quais quer ver.');
  assert.match(C.guiaDaConversa({tipo: 'arquivo', pronta: false, colunasPendentes: true}, null, null), /painel Colunas/);
  assert.equal(C.guiaDaConversa({tipo: 'brasil', pronta: true, colunasPendentes: false}, null, BRASIL),
    'Escolha no gráfico quais estados abrir, ou me diga quais municípios quer ver.');
  const estados = {...CONTEXTO, nivel: 'estados'};
  const planilha = C.guiaDaConversa({tipo: 'arquivo', pronta: true, colunasPendentes: false}, estados, DISTRITOS);
  assert.equal(planilha, 'Escolha no gráfico quais províncias abrir, ou me diga quais distritos quer ver.');
  assert.equal(C.guiaDaConversa({tipo: 'arquivo', pronta: true, colunasPendentes: false}, null,
    {unidade: {singular: 'condado', plural: 'condados'}, grupo: null}), 'Escolha condados no gráfico ou me diga quais quer ver.');
  assert.match(C.guiaDaConversa({tipo: 'brasil', pronta: true, colunasPendentes: false}, CONTEXTO, BRASIL), /mostre o Pará/);
  const comandos = C.guiaDaConversa({tipo: 'arquivo', pronta: true, colunasPendentes: false}, CONTEXTO, DISTRITOS);
  assert.equal(comandos, 'Peça mudanças no gráfico citando distritos pelo nome: comparar, juntar, usar como referência ou voltar ' +
    'ao nível de províncias.');
  for (const texto of [planilha, comandos]) assert.doesNotMatch(texto, /munic/i);
});
