# Regras de trabalho para agentes e pessoas

Valem para qualquer agente (Claude Code, Codex e outros) e para pessoas que alterem este repositório.
As regras marcadas com **(CI)** são conferidas automaticamente pelo GitHub Actions. Escreva a
documentação e os textos da interface em português do Brasil.

## 1. Mudança de comportamento: classificada antes de codar, registrada no mesmo commit (CI)

- **Mudança de comportamento** é qualquer alteração, em relação ao que o sistema faz hoje, que o
  usuário ou um consumidor da API perceba: telas, textos, fluxos, mensagens, cálculos, valores
  padrão, validações, exportações, contratos da API e dados versionados. **Remover uma função e
  implementar um item da SPEC também são mudanças de comportamento.** A SPEC diz o que o sistema deve
  fazer; o registro conta o que ele passou a fazer, quando e como.
- **Antes de codar, classifique cada item do pedido pela leitura, não por testes.** Com vários itens,
  classifique todos de uma vez, no início.
  1. Leia o pedido e o documento que descreve a área afetada (`README.md` ou `Docs/...`), que dizem
     o que o sistema faz hoje. **Sem mudança de comportamento**, siga para o código **sem consultar a
     SPEC**; o commit leva a linha `Comportamento: sem alteração — <motivo>`.
  2. **Com mudança de comportamento**, leia a SPEC (`IMPLEMENTATION_SPEC.md`) e as divergências já
     aprovadas no registro de comportamento e aplique dois testes:
     - **escopo:** a mudança decorre do pedido ou do item da SPEC que está sendo implementado?
     - **compatibilidade:** ela não contraria a SPEC nem uma divergência já aprovada?

     A previsão não é literal: o que a SPEC não descreve, mas também não contraria, passa no teste
     de compatibilidade.
  3. **Passou nos dois testes: mudança prevista.** Siga para o código e registre conforme os itens
     abaixo.
  4. **Falhou em um deles, mesmo que a mudança venha do pedido do responsável pelo produto: pare
     antes de implementá-la** e consulte o responsável, com o que muda, qual teste falhou e por quê,
     a alternativa (se houver) e o ajuste proposto na documentação. Com vários itens, junte as
     dúvidas numa só consulta; o que não depender delas segue. Aprovada, a mudança entra no
     registro, como divergência aprovada quando contrariar a SPEC. Recusada, siga sem ela ou com a
     alternativa escolhida.
- A classificação vale também para mudanças que surgem durante a implementação ou na correção de
  uma falha do CI.
- Na dúvida se há mudança de comportamento, trate como mudança. Na dúvida sobre escopo ou
  compatibilidade, pergunte ao responsável.
- No **mesmo commit** da mudança:
  - acrescente uma entrada em [`Docs/REGISTRO_DE_COMPORTAMENTO.md`](Docs/REGISTRO_DE_COMPORTAMENTO.md),
    seguindo o modelo do próprio arquivo;
  - atualize o documento que descreve aquele comportamento (`README.md` ou `Docs/...`). Se nenhum
    documento o descreve, crie a seção.
- Se o commit altera arquivos do produto **sem** mudar comportamento, escreva na mensagem a linha
  `Comportamento: sem alteração — <motivo>`.
- Nenhum documento pode continuar afirmando algo que o código deixou de fazer.

## 2. Integridade dos dados

- `Dados_Brasil.xlsx`, `Dados_Estados_Brasil.csv`, `Dados_Municipios_Brasil.csv` e `dados/brasil/` só mudam
  por pedido explícito do responsável pelo produto, **nunca** para fazer um teste passar.
- O backend recusa arquivos que divergem de `dados/brasil/manifesto.json` (tamanho e SHA-256).
  Para conferir: `python backend/brazil_data.py diagnostico` deve mostrar `"integridade": "verificada"`.
- Para atualizar a base, siga esta ordem:
  1. substitua os arquivos;
  2. regrave o manifesto com `python backend/brazil_data.py manifesto --gravar`;
  3. revise o diff;
  4. registre a mudança (regra 1);
  5. envie e acompanhe no CI os testes com dados reais (job `dados-reais`, seção 5).
- Testes com dados reais são somente leitura. Eles conferem os hashes antes e depois.
- Nenhum arquivo, linha, registro individual, identificador, nome de campo ou credencial vai para o provedor de IA.
  Só vão a mensagem triada, a janela da conversa triada, estados técnicos e os resultados agregados exibidos na tela
  (decisão de 26/10/2026; README, "Política dos dados do Brasil", e Adendo PAR-20261026 da SPEC).

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
  - `validar_gemini_real.py`: amostra pequena e delimitada de conversas com o Gemini real (com `GEMINI_API_KEY`), com
    teto de chamadas próprio; fora do CI.
