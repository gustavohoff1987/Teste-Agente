# Roteiros de navegador legados (não executados)

Estes 7 roteiros testavam a interface **anterior ao redesenho conversacional de 12/10/2026**. Foram
movidos para cá em 15/10/2026 por três motivos:

1. **Nunca rodaram no CI.** Por isso, suas falhas não apareciam em lugar nenhum.
2. **Falham contra a interface atual logo nos primeiros passos.** Execução de 15/10/2026 no commit
   `dbaa0bd`:
   - `ui_audit_smoke.py`: falta o texto "temporal.csv carregado";
   - `ui_carousel_smoke.py`: falta `#analises button[aria-pressed]`;
   - `ui_preparation_smoke.py`: falta o botão "Usar dados do Brasil" no painel antigo;
   - `ui_session_smoke.py`: falta "Proposta simulada…" no histórico da conversa;
   - `ui_integration_smoke.py`: falta "Sugestão preliminar: Densidade";
   - `ui_brazil_smoke.py` e `ui_smoke.py`: exigiam `ADT_REAL_DATA_DIR` e também usam o fluxo antigo.
3. **Mantê-los em `backend/tests/` dava uma falsa impressão de cobertura.**

Ficam aqui apenas como referência para reescrita. **Não rodam como estão**, porque importam
`ui_support.py` de `backend/tests/`, cujas funções `select`, `stage` e `card` existem só para eles.
Novos roteiros de navegador devem ficar em `backend/tests/` e ser registrados em
`backend/tests/run_ui_checks.py`. A verificação de governança do CI recusa roteiros ativos que não rodam.

## O que cobriam e onde essa cobertura está hoje

| Roteiro legado | O que cobria | Cobertura atual no CI | Lacuna |
|---|---|---|---|
| `ui_audit_smoke.py` | A02 indicadores explícitos e navegação; A05 CSV em precisão integral; A08; A10 falha do pré-exame com orientação local | A05: `ui_block1_smoke`/`ui_block1_regression` conferem CSV e JSON contra o motor. A10: recuperação em `ui_block1_integration` | A02 e A08 na interface atual |
| `ui_carousel_smoke.py` | 10 cartões; teclado, roda do mouse, Ctrl+roda reservado ao zoom, deslizar no celular, movimento reduzido | Navegação pelo carrossel em `ui_visibility_diagnostic`; larguras de 390 e 768 px em `ui_block1_smoke` | Teclado, roda, deslizar e movimento reduzido no carrossel atual |
| `ui_preparation_smoke.py` | Etapas da preparação antiga; confirmação de código; distribuição com população; revalidação que não reaproveita habilitação; upload independente do catálogo | Preparação na conversa em `ui_conversational_smoke`, `ui_block1_*`; troca de fonte em `ui_block1_regression` | Erro de revalidação na preparação atual |
| `ui_session_smoke.py` | Aceite de privacidade e foco preso no modal; `sessionStorage` bloqueado; nova aba = nova sessão; falha e recuperação da conversa | Aceite ("Li e concordo") em todas as jornadas; recuperação em `ui_block1_integration` | Foco no modal, armazenamento bloqueado, nova aba |
| `ui_integration_smoke.py` | 14 verificações: fluxo preliminar, A09–A13, troca nacional/municipal, concorrência, XLSX com duas abas, XLS, CSV malformado, extensão não suportada, minimização ao provedor | XLSX com duas abas em `ui_block1_regression`; A12 e minimização em `ui_block1_integration`; XLS e extensão não suportada na API (`test_upload_api.py`); CSV malformado na API (`test_upload_api.py`, desde 15/10/2026) | Concorrência (resposta pendente invalidada) e XLS/CSV malformado vistos no navegador |
| `ui_brazil_smoke.py` | Catálogo Brasil: CSV nacional, densidade municipal, troca de abrangência, upload internacional, celular (dados reais) | Jornada do Bloco 1 com a base versionada (suíte `base-versionada`) e suíte de dados reais do backend (job `dados-reais`) | Troca de abrangência nacional/municipal com dados reais no navegador |
| `ui_smoke.py` | Upload real do CSV municipal (122.534 linhas) e exportação conferida linha a linha contra o original | Testes de dados reais do backend conferem todas as linhas com aritmética independente (job `dados-reais`) | Upload do arquivo grande pelo navegador |

As lacunas acima são a lista de trabalho para os próximos roteiros. Escreva cada roteiro contra a
interface vigente e registre-o em `run_ui_checks.py`.
