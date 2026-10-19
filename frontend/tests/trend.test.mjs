import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {classOfLabel, countGroups, familyFilterOptions, familyOfClass, stageNote, trendMeta, trendMotiveText, unitVelocities,
  velocityBars} = await source('trend');

// Formato de metadata.tendencia entregue pelo motor (backend/temporal_change.py); os números são do motor.
const classes = [
  ['CRESCIMENTO', 'Crescimento', 'CRESCIMENTO'], ['CRESCIMENTO_ACELERADO', 'Aceleração do crescimento', 'CRESCIMENTO'],
  ['CRESCIMENTO_DESACELERADO', 'Desaceleração do crescimento', 'CRESCIMENTO'], ['DECLINIO', 'Declínio', 'DECLINIO'],
  ['DECLINIO_ACELERADO', 'Aceleração do declínio', 'DECLINIO'], ['DECLINIO_DESACELERADO', 'Desaceleração do declínio', 'DECLINIO'],
  ['SEM_CLASSIFICACAO', 'Sem classificação', 'NENHUMA'],
].map(([codigo, rotulo, familia]) => ({codigo, rotulo, familia}));
const meta = {
  capacidade: 'CAP-TEN-01', versao_metodo: 'CAP-TEN-01/DA-15/1', desfecho: 'RES-LIM', bloqueio: null,
  unidades_total: 9, avaliaveis: 8, nao_avaliaveis: 1, indicador: 'quantity', unidade_valor: 'pessoas', unidade_tempo: 'mês',
  contagens: {CRESCIMENTO: 3, CRESCIMENTO_ACELERADO: 1, CRESCIMENTO_DESACELERADO: 0, DECLINIO: 1, DECLINIO_ACELERADO: 0,
    DECLINIO_DESACELERADO: 0, SEM_CLASSIFICACAO: 3},
  sem_classificacao_por_motivo: {MUDANCA_DE_DIRECAO: 2, SERIE_ESTAVEL: 1},
  nao_avaliaveis_por_motivo: {SERIE_INSUFICIENTE: 1, INCOMPARABILIDADE: 0},
  familias: {CRESCIMENTO: 4, DECLINIO: 1, NENHUMA: 3}, classes,
  rotulos_familia: {CRESCIMENTO: 'Família do crescimento', DECLINIO: 'Família do declínio', NENHUMA: 'Sem classificação'},
  rotulos_nao_avaliavel: {SERIE_INSUFICIENTE: 'Não avaliável: série insuficiente', INCOMPARABILIDADE: 'Não avaliável: série não comparável'},
  rotulos_motivo: {MUDANCA_DE_DIRECAO: 'Mudança de direção', SERIE_ESTAVEL: 'Série estável'},
  janela: {periodos: ['202301', '202306', '202401', '202406'], inicio: '202301', fim: '202406', intervalos: [5, 7],
    intervalo_constante: false, serie_anual: null, serie_anual_disponivel: false, competencias_serie_anual: []},
  unidades: [{territorio: 'Manaus', categoria: 'MEDICINA', velocidades: [0.4, 0.5, 0.6], ausentes: []},
    {territorio: 'Tefé', categoria: 'MEDICINA', velocidades: [2, 0, -1], ausentes: []},
    {territorio: 'Coari', categoria: 'MEDICINA', velocidades: [], ausentes: ['202306']}],
};

test('código e família pela metadata do motor, sem classificar no navegador', () => {
  assert.equal(trendMeta({tendencia: meta}), meta);
  assert.equal(trendMeta({}), null);
  assert.equal(classOfLabel('Aceleração do crescimento', meta), 'CRESCIMENTO_ACELERADO');
  assert.equal(classOfLabel('Sem classificação', meta), 'SEM_CLASSIFICACAO');
  assert.equal(classOfLabel('Não avaliável: série não comparável', meta), 'NAO_AVALIAVEL');
  assert.equal(classOfLabel('Estável', meta), null);   // rótulo antigo não é classe da SPEC
  assert.equal(classOfLabel(null, meta), null);
  assert.equal(familyOfClass('DECLINIO_DESACELERADO', meta), 'DECLINIO');
  assert.equal(familyOfClass('SEM_CLASSIFICACAO', meta), 'NENHUMA');
  assert.equal(familyOfClass('NAO_AVALIAVEL', meta), 'NAO_AVALIAVEL');
});

test('motivo da tendência na tabela: com a classe atribuída não se aplica, e a linha não vira "Não avaliável"', () => {
  assert.equal(trendMotiveText(null), 'Não se aplica');            // Crescimento, Aceleração… (motivo vazio no motor e no CSV)
  assert.equal(trendMotiveText(undefined), 'Não se aplica');
  assert.equal(trendMotiveText('Mudança de direção'), 'Mudança de direção');
  assert.equal(trendMotiveText('2 de 4 observações necessárias'), '2 de 4 observações necessárias');
});

test('contagens na ordem da SPEC, sem classificação por motivo e não avaliáveis à parte (AT-18)', () => {
  const groups = countGroups(meta);
  assert.deepEqual(groups.map(group => [group.family, group.total]),
    [['CRESCIMENTO', 4], ['DECLINIO', 1], ['NENHUMA', 3], ['NAO_AVALIAVEL', 1]]);
  assert.deepEqual(groups[0].entries.map(entry => [entry.code, entry.value]),
    [['CRESCIMENTO', 3], ['CRESCIMENTO_ACELERADO', 1], ['CRESCIMENTO_DESACELERADO', 0]]);
  assert.deepEqual(groups[2].entries.map(entry => [entry.label, entry.value]),
    [['Sem classificação (mudança de direção)', 2], ['Sem classificação (série estável)', 1]]);
  assert.deepEqual(groups[3].entries.map(entry => [entry.label, entry.value]),
    [['Não avaliável: série insuficiente', 1], ['Não avaliável: série não comparável', 0]]);
  assert.deepEqual(familyFilterOptions(meta).map(item => item.label),
    ['Família do crescimento (4)', 'Família do declínio (1)', 'Sem classificação (3)', 'Não avaliável (1)']);
  assert.equal(familyFilterOptions({...meta, familias: {...meta.familias, NENHUMA: 5512}})[2].label, 'Sem classificação (5.512)');
});

test('avisos da etapa: BLQ-MET com os textos do catálogo e RES-SCL', () => {
  assert.equal(stageNote(meta), null);
  const block = {desfecho: 'BLQ-MET', motivo: 'SERIE_INSUFICIENTE', periodos_distintos: 2,
    texto: 'Não foi possível analisar a tendência porque há apenas 2 observações válidas.',
    texto_minimo: 'A análise de tendência exige quatro observações válidas.'};
  assert.equal(stageNote({...meta, desfecho: 'BLQ-MET', bloqueio: block}),
    'Não foi possível analisar a tendência porque há apenas 2 observações válidas. A análise de tendência exige quatro ' +
    'observações válidas. A mudança entre o primeiro e o último período continua disponível.');
  assert.match(stageNote({...meta, desfecho: 'RES-SCL'}), /^Método executado: nenhum território recebeu classe/);
});

test('velocidades do motor com as competências de cada intervalo; ausência não vira intervalo', () => {
  assert.deepEqual(unitVelocities(meta, 'Manaus', 'MEDICINA').map(item => [item.from, item.to, item.value]),
    [['202301', '202306', 0.4], ['202306', '202401', 0.5], ['202401', '202406', 0.6]]);
  assert.deepEqual(unitVelocities(meta, 'Coari', 'MEDICINA'), []);
  assert.deepEqual(unitVelocities(meta, 'Inexistente'), []);
});

test('geometria das barras: a partir do zero, sinal preservado e zero como traço', () => {
  const positive = velocityBars([1, 2, 4], 100, 50);
  assert.equal(positive.baseline, 48);
  assert.deepEqual(positive.bars.map(bar => bar.sign), [1, 1, 1]);
  assert.equal(positive.bars[2].height, 46);                     // maior magnitude ocupa a altura útil
  assert.equal(positive.bars[0].height * 4, positive.bars[2].height);
  assert.ok(positive.bars.every(bar => bar.y + bar.height === positive.baseline));
  const mixed = velocityBars([2, 0, -1], 100, 50);
  assert.equal(mixed.baseline, 25);
  assert.deepEqual(mixed.bars.map(bar => bar.sign), [1, 0, -1]);
  assert.equal(mixed.bars[1].height, 2);                         // velocidade zero: traço na linha de base
  assert.equal(mixed.bars[2].y, 25);                             // negativa desce a partir do zero
  assert.deepEqual(velocityBars([], 100, 50).bars, []);
});
