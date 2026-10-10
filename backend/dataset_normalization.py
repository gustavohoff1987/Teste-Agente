"""Adaptações estruturais em memória, preservando as colunas do arquivo."""
import re
import unicodedata

import pandas as pd


def _header(value):
    value = unicodedata.normalize("NFKD", str(value).strip().lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def compose_period(frame):
    """Propõe AAAAMM somente para o par explícito periodo_ano/periodo_mes.

    Não substitui períodos existentes, não agrega registros e não confirma
    significados. A mesma transformação é aplicada em todas as rotas.
    """
    sources = [[c for c in frame.columns if _header(c) == name]
               for name in ("periodo ano", "periodo mes")]
    if any(len(columns) != 1 for columns in sources):
        return frame
    year_column, month_column = (columns[0] for columns in sources)
    values = []
    for column, low, high in ((year_column, 1000, 9999), (month_column, 1, 12)):
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if (numeric.isna() | ~numeric.between(low, high) | numeric.mod(1).ne(0)).any():
            raise ValueError(f"A coluna {column} deve conter inteiros entre {low} e {high}, sem valores ausentes, para compor o período ano/mês.")
        values.append(numeric.astype("int64"))
    label = "Período (ano e mês)"
    column = label
    suffix = 2
    while column in frame.columns:
        column = f"{label} {suffix}"
        suffix += 1
    frame = frame.copy()
    frame[column] = (values[0] * 100 + values[1]).astype(str)
    frame.attrs["derived_fields"] = [{
        "column": column, "role": "period", "source_columns": [year_column, month_column],
        "format": "yyyymm", "rule": "year * 100 + month",
    }]
    return frame
