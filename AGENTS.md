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

## 4. Antes de cada push

Rode na raiz e só envie se tudo passar:

```bash
(cd backend && python -m pytest -q)
(cd frontend && npm ci && npm run build)        # npm ci: veja a dispensa logo abaixo
python backend/tests/run_ui_checks.py           # sem o Google Chrome: ADT_BROWSER_CHANNEL=chromium
python .github/scripts/verificar_governanca.py
```

Na verificação local, o `npm ci` pode ser dispensado quando `package.json` e `package-lock.json`
não mudaram desde o último `npm ci` bem-sucedido; nesse caso, rode só `npm run build` (decisão do
responsável pelo produto em 18/10/2026). O CI continua rodando `npm ci` sempre.

Se a mudança toca o motor, a API ou os dados, rode também:

```bash
(cd backend && ADT_REAL_DATA_DIR="$(cd .. && pwd)" python -m pytest -q -rs)
```

Se alguma verificação não puder rodar no seu ambiente, diga isso explicitamente ao responsável.
Não presuma que ela passaria.

## 5. Commits, envio e CI

- Código, testes e documentação de uma mudança vão **no mesmo commit**. Não deixe um commit quebrado
  à espera do commit seguinte.
- Envie a sequência de commits **num único push**. Cada envio dispara o CI completo.
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
