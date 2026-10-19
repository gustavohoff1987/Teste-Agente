# Regras de trabalho para agentes e pessoas

Valem para qualquer agente (Claude Code, Codex e outros) e para pessoas que alterem este repositório.
As regras marcadas com **(CI)** são conferidas automaticamente pelo GitHub Actions. Escreva a
documentação e os textos da interface em português do Brasil.

## 1. Mudança de comportamento é documentada no mesmo commit (CI)

- **Mudança de comportamento** é qualquer alteração que o usuário ou um consumidor da API perceba:
  telas, textos, fluxos, mensagens, cálculos, valores padrão, validações, exportações, contratos da
  API e dados versionados. **Remover uma função também é mudança de comportamento.**
- **Antes de codar**, leia a SPEC (`IMPLEMENTATION_SPEC.md`) e o documento que descreve a área
  afetada (`README.md` ou `Docs/...`) e classifique a mudança. A classificação é feita pela leitura,
  não por testes:
  - **sem mudança de comportamento:** siga para o código;
  - **mudança prevista**, isto é, descrita na SPEC ou decidida pelo responsável pelo produto (no
    pedido da tarefa ou em decisão registrada em `Docs/`): siga para o código e registre a mudança
    conforme os itens abaixo;
  - **mudança não prevista**, que nem a SPEC nem uma decisão do responsável cobrem (por exemplo, um
    efeito colateral ou uma alteração que a implementação parece exigir): **pare antes de
    implementá-la** e devolva ao responsável pelo produto para validação, com o que muda, por que, a
    alternativa sem a mudança (se houver) e o ajuste proposto na documentação. Só continue depois da
    validação explícita. Isso vale também quando a correção de uma falha do CI exigir a mudança.
  - Na dúvida entre prevista e não prevista, pergunte ao responsável.
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
  5. envie e acompanhe no CI os testes com dados reais (job `dados-reais`, seção 5).
- Testes com dados reais são somente leitura. Eles conferem os hashes antes e depois.
- Nenhum dado, arquivo, nome de campo ou valor da base vai para o provedor de IA (README,
  "Política dos dados do Brasil").

## 3. Testes

- **Nunca** enfraqueça, pule, apague ou afrouxe um teste para o CI ficar verde. Antes de mexer num
  teste que falha, descubra se o defeito está no produto ou no teste e registre a conclusão no commit.
- Uma mudança de comportamento traz, no mesmo commit, os testes que a cobrem. Quem os executa é o CI
  (seção 4).
- Se um teste muda porque o comportamento mudou de propósito, a mudança é registrada no mesmo commit
  (regra 1).
- Mover ou apagar um teste exige registrar onde a cobertura passou a existir, como em
  `backend/tests/legado/README.md`.
- **(CI)** Todo roteiro de navegador `backend/tests/ui_*.py` precisa estar registrado em
  `backend/tests/run_ui_checks.py`, ou seja, precisa rodar no CI.
- **(CI)** Com a base versionada, nenhum teste pode ficar pulado (job `dados-reais`).
- Nos roteiros de navegador, prefira seletores estáveis: `data-testid`, ou papel com nome exato e
  único. Evite textos que podem se repetir na tela.

## 4. O CI é o único ambiente de verificação

Os testes e as verificações de integridade rodam só no CI, que executa todos os jobs em todo push
(seção 5). O trabalho só termina com o CI em PASS. Decisão do responsável pelo produto em 19/10/2026,
que substitui a verificação local proporcional de 18/10/2026.

- **Não rode localmente:** a suíte pytest, os testes com dados reais, os roteiros de navegador, o
  `npm run build`, `scripts/verificar_tudo.py` e as capturas de `scripts/capturar_telas.py`. Eles só
  rodam localmente por pedido explícito do responsável.
- **Antes do push, só checagens de segundos:**
  - Python alterado: `python -m py_compile <arquivos alterados>`;
  - TypeScript alterado: `(cd frontend && npx --no-install tsc --noEmit)`, quando
    `frontend/node_modules` já existir (sem ele, não instale só para isso);
  - depois do commit, a governança: `python .github/scripts/verificar_governanca.py`.
- Se uma dessas checagens não puder rodar no seu ambiente (por exemplo, a governança num clone raso),
  diga isso no relato e siga: o CI confere.
- **Exceção única:** para diagnosticar uma falha do CI que o log não explica, rode localmente só o
  teste que falhou.

Para reproduzir localmente, quando pedido: `run_ui_checks.py --roteiro <arquivo>` roda só os roteiros
indicados, e `--suite` roda uma suíte inteira (sem o Google Chrome: `ADT_BROWSER_CHANNEL=chromium`).
No Windows, rode o pytest com `PYTHONUTF8=1` e uma pasta temporária gravável (`--basetemp`);
`scripts/verificar_tudo.py` já faz isso.

## 5. Commits, envio e CI

- Código, testes e documentação de uma mudança vão **no mesmo commit**. Não deixe um commit quebrado
  à espera do commit seguinte.
- Envie a sequência de commits **num único push**. Cada envio dispara o CI completo.
- O CI roda no push dos ramos listados em `.github/workflows/ci.yml` e em qualquer pull request. Num
  ramo fora da lista, abra um pull request para que o CI rode.
- Depois de cada push, acompanhe o GitHub Actions até PASS em todos os jobs obrigatórios; o job
  `resumo` reúne os resultados. Com o GitHub CLI:
  - `gh run list --commit "$(git rev-parse HEAD)" --limit 1` mostra o `<id>` da execução;
  - `gh run watch <id> --exit-status` acompanha até o fim;
  - na falha, `gh run view <id> --log-failed` mostra o log dos passos que falharam.
- **CI vermelho nunca é normal.** Comece pelo job `resumo`, corrija só o que falhou, envie de novo e
  só depois inicie outra mudança.
- **No máximo 3 rodadas de correção** para a mesma falha. Se ela persistir, pare e relate ao
  responsável o que falhou, a hipótese de causa e o que foi tentado.
- Falha sem relação com a sua mudança (teste instável ou falha que já existia antes do seu push):
  reexecute uma vez os jobs que falharam (`gh run rerun <id> --failed`). Se persistir, relate ao
  responsável em vez de investigar por conta própria.
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
  - `verificar_tudo.py`: verificação completa local, na ordem, com o resultado de cada passo e um
    resumo final; só por pedido explícito do responsável (seção 4).
  - `capturar_telas.py`: capturas das telas principais com a base versionada, para a conferência
    visual; só por pedido explícito do responsável (seção 4).
