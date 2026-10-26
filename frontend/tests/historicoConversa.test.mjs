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
