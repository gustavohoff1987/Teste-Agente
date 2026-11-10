import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
// Detector de Sinais Territoriais (comando V22, etapa 3): o modelo puro da tela (detectorModel.ts) — a leitura da resposta de
// POST /api/detector, os textos curtos da tabela em linguagem simples (decisão D-C), os filtros, a ordem e as exportações — e a
// seleção no contrato das ferramentas (painelModel.selecaoDasFerramentas). Nada é calculado na tela.
const D = await source('detectorModel');
const M = await source('painelModel');

const linha = (extra = {}) => ({
  id: 'code:130260', tipo: 'municipio', nivel: 'municipios', rotulo: 'MANAUS (AM)', uf: 'AM',
  ultima: {competencia: '202406', valor: 12, na_data: true}, porte: 2, sinais: [], dimensoes: {estrutural: null, trajetoria: null, ritmo: null},
  estrutural: {estado: 'sem_sinal', classe: null, n: 12, impacto_pct: 8.333333333333334, zeros: null, mantida: false},
  perda: {estado: 'sem_perda', classe: null, delta: 0, pct: 0, de: '202401', ate: '202406', magnitude: null, motivo: null, verificar: null},
  patamar: {estado: 'sem_sinal', classe: null, patamar: 11.5, diferenca_pct: 4.3, abaixo: false, critica: null},
  declinio: {estado: 'sem_sinal', reducoes: 0, perda_pct: null, sinal: null},
  desaceleracao: {estado: 'sem_sinal', desacelera: false, persistente: null, rotulo: 'Crescimento'},
  instabilidade: {estado: 'descritivo', indice: 1.24}, registro: {estado: 'normal', tipos: []}, ...extra});
const resposta = (linhas, extra = {}) => ({
  versao: 'DETECTOR-SINAIS/V2.2/1',
  fonte: {base: 'Brasil', categoria: 'MEDICINA', versao: 'abc', primeira: '201401', ultima: '202406', competencias: 22, unidades: {municipio: 'médicos registrados'}},
  janela: {inicio: '201401', fim: '202406', registros: 22, meses: 125, padrao: true, ultimo_registro_da_base: '202406', e_o_ultimo: true},
  competencias: ['201401', '201406', '202406'],
  parametros: {padrao: {perda: {alta_alfa: 1, alta_minimo: 2}}, em_uso: {perda: {alta_alfa: 1, alta_minimo: 2}}, personalizados: false,
    editaveis: {perda: {alta_alfa: {minimo: 0.01, maximo: 20, inteiro: false}}}},
  exploratorio: false, linhas,
  resumo: {territorios: linhas.length, por_tipo: {municipio: linhas.length}, estrutural: {critica: 1}, trajetoria: {}, sinais: {perda: 2}, sem_registro_na_data: 0},
  calibracao: {competencia: '202406', intervalo_meses: 5, perda: [{porte: '1 a 3', transicoes: 6572, queda_incomum_pct: 66.7, queda_muito_incomum_pct: null,
    alta: 'calibrado', critica: 'calibrado'}], patamar: [{porte: '20 a 49', observacoes: 13942, afastamento_incomum_pct: 39.5, alta: 'calibrado', critica: 'nao_calibravel'}],
    monitoramento: {avaliadas: 5570, incomuns: 27, taxa_pct: 0.48}},
  notas: ['Base: só médicos.'], limitacoes: ['LIMITES_PROVISORIOS'], ...extra});

test('a resposta do motor vira os tipos da tela, sem calcular nada', () => {
  const lida = D.normalizarDetector(resposta([linha(), {id: null}, linha({id: 'uf:15', tipo: 'estado', rotulo: 'Pará (PA)', porte: 6})]));
  assert.equal(lida.linhas.length, 2, 'a linha sem id fica de fora');
  assert.deepEqual(lida.linhas[0].ultima, {competencia: '202406', valor: 12, naData: true});
  assert.equal(lida.linhas[0].estrutural.impactoPct, 8.333333333333334);
  assert.deepEqual(lida.janela, {inicio: '201401', fim: '202406', registros: 22, meses: 125, padrao: true, ultimoRegistroDaBase: '202406', eOUltimo: true});
  assert.deepEqual(lida.parametros.editaveis.perda.alta_alfa, {minimo: 0.01, maximo: 20, inteiro: false});
  assert.equal(lida.calibracao.perda[0].quedaMuitoIncomumPct, null);
  assert.equal(lida.calibracao.monitoramento.taxaPct, 0.48);
  assert.equal(lida.resumo.sinais.perda, 2);
  // Uma resposta vazia ou estranha não derruba a tela.
  const vazia = D.normalizarDetector(null);
  assert.deepEqual([vazia.linhas, vazia.competencias, vazia.exploratorio], [[], [], false]);
  const detalhe = D.normalizarDetalhe({territorio: {id: 'c1', rotulo: 'Par', tipo: 'conjunto', unidade: 'soma', nomes_dos_membros: ['A', 'B']},
    janela: resposta([]).janela, janela_do_territorio: {inicio: '201801', depois_da_quebra: true},
    serie: [{competencia: '201401', valor: null, estado: 'ausencia_de_dado'}, {competencia: '201406', valor: 0, estado: 'zero_confirmado', marca: 'quebra_de_fonte'}],
    historico: [{competencia: '201406', valor: 3, estrutural: 'alta', perda: {delta: -2, pct: -40, estado: 'nao_calibrado', classe: null},
      patamar: {estado: 'descritivo', classe: null, diferenca_pct: -25}, declinio: {reducoes: 2, sinal: 'forte'}, desaceleracao: null}],
    fenomenos: [{chave: 'perda', numero: '6', nome: 'Perda abrupta de médicos', dimensao: 'Trajetória', estado: 'alerta', classe: 'alta', situacao: 's',
      observado: 'o', criterio: 'c', habitual: 'h', significa: 'sig', nao_significa: 'ns', limitacoes: 'l', qualidade: 'q'}], notas: ['n'], exploratorio: true});
  assert.deepEqual([detalhe.id, detalhe.membros, detalhe.inicioDoTerritorio, detalhe.depoisDaQuebra, detalhe.exploratorio],
    ['c1', ['A', 'B'], '201801', true, true]);
  assert.deepEqual(detalhe.serie[0], {competencia: '201401', valor: null, estado: 'ausencia_de_dado', marca: null, membrosSemRegistro: null});
  assert.equal(detalhe.serie[1].valor, 0, 'zero é valor, não ausência');
  assert.deepEqual(detalhe.historico[0].perda, {delta: -2, pct: -40, estado: 'nao_calibrado', classe: null});
  assert.equal(detalhe.fenomenos[0].naoSignifica, 'ns');
});

test('os textos da tabela usam linguagem simples: sem classificação com o motivo, nunca "não calibrado" nem "candidato"', () => {
  const ler = extra => D.normalizarDetector(resposta([linha(extra)])).linhas[0];
  // Condição estrutural.
  assert.deepEqual(D.trechoEstrutural(ler({})), {chave: 'estrutural', texto: '12 médicos', classe: null, apoio: 'sem sinal por esta escala'});
  assert.deepEqual(D.trechoEstrutural(ler({estrutural: {estado: 'classificado', classe: 'alta', n: 3, impacto_pct: 100 / 3, zeros: null, mantida: false}})),
    {chave: 'estrutural', texto: '3 médicos · a saída de 1 tira 33,3%', classe: 'alta', apoio: null});
  assert.equal(D.trechoEstrutural(ler({estrutural: {estado: 'classificado', classe: 'critica', n: 0, impacto_pct: null, zeros: 3, mantida: false}})).texto,
    'Nenhum médico registrado há 3 registros');
  assert.equal(D.trechoEstrutural(ler({estrutural: {estado: 'classificado', classe: 'alta', n: 6, impacto_pct: 16.7, zeros: null, mantida: true}})).apoio,
    'mantida pelo registro anterior');
  assert.equal(D.trechoEstrutural(ler({estrutural: {estado: 'ausencia_de_dado', classe: null, n: null}})).apoio, 'ausência de dado, não é zero');
  assert.equal(D.trechoEstrutural(ler({estrutural: {estado: 'nivel_sem_classificacao', classe: null, n: 253, impacto_pct: 0.4}})).apoio, 'sem classificação neste nível');
  // Trajetória: a perda sempre aparece; o alerta só com a intensidade do motor; sem classificação, o motivo em palavras.
  const perda = extra => D.trechosDaTrajetoria(ler({perda: {estado: 'perda_observada', classe: null, delta: -5, pct: -41.666, de: '202401', ate: '202406',
    magnitude: 'critica', motivo: null, verificar: null, ...extra}}))[0];
  assert.deepEqual(perda({estado: 'alerta', classe: 'critica'}), {chave: 'perda', texto: '−5 (−41,7%) no último registro', classe: 'critica',
    apoio: 'alerta: queda grande e incomum para o porte'});
  assert.equal(perda({motivo: 'comum_para_o_porte'}).apoio, 'queda comum para o porte, sem alerta');
  assert.equal(perda({motivo: 'magnitude_abaixo'}).apoio, 'queda pequena para o porte, sem alerta');
  assert.equal(perda({estado: 'nao_calibrado', motivo: 'poucas_transicoes'}).apoio,
    'sem classificação: poucos municípios parecidos na base para dizer se esta queda é incomum');
  assert.equal(perda({estado: 'descontinuidade_de_registro'}).apoio, 'volta de um pico de registro, sem alerta');
  assert.equal(perda({estado: 'alerta', classe: 'alta', verificar: 'queda'}).apoio, 'alerta: queda grande e incomum para o porte · verificar registro');
  assert.deepEqual(D.trechosDaTrajetoria(ler({})), [], 'sem perda, sem afastamento e sem declínio, nada a dizer');
  const completa = D.trechosDaTrajetoria(ler({patamar: {estado: 'classificado', classe: 'alta', patamar: 59.2, diferenca_pct: -47.7, abaixo: true, critica: 'nao_calibravel'},
    declinio: {estado: 'sinal_observado', reducoes: 3, perda_pct: 21, sinal: 'muito_forte'}}));
  assert.deepEqual(completa, [
    {chave: 'patamar', texto: '47,7% abaixo do patamar anterior', classe: 'alta', apoio: 'crítica: sem base para avaliar'},
    {chave: 'declinio', texto: 'Queda em 3 junhos seguidos (−21,0%)', classe: null, apoio: 'sinal observado muito forte'}]);
  assert.equal(D.trechosDaTrajetoria(ler({patamar: {estado: 'descritivo', classe: null, patamar: 4, diferenca_pct: -25, abaixo: true, critica: null}}))[0].apoio,
    'descritivo: patamar com poucos médicos');
  // Ritmo e instabilidade: descritivos, sem intensidade.
  assert.deepEqual(D.trechosDoRitmo(ler({desaceleracao: {estado: 'sinal_observado', desacelera: true, persistente: true, rotulo: 'Desaceleração do crescimento'}})), [
    {chave: 'desaceleracao', texto: 'Desaceleração do crescimento', classe: null, apoio: 'repetida (leitura exploratória)'},
    {chave: 'instabilidade', texto: 'Oscilação 1,2× a típica do porte', classe: null, apoio: null}]);
  // Qualidade do registro e última observação.
  assert.deepEqual(D.textoDoRegistro(ler({registro: {estado: 'descontinuidade_de_registro', tipos: ['pico_que_volta']}})),
    {texto: 'Descontinuidade de registro (pico que volta)', marca: 'descontinuidade'});
  assert.deepEqual(D.textoDoRegistro(ler({registro: {estado: 'verificar_registro', tipos: ['queda_grande', 'salto']}})),
    {texto: 'Verificar registro (queda grande, salto)', marca: 'verificar'});
  assert.equal(D.textoDoRegistro(ler({})).texto, 'Normal');
  assert.equal(D.textoDaUltima(ler({}), '202406'), 'jun/2024 · 12 médicos');
  assert.equal(D.textoDaUltima(ler({ultima: {competencia: '202401', valor: 1, na_data: false}}), '202406'), 'jan/2024 · 1 médico (sem registro em jun/2024)');
  assert.equal(D.tipoDoTerritorio(ler({tipo: 'conjunto', membros: 3})), 'conjunto · soma de 3 territórios');
  assert.equal(D.tipoDoTerritorio(ler({tipo: 'estado'})), 'estado como unidade · fonte estadual');
  // Nenhum termo técnico na tabela (decisão D-C).
  const codigo = readFileSync(new URL('../src/detectorModel.ts', import.meta.url), 'utf8') + readFileSync(new URL('../src/DetectorDeSinais.tsx', import.meta.url), 'utf8');
  for (const termo of ['não calibrado', 'Não calibrado', 'limiar candidato', 'limite candidato', 'criticidade'])
    assert.ok(!codigo.replace(/\/\/.*$/gm, '').includes(termo), termo);
  assert.match(D.TEXTO_LIMITES_PROVISORIOS, /limites provisórios/);
});

test('filtros por fenômeno, porte e nome; a ordem por intensidade não é um índice geral', () => {
  const linhas = D.normalizarDetector(resposta([
    linha({id: 'a', rotulo: 'ÁGUA BRANCA (AL)', sinais: ['estrutural', 'perda'], porte: 0, ultima: {competencia: '202406', valor: 2, na_data: true},
      dimensoes: {estrutural: 'alta', trajetoria: null, ritmo: null}}),
    linha({id: 'b', rotulo: 'Belém (PA)', sinais: ['patamar'], porte: 6, ultima: {competencia: '202406', valor: 900, na_data: true},
      dimensoes: {estrutural: null, trajetoria: 'atencao', ritmo: null}}),
    linha({id: 'c', rotulo: 'Cacoal (RO)', sinais: ['estrutural', 'ausencia'], porte: null, ultima: {competencia: '202406', valor: 0, na_data: true},
      dimensoes: {estrutural: 'critica', trajetoria: null, ritmo: null}}),
    linha({id: 'd', rotulo: 'Dourados (MS)', sinais: [], porte: 2})])).linhas;
  const ids = lista => lista.map(item => item.id);
  assert.deepEqual(ids(D.filtrarLinhas(linhas, D.SEM_FILTROS)), ['a', 'b', 'c', 'd']);
  assert.deepEqual(ids(D.filtrarLinhas(linhas, {...D.SEM_FILTROS, fenomeno: 'estrutural'})), ['a', 'c']);
  assert.deepEqual(ids(D.filtrarLinhas(linhas, {...D.SEM_FILTROS, porte: 'zero'})), ['c']);
  assert.deepEqual(ids(D.filtrarLinhas(linhas, {...D.SEM_FILTROS, porte: '0'})), ['a']);
  assert.deepEqual(ids(D.filtrarLinhas(linhas, {...D.SEM_FILTROS, busca: 'agua'})), ['a'], 'a busca ignora acentos e caixa');
  assert.deepEqual(ids(D.filtrarLinhas(linhas, {fenomeno: 'estrutural', porte: 'zero', busca: 'cac'})), ['c']);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'intensidade')), ['c', 'a', 'b', 'd']);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'nome')), ['a', 'b', 'c', 'd']);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'medicos')), ['c', 'a', 'd', 'b']);
  assert.deepEqual(ids(linhas), ['a', 'b', 'c', 'd'], 'ordenar não muda a lista recebida');
  assert.ok(D.FILTROS_DE_FENOMENO.every(item => item.chave === 'todos' ||
    ['estrutural', 'ausencia', 'perda', 'alerta_perda', 'patamar', 'declinio', 'desaceleracao', 'registro'].includes(item.chave)));
});

test('parâmetros personalizados: só o que difere do padrão vai no pedido', () => {
  const padrao = {perda: {alta_alfa: 1, alta_minimo: 2}, patamar: {atencao: 15}};
  assert.equal(D.parametrosPersonalizados(padrao, {perda: {alta_alfa: 1, alta_minimo: 2}, patamar: {atencao: 15}}), null);
  assert.deepEqual(D.parametrosPersonalizados(padrao, {perda: {alta_alfa: 5, alta_minimo: 2}, patamar: {atencao: 15}}), {perda: {alta_alfa: 5}});
  assert.deepEqual(D.parametrosPersonalizados(padrao, {patamar: {atencao: 20, outro: 3}}), {patamar: {atencao: 20}}, 'campo desconhecido não vai');
});

test('exportações: o CSV da tabela e o método em JSON levam a janela, as versões e a configuração', () => {
  const lida = D.normalizarDetector(resposta([linha({rotulo: 'A; "B"', perda: {estado: 'alerta', classe: 'alta', delta: -5, pct: -41.5, de: '202401', ate: '202406',
    magnitude: 'alta', motivo: null, verificar: null}, registro: {estado: 'verificar_registro', tipos: ['queda_grande']}})], {exploratorio: true}));
  const csv = D.csvDoDetector(lida, lida.linhas);
  assert.ok(csv.startsWith('﻿Identificador;Território;Tipo;UF;Janela: início;Janela: fim;'));
  const [cabecalho, dados] = csv.slice(1).trim().split('\r\n');
  const colunas = cabecalho.split(';');
  assert.equal(new Set(colunas).size, colunas.length, 'nenhum cabeçalho repetido');
  assert.ok(dados.startsWith('code:130260;"A; ""B""";município;AM;201401;202406;202406;12;10 a 19;'));
  assert.ok(dados.includes(';-5;-41,5;alerta;Alta;'), dados);
  assert.ok(dados.endsWith(';personalizada (exploratória);DETECTOR-SINAIS/V2.2/1;abc'));
  const metodo = JSON.parse(D.metodoDoDetector(lida));
  assert.equal(metodo.ferramenta, 'Detector de Sinais Territoriais');
  assert.deepEqual([metodo.versao_do_metodo, metodo.janela.fim, metodo.parametros.personalizados, metodo.fonte.categoria],
    ['DETECTOR-SINAIS/V2.2/1', '202406', false, 'MEDICINA']);
  assert.equal(metodo.comparacao_na_data.perda[0].transicoes, 6572);
});

test('a seleção em uso vai às ferramentas no contrato do painel: municípios, estados como unidade e conjuntos', () => {
  const base = (estados, ids = [], todos = false) => ({todos, estados, ids});
  const conjunto = {id: 'c1', rotulo: 'Carajás', membros: ['code:150553', 'code:150420'], substitui: true, retirados: ['code:150553'], versao: 2};
  const deEstados = {id: 'c2', rotulo: 'Norte-Nordeste', membros: ['uf:21', 'uf:29']};
  assert.deepEqual(M.selecaoDasFerramentas({nivel: 'municipios', base: base(['13'], ['code:150140']), estados: ['29', '15', '15'], conjuntos: [conjunto, deEstados]}), {
    base: {municipios: {todos: false, estados: ['13'], ids: ['code:150140']}}, estados_unidade: ['15', '29'],
    conjuntos: [{id: 'c1', rotulo: 'Carajás', membros: ['code:150553', 'code:150420'], versao: 2}, {id: 'c2', rotulo: 'Norte-Nordeste', membros: ['uf:21', 'uf:29']}]});
  // Sem municípios marcados, nenhum `base`; no nível dos estados, só os estados como unidade e os conjuntos de estados.
  assert.deepEqual(M.selecaoDasFerramentas({nivel: 'municipios', base: base([]), estados: [], conjuntos: [conjunto]}),
    {conjuntos: [{id: 'c1', rotulo: 'Carajás', membros: ['code:150553', 'code:150420'], versao: 2}]});
  assert.deepEqual(M.selecaoDasFerramentas({nivel: 'estados', base: base(['13']), estados: ['35', '13'], conjuntos: [conjunto, deEstados]}),
    {estados_unidade: ['13', '35'], conjuntos: [{id: 'c2', rotulo: 'Norte-Nordeste', membros: ['uf:21', 'uf:29']}]});
});
