"""Catálogo de operações existentes, compartilhado pelo motor e pela conversa."""
OPERATION_LABELS = {
    "density": "Densidade", "counts": "Quantitativos", "distribution": "Distribuição",
    "comparisons": "Comparações", "temporal": "Evolução temporal", "aggregate": "Agregações",
    "spatial": "Análise espacial", "ranking": "Recortes e rankings",
    "rotation": "Rotatividade", "report": "Relatórios",
}
# Capacidades do motor fora do contrato de interpretação do LLM (Bloco 2, Etapa 1): a conversa
# só as prepara por comando determinístico; o LLM não as propõe nem recebe seu estado.
ENGINE_ONLY_LABELS = {"nearest": "Referência mais próxima"}
ENGINE_OPERATION_LABELS = {**OPERATION_LABELS, **ENGINE_ONLY_LABELS}
