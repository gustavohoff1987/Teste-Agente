import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name, ajustar = code => code) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(ajustar(code)).toString('base64'));
}
// Área de análise (23/10/2026): os ajustes dentro de cada análise, a vista do desenho (gráfico, mapa ou lado a lado), as decisões
// puras do mapa (disponibilidade com o motivo, pintura com os quintis do motor, cor contínua, tamanho e ligações), o estado salvo
// com a vista, o aspecto "mapa" dos não avaliáveis, a frase-resumo do motor, os dados do mapa no cliente, os nomes das abas, a
// apresentação de cada aba e as explicações da tendência (painelModel.ts e painelApi.ts, com a sessão substituída por um esboço:
// os testes não fazem pedidos).
const M = await source('painelModel');
const A = await source('painelApi', code => code.replace(/import\s*\{[^}]*\}\s*from\s*["']\.\/conversationSession["'];?/,
  'const contextRevision = () => 0; const fetch = globalThis.fetch;'));

const VAZIO = {populacao: null, quantidade: null, densidade: null};
const municipio = (id, rotulo, valores = {}) => ({id, tipo: 'municipio', rotulo, uf: rotulo.slice(-3, -1), populacao: 1000, quantidade: 10,
  densidade: 10, distancia_km: null, inicial: {...VAZIO}, variacao_percentual: {...VAZIO},
  avaliavel: {densidade: true, distancia: null, variacao: null}, motivos: [], referencia: false, ...valores});
const SEM_REGISTRO = 'Sem registro em junho de 2024 na categoria MEDICINA: valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)';
const SEM_PONTO = 'Sem coordenada válida da sede municipal na competência (SEM_INFORMACAO_ESPACIAL)';
const BR = M.ROTULOS_BRASIL;
const DISTRITOS = {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}};
const definicao = (extra = {}) => ({...M.definicaoInicial({tipo: 'brasil', periodos: ['202306', '202406'], categoria: 'MEDICINA', temGrupos: true}), ...extra});
const resposta = (extra = {}) => ({competencia: '202406', competencia_inicial: null, categoria: 'MEDICINA', versao_base: 'v1', chave_execucao: 'k1',
  nivel: 'municipios', referencia: null, itens: [], dominios: {}, notas: ['Nota do motor.'], limitacoes: [], tendencia: null, grupos: null,
  faixas: null, faixasDistancia: null, condicoes: null, ordenacao: null, comparacao: null, contextoBrasil: null, disponibilidade: {}, sessao: null,
  rotulos: null, indicador: 'densidade', resumo: null, ...extra});

test('ajustes dentro da análise: cada aba só com os seus; o mesmo indicador em todas, menos na rotatividade; nos estados, os da distribuição', () => {
  const a = extra => M.ajustesDaAnalise({familia: 'distribuicao', nivel: 'municipios', disponivel: true, categorias: 1, ...extra});
  assert.deepEqual(a({}), ['indicador', 'competencia', 'agrupar']);
  assert.deepEqual(a({categorias: 2}), ['indicador', 'categoria', 'competencia', 'agrupar']);  // a categoria junto do indicador
  assert.deepEqual(a({familia: 'espacial'}), ['indicador', 'competencia', 'referencia']);
  assert.deepEqual(a({familia: 'tendencia', categorias: 3}), ['indicador', 'categoria', 'janela', 'visao']);
  assert.deepEqual(a({familia: 'rotatividade'}), ['periodos']);
  assert.deepEqual(a({familia: 'rotatividade', categorias: 2}), ['periodos', 'categoria']);
  // O indicador é um só (fica na definição): a escolha acompanha a pessoa em todas as abas que o têm, sempre à vista e em primeiro.
  for (const familia of ['distribuicao', 'espacial', 'tendencia']) assert.equal(a({familia})[0], 'indicador');
  // Nos estados e no Brasil (24/10/2026), a distribuição e a tendência valem; a espacial espera municípios (os ajustes da
  // distribuição). Com o Brasil, uma unidade só, sem grupos nem faixas.
  for (const familia of ['distribuicao', 'espacial']) assert.deepEqual(a({familia, nivel: 'estados'}), ['indicador', 'competencia', 'agrupar']);
  assert.deepEqual(a({familia: 'tendencia', nivel: 'estados'}), ['indicador', 'janela', 'visao']);
  for (const familia of ['distribuicao', 'espacial', 'rotatividade']) assert.deepEqual(a({familia, nivel: 'brasil'}), ['indicador', 'competencia']);
  assert.deepEqual(a({familia: 'tendencia', nivel: 'brasil'}), ['indicador', 'janela', 'visao']);
  assert.deepEqual(a({familia: 'rotatividade', disponivel: false}), ['indicador', 'competencia', 'agrupar']);
  // A escala não é ajuste da análise: fica junto do desenho.
  for (const familia of ['distribuicao', 'espacial', 'tendencia', 'rotatividade']) assert.ok(!a({familia}).includes('escala'));
  assert.equal(M.TEXTO_SEM_POPULACAO, 'Sem população na planilha: só a quantidade.');
});

test('vista do desenho: o mapa nos municípios; desligado nos estados (com o atalho), na planilha sem coordenadas e em Séries, com o motivo', () => {
  const d = extra => M.disponibilidadeDoMapa({fonte: 'brasil', temCoordenadas: true, nivel: 'municipios', series: false, rotatividade: false,
    rotulos: BR, ...extra});
  assert.deepEqual(d({}), {disponivel: true, motivo: null, atalho: null});
  // Os estados não têm um ponto (os ladrilhos não foram aprovados): o atalho leva aos municípios no mapa.
  assert.deepEqual(d({nivel: 'estados'}), {disponivel: false, atalho: 'Ver os municípios no mapa',
    motivo: 'Os estados não têm um ponto no mapa: cada ponto do mapa é um município.'});
  const semColunas = d({fonte: 'arquivo', temCoordenadas: false, rotulos: DISTRITOS});
  assert.equal(semColunas.disponivel, false);
  assert.equal(semColunas.atalho, null);
  assert.equal(semColunas.motivo, 'A planilha não tem as colunas de latitude e longitude: o mapa precisa das coordenadas de cada distrito. ' +
    'A tabela continua.');
  assert.ok(d({fonte: 'arquivo', temCoordenadas: false, rotatividade: true, rotulos: DISTRITOS}).motivo
    .startsWith('Sem latitude e longitude na planilha, a rotatividade fica nas barras'));
  assert.equal(d({fonte: 'arquivo', temCoordenadas: true, rotatividade: true, rotulos: DISTRITOS}).disponivel, true);
  const series = d({series: true});
  assert.equal(series.disponivel, false);
  assert.equal(series.motivo, 'Na visão Série temporal, cada município é uma linha no tempo: o mapa fica com Tendência e Trajetória.');
  // Numa planilha com grupos, os nomes da planilha.
  assert.deepEqual(d({fonte: 'arquivo', nivel: 'estados', rotulos: DISTRITOS}), {disponivel: false, atalho: 'Ver os distritos no mapa',
    motivo: 'As províncias não têm um ponto no mapa: cada ponto do mapa é um distrito.'});
  assert.equal(d({fonte: null}).disponivel, false);
  assert.equal(M.LARGURA_LADO_A_LADO, 1600);
});

test('pintura do mapa: a camada do gráfico, a cor contínua da rotatividade ou os 5 grupos iguais (quintis) do motor, sem pergunta', () => {
  const p = extra => M.pinturaDoMapa({camada: 'unica', rotatividade: false, gruposDoMapa: true, ...extra});
  assert.equal(p({}), 'quintis');  // sem cor própria da análise, os quintis que o motor devolveu em grupos_mapa
  assert.equal(p({gruposDoMapa: false}), 'camada');  // sem eles (uma análise guardada antes), a cor única do gráfico
  for (const camada of ['grupos', 'faixas', 'condicoes', 'ordem', 'classes', 'variacao']) {
    assert.equal(p({camada}), 'camada');  // a camada em uso no gráfico vale também no mapa
    assert.equal(p({camada, gruposDoMapa: false}), 'camada');
  }
  assert.equal(p({rotatividade: true}), 'continua');
  assert.equal(M.opcoesDePintura, undefined);  // a pergunta "Como pintar o mapa?" saiu (23/10/2026)
  // O pedido leva os quintis do mapa só quando a análise não tem cor própria e o mapa está disponível.
  const d = extra => definicao({base: {todos: false, estados: ['13'], ids: []}, ...extra});
  const q = (def, familia = 'distribuicao', mapa = true) => M.precisaQuintisDoMapa(def, familia, mapa);
  assert.equal(q(d()), true);
  assert.equal(q(d(), 'espacial'), true);  // a distância nunca pinta o mapa (RQ-REP-02): os quintis do indicador
  assert.equal(q(d(), 'tendencia'), false);  // as classes já pintam
  assert.equal(q(d(), 'rotatividade'), false);  // a permanência já pinta
  assert.equal(q(d(), 'distribuicao', false), false);  // sem mapa (planilha sem coordenadas, visão Séries)
  assert.equal(q(d({nivel: 'estados'})), false);
  assert.equal(q(d({agrupar: {tipo: 'quartis', faixas: []}})), false);
  assert.equal(q(d({agrupar: {tipo: 'faixas', faixas: [1, 2]}})), false);
  assert.equal(q(d({agrupar: {tipo: 'faixas', faixas: [1]}})), true);  // faixas incompletas não pintam o gráfico
  assert.equal(q(d({condicoes: [{atributo: 'densidade', operador: '>', valor: 1}]})), false);
  assert.equal(q(d({ordenar: {atributo: 'densidade', ordem: 'desc'}})), false);
  const opcoes = M.montarOpcoes(d(), 'distribuicao', undefined, {quintisDoMapa: true});
  assert.deepEqual(opcoes.grupos_mapa, {tipo: 'quintis'});
  assert.equal(opcoes.grupos, undefined);  // o gráfico continua sem grupos
  assert.equal(M.montarOpcoes(d(), 'distribuicao').grupos_mapa, undefined);
  // Com os quintis do mapa, o indicador muda a resposta: a troca do indicador pede de novo; a troca da vista, não.
  assert.equal(M.pedidoDependeDoIndicador(opcoes), true);
  assert.equal(M.pedidoDependeDoIndicador(M.montarOpcoes(d(), 'distribuicao')), false);
  assert.notEqual(M.chaveDoPedido(opcoes), M.chaveDoPedido({...opcoes, indicador: 'quantidade'}));
  // Cor contínua: o indicador no domínio do motor, ou a permanência da coorte inicial de 0 a 100%.
  const dominios = {densidade: [0.5, 15], quantidade: [1, 105], populacao: [1000, 9000]};
  const cor = M.corContinuaDoMapa({rotatividade: false, indicador: 'densidade', dominios});
  assert.deepEqual([cor.rotulo, cor.dominio], ['Densidade (por 1.000 habitantes)', [0.5, 15]]);
  assert.equal(cor.valor(municipio('code:1', 'A (AM)', {densidade: 2.5})), 2.5);
  assert.equal(cor.valor(municipio('code:1', 'A (AM)', {densidade: null})), null);
  assert.equal(M.corContinuaDoMapa({rotatividade: false, indicador: 'quantidade', dominios}).rotulo, 'Quantidade (profissionais)');
  const permanencia = M.corContinuaDoMapa({rotatividade: true, indicador: 'densidade', dominios});
  assert.deepEqual([permanencia.rotulo, permanencia.dominio], ['Permanência da coorte inicial (%)', [0, 100]]);
  assert.equal(permanencia.valor(municipio('code:2', 'B (AM)', {rotatividade: {coorteInicial: 120, permanencia: 72.5}})), 72.5);
  // Tamanho (área proporcional): população na densidade, quantidade na quantidade, coorte inicial na rotatividade.
  const populacao = M.tamanhoDoMapa({rotatividade: false, indicador: 'densidade', dominios});
  assert.deepEqual([populacao.rotulo, populacao.maximo, populacao.valor(municipio('code:1', 'A (AM)', {populacao: 1234}))], ['População', 9000, 1234]);
  const quantidade = M.tamanhoDoMapa({rotatividade: false, indicador: 'quantidade', dominios});
  assert.deepEqual([quantidade.rotulo, quantidade.maximo, quantidade.valor(municipio('code:1', 'A (AM)', {quantidade: 7}))],
    ['Quantidade de profissionais', 105, 7]);
  const coorte = M.tamanhoDoMapa({rotatividade: true, indicador: 'densidade', dominios});
  assert.deepEqual([coorte.rotulo, coorte.maximo, coorte.valor(municipio('code:2', 'B (AM)', {rotatividade: {coorteInicial: 120}}))],
    ['Coorte inicial', null, 120]);
});

test('ligações ilustrativas do mapa: só das unidades selecionadas, até a referência mais próxima do motor (com o empate), até 30', () => {
  const manaus = {id: 'code:130260', rotulo: 'MANAUS (AM)'};
  const itens = [municipio('code:130260', 'MANAUS (AM)', {referencia: true}),
    municipio('code:130420', 'TEFE (AM)', {referenciaDoItem: [manaus]}),
    municipio('code:130340', 'PARINTINS (AM)', {referenciaDoItem: [manaus, {id: 'code:130185', rotulo: 'IRANDUBA (AM)'}]}),
    municipio('code:350010', 'FORA (SP)', {referenciaDoItem: null}),
    {...municipio('c1', 'Interior'), tipo: 'conjunto', referenciaDoItem: [manaus]}];
  assert.deepEqual(M.ligacoesDoMapa(itens, ['code:130340', 'code:130260', 'code:350010', 'c1', 'code:130420']),
    [{de: 'code:130340', para: ['code:130260', 'code:130185']}, {de: 'code:130420', para: ['code:130260']}]);
  assert.deepEqual(M.ligacoesDoMapa(itens, []), []);
  const muitos = Array.from({length: 40}, (_, i) => municipio('code:' + (100000 + i), 'M' + i + ' (AM)', {referenciaDoItem: [manaus]}));
  assert.equal(M.MAX_LIGACOES, 30);
  assert.equal(M.ligacoesDoMapa(muitos, muitos.map(item => item.id)).length, 30);
});

test('Histórico: a vista do desenho e a cor contínua entram no estado salvo; o estado de antes, sem os campos, continua legível', () => {
  const def = definicao({nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}});
  const corpo = resposta();
  const salvo = M.salvarEstado('Densidade de médicos', {chave: 'k', familia: 'distribuicao', opcoes: {competencia: '202406', categoria: 'MEDICINA'},
    definicao: def, visual: {escala: 'linear', corte: null, selecionados: [], vista: 'mapa', corContinua: true}}, corpo, '2026-10-23T12:00:00.000Z');
  const lido = M.lerEstadoSalvo(salvo);
  assert.deepEqual(lido.visual, {escala: 'linear', corte: null, selecionados: [], vista: 'mapa', corContinua: true});
  assert.deepEqual(lido, {...salvo.definicao, resposta: corpo});
  const lado = M.salvarEstado('T', {...salvo.definicao, visual: {...salvo.definicao.visual, vista: 'lado'}}, corpo);
  assert.equal(M.lerEstadoSalvo(lado).visual.vista, 'lado');  // numa janela estreita, a área troca pelo mapa
  // Estado de antes de 23/10, sem vista nem cor: reabre sem os campos (a área mostra o gráfico).
  const antigo = {titulo: 'T', quando: '', resposta: corpo, definicao: {versao: 1, chave: 'k', familia: 'distribuicao', opcoes: null, definicao: def,
    visual: {escala: 'logaritmica', corte: null, selecionados: ['code:130260']}}};
  assert.deepEqual(M.lerEstadoSalvo(antigo).visual, {escala: 'logaritmica', corte: null, selecionados: ['code:130260']});
  // Valores estranhos ficam de fora, sem derrubar o estado.
  const estranho = {...antigo, definicao: {...antigo.definicao, visual: {...antigo.definicao.visual, vista: 'tela-cheia', corContinua: 'sim'}}};
  assert.deepEqual(M.lerEstadoSalvo(estranho).visual, {escala: 'logaritmica', corte: null, selecionados: ['code:130260']});
});

test('não avaliáveis no mapa: com o mapa à vista, a unidade sem coordenada válida entra à parte, com o motivo do motor, e continua no gráfico', () => {
  const itens = [municipio('code:130420', 'TEFE (AM)'), municipio('code:130260', 'MANAUS (AM)'),
    municipio('code:130185', 'IRANDUBA (AM)', {populacao: null, quantidade: null, densidade: null, motivos: [SEM_REGISTRO],
      avaliavel: {densidade: false, distancia: null, variacao: null}})];
  const semCoordenada = new Map([['code:130420', SEM_PONTO], ['code:130260', ''], ['code:130185', SEM_PONTO]]);
  const {plotaveis, fora} = M.separarItens(itens, 'densidade', {semCoordenada});
  assert.deepEqual(plotaveis.map(item => item.id), ['code:130260', 'code:130420']);  // no gráfico, as bolhas ficam
  assert.deepEqual(fora.map(item => [item.id, item.aspecto, item.motivo]), [['code:130185', 'indicador', SEM_REGISTRO],
    ['code:130260', 'mapa', 'Sem coordenada válida para o mapa.'], ['code:130420', 'mapa', SEM_PONTO]]);
  // Sem o mapa à vista, a lista não muda.
  assert.deepEqual(M.separarItens(itens, 'densidade', {}).fora.map(item => item.aspecto), ['indicador']);
  assert.deepEqual(M.separarItens(itens, 'densidade', {semCoordenada: null}).fora.map(item => item.aspecto), ['indicador']);
  // Na rotatividade, a coorte avaliável sem coordenada também; a não avaliável fica só com o motivo da coorte.
  const coortes = [municipio('code:3', 'C (AM)', {rotatividade: {coorteInicial: 120, permaneceram: 87, sairam: 33, permanencia: 72.5, saida: 27.5,
    avaliavel: true, motivo: null}}), municipio('code:4', 'D (AM)', {rotatividade: {coorteInicial: null, permaneceram: null, sairam: null,
    permanencia: null, saida: null, avaliavel: false, motivo: 'Não avaliável: sem registro observado em um dos períodos (SEM_REGISTRO_OBSERVADO)'}})];
  const rot = M.separarItens(coortes, 'densidade', {rotatividade: true, semCoordenada: new Map([['code:3', SEM_PONTO], ['code:4', SEM_PONTO]])});
  assert.deepEqual(rot.plotaveis.map(item => item.id), ['code:3']);
  assert.deepEqual(rot.fora.map(item => [item.id, item.aspecto]), [['code:3', 'mapa'], ['code:4', 'rotatividade']]);
  // A dica do ponto na rotatividade traz a permanência e a coorte inicial do motor.
  const dica = M.montarDica(coortes[0], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR});
  assert.ok(dica.linhas.some(linha => linha.rotulo === 'Permanência da coorte inicial' && linha.valor === '72,50%'));
  assert.ok(dica.linhas.some(linha => linha.rotulo === 'Coorte inicial' && linha.valor === '120'));
  assert.ok(M.montarDica(coortes[1], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR}).notas.some(nota => nota.endsWith('(SEM_REGISTRO_OBSERVADO)')));
});

test('conversa: "ver no mapa" e "volte ao gráfico" são estado visual; o mapa vale para a análise que resulta do pedido; nos estados, o motivo', () => {
  const c = {periodos: ['202306', '202406'], nomes: new Map(), temGrupos: true,
    disponivel: f => M.disponibilidadeDaFamilia(f, {fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR}),
    mapa: d => M.disponibilidadeDoMapa({fonte: 'brasil', temCoordenadas: true, nivel: d.nivel, series: false, rotatividade: false, rotulos: BR})};
  const estados = definicao({nivel: 'estados'});
  const noMapa = M.aplicarPedido(estados, {vista: 'mapa'}, c);
  assert.equal(noMapa.vista, null);
  assert.deepEqual(noMapa.mensagens, ['Mapa: Os estados não têm um ponto no mapa: cada ponto do mapa é um município.']);
  assert.equal(noMapa.definicao.nivel, 'estados');  // a vista não muda a análise
  const amazonas = M.aplicarPedido(estados, {municipios: {todos: false, estados: ['13'], ids: []}, vista: 'mapa'}, c);
  assert.equal(amazonas.vista, 'mapa');
  assert.deepEqual(amazonas.mensagens, []);
  assert.equal(M.aplicarPedido(estados, {vista: 'grafico'}, c).vista, 'grafico');
  assert.equal(M.aplicarPedido(estados, {}, c).vista, null);
  const {mapa, ...semConferencia} = c;
  assert.equal(M.aplicarPedido(estados, {vista: 'mapa'}, semConferencia).vista, 'mapa');
});

test('frase-resumo do motor no cliente e no arquivo de método; dados do mapa normalizados (pontos num Map, sem coordenada com o motivo)', () => {
  const bruta = {competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'quantidade', itens: [],
    resumo: {texto: '  Nos 62 municípios do Amazonas, em junho de 2024, a quantidade de médicos vai de 1 a 4.730.  '}};
  const r = A.normalizarResposta(bruta);
  assert.deepEqual(r.resumo, {texto: 'Nos 62 municípios do Amazonas, em junho de 2024, a quantidade de médicos vai de 1 a 4.730.'});
  assert.equal(r.indicador, 'quantidade');
  const antiga = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: []});
  assert.deepEqual([antiga.resumo, antiga.indicador], [null, null]);  // a resposta de antes continua legível
  assert.deepEqual(A.resumoDe('Frase do motor.'), {texto: 'Frase do motor.'});
  assert.equal(A.resumoDe({texto: '   '}), null);
  assert.equal(A.resumoDe(null), null);
  const metodo = M.textoDoMetodo(resposta({resumo: {texto: 'Frase do motor.'}}), 'Densidade de médicos', null);
  assert.deepEqual(metodo.split('\n').slice(0, 4), ['Densidade de médicos', 'Frase do motor.', '', 'Procedência']);
  assert.ok(!M.textoDoMetodo(resposta({resumo: {texto: 'Frase do motor.'}}), 'T', null, null).includes('Frase do motor.'));  // fora da tela, fora do arquivo
  assert.deepEqual(M.textoDoMetodo(resposta(), 'T', null).split('\n').slice(0, 2), ['T', '']);
  const dados = A.normalizarMapa({competencia: '202406', referencial: 'SIRGAS2000',
    pontos: [{id: 'code:130260', lat: -3.1019, lon: -60.025}, {id: 'code:130420', lat: '-3.35', lon: -64.71}, {id: 'code:1', lat: 95, lon: 0}, {lat: 1, lon: 1}],
    sem_coordenada: [{id: 'code:130185', rotulo: 'IRANDUBA (AM)', motivo: SEM_PONTO}, {rotulo: 'sem identificador'}]});
  assert.equal(dados.competencia, '202406');
  assert.equal(dados.referencial, 'SIRGAS2000');
  assert.ok(dados.pontos instanceof Map);
  assert.deepEqual([...dados.pontos.entries()], [['code:130260', [-3.1019, -60.025]]]);
  assert.deepEqual(dados.semCoordenada, [{id: 'code:130185', rotulo: 'IRANDUBA (AM)', motivo: SEM_PONTO}]);
  assert.throws(() => A.normalizarMapa({competencia: '202406'}), erro => erro instanceof A.ErroDoMotor);
});

test('nomes padronizados: a Seleção de Territórios primeiro, e as quatro análises com o nome completo', () => {
  assert.deepEqual(M.ABAS, ['territorios', 'distribuicao', 'espacial', 'tendencia', 'rotatividade']);
  assert.deepEqual(M.ABAS.map(M.nomeDaAba), ['Seleção de Territórios', 'Análise de Distribuição', 'Análise Espacial',
    'Análise de Tendência', 'Análise de Rotatividade']);
  assert.equal(M.NOME_SELECAO, 'Seleção de Territórios');  // a seleção não é uma análise
  // A orientação da Seleção, curta (24/10/2026), sem instruções sobre as caixas.
  assert.equal(M.TEXTO_DA_SELECAO, 'Escolha os territórios que entram nas análises. A seleção vale para todas elas e pode ser mudada a ' +
    'qualquer momento.');
  // A abertura: a identificação do sistema e a chamada para escolher os dados, com as duas entradas.
  assert.equal(M.TITULO_DO_SISTEMA, 'Diagnóstico Territorial da Força de Trabalho na Saúde');  // o nome da plataforma (24/10/2026)
  assert.equal(M.TEXTO_ESCOLHA_DOS_DADOS, 'Escolha seus dados para começar');
  assert.ok(!/privacidade|modelo/i.test(M.TEXTO_DAS_FONTES), M.TEXTO_DAS_FONTES);
  // A abertura não marca territórios: nada é pedido ao motor até a escolha.
  for (const tipo of ['brasil', 'arquivo']) {
    const inicial = M.definicaoInicial({tipo, periodos: ['202406'], categoria: '', temGrupos: tipo === 'brasil'});
    assert.equal(inicial.nivel, 'municipios');
    assert.deepEqual(inicial.base, {todos: false, estados: [], ids: []});
    assert.equal(M.bloqueioDoPedido(inicial, {fonte: tipo, rotulos: BR}), M.TEXTO_SEM_SELECAO);
  }
});

test('apresentação de cada aba: o que a aba faz, com os nomes territoriais da fonte e sem códigos internos', () => {
  const brasil = aba => M.apresentacaoDaAba(aba, {rotulos: BR, brasil: true, comGrupos: true});
  const planilha = aba => M.apresentacaoDaAba(aba, {rotulos: DISTRITOS, brasil: false, comGrupos: true});
  const tudo = a => [a.titulo, ...a.paragrafos, ...(a.itens || []).flatMap(item => [item.termo, item.texto]), a.nota || ''].join(' ');
  for (const aba of M.ABAS) {
    assert.equal(brasil(aba).titulo, M.nomeDaAba(aba));
    assert.ok(brasil(aba).paragrafos.length >= 1);
    const texto = tudo(planilha(aba));
    assert.ok(!/município|estado|Brasil/i.test(texto), aba + ': ' + texto);  // a planilha fala de distritos e províncias
    // Sem códigos do motor nem do método na tela (24/10/2026: a referência do método fica em Detalhes, na aba Método e procedência).
    assert.ok(!/[A-Z]{3,}_[A-Z]|CAP-|DA-\d/.test(tudo(brasil(aba)) + texto), aba + ': ' + texto);
  }
  // A Seleção: só a orientação curta (as instruções das caixas saíram).
  assert.deepEqual(brasil('territorios').paragrafos, [M.TEXTO_DA_SELECAO]);
  assert.deepEqual(planilha('territorios').paragrafos, [M.TEXTO_DA_SELECAO]);
  const antes = M.apresentacaoDaAba('territorios', {rotulos: M.ROTULOS_GENERICOS, brasil: false, comGrupos: false, semDados: true});
  assert.equal(antes.paragrafos[0], 'Depois de escolher os dados, a lista de territórios aparece aqui.');
  assert.ok(brasil('distribuicao').paragrafos[1].includes('5 grupos iguais (quintis)'));
  assert.ok(brasil('espacial').paragrafos[1].includes('(a sede municipal)'));
  assert.ok(brasil('espacial').paragrafos[1].includes('os estados e o Brasil não têm um ponto no mapa'));
  assert.ok(!planilha('espacial').paragrafos[1].includes('sede'));
  assert.ok(brasil('rotatividade').paragrafos[1].includes('envie uma planilha com o identificador individual'));
  assert.ok(!planilha('rotatividade').paragrafos[1].includes('envie'));
  // As classes da tendência, na ordem da SPEC, cada uma com o que quer dizer e um exemplo curto, e o não avaliável.
  const tendencia = brasil('tendencia');
  assert.deepEqual(tendencia.itens.map(item => item.termo), ['Crescimento', 'Aceleração do crescimento', 'Desaceleração do crescimento',
    'Declínio', 'Aceleração de declínio', 'Desaceleração de declínio', 'Sem classificação', 'Não avaliável']);
  assert.ok(tendencia.itens.every(item => item.texto && item.texto.endsWith('.')));
  assert.ok(tendencia.itens.slice(0, 7).every(item => /Exemplos?: /.test(item.texto)), 'cada classe com um exemplo');
  assert.ok(tendencia.paragrafos[0].includes('nos últimos 4 períodos, anuais ou semestrais (você escolhe no campo Período)'));
  assert.ok(tendencia.paragrafos[0].includes('o indicador sobe (alta), cai (queda) ou fica igual (pausa)'));
  assert.ok(tendencia.nota.includes('a seta para cima é alta; para baixo, queda; para o lado, pausa'));
  assert.ok(tendencia.nota.includes('o tamanho de cada alta ou queda é comparado por mês'));
  assert.ok(tendencia.nota.endsWith('A referência do método fica em Detalhes, na aba Método e procedência.'));
  assert.ok(!/janelas longas|trecho|avanço/.test(tendencia.nota + tendencia.paragrafos.join(' ')));
  assert.deepEqual(Object.keys(M.DESCRICAO_DAS_CLASSES), M.CLASSES_TENDENCIA.map(classe => classe.codigo));
});

test('as classes da tendência em palavras simples: os exemplos seguem a regra do motor (CAP-TEN-01), passo a passo', () => {
  // Cada exemplo da explicação, classificado aqui pela mesma regra do motor (backend/trend.py, classify_speeds: o sinal de cada
  // avanço e se o tamanho cresce ou diminui), dá a classe que ele ilustra. Os períodos dos exemplos têm a mesma distância.
  const classe = valores => {
    const v = valores.slice(1).map((x, i) => x - valores[i]);
    if (v.every(x => x === 0)) return 'SEM_CLASSIFICACAO';
    if (v.some(x => x > 0) && v.some(x => x < 0)) return 'SEM_CLASSIFICACAO';
    const base = v.every(x => x >= 0) ? 'CRESCIMENTO' : 'DECLINIO';
    if (v.some(x => x === 0)) return base;
    const m = v.map(Math.abs), passos = m.slice(1).map((x, i) => [m[i], x]);
    if (passos.every(([a, b]) => b >= a) && passos.some(([a, b]) => b > a)) return base + '_ACELERADO';
    if (passos.every(([a, b]) => b <= a) && passos.some(([a, b]) => b < a)) return base + '_DESACELERADO';
    return base;
  };
  for (const [codigo, texto] of Object.entries(M.DESCRICAO_DAS_CLASSES)) {
    const exemplos = texto.split(/Exemplos?: /)[1].split(';').map(trecho => trecho.replace(/\(.*?\)/g, '').match(/\d+/g).map(Number));
    for (const exemplo of exemplos) assert.equal(classe(exemplo), codigo, codigo + ': ' + exemplo.join(', '));
  }
  // O que a classe quer dizer, junto do resultado de um território só: o rótulo do motor e a descrição, sem o exemplo.
  const t = extra => ({classe: 'CRESCIMENTO_ACELERADO', familia: 'CRESCIMENTO', rotulo: 'Aceleração do crescimento', motivo: null,
    motivoCodigo: null, motivoTexto: null, avaliavel: true, observacoes: [], velocidades: [], ...extra});
  assert.equal(M.significadoDaClasse(t()), 'Aceleração do crescimento: o indicador subiu em todos os períodos, e cada alta foi do mesmo ' +
    'tamanho ou maior que a anterior, com pelo menos uma maior: o crescimento ganhou ritmo.');
  assert.equal(M.significadoDaClasse(t({avaliavel: false, classe: null})), 'Não avaliável: ' + M.DESCRICAO_NAO_AVALIAVEL);
  assert.equal(M.significadoDaClasse(null), null);
});

test('tendência: o motivo de cada unidade em palavras, sem o código; a nota das sem classificação conta pelo motor e explica a regra', () => {
  const t = extra => ({classe: 'SEM_CLASSIFICACAO', familia: 'NENHUMA', rotulo: 'Sem classificação', motivo: null, motivoCodigo: null,
    motivoTexto: null, avaliavel: true, observacoes: 22, velocidades: [], ...extra});
  assert.equal(M.explicacaoDaTendencia(t({motivoCodigo: 'MUDANCA_DE_DIRECAO', motivoTexto: 'Mudança de direção'})),
    'Sem classificação: o indicador subiu num período e caiu em outro (mudou de direção).');
  assert.equal(M.explicacaoDaTendencia(t({motivoCodigo: 'SERIE_ESTAVEL'})),
    'Sem classificação: o indicador ficou igual em todos os períodos.');
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: null, motivoCodigo: 'SERIE_INSUFICIENTE',
    motivoTexto: '3 de 4 observações necessárias'})),
    'Não avaliável: falta o valor do indicador em algum dos períodos (3 de 4 observações necessárias).');
  // Sem o código nem o texto do motivo (uma resposta de antes), vale o rótulo do motor, que já diz o motivo.
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: 'Não avaliável: série insuficiente'})),
    'Não avaliável: série insuficiente');
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: 'Não avaliável'})), 'Não avaliável.');
  assert.equal(M.explicacaoDaTendencia(t({motivo: 'Mudança de direção (MUDANCA_DE_DIRECAO)'})), 'Sem classificação: mudança de direção.');
  assert.equal(M.explicacaoDaTendencia(t({classe: 'CRESCIMENTO_ACELERADO', familia: 'CRESCIMENTO', rotulo: 'Aceleração do crescimento'})),
    'Aceleração do crescimento: ' + M.DESCRICAO_DAS_CLASSES.CRESCIMENTO_ACELERADO.replace(/\s*Exemplo:.*$/, ''));
  assert.equal(M.explicacaoDaTendencia(null), null);
  for (const caso of [t({motivoCodigo: 'MUDANCA_DE_DIRECAO'}), t({motivoCodigo: 'SERIE_ESTAVEL'})])
    assert.ok(!/MUDANCA_DE_DIRECAO|SERIE_ESTAVEL/.test(M.explicacaoDaTendencia(caso)));
  const topo = (contagens, porMotivo) => ({contagens, semClassificacaoPorMotivo: porMotivo});
  // Todas as unidades sem classe (o cenário real das 22 competências): a contagem por motivo e a explicação da regra.
  const real = M.notaSemClassificacao(topo({SEM_CLASSIFICACAO: 62}, {MUDANCA_DE_DIRECAO: 62}), {rotulos: BR, brasil: true});
  assert.ok(real.startsWith('Sem classificação: 62 municípios mudaram de direção (o indicador subiu num período e caiu em outro).'), real);
  assert.ok(real.includes('Nenhum município recebeu classe nestes períodos'));
  assert.ok(real.includes('basta subir num e cair em outro para ficar sem classificação'));
  assert.ok(!real.includes('junhos') && !real.includes('Janelas com menos'), real);  // a janela é sempre a dos últimos 4 períodos
  assert.ok(real.endsWith('É o resultado do método, não falta de dados.'));
  // Com unidades classificadas, só a contagem por motivo.
  assert.equal(M.notaSemClassificacao(topo({CRESCIMENTO: 17, SEM_CLASSIFICACAO: 38}, {MUDANCA_DE_DIRECAO: 37, SERIE_ESTAVEL: 1}),
    {rotulos: BR, brasil: true}), 'Sem classificação: 37 municípios mudaram de direção (o indicador subiu num período e caiu em outro); ' +
    '1 município ficou igual em todos os períodos.');
  assert.equal(M.notaSemClassificacao(topo({CRESCIMENTO: 5}, {}), {rotulos: BR, brasil: true}), null);
  assert.equal(M.notaSemClassificacao(null, {rotulos: BR, brasil: true}), null);
  const distritos = M.notaSemClassificacao(topo({SEM_CLASSIFICACAO: 3}, {MUDANCA_DE_DIRECAO: 3}), {rotulos: DISTRITOS, brasil: false});
  assert.ok(distritos.includes('Nenhum distrito recebeu classe') && !distritos.includes('junhos'), distritos);
  // A resposta do motor chega com o motivo separado do código e a contagem por motivo.
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: [{id: 'code:1', tipo: 'municipio', rotulo: 'A (AM)',
    tendencia: {classe: 'SEM_CLASSIFICACAO', familia: 'NENHUMA', rotulo: 'Sem classificação', motivo: 'MUDANCA_DE_DIRECAO',
      motivo_texto: 'Mudança de direção', avaliavel: true, observacoes: 22, velocidades: []}}],
    tendencia: {competencias: ['202306', '202406'], contagens: {SEM_CLASSIFICACAO: 1}, sem_classificacao_por_motivo: {MUDANCA_DE_DIRECAO: 1}}});
  assert.equal(r.itens[0].tendencia.motivoCodigo, 'MUDANCA_DE_DIRECAO');
  assert.equal(r.tendencia.semClassificacaoPorMotivo.MUDANCA_DE_DIRECAO, 1);
});

test('quadro de setas: um ponto por período, uma seta por avanço com o sinal do motor, escala da linha e a ordem por classe', () => {
  const tendencia = (classe, observacoes, velocidades, extra = {}) => ({classe, familia: M.familiaDaClasse(classe), rotulo: classe ? 'Classe' : 'Não avaliável',
    motivo: null, motivoCodigo: null, motivoTexto: null, avaliavel: true, observacoes, velocidades, ...extra});
  const janela = ['202106', '202206', '202306', '202406'];
  const obs = valores => valores.map((valor, i) => ({competencia: janela[i], valor}));
  const vel = valores => valores.slice(1).map((valor, i) => ({de: janela[i], ate: janela[i + 1], valor: (valor - valores[i]) / 12}));
  // Manaus nos últimos 4 junhos (base versionada, arredondado): três altas, cada uma maior que a anterior.
  const valores = [1.81, 1.87, 1.96, 2.07];
  const manaus = tendencia('CRESCIMENTO_ACELERADO', obs(valores), vel(valores), {rotulo: 'Aceleração do crescimento'});
  const caixa = {x0: 0, x1: 120, y0: 0, y1: 40};
  const {pontos, setas} = M.montarSetas(manaus, janela, caixa);
  const arredondar = valor => Math.round(valor * 1e6) / 1e6;  // as posições são contas em ponto flutuante
  assert.deepEqual(pontos.map(p => arredondar(p.x)), [0, 40, 80, 120]);  // a cada 12 meses, no tempo real
  assert.deepEqual([arredondar(pontos[0].y), arredondar(pontos[3].y)], [40, 0]);  // escala da linha: o menor no pé, o maior no topo
  assert.deepEqual(setas.map(s => [s.de, s.ate, s.sinal]), [['202106', '202206', 'alta'], ['202206', '202306', 'alta'], ['202306', '202406', 'alta']]);
  assert.ok(setas.every(s => s.angulo < 0 && s.meioX > s.x1 && s.meioX < s.x2), 'a ponta no meio de cada avanço, subindo');
  // O sinal é o da velocidade do motor (pausa, alta, queda); a amplitude mínima não faz uma série quase parada parecer um salto.
  const quase = M.montarSetas(tendencia('SEM_CLASSIFICACAO', obs([5, 5, 5.0001, 5]), [{de: '202106', ate: '202206', valor: 0},
    {de: '202206', ate: '202306', valor: 0.00001}, {de: '202306', ate: '202406', valor: -0.00001}]), janela, caixa);
  assert.deepEqual(quase.setas.map(s => s.sinal), ['pausa', 'alta', 'queda']);
  assert.ok(Math.max(...quase.pontos.map(p => p.y)) - Math.min(...quase.pontos.map(p => p.y)) < 1, 'quase plana');
  // Período sem valor: nenhum ponto inventado; a seta liga as observações que o motor usou. Semestral: 5 e 7 meses.
  const semestral = ['202301', '202306', '202401', '202406'];
  const lacuna = M.montarSetas(tendencia(null, [{competencia: '202301', valor: 1}, {competencia: '202306', valor: null}, {competencia: '202401', valor: 2},
    {competencia: '202406', valor: 3}], [{de: '202301', ate: '202401', valor: 0.08}, {de: '202401', ate: '202406', valor: 0.2}], {avaliavel: false}),
  semestral, {x0: 0, x1: 170, y0: 0, y1: 40});
  assert.deepEqual(lacuna.pontos.map(p => [p.competencia, arredondar(p.x)]), [['202301', 0], ['202401', 120], ['202406', 170]]);
  assert.deepEqual(lacuna.setas.map(s => [s.de, s.ate]), [['202301', '202401'], ['202401', '202406']]);
  assert.deepEqual(M.montarSetas(null, janela, caixa), {pontos: [], setas: []});
  // Ordem: a classe na ordem da SPEC e, nela, a maior variação primeiro (sem valor no fim); os não avaliáveis por último. Com a
  // ordenação em uso, a posição do motor.
  const item = (id, classe, variacao) => ({id, tipo: 'municipio', rotulo: id, densidade: 1, variacao_percentual: {densidade: variacao},
    tendencia: classe ? tendencia(classe, [], []) : tendencia(null, [], [], {avaliavel: false}), ordem: null});
  const itens = [item('A', 'SEM_CLASSIFICACAO', 9), item('B', 'CRESCIMENTO', 2), item('C', 'CRESCIMENTO', 7), item('D', null, 50),
    item('E', 'CRESCIMENTO_ACELERADO', 1), item('F', 'CRESCIMENTO', null)];
  assert.deepEqual(M.ordemDoQuadro(itens, 'densidade', false).map(i => i.id), ['C', 'B', 'F', 'E', 'A', 'D']);
  const comPosicao = itens.map((i, n) => ({...i, ordem: {posicao: [3, null, 1, 2, null, 4][n]}}));
  assert.deepEqual(M.ordemDoQuadro(comPosicao, 'densidade', true).map(i => i.id), ['C', 'D', 'A', 'F', 'B', 'E']);
  // Para os leitores de tela: a classe do motor e cada período com o valor e o avanço até ele.
  assert.equal(M.descricaoDasSetas({...item('MANAUS (AM)', 'CRESCIMENTO_ACELERADO', 14), tendencia: manaus}, 'densidade'),
    'MANAUS (AM): Aceleração do crescimento. 06/2021: 1,81; 06/2022: 1,87, alta; 06/2023: 1,96, alta; 06/2024: 2,07, alta.');
  assert.equal(M.sinalDoAvanco(-0.1), 'queda');
});

test('planilha com a coluna-mãe: os grupos da Seleção vêm do catálogo do pré-exame (a província de cada distrito)', () => {
  const unidade = (id, nome, provincia) => ({id, name: nome, code: '', label: nome, state: '', state_name: '', state_code: '',
    parents: provincia ? [provincia] : []});
  const catalogo = [unidade('name:Alfa', 'Alfa', 'Norte'), unidade('name:Beta', 'Beta', 'Norte'), unidade('name:Gama', 'Gama', 'Sul'),
    unidade('name:Delta', 'Delta', 'Sul')];
  assert.deepEqual(M.gruposDaFonte(undefined, catalogo).map(grupo => [grupo.id, grupo.nome, grupo.unidades]), [['Norte', 'Norte', 2],
    ['Sul', 'Sul', 2]]);
  assert.equal(M.grupoDaUnidade(catalogo[2]), 'Sul');
  // Sem a coluna-mãe, a lista fica sem grupos; na base do Brasil, o estado pelo código IBGE continua valendo.
  assert.deepEqual(M.gruposDaFonte(undefined, catalogo.map(item => ({...item, parents: []}))), []);
  assert.equal(M.grupoDaUnidade({...catalogo[0], state: 'AM', state_code: '13', parents: ['Amazonas']}), '13');
  // A província marcada inteira vai ao motor pelo valor dela, e os distritos dela saem da lista solta.
  assert.deepEqual(M.normalizarBase({todos: false, estados: ['Sul'], ids: ['name:Gama', 'name:Alfa']}, id =>
    M.grupoDaUnidade(catalogo.find(item => item.id === id))), {todos: false, estados: ['Sul'], ids: ['name:Alfa']});
});

// ================================================================================================ ajustes de 24/10/2026 (segunda rodada)
test('Desfazer: um passo por ação, o arraste contínuo vira um passo só, com o estado de antes, e o texto do botão diz o que desfaz', () => {
  let pilha = [];
  pilha = M.empilharPasso(pilha, {rotulo: 'MANAUS (AM) marcado', tipo: 'MANAUS (AM) marcado', quando: 1000, estado: {n: 0}});
  pilha = M.empilharPasso(pilha, {rotulo: 'TEFE (AM) marcado', tipo: 'TEFE (AM) marcado', quando: 1500, estado: {n: 1}});
  assert.deepEqual(pilha.map(passo => passo.estado.n), [0, 1]);
  // A régua arrastada: passos seguidos do mesmo tipo contínuo ficam como um só, com o estado de antes do primeiro.
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2000, estado: {n: 2}});
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2300, estado: {n: 3}});
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2900, estado: {n: 4}});
  assert.deepEqual(pilha.map(passo => passo.estado.n), [0, 1, 2]);
  // Depois de uma pausa de PASSO_CONTINUO_MS, outro arraste é outro passo; ações discretas iguais nunca se juntam.
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2900 + M.PASSO_CONTINUO_MS, estado: {n: 5}});
  pilha = M.empilharPasso(pilha, {rotulo: 'TEFE (AM) marcado', tipo: 'TEFE (AM) marcado', quando: 9000, estado: {n: 6}});
  pilha = M.empilharPasso(pilha, {rotulo: 'TEFE (AM) marcado', tipo: 'TEFE (AM) marcado', quando: 9100, estado: {n: 7}});
  assert.deepEqual(pilha.map(passo => passo.estado.n), [0, 1, 2, 5, 6, 7]);
  // A pilha guarda até MAX_PASSOS passos (os mais antigos saem).
  let longa = [];
  for (let i = 0; i < M.MAX_PASSOS + 5; i++) longa = M.empilharPasso(longa, {rotulo: 'p' + i, tipo: 'p' + i, quando: i * 5000, estado: i});
  assert.equal(longa.length, M.MAX_PASSOS);
  assert.equal(longa[0].estado, 5);
  // O botão se chama Desfazer desde 25/10/2026 (antes, Voltar): o title diz o que o próximo clique desfaz, sem o ponto final do
  // passo, e o aviso diz o que foi desfeito; o nome próprio no começo do passo fica como é.
  assert.equal(M.textoDoDesfazer(null), 'Nada para desfazer ainda');
  assert.equal(M.textoDoDesfazer({rotulo: 'Limpar seleção'}), 'Desfazer: limpar seleção');
  assert.equal(M.textoDoDesfazer({rotulo: 'Abrir a Análise de Tendência'}), 'Desfazer: abrir a Análise de Tendência');
  assert.equal(M.textoDoDesfazer({rotulo: 'Todos os estados marcados.'}), 'Desfazer: todos os estados marcados');
  assert.equal(M.textoDoDesfeito({rotulo: 'Abrir a Seleção de Territórios'}), 'Desfeito: abrir a Seleção de Territórios.');
  assert.equal(M.textoDoDesfeito({rotulo: 'Municípios do Amazonas desmarcados.'}), 'Desfeito: municípios do Amazonas desmarcados.');
  assert.equal(M.textoDoDesfazer({rotulo: 'Marcar MANAUS (AM)'}), 'Desfazer: marcar MANAUS (AM)');
  assert.equal(M.textoDoVoltar, undefined, 'o texto antigo saiu com o nome Voltar');
});

test('período com que a tendência abre: o anual, à vista; sem ele, o único ritmo da base; sem nenhum, a escolha', () => {
  const semestrais = ['201401', '201406', '201501', '201506', '201601', '201606', '201701', '201706', '201801', '201806', '201901', '201906',
    '202001', '202006', '202101', '202106', '202201', '202206', '202301', '202306', '202401', '202406'];
  assert.deepEqual(M.janelaPadrao(semestrais), ['202106', '202206', '202306', '202406']);
  // Dois anos de competências trimestrais: o anual não tem 4 períodos, e o semestral é o único ritmo (RQ-GOV-14).
  const trimestrais = ['202301', '202303', '202306', '202309', '202312', '202403', '202406'];
  assert.deepEqual(M.janelaPadrao(trimestrais), ['202301', '202306', '202312', '202406']);
  assert.deepEqual(M.janelaPadrao(trimestrais), M.ritmosDaBase(trimestrais).find(item => item.ritmo === 'semestral').janela);
  // Sem nenhum ritmo com 4 períodos: nada é escolhido, e o aviso pede a escolha.
  assert.deepEqual(M.janelaPadrao(['202306', '202406']), []);
  // A definição inicial continua sem janela: ela entra ao abrir a Análise de Tendência, na visão Tendência.
  const inicial = M.definicaoInicial({tipo: 'brasil', periodos: semestrais, categoria: 'MEDICINA', temGrupos: true});
  assert.deepEqual([inicial.janela, inicial.visao, inicial.serie], [[], 'classes', []]);
});

test('visões da tendência: Tendência, Trajetória e Série temporal, nesta ordem; a Série temporal tem o intervalo nos ajustes', () => {
  assert.deepEqual(M.ORDEM_DAS_VISOES.map(visao => M.NOMES_VISOES[visao]), ['Tendência', 'Trajetória', 'Série temporal']);
  const a = extra => M.ajustesDaAnalise({familia: 'tendencia', nivel: 'municipios', disponivel: true, categorias: 1, ...extra});
  assert.deepEqual(a({visao: 'classes'}), ['indicador', 'janela', 'visao']);
  assert.deepEqual(a({visao: 'mudanca'}), ['indicador', 'janela', 'visao']);
  assert.deepEqual(a({visao: 'series'}), ['indicador', 'serie', 'visao']);
  // A Tendência sem 4 competências vira Trajetória; a Série temporal não depende da janela e não tem cor de classe.
  assert.equal(M.visaoEfetiva(definicao({familia: 'tendencia', visao: 'classes', janela: ['202306', '202406']})), 'mudanca');
  assert.equal(M.visaoEfetiva(definicao({familia: 'tendencia', visao: 'series', janela: []})), 'series');
  assert.equal(M.camadaDeCor('tendencia', 'series', resposta(), definicao()), 'unica');
});

test('Série temporal: toda a extensão da base, lida dos dados, ou o intervalo escolhido; o CSV com uma coluna por competência', () => {
  const periodos = ['202406', '201401', '201906', '202106'];
  assert.deepEqual(M.intervaloDaSerie({serie: []}, periodos), ['201401', '201906', '202106', '202406']);  // do primeiro ao último
  assert.deepEqual(M.intervaloDaSerie({serie: ['202106', '201906']}, periodos), ['201906', '202106']);
  assert.deepEqual(M.intervaloEntre(periodos, '201906', '202406'), ['201906', '202106', '202406']);
  assert.deepEqual(M.intervaloEntre(periodos, '202406', '201906'), ['201906', '202106', '202406']);  // a ordem dos campos não importa
  assert.deepEqual(M.intervaloEntre(periodos, '201401', '202406'), []);  // a extensão inteira volta a ser "toda a série"
  // O cliente lê a série da resposta: o intervalo no topo e as observações de cada item (null sem valor, nunca zero).
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    serie: {janela: {inicio: '201401', fim: '202406', competencias: ['201401', '202106', '202406']}, competencias: 3, unidade_valor: 'por 1.000 habitantes'},
    itens: [municipio('code:130260', 'MANAUS (AM)', {serie: {observacoes: [{competencia: '201401', valor: 1.37}, {competencia: '202106', valor: null},
      {competencia: '202406', valor: 2.07}], comparavel: true, motivo: null}}),
      {...municipio('c1', 'Capitais'), tipo: 'conjunto', serie: {observacoes: [{competencia: '201401', valor: 1.4}], comparavel: false,
        motivo: 'Série não comparável: os membros mudam (INCOMPARABILIDADE)'}}]});
  assert.deepEqual(r.serie, {competencias: ['201401', '202106', '202406'], inicio: '201401', fim: '202406', unidadeValor: 'por 1.000 habitantes'});
  assert.deepEqual(r.itens[0].serie.observacoes.map(obs => obs.valor), [1.37, null, 2.07]);
  assert.equal(r.itens[1].serie.comparavel, false);
  const csv = M.montarCsv(r, {familia: 'tendencia', indicador: 'densidade', rotulos: BR}).slice(1).split('\r\n');
  assert.ok(csv[0].includes('"Densidade em 01/2014";"Densidade em 06/2021";"Densidade em 06/2024";"Série comparável"'), csv[0]);
  assert.ok(csv.some(linha => linha.startsWith('"code:130260"') && linha.includes('"1.37";"";"2.07";"sim"')));
  assert.ok(M.textoDoMetodo(r, 'Série temporal', null).includes('- Série temporal: 01/2014 a 06/2024 (3 competências)'));
});

test('Série temporal no desenho: a cor única do gráfico (sem classe) e, sem comparabilidade, só os pontos, sem linha', () => {
  const competencias = ['201401', '201406', '201501'];
  const item = (id, valores, comparavel = true) => ({...municipio(id, id + ' (AM)'), tendencia: {classe: 'CRESCIMENTO', familia: 'CRESCIMENTO',
    rotulo: 'Crescimento', avaliavel: true, observacoes: [], velocidades: []},
    serie: {observacoes: competencias.map((competencia, i) => ({competencia, valor: valores[i]})), comparavel, motivo: null}});
  const itens = [item('a', [1, 2, 3]), item('b', [2, null, 4]), item('c', [1, 1, 1], false)];
  const observacoesDe = it => it.serie.observacoes;
  const dominio = M.dominioDasSeries(itens, observacoesDe);
  const {series} = M.montarSeries({itens, janela: competencias, dominio, x0: 0, x1: 100, y0: 0, y1: 100, observacoesDe, corUnica: '#008b9e',
    ligar: it => it.serie.comparavel});
  assert.ok(series.every(serie => serie.cor === '#008b9e' && serie.familia === null), 'sem a cor da classe');
  assert.deepEqual(series.map(serie => serie.pontos.length), [3, 2, 3]);
  assert.deepEqual(series.map(serie => serie.caminhos.length), [1, 0, 0]);  // a lacuna não é ligada; o não comparável fica sem linha
  assert.deepEqual(series.map(serie => serie.ligada), [true, true, false]);
  // Sem os parâmetros novos, as séries continuam como antes (as observações da tendência, na cor da classe).
  assert.equal(M.montarSeries({itens: [item('a', [1, 2, 3])], janela: competencias, dominio, x0: 0, x1: 100, y0: 0, y1: 100}).series[0].familia,
    'CRESCIMENTO');
});

test('Trajetória: os períodos do meio, como foram observados, no caminho do rastro e na dica; sem a variação, sem caminho', () => {
  const janela = ['202106', '202206', '202306', '202406'];
  const tendencia = valores => ({classe: 'SEM_CLASSIFICACAO', familia: 'SEM_CLASSIFICACAO', rotulo: 'Sem classificação', avaliavel: true,
    motivo: null, motivoCodigo: 'MUDANCA_DE_DIRECAO', motivoTexto: null, observacoes: valores.map((valor, i) => ({competencia: janela[i], valor})),
    velocidades: []});
  const sobe = municipio('code:1', 'A (AM)', {densidade: 4, inicial: {populacao: 1000, quantidade: 2, densidade: 2},
    variacao_percentual: {populacao: 0, quantidade: 100, densidade: 100}, tendencia: tendencia([2, 5, null, 4])});
  const semVariacao = municipio('code:2', 'B (AM)', {densidade: 3, tendencia: tendencia([1, 2, 3, 3])});
  const pintura = () => ({cor: '#008b9e', vazada: false, apagada: false});
  const comum = {indicador: 'densidade', escala: 'linear', distancia: false, cometa: true, vista: 'final', largura: 800, rotuloDistancia: '', pintura};
  const g = M.montarGrafico({...comum, itens: [sobe, semVariacao], dominios: {densidade: [1, 4], tendencia: [1, 5]}, trajetoria: true});
  const a = g.bolhas.find(b => b.id === 'code:1'), b = g.bolhas.find(b => b.id === 'code:2');
  assert.deepEqual(a.trajeto.map(passo => [passo.competencia, passo.valor, passo.dx]), [['202206', 5, 0]]);  // sem imputar 06/2023
  assert.ok(a.trajeto[0].dy < 0, 'o valor 5 fica acima do valor final (4)');
  assert.equal(b.trajeto, null);  // sem a variação, não há caminho (RQ-REP-15)
  assert.ok(g.eixoY.dominio[1] >= 5, 'o eixo cabe o valor do meio');
  // Sem a Trajetória, nada muda no desenho.
  assert.equal(M.montarGrafico({...comum, itens: [sobe], dominios: {densidade: [1, 4]}}).bolhas[0].trajeto, null);
  const dica = M.montarDica(sobe, {indicador: 'densidade', competencia: '202406', competenciaInicial: '202106', distancia: false, variacao: true,
    tendencia: false, nomes: new Map(), rotulos: BR, trajetoria: true});
  assert.deepEqual(dica.linhas.filter(linha => /^Densidade em /.test(linha.rotulo)).map(linha => [linha.rotulo, linha.valor]),
    [['Densidade em 06/2021', '2,00 por 1.000 habitantes'], ['Densidade em 06/2022', '5,00 ▲'], ['Densidade em 06/2023', 'sem valor']]);
});

test('território de referência: a guarda, as delimitações que a fonte tem, o valor de corte pela natureza do atributo e o que a tela mostra', () => {
  const elegivel = {relacao: 'mais_proxima', delimitacao: {tipo: 'regioes', valores: ['Norte']}, condicao: {atributo: 'densidade', operador: '>', valor: 2.36}};
  assert.equal(M.referenciaElegivel(elegivel), true);
  assert.equal(M.referenciaElegivel({membros: ['code:130260']}), false);
  assert.equal(M.referenciaElegivel(null), false);
  // O pedido leva o território de referência como foi definido, na análise espacial dos municípios.
  const am = {nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}};
  assert.deepEqual(M.montarOpcoes(definicao({...am, familia: 'espacial', referencia: elegivel}), 'espacial').referencia, elegivel);
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'espacial', referencia: elegivel}), true), 'espacial');
  // As delimitações seguem os níveis da fonte: no Brasil, estados e regiões; numa planilha com a coluna-mãe, o grupo; sem ela, a planilha.
  assert.deepEqual(M.delimitacoesDaFonte({brasil: true, comGrupos: true, rotulos: BR}).map(d => [d.tipo, d.rotulo]), [
    ['mesmo_grupo', 'No mesmo estado de cada município'], ['grupos', 'Estados escolhidos'], ['mesma_regiao', 'Na mesma região de cada município'],
    ['regioes', 'Regiões escolhidas'], ['todos', 'No Brasil inteiro']]);
  assert.deepEqual(M.delimitacoesDaFonte({brasil: false, comGrupos: true, rotulos: DISTRITOS}).map(d => d.rotulo),
    ['Na mesma província de cada distrito', 'Províncias escolhidas', 'Na planilha inteira']);
  assert.deepEqual(M.delimitacoesDaFonte({brasil: false, comGrupos: false, rotulos: DISTRITOS}).map(d => d.tipo), ['todos']);
  assert.deepEqual(M.REGIOES_DO_BRASIL.map(r => r.nome), ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']);
  assert.deepEqual([M.regiaoDoEstado('12'), M.regiaoDoEstado('43'), M.regiaoDoEstado('53')], ['Norte', 'Sul', 'Centro-Oeste']);
  // O valor de corte: a densidade com vírgula ou ponto decimal; a quantidade e a população, inteiros (pessoas e habitantes).
  assert.equal(M.lerValorDeCorte('2,36', 'densidade'), 2.36);
  assert.equal(M.lerValorDeCorte('2.36', 'densidade'), 2.36);
  assert.equal(M.lerValorDeCorte('1.234,5', 'densidade'), 1234.5);
  assert.equal(M.lerValorDeCorte('50.000', 'populacao'), 50000);
  assert.equal(M.lerValorDeCorte(' 50000 ', 'populacao'), 50000);
  assert.equal(M.lerValorDeCorte('0', 'quantidade'), 0);
  assert.equal(M.lerValorDeCorte('2,5', 'quantidade'), null);  // profissionais são inteiros
  assert.equal(M.lerValorDeCorte('-1', 'densidade'), null);
  assert.equal(M.lerValorDeCorte('abc', 'populacao'), null);
  assert.equal(M.lerValorDeCorte('', 'densidade'), null);
  assert.equal(M.UNIDADES_DO_CORTE.densidade.unidade, 'profissionais por 1.000 habitantes');
  assert.equal(M.UNIDADES_DO_CORTE.quantidade.unidade, 'profissionais');
  assert.equal(M.UNIDADES_DO_CORTE.populacao.unidade, 'habitantes');
  // A resposta: a definição com os textos do cálculo, as contagens da condição e a referência de cada item (referencia_do_item).
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    referencia: {tipo: 'elegiveis', relacao: 'mais_distante', delimitacao: {tipo: 'mesmo_grupo', valores: [], texto: 'do mesmo estado de cada município'},
      condicao: {atributo: 'populacao', operador: '>', valor: '50000', texto: 'população > 50000 habitantes'},
      elegiveis: {universo: 5570, atende: 360, nao_atende: 5210, nao_avaliaveis: 0},
      membros: [{id: 'code:120040', rotulo: 'RIO BRANCO (AC)'}], origem: 'Para cada município, o município mais distante…'},
    itens: [municipio('code:120010', 'BRASILEIA (AC)', {distancia_km: 571.0, referencia_do_item: {id: 'code:120020', rotulo: 'CRUZEIRO DO SUL (AC)', empate: []}})]});
  assert.equal(r.referencia.tipo, 'elegiveis');
  assert.equal(r.referencia.relacao, 'mais_distante');
  assert.deepEqual(r.referencia.delimitacao, {tipo: 'mesmo_grupo', valores: [], texto: 'do mesmo estado de cada município'});
  assert.deepEqual(r.referencia.elegiveis, {universo: 5570, atende: 360, naoAtende: 5210, naoAvaliaveis: 0});
  assert.equal(r.referencia.condicao.texto, 'população > 50000 habitantes');
  assert.deepEqual(r.itens[0].referenciaDoItem, [{id: 'code:120020', rotulo: 'CRUZEIRO DO SUL (AC)'}]);
  const dica = M.montarDica(r.itens[0], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: true, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR, relacao: 'mais_distante'});
  assert.deepEqual(dica.linhas.filter(linha => /referência/.test(linha.rotulo)).map(linha => [linha.rotulo, linha.valor]),
    [['Distância até o território de referência', '571,00 km'], ['Território de referência (o mais distante)', 'CRUZEIRO DO SUL (AC)']]);
  const csv = M.montarCsv(r, {familia: 'espacial', indicador: 'densidade', rotulos: BR}).slice(1).split('\r\n');
  assert.ok(csv[0].includes('"Distância até o território de referência (km)";"Território de referência (o mais distante)"'), csv[0]);
  assert.ok(!csv[0].includes('Membro da referência'));
  assert.ok(csv[1].includes('"CRUZEIRO DO SUL (AC)"'));
  // As ligações do mapa vão até a referência de cada item.
  assert.deepEqual(M.ligacoesDoMapa(r.itens, ['code:120010']), [{de: 'code:120010', para: ['code:120020']}]);
  // A apresentação da análise espacial fala do fluxo novo (sem "pelo nome" nem "um conjunto"), e o próprio território nunca é referência.
  const espacial = M.apresentacaoDaAba('espacial', {rotulos: BR, brasil: true, comGrupos: true}).paragrafos.join(' ');
  assert.ok(espacial.includes('o mesmo estado, uma região ou o Brasil inteiro'), espacial);
  assert.ok(espacial.includes('O próprio município nunca é a sua referência'), espacial);
  assert.ok(!/pelo nome|um conjunto deles/.test(espacial), espacial);
  assert.ok(M.apresentacaoDaAba('espacial', {rotulos: DISTRITOS, brasil: false, comGrupos: true}).paragrafos[0]
    .includes('a mesma província ou a planilha inteira'));
});

test('territórios base (25/10/2026): todos os selecionados ou alguns, cumulativos; cada um ligado à sua referência, com os valores do motor, sem novo pedido', () => {
  // Por elegibilidade, o motor manda a UF e os valores de cada território de referência; o item diz qual é o de cada um.
  const SEM_REF = 'Sem território de referência: nenhum outro município de todo o Brasil atende à condição densidade > 9 por 1.000 habitantes (CONJUNTO_REFERENCIAS_VAZIO)';
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    referencia: {tipo: 'elegiveis', relacao: 'mais_proxima', delimitacao: {tipo: 'todos', valores: [], texto: 'de todo o Brasil'},
      condicao: {atributo: 'densidade', operador: '>', valor: '2', texto: 'densidade > 2 por 1.000 habitantes'},
      elegiveis: {universo: 5570, atende: 2510, nao_atende: 3060, nao_avaliaveis: 0},
      membros: [{id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', uf: 'AM', populacao: 33004, quantidade: 71, densidade: 2.1512543934068598},
        {id: 'code:140010', rotulo: 'BOA VISTA (RR)', uf: 'RR', populacao: 470169, quantidade: 1181, densidade: 2.5118627557325133}],
      origem: 'Para cada município, o município mais próximo…'},
    itens: [
      municipio('code:140002', 'AMAJARI (RR)', {populacao: 15583, distancia_km: 124.43, referencia_do_item: {id: 'code:140010', rotulo: 'BOA VISTA (RR)', empate: []}}),
      municipio('code:140010', 'BOA VISTA (RR)', {populacao: 470169, quantidade: 1181, densidade: 2.5118627557325133, distancia_km: 543.82,
        referencia_do_item: {id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', empate: []}}),
      municipio('code:140015', 'BONFIM (RR)', {distancia_km: null, referencia_do_item: null, motivos: [SEM_REF]}),
      municipio('code:140020', 'CARACARAI (RR)', {distancia_km: 100, referencia_do_item: {id: 'code:140010', rotulo: 'BOA VISTA (RR)',
        empate: [{id: 'code:140010', rotulo: 'BOA VISTA (RR)'}, {id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)'}]}}),
      {...municipio('c1', 'Juntos'), tipo: 'conjunto'}, {...municipio('uf:14', 'Roraima (RR)'), tipo: 'estado'}]});
  assert.deepEqual(r.referencia.membros[0], {id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', uf: 'AM', populacao: 33004, quantidade: 71,
    densidade: 2.1512543934068598});
  // As opções do Território base: as unidades em análise, sem conjuntos nem estados, na ordem dos nomes.
  const bases = M.basesPossiveis(r.itens);
  assert.deepEqual(bases.map(base => base.rotulo), ['AMAJARI (RR)', 'BOA VISTA (RR)', 'BONFIM (RR)', 'CARACARAI (RR)']);
  // Cumulativos: nulo é todos os selecionados (também os que entrarem depois); a lista vale na ordem das opções, só com quem
  // continua em análise; com todas marcadas, volta a nulo.
  const TODAS = ['code:140002', 'code:140010', 'code:140015', 'code:140020'];
  assert.deepEqual(M.basesEmUso(null, bases), TODAS);
  assert.deepEqual(M.basesEmUso(['code:140020', 'code:999999', 'code:140010'], bases), ['code:140010', 'code:140020']);
  assert.deepEqual(M.basesEmUso([], bases), []);
  assert.equal(M.normalizarBases([...TODAS].reverse(), bases), null);
  assert.deepEqual(M.normalizarBases(['code:140020', 'code:140010', 'code:999999'], bases), ['code:140010', 'code:140020']);
  assert.deepEqual(M.normalizarBases([], bases), []);
  // A referência fora da análise: contexto no gráfico (não é desenhada lá), com os valores dos membros e a distância do item.
  const boaVista = M.parDaBase(r, 'code:140010');
  assert.equal(boaVista.base.id, 'code:140010');
  assert.deepEqual(boaVista.referencias, [{id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', uf: 'AM', populacao: 33004, quantidade: 71,
    densidade: 2.1512543934068598, noGrafico: false, emAnalise: false}]);
  assert.deepEqual([boaVista.distancia, boaVista.motivo], [543.82, null]);
  assert.equal(M.textoDoParDaBase(boaVista, 'mais_proxima'), 'Território base: BOA VISTA (RR) · Território de referência (o mais próximo): ' +
    'PRESIDENTE FIGUEIREDO (AM), a 543,82 km em linha reta.');
  // A referência que também está em análise (com a sua própria distância): o contexto continua.
  const [deAmajari] = M.parDaBase(r, 'code:140002').referencias;
  assert.deepEqual([deAmajari.id, deAmajari.noGrafico, deAmajari.emAnalise, deAmajari.densidade], ['code:140010', false, true, 2.5118627557325133]);
  // Empate: todas as empatadas, a primeira antes (CAP-ESP-02); sem referência, o motivo do motor; sem base ou com a base fora da
  // análise, nada.
  const caracarai = M.parDaBase(r, 'code:140020');
  assert.deepEqual(caracarai.referencias.map(ref => ref.id), ['code:140010', 'code:130353']);
  assert.equal(M.textoDoParDaBase(caracarai, 'mais_proxima'), 'Território base: CARACARAI (RR) · Território de ' +
    'referência (o mais próximo): BOA VISTA (RR) (empate com PRESIDENTE FIGUEIREDO (AM)), a 100,00 km em linha reta.');
  const bonfim = M.parDaBase(r, 'code:140015');
  assert.deepEqual([bonfim.referencias, bonfim.motivo], [[], SEM_REF]);
  assert.equal(M.textoDoParDaBase(bonfim, 'mais_proxima'), 'Território base: BONFIM (RR). ' + SEM_REF);
  assert.equal(M.parDaBase(r, 'c1'), null);
  assert.equal(M.parDaBase(r, 'code:999999'), null);
  assert.equal(M.parDaBase(r, null), null);
  assert.equal(M.parDaBase(null, 'code:140010'), null);
  // Todos os selecionados: um par por base, na ordem das opções; as referências de contexto uma vez cada, com as bases ligadas a
  // elas e a distância de cada uma.
  const pares = M.paresDasBases(r, M.basesEmUso(null, bases));
  assert.deepEqual(pares.map(par => par.base.id), TODAS);
  assert.deepEqual(M.paresDasBases(r, ['code:140010', 'code:999999']).map(par => par.base.id), ['code:140010']);
  const contextos = M.referenciasDeContexto(pares);
  assert.deepEqual(contextos.map(c => [c.referencia.id, c.bases.map(item => [item.base.id, item.distancia])]), [
    ['code:140010', [['code:140002', 124.43], ['code:140020', 100]]],
    ['code:130353', [['code:140010', 543.82], ['code:140020', 100]]]]);
  // A dica de uma referência de contexto: os valores do motor e a distância até cada base ligada a ela.
  const [deBoaVista, dePresidente] = contextos;
  const dica = M.dicaDaReferenciaDeContexto(dePresidente, 'mais_proxima');
  assert.equal(dica.titulo, 'PRESIDENTE FIGUEIREDO (AM)');
  assert.equal(dica.subtitulo, 'Território de referência (o mais próximo) de BOA VISTA (RR) e CARACARAI (RR)');
  assert.deepEqual(dica.linhas.map(linha => [linha.rotulo, linha.valor]), [['População', '33.004 habitantes'], ['Profissionais', '71'],
    ['Densidade', '2,15 por 1.000 habitantes'], ['Distância até BOA VISTA (RR)', '543,82 km'], ['Distância até CARACARAI (RR)', '100,00 km']]);
  assert.deepEqual(dica.notas, ['Fora da seleção: aparece só como território de referência, no início do eixo (0 km).']);
  assert.match(M.dicaDaReferenciaDeContexto(deBoaVista, 'mais_proxima').notas[0], /^Também está em análise/);
  // Com mais de quatro bases ligadas à mesma referência: três nomes no subtítulo, as quatro primeiras distâncias e quantas faltam.
  const seis = {referencia: dePresidente.referencia, bases: Array.from({length: 6}, (_, i) => ({base: {...r.itens[0], rotulo: 'B' + i}, distancia: i}))};
  const cheia = M.dicaDaReferenciaDeContexto(seis, null);
  assert.equal(cheia.subtitulo, 'Território de referência de B0, B1, B2 e mais 3');
  assert.deepEqual(cheia.linhas.slice(3).map(linha => linha.rotulo), ['Distância até B0', 'Distância até B1', 'Distância até B2', 'Distância até B3']);
  assert.equal(cheia.notas[0], 'E mais 2 territórios base ligados a esta referência (as distâncias estão na tabela).');
  // A linha acima do desenho: com uma base, o par dela; com mais, quantas, os quatro primeiros pares e, quando o gráfico liga menos
  // do que os pares com referência, quantas ligações ele desenha; sem bases, o que falta.
  assert.equal(M.textoDosTerritoriosBase({pares: [boaVista], todos: false, ligados: 1, relacao: 'mais_proxima'}),
    M.textoDoParDaBase(boaVista, 'mais_proxima'));
  assert.equal(M.textoDosTerritoriosBase({pares: [boaVista], todos: false, ligados: 0, relacao: 'mais_proxima'}),
    M.textoDoParDaBase(boaVista, 'mais_proxima') + ' Nenhuma ligação à vista no gráfico: a bolha do território base está fora da régua ou dos filtros.');
  assert.equal(M.textoDosTerritoriosBase({pares, todos: true, ligados: 3, relacao: 'mais_proxima'}),
    'Territórios base: 4 (todos os selecionados) · cada um ligado ao seu território de referência (o mais próximo) por linha ' +
    'tracejada: AMAJARI (RR) → BOA VISTA (RR), 124,43 km; BOA VISTA (RR) → PRESIDENTE FIGUEIREDO (AM), 543,82 km; BONFIM (RR): sem ' +
    'território de referência; CARACARAI (RR) → BOA VISTA (RR) ou PRESIDENTE FIGUEIREDO (AM) (empate), 100,00 km.');
  assert.match(M.textoDosTerritoriosBase({pares: [...pares, M.parDaBase(r, 'code:140002')], todos: false, ligados: 2, relacao: null}),
    /^Territórios base: 5 · cada um ligado ao seu território de referência por linha tracejada: .+; e mais 1 \(nas dicas e na tabela\)\. O gráfico desenha 2 dessas ligações: no máximo 30, e só das bolhas à vista\.$/);
  assert.equal(M.textoDosTerritoriosBase({pares: [], todos: false, ligados: 0}),
    'Nenhum território base: o gráfico e o mapa não mostram as ligações até os territórios de referência.');
  // O resumo no ajuste do Território de referência: só com as bases escolhidas uma a uma (todos é o padrão).
  const nome = id => bases.find(base => base.id === id)?.rotulo ?? id;
  assert.equal(M.resumoDosTerritoriosBase(TODAS, true, nome), '');
  assert.equal(M.resumoDosTerritoriosBase([], false, nome), ' · nenhum território base');
  assert.equal(M.resumoDosTerritoriosBase(['code:140010'], false, nome), ' · território base: BOA VISTA (RR)');
  assert.equal(M.resumoDosTerritoriosBase(['code:140002', 'code:140010'], false, nome), ' · territórios base: AMAJARI (RR) e BOA VISTA (RR)');
  assert.equal(M.resumoDosTerritoriosBase(TODAS, false, nome), ' · 4 territórios base');
  // Pelos membros escolhidos (a conversa: "use Manaus como referência"), o membro já está no gráfico, a distância zero, com a mira:
  // os valores vêm do item, a ligação vai até a bolha dele, e ele não entra como contexto.
  const pelosMembros = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    referencia: {tipo: 'municipio', membros: [{id: 'code:130260', rotulo: 'MANAUS (AM)'}], origem: 'Referência escolhida.'},
    itens: [municipio('code:130260', 'MANAUS (AM)', {populacao: 2000, quantidade: 50, densidade: 25, distancia_km: 0, referencia: true}),
      municipio('code:130420', 'TEFE (AM)', {distancia_km: 522.5, referencia_mais_proxima: {id: 'code:130260', rotulo: 'MANAUS (AM)', empate: []}})]});
  const tefe = M.parDaBase(pelosMembros, 'code:130420');
  const [manaus] = tefe.referencias;
  assert.deepEqual([manaus.noGrafico, manaus.emAnalise, manaus.populacao, manaus.densidade], [true, false, 2000, 25]);
  assert.deepEqual(M.parDaBase(pelosMembros, 'code:130260').referencias, []);  // o próprio membro não tem outra referência
  assert.deepEqual(M.referenciasDeContexto([tefe]), []);
  assert.deepEqual(M.basesPossiveis(pelosMembros.itens).map(base => base.id), ['code:130420']);  // o membro é a referência, não base
  // Só estado visual: o pedido ao motor é o mesmo com ou sem bases; a definição começa com todos os selecionados, e o estado salvo
  // guarda a escolha (de antes de serem cumulativos, o único escolhido vira a lista).
  const espacial = definicao({nivel: 'municipios', base: {todos: false, estados: ['14'], ids: []}, familia: 'espacial',
    referencia: {relacao: 'mais_proxima', delimitacao: {tipo: 'todos'}, condicao: {atributo: 'densidade', operador: '>', valor: 2}}});
  assert.equal(M.definicaoInicial({tipo: 'brasil', periodos: ['202406'], categoria: 'MEDICINA', temGrupos: true}).territoriosBase, null);
  assert.deepEqual(M.montarOpcoes({...espacial, territoriosBase: ['code:140010']}, 'espacial'), M.montarOpcoes(espacial, 'espacial'));
  const salvar = def => M.salvarEstado('t', {chave: 'k', familia: 'espacial', opcoes: null, definicao: def,
    visual: {escala: 'linear', corte: null, selecionados: []}}, null);
  assert.deepEqual(M.lerEstadoSalvo(salvar({...espacial, territoriosBase: ['code:140010', 7]})).definicao.territoriosBase, ['code:140010']);
  assert.equal(M.lerEstadoSalvo(salvar({...espacial, territoriosBase: null})).definicao.territoriosBase, null);
  const antigo = M.lerEstadoSalvo(salvar({...espacial, territoriosBase: undefined, territorioBase: 'code:140010'})).definicao;
  assert.deepEqual([antigo.territoriosBase, 'territorioBase' in antigo], [['code:140010'], false]);
  assert.equal(M.lerEstadoSalvo(salvar({...espacial, territoriosBase: undefined, territorioBase: 7})).definicao.territoriosBase, null);
  // O gráfico cobre as referências de contexto: o eixo com o valor delas e a escala de tamanho com a população delas.
  const grafico = (extra = {}) => M.montarGrafico({itens: r.itens.slice(0, 2), dominios: {}, indicador: 'densidade', escala: 'linear',
    distancia: true, cometa: false, vista: 'final', largura: 900, rotuloDistancia: 'Distância (km)', pintura: () => ({cor: '#123', vazada: false, apagada: false}), ...extra});
  assert.equal(grafico().populacaoMaxima, 470169);
  assert.equal(grafico({extrasPopulacao: [900000]}).populacaoMaxima, 900000);
  assert.ok(grafico().eixoY.dominio[1] < 40, String(grafico().eixoY.dominio));
  const alto = grafico({extras: [40]});
  assert.ok(alto.eixoY.dominio[1] >= 40, String(alto.eixoY.dominio));
});

test('decisões 4 e 5 (25/10/2026): "maior/menor" da conversa vira o operador, e Limpar seleção tira só o nível em uso', () => {
  // Decisão 4: a ordem do critério da conversa vira o operador da condição; o valor de corte, a relação e a delimitação ficam com
  // a pessoa (nenhum território é escolhido pela posição na ordem).
  assert.equal(M.operadorDoCriterio({atributo: 'densidade', ordem: 'desc'}), '>');
  assert.equal(M.operadorDoCriterio({atributo: 'populacao', ordem: 'asc'}), '<');
  assert.equal(M.operadorDoCriterio(null), null);
  // Decisão 5: cada nível guarda a sua escolha. Em Municípios, saem os municípios e os conjuntos; em Estados, os estados; o resto fica.
  const municipios = {todos: false, estados: ['13'], ids: ['code:150140']};
  const conjunto = {nome: 'Conjunto 1', membros: ['code:130260', 'code:130340']};
  assert.deepEqual(M.limparNivel({nivel: 'municipios', base: municipios, estados: ['13', '15'], conjuntos: [conjunto]}),
    {nivel: 'municipios', base: {todos: false, estados: [], ids: []}, estados: ['13', '15'], conjuntos: []});
  assert.deepEqual(M.limparNivel({nivel: 'municipios', base: {todos: true, estados: [], ids: []}, estados: [], conjuntos: []}),
    {nivel: 'municipios', base: {todos: false, estados: [], ids: []}, estados: [], conjuntos: []});
  assert.deepEqual(M.limparNivel({nivel: 'estados', base: municipios, estados: ['13', '15'], conjuntos: [conjunto]}),
    {nivel: 'estados', base: municipios, estados: [], conjuntos: [conjunto]});
  // No nível Brasil, o país é a própria unidade; sem nada marcado no nível em uso, também não há o que limpar.
  assert.equal(M.limparNivel({nivel: 'brasil', base: municipios, estados: ['13'], conjuntos: []}), null);
  assert.equal(M.limparNivel({nivel: 'municipios', base: {todos: false, estados: [], ids: []}, estados: ['13'], conjuntos: []}), null);
  assert.equal(M.limparNivel({nivel: 'estados', base: municipios, estados: [], conjuntos: []}), null);
});

// ================================================================================================ ajustes de 25/10/2026
test('mapa com todas as unidades em análise: também as que o gráfico deixa de fora, no lugar delas, com os filtros que esmaecem', () => {
  // Roraima com o território de referência no mesmo estado: BOA VISTA fica sem distância; IRACEMA, sem o indicador.
  const boaVista = municipio('code:140010', 'BOA VISTA (RR)', {distancia_km: null});
  const altoAlegre = municipio('code:140005', 'ALTO ALEGRE (RR)', {distancia_km: 74.2});
  const iracema = municipio('code:140028', 'IRACEMA (RR)', {populacao: null, densidade: null, distancia_km: 83.3});
  const conjunto = {...municipio('c1', 'NORTE (soma)', {distancia_km: 10}), tipo: 'conjunto', membros: ['code:140005']};
  const roraima = {...municipio('uf:14', 'Roraima (RR)'), tipo: 'estado'};
  const itens = [iracema, conjunto, roraima, boaVista, altoAlegre];
  const {plotaveis, fora} = M.separarItens(itens.filter(item => item.tipo !== 'estado'), 'densidade', {distancia: true});
  assert.deepEqual(plotaveis.map(item => item.id), ['code:140005', 'c1'], 'no gráfico, só quem tem a distância e o indicador');
  assert.deepEqual(fora.map(item => [item.id, item.aspecto]), [['code:140010', 'distancia'], ['code:140028', 'indicador']]);
  // No mapa, todas as unidades (os estados não têm ponto; o conjunto dá o anel aos membros), na ordem neutra do gráfico.
  assert.deepEqual(M.itensParaOMapa(itens).map(item => item.id), ['code:140005', 'code:140010', 'code:140028', 'c1']);
  const filtros = {indicador: 'densidade', corte: null, soAtende: false, condicoes: false, filtroClasse: null, tendencia: false};
  assert.ok(M.itensParaOMapa(itens).every(item => M.dentroDosFiltros(item, filtros)), 'sem filtros, ninguém esmaece no mapa');
  // Com a régua, quem não tem o valor do indicador fica fora do corte (esmaece no mapa, nunca some); o conjunto não entra na régua.
  const corte = {minimo: 5, maximo: 20};
  assert.deepEqual(M.itensParaOMapa(itens).filter(item => !M.dentroDosFiltros(item, {...filtros, corte})).map(item => item.id), ['code:140028']);
  assert.deepEqual(M.itensParaOMapa(itens).filter(item => !M.dentroDosFiltros(item, {...filtros, corte: {minimo: 11, maximo: 20}}))
    .map(item => item.id), ['code:140005', 'code:140010', 'code:140028']);
  // Os mesmos filtros do gráfico: "Mostrar só quem atende" (com as condições no desenho) e a classe escolhida na tendência.
  const atende = municipio('code:1', 'A (AM)', {condicoes: {situacao: 'ATENDE', porCondicao: [], motivo: null}});
  const naoAtende = municipio('code:2', 'B (AM)', {condicoes: {situacao: 'NAO_ATENDE', porCondicao: [], motivo: null}});
  assert.equal(M.dentroDosFiltros(atende, {...filtros, soAtende: true, condicoes: true}), true);
  assert.equal(M.dentroDosFiltros(naoAtende, {...filtros, soAtende: true, condicoes: true}), false);
  assert.equal(M.dentroDosFiltros(naoAtende, {...filtros, soAtende: true, condicoes: false}), true, 'sem as condições no desenho, não filtra');
  const cresce = municipio('code:3', 'C (AM)', {tendencia: {classe: 'CRESCIMENTO', avaliavel: true}});
  const semClasse = municipio('code:4', 'D (AM)', {tendencia: {classe: null, avaliavel: false}});
  assert.equal(M.dentroDosFiltros(cresce, {...filtros, tendencia: true, filtroClasse: 'CRESCIMENTO'}), true);
  assert.equal(M.dentroDosFiltros(semClasse, {...filtros, tendencia: true, filtroClasse: 'CRESCIMENTO'}), false);
  assert.equal(M.dentroDosFiltros(semClasse, {...filtros, tendencia: true, filtroClasse: 'NAO_AVALIAVEL'}), true);
  // Sem camada de cor, a cor única não codifica nada: no mapa, a unidade sem o indicador fica vazada, nunca preenchida; a que
  // só não tem a distância continua com a cor única (o mapa não desenha a distância).
  const p = {camada: 'unica', indicador: 'densidade', limiteVariacao: 0, totalGrupos: 0, totalFaixas: 0, primeiros: null};
  assert.deepEqual(M.pintar(iracema, p), {cor: M.PALETA_CLARA.vazia, vazada: true, apagada: false});
  assert.deepEqual(M.pintar(boaVista, p), {cor: M.COR_BOLHA, vazada: false, apagada: false});
  assert.deepEqual(M.pintar(iracema, {...p, indicador: 'quantidade'}), {cor: M.COR_BOLHA, vazada: false, apagada: false},
    'com a quantidade, IRACEMA tem o valor do indicador');
});

test('fora do gráfico: o aviso diz quem ficou de fora e por quê, com o caminho do motivo e o mapa', () => {
  const boaVista = municipio('code:140010', 'BOA VISTA (RR)', {distancia_km: null});
  const altoAlegre = municipio('code:140005', 'ALTO ALEGRE (RR)', {distancia_km: 74.2});
  const iracema = municipio('code:140028', 'IRACEMA (RR)', {populacao: null, densidade: null, distancia_km: 83.3});
  const so = M.separarItens([boaVista, altoAlegre], 'densidade', {distancia: true}).fora;
  assert.equal(M.textoForaDoDesenho(so, {rotulos: BR, mapa: true}), 'Fora do gráfico, sem distância até a referência: BOA VISTA (RR). ' +
    'O motivo está em Não avaliáveis, nos Detalhes; no mapa, o município aparece no lugar dele.');
  assert.equal(M.textoForaDoDesenho(so, {rotulos: BR, mapa: false}), 'Fora do gráfico, sem distância até a referência: BOA VISTA (RR). ' +
    'O motivo está em Não avaliáveis, nos Detalhes.');
  // Dois motivos, cada um com os seus nomes; o indicador primeiro.
  const dois = M.separarItens([iracema, boaVista, altoAlegre], 'densidade', {distancia: true}).fora;
  assert.equal(M.textoForaDoDesenho(dois, {rotulos: BR, mapa: true}), 'Fora do gráfico, sem valor do indicador na competência: IRACEMA (RR). ' +
    'Sem distância até a referência: BOA VISTA (RR). O motivo de cada um está em Não avaliáveis, nos Detalhes; no mapa, os municípios ' +
    'aparecem no lugar deles.');
  // Muitos: os cinco primeiros pelo nome e a contagem; numa planilha, os nomes dela (no feminino, "cada uma" e "dela").
  const muitos = Array.from({length: 7}, (_, i) => ({id: 'code:' + (i + 1), rotulo: 'M' + (i + 1), tipo: 'municipio', aspecto: 'distancia', motivo: 'x'}));
  assert.equal(M.textoForaDoDesenho(muitos, {rotulos: BR, mapa: false}), 'Fora do gráfico, sem distância até a referência (7): M1, M2, M3, M4, M5 ' +
    'e mais 2. O motivo de cada um está em Não avaliáveis, nos Detalhes.');
  const unidades = {unidade: {singular: 'unidade', plural: 'unidades'}};
  assert.equal(M.textoForaDoDesenho(muitos.slice(0, 1), {rotulos: unidades, mapa: true}), 'Fora do gráfico, sem distância até a referência: M1. ' +
    'O motivo está em Não avaliáveis, nos Detalhes; no mapa, a unidade aparece no lugar dela.');
  // Um conjunto não tem ponto no mapa; a rotatividade sem coorte também fica dita. Os aspectos que não tiram do desenho não entram.
  assert.equal(M.textoForaDoDesenho([{id: 'c1', rotulo: 'NORTE (soma)', tipo: 'conjunto', aspecto: 'indicador', motivo: 'x'}], {rotulos: BR, mapa: true}),
    'Fora do gráfico, sem valor do indicador na competência: NORTE (soma). O motivo está em Não avaliáveis, nos Detalhes.');
  assert.match(M.textoForaDoDesenho([{id: 'code:9', rotulo: 'X', tipo: 'municipio', aspecto: 'rotatividade', motivo: 'x'}], {rotulos: BR, mapa: false}),
    /^Fora do gráfico, sem coorte inicial avaliável: X\./);
  assert.equal(M.textoForaDoDesenho([{id: 'code:9', rotulo: 'X', tipo: 'municipio', aspecto: 'variacao', motivo: 'x'},
    {id: 'code:8', rotulo: 'Y', tipo: 'municipio', aspecto: 'mapa', motivo: 'x'}], {rotulos: BR, mapa: true}), null);
  assert.equal(M.textoForaDoDesenho([], {rotulos: BR, mapa: true}), null);
});

test('bolhas: marcar não esmaece as outras; só a pintura apagada fica mais clara, e a bolha sem posição na vista, oculta', () => {
  // A opacidade não depende da seleção (25/10/2026): as marcadas ganham o anel escuro e o nome, como no mapa.
  assert.equal(M.opacidadeDaBolha({visivel: true, apagada: false}), 1);
  assert.equal(M.opacidadeDaBolha({visivel: true, apagada: true}), 0.45);
  assert.equal(M.opacidadeDaBolha({visivel: false, apagada: false}), 0);
  assert.equal(M.opacidadeDaBolha.length, 1, 'só a bolha decide: nada da seleção, do mouse ou do foco');
});
