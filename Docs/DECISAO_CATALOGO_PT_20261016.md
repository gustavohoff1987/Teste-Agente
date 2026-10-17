# APT-20261016 — autorização delimitada de apresentação em português

Status: autorizada pelo responsável pelo produto no comando de implementação de 16/10/2026, nesta tarefa. Escopo: repositório Teste-Agente, branch feat/novos-blocos-incrementais. Esta decisão é configuração governada externa às sessões analíticas; uma mensagem ao agente em execução não pode alterá-la.

Autoriza a integração técnica das formas PT existentes cuja correspondência com a SPEC seja comprovada, preservando texto, ID, versão, condições e referências. Não autoriza novas formas, paráfrase metodológica livre, alteração de cálculo ou aprovação tácita de EN.

O adendo ao final de IMPLEMENTATION_SPEC.md dá eficácia estritamente local a essa autorização, excepcionando apenas o impedimento de aceitação PT decorrente da revisão EN pendente (§4.4.23.4, passo 10; §4.4.23.5; §25.9/D31). O fechamento integral PT/EN continua pendente. Não há mudança de precedência do CONCEPT nem de competência do modelo.

## Fontes e integridade

- Catálogo incorporado por `3ee8bdce2e3086f676b3dae1e23cc59353b93be1`; SHA-256 Git UTF-8/LF: `65766f37c27d1f2bc0a32cfeef928cdc59cb1bd968ddcaeedb607139c8827d89`.
- Corpo original da SPEC 1.2.4, antes deste adendo: SHA-256 Git UTF-8/LF `5769399e20b2f3492970951aea4d8b499e9b16e7c09a26e01a83522f2e20a11b`. O adendo é acrescentado após o Anexo A para preservar seus localizadores; não reescreve textos catalogados.
- CONCEPT consultado em `../agente-diagnostico-territorial/Docs/CONCEPT.md`, na cópia local de origem. SHA-256 UTF-8 com normalização exclusiva CRLF→LF: `c095d81f010a34b8b8cea3f7885448d9b84a048bb3cb88331cfdc744e1dfe65f`, igual ao registrado em §25.9 da SPEC. O arquivo não foi copiado nem alterado.
- Compatibilidade: CONCEPT §§1.1/1.2, 5.1–5.8 e 8.10 separam competência linguística de autoridade factual/determinística, exigem configuração governada e permitem variação linguística com significado preservado. A decisão PT não amplia essas competências. Decisões DA/P/F/D incorporadas na SPEC permanecem aplicáveis; não foram encontrados registros separados de decisões neste checkout.

## Aplicação verificável

O carregador confere identidade do catálogo e do corpo da SPEC, inventário do Anexo A e identidade literal de todas as 703 formas-base PT. A apresentação usa apenas as formas para as quais o caminho implementado sabe comprovar condições e referências. Autorizar um literal não comprova a ocorrência de uma situação concreta.

EN permanece bloqueado neste incremento, inclusive quando uma forma isolada parece atual: nenhuma equivalência adicional foi aprovada. Não há tradução automática nem troca silenciosa de idioma. Uma revisão futura deve atualizar a autorização de forma rastreável, nunca durante uma sessão.

Esta autorização não corrige a divergência histórica de RQ-FLX-14 nem completa CAP-TEN-01. O incremento preserva os controles diretos e o motor existente; não declara conformidade integral do protótipo.
