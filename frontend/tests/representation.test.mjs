import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {levelOf, niceDomain, referenceFor, tableColumns} = await source('representation');

test('escala vertical em números redondos ao redor dos valores observados', () => {
  assert.deepEqual(niceDomain([1.700594, 1.683583, 1.95, 1.6]), [1.6, 2]);
  assert.deepEqual(niceDomain([0, 10]), [0, 10]);
  assert.deepEqual(niceDomain([5, 5]), [4.5, 5.5]);
  assert.deepEqual(niceDomain([-2, 3]), [-2, 4]);
  assert.deepEqual(niceDomain([0.2, 9.8]), [0, 10]);  // valores positivos nunca ganham eixo negativo
  assert.deepEqual(niceDomain([]), [0, 1]);
});

test('competências aparecem como mês/ano na tabela, sem alterar as demais colunas', () => {
  const [territory, period, initial] = tableColumns(['Território', 'Período', 'Período inicial']);
  assert.equal(territory.display, undefined);
  assert.equal(period.display('202406'), '06/2024');
  assert.equal(initial.display('201401'), '01/2014');
  assert.equal(period.display('Período declarado'), 'Período declarado');
});

test('taxa nacional de contexto (D5): só na densidade, com um valor único da competência e da categoria', () => {
  const rep = {referencias: [{rotulo: 'Brasil (total nacional)', papel: 'REFERENCIA_DE_CONTEXTO', unidade: 'por 1.000 habitantes',
    nota: '', valores: [
      {competencia: '202406', categoria: 'MEDICINA', valor: 2.363750757054573, avaliabilidade: 'AVALIAVEL', competencia_populacao: '202406'},
      {competencia: '202401', categoria: 'MEDICINA', valor: 2.3026924682625083, avaliabilidade: 'AVALIAVEL', competencia_populacao: '202406'},
      {competencia: '201501', categoria: 'MEDICINA', valor: null, avaliabilidade: 'NAO_AVALIAVEL', competencia_populacao: null}]}]};
  const june = referenceFor(rep, ['202406'], ['MEDICINA'], 'Densidade por 1.000');
  assert.equal(june.valor, 2.363750757054573);
  assert.equal(june.texto, 'Brasil (total nacional): 2,36 por 1.000 habitantes · referência de contexto; a cor dos municípios ' +
    'não é classificada em relação a ela.');
  assert.equal(june.nota, '');
  assert.equal(referenceFor(rep, ['202401'], ['MEDICINA'], 'Densidade por 1.000').nota, 'Em janeiro, a população do Brasil é a de junho de 2024.');
  assert.equal(referenceFor(rep, ['202406'], ['MEDICINA'], 'Quantidade'), null);          // só na densidade
  assert.equal(referenceFor(rep, ['202401', '202406'], ['MEDICINA'], 'Densidade por 1.000'), null);  // sem valor único
  assert.equal(referenceFor(rep, ['201501'], ['MEDICINA'], 'Densidade por 1.000'), null);  // não avaliável: sem marca
  assert.equal(referenceFor({}, ['202406'], ['MEDICINA'], 'Densidade por 1.000'), null);
});

test('nível dos itens do resultado: o declarado pelo backend ou, sem ele, município', () => {
  const level = levelOf({metadata: {universe: {members: [{id: 'br', label: 'Brasil (total nacional)', nivel: 'BR'},
    {id: 'uf:13', label: 'Amazonas (AM)', nivel: 'UF'}, {id: 'code:130260', label: 'MANAUS [130260]', nivel: 'MUN'}]}}});
  assert.deepEqual(['br', 'uf:13', 'code:130260', 'code:999999', 'x'].map(level), ['BR', 'UF', 'MUN', 'MUN', '']);
});
