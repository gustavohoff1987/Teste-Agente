"""Catálogo de operações existentes, compartilhado pelo motor e pela conversa."""
OPERATION_LABELS = {
    "density": "Densidade", "counts": "Quantitativos", "distribution": "Distribuição",
    "comparisons": "Comparações", "temporal": "Evolução temporal", "aggregate": "Agregações",
    "spatial": "Análise espacial", "ranking": "Recortes e rankings",
    "rotation": "Rotatividade", "report": "Relatórios",
}
# Capacidades do motor fora do contrato de interpretação do LLM (Bloco 2, Etapas 1 e 2): a conversa
# só as prepara por comando determinístico; o LLM não as propõe nem recebe seu estado.
ENGINE_ONLY_LABELS = {"nearest": "Referência mais próxima", "criteria": "Critérios combinados"}
ENGINE_OPERATION_LABELS = {**OPERATION_LABELS, **ENGINE_ONLY_LABELS}
