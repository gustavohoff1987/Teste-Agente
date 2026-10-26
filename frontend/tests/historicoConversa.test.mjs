import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// Histórico da conversa (26/10/2026): a conversa inteira à vista, em ordem, sem duplicar; a janela que vai ao backend é
// separada do histórico da tela; a indisponibilidade aparece como aviso cordial, sem código nem mensagem técnica.
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const H = await source('historicoConversa');

test('mensagens entram em ordem, com ids únicos, e o mesmo id não duplica', () => {
  const usuario = {id: H.novoId('usuario'), papel: 'usuario', texto: 'Compare Rio de Janeiro com Porto Alegre.'};
  const agente = {id: H.novoId('agente'), papel: 'agente', texto: 'Você se refere ao município ou ao estado do Rio de Janeiro?'};
  const resposta = {id: H.novoId('usuario'), papel: 'usuario', texto: 'Município.'};
  let lista = H.acrescentar([], usuario);
  lista = H.acrescentar(lista, agente);
  lista = H.acrescentar(lista, resposta);
  lista = H.acrescentar(lista, agente);  // renderização repetida do mesmo estado
  assert.deepEqual(lista.map(m => m.texto), [usuario.texto, agente.texto, 'Município.']);
  assert.equal(new Set([usuario.id, agente.id, resposta.id]).size, 3);
  assert.equal(H.ultimaResposta(lista).id, agente.id);
});

test('a mensagem da pessoa fica exatamente como foi escrita; a janela enviada é só a mais recente e sem avisos', () => {
  const texto = 'Meu CPF é 123.456.789-00 e quero ver Maria em Tefé';
  const lista = [];
  for (let i = 0; i < 12; i += 1) lista.push({id: 'u' + i, papel: i % 2 ? 'agente' : 'usuario', texto: 'mensagem ' + i});
  lista.push({id: 'aviso', papel: 'aviso', titulo: H.TITULO_INDISPONIVEL, texto: H.TEXTO_INDISPONIVEL});
  lista.push({id: 'u-final', papel: 'usuario', texto});
  const janela = H.turnosParaEnvio(lista);
  assert.equal(janela.length, H.MAX_TURNOS_ENVIADOS);
  assert.deepEqual(janela.at(-1), {papel: 'usuario', texto});  // a triagem é do backend; a tela não altera o texto
  assert.ok(janela.every(t => t.texto !== H.TEXTO_INDISPONIVEL));
  assert.equal(lista.length, 14);  // o histórico da tela continua inteiro
  const longo = H.turnosParaEnvio([{id: 'x', papel: 'agente', texto: 'a'.repeat(2000)}]);
  assert.equal(longo[0].texto.length, H.MAX_CARACTERES_POR_TURNO);
});

test('a rolagem só acompanha quem está no fim da conversa', () => {
  assert.equal(H.estaNoFim(900, 1300, 400), true);
  assert.equal(H.estaNoFim(870, 1300, 400), true);   // dentro da margem
  assert.equal(H.estaNoFim(200, 1300, 400), false);  // lendo mensagens antigas
});

test('avisos cordiais conforme a causa, sem código HTTP nem mensagem técnica', () => {
  assert.deepEqual(H.avisoDeFalha(429), {tipo: 'cota', titulo: H.TITULO_INDISPONIVEL, texto: H.TEXTO_COTA});
  for (const status of [500, 502, 503, 504, null, 0]) {
    const aviso = H.avisoDeFalha(status, 'Traceback: HTTP 503 RESOURCE_EXHAUSTED');
    assert.equal(aviso.tipo, 'indisponivel');
    assert.equal(aviso.texto, H.TEXTO_INDISPONIVEL);
  }
  assert.deepEqual(H.avisoDeFalha(422, 'Mensagem acima do limite de 800 caracteres.'),
    {tipo: 'entrada', texto: 'Mensagem acima do limite de 800 caracteres.'});
  assert.equal(H.avisoDeFalha(422, 'Erro HTTP 422').tipo, 'indisponivel');
  for (const texto of [H.TEXTO_COTA, H.TEXTO_INDISPONIVEL, H.TITULO_INDISPONIVEL])
    assert.ok(!/HTTP|\b\d{3}\b|RESOURCE_EXHAUSTED|quota|rate limit/i.test(texto));
  assert.ok(!H.TEXTO_INDISPONIVEL.includes('limite'));  // indisponibilidade não é anunciada como limite de consultas
});

test('o aviso da resposta do backend vira mensagem de aviso no histórico', () => {
  const corpo = {reply: H.TEXTO_COTA, indisponibilidade: {tipo: 'cota', titulo: H.TITULO_INDISPONIVEL, texto: H.TEXTO_COTA}};
  const aviso = H.avisoDaResposta(corpo);
  assert.deepEqual(aviso, {tipo: 'cota', titulo: H.TITULO_INDISPONIVEL, texto: H.TEXTO_COTA});
  const mensagem = H.mensagemDeAviso(aviso);
  assert.equal(mensagem.papel, 'aviso');
  assert.equal(mensagem.titulo, H.TITULO_INDISPONIVEL);
  assert.equal(H.avisoDaResposta({reply: 'ok'}), null);
  assert.equal(H.mensagemDeAviso({tipo: 'entrada', texto: 'Escolha a planilha.'}).papel, 'agente');
});

test('os textos da tela são os mesmos do backend', () => {
  const backend = readFileSync(new URL('../../backend/llm_bridge.py', import.meta.url), 'utf8');
  const junta = nome => backend.split(nome + ' = (')[1].split(')\n')[0].match(/"([^"]*)"/g).map(t => t.slice(1, -1)).join('');
  assert.equal(junta('TEXTO_COTA'), H.TEXTO_COTA);
  assert.equal(junta('TEXTO_INDISPONIVEL'), H.TEXTO_INDISPONIVEL);
  assert.ok(backend.includes('TITULO_INDISPONIVEL = "' + H.TITULO_INDISPONIVEL + '"'));
});

// Ajustes de 26/10/2026: a hora no balão, a resposta em blocos de leitura (sem reescrever o texto), a rolagem que mantém a
// pergunta à vista numa resposta longa e o aviso do prazo da tela (o pedido não fica girando sem fim).
test('a hora da mensagem fica no formato HH:MM', () => {
  assert.equal(H.horaDaMensagem(new Date(2026, 9, 26, 9, 5)), '09:05');
  assert.equal(H.horaDaMensagem(new Date(2026, 9, 26, 23, 41)), '23:41');
  assert.match(H.horaDaMensagem(), /^\d{2}:\d{2}$/);
});

test('a resposta em blocos: parágrafos, rótulo e exemplos realçados, e o texto juntado é o original', () => {
  const texto = 'Em junho de 2024, o gráfico tem 144 municípios. A densidade vai de 0,27 a 5,70 por 1.000 habitantes.\n\n' +
    'Maior valor de densidade: OURILANDIA DO NORTE (PA) (5,70 por 1.000 habitantes). Menor valor: BAIAO (PA).\n\n' +
    'Se quiser, peça, por exemplo, “compare o de maior e o de menor densidade” ou “mostre a tendência anual”.\n- um item\n- outro';
  const blocos = H.blocosDoTexto(texto);
  const juntar = lista => lista.map(bloco => bloco.tipo === 'separador' ? bloco.texto : bloco.trechos.map(t => t.texto).join('')).join('');
  assert.equal(juntar(blocos), texto, 'a tela só realça: o conteúdo é o mesmo');
  assert.deepEqual(blocos.map(bloco => bloco.tipo), ['paragrafo', 'separador', 'paragrafo', 'separador', 'paragrafo']);
  assert.deepEqual(blocos[2].trechos[0], {tipo: 'rotulo', texto: 'Maior valor de densidade:'});
  assert.equal(blocos[0].trechos.some(t => t.tipo === 'rotulo'), false, 'frase comum não vira rótulo');
  assert.deepEqual(blocos[4].trechos.filter(t => t.tipo === 'exemplo').map(t => t.texto),
    ['“compare o de maior e o de menor densidade”', '“mostre a tendência anual”']);
  for (const solto of ['', 'Uma frase só.', '\n\nComeça com linha em branco', 'Aspas “sem fim', 'Fórmula: D(u, p, c) = Q / P'])
    assert.equal(juntar(H.blocosDoTexto(solto)), solto);
});

test('a rolagem mantém a pergunta curta à vista quando a resposta é longa', () => {
  // As duas cabem: vai ao fim.
  assert.equal(H.posicaoDaRolagem({fim: 1000, altura: 400, topoDaNova: 800, topoDaAnterior: 700, alturaDaAnterior: 60,
    anteriorDaPessoa: true}), 600);
  // Resposta longa depois de uma pergunta curta: a pergunta no alto, com o começo da resposta logo abaixo.
  assert.equal(H.posicaoDaRolagem({fim: 2000, altura: 400, topoDaNova: 1100, topoDaAnterior: 1040, alturaDaAnterior: 50,
    anteriorDaPessoa: true}), 1032);
  // A anterior não é pergunta da pessoa (uma continuação): no fim, se a nova cabe; senão, o começo da nova.
  assert.equal(H.posicaoDaRolagem({fim: 2000, altura: 400, topoDaNova: 1700, topoDaAnterior: 1000, alturaDaAnterior: 600,
    anteriorDaPessoa: false}), 1600);
  assert.equal(H.posicaoDaRolagem({fim: 2000, altura: 400, topoDaNova: 1100, topoDaAnterior: 1000, alturaDaAnterior: 90,
    anteriorDaPessoa: false}), 1092);
  // Pergunta longa demais para ficar no alto: o começo da resposta.
  assert.equal(H.posicaoDaRolagem({fim: 2000, altura: 400, topoDaNova: 1300, topoDaAnterior: 1000, alturaDaAnterior: 300,
    anteriorDaPessoa: true}), 1292);
  // Nunca fora dos limites da rolagem.
  assert.equal(H.posicaoDaRolagem({fim: 300, altura: 400, topoDaNova: 100, topoDaAnterior: null, alturaDaAnterior: 0,
    anteriorDaPessoa: false}), 0);
});

test('o prazo da tela vira aviso cordial próprio, sem código nem mensagem técnica', () => {
  const aviso = H.avisoDeDemora();
  assert.deepEqual(aviso, {tipo: 'tempo', titulo: H.TITULO_DEMORA, texto: H.TEXTO_DEMORA});
  assert.equal(H.mensagemDeAviso(aviso).papel, 'aviso');
  assert.ok(!/HTTP|\b\d{3}\b|timeout|Abort/i.test(H.TITULO_DEMORA + H.TEXTO_DEMORA));
});
