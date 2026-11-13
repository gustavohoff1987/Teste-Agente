import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
// Detector de Sinais Territoriais (comando V22, etapas 3 e 5): o modelo puro da tela (detectorModel.ts) — a leitura da resposta de
// POST /api/detector, os textos curtos da tabela em linguagem simples (decisão D-C), os filtros, a ordem e as exportações — e a
// seleção no contrato das ferramentas (painelModel.selecaoDasFerramentas). Da etapa 5: os fenômenos 8 a 12 (os campos da linha, os
// textos curtos, os itens das bolhas, as camadas do mapa, a série da taxa) e o que o Detector leva ao Simulador. Nada é calculado
// na tela.
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
  // O nome anterior de um município continua achando-o (base Brasil, 13/11/2026): "Parati" acha PARATY, e a tela mostra o atual.
  const renomeadas = D.normalizarDetector(resposta([linha({id: 'code:330380', rotulo: 'PARATY (RJ)', nomes_anteriores: ['PARATI']}),
    linha({id: 'code:130260', rotulo: 'MANAUS (AM)'})])).linhas;
  assert.deepEqual([renomeadas[0].nomesAnteriores, 'nomesAnteriores' in renomeadas[1]], [['PARATI'], false]);
  assert.deepEqual(['parati', 'Paraty', 'manaus', 'ouro'].map(busca => ids(D.filtrarLinhas(renomeadas, {...D.SEM_FILTROS, busca}))),
    [['code:330380'], ['code:330380'], ['code:130260'], []]);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'intensidade')), ['c', 'a', 'b', 'd']);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'nome')), ['a', 'b', 'c', 'd']);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'medicos')), ['c', 'a', 'd', 'b']);
  assert.deepEqual(ids(linhas), ['a', 'b', 'c', 'd'], 'ordenar não muda a lista recebida');
  // Os filtros são os sinais do motor: os do núcleo (etapa 3) e os dos fenômenos 8 a 12 (etapa 5), na mesma ordem do resumo.
  assert.deepEqual(D.FILTROS_DE_FENOMENO.map(item => item.chave), ['todos', 'estrutural', 'ausencia', 'perda', 'alerta_perda', 'patamar', 'declinio',
    'desaceleracao', 'registro', 'disponibilidade', 'posicao', 'defasagem', 'combinados']);
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

// ------------------------------------------------------------------------------------------------ fenômenos 8 a 12 (etapa 5 do comando V22)
const SINAIS_RELATIVOS = {disponibilidade: {estado: 'sinal_observado', taxa: 3.0727, populacao: 36125, variacao_pct: -36.205, sinal: 'muito_forte'},
  posicao: {estado: 'sinal_observado', percentil: 86.29, universo: 5570, variacao_pp: -11.526, sinal: 'queda'},
  defasagem: {estado: 'sinal_observado', indice: 72.887, variacao_pontos: -55.21, sinal: 'forte'}};
const nivelDaData = estado => ({disponibilidade: {estado, taxa: 2.34, populacao: 2063689, variacao_pct: null, sinal: null},
  posicao: {estado, percentil: 71.4, universo: 5570, variacao_pp: null, sinal: null}, defasagem: {estado, indice: 260.9, variacao_pontos: null, sinal: null}});
const SEM_CONTEXTO = {distancia_km: null, referencia: null, referencia_id: null, percentil: null};
const comparada = () => D.normalizarDetector(resposta([
  linha({id: 'code:350530', rotulo: 'BARRA BONITA (SP)', uf: 'SP', sinais: ['perda', 'disponibilidade', 'posicao', 'defasagem'], ...SINAIS_RELATIVOS,
    contexto: {estado: 'atende_ao_criterio', ...SEM_CONTEXTO}, coexistencia: {estado: 'sem_combinacao', combinacoes: [], textos: [], repercussoes: 4}}),
  linha({sinais: ['patamar', 'combinados'], ...nivelDaData('sem_sinal'),
    disponibilidade: {estado: 'sem_sinal', taxa: 1.8135, populacao: 2255903, variacao_pct: 12.45, sinal: null},
    contexto: {estado: 'contexto', distancia_km: 423.514, referencia: 'JACAREACANGA (PA)', referencia_id: 'code:150375', percentil: 98.27},
    coexistencia: {estado: 'sinais_combinados', combinacoes: ['patamar_e_estrutural'], textos: ['Abaixo do patamar anterior e poucos médicos'], repercussoes: 2}}),
  linha({id: 'uf:15', tipo: 'estado', nivel: 'estados', rotulo: 'Pará (PA)', uf: 'PA', ...nivelDaData('comparacao_nao_habilitada'),
    contexto: {estado: 'nao_aplicavel', ...SEM_CONTEXTO}}),
  linha({id: 'c1', tipo: 'conjunto', rotulo: 'Par', uf: null, membros: 2, ids_dos_membros: ['code:110001', 'code:999999'], sinais: ['combinados'],
    disponibilidade: {estado: 'descritivo', taxa: 0.5, populacao: 20000, variacao_pct: -50, sinal: null},
    posicao: {estado: 'nao_aplicavel', percentil: null, universo: null, variacao_pp: null, sinal: null},
    defasagem: {estado: 'descritivo', indice: 40.04, variacao_pontos: -3.26, sinal: null},
    contexto: {estado: 'contexto', distancia_km: 88.04, referencia: 'PORTO VELHO (RO)', referencia_id: 'code:110020', percentil: null}}),
  linha({id: 'code:110001', rotulo: 'ALTA FLORESTA (RO)', uf: 'RO'})], {
  versao: 'DETECTOR-SINAIS/V2.2/2', janela: {inicio: '201401', fim: '202106', registros: 16, meses: 89, padrao: false, ultimo_registro_da_base: '202406', e_o_ultimo: false},
  comparacao: {de: '201906', ate: '202106', estado: 'comparavel', trechos: [[2014, 2017], [2018, 2021]], minimo_de_medicos: 20,
    contexto: {taxa_minima: 1.9834, taxa_do_brasil: 1.9834, pct_da_taxa_do_brasil: 100, atendem: 1720, universo: 3846}},
  coordenadas: {'code:130260': [-3.1, -60.0], 'code:150375': [-6.2, -57.7], 'code:350530': [-22.5, -48.6], 'code:110001': [-11.9, -62.0], x: [1]}}));

test('fenômenos 8 a 12: a linha, a janela de comparação e as coordenadas vêm do motor', () => {
  const lida = comparada();
  const [barra, manaus, , par, semDados] = lida.linhas;
  assert.deepEqual([barra.disponibilidade, barra.posicao, barra.defasagem], [
    {estado: 'sinal_observado', taxa: 3.0727, populacao: 36125, variacaoPct: -36.205, sinal: 'muito_forte'},
    {estado: 'sinal_observado', percentil: 86.29, universo: 5570, variacaoPp: -11.526, sinal: 'queda'},
    {estado: 'sinal_observado', indice: 72.887, variacaoPontos: -55.21, sinal: 'forte'}]);
  assert.deepEqual(manaus.contexto, {estado: 'contexto', distanciaKm: 423.514, referencia: 'JACAREACANGA (PA)', referenciaId: 'code:150375', percentil: 98.27});
  assert.deepEqual(manaus.coexistencia, {estado: 'sinais_combinados', combinacoes: ['patamar_e_estrutural'],
    textos: ['Abaixo do patamar anterior e poucos médicos'], repercussoes: 2});
  assert.deepEqual(par.idsDosMembros, ['code:110001', 'code:999999']);
  // Uma linha sem os campos novos (uma resposta antiga) não derruba a tela nem inventa valor.
  assert.deepEqual([semDados.disponibilidade.taxa, semDados.posicao.percentil, semDados.defasagem.indice, semDados.contexto.distanciaKm,
    semDados.coexistencia.textos, semDados.idsDosMembros], [null, null, null, null, [], []]);
  assert.deepEqual(lida.comparacao, {de: '201906', ate: '202106', estado: 'comparavel', minimoDeMedicos: 20, trechos: [[2014, 2017], [2018, 2021]], motivo: null,
    contexto: {taxaMinima: 1.9834, taxaDoBrasil: 1.9834, pctDaTaxaDoBrasil: 100, atendem: 1720, universo: 3846}});
  assert.deepEqual(Object.keys(lida.coordenadas), ['code:130260', 'code:150375', 'code:350530', 'code:110001'], 'o par incompleto fica de fora');
  const vazia = D.normalizarDetector(null);
  assert.deepEqual([vazia.comparacao.estado, vazia.comparacao.contexto.taxaMinima, vazia.coordenadas], ['', null, {}]);
  // Os trechos de população comparável e o motivo vêm do motor, lidos da própria base (comando V23, Parte D).
  assert.deepEqual([vazia.comparacao.trechos, vazia.comparacao.motivo], [[], null]);
  assert.deepEqual(D.normalizarDetector(resposta([], {comparacao: {estado: 'comparacao_nao_habilitada', trechos: [[2014, 2023], [2024], 'x'],
    motivo: 'a população de 2024 muda de patamar em boa parte da base'}})).comparacao.trechos, [[2014, 2023]], 'só os pares de anos');
  assert.deepEqual([[[2014, 2024]], [[2014, 2017], [2018, 2021]], [[2014, 2015], [2017, 2019], [2021, 2024]], []].map(D.textoDosTrechos),
    ['de 2014 a 2024', 'de 2014 a 2017 e de 2018 a 2021', 'de 2014 a 2015, de 2017 a 2019 e de 2021 a 2024', 'em nenhum trecho desta base']);
});

test('fenômenos 8 a 12 na tabela: sinais observados com limites provisórios, sem intensidade', () => {
  const [barra, manaus, para, par, semDados] = comparada().linhas;
  // A taxa por habitante, a posição e o índice ante a referência, com a variação em 2 anos e o nome curto do sinal.
  assert.deepEqual(D.trechosDaComparacao(barra), [
    {chave: 'disponibilidade', classe: null, apoio: 'sinal muito forte', texto: '3,07 por 1.000 hab. (−36,2% em 2 anos)'},
    {chave: 'posicao', classe: null, apoio: 'queda de posição', texto: 'Percentil 86 (−11,5 pontos)'},
    {chave: 'defasagem', classe: null, apoio: 'sinal forte', texto: 'Índice 72,9 ante a referência (−55,2 pontos)'}]);
  assert.ok(D.trechosDaComparacao(barra).every(trecho => trecho.classe === null), 'nenhuma intensidade nestes indicadores (decisão D-A)');
  assert.match(D.TEXTO_SINAIS_RELATIVOS, /sinais observados em 2 anos, com limites provisórios e sem intensidade/);
  assert.deepEqual(D.trechosDaComparacao(manaus).map(trecho => [trecho.texto, trecho.apoio]),
    [['1,81 por 1.000 hab. (+12,5% em 2 anos)', null], ['Percentil 71', null], ['Índice 260,9 ante a referência', null]]);
  // Comparação não habilitada (a janela cruza a troca de base da população): o nível da data fica à vista, e o motivo aparece uma vez.
  assert.deepEqual(D.trechosDaComparacao(para).map(trecho => [trecho.texto, trecho.apoio]),
    [['2,34 por 1.000 hab.', null], ['Percentil 71', null], ['Índice 260,9 ante a referência', 'variação em 2 anos: comparação não habilitada']]);
  const ler = extra => D.normalizarDetector(resposta([linha(extra)])).linhas[0];
  assert.equal(D.trechosDaComparacao(ler(nivelDaData('janela_insuficiente'))).at(-1).apoio, 'variação em 2 anos: janela insuficiente');
  assert.equal(D.trechosDaComparacao(ler(nivelDaData('descritivo'))).at(-1).apoio, 'descritivo: menos de 20 médicos no início da janela');
  assert.deepEqual(D.trechosDaComparacao(ler(nivelDaData('nao_calculavel'))).map(trecho => trecho.apoio), Array(3).fill('variação não calculável'));
  assert.equal(D.trechosDaComparacao(ler({disponibilidade: {estado: 'sem_sinal', taxa: 2, populacao: 1000, variacao_pct: 0.04, sinal: null}}))[0].texto,
    '2,00 por 1.000 hab. (0,0% em 2 anos)', 'o que arredonda para zero sai sem sinal');
  // O conjunto não entra em universos de percentis: só a taxa (soma ÷ soma) e o índice.
  assert.deepEqual(D.trechosDaComparacao(par).map(trecho => trecho.chave), ['disponibilidade', 'defasagem']);
  assert.deepEqual(D.trechosDaComparacao(semDados), []);
  // Contexto geográfico: só contexto, sem intensidade.
  assert.deepEqual(D.trechoDoContexto(manaus), {chave: 'contexto', classe: null, texto: 'A 423,5 km de JACAREACANGA (PA)',
    apoio: 'mais longe que 98% dos municípios que não atendem ao critério'});
  assert.deepEqual(D.trechoDoContexto(par), {chave: 'contexto', classe: null, texto: 'A 88,0 km de PORTO VELHO (RO)', apoio: 'pelo componente mais próximo'});
  // Com a taxa do critério, a célula e o cabeçalho dizem o critério por extenso (revisão da etapa 5, 13/11/2026).
  assert.equal(D.trechoDoContexto(manaus, 2.3638).apoio, 'mais longe que 98% dos municípios abaixo de 2,36 médicos por 1.000 habitantes');
  assert.equal(D.trechoDoContexto(barra, 2.3638).apoio, 'taxa de 2,36 médicos por 1.000 habitantes ou mais');
  assert.equal(D.trechoDoContexto(par, 2.3638).apoio, 'pelo componente mais próximo');
  assert.deepEqual([D.criterioDoContexto(2.3638), D.criterioDoContexto(null)], ['município mais próximo com 2,36 médicos por 1.000 habitantes ou mais', null]);
  assert.deepEqual([D.trechoDoContexto(barra), D.trechoDoContexto(para)].map(trecho => [trecho.texto, trecho.apoio]),
    [['Atende ao critério', 'taxa igual ou maior que a do critério'], ['Não se aplica', 'o estado como unidade não tem um ponto único']]);
  assert.deepEqual(['sem_coordenada', 'nao_calculavel', ''].map(estado => D.trechoDoContexto(ler({contexto: {estado, distancia_km: null}})).texto),
    ['Sem coordenada válida', 'Não calculável', 'Não calculável']);
  // Sinais combinados: as combinações pré-definidas, e os efeitos da mesma queda contados como um evento. Sem índice geral.
  assert.deepEqual(D.trechosCombinados(manaus), [{chave: 'coexistencia', texto: 'Abaixo do patamar anterior e poucos médicos', classe: null,
    apoio: '2 sinais vêm de quedas no número de médicos: contam como um evento'}]);
  assert.deepEqual([D.trechosCombinados(barra), D.trechosCombinados(semDados)], [[], []]);
  for (const proibido of ['isolad', 'desassistid', 'índice geral', 'escore'])
    assert.ok(!JSON.stringify([D.trechosDaComparacao(barra), D.trechoDoContexto(manaus), D.trechosCombinados(manaus)]).toLowerCase().includes(proibido), proibido);
});

test('fenômenos 8 a 12 em gráfico e mapa: só os valores e as coordenadas do motor', () => {
  const lida = comparada();
  const [barra] = lida.linhas;
  // As bolhas do Agente: X = a distância até o município mais próximo que atende ao critério; Y = a taxa; o tamanho, a população.
  const itens = D.itensDoContexto(lida.linhas);
  assert.deepEqual(itens.map(item => [item.id, item.tipo, item.distancia_km, item.densidade, item.populacao, item.quantidade]),
    [['code:130260', 'municipio', 423.514, 1.8135, 2255903, 12], ['c1', 'conjunto', 88.04, 0.5, 20000, 12]], 'só as linhas com distância a mostrar');
  assert.deepEqual([itens[0].referenciaDoItem, itens[1].membros, itens[1].contagem, itens[0].avaliavel],
    [[{id: 'code:150375', rotulo: 'JACAREACANGA (PA)'}], ['code:110001', 'code:999999'], 'SOMA_DOS_COMPONENTES', {densidade: true, distancia: true, variacao: null}]);
  assert.deepEqual(D.dominiosDoContexto(itens), {densidade: [0.5, 1.8135], distancia_km: [88.04, 423.514], populacao: [20000, 2255903], quantidade: [12, 12]});
  assert.deepEqual(D.dominiosDoContexto([]), {densidade: null, distancia_km: null, populacao: null, quantidade: null});
  // O mapa: em destaque, os municípios com o fenômeno do filtro (sem filtro, os sinais combinados); vazado, o município mais
  // próximo que atende ao critério; o conjunto, pelo contorno dos componentes com ponto. Estados como unidade não têm ponto.
  assert.deepEqual(D.camadasDoMapa(lida, lida.linhas, 'todos'), {fundo: ['code:350530', 'code:110001'], destaque: ['code:130260'], sinal: 'combinados',
    conjuntos: [{id: 'c1', nome: 'Par', membros: ['code:110001']}], referencias: ['code:150375']});
  assert.deepEqual(D.camadasDoMapa(lida, lida.linhas, 'disponibilidade'), {fundo: ['code:130260', 'code:110001'], destaque: ['code:350530'],
    sinal: 'disponibilidade', conjuntos: [{id: 'c1', nome: 'Par', membros: ['code:110001']}], referencias: []});
  assert.deepEqual(D.camadasDoMapa(lida, lida.linhas, 'registro').destaque, []);
  assert.deepEqual(D.camadasDoMapa(lida, [barra], 'disponibilidade'), {fundo: [], destaque: ['code:350530'], sinal: 'disponibilidade', conjuntos: [], referencias: []});
  // A série da taxa do território e a da referência dele (tracejada), para a Série temporal do Agente; a ausência não vira zero.
  const detalhe = D.normalizarDetalhe({territorio: {id: 'code:350530', rotulo: 'BARRA BONITA (SP)', tipo: 'municipio', unidade: 'médicos'}, janela: resposta([]).janela,
    comparativo: {competencias: ['201906', '202006', '202106'], taxa: [4.8, null, 3.07], indice: [128.1, null, 72.9], trechos: [[2014, 2017], [2018, 2021]],
      referencia: {rotulo: 'demais municípios de São Paulo (soma municipal)', motivo: null, taxa: [3.75, 4.0, 4.21]}}});
  assert.deepEqual(detalhe.comparativo, {competencias: ['201906', '202006', '202106'], taxa: [4.8, null, 3.07], indice: [128.1, null, 72.9],
    trechos: [[2014, 2017], [2018, 2021]],
    referencia: {rotulo: 'demais municípios de São Paulo (soma municipal)', motivo: null, taxa: [3.75, 4, 4.21]}});
  const series = D.seriesDoComparativo(detalhe);
  assert.deepEqual([series.item.id, series.item.densidade, series.item.serie], ['code:350530', 3.07, {comparavel: true, motivo: null,
    observacoes: [{competencia: '201906', valor: 4.8}, {competencia: '202006', valor: null}, {competencia: '202106', valor: 3.07}]}]);
  assert.deepEqual(series.referencias, [{id: 'referencia', rotulo: 'Referência: demais municípios de São Paulo',
    observacoes: [{competencia: '201906', valor: 3.75}, {competencia: '202006', valor: 4}, {competencia: '202106', valor: 4.21}]}]);
  const semReferencia = {...detalhe, comparativo: {...detalhe.comparativo, referencia: {rotulo: '', motivo: 'A UF não tem outros municípios.', taxa: [null, null, null]}}};
  assert.deepEqual(D.seriesDoComparativo(semReferencia).referencias, []);
  assert.deepEqual([D.seriesDoComparativo({...detalhe, comparativo: null}), D.seriesDoComparativo({...detalhe, comparativo: {...detalhe.comparativo, taxa: [null, null, null]}}),
    D.normalizarDetalhe({territorio: {id: 'a', rotulo: 'A'}, janela: {}}).comparativo], [null, null, null]);
});

test('fenômenos 8 a 12: os filtros, as exportações e o que o Detector leva ao Simulador', () => {
  const lida = comparada();
  const [barra, manaus, , par] = lida.linhas;
  assert.deepEqual(['disponibilidade', 'posicao', 'defasagem', 'combinados'].map(fenomeno =>
    D.filtrarLinhas(lida.linhas, {...D.SEM_FILTROS, fenomeno}).map(item => item.id)), [['code:350530'], ['code:350530'], ['code:350530'], ['code:130260', 'c1']]);
  assert.deepEqual(D.FILTROS_DE_FENOMENO.slice(-4), [{chave: 'disponibilidade', rotulo: 'Queda da taxa por habitante (2 anos)'},
    {chave: 'posicao', rotulo: 'Queda da posição relativa (2 anos)'}, {chave: 'defasagem', rotulo: 'Defasagem ante a referência (2 anos)'},
    {chave: 'combinados', rotulo: 'Sinais combinados'}]);
  assert.deepEqual([D.formatarTaxa(3.0727), D.formatarTaxa(2), D.formatarTaxa(1234.5)], ['3,07', '2,00', '1.234,50']);
  // O CSV leva a janela de comparação, o nível da data, a variação, o estado e o sinal de cada indicador, e o critério do contexto.
  const [cabecalho, daBarra, doPar] = D.csvDoDetector(lida, [barra, par]).slice(1).trim().split('\r\n').map(texto => texto.split(';'));
  assert.equal(new Set(cabecalho).size, cabecalho.length);
  assert.deepEqual(cabecalho.slice(32), ['Janela de comparação: de', 'Janela de comparação: até', 'Janela de comparação: estado', 'Taxa por 1.000 habitantes', 'População',
    'Variação da taxa em 2 anos (%)', 'Taxa: estado', 'Taxa: sinal observado', 'Percentil da taxa', 'Universo do percentil', 'Variação do percentil em 2 anos (pontos)',
    'Posição: estado', 'Posição: sinal observado', 'Índice ante a referência', 'Variação do índice em 2 anos (pontos)', 'Defasagem: estado', 'Defasagem: sinal observado',
    'Distância ao município mais próximo que atende ao critério (km)', 'Município mais próximo que atende ao critério', 'Percentil da distância',
    'Contexto geográfico: estado', 'Critério do contexto: taxa mínima', 'Sinais combinados', 'Configuração', 'Versão do método', 'Versão da base']);
  assert.deepEqual(daBarra.slice(32), ['201906', '202106', 'comparavel', '3,0727', '36125', '-36,205', 'sinal_observado', 'muito_forte', '86,29', '5570', '-11,526',
    'sinal_observado', 'queda', '72,887', '-55,21', 'sinal_observado', 'forte', '', '', '', 'atende_ao_criterio', '1,9834', '', 'padrão (limites provisórios)',
    'DETECTOR-SINAIS/V2.2/2', 'abc']);
  assert.deepEqual(doPar.slice(49, 53), ['88,04', 'PORTO VELHO (RO)', '', 'contexto']);
  assert.deepEqual(JSON.parse(D.metodoDoDetector(lida)).comparacao_relativa.contexto, {taxaMinima: 1.9834, taxaDoBrasil: 1.9834, pctDaTaxaDoBrasil: 100,
    atendem: 1720, universo: 3846});
  assert.deepEqual(Object.keys(D.NOMES_DOS_PARAMETROS.posicao.campos), ['queda', 'forte', 'muito_forte']);
  assert.equal(D.NOMES_DOS_PARAMETROS.contexto.campos.taxa_do_brasil_pct, 'Critério: taxa mínima do município mais próximo (% da taxa do Brasil)');
  // "Abrir no Simulador" e "Simular recuperação": o território, a data avaliada, os sinais à vista (pelos nomes dos filtros) e a janela
  // só quando a pessoa a escolheu (a janela padrão do Detector, a série inteira, não é levada).
  assert.deepEqual(D.alvoDoSimulador(manaus, lida), {id: 'code:130260', tipo: 'municipio', rotulo: 'MANAUS (AM)',
    sinais: ['Abaixo do patamar anterior', 'Sinais combinados'], fim: '202106', janela: {inicio: '201401', fim: '202106'}, exploratorio: false});
  assert.deepEqual(D.alvoDoSimulador(par, {janela: {...lida.janela, padrao: true}, exploratorio: true}), {id: 'c1', tipo: 'conjunto', rotulo: 'Par',
    sinais: ['Sinais combinados'], fim: '202106', janela: null, exploratorio: true});
  // "Simular recuperação" só existe para quem está abaixo do patamar anterior: acima dele, não há o que recuperar.
  const comPatamar = (patamar, diferenca_pct) => D.normalizarDetector(resposta([linha({patamar: {estado: 'descritivo', classe: null, patamar, diferenca_pct,
    abaixo: diferenca_pct < 0, critica: null}})])).linhas[0];
  assert.deepEqual([comPatamar(78.25, -30.99), comPatamar(4086, 15.76), comPatamar(12, 0), comPatamar(null, null)].map(D.patamarARecuperar), [78.25, null, null, null]);
});
