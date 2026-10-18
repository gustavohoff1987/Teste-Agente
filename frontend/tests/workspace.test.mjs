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
const {matchesCuratedPreparation} = await source('curatedPreparation');
test('comandos de navegação aceitam acentos, pontuação e espaços sem interpretar pedidos analíticos', () => {
  assert.equal(normalizeCommand('  Usar  dados do Brasil. '), 'usar dados do brasil');
  assert.equal(navigationCommand('Volte para a seleção de territórios.', 'results', true), 'territories');
  assert.equal(navigationCommand('Mostre os resultados!', 'preparation', true), 'results');
  assert.equal(navigationCommand('Mostre os resultados!', 'preparation', false), null);
  assert.equal(navigationCommand('Voltar à preparação.', 'results', true), 'preparation');
  assert.equal(navigationCommand('Compare Manaus e Tefé.', 'preparation', true), null);
  assert.equal(navigationCommand('Não volte para a seleção de territórios.', 'results', true), null);
});
test('reconhecimento oficial não sobrevive a mudanças dos significados nem se aplica a importações', () => {
  const defaults = {mapping: {count:'quantidade', period:'competencia', territory:'municipio', population:'populacao'},
    category:'MEDICINA', count_unit:'pessoas', fts_scope_confirmed:true, object_confirmed:true, population_denominator_confirmed:true};
  const valid = {official:true, mapping:{...defaults.mapping}, category:'MEDICINA', countUnit:'pessoas', fts:true, object:true, population:true};
  assert.equal(matchesCuratedPreparation(defaults, valid), true);
  for (const patch of [{official:false}, {category:'OUTRA'}, {countUnit:'vinculos'}, {population:false}, {fts:false}, {object:false},
    {mapping:{...valid.mapping, count:'outro_campo'}}, {mapping:{...valid.mapping, identity:'cpf'}}, {mapping:{...valid.mapping, period:''}}])
    assert.equal(matchesCuratedPreparation(defaults, {...valid, ...patch}), false);
  assert.equal(matchesCuratedPreparation(null, valid), false);
});
