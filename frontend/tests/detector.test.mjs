import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const ler = caminho => readFileSync(new URL('../src/' + caminho, import.meta.url), 'utf8');
// Detector de Sinais Territoriais (comando V23, Proposta V3, Parte B): o modelo puro da tela (detectorModel.ts) — a leitura da
// resposta de POST /api/detector (o alerta de cada território, os níveis, a régua da data e os "Entenda"), os textos da lista de
// quatro colunas, o resumo dos níveis, os filtros (Nível, Sinal e Buscar), a ordem, os critérios em frases com os campos dentro
// delas, o mapa e o gráfico pelos níveis, as exportações e o que o Detector leva ao Simulador —, a seleção no contrato das
// ferramentas (painelModel.selecaoDasFerramentas) e o componente "Entenda". Nada é calculado na tela.
const D = await source('detectorModel');
const M = await source('painelModel');

const SEM_ALERTA = {estado: 'sem_alerta', nivel: null, sinal: null, criterio: null, outros: 0, por_que: null, sinais: [], mesma_queda: [], sem_comparacoes: [],
  motivo: null};
const alerta = (nivel, sinal, criterio, por_que, extra = {}) => ({estado: 'alerta', nivel, sinal, criterio, outros: 0, por_que,
  sinais: [{sinal, nivel, criterio}], mesma_queda: [], sem_comparacoes: [], motivo: null, ...extra});
const linha = (extra = {}) => ({
  id: 'code:130260', tipo: 'municipio', nivel: 'municipios', rotulo: 'MANAUS (AM)', uf: 'AM',
  ultima: {competencia: '202406', valor: 12, na_data: true}, porte: 2, sinais: [], alerta: SEM_ALERTA,
  estrutural: {estado: 'sem_sinal', classe: null, n: 12, impacto_pct: 8.333333333333334, zeros: null, mantida: false},
  perda: {estado: 'sem_perda', classe: null, delta: 0, pct: 0, de: '202401', ate: '202406', magnitude: null, motivo: null, verificar: null},
  patamar: {estado: 'sem_sinal', classe: null, patamar: 11.5, diferenca_pct: 4.3, abaixo: false},
  declinio: {estado: 'sem_sinal', classe: null, reducoes: 0, perda_pct: null},
  desaceleracao: {estado: 'sem_sinal', classe: null, desacelera: false, persistente: null, anos: 0, rotulo: 'Crescimento'},
  instabilidade: {estado: 'sem_sinal', classe: null, indice: 1.24}, registro: {estado: 'normal', tipos: []}, ...extra});
const ROTULOS = {profissional: 'médico', profissionais: 'médicos', unidade: 'município', unidades: 'municípios', grupo: 'estado', grupos: 'estados', todo: 'Brasil'};
// Os nomes de outra base (seção A.2.6): nada de "médicos", "município" ou "estado" que não venha dela.
const ENF = {profissional: 'enfermeiro', profissionais: 'enfermeiros', unidade: 'distrito', unidades: 'distritos', grupo: 'região', grupos: 'regiões', todo: 'a base'};
const PORTES = ['1 a 3', '4 a 9', '10 a 19', '20 a 49', '50 a 99', '100 a 299', '300 a 999', '1.000 a 2.999', '3.000 a 9.999', '10.000 ou mais'];
const corte = (um_em, valor, campo = 'queda_pct') => ({um_em, pede: um_em - 1, [campo]: valor});
const resposta = (linhas, extra = {}) => ({
  versao: 'DETECTOR-SINAIS/V3/1',
  fonte: {base: 'Brasil', categoria: 'MEDICINA', versao: 'abc', primeira: '201401', ultima: '202406', competencias: 22, rotulos: ROTULOS,
    unidades: {municipio: 'médicos registrados'}},
  janela: {inicio: '201401', fim: '202406', registros: 22, meses: 125, padrao: true, ultimo_registro_da_base: '202406', e_o_ultimo: true},
  competencias: ['201401', '201406', '202406'],
  parametros: {padrao: {perda: {moderado_um_em: 20, moderado_minimo: 2}}, em_uso: {perda: {moderado_um_em: 20, moderado_minimo: 2}}, personalizados: false,
    editaveis: {perda: {moderado_um_em: {minimo: 2, maximo: 100000, inteiro: true}}}},
  exploratorio: false, linhas,
  niveis: [{chave: 'moderado', nome: 'Moderado', um_em: 20, pede: 19}, {chave: 'elevado', nome: 'Elevado', um_em: 100, pede: 99},
    {chave: 'critico', nome: 'Crítico', um_em: 1000, pede: 999}, {chave: 'outro', nome: 'x'}],
  grupos: [{chave: 'quantos', nome: 'Quantos há', sinais: ['estrutural']}, {chave: 'mudou', nome: 'Como mudou', sinais: ['declinio', 'perda']}],
  portes: PORTES, entenda: {ferramenta: {texto: 'Compara com a própria base.', exemplo: 'De 18 para 11.'}, termos: {texto: 'Porte é o tamanho.'}},
  resumo: {territorios: linhas.length, por_tipo: {municipio: linhas.length},
    niveis: {critico: 1, elevado: 0, moderado: 2, sem_alerta: 3, sem_comparacoes: 0, sem_nivel: 1}, com_nivel: {perda: 2}, sinais: {perda: 2},
    sem_registro_na_data: 0},
  calibracao: {competencia: '202406', intervalo_meses: 5,
    perda: [{porte: '1 a 3', comparacoes: 6572, critico: corte(1000, 100), elevado: corte(100, 50), moderado: corte(20, 33.33333333333333)},
      {porte: '3.000 a 9.999', comparacoes: 203, critico: corte(1000, null), elevado: corte(100, 7.605070046697798), moderado: corte(20, -0.229)}],
    patamar: [{porte: '20 a 49', comparacoes: 13942, critico: corte(1000, 62.16216216216216, 'afastamento_pct'), elevado: corte(100, 39.53488372093024, 'afastamento_pct')}],
    monitoramento: {avaliadas: 5570, raras: 161, taxa_pct: 2.89048473967684, esperado_pct: 5, aviso_da_base: false}},
  aviso_da_base: null, notas: ['Um nível por território.'], limitacoes: ['RARO_E_INCOMUM_NA_BASE'], ...extra});
const lerLinha = extra => D.normalizarDetector(resposta([linha(extra)])).linhas[0];

test('a resposta do motor vira os tipos da tela, sem calcular nada: o alerta, os níveis, a régua da data e os "Entenda"', () => {
  const lida = D.normalizarDetector(resposta([linha(), {id: null}, linha({id: 'uf:15', tipo: 'estado', rotulo: 'Pará (PA)', porte: 8})]));
  assert.equal(lida.linhas.length, 2, 'a linha sem id fica de fora');
  assert.deepEqual(lida.linhas[0].ultima, {competencia: '202406', valor: 12, naData: true});
  assert.equal(lida.linhas[0].estrutural.impactoPct, 8.333333333333334);
  assert.deepEqual(lida.linhas[0].alerta, {estado: 'sem_alerta', nivel: null, sinal: null, criterio: null, outros: 0, porQue: null, sinais: [], mesmaQueda: [],
    semComparacoes: [], motivo: null});
  assert.deepEqual(lida.janela, {inicio: '201401', fim: '202406', registros: 22, meses: 125, padrao: true, ultimoRegistroDaBase: '202406', eOUltimo: true});
  assert.deepEqual(lida.parametros.editaveis.perda.moderado_um_em, {minimo: 2, maximo: 100000, inteiro: true});
  // Os níveis (1 em cada N e as comparações que cada um pede), os grupos dos sinais, os portes e os nomes da base vêm do motor.
  assert.deepEqual(lida.niveis, [{chave: 'moderado', nome: 'Moderado', umEm: 20, pede: 19}, {chave: 'elevado', nome: 'Elevado', umEm: 100, pede: 99},
    {chave: 'critico', nome: 'Crítico', umEm: 1000, pede: 999}], 'um nível desconhecido fica de fora');
  assert.deepEqual(lida.grupos[1], {chave: 'mudou', nome: 'Como mudou', sinais: ['declinio', 'perda']});
  assert.deepEqual([lida.portes.length, lida.portes[6], lida.portes[9]], [10, '300 a 999', '10.000 ou mais']);
  assert.deepEqual(lida.fonte.rotulos, ROTULOS);
  assert.deepEqual(lida.entenda, {ferramenta: {texto: 'Compara com a própria base.', exemplo: 'De 18 para 11.'}, termos: {texto: 'Porte é o tamanho.', exemplo: ''}});
  assert.deepEqual(lida.resumo.niveis, {critico: 1, elevado: 0, moderado: 2, sem_alerta: 3, sem_comparacoes: 0, sem_nivel: 1});
  assert.deepEqual([lida.resumo.comNivel, lida.resumo.sinais.perda], [{perda: 2}, 2]);
  // A régua da data: por porte, as comparações e o corte de cada nível; sem comparações bastantes, o corte é nulo.
  assert.deepEqual(lida.calibracao.perda[1], {porte: '3.000 a 9.999', comparacoes: 203, niveis: {critico: {umEm: 1000, pede: 999, cortePct: null},
    elevado: {umEm: 100, pede: 99, cortePct: 7.605070046697798}, moderado: {umEm: 20, pede: 19, cortePct: -0.229}}});
  assert.deepEqual(lida.calibracao.patamar[0].niveis, {critico: {umEm: 1000, pede: 999, cortePct: 62.16216216216216},
    elevado: {umEm: 100, pede: 99, cortePct: 39.53488372093024}}, 'o moderado do sinal 7 é por convenção: sem corte na régua');
  assert.deepEqual(lida.calibracao.monitoramento, {avaliadas: 5570, raras: 161, taxaPct: 2.89048473967684, esperadoPct: 5, avisoDaBase: false});
  assert.deepEqual([lida.calibracaoDosEstados, lida.avisoDaBase], [null, null]);
  const comEstados = D.normalizarDetector(resposta([], {calibracao_dos_estados: {competencia: '202406', intervalo_meses: 5,
    perda: [{porte: '10.000 ou mais', comparacoes: 101, critico: corte(1000, null), elevado: corte(100, 1.49), moderado: corte(20, -0.28)}], patamar: []},
    aviso_da_base: 'Em jun/2024, 18,0% dos territórios tiveram uma queda rara ao mesmo tempo.'}));
  assert.deepEqual([comEstados.calibracaoDosEstados.perda[0].comparacoes, comEstados.calibracaoDosEstados.perda[0].niveis.critico.cortePct,
    comEstados.avisoDaBase], [101, null, 'Em jun/2024, 18,0% dos territórios tiveram uma queda rara ao mesmo tempo.']);
  // Sem os nomes na resposta, valem os da base do Brasil; uma resposta vazia ou estranha não derruba a tela.
  const vazia = D.normalizarDetector(null);
  assert.deepEqual([vazia.linhas, vazia.competencias, vazia.exploratorio, vazia.niveis, vazia.grupos, vazia.portes, vazia.entenda, vazia.fonte.rotulos],
    [[], [], false, [], [], [], {}, D.ROTULOS_DO_BRASIL]);
  assert.deepEqual(D.normalizarDetector(resposta([], {fonte: {rotulos: {profissionais: 'enfermeiros', grupo: 7}}})).fonte.rotulos,
    {...D.ROTULOS_DO_BRASIL, profissionais: 'enfermeiros'});
  // O detalhe: a série, o histórico (com o alerta de cada data) e cada sinal com o nível, a frase, o "Entenda" e a explicação.
  const detalhe = D.normalizarDetalhe({territorio: {id: 'c1', rotulo: 'Par', tipo: 'conjunto', unidade: 'soma', nomes_dos_membros: ['A', 'B']},
    janela: resposta([]).janela, janela_do_territorio: {inicio: '201801', depois_da_quebra: true},
    serie: [{competencia: '201401', valor: null, estado: 'ausencia_de_dado'}, {competencia: '201406', valor: 0, estado: 'zero_confirmado', marca: 'quebra_de_fonte'}],
    historico: [{competencia: '201406', valor: 3, alerta: 'elevado', estrutural: 'elevado', perda: {delta: -2, pct: -40, estado: 'sem_comparacoes', classe: null},
      patamar: {estado: 'descritivo', classe: null, diferenca_pct: -25}, instabilidade: 'moderado', declinio: {reducoes: 2, classe: 'moderado'}, desaceleracao: null}],
    fenomenos: [{chave: 'perda', numero: '6', nome: 'Queda recente', grupo: 'mudou', dimensao: 'Trajetória', nivel: 'elevado', estado_do_nivel: 'alerta',
      criterio_do_nivel: 'comparado com a base', situacao: 'Caiu de 18 para 11 (−38,9%)', entenda: {texto: 'Compara a queda.', exemplo: 'De 2 para 1.'},
      exploratorio: false, sem_comparacoes: {niveis: ['critico'], nivel: 'critico', comparacoes: 203, pede: 999,
        texto: 'Sem comparações suficientes para o crítico: há 203, e ele pede 999.'},
      observado: 'o', criterio: 'c', habitual: 'h', significa: 'sig', nao_significa: 'ns', limitacoes: 'l', qualidade: 'q'},
    {chave: 'desaceleracao', numero: '4', nome: 'Desaceleração', grupo: 'mudou', nivel: 'nenhum', estado_do_nivel: 'sem_alerta', exploratorio: true,
      sem_comparacoes: null}],
    linha: linha({id: 'c1', tipo: 'conjunto', alerta: {...SEM_ALERTA, estado: 'sem_nivel', motivo: 'm'}}), notas: ['n'], exploratorio: true});
  assert.deepEqual([detalhe.id, detalhe.membros, detalhe.inicioDoTerritorio, detalhe.depoisDaQuebra, detalhe.exploratorio],
    ['c1', ['A', 'B'], '201801', true, true]);
  assert.deepEqual(detalhe.serie[0], {competencia: '201401', valor: null, estado: 'ausencia_de_dado', marca: null, membrosSemRegistro: null});
  assert.equal(detalhe.serie[1].valor, 0, 'zero é valor, não ausência');
  assert.deepEqual(detalhe.historico[0], {competencia: '201406', valor: 3, alerta: 'elevado', estrutural: 'elevado',
    perda: {delta: -2, pct: -40, estado: 'sem_comparacoes', classe: null}, patamar: {estado: 'descritivo', classe: null, diferencaPct: -25},
    instabilidade: 'moderado', declinio: {reducoes: 2, classe: 'moderado'}, desaceleracao: null});
  const [queda, ritmo] = detalhe.fenomenos;
  assert.deepEqual([queda.nivel, queda.estadoDoNivel, queda.criterioDoNivel, queda.grupo, queda.situacao, queda.entenda, queda.exploratorio, queda.naoSignifica],
    ['elevado', 'alerta', 'comparado com a base', 'mudou', 'Caiu de 18 para 11 (−38,9%)', {texto: 'Compara a queda.', exemplo: 'De 2 para 1.'}, false, 'ns']);
  assert.deepEqual(queda.semComparacoes, {niveis: ['critico'], comparacoes: 203, pede: 999, texto: 'Sem comparações suficientes para o crítico: há 203, e ele pede 999.'});
  assert.deepEqual([ritmo.nivel, ritmo.estadoDoNivel, ritmo.exploratorio, ritmo.semComparacoes, ritmo.entenda], [null, 'sem_alerta', true, null, {texto: '', exemplo: ''}]);
  assert.deepEqual([detalhe.linha.id, detalhe.linha.alerta.estado, D.normalizarDetalhe({}).linha], ['c1', 'sem_nivel', null]);
});

test('a lista de quatro colunas: o alerta (um nível, sempre escrito, com o tipo de critério), o porquê e o último registro', () => {
  // Alerta: o nível e o tipo de critério; o porquê é a frase do motor, com quantos outros sinais têm nível.
  const critico = lerLinha({alerta: alerta('critico', 'estrutural', 'por convenção', 'Só 1 médico (+1 sinal)', {outros: 1,
    sinais: [{sinal: 'estrutural', nivel: 'critico', criterio: 'por convenção'}, {sinal: 'perda', nivel: 'moderado', criterio: 'comparado com a base'}]})});
  assert.deepEqual(D.textoDoAlerta(critico), {estado: 'critico', nivel: 'critico', texto: 'Crítico', criterio: 'por convenção'});
  assert.equal(D.textoDoPorQue(critico), 'Só 1 médico (+1 sinal)');
  assert.deepEqual(critico.alerta.sinais.map(item => item.sinal + ':' + item.nivel), ['estrutural:critico', 'perda:moderado']);
  // Sem alerta, sem comparações suficientes (com os sinais que faltaram) e sem nível (o conjunto, com o motivo do motor).
  assert.deepEqual([D.textoDoAlerta(lerLinha({})), D.textoDoPorQue(lerLinha({}))],
    [{estado: 'sem_alerta', nivel: null, texto: 'Sem alerta', criterio: null}, 'Nenhum sinal com nível.']);
  const semComparacoes = lerLinha({alerta: {...SEM_ALERTA, estado: 'sem_comparacoes', sem_comparacoes: ['perda', 'instabilidade']}});
  assert.deepEqual([D.textoDoAlerta(semComparacoes).texto, D.textoDoPorQue(semComparacoes)],
    ['Sem comparações suficientes', 'A base ainda não tem história para comparar: queda recente e instabilidade.']);
  assert.equal(D.textoDoPorQue(lerLinha({alerta: {...SEM_ALERTA, sem_comparacoes: ['disponibilidade']}})),
    'Nenhum sinal com nível (sem comparações suficientes em menos médicos por habitante).');
  const conjunto = lerLinha({tipo: 'conjunto', membros: 3,
    alerta: {...SEM_ALERTA, estado: 'sem_nivel', motivo: 'Um conjunto não tem outros iguais para comparar: a tela mostra os fatos, sem nível.'}});
  assert.deepEqual([D.textoDoAlerta(conjunto).texto, D.textoDoAlerta(conjunto).criterio, D.textoDoPorQue(conjunto)],
    ['Sem nível (conjunto)', null, 'Um conjunto não tem outros iguais para comparar: a tela mostra os fatos, sem nível.']);
  assert.equal(D.textoDoPorQue(lerLinha({ultima: null})), 'Sem registro na janela.');
  // Os efeitos da mesma queda contam como um evento, e a tela diz isso.
  const queda = lerLinha({alerta: alerta('elevado', 'disponibilidade', 'comparado com a base', '−38,2% de médicos por habitante em 2 anos (+3 sinais)',
    {outros: 3, mesma_queda: ['disponibilidade', 'defasagem', 'patamar', 'posicao']})});
  assert.equal(D.textoDaMesmaQueda(queda),
    'Menos médicos por habitante, mais longe da referência, abaixo do que já teve e perda de posição vêm da mesma queda: contam como um evento.');
  assert.equal(D.textoDaMesmaQueda(critico), null);
  // O resumo dos níveis (clicável como filtro) e os nomes dos estados do alerta.
  assert.deepEqual([['critico', 41], ['critico', 1], ['elevado', 434], ['moderado', 1], ['sem_alerta', 4118], ['sem_comparacoes', 3], ['sem_nivel', 1],
    ['sem_nivel', 2]].map(([estado, n]) => D.textoDaContagem(estado, n)), ['41 críticos', '1 crítico', '434 elevados', '1 moderado', '4.118 sem alerta',
    '3 sem comparações suficientes', '1 sem nível (conjunto)', '2 sem nível (conjuntos)']);
  assert.deepEqual(D.ESTADOS_DO_ALERTA.map(D.nomeDoEstado), ['Crítico', 'Elevado', 'Moderado', 'Sem alerta', 'Sem comparações suficientes', 'Sem nível (conjunto)']);
  assert.deepEqual([D.NIVEIS, D.NOMES_DOS_NIVEIS], [['critico', 'elevado', 'moderado'], {moderado: 'Moderado', elevado: 'Elevado', critico: 'Crítico'}]);
  // Os nomes dos sinais e o último registro usam os nomes da base.
  assert.deepEqual(['estrutural', 'ausencia', 'declinio', 'desaceleracao', 'instabilidade', 'perda', 'patamar', 'disponibilidade', 'posicao', 'defasagem',
    'contexto', 'coexistencia', 'x'].map(chave => D.nomeDoSinal(chave)), ['Poucos médicos', 'Nenhum médico registrado', 'Declínio persistente', 'Desaceleração',
    'Instabilidade', 'Queda recente', 'Abaixo do que já teve', 'Menos médicos por habitante', 'Perda de posição', 'Mais longe da referência', 'Distância',
    'Sinais juntos', 'x']);
  assert.deepEqual(['estrutural', 'ausencia', 'disponibilidade'].map(chave => D.nomeDoSinal(chave, ENF)),
    ['Poucos enfermeiros', 'Nenhum enfermeiro registrado', 'Menos enfermeiros por habitante']);
  assert.deepEqual([D.textoDaUltima(lerLinha({}), '202406'), D.textoDaUltima(lerLinha({ultima: {competencia: '202401', valor: 1, na_data: false}}), '202406'),
    D.textoDaUltima(lerLinha({ultima: null}), '202406'), D.textoDaUltima(lerLinha({}), '202406', ENF)],
    ['jun/2024 · 12 médicos', 'jan/2024 · 1 médico (sem registro em jun/2024)', 'Sem registro na janela', 'jun/2024 · 12 enfermeiros']);
  assert.deepEqual([D.tipoDoTerritorio(conjunto), D.tipoDoTerritorio(lerLinha({tipo: 'estado'})), D.tipoDoTerritorio(lerLinha({})),
    D.tipoDoTerritorio(lerLinha({tipo: 'estado'}), ENF)],
    ['conjunto · soma de 3 territórios', 'estado como unidade · régua própria', null, 'região como unidade · régua própria']);
  // A qualidade do registro continua à vista: "verificar registro" e a descontinuidade de registro.
  assert.deepEqual(D.textoDoRegistro(lerLinha({registro: {estado: 'descontinuidade_de_registro', tipos: ['pico_que_volta']}})),
    {texto: 'Descontinuidade de registro (pico que volta)', marca: 'descontinuidade'});
  assert.deepEqual(D.textoDoRegistro(lerLinha({registro: {estado: 'verificar_registro', tipos: ['queda_grande', 'salto']}})),
    {texto: 'Verificar registro (queda grande, salto)', marca: 'verificar'});
  assert.equal(D.textoDoRegistro(lerLinha({})).texto, 'Normal');
  // Os nomes novos (decisão 2 de 13/11/2026): nenhum termo antigo nos fontes da tela, e o nível sempre escrito.
  const codigo = (ler('detectorModel.ts') + ler('DetectorDeSinais.tsx') + ler('DetectorGraficos.tsx')).replace(/\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '');
  for (const termo of ['não calibrado', 'Não calibrado', 'sem classificação', 'Sem classificação', 'limiar candidato', 'limite provisório', 'limites provisórios',
    'criticidade', 'intensidade', 'Atenção', 'isolamento', 'desassist'])
    assert.ok(!codigo.includes(termo), termo);
  assert.match(ler('DetectorDeSinais.tsx'), /<span data-testid="detector-nivel" data-nivel=\{nivel\}[^>]*>\{NOMES_DOS_NIVEIS\[nivel\]\}<\/span>/,
    'o nível aparece sempre escrito, nunca só pela cor');
});

test('filtros (Nível, Sinal e Buscar) e a ordem da lista, que não é um índice', () => {
  const linhas = D.normalizarDetector(resposta([
    linha({id: 'a', rotulo: 'ÁGUA BRANCA (AL)', ultima: {competencia: '202406', valor: 2, na_data: true}, sinais: ['estrutural', 'perda', 'alerta_perda'],
      alerta: alerta('elevado', 'estrutural', 'por convenção', '2 médicos (+1 sinal)', {outros: 1,
        sinais: [{sinal: 'estrutural', nivel: 'elevado', criterio: 'por convenção'}, {sinal: 'perda', nivel: 'moderado', criterio: 'comparado com a base'}]})}),
    linha({id: 'b', rotulo: 'Belém (PA)', ultima: {competencia: '202406', valor: 900, na_data: true}, sinais: ['patamar', 'registro'],
      alerta: alerta('moderado', 'patamar', 'por convenção', '18% abaixo do que já teve (patamar de 1.098)')}),
    linha({id: 'c', rotulo: 'Cacoal (RO)', ultima: {competencia: '202406', valor: 0, na_data: true}, sinais: ['estrutural', 'ausencia'],
      alerta: alerta('critico', 'ausencia', 'por convenção', 'Nenhum médico registrado há 2 registros, desde jan/2024')}),
    linha({id: 'd', rotulo: 'Dourados (MS)', alerta: {...SEM_ALERTA, estado: 'sem_comparacoes', sem_comparacoes: ['perda']}}),
    linha({id: 'e', rotulo: 'Erechim (RS)', ultima: {competencia: '202406', valor: 300, na_data: true}}),
    linha({id: 'f', tipo: 'conjunto', rotulo: 'Conjunto A', ultima: {competencia: '202406', valor: 40, na_data: true}, alerta: {...SEM_ALERTA, estado: 'sem_nivel'}})])).linhas;
  const ids = lista => lista.map(item => item.id);
  assert.deepEqual(ids(D.filtrarLinhas(linhas, D.SEM_FILTROS)), ['a', 'b', 'c', 'd', 'e', 'f']);
  // Nível: o do alerta do território (um nível só), "sem alerta", "sem comparações suficientes" e "sem nível".
  assert.deepEqual(D.ESTADOS_DO_ALERTA.map(nivel => ids(D.filtrarLinhas(linhas, {...D.SEM_FILTROS, nivel}))), [['c'], ['a'], ['b'], ['e'], ['d'], ['f']]);
  assert.deepEqual(linhas.map(D.estadoDoAlerta), ['elevado', 'moderado', 'critico', 'sem_comparacoes', 'sem_alerta', 'sem_nivel']);
  // Sinal: a linha passa quando o sinal tem nível nela (não só o principal); mais de um sinal com nível; registro a verificar.
  assert.deepEqual(['estrutural', 'perda', 'ausencia', 'patamar', 'juntos', 'registro', 'declinio'].map(sinal => ids(D.filtrarLinhas(linhas, {...D.SEM_FILTROS, sinal}))),
    [['a'], ['a'], ['c'], ['b'], ['a'], ['b'], []]);
  assert.deepEqual(ids(D.filtrarLinhas(linhas, {...D.SEM_FILTROS, busca: 'agua'})), ['a'], 'a busca ignora acentos e caixa');
  assert.deepEqual(ids(D.filtrarLinhas(linhas, {nivel: 'critico', sinal: 'ausencia', busca: 'cac'})), ['c']);
  assert.deepEqual(D.filtrosDeSinal().map(item => item.chave), ['todos', 'estrutural', 'ausencia', 'declinio', 'desaceleracao', 'instabilidade', 'perda', 'patamar',
    'disponibilidade', 'posicao', 'defasagem', 'juntos', 'registro']);
  assert.deepEqual(D.filtrosDeSinal(ENF).slice(1, 3).map(item => item.rotulo), ['Poucos enfermeiros', 'Nenhum enfermeiro registrado']);
  // O nome anterior de um município continua achando-o (base Brasil, 13/11/2026): "Parati" acha PARATY, e a tela mostra o atual.
  const renomeadas = D.normalizarDetector(resposta([linha({id: 'code:330380', rotulo: 'PARATY (RJ)', nomes_anteriores: ['PARATI']}),
    linha({id: 'code:130260', rotulo: 'MANAUS (AM)'})])).linhas;
  assert.deepEqual([renomeadas[0].nomesAnteriores, 'nomesAnteriores' in renomeadas[1]], [['PARATI'], false]);
  assert.deepEqual(['parati', 'Paraty', 'manaus', 'ouro'].map(busca => ids(D.filtrarLinhas(renomeadas, {...D.SEM_FILTROS, busca}))),
    [['code:330380'], ['code:330380'], ['code:130260'], []]);
  // A ordem: pelo nível (do crítico ao moderado; depois quem a base não pôde comparar, os conjuntos e os sem alerta), pelo nome ou
  // pelo número do último registro. Nenhuma soma de níveis entra na ordem.
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'nivel')), ['c', 'a', 'b', 'd', 'f', 'e']);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'nome')), ['a', 'b', 'c', 'f', 'd', 'e']);
  assert.deepEqual(ids(D.ordenarLinhas(linhas, 'numero')), ['c', 'a', 'd', 'f', 'e', 'b']);
  assert.deepEqual(ids(linhas), ['a', 'b', 'c', 'd', 'e', 'f'], 'ordenar não muda a lista recebida');
});

test('"Ajustar critérios": os limites em frases, com os campos dentro delas, para todos os parâmetros do motor', () => {
  const criterios = D.criteriosEmFrases();
  assert.deepEqual(criterios.map(criterio => [criterio.sinal, criterio.numero, criterio.titulo, criterio.tipo, criterio.frases.length]), [
    ['estrutural', '1–2', 'Poucos médicos ou nenhum', 'por convenção', 1], ['declinio', '3', 'Declínio persistente', 'por convenção', 3],
    ['desaceleracao', '4', 'Desaceleração', 'por convenção (exploratório)', 1], ['instabilidade', '5', 'Instabilidade', 'comparado com a base', 1],
    ['perda', '6', 'Queda recente', 'comparado com a base, com tamanho mínimo', 3], ['patamar', '7', 'Abaixo do que já teve', 'por convenção e comparado com a base', 4],
    ['disponibilidade', '8', 'Menos médicos por habitante', 'comparado com a base', 2], ['posicao', '9', 'Perda de posição', 'comparado com a base', 2],
    ['defasagem', '10', 'Mais longe da referência', 'comparado com a base', 2], ['contexto', '11', 'Distância', 'só contexto', 1]]);
  // Cada parâmetro que o motor deixa trocar (detector.EDITAVEIS e comparativos.EDITAVEIS) tem um campo numa frase, uma vez só.
  const campos = criterios.flatMap(criterio => criterio.frases.flatMap(frase => frase.filter(parte => typeof parte !== 'string').map(parte => parte.grupo + '.' + parte.campo)));
  const um_em = grupo => ['moderado', 'elevado', 'critico'].map(nivel => grupo + '.' + nivel + '_um_em');
  const doMotor = ['estrutural.critico', 'estrutural.elevado', 'estrutural.moderado',
    ...['moderado', 'elevado', 'critico'].flatMap(nivel => ['declinio.' + nivel + '_quedas', 'declinio.' + nivel + '_perda']), 'desaceleracao.anos',
    'instabilidade.moderado_um_em', ...um_em('perda'), ...['moderado', 'elevado', 'critico'].flatMap(nivel => ['perda.' + nivel + '_minimo', 'perda.' + nivel + '_fracao']),
    'patamar.moderado', 'patamar.critico', 'patamar.minimo', 'patamar.elevado_um_em', 'patamar.critico_um_em', ...um_em('disponibilidade'), ...um_em('posicao'),
    ...um_em('defasagem'), 'contexto.taxa_do_brasil_pct'];
  assert.deepEqual([...campos].sort(), [...doMotor].sort());
  assert.equal(new Set(campos).size, campos.length, 'nenhum campo repetido');
  // A frase do anexo (seção A.4), com os campos no lugar dos números.
  const emTexto = frase => frase.map(parte => typeof parte === 'string' ? parte : '[' + parte.grupo + '.' + parte.campo + ']').join('');
  const queda = criterios.find(criterio => criterio.sinal === 'perda');
  assert.equal(emTexto(queda.frases[1]), 'Alerta elevado quando a queda for de pelo menos [perda.elevado_minimo] médicos e [perda.elevado_fracao]% do que havia, ' +
    'e for rara: em territórios do mesmo porte, só 1 em cada [perda.elevado_um_em] mudanças anteriores foi uma queda igual ou maior.');
  assert.equal(emTexto(criterios[0].frases[0]), 'Pelo número de médicos no último registro: crítico até [estrutural.critico] (zero é sempre crítico); elevado até ' +
    '[estrutural.elevado]; moderado até [estrutural.moderado].');
  assert.equal(emTexto(criterios.find(criterio => criterio.sinal === 'patamar').frases[3]), 'Só vale para patamar de pelo menos [patamar.minimo] médicos.');
  assert.equal(emTexto(criterios.at(-1).frases[0]), 'Medir a distância até o território mais próximo com taxa de pelo menos [contexto.taxa_do_brasil_pct]% da taxa da ' +
    'base toda.');
  // O nome de cada campo para o leitor de tela: o sinal e o que vem antes do campo na frase.
  assert.deepEqual(queda.frases[0].map((parte, indice) => typeof parte === 'string' ? null : D.rotuloDoCampo(queda, queda.frases[0], indice)).filter(Boolean),
    ['Queda recente: Alerta moderado quando a queda for de pelo menos', 'Queda recente: médicos e',
      'Queda recente: % do que havia, e for rara: em territórios do mesmo porte, só 1 em cada']);
  // Com os nomes de outra base, nenhuma frase traz "médicos".
  const outra = D.criteriosEmFrases(ENF);
  assert.deepEqual([outra[0].titulo, outra[6].titulo], ['Poucos enfermeiros ou nenhum', 'Menos enfermeiros por habitante']);
  assert.ok(!JSON.stringify(outra).includes('médico'));
  assert.match(emTexto(outra.find(criterio => criterio.sinal === 'perda').frases[0]), /pelo menos \[perda\.moderado_minimo\] enfermeiros e/);
  // Só o que difere do padrão vai no pedido (a configuração exploratória).
  const padrao = {perda: {moderado_um_em: 20, moderado_minimo: 2}, patamar: {moderado: 15}};
  assert.equal(D.parametrosPersonalizados(padrao, {perda: {moderado_um_em: 20, moderado_minimo: 2}, patamar: {moderado: 15}}), null);
  assert.deepEqual(D.parametrosPersonalizados(padrao, {perda: {moderado_um_em: 10, moderado_minimo: 2}, patamar: {moderado: 15}}), {perda: {moderado_um_em: 10}});
  assert.deepEqual(D.parametrosPersonalizados(padrao, {patamar: {moderado: 20, outro: 3}}), {patamar: {moderado: 20}}, 'campo desconhecido não vai');
  // Na tela: os campos dentro das frases, o aviso de configuração exploratória e "Voltar ao padrão" sempre à vista.
  const tela = ler('DetectorDeSinais.tsx');
  assert.match(tela, /data-testid=\{"detector-parametro-" \+ parte\.grupo \+ "-" \+ parte\.campo\}/);
  assert.match(tela, /data-testid="detector-voltar-ao-padrao"[^>]*disabled=\{!resposta\?\.exploratorio && !comRascunho\}/);
  assert.match(tela, /data-testid="detector-exploratorio"[\s\S]{0,200}Configuração exploratória\./);
});

test('a régua da data em palavras: a partir de que mudança ela é rara, ou "sem comparações suficientes", com os números', () => {
  const lida = D.normalizarDetector(resposta([]));
  const [pequenos, grandes] = lida.calibracao.perda;
  assert.deepEqual(['moderado', 'elevado', 'critico'].map(nivel => D.textoDoCorte(pequenos, nivel)),
    ['queda maior que 33,3%', 'queda maior que 50,0%', 'queda maior que 100,0%']);
  // De 3.000 para cima, a base não tem 999 comparações de tamanho parecido: o crítico fica "sem comparações suficientes".
  assert.deepEqual(['moderado', 'elevado', 'critico'].map(nivel => D.textoDoCorte(grandes, nivel)),
    ['qualquer queda', 'queda maior que 7,6%', 'sem comparações suficientes (203 de 999)']);
  assert.deepEqual(['moderado', 'elevado', 'critico'].map(nivel => D.textoDoCorte(lida.calibracao.patamar[0], nivel, 'afastamento')),
    ['—', 'afastamento maior que 39,5%', 'afastamento maior que 62,2%']);
});

test('exportações: o CSV da lista e o método em JSON levam o alerta, a janela, as versões e a configuração', () => {
  const lida = D.normalizarDetector(resposta([linha({rotulo: 'A; "B"', alerta: alerta('elevado', 'perda', 'comparado com a base', 'Caiu de 12 para 7 (−41,5%)'),
    perda: {estado: 'alerta', classe: 'elevado', delta: -5, pct: -41.5, de: '202401', ate: '202406', magnitude: 'critico', motivo: null, verificar: null},
    registro: {estado: 'verificar_registro', tipos: ['queda_grande']}})], {exploratorio: true}));
  const csv = D.csvDoDetector(lida, lida.linhas);
  assert.ok(csv.startsWith('﻿Identificador;Território;Tipo;Grupo;Janela: início;Janela: fim;Alerta;Tipo de critério;Por quê;Sinais com nível;'));
  const [cabecalho, dados] = csv.slice(1).trim().split('\r\n');
  const colunas = cabecalho.split(';');
  assert.equal(new Set(colunas).size, colunas.length, 'nenhum cabeçalho repetido');
  assert.ok(dados.startsWith('code:130260;"A; ""B""";município;AM;201401;202406;Elevado;comparado com a base;Caiu de 12 para 7 (−41,5%);Queda recente: Elevado;;;' +
    '202406;12;10 a 19;'), dados);
  assert.ok(dados.includes(';1,24;Elevado;202401;202406;-5;-41,5;alerta;;;11,5;4,3;sem_sinal;verificar_registro;queda_grande;'), dados);
  assert.ok(dados.endsWith(';exploratória (critérios diferentes do padrão);DETECTOR-SINAIS/V3/1;abc'));
  assert.deepEqual(colunas.slice(-3), ['Configuração', 'Versão do método', 'Versão da base']);
  // Com os nomes de outra base, os cabeçalhos são os dela.
  const outra = D.normalizarDetector(resposta([linha()], {fonte: {...resposta([]).fonte, rotulos: ENF}}));
  const cabecalhoDaOutra = D.csvDoDetector(outra, outra.linhas).slice(1).split('\r\n')[0];
  assert.ok(cabecalhoDaOutra.includes(';Enfermeiros;Faixa de porte;Poucos enfermeiros: nível;') && !cabecalhoDaOutra.includes('édico'), cabecalhoDaOutra);
  const metodo = JSON.parse(D.metodoDoDetector(lida));
  assert.equal(metodo.ferramenta, 'Detector de Sinais Territoriais');
  assert.deepEqual([metodo.versao_do_metodo, metodo.janela.fim, metodo.parametros.personalizados, metodo.fonte.categoria, metodo.configuracao, metodo.referencia],
    ['DETECTOR-SINAIS/V3/1', '202406', false, 'MEDICINA', 'exploratória (critérios diferentes do padrão)', 'Docs/DETECTOR_E_SIMULADOR_V3.md, Partes A e B']);
  assert.deepEqual([metodo.regua_na_data.perda[0].comparacoes, metodo.niveis.length, 'regua_dos_estados_na_data' in metodo], [6572, 3, false]);
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

// ------------------------------------------------------------------------------------------------ mapa, gráfico e Simulador
const SEM_CONTEXTO = {distancia_km: null, referencia: null, referencia_id: null, percentil: null};
const relativo = (estado, classe = null) => ({disponibilidade: {estado, classe, taxa: 2.34, populacao: 2063689, variacao_pct: null},
  posicao: {estado, classe, percentil: 71.4, universo: 5570, variacao_pp: null}, defasagem: {estado, classe, indice: 260.9, variacao_pontos: null}});
/** Cinco territórios, como o motor os devolve: um município com alerta elevado (a mesma queda em três sinais), um com alerta
 * moderado por convenção e distância a mostrar, um estado como unidade sem comparações suficientes, um conjunto (sem nível) e um
 * município sem alerta e sem os campos dos sinais 8 a 12. */
const comparada = () => D.normalizarDetector(resposta([
  linha({id: 'code:350530', rotulo: 'BARRA BONITA (SP)', uf: 'SP', sinais: ['perda', 'disponibilidade', 'posicao', 'defasagem'],
    alerta: alerta('elevado', 'disponibilidade', 'comparado com a base', '−36,2% de médicos por habitante em 2 anos (+2 sinais)', {outros: 2,
      sinais: [{sinal: 'disponibilidade', nivel: 'elevado', criterio: 'comparado com a base'}, {sinal: 'defasagem', nivel: 'moderado', criterio: 'comparado com a base'},
        {sinal: 'posicao', nivel: 'moderado', criterio: 'comparado com a base'}], mesma_queda: ['disponibilidade', 'defasagem', 'posicao']}),
    disponibilidade: {estado: 'classificado', classe: 'elevado', taxa: 3.0727, populacao: 36125, variacao_pct: -36.205},
    posicao: {estado: 'classificado', classe: 'moderado', percentil: 86.29, universo: 5570, variacao_pp: -11.526},
    defasagem: {estado: 'classificado', classe: 'moderado', indice: 72.887, variacao_pontos: -55.21},
    contexto: {estado: 'atende_ao_criterio', ...SEM_CONTEXTO}, coexistencia: {estado: 'sem_combinacao', combinacoes: [], textos: [], repercussoes: 3}}),
  linha({sinais: ['patamar', 'registro'], ...relativo('sem_sinal'),
    alerta: alerta('moderado', 'patamar', 'por convenção', '18% abaixo do que já teve (patamar de 15)'),
    patamar: {estado: 'classificado', classe: 'moderado', patamar: 14.6, diferenca_pct: -17.8, abaixo: true},
    registro: {estado: 'verificar_registro', tipos: ['queda_grande']},
    disponibilidade: {estado: 'sem_sinal', classe: null, taxa: 1.8135, populacao: 2255903, variacao_pct: 12.45},
    contexto: {estado: 'contexto', distancia_km: 423.514, referencia: 'JACAREACANGA (PA)', referencia_id: 'code:150375', percentil: 98.27},
    coexistencia: {estado: 'sem_combinacao', combinacoes: [], textos: [], repercussoes: 1}}),
  linha({id: 'uf:15', tipo: 'estado', nivel: 'estados', rotulo: 'Pará (PA)', uf: 'PA', ultima: {competencia: '202406', valor: 8500, na_data: true},
    alerta: {...SEM_ALERTA, estado: 'sem_comparacoes', sem_comparacoes: ['perda']}, ...relativo('comparacao_nao_habilitada'),
    contexto: {estado: 'nao_aplicavel', ...SEM_CONTEXTO}}),
  linha({id: 'c1', tipo: 'conjunto', rotulo: 'Par', uf: null, membros: 2, ids_dos_membros: ['code:110001', 'code:999999'],
    ultima: {competencia: '202406', valor: 40, na_data: true},
    alerta: {...SEM_ALERTA, estado: 'sem_nivel', motivo: 'Um conjunto não tem outros iguais para comparar: a tela mostra os fatos, sem nível.'},
    disponibilidade: {estado: 'nivel_sem_classificacao', classe: null, taxa: 0.5, populacao: 20000, variacao_pct: -50},
    posicao: {estado: 'nao_aplicavel', classe: null, percentil: null, universo: null, variacao_pp: null},
    defasagem: {estado: 'nivel_sem_classificacao', classe: null, indice: 40.04, variacao_pontos: -3.26},
    contexto: {estado: 'contexto', distancia_km: 88.04, referencia: 'PORTO VELHO (RO)', referencia_id: 'code:110020', percentil: null}}),
  linha({id: 'code:110001', rotulo: 'ALTA FLORESTA (RO)', uf: 'RO', ultima: {competencia: '202406', valor: 3, na_data: true}})], {
  janela: {inicio: '201401', fim: '202106', registros: 16, meses: 89, padrao: false, ultimo_registro_da_base: '202406', e_o_ultimo: false},
  comparacao: {de: '201906', ate: '202106', estado: 'comparavel', trechos: [[2014, 2024]], minimo_de_medicos: 20,
    contexto: {taxa_minima: 1.9834, taxa_do_brasil: 1.9834, pct_da_taxa_do_brasil: 100, atendem: 1720, universo: 3846}},
  coordenadas: {'code:130260': [-3.1, -60.0], 'code:150375': [-6.2, -57.7], 'code:350530': [-22.5, -48.6], 'code:110001': [-11.9, -62.0], x: [1]}}));

test('sinais 8 a 12: a linha, a janela de comparação e as coordenadas vêm do motor', () => {
  const lida = comparada();
  const [barra, manaus, , par, semDados] = lida.linhas;
  assert.deepEqual([barra.disponibilidade, barra.posicao, barra.defasagem], [
    {estado: 'classificado', classe: 'elevado', taxa: 3.0727, populacao: 36125, variacaoPct: -36.205},
    {estado: 'classificado', classe: 'moderado', percentil: 86.29, universo: 5570, variacaoPp: -11.526},
    {estado: 'classificado', classe: 'moderado', indice: 72.887, variacaoPontos: -55.21}]);
  assert.deepEqual(manaus.contexto, {estado: 'contexto', distanciaKm: 423.514, referencia: 'JACAREACANGA (PA)', referenciaId: 'code:150375', percentil: 98.27});
  assert.deepEqual(par.idsDosMembros, ['code:110001', 'code:999999']);
  // Uma linha sem os campos dos sinais 8 a 12 não derruba a tela nem inventa valor.
  assert.deepEqual([semDados.disponibilidade.taxa, semDados.posicao.percentil, semDados.defasagem.indice, semDados.contexto.distanciaKm,
    semDados.coexistencia.textos, semDados.idsDosMembros], [null, null, null, null, [], []]);
  assert.deepEqual(lida.comparacao, {de: '201906', ate: '202106', estado: 'comparavel', minimoDeMedicos: 20, trechos: [[2014, 2024]], motivo: null,
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
  assert.deepEqual([D.criterioDoContexto(2.3638), D.criterioDoContexto(null), D.criterioDoContexto(2.3638, ENF)],
    ['município mais próximo com 2,36 médicos por 1.000 habitantes ou mais', null, 'distrito mais próximo com 2,36 enfermeiros por 1.000 habitantes ou mais']);
  assert.deepEqual([D.formatarTaxa(3.0727), D.formatarTaxa(2), D.formatarTaxa(1234.5)], ['3,07', '2,00', '1.234,50']);
});

test('mapa e gráfico pelos níveis: só os valores, os níveis e as coordenadas do motor', () => {
  const lida = comparada();
  const [barra] = lida.linhas;
  // O mapa: cada município com ponto, pelo nível do alerta (os sem nível, no fundo); o conjunto, pelo contorno dos componentes com
  // ponto; o nome de cada grupo de cima junto aos pontos dele. O estado como unidade não tem ponto.
  const grupos = [{id: 'grupo:SP', nome: 'SP', membros: ['code:350530']}, {id: 'grupo:AM', nome: 'AM', membros: ['code:130260']},
    {id: 'grupo:RO', nome: 'RO', membros: ['code:110001']}];
  const conjuntos = [{id: 'c1', nome: 'Par', membros: ['code:110001']}];
  assert.deepEqual(D.camadasDoMapa(lida, lida.linhas, 'todos'), {fundo: ['code:110001'],
    porNivel: {critico: [], elevado: ['code:350530'], moderado: ['code:130260']}, conjuntos, grupos});
  // Com o filtro "Sinal", o nível é o daquele sinal no território (não o do alerta).
  assert.deepEqual(D.camadasDoMapa(lida, lida.linhas, 'posicao'), {fundo: ['code:130260', 'code:110001'],
    porNivel: {critico: [], elevado: [], moderado: ['code:350530']}, conjuntos, grupos});
  assert.deepEqual(D.camadasDoMapa(lida, [barra], 'disponibilidade'), {fundo: [], porNivel: {critico: [], elevado: ['code:350530'], moderado: []}, conjuntos: [],
    grupos: [grupos[0]]});
  assert.deepEqual(lida.linhas.map(item => [D.nivelNoDesenho(item, 'todos'), D.nivelNoDesenho(item, 'patamar'), D.nivelNoDesenho(item, 'juntos')]),
    [['elevado', null, 'elevado'], ['moderado', 'moderado', 'moderado'], [null, null, null], [null, null, null], [null, null, null]]);
  // As cores dos níveis: amarelo, laranja e vermelho, os passos de estado (aviso, sério e crítico); o nível vem sempre escrito.
  assert.deepEqual(D.CORES_DOS_NIVEIS, {moderado: '#fab219', elevado: '#ec835a', critico: '#d03b3b'});
  const graficos = ler('DetectorGraficos.tsx');
  assert.match(graficos, /data-testid="detector-legenda-niveis"/);
  assert.match(graficos, /\{NOMES_DOS_NIVEIS\[nivel\]\}: \{formatarInteiro\(contagens\[nivel\]\)\}/, 'a legenda diz o nível por extenso');
  // As bolhas do Agente: X = a distância até o mais próximo que atende ao critério; Y = a taxa; o tamanho, a população.
  const itens = D.itensDoContexto(lida.linhas);
  assert.deepEqual(itens.map(item => [item.id, item.tipo, item.distancia_km, item.densidade, item.populacao, item.quantidade]),
    [['code:130260', 'municipio', 423.514, 1.8135, 2255903, 12], ['c1', 'conjunto', 88.04, 0.5, 20000, 40]], 'só as linhas com distância a mostrar');
  assert.deepEqual([itens[0].referenciaDoItem, itens[1].membros, itens[1].contagem, itens[0].avaliavel],
    [[{id: 'code:150375', rotulo: 'JACAREACANGA (PA)'}], ['code:110001', 'code:999999'], 'SOMA_DOS_COMPONENTES', {densidade: true, distancia: true, variacao: null}]);
  assert.deepEqual(D.dominiosDoContexto(itens), {densidade: [0.5, 1.8135], distancia_km: [88.04, 423.514], populacao: [20000, 2255903], quantidade: [12, 40]});
  assert.deepEqual(D.dominiosDoContexto([]), {densidade: null, distancia_km: null, populacao: null, quantidade: null});
  // A série da taxa do território e a da referência dele (tracejada), para a Série temporal do Agente; a ausência não vira zero.
  const detalhe = D.normalizarDetalhe({territorio: {id: 'code:350530', rotulo: 'BARRA BONITA (SP)', tipo: 'municipio', unidade: 'médicos'}, janela: resposta([]).janela,
    comparativo: {competencias: ['201906', '202006', '202106'], taxa: [4.8, null, 3.07], indice: [128.1, null, 72.9], trechos: [[2014, 2024]],
      referencia: {rotulo: 'demais municípios de São Paulo (soma municipal)', motivo: null, taxa: [3.75, 4.0, 4.21]}}});
  assert.deepEqual(detalhe.comparativo, {competencias: ['201906', '202006', '202106'], taxa: [4.8, null, 3.07], indice: [128.1, null, 72.9],
    trechos: [[2014, 2024]], referencia: {rotulo: 'demais municípios de São Paulo (soma municipal)', motivo: null, taxa: [3.75, 4, 4.21]}});
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

test('o que o Detector leva ao Simulador: o território, a data, a janela escolhida e os sinais com nível', () => {
  const lida = comparada();
  const [barra, , , par] = lida.linhas;
  // "Abrir no Simulador" e "Simular recuperação": os sinais com nível, pelos nomes da tela, e a janela só quando a pessoa a
  // escolheu (a janela padrão do Detector, a série inteira, não é levada).
  assert.deepEqual(D.alvoDoSimulador(barra, lida), {id: 'code:350530', tipo: 'municipio', rotulo: 'BARRA BONITA (SP)',
    sinais: ['Menos médicos por habitante (elevado)', 'Mais longe da referência (moderado)', 'Perda de posição (moderado)'], fim: '202106',
    janela: {inicio: '201401', fim: '202106'}, exploratorio: false});
  assert.deepEqual(D.alvoDoSimulador(par, {janela: {...lida.janela, padrao: true}, exploratorio: true}), {id: 'c1', tipo: 'conjunto', rotulo: 'Par',
    sinais: [], fim: '202106', janela: null, exploratorio: true});
  // "Simular recuperação" só existe para quem está abaixo do patamar: acima dele, não há o que recuperar.
  const comPatamar = (patamar, diferenca_pct) => D.normalizarDetector(resposta([linha({patamar: {estado: 'descritivo', classe: null, patamar, diferenca_pct,
    abaixo: diferenca_pct < 0}})])).linhas[0];
  assert.deepEqual([comPatamar(78.25, -30.99), comPatamar(4086, 15.76), comPatamar(12, 0), comPatamar(null, null)].map(D.patamarARecuperar), [78.25, null, null, null]);
});

test('"Entenda": abre com o mouse, com um toque e pelo teclado; fecha ao sair; a explicação inteira fica em "Ver explicação completa"', () => {
  const codigo = ler('Entenda.tsx');
  // Mouse: abre ao passar por cima e fecha ao sair (com uma folga para chegar à caixa). Toque e teclado: o botão abre e fixa.
  assert.match(codigo, /onMouseEnter=\{abrir\}/);
  assert.match(codigo, /onMouseLeave=\{\(\) => \{ if \(fixo\) return;/);
  assert.match(codigo, /onFocus=\{\(\) => \{[\s\S]{0,120}abrir\(\); \}\}/);
  assert.match(codigo, /onClick=\{\(\) => \{ if \(aberto && fixo\) fechar\(\); else \{ setFixo\(true\); abrir\(\); \} \}\}/);
  // Fecha ao sair: o foco deixa o bloco, Esc ou um toque fora.
  assert.match(codigo, /onBlur=\{evento => \{ if \(!bloco\.current\?\.contains\(evento\.relatedTarget as Node \| null\)\) fechar\(\); \}\}/);
  assert.match(codigo, /evento\.key !== "Escape"/);
  assert.match(codigo, /document\.addEventListener\("pointerdown", fora\)/);
  // Acessível: um botão de verdade, com o estado e o nome do que explica; a caixa não é cortada pela rolagem das tabelas.
  assert.match(codigo, /<button ref=\{botao\} type="button"[^>]*aria-expanded=\{aberto\} aria-controls=\{id\}\s+aria-label=\{"Entenda: " \+ sobre\}/);
  assert.match(codigo, /role="note"/);
  assert.match(codigo, /<strong>Exemplo:<\/strong> \{exemplo\}/);
  assert.match(codigo, /onClick=\{\(\) => \{ fechar\(\); onCompleta\(\); \}\}>Ver explicação completa<\/button>/);
  assert.match(ler('analise.css'), /\.entenda-caixa \{ position: fixed;[^}]*width: min\(360px, calc\(100vw - 24px\)\)/, 'cabe na largura do celular');
  // Na tela do Detector: o "Entenda" da ferramenta, o do alerta, o dos termos da lista e o de cada sinal, com os textos do motor.
  const tela = ler('DetectorDeSinais.tsx');
  for (const testid of ['detector-entenda-ferramenta', 'detector-entenda-alerta', 'detector-entenda-termos', 'detector-entenda'])
    assert.ok(tela.includes('testid="' + testid + '"'), testid);
  assert.match(tela, /<Entenda sobre=\{sinal\.nome\} texto=\{sinal\.entenda\.texto\} exemplo=\{sinal\.entenda\.exemplo\}/);
});
