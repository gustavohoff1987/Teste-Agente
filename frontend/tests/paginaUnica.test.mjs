import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// Página única (22/10/2026): resumo da fonte, rótulos das unidades, painel "Colunas" da planilha, Histórico e CSV da sessão.
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const P = await source('paginaUnica');

const DISTRITOS = {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}};

test('resumo da fonte: base do Brasil e planilha, com a categoria em frase e o intervalo dos períodos', () => {
  assert.equal(P.competenciaCurta('202406'), 'jun/2024');
  assert.equal(P.competenciaCurta('2024'), '2024');
  assert.equal(P.competenciaCurta('202413'), '202413');
  assert.equal(P.intervaloDePeriodos(['202406', '201401', '201406']), 'jan/2014 a jun/2024');
  assert.equal(P.intervaloDePeriodos(['202406']), 'jun/2024');
  assert.equal(P.intervaloDePeriodos([]), '');
  assert.equal(P.nomeDaCategoria('MEDICINA'), 'Medicina');
  assert.equal(P.nomeDaCategoria('Enfermagem obstétrica'), 'Enfermagem obstétrica');
  assert.equal(P.resumoDaFonte({tipo: 'brasil', nome: 'Dados do Brasil', categorias: ['MEDICINA'], periodos: ['201401', '202406', '201406']}),
    'Dados do Brasil · Medicina · jan/2014 a jun/2024');
  assert.equal(P.resumoDaFonte({tipo: 'arquivo', nome: 'distritos.csv', categorias: [], periodos: ['2021', '2024', '2022'], rotulos: DISTRITOS}),
    'distritos.csv · distritos e províncias · 2021 a 2024');
  assert.equal(P.resumoDaFonte({tipo: 'arquivo', nome: 'a.csv', categorias: ['A', 'B'], periodos: [],
    rotulos: {unidade: {singular: 'condado', plural: 'condados'}, grupo: null}}), 'a.csv · condados · 2 categorias');
});

test('rótulos: fixos na base do Brasil; na planilha, sugeridos pelo nome da coluna, com acento e plural', () => {
  assert.deepEqual(P.ROTULOS_DO_BRASIL, {unidade: {singular: 'município', plural: 'municípios'}, grupo: {singular: 'estado', plural: 'estados'}});
  assert.deepEqual(P.sugerirRotulo('distrito'), {singular: 'distrito', plural: 'distritos'});
  assert.deepEqual(P.sugerirRotulo('provincia'), {singular: 'província', plural: 'províncias'});
  assert.deepEqual(P.sugerirRotulo('nome_distrito'), {singular: 'distrito', plural: 'distritos'});
  assert.deepEqual(P.sugerirRotulo('cod_municipio'), {singular: 'município', plural: 'municípios'});
  assert.deepEqual(P.sugerirRotulo('County'), {singular: 'condado', plural: 'condados'});
  assert.deepEqual(P.sugerirRotulo('Região'), {singular: 'região', plural: 'regiões'});
  assert.deepEqual(P.sugerirRotulo('territorio_superior_1'), {singular: 'território', plural: 'territórios'});
  assert.deepEqual(P.sugerirRotulo('barangay'), {singular: 'barangay', plural: 'barangays'});
  assert.equal(P.sugerirRotulo('cod'), null);
  assert.equal(P.sugerirRotulo(''), null);
  assert.equal(P.pluralizar('canal'), 'canais');
  assert.equal(P.pluralizar('setor'), 'setores');
  assert.equal(P.pluralizar('cantão'), 'cantões');
  assert.equal(P.pluralizar('vila'), 'vilas');
  assert.deepEqual(P.rotulosSugeridos(undefined, undefined), {unidade: {singular: 'unidade', plural: 'unidades'}, grupo: null});
  assert.deepEqual(P.rotulosSugeridos('distrito', 'xpto_1'), {unidade: {singular: 'distrito', plural: 'distritos'},
    grupo: {singular: 'xpto', plural: 'xptos'}});
});

test('colunas: só o reconhecido por regra vem escolhido; escolher uma coluna tira-a do papel anterior e ajusta os nomes', () => {
  const inicio = P.escolhasIniciais({count: 'quantidade', period: 'ano', desconhecido: 'x'});
  assert.deepEqual(inicio.mapeamento, {period: 'ano', count: 'quantidade'});
  assert.deepEqual(inicio.escolhidos, []);
  assert.deepEqual(inicio.rotulos, {unidade: {singular: 'unidade', plural: 'unidades'}, grupo: null});
  let escolhas = P.escolherColuna(inicio, 'territory', 'distrito');
  assert.equal(escolhas.mapeamento.territory, 'distrito');
  assert.deepEqual(escolhas.escolhidos, ['territory']);
  assert.deepEqual(escolhas.rotulos.unidade, {singular: 'distrito', plural: 'distritos'});
  escolhas = P.escolherColuna(escolhas, 'grupo_territorial', 'provincia');
  assert.deepEqual(escolhas.rotulos.grupo, {singular: 'província', plural: 'províncias'});
  // A mesma coluna num papel só: a província como unidade sai do grupo, e o grupo some dos nomes.
  const trocada = P.escolherColuna(escolhas, 'territory', 'provincia');
  assert.equal(trocada.mapeamento.grupo_territorial, undefined);
  assert.equal(trocada.rotulos.grupo, null);
  assert.deepEqual(trocada.rotulos.unidade, {singular: 'província', plural: 'províncias'});
  // Nome editado pela pessoa não acompanha a coluna.
  const editada = P.editarRotulo(escolhas, 'unidade', 'plural', 'distritos sanitários');
  assert.equal(editada.rotulosEditados.unidade, true);
  assert.deepEqual(P.escolherColuna(editada, 'territory', 'outra').rotulos.unidade, {singular: 'distrito', plural: 'distritos sanitários'});
  // Outra coluna de quantidade: a unidade de contagem volta a ser escolhida.
  const contada = {...escolhas, unidadeDeContagem: 'pessoas'};
  assert.equal(P.escolherColuna(contada, 'count', 'total').unidadeDeContagem, '');
  assert.equal(P.escolherColuna(contada, 'population', 'pop').unidadeDeContagem, 'pessoas');
  // Tirar a coluna de um papel tira o papel das escolhas.
  assert.deepEqual(P.escolherColuna(escolhas, 'territory', '').escolhidos, ['grupo_territorial']);
});

test('pendências: unidade territorial, período, quantidade e o que ela conta, quem são os trabalhadores e os nomes', () => {
  const OBJETO = 'Diga quem são os trabalhadores contados, por exemplo, médicos ou enfermeiros.';
  const vazio = P.escolhasIniciais({});
  assert.deepEqual(P.pendenciasDasColunas(vazio), ['Escolha a coluna da unidade territorial.', 'Escolha a coluna do período.',
    'Escolha a coluna da quantidade.', OBJETO]);
  // Sem coluna de categoria, o objeto da análise é escrito pela pessoa e vira category_constant; com a coluna, não é pedido.
  const semObjeto = P.escolhasIniciais({territory: 'distrito', period: 'ano', count: 'quantidade'});
  assert.deepEqual(P.pendenciasDasColunas({...semObjeto, unidadeDeContagem: 'pessoas'}), [OBJETO]);
  assert.deepEqual(P.pendenciasDasColunas({...semObjeto, unidadeDeContagem: 'pessoas', objeto: '  '}), [OBJETO]);
  const comCategoria = P.escolhasIniciais({territory: 'distrito', period: 'ano', count: 'quantidade', category: 'categoria'});
  assert.deepEqual(P.pendenciasDasColunas({...comCategoria, unidadeDeContagem: 'pessoas'}), []);
  const comObjeto = {...semObjeto, unidadeDeContagem: 'pessoas', objeto: ' médicos '};
  assert.deepEqual(P.premissasDaPlanilha(comObjeto), {count_unit: 'pessoas', category_constant: 'médicos'});
  assert.equal(P.contextoDaPlanilha(comObjeto).options.category_constant, 'médicos');
  assert.equal(P.premissasDaPlanilha({...comCategoria, unidadeDeContagem: 'pessoas', objeto: 'médicos'}).category_constant, undefined);
  let escolhas = {...semObjeto, objeto: 'médicos'};
  assert.deepEqual(P.pendenciasDasColunas(escolhas), ['Diga o que a quantidade conta: pessoas, vínculos, postos ou outra unidade.']);
  escolhas = {...escolhas, unidadeDeContagem: 'outro'};
  assert.deepEqual(P.pendenciasDasColunas(escolhas), ['Descreva a unidade de contagem.']);
  escolhas = {...escolhas, textoDaUnidade: 'equipes'};
  assert.deepEqual(P.pendenciasDasColunas(escolhas), []);
  const semNome = P.editarRotulo(P.escolherColuna(escolhas, 'grupo_territorial', 'provincia'), 'grupo', 'plural', ' ');
  assert.deepEqual(P.pendenciasDasColunas(semNome), ['Diga como se chamam os grupos, no singular e no plural.']);
});

test('planilha no pré-exame e na conversa: o grupo vai em hierarchy_columns; no motor do gráfico e na conversa, também no mapeamento', () => {
  let escolhas = P.escolhasIniciais({territory: 'distrito', period: 'ano', count: 'quantidade', latitude: 'lat', longitude: 'lon'});
  escolhas = P.escolherColuna(escolhas, 'grupo_territorial', 'provincia');
  escolhas = {...escolhas, unidadeDeContagem: 'pessoas', referencial: 'SIRGAS2000'};
  const {mapping, options} = P.contextoDaPlanilha(escolhas);
  assert.deepEqual(mapping, {territory: 'distrito', period: 'ano', count: 'quantidade', latitude: 'lat', longitude: 'lon'});
  assert.deepEqual(options, {confirmed_roles: [], count_unit: 'pessoas', crs: 'SIRGAS2000',
    hierarchy_columns: {territorio_superior_1: 'provincia'}});
  assert.deepEqual(P.mapeamentoDaPlanilha(escolhas.mapeamento), {territory: 'distrito', grupo_territorial: 'provincia', period: 'ano',
    count: 'quantidade', latitude: 'lat', longitude: 'lon'});
  // A conversa (28/10/2026) recebe o papel do grupo no mapeamento, que o backend tira antes do pré-exame e usa para reconhecer os
  // grupos pelo nome ("mostre a província …"); sem grupo, o mapeamento é o do pré-exame.
  assert.deepEqual(P.mapeamentoDaConversa(escolhas), {...mapping, grupo_territorial: 'provincia'});
  assert.deepEqual(P.mapeamentoDaConversa(P.escolherColuna(escolhas, 'grupo_territorial', '')), mapping);
  assert.deepEqual(P.premissasDaPlanilha(escolhas), {count_unit: 'pessoas', crs: 'SIRGAS2000'});
  // Só SIRGAS 2000 e WGS 84 (aprovado em 22/10/2026) viram premissa, como informados, sem conversão; outro referencial, ou
  // nenhum, não vira premissa.
  assert.deepEqual(P.REFERENCIAIS, [['SIRGAS2000', 'SIRGAS 2000'], ['WGS84', 'WGS 84'], ['outro', 'Outro referencial'],
    ['desconhecido', 'Não sei']]);
  assert.deepEqual(P.premissasDaPlanilha({...escolhas, referencial: 'WGS84'}), {count_unit: 'pessoas', crs: 'WGS84'});
  assert.equal(P.contextoDaPlanilha({...escolhas, referencial: 'WGS84'}).options.crs, 'WGS84');
  assert.deepEqual(P.premissasDaPlanilha({...escolhas, referencial: 'outro'}), {count_unit: 'pessoas'});
  assert.equal(P.contextoDaPlanilha({...escolhas, referencial: 'desconhecido'}).options.crs, undefined);
  // Sem latitude e longitude, nem o referencial nem o separador seguem.
  const semCoordenadas = {...P.escolherColuna(escolhas, 'latitude', ''), separador: 'decimal_comma'};
  assert.deepEqual(P.premissasDaPlanilha(semCoordenadas), {count_unit: 'pessoas'});
  // Papéis escolhidos pela pessoa (o grupo não é papel do pré-exame).
  const escolhida = P.escolherColuna(escolhas, 'population', 'pop');
  assert.deepEqual(P.contextoDaPlanilha(escolhida).options.confirmed_roles, ['population']);
  // No motor do gráfico também: a coluna escolhida vai em confirmed_roles (D1); o grupo não é papel do motor comum.
  assert.deepEqual(P.premissasDaPlanilha(escolhida), {confirmed_roles: ['population'], count_unit: 'pessoas', crs: 'SIRGAS2000'});
  assert.deepEqual(P.premissasDaPlanilha({...escolhas, unidadeDeContagem: 'outro', textoDaUnidade: ' equipes '}),
    {count_unit: 'outro', custom_count_unit: 'equipes', crs: 'SIRGAS2000'});
});

test('o que a planilha permite: indisponível com o motivo, inclusive o referencial que não é SIRGAS 2000 nem WGS 84', () => {
  const capacidades = {counts: {status: 'available', reasons: []}, density: {status: 'unavailable', reasons: ['Sem população.']},
    spatial: {status: 'needs_confirmation', reasons: ['Selecione o território de referência.']},
    temporal: {status: 'unavailable', reasons: ['Evolução temporal exige ao menos dois períodos reconhecidos.']},
    rotation: {status: 'unavailable', reasons: ['Rotatividade exige um identificador individual da mesma pessoa.']}};
  const escolhas = P.escolhasIniciais({territory: 'distrito', period: 'ano', count: 'quantidade'});
  assert.deepEqual(P.disponibilidadeDaPlanilha(undefined, escolhas, false), []);
  const lista = P.disponibilidadeDaPlanilha(capacidades, escolhas, false);
  assert.deepEqual(lista.map(item => [item.familia, item.disponivel]),
    [['distribuicao', true], ['espacial', false], ['tendencia', false], ['rotatividade', false]]);
  // Os mesmos nomes das abas da área de análise.
  assert.deepEqual(lista.map(item => item.rotulo),
    ['Análise de Distribuição', 'Análise Espacial', 'Análise de Tendência', 'Análise de Rotatividade']);
  assert.equal(lista[1].motivo, 'Faltam as colunas de latitude e longitude.');
  assert.equal(lista[2].motivo, 'Evolução temporal exige ao menos dois períodos reconhecidos.');
  assert.equal(lista[3].motivo, 'Falta a coluna do identificador individual.');
  const coordenadas = {...escolhas, mapeamento: {...escolhas.mapeamento, latitude: 'lat', longitude: 'lon'}};
  const espacial = referencial => P.disponibilidadeDaPlanilha(capacidades, {...coordenadas, referencial}, false)[1];
  assert.equal(espacial('').motivo, 'Escolha o referencial das coordenadas.');
  assert.equal(espacial('outro').motivo,
    'Só os referenciais SIRGAS 2000 e WGS 84 são admitidos; com outro, ou sem saber qual é, nada é presumido.');
  assert.equal(espacial('desconhecido').disponivel, false);
  // A escolha pendente da referência é feita no gráfico: não torna a análise espacial indisponível.
  assert.equal(espacial('SIRGAS2000').disponivel, true);
  assert.equal(espacial('WGS84').disponivel, true);
  const misto = P.disponibilidadeDaPlanilha(capacidades, {...coordenadas, referencial: 'SIRGAS2000'}, true)[1];
  assert.deepEqual([misto.disponivel, misto.motivo], [false, 'Escolha o separador decimal das coordenadas.']);
  const semMedida = P.disponibilidadeDaPlanilha({...capacidades, counts: {status: 'unavailable', reasons: ['Escolha a coluna de quantitativos.']}},
    escolhas, false)[0];
  assert.deepEqual([semMedida.disponivel, semMedida.motivo], [false, 'Escolha a coluna de quantitativos.']);
});

test('Histórico: a análise em exibição é atualizada, a nova entra no fim, e a anterior é a da mesma fonte', () => {
  const estado = titulo => ({titulo, definicao: {}, resposta: null, quando: '2026-10-22T14:05:00'});
  let lista = P.registrarEstado([], {id: 1, fonteChave: 'brasil:v1', fonteNome: 'Dados do Brasil', estado: estado('A')});
  lista = P.registrarEstado(lista, {id: 2, fonteChave: 'brasil:v1', fonteNome: 'Dados do Brasil', estado: estado('B')});
  lista = P.registrarEstado(lista, {id: 1, fonteChave: 'brasil:v1', fonteNome: 'Dados do Brasil', estado: estado('A2')});
  assert.deepEqual(lista.map(item => [item.id, item.estado.titulo]), [[1, 'A2'], [2, 'B']]);
  lista = P.registrarEstado(lista, {id: 3, fonteChave: 'arquivo:5', fonteNome: 'x.csv', estado: estado('C')});
  assert.equal(P.analiseAnterior(lista, 4, 'brasil:v1').id, 2);
  assert.equal(P.analiseAnterior(lista, 2, 'brasil:v1').id, 1);
  assert.equal(P.analiseAnterior(lista, 1, 'brasil:v1'), null);
  assert.equal(P.analiseAnterior(lista, 9, 'arquivo:7'), null);
  assert.equal(P.horaDe('2026-10-22T14:05:00'), '14:05');
  assert.equal(P.horaDe('ontem'), 'ontem');
  assert.equal(P.resultadoDaSessao({...estado('A'), resposta: {sessao: {registrado: true, result_id: 'r1'}}}), 'r1');
  assert.equal(P.resultadoDaSessao({...estado('A'), resposta: {sessao: {registrado: false, result_id: 'r1'}}}), '');
  assert.equal(P.resultadoDaSessao(null), '');
  // A resposta guardada pela área é a normalizada por painelApi (sessao.resultId): a conversa recebe o resultado em exibição.
  assert.equal(P.resultadoDaSessao({...estado('A'), resposta: {sessao: {registrado: true, resultId: 'r2'}}}), 'r2');
  assert.equal(P.resultadoDaSessao({...estado('A'), resposta: {sessao: {registrado: false, resultId: 'r2'}}}), '');
  assert.equal(P.resultadoDaSessao({...estado('A'), resposta: {sessao: {registrado: true, resultId: null}}}), '');
  assert.equal(P.dataLocal(new Date(2026, 9, 2)), '2026-10-02');
});

test('CSV da análise em exibição: todos os campos do motor, em precisão integral, sem fórmulas', () => {
  const resposta = {itens: [
    {id: 'code:130420', tipo: 'municipio', rotulo: 'TEFE (AM)', densidade: 0.7058823529411765, distancia_km: null,
      avaliavel: {densidade: true, distancia: null}, motivos: ['Sem coordenada (COORDENADA_INVALIDA)', 'x'], variacao: -1.5},
    {id: 'c1', tipo: 'conjunto', rotulo: '=SOMA(A1)', densidade: 2, membros: ['code:1', 'code:2'], extra: [{a: 1}], nota: 'diz "oi"'},
  ]};
  const linhas = P.csvDaResposta(resposta).split('\r\n');
  assert.ok(linhas[0].startsWith('﻿'));
  const cabecalho = linhas[0].slice(1).split(';');
  assert.deepEqual(cabecalho, ['"id"', '"tipo"', '"rotulo"', '"densidade"', '"distancia_km"', '"avaliavel.densidade"',
    '"avaliavel.distancia"', '"motivos"', '"variacao"', '"membros"', '"extra"', '"nota"']);
  assert.equal(linhas[1], '"code:130420";"municipio";"TEFE (AM)";"0.7058823529411765";"";"true";"";' +
    '"Sem coordenada (COORDENADA_INVALIDA) | x";"-1.5";"";"";""');
  assert.equal(linhas[2], '"c1";"conjunto";"\'=SOMA(A1)";"2";"";"";"";"";"";"code:1 | code:2";"[{""a"":1}]";"diz ""oi"""');
  assert.equal(P.csvDaResposta({itens: []}), '');
  assert.equal(P.csvDaResposta(null), '');
  // Os grupos do mapa (só para pintar o mapa) ficam fora; os grupos da análise continuam.
  const comMapa = P.csvDaResposta({itens: [{id: 'a', densidade: 1, grupo: {indice: 2, rotulo: '2º quartil'},
    grupoMapa: {indice: 3, rotulo: '3º quintil'}, grupo_mapa: {indice: 3, rotulo: '3º quintil'}}]});
  assert.equal(comMapa.split('\r\n')[0], '﻿"id";"densidade";"grupo.indice";"grupo.rotulo"');
});
