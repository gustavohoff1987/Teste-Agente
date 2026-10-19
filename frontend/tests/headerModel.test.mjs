import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {groupDigits, kpiSeries, kpiView, partText, periodsInText, resolvePath, sparkGeometry, summaryOf, summaryParts} = await source('headerModel');
const {displayPeriod, formatNumber} = await source('representation');
const fmt = {number: (value, kind) => formatNumber(value, kind || 'CONTINUO'), period: displayPeriod};

// Resultado no formato do motor (metadata.representacao.resumo, backend/result_summary.py); os números são do motor.
const result = {
  result_id: 'r1', total_rows: 3,
  rows: [{'Nível': 'Brasil (total nacional)', 'Território': 'Brasil', 'Período': '202406', Categoria: 'MEDICINA', Quantidade: 502495,
    'População': 212583750, 'Densidade por 1.000': 2.363750757054573},
  {'Objeto A': 'A', 'Valor A': 20.0, 'Objeto B': 'B', 'Valor B': 30.0, 'Diferença A − B': -10.0}],
  metrics: [{label: 'Municípios: registros avaliáveis', value: 5570, nivel: 'MUN'}],
  metadata: {periods: ['202406'], categories: ['MEDICINA'],
    referencia_nacional: {serie: [
      {competencia: '202306', categoria: 'MEDICINA', valor: 2.2, avaliabilidade: 'AVALIAVEL'},
      {competencia: '201506', categoria: 'MEDICINA', valor: null, avaliabilidade: 'NAO_AVALIAVEL'},
      {competencia: '202406', categoria: 'MEDICINA', valor: 2.36, avaliabilidade: 'AVALIAVEL'},
      {competencia: '201406', categoria: 'MEDICINA', valor: 1.59, avaliabilidade: 'AVALIAVEL'}]},
    representacao: {versao: 1, resumo: {versao: 1, modelo: 'density', texto: '', partes: [
      {texto: 'Na competência '}, {texto: '202406', segmento: 0, tipo: 'PARAMETRO', caminho: ['metadata', 'periods', 0]},
      {texto: ', '}, {texto: '5570', segmento: 1, tipo: 'VALOR', caminho: ['metrics', 0, 'value']},
      {texto: ' registros; diferença '}, {texto: '-10,00', segmento: 2, tipo: 'VALOR', caminho: ['rows', 1, 'Diferença A − B']},
      {texto: '; densidade '}, {texto: '2,36', segmento: 3, tipo: 'VALOR', caminho: ['rows', 0, 'Densidade por 1.000']},
      {texto: ' O valor de A é menor que o de B.', segmento: 4, tipo: 'RELACAO', caminho: ['rows', 1]}],
    indicadores: [
      {rotulo: 'Brasil (total nacional)', caminho: ['rows', 0, 'Densidade por 1.000'], valor: 2.363750757054573, texto: '2,36', tipo: 'CONTINUO',
        unidade: 'por 1.000 habitantes', nivel: 'BR', serie: {caminho: ['metadata', 'referencia_nacional', 'serie'], periodo: 'competencia', valor: 'valor'}},
      {rotulo: 'Taxa nacional (referência de contexto)', tipo: 'CONTINUO', unidade: 'por 1.000 habitantes', papel: 'REFERENCIA_DE_CONTEXTO',
        serie: {caminho: ['metadata', 'referencia_nacional', 'serie'], periodo: 'competencia', valor: 'valor'}},
      {rotulo: 'Brasil (total nacional) em 202406', caminho: ['metrics', 0, 'value'], valor: 5570, texto: '5570', tipo: 'CONTAGEM'}],
    procedencia: [{rotulo: 'Chave de execução', valor: 'abc123def456'}]}}},
};

test('resumo do motor só na versão 1, com partes e indicadores; resultado antigo fica com a grade de métricas', () => {
  assert.equal(summaryOf(result.metadata).modelo, 'density');
  assert.equal(summaryOf({representacao: {versao: 1}}), null);
  assert.equal(summaryOf({representacao: {resumo: {versao: 2, partes: [], indicadores: []}}}), null);
  assert.equal(summaryOf(undefined), null);
});

test('partes da frase: competência como mês/ano, inteiro com milhar, sinal tipográfico; texto fixo e relação como estão', () => {
  const resumo = summaryOf(result.metadata);
  const parts = summaryParts(resumo, result, fmt);
  assert.deepEqual(parts.map(part => part.text), ['Na competência ', '06/2024', ', ', '5.570', ' registros; diferença ', '−10,00',
    '; densidade ', '2,36', ' O valor de A é menor que o de B.']);
  assert.deepEqual(parts.map(part => part.value), [false, true, false, true, false, true, false, true, true]);
  // Valor inteiro escrito com casas pelo motor (densidade 15,00) continua com as casas do motor.
  assert.equal(partText({texto: '15,00', tipo: 'VALOR', caminho: ['x']}, {x: 15}, fmt), '15,00');
  // Caminho que não resolve: o texto do motor.
  assert.equal(partText({texto: '7', tipo: 'VALOR', caminho: ['nada', 0]}, result, fmt), '7');
});

test('milhar e sinal sem mudar as casas escritas pelo motor; competências em rótulos', () => {
  assert.equal(groupDigits('212583750,5'), '212.583.750,5');
  assert.equal(groupDigits('-3,6667'), '−3,6667');
  assert.equal(groupDigits('abc'), 'abc');
  assert.equal(periodsInText('Brasil (total nacional) em 202406', fmt), 'Brasil (total nacional) em 06/2024');
  assert.equal(periodsInText('Código 130260 e 201413', fmt), 'Código 130260 e 201413');  // mês inválido não é competência
  assert.equal(resolvePath({a: [{b: 1}]}, ['a', 0, 'b']), 1);
  assert.equal(resolvePath({a: null}, ['a', 'b']), undefined);
});

test('KPIs: valor do motor; sem valor único, o último ponto avaliável da série (seleção); minigráfico em ordem, com lacuna', () => {
  const [brazil, national, labelled] = summaryOf(result.metadata).indicadores.map(item => kpiView(item, result, fmt));
  assert.equal(brazil.value, '2,36');
  assert.equal(brazil.level, 'BR');
  assert.deepEqual(brazil.spark.map(point => point.period), ['201406', '201506', '202306', '202406']);
  assert.deepEqual(brazil.spark.map(point => point.value), [1.59, null, 2.2, 2.36]);
  assert.equal(national.context, true);
  assert.equal(national.full, 2.36);
  assert.equal(national.period, '202406');
  assert.equal(labelled.label, 'Brasil (total nacional) em 06/2024');
  assert.equal(labelled.value, '5.570');
  assert.equal(labelled.kind, 'CONTAGEM');
});

test('série do KPI: só a categoria do próprio KPI (ou a única do resultado); sem duas competências, nenhum minigráfico', () => {
  const rows = [{'Período': '202406', Categoria: 'A', Quantidade: 3}, {'Período': '202306', Categoria: 'A', Quantidade: 2},
    {'Período': '202406', Categoria: 'B', Quantidade: 9}];
  const own = {rotulo: 'x', caminho: ['rows', 0, 'Quantidade'], valor: 3, tipo: 'CONTAGEM', serie: {caminho: ['rows'], periodo: 'Período', valor: 'Quantidade'}};
  assert.deepEqual(kpiSeries(own, {rows, metadata: {categories: ['A', 'B']}}), [{period: '202306', value: 2}, {period: '202406', value: 3}]);
  const loose = {...own, caminho: undefined};
  assert.equal(kpiSeries(loose, {rows, metadata: {categories: ['A', 'B']}}), null);  // categorias misturadas: sem minigráfico
  assert.equal(kpiSeries({...own, caminho: ['rows', 2, 'Quantidade']}, {rows, metadata: {}}), null);  // uma competência só
});

test('geometria do minigráfico: lacuna quebra a linha; valores iguais no meio da altura', () => {
  const geometry = sparkGeometry([{period: '1', value: 1}, {period: '2', value: null}, {period: '3', value: 3}, {period: '4', value: 2}], 100, 40, 0);
  assert.equal(geometry.segments.length, 2);
  assert.deepEqual(geometry.segments[0], [[0, 40]]);
  assert.deepEqual(geometry.segments[1], [[200 / 3, 0], [100, 20]]);
  assert.deepEqual(geometry.domain, [1, 3]);
  const flat = sparkGeometry([{period: '1', value: 5}, {period: '2', value: 5}], 100, 40, 0);
  assert.deepEqual(flat.dots.map(dot => dot.y), [20, 20]);
});
