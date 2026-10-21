import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {missingChoices, missingMessage} = await source('preparationReadiness');
const complete = {category: 'MEDICINA', periodReady: true, territoryPending: false, indicator: 'density', requiresIndicator: true};

test('base oficial: com as escolhas da análise feitas, nada falta', () => {
  assert.deepEqual(missingChoices(complete), []);
  assert.equal(missingMessage([]), '');
  // Análise sem escolha de indicador (o indicador é o próprio da análise).
  assert.deepEqual(missingChoices({...complete, indicator: '', requiresIndicator: false}), []);
});

test('cada escolha que falta é nomeada pelo título da caixa, na ordem das configurações', () => {
  assert.deepEqual(missingChoices({...complete, periodReady: false}), ['Período']);
  assert.deepEqual(missingChoices({...complete, category: ''}), ['Categoria']);
  assert.deepEqual(missingChoices({...complete, category: 'MEDICINA', categoryChoiceRequired: true}), ['Categoria']);
  assert.deepEqual(missingChoices({...complete, territoryPending: true}), ['Abrangência territorial']);
  assert.deepEqual(missingChoices({...complete, indicator: ''}), ['Indicador']);
  assert.deepEqual(missingChoices({category: '', periodReady: false, territoryPending: true, indicator: '', requiresIndicator: true}),
    ['Categoria', 'Período', 'Abrangência territorial', 'Indicador']);
});

test('parâmetros próprios da análise espacial também são nomeados; o referencial só fora da versão governada', () => {
  const spatial = {...complete, requiresIndicator: false, requiresReference: true, reference: ''};
  assert.deepEqual(missingChoices(spatial), ['Território de referência']);
  assert.deepEqual(missingChoices({...spatial, reference: 'code:130260'}), []);
  assert.deepEqual(missingChoices({...spatial, reference: 'code:130260', requiresCrs: true, crs: ''}), ['Referencial geodésico']);
  assert.deepEqual(missingChoices({...spatial, reference: 'code:130260', requiresCrs: false, crs: ''}), []);
});

test('a mensagem lista as escolhas em português, sem pedir nada sobre a base', () => {
  assert.equal(missingMessage(['Período']), 'Falta escolher: Período.');
  assert.equal(missingMessage(['Período', 'Indicador']), 'Falta escolher: Período e Indicador.');
  assert.equal(missingMessage(['Categoria', 'Período', 'Indicador']), 'Falta escolher: Categoria, Período e Indicador.');
  const all = missingMessage(missingChoices({category: '', periodReady: false, territoryPending: true, indicator: '',
    requiresIndicator: true, requiresReference: true, reference: '', requiresCrs: true, crs: ''}));
  assert.doesNotMatch(all, /IBGE|código|confirm|coluna|campo da base/i);
});
