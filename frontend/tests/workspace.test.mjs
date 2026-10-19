import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {normalizeCommand, navigationCommand} = await source('workspaceNavigation');
const {governedRoles} = await source('curatedPreparation');
test('comandos de navegação aceitam acentos, pontuação e espaços sem interpretar pedidos analíticos', () => {
  assert.equal(normalizeCommand('  Usar  dados do Brasil. '), 'usar dados do brasil');
  assert.equal(navigationCommand('Volte para a seleção de territórios.', 'results', true), 'territories');
  assert.equal(navigationCommand('Mostre os resultados!', 'preparation', true), 'results');
  assert.equal(navigationCommand('Mostre os resultados!', 'preparation', false), null);
  assert.equal(navigationCommand('Voltar à preparação.', 'results', true), 'preparation');
  assert.equal(navigationCommand('Compare Manaus e Tefé.', 'preparation', true), null);
  assert.equal(navigationCommand('Não volte para a seleção de territórios.', 'results', true), null);
});
test('perfil oficial vale campo a campo: mudar uma coluna tira só aquele papel e importações não têm perfil', () => {
  const defaults = {mapping: {count:'quantidade', period:'competencia', territory:'municipio', population:'populacao'}};
  assert.deepEqual(governedRoles(defaults, {...defaults.mapping}), ['count', 'period', 'territory', 'population']);
  // D1: antes, qualquer mudança desligava o perfil inteiro; agora só o papel alterado sai dele.
  assert.deepEqual(governedRoles(defaults, {...defaults.mapping, count:'outro_campo'}), ['period', 'territory', 'population']);
  assert.deepEqual(governedRoles(defaults, {...defaults.mapping, period:''}), ['count', 'territory', 'population']);
  assert.deepEqual(governedRoles(defaults, {...defaults.mapping, identity:'cpf'}), ['count', 'period', 'territory', 'population']);
  assert.deepEqual(governedRoles(null, defaults.mapping), []);
  assert.deepEqual(governedRoles(undefined, {}), []);
});
