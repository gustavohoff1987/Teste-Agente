# Regras de trabalho para agentes e pessoas

Valem para qualquer agente (Claude Code, Codex e outros) e para pessoas que alterem este repositório.
As regras marcadas com **(CI)** são conferidas automaticamente pelo GitHub Actions. Escreva a
documentação e os textos da interface em português do Brasil.

## 1. Mudança de comportamento é documentada no mesmo commit (CI)

- **Mudança de comportamento** é qualquer alteração que o usuário ou um consumidor da API perceba:
  telas, textos, fluxos, mensagens, cálculos, valores padrão, validações, exportações, contratos da
  API e dados versionados. **Remover uma função também é mudança de comportamento.**
- No **mesmo commit** da mudança:
  - acrescente uma entrada em [`Docs/REGISTRO_DE_COMPORTAMENTO.md`](Docs/REGISTRO_DE_COMPORTAMENTO.md),
    seguindo o modelo do próprio arquivo;
  - atualize o documento que descreve aquele comportamento (`README.md` ou `Docs/...`). Se nenhum
    documento o descreve, crie a seção.
- Se o commit altera arquivos do produto **sem** mudar comportamento, escreva na mensagem a linha
  `Comportamento: sem alteração — <motivo>`.
- Na dúvida, trate como mudança de comportamento e registre.
- Nenhum documento pode continuar afirmando algo que o código deixou de fazer.

## 2. Integridade dos dados

- `Dados_Brasil.xlsx`, `Dados_Municipios_Brasil.csv` e `dados/brasil/` só mudam por pedido explícito
  do responsável pelo produto, **nunca** para fazer um teste passar.
- O backend recusa arquivos que divergem de `dados/brasil/manifesto.json` (tamanho e SHA-256).
  Para conferir: `python backend/brazil_data.py diagnostico` deve mostrar `"integridade": "verificada"`.
- Para atualizar a base, siga esta ordem:
  1. substitua os arquivos;
  2. regrave o manifesto com `python backend/brazil_data.py manifesto --gravar`;
  3. revise o diff;
  4. registre a mudança (regra 1);
  5. rode os testes com dados reais (seção 4).
- Testes com dados reais são somente leitura. Eles conferem os hashes antes e depois.
- Nenhum dado, arquivo, nome de campo ou valor da base vai para o provedor de IA (README,
  "Política dos dados do Brasil").

## 3. Testes

- **Nunca** enfraqueça, pule, apague ou afrouxe um teste para o CI ficar verde. Antes de mexer num
  teste que falha, descubra se o defeito está no produto ou no teste e registre a conclusão no commit.
- Se um teste muda porque o comportamento mudou de propósito, a mudança é registrada no mesmo commit
  (regra 1).
- Mover ou apagar um teste exige registrar onde a cobertura passou a existir, como em
  `backend/tests/legado/README.md`.
- **(CI)** Todo roteiro de navegador `backend/tests/ui_*.py` precisa estar registrado em
  `backend/tests/run_ui_checks.py`, ou seja, precisa rodar no CI.
- **(CI)** Com a base versionada, nenhum teste pode ficar pulado (job `dados-reais`).
- Nos roteiros de navegador, prefira seletores estáveis: `data-testid`, ou papel com nome exato e
  único. Evite textos que podem se repetir na tela.

## 4. Verificação proporcional antes do push

A verificação local é proporcional à natureza, ao alcance e ao risco da mudança (decisão do
responsável pelo produto em 18/10/2026). Rodar toda a suíte localmente antes de cada push não é
obrigatório: o CI roda todas as verificações em todo push, e o trabalho só termina com o CI em PASS
(seção 5). Microajustes não pedem a verificação completa. Amplie o escopo quando houver risco
concreto de integração, regressão ou violação de governança.

Obrigatório antes de cada push:

- rodar as verificações ligadas ao que mudou, conforme a tabela abaixo;
- depois do commit, rodar a governança: `python .github/scripts/verificar_governanca.py` (leva segundos);
- se uma verificação obrigatória não puder rodar no seu ambiente, dizer isso explicitamente ao
  responsável, sem presumir que ela passaria.

| O que mudou | Verificação local |
|---|---|
| Código do backend | os testes dos módulos alterados; em mudança ampla ou compartilhada, `(cd backend && python -m pytest -q)` |
| Motor, API ou dados | também os testes com dados reais: `(cd backend && ADT_REAL_DATA_DIR="$(cd .. && pwd)" python -m pytest -q -rs)` |
| Dados versionados | a ordem da regra 2, com a integridade (`python backend/brazil_data.py diagnostico`) e os testes com dados reais |
| Frontend | `(cd frontend && npm run build)`, que inclui TypeScript e os testes Node, e os roteiros de navegador afetados |
| Dependências do frontend | `npm ci` antes do build. Localmente, só quando `package.json` ou `package-lock.json` mudaram desde o último `npm ci` bem-sucedido; o CI roda sempre |
| Roteiro de navegador | o próprio roteiro: `python backend/tests/run_ui_checks.py --roteiro ui_exemplo.py` |
| Só documentação | a governança |

Ferramentas: `run_ui_checks.py --roteiro <arquivo>` roda só os roteiros indicados, e `--suite` roda
uma suíte inteira (sem o Google Chrome: `ADT_BROWSER_CHANNEL=chromium`). Quando o risco justificar,
`python scripts/verificar_tudo.py` faz a verificação completa, na ordem e com resumo. No Windows, rode
o pytest com `PYTHONUTF8=1` e uma pasta temporária gravável (`--basetemp`); o script já faz isso.

## 5. Commits, envio e CI

- Código, testes e documentação de uma mudança vão **no mesmo commit**. Não deixe um commit quebrado
  à espera do commit seguinte.
- Envie a sequência de commits **num único push**. Cada envio dispara o CI completo.
- Depois de cada push, acompanhe o GitHub Actions até PASS em todos os jobs obrigatórios; o job
  `resumo` reúne os resultados.
- **CI vermelho nunca é normal.** Comece pelo job `resumo`, corrija a falha e só depois inicie outra
  mudança.
- Não afrouxe `.github/workflows/ci.yml` sem pedido explícito e registro. Isso inclui remover jobs,
  usar `continue-on-error`, pular testes e trocar dados reais por sintéticos.
- Não altere `IMPLEMENTATION_SPEC.md` (SPEC) sem pedido explícito.

## 6. Mapa rápido

- `backend/`: API FastAPI, motor determinístico, ponte semântica e integração opcional com Gemini.
- `frontend/src/`: interface React + Vite.
- `backend/tests/`: contém os seguintes tipos de arquivo.
  - `test_*.py`: pytest.
  - `ui_*.py`: roteiros de navegador, rodados pelo `run_ui_checks.py`.
  - `serve_*.py` e `prepare_*.py`: servidores e catálogos de teste.
  - `bench_*.py`: medições de tempo, fora do CI.
  - `legado/`: roteiros obsoletos, que não rodam.
- `README.md`, `Docs/` e [`Docs/REGISTRO_DE_COMPORTAMENTO.md`](Docs/REGISTRO_DE_COMPORTAMENTO.md): documentação.
- `.github/workflows/ci.yml` e `.github/scripts/verificar_governanca.py`: CI e governança.
- `scripts/`: ferramentas de desenvolvimento, fora do produto e do CI.
  - `verificar_tudo.py`: verificação completa (todos os passos da seção 4, na ordem), com o resultado de
    cada passo e um resumo final, para quando o risco justificar.
  - `capturar_telas.py`: capturas das telas principais com a base versionada, para a conferência visual.
