import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {aggregateMembers, cohortBars, colorPosition, colorScaleFor, comparisonModel, distributionStrip, neighborTexts, position,
  scaleTicks, seriesSegments, smallMultiples, temporalDumbbells, valueExtent, visibleRange, zeroExtent} = await source('visualModels');

// Comparação com competência dos valores e janela, no formato do motor (backend/comparison_window.py e territorial_levels.py).
const window = {'Período inicial': '201406', 'Período final': '202406', 'Direção da mudança': 'Aumento',
  'Condição da mudança': 'Avaliável', 'Observações da tendência': 11};
const levels = {
  rows: [
    {'Nível': 'Brasil (total nacional)', 'Período': '202406', Categoria: 'MEDICINA', 'Território': 'Brasil', 'Densidade por 1.000': 2.36,
      'Condição': 'Lado a lado: o Brasil é outro nível e não entra em maior, menor nem diferença com estados ou municípios.'},
    {'Nível': 'Estado', 'Período': '202406', Categoria: 'MEDICINA', 'Objeto A': 'Amazonas (AM)', 'Valor A': 1.4,
      'Objeto B': 'São Paulo (SP)', 'Valor B': 3.24, 'Relação A/B': 'MENOR', 'Diferença A − B': -1.84, 'Condição': 'Comparável'},
    {'Nível': 'Município', 'Período': '202406', Categoria: 'MEDICINA', 'Território': 'MANAUS [130260]', 'Densidade por 1.000': 2.07, 'Condição': 'Comparável'},
    {'Nível': 'Município', 'Período': '202406', Categoria: 'MEDICINA', 'Território': 'TEFE [130420]', 'Densidade por 1.000': 0.87, 'Condição': 'Comparável'},
    {'Nível': 'Município', 'Período': '202406', Categoria: 'MEDICINA', 'Território': 'PARINTINS [130340]', 'Densidade por 1.000': 1.16, 'Condição': 'Comparável'}],
  detail_rows: [
    {'Nível': 'Brasil (total nacional)', 'Território': 'Brasil', Categoria: 'MEDICINA', 'Período': '202406', Quantidade: 502495, 'População': 212583750,
      'Densidade por 1.000': 2.36, 'Tipo de contagem': 'Unidades distintas: contagem nacional', 'Condição': 'Avaliável', ...window,
      Inicial: 1.59, Final: 2.36, 'Variação absoluta': 0.78, 'Tendência': 'Crescimento', 'Motivo da tendência': null},
    {'Nível': 'Estado', 'Território': 'Amazonas (AM)', Categoria: 'MEDICINA', 'Período': '202406', Quantidade: 5990,
      'População': 4281209, 'Densidade por 1.000': 1.4, 'Tipo de contagem': 'Unidades distintas: contagem estadual (não é a soma dos municípios)',
      'Condição': 'Avaliável', ...window, Inicial: 0.94, Final: 1.4, 'Variação absoluta': 0.46, 'Tendência': 'Crescimento', 'Motivo da tendência': null},
    {'Nível': 'Estado', 'Território': 'São Paulo (SP)', Categoria: 'MEDICINA', 'Período': '202406', Quantidade: 148909,
      'População': 45973194, 'Densidade por 1.000': 3.24, 'Tipo de contagem': 'Unidades distintas: contagem estadual (não é a soma dos municípios)',
      'Condição': 'Avaliável', ...window, Inicial: 2.2, Final: 3.24, 'Variação absoluta': 1.04, 'Tendência': 'Crescimento', 'Motivo da tendência': null},
    {'Nível': 'Município', 'Território': 'MANAUS [130260]', Categoria: 'MEDICINA', 'Período': '202406', Quantidade: 4730, 'População': 2279686,
      'Densidade por 1.000': 2.07, 'Tipo de contagem': 'Unidades distintas: pessoas', 'Condição': 'Avaliável', ...window, Inicial: 1.44, Final: 2.07,
      'Variação absoluta': 0.63, 'Tendência': 'Sem classificação', 'Motivo da tendência': 'Mudança de direção'}],
  metadata: {indicator: 'density', comparacao: {competencia_valores: '202406', indicador: 'density', mudanca_e_tendencia: true,
    janela: {periodos: [], inicio: '201406', fim: '202406', competencias: 11},
    grupos: [{nivel: 'BR', objetos: ['Brasil'], relacoes: false}, {nivel: 'UF', objetos: ['Amazonas (AM)', 'São Paulo (SP)'], relacoes: true},
      {nivel: 'MUN', objetos: ['MANAUS [130260]'], relacoes: true}]}},
};

test('comparação: grupos por nível na ordem Brasil, estados, municípios; par com a relação e a diferença do motor', () => {
  const model = comparisonModel(levels);
  assert.equal(model.valuesPeriod, '202406');
  assert.deepEqual(model.window, {start: '201406', end: '202406', count: 11});
  assert.equal(model.withChange, true);
  assert.deepEqual(model.groups.map(group => group.level), ['BR', 'UF', 'MUN']);
  const [brazil, states, towns] = model.groups;
  assert.equal(brazil.relations, false);
  assert.equal(brazil.pair, null);
  assert.deepEqual(states.pair, {a: 'Amazonas (AM)', b: 'São Paulo (SP)', valueA: 1.4, valueB: 3.24, relation: 'MENOR', difference: -1.84,
    condition: 'Comparável'});
  assert.equal(states.countType, 'Unidades distintas: contagem estadual (não é a soma dos municípios)');
  assert.equal(towns.relations, false);  // um município só: nada a relacionar
  const amazonas = states.objects[0];
  assert.deepEqual([amazonas.quantity, amazonas.population, amazonas.density, amazonas.value], [5990, 4281209, 1.4, 1.4]);
  assert.deepEqual([amazonas.window.initial, amazonas.window.final, amazonas.window.delta, amazonas.window.trend],
    [0.94, 1.4, 0.46, 'Crescimento']);
});

test('comparação sem competência dos valores: valores das relações num recorte; vários recortes ficam na tabela', () => {
  const pair = {rows: [{'Período': '2024', Categoria: 'M', 'Objeto A': 'A', 'Valor A': 20, 'Objeto B': 'B', 'Valor B': 30,
    'Relação A/B': 'MENOR', 'Diferença A − B': -10, 'Condição': 'Comparável'}], metadata: {indicator: 'quantity'}};
  const model = comparisonModel(pair);
  assert.equal(model.detailed, false);
  assert.equal(model.column, 'Quantidade');
  assert.deepEqual(model.groups[0].objects.map(item => [item.territory, item.value]), [['A', 20], ['B', 30]]);
  assert.equal(model.groups[0].pair.difference, -10);
  const several = {rows: [...pair.rows, {...pair.rows[0], 'Período': '2023'}], metadata: {}};
  assert.deepEqual(comparisonModel(several).groups, []);
});

test('halteres da evolução: uma linha do motor por território e categoria, na ordem do resultado', () => {
  const rows = [{'Território': 'B', Categoria: 'M', Inicial: 2, Final: 1, 'Variação absoluta': -1, 'Tendência': 'Declínio'},
    {'Território': 'A', Categoria: 'M', Inicial: null, Final: 3, 'Variação absoluta': null, 'Condição da mudança': 'Não avaliável'},
    {'Território': 'A', Categoria: 'N', Inicial: 1, Final: 2, 'Variação absoluta': 1}];
  const items = temporalDumbbells(rows, 'M');
  assert.deepEqual(items.map(item => [item.territory, item.initial, item.final, item.delta]), [['B', 2, 1, -1], ['A', null, 3, null]]);
  assert.equal(items[1].condition, 'Não avaliável');
});

test('pequenos múltiplos: mesmas competências e mesma escala em todas as páginas; ausência como lacuna', () => {
  const spec = {periodo: 'Período', territorio: 'Território', categoria: 'Categoria', valor: 'Valor'};
  const source = [];
  ['A', 'B', 'C'].forEach((name, index) => ['202306', '202406'].forEach(period => {
    if (!(name === 'B' && period === '202306')) source.push({'Território': name, 'Período': period, Categoria: 'M', Valor: index * 10 + Number(period.slice(3, 4))});
  }));
  const first = smallMultiples(source, spec, ['A', 'B', 'C'], 'M', 0, 2);
  const second = smallMultiples(source, spec, ['A', 'B', 'C'], 'M', 1, 2);
  assert.deepEqual(first.periods, ['202306', '202406']);
  assert.equal(first.pages, 2);
  assert.deepEqual(first.items.map(item => item.territory), ['A', 'B']);
  assert.deepEqual(second.items.map(item => item.territory), ['C']);
  assert.deepEqual(first.domain, second.domain);
  assert.deepEqual(first.items[1].points.map(point => point.value), [null, 14]);
  assert.equal(smallMultiples(source, spec, ['A'], 'M', 9, 2).page, 0);  // página fora do intervalo volta à existente
  const {segments, dots} = seriesSegments([{value: 1}, {value: null}, {value: 2}, {value: 3}], 100, 50, [1, 3], 0);
  assert.equal(segments.length, 2);
  assert.equal(dots.length, 3);
  assert.deepEqual(segments[0], [[0, 50]]);
});

test('escala de cor do mapa: contínua (sem classes), logarítmica só com valores positivos, domínio [mínimo, máximo]', () => {
  assert.equal(colorScaleFor([0.23, 81.07], 'logaritmica'), 'logaritmica');
  assert.equal(colorScaleFor([0, 81.07], 'logaritmica'), 'linear');
  assert.equal(colorScaleFor([0.23, 81.07], 'linear'), 'linear');
  assert.equal(colorScaleFor(null, 'logaritmica'), 'linear');
  const domain = [0.23, 81.07];
  assert.equal(colorPosition(0.23, domain, 'logaritmica'), 0);
  assert.equal(colorPosition(81.07, domain, 'logaritmica'), 1);
  // 2,36 por 1.000: quase no começo da escala linear e bem mais adiante na logarítmica (melhor leitura dos valores baixos).
  assert.ok(colorPosition(2.36, domain, 'linear') < 0.03);
  assert.ok(colorPosition(2.36, domain, 'logaritmica') > 0.35);
  // Monótona: a ordem dos valores é a ordem das cores.
  const values = [0.23, 0.5, 1, 2, 5, 10, 40, 81.07].map(value => colorPosition(value, domain, 'logaritmica'));
  assert.deepEqual([...values].sort((a, b) => a - b), values);
  assert.equal(colorPosition(5, [5, 5], 'logaritmica'), 0.5);
  assert.equal(colorPosition(-1, [0, 10], 'linear'), 0);
});

test('marcas da legenda: 1, 2 e 5 × 10ⁿ dentro do domínio, longe das pontas; nenhuma na linear', () => {
  const ticks = scaleTicks([0.23, 81.07], 'logaritmica');
  assert.ok(ticks.length >= 2);
  assert.ok(ticks.every(tick => [1, 2, 5].includes(Number(String(tick.value).replace(/0+$|\./g, '').replace(/^0+/, '')))));
  assert.ok(ticks.every((tick, index) => index === 0 || tick.at - ticks[index - 1].at >= 0.14));
  assert.ok(ticks.every(tick => tick.at >= 0.08 && tick.at <= 0.92));
  assert.deepEqual(scaleTicks([0.23, 81.07], 'linear'), []);
  assert.deepEqual(scaleTicks([0, 10], 'logaritmica'), []);
});

test('faixa da distribuição: raia da classe do motor, na ordem das classes; sem valor, fora da faixa', () => {
  const summary = [{Classe: 'Q1', Quintil: '1º quintil — Menores valores'}, {Classe: 'Q2', Quintil: '2º quintil — Valores baixos'}];
  const detail = [{'Território': 'A', Quintil: '2º quintil', D: 5}, {'Território': 'B', Quintil: '1º quintil', D: 1},
    {'Território': 'C', Quintil: '1º quintil', D: null}];
  const strip = distributionStrip(summary, detail, 'D');
  assert.deepEqual(strip.lanes, ['1º quintil', '2º quintil']);
  assert.deepEqual(strip.points.map(point => [point.territory, point.lane]), [['A', 1], ['B', 0]]);
  assert.deepEqual(strip.domain, [1, 5]);
});

test('coorte, agregação e escalas de desenho: só valores do motor', () => {
  const [bar] = cohortBars([{'Território': 'ALFA', Categoria: 'M', 'Período inicial': '202401', 'Período final': '202406', 'Coorte inicial': 10,
    Permanecem: 6, 'Saíram': 4, 'Permanência (%)': 60, 'Rotatividade (%)': 40, 'Condição': 'Avaliável'}]);
  assert.deepEqual([bar.stay, bar.left, bar.stayShare, bar.leftShare], [6, 4, 60, 40]);
  const {members, expansions} = aggregateMembers({universe: {members: [{id: 'code:1', label: 'Um', state: 'AM'}]},
    selecao_territorial: {expansoes: [{id: 'mun:uf:13', ausentes_por_competencia: {'202406': ['130001']}}]}});
  assert.deepEqual(members, [{id: 'code:1', label: 'Um', state: 'AM'}]);
  assert.equal(expansions.length, 1);
  assert.deepEqual(zeroExtent([3, null, 5]), [0, 5]);
  assert.deepEqual(zeroExtent([-2, 4]), [-2, 4]);
  assert.deepEqual(valueExtent([2, 2]), [1.8, 2.2]);
  assert.equal(position(5, [0, 10]), 0.5);
  assert.equal(position(20, [0, 10]), 1);
  assert.deepEqual(visibleRange(0, 30, 100, 20), {start: 0, end: 20});
  assert.deepEqual(visibleRange(3000, 30, 100, 20), {start: 80, end: 100});
});

test('valores vizinhos que o arredondamento igualaria ganham as casas que os distinguem, sem reordenar nem comparar', () => {
  const format = value => value.toFixed(2).replace('.', ',');
  const pair = (a, b) => { for (let digits = 2; digits <= 8; digits++) { const fa = a.toFixed(digits), fb = b.toFixed(digits);
    if (fa !== fb) return [fa.replace('.', ','), fb.replace('.', ',')]; } return [format(a), format(b)]; };
  // Roraima e Piauí em 06/2024 (posições 21 e 22 dos estados): 1,9810… e 1,9783… viram 1,981 e 1,978.
  assert.deepEqual(neighborTexts([2.5659, 1.98104613, 1.97828800, 1.8509], format, pair), ['2,57', '1,981', '1,978', '1,85']);
  // Valores iguais continuam iguais; ausência fica vazia (a tela escreve "Não avaliável"); a ordem é a recebida.
  assert.deepEqual(neighborTexts([1.5, 1.5, null, 0.2], format, pair), ['1,50', '1,50', '', '0,20']);
  assert.deepEqual(neighborTexts([], format, pair), []);
});
