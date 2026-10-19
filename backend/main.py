"""Motor determinístico experimental com interpretação LLM opcional e isolada.

Referência metodológica: IMPLEMENTATION_SPEC.md v1.2.4.
A integração conversacional não implementa a governança integral da SPEC.
Uploads não são persistidos. A base Brasil usa armazenamento privado configurável.
Nenhum arquivo ou registro é enviado ao LLM.
"""
import csv
import hashlib
import io
import json
import logging
import os
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from pyproj import Geod
from semantic_bridge import candidates, normalize_headers, preflight, suggested_columns, ROLES, EXACT, OPERATIONS
from data_contract import validate_operation, rotation_data, period_positions, scoped, text_values, count_unit_label, canonical_crs
from dataset_normalization import compose_period
from recommended_template import HEADERS as RECOMMENDED_HEADERS, LEGEND_HEADER, recommended_workbook
from territorial_hierarchy import describe_hierarchy
from brazil_data import diagnostics as brazil_diagnostics, load_brazil
from brazil_catalog_profile import curated_profile, suggested_mapping
from analysis_premises import apply_premises, limitations, premise_notes
from llm_bridge import ChatRequest, LLMError, interpret as llm_interpret, status as llm_status, local_response as llm_local_response
from llm_context import review_interpretation, investigation_context, dialogue_projection, screen_reply, bind_local_parameters
from llm_bridge import dialogue_action, _system_response, _document_response
from document_catalog import TOPICS
from conversation_session import sessions, lifespan
from result_conversation import answer_result
from territorial_selection import universe_metadata
from exploration import interpret_exploration, operation_for, normalize as normalize_exploration
from request_memo import RequestMemoMiddleware
from combined_criteria import needs as criteria_needs
from criteria_conversation import criteria_command

app = FastAPI(title="Agente Diagnóstico Territorial — Teste", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ADT_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
# Catálogo, recorte territorial e hierarquia repetidos numa requisição são calculados uma vez.
app.add_middleware(RequestMemoMiddleware)
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
ALIASES = EXACT
ANALYSES = OPERATIONS


def canonical_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(name).strip().lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return "_".join(normalized.replace("-", " ").split())


def suggest(columns: list[str]) -> dict[str, str]:
    """Compatibilidade com os testes; delega à ponte única."""
    return candidates(pd.DataFrame(columns=[str(x) for x in columns]))[0]


def read_dataset(contents: bytes, filename: str, sheet: str = "") -> tuple[pd.DataFrame | None, list[str]]:
    if not contents:
        raise ValueError("O arquivo está vazio.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise ValueError("Arquivo maior que o limite experimental de 30 MB; nenhum dado foi analisado.")
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "csv":
        text = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = contents.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise ValueError("Codificação do CSV não reconhecida.")
        try:
            dialect = csv.Sniffer().sniff(text[:16384], delimiters=",;")
            separator = dialect.delimiter
        except csv.Error:
            first = text.splitlines()[0] if text.splitlines() else ""
            candidates = [item for item in (",", ";") if item in first]
            if len(candidates) != 1:
                raise ValueError("Separador CSV ambíguo. Informe um CSV delimitado por vírgulas ou ponto e vírgula.")
            separator = candidates[0]
        try:
            # Um único parser preserva aspas, delimitadores e quebras em células.
            # Pandas pode inferir um índice e deslocar colunas em linhas excedentes.
            records = csv.reader(io.StringIO(text, newline=""), delimiter=separator, strict=True)
            header = next(records)
            normalize_headers(pd.DataFrame(columns=header))
            rows = []
            for record in records:
                if not record:
                    continue
                if len(record) != len(header):
                    raise ValueError(f"CSV inconsistente na linha {records.line_num}: número de campos diferente do cabeçalho.")
                rows.append(record)
            frame = pd.DataFrame(rows, columns=header)
            frame = frame.replace(r"^\s*$", pd.NA, regex=True)
        except (csv.Error, StopIteration) as exc:
            raise ValueError("Não foi possível interpretar a estrutura do CSV.") from exc
        return compose_period(normalize_headers(frame)), []
    if extension in ("xlsx", "xls"):
        try:
            engine = "openpyxl" if extension == "xlsx" else "xlrd"
            book = pd.ExcelFile(io.BytesIO(contents), engine=engine)
            sheets = book.sheet_names
            if not sheet and len(sheets) > 1:
                return None, sheets
            if sheet and sheet not in sheets:
                raise ValueError("A planilha selecionada não existe neste arquivo.")
            raw = pd.read_excel(book, sheet_name=sheet or sheets[0], header=None, dtype=object)
            if raw.empty:
                raise ValueError("Planilha sem registros.")
            # A legenda à direita do modelo recomendado não é parte da base importada.
            recommended = raw.shape[1] > len(RECOMMENDED_HEADERS) + 1 and str(raw.iat[0, 12]).strip() == LEGEND_HEADER
            if recommended:
                raw = raw.iloc[:, :len(RECOMMENDED_HEADERS)]
            frame = raw.iloc[1:].reset_index(drop=True)
            if recommended:
                frame = frame.dropna(how="all").reset_index(drop=True)
                if frame.empty:
                    raise ValueError("Preencha ao menos uma linha de dados antes de importar o modelo recomendado.")
            frame.columns = [str(x).strip() if pd.notna(x) else f"Unnamed: {i}" for i, x in enumerate(raw.iloc[0])]
            return compose_period(normalize_headers(frame)), sheets
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Não foi possível interpretar este arquivo Excel. Confira se é um .xls ou .xlsx válido, sem proteção por senha.") from exc
    raise ValueError("Formato não suportado. Utilize CSV, XLS ou XLSX.")


def _result(title: str, description: str, rows: list[dict], metrics: list[dict] | None = None, notes: list[str] | None = None) -> dict:
    def clean(value):
        if isinstance(value, dict):
            return {str(k): clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            return float(value) if np.isfinite(value) else None
        if pd.isna(value):
            return None
        return value
    return clean({"title": title, "description": description, "rows": rows, "total_rows": len(rows), "metrics": metrics or [], "notes": notes or []})


def _records(data: pd.DataFrame) -> list[dict]:
    return data.replace({np.nan: None}).to_dict(orient="records")


def compute(df: pd.DataFrame, mapping: dict[str, str], operation: str, options: dict[str, Any]) -> dict:
    if operation in ("spatial", "nearest", "criteria") and canonical_crs(options.get("crs")):
        options = {**options, "crs": canonical_crs(options["crs"])}
    result = _compute(df, mapping, operation, options)
    nearest = result.pop("_nearest", None)
    criteria = result.pop("_criteria", None)
    result["metadata"] = {"method_version": "deterministic-0.4", "operation": operation,
                          "mapping": mapping, "options": options, "input_rows": len(df),
                          "derived_fields": df.attrs.get("derived_fields", [])}
    result["metadata"]["territorial_hierarchy"] = describe_hierarchy(df, mapping, options.get("hierarchy_columns"))
    universe = universe_metadata(scoped(df, mapping, options), mapping, options)
    result["metadata"]["universe"] = universe
    result["metadata"]["input_file"] = df.attrs.get("input_file")
    actual_scope = scoped(df, mapping, options)
    result["metadata"]["periods"] = sorted(text_values(actual_scope[mapping["period"]]).dropna().unique().tolist()) if mapping.get("period") else ["Período declarado"]
    result["metadata"]["categories"] = sorted(text_values(actual_scope[mapping["category"]]).dropna().unique().tolist()) if mapping.get("category") else [options.get("category_constant", "FTS declarada")]
    result["metadata"]["indicator"] = (options.get("comparison_indicator", "density") if operation=="comparisons" else
        options.get(operation + "_indicator") if operation in ("temporal", "report", "distribution") else
        "quantity" if operation=="counts" else "density" if operation in ("density", "aggregate", "ranking") else operation)
    limits = limitations(options, operation)
    result["metadata"]["evaluability"] = {"status": "AVALIAVEL_COM_LIMITACOES" if limits or any(
        "Não avaliável" in str(value) or "possível dupla contagem" in str(value) for row in result["rows"] for value in row.values()) else "AVALIAVEL",
        "policy": "Ausências não são convertidas em zero; condições por elemento preservadas nas linhas."}
    if limits:
        result["metadata"]["evaluability"]["limitacoes"] = limits
    if nearest:
        result["metadata"]["evaluability"]["status"] = nearest["evaluability"]
        result["metadata"]["nearest_reference"] = nearest["structured"]
    if criteria:
        result["metadata"]["evaluability"]["status"] = criteria["evaluability"]
        result["metadata"]["criterios"] = criteria["structured"]
    geo = _geo_identity(df, operation, options)
    if geo is not None:
        result["metadata"]["complemento_geografico"] = geo
    if operation in ("ranking", "distribution", "comparisons"):
        result["notes"].append("Universo desta execução: " + universe["classification_scope"] +
                               ". Posições/classes anteriores não são transferidas para este universo.")
    if df.attrs.get("source"):
        result["metadata"]["source"] = df.attrs["source"]
    for field in df.attrs.get("derived_fields", []):
        if mapping.get(field["role"]) == field["column"]:
            result["notes"].append("Período AAAAMM composto em memória a partir de " +
                                   " e ".join(field["source_columns"]) + "; colunas originais preservadas.")
    unit = count_unit_label(mapping, options)
    if operation != "spatial" and (operation != "nearest" or options.get("reference_mode") == "criterion") and (
            operation != "criteria" or criteria_needs(options)["count"]):
        result["notes"].append("Unidade de contagem: " + str(unit) + ". Não há conversão entre pessoas, vínculos e postos.")
    if mapping.get("territory_id"):
        origin = ("código IBGE do perfil da base oficial" if "territory_id" in (options.get("governed_roles") or [])
                  else "nome e código escolhidos por você")
        result["notes"].append("Identificação territorial: " + origin + "; códigos não foram confrontados com cadastro externo.")
    if options.get("duplicate_policy") == "remove_exact":
        removed = int(scoped(df, mapping, options).duplicated().sum())
        result["notes"].append(f"Remoção, escolhida por você, de {removed} cópias idênticas em todas as colunas.")
    if options.get("rows_additive_confirmed") and "rows_additive_confirmed" not in (options.get("analysis_premises") or []):
        result["notes"].append("Componentes somados nas colunas escolhidas como partes da mesma unidade; população territorial utilizada uma vez.")
    # Origem das premissas: perfil da base oficial e premissas da análise aplicadas pelo backend (sem confirmação).
    result["notes"][:0] = premise_notes(options, operation, mapping)
    result["metadata"]["representacao"] = _representation(df, mapping, operation, options, result, nearest, criteria)
    return result


def _representation(df, mapping, operation, options, result, nearest, criteria):
    """Contrato de apresentação (Bloco 3): uma falha nele nunca invalida o resultado analítico."""
    from representation import VERSION, payload
    try:
        return payload(df, mapping, operation, options, result, nearest, criteria)
    except Exception:  # noqa: BLE001 — registrada no log; tabela e exportações seguem disponíveis
        logging.getLogger(__name__).exception("Falha ao preparar a representação do resultado")
        return {"versao": VERSION, "geometria": {"estado": "INDISPONIVEL", "motivo": "Falha interna ao preparar a "
                                                 "representação; a tabela e as exportações continuam disponíveis."}}


def _compute(df: pd.DataFrame, mapping: dict[str, str], operation: str, options: dict[str, Any]) -> dict:
    if operation not in ANALYSES:
        raise ValueError("Análise não reconhecida.")
    if operation == "rotation":
        validate_operation(df, mapping, options, operation)
        tmp, first, last = rotation_data(df, mapping, options)
        rows = []
        for (ter, cat), group in tmp.groupby(["territory", "category"]):
            c0 = set(group[group.period == first].person)
            c1 = set(group[group.period == last].person)
            # CAP-ROT-01: unidade sem registro em um dos períodos não tem coorte observável (não é 100% de saída).
            observed = bool(c0) and bool(c1)
            ongoing = len(c0 & c1)
            rows.append({"Território": ter, "Categoria": cat, "Período inicial": first, "Período final": last, "Coorte inicial": len(c0),
                         "Permanecem": ongoing if observed else None, "Saíram": len(c0) - ongoing if observed else None,
                         "Permanência (%)": 100 * ongoing / len(c0) if observed else None,
                         "Rotatividade (%)": 100 * (len(c0) - ongoing) / len(c0) if observed else None,
                         "Condição": "Avaliável" if observed else
                                     "Não avaliável: sem registro observado em um dos períodos (SEM_REGISTRO_OBSERVADO)"})
        return _result("Rotatividade e permanência", "Coorte inicial de pessoas distintas; identificadores não são retornados.", rows,
                       notes=["A coorte reúne as pessoas distintas do período inicial pelo identificador individual associado; "
                              "a permanência é conferida no período final."])
    if operation == "nearest":
        from nearest_reference import compute_nearest
        nearest = compute_nearest(df, mapping, options)
        result = _result(nearest["title"], nearest["description"], nearest["rows"], nearest["metrics"], nearest["notes"])
        result["_nearest"] = {"structured": nearest["structured"], "evaluability": nearest["evaluability"]}
        return result
    if operation == "criteria":
        from combined_criteria import compute_criteria
        criteria = compute_criteria(df, mapping, options)
        result = _result(criteria["title"], criteria["description"], criteria["rows"], criteria["metrics"], criteria["notes"])
        result["_criteria"] = {"structured": criteria["structured"], "evaluability": criteria["evaluability"]}
        return result
    if operation == "spatial":
        geo = validate_operation(df, mapping, options, operation).rename(columns={"latitude": "lat", "longitude": "lon"})
        refname = options.get("reference_territory")
        match = geo[geo.territory == refname]
        if match.empty:
            raise ValueError("Selecione um território de referência existente na base.")
        reference = match.iloc[0]
        geod = Geod(ellps="GRS80")
        rows = []
        complemented = set(geo.territory[geo.complementada]) if "complementada" in geo else set()
        for _, item in geo.iterrows():
            _, _, meters = geod.inv(float(reference.lon), float(reference.lat), float(item.lon), float(item.lat))
            row = {"Território": item.territory, "Distância (km)": meters / 1000}
            if complemented:  # coluna só existe quando a camada complementar foi efetivamente usada
                sides = [side for side, used in (("território", item.territory in complemented),
                                                 ("referência", reference.territory in complemented)) if used]
                row["Coordenada complementada (camada oficial)"] = " e ".join(sides).capitalize() if sides else "Não"
            rows.append(row)
        notes = ["Referência: " + str(refname)]
        if complemented:
            notes.append(str(len(complemented)) + " território(s) com ponto inválido na fonte original usam coordenadas da camada "
                         "geográfica complementar versionada, sob a premissa do usuário de coordenada fixa de 2014 a 2024.")
        return _result("Distâncias geodésicas", "Distância direta no referencial " + options["crs"] + ". Não representa tempo nem distância por estrada.",
                       sorted(rows, key=lambda x: x["Distância (km)"]), notes=notes)
    data = validate_operation(df, mapping, options, operation)
    keys = ["territory", "period", "category"]
    cols = {"territory": "Território", "period": "Período", "category": "Categoria",
            "quantity": "Quantidade", "population": "População", "density": "Densidade por 1.000"}
    if operation == "counts":
        rows = _records(data[keys + ["quantity"]].rename(columns=cols))
        return _result("Quantitativos absolutos", "Contagem conforme a unidade de observação e o significado autorizados.", rows,
                       [{"label": "Registros territoriais", "value": len(rows)}])
    if operation in ("density", "aggregate") and data["population"].isna().all():
        raise ValueError("Associe uma coluna População para calcular densidades.")
    if operation == "aggregate":
        if data["period"].nunique() > 1 or data["category"].nunique() > 1:
            raise ValueError("Selecione um único período e uma única categoria antes da agregação.")
        if data["population"].isna().any() or (data["population"] <= 0).any():
            raise ValueError("Agregação exige denominadores populacionais válidos em todas as unidades.")
        summed_quantity = float(data["quantity"].sum())
        summed_population = float(data.groupby("territory")["population"].first().sum())
        is_unique = bool(options.get("no_overlap_confirmed"))
        if not mapping.get("count") and options.get("identity_union_confirmed"):
            selected = scoped(df, mapping, options)
            summed_quantity = int(text_values(selected[mapping["identity"]]).nunique())
            is_unique = True
        unit = count_unit_label(mapping, options) if mapping.get("count") else "pessoas"
        label = ("Unidades distintas: " + unit) if is_unique else "Soma dos componentes (possível dupla contagem)"
        rows = [{"Tipo": label, "Quantidade": summed_quantity, "População": summed_population,
                 "Densidade por 1.000": summed_quantity / summed_population * 1000}]
        notes = ["Densidade agregada = soma dos quantitativos / soma das populações × 1.000.",
                 "A ausência de sobreposição não é inferida. Sem premissa/deduplicação, o resultado é apenas soma dos componentes."]
        return _result("Agregação territorial", "População territorial compartilhada contabilizada uma vez.", rows, notes=notes)
    if operation == "distribution":
        # A escolha do indicador e do universo é obrigatória no contrato compartilhado.
        indicator = options["distribution_indicator"]
        metric = "density" if indicator == "density" else "quantity"
        unit = count_unit_label(mapping, options)
        label = "Densidade por 1.000 habitantes" if indicator == "density" else "Quantidade de " + unit
        k = int(options.get("quantile_count", 5))
        rows = []
        detail_rows = []
        names = {1: "Menores valores", 2: "Valores baixos", 3: "Valores intermediários",
                 4: "Valores altos", 5: "Maiores valores"}
        for (period, category), group in data.groupby(["period", "category"], sort=True):
            series = group[metric]
            if len(group) < 2 or series.isna().any():
                raise ValueError("A distribuição exige ao menos dois territórios avaliáveis por período e categoria.")
            cuts = [float(np.quantile(series, j / k, method="linear")) for j in range(1, k)]
            classes = np.searchsorted(cuts, series.to_numpy(), side="left") + 1
            # Posições crescentes por período/categoria. Empates recebem a menor
            # posição, sem desempate artificial (por exemplo: 1, 1, 3).
            overall_positions = series.rank(method="min", ascending=True).astype(int).to_numpy()
            inside_positions = series.groupby(classes).rank(method="min", ascending=True).astype(int).to_numpy()
            group_label = {4: "quartil", 5: "quintil", 10: "decil"}.get(k)
            position_column = "Posição no " + group_label if group_label else "Posição na faixa"
            for i in range(1, k + 1):
                title = (f"{i}º quintil — {names[i]}" if k == 5 else
                         f"{i}º {group_label}" if group_label else f"{i}ª faixa de {k}")
                rows.append({"Período": period, "Categoria": category,
                             "Classe": "Q" + str(i), "Quintil": title,
                             "Unidades": int((classes == i).sum()), "Indicador": label,
                             "Unidade de contagem": unit})
            for pos, (_, record) in enumerate(group.iterrows()):
                i = int(classes[pos])
                detail_rows.append({
                    "Território": record["territory"], "Período": period, "Categoria": category,
                    "Quintil": f"{i}º {group_label}" if group_label else f"{i}ª faixa de {k}",
                    position_column: int(inside_positions[pos]),
                    "Posição geral": int(overall_positions[pos]),
                    label: float(record[metric]),
                    "Unidade de contagem": unit,
                    "Quantidade": float(record["quantity"]),
                    "População": float(record["population"]) if pd.notna(record["population"]) else None,
                })
        result = _result(
            "Distribuição territorial",
            "Unidades territoriais classificadas do menor para o maior valor do indicador escolhido. Cada período e categoria compõem um universo próprio.",
            rows, notes=["Indicador escolhido: " + label,
                         "Distribuição com pontos de corte Hyndman–Fan tipo 7. Valores iguais permanecem na classe inferior, portanto as contagens podem ser diferentes.",
                         "Posições crescentes por período e categoria; empates preservados (1, 1, 3).",
                         "Os pontos de corte são usados internamente; os resultados individuais estão no detalhamento territorial."]
        )
        result["detail_rows"] = detail_rows
        return result
    if operation == "temporal":
        metric = options["temporal_indicator"]
        pivot = data.pivot_table(index=["territory", "category"], columns="period", values=metric, aggfunc="first")
        positions = period_positions(data.period.unique(), options.get("period_convention", "auto"))
        periods = sorted(positions, key=positions.get)
        if len(periods) < 2:
            raise ValueError("Mudança temporal exige ao menos dois períodos.")
        rows = []
        for (ter, cat), values in pivot.iterrows():
            a, b = values.get(periods[0]), values.get(periods[-1])
            endpoints = pd.notna(a) and pd.notna(b)
            row = {"Território": ter, "Categoria": cat, "Período inicial": periods[0], "Período final": periods[-1], "Inicial": float(a), "Final": float(b),
                   "Variação absoluta": float(b - a) if endpoints else None,
                   "Variação (%)": float((b - a) / a * 100) if endpoints and a != 0 else None,
                   "Condição da mudança": "Avaliável" if endpoints else "Não avaliável: observação ausente em um dos extremos"}
            observations = [(positions[p], float(values[p])) for p in periods if p in values and pd.notna(values[p])]
            if len(observations) >= 4:
                speeds = [(observations[j+1][1]-observations[j][1])/(observations[j+1][0]-observations[j][0])
                          for j in range(len(observations)-1)]
                direction = ("Estável" if all(v == 0 for v in speeds) else
                             "Mudança de direção" if any(v > 0 for v in speeds) and any(v < 0 for v in speeds) else
                             "Crescimento" if all(v >= 0 for v in speeds) else "Declínio")
                row["Tendência"] = direction
            else:
                row["Tendência"] = "Não avaliável (< 4 observações)"
            rows.append(row)
        # As premissas de comparação (perfil oficial ou da análise) entram nas notas por compute; nenhuma é declarada aqui.
        result = _result("Evolução temporal", "Variação de " + ("densidade por 1.000 habitantes" if metric == "density" else "quantitativos") + " entre períodos; tendência somente com quatro ou mais observações.",
                       rows, notes=["Cada competência é independente; não se somam pessoas de períodos diferentes."])
        result["detail_rows"] = _records(data[keys + [metric]].rename(columns=cols))
        return result
    if operation == "comparisons":
        rows = []
        metric = options.get("comparison_indicator", "density")
        metric_label = "Densidade por 1.000" if metric == "density" else "Quantidade"
        # AT-84: a cardinalidade é a do conjunto solicitado, não a dos objetos que restarem por recorte.
        pair = data.territory.nunique() == 2
        for (period, category), group in data.groupby(["period", "category"], sort=True):
            group = group.sort_values("territory")
            common = {"Período": period, "Categoria": category,
                      "Indicador": metric_label, "Unidade de contagem": count_unit_label(mapping, options)}
            if pair and len(group) == 2:
                a, b = group.iloc[0], group.iloc[1]
                rows.append({**common, "Objeto A": a.territory, "Valor A": a[metric],
                    "Objeto B": b.territory, "Valor B": b[metric],
                    "Relação A/B": "IGUALDADE" if a[metric] == b[metric] else "MAIOR" if a[metric] > b[metric] else "MENOR",
                    "Diferença A − B": a[metric] - b[metric], "Condição": "Comparável"})
            else:
                values = sorted(group[metric].unique())
                following = dict(zip(values, [*values[1:], None]))
                equal_counts = group[metric].value_counts()
                for item in group.itertuples():
                    value = getattr(item, metric)
                    rows.append({**common, "Território": item.territory, metric_label: value,
                        "Próximo valor maior": following[value],
                        "Unidades com mesmo valor": int(equal_counts[value]),
                        "Condição": "Comparável" if len(group) > 1 else "Não avaliável: menos de dois territórios neste recorte"})
        # Períodos com cardinalidades diferentes mantêm todas as colunas no CSV.
        columns = dict.fromkeys(key for row in rows for key in row)
        rows = [{key: row.get(key) for key in columns} for row in rows]
        return _result("Comparação territorial", "Valores e relações comparativas por período e categoria, sem posições de ranking.", rows,
            notes=["Entre dois objetos: A e B em ordem de nome, relação A/B e diferença assinada A − B.",
                   "Entre três ou mais: valores iguais e próximo valor estritamente maior descrevem a ordem do conjunto; sem diferenças automáticas entre pares."])
    if operation == "ranking":
        if not data["density"].notna().any():
            raise ValueError("Estas análises requerem densidades avaliáveis.")
        data = data.sort_values(["period", "category", "density", "territory"], ascending=[True, True, False, True]).copy()
        data["position"] = data.groupby(["period", "category"])["density"].rank(method="min", ascending=False).astype(int)
        comparable = data.groupby(["period", "category"])["territory"].transform("nunique").ge(2)
        data["position"] = data.position.where(comparable)
        data["Condição"] = np.where(comparable, "Comparável", "Não avaliável: menos de dois territórios neste recorte")
        rows = _records(data[["position", "territory", "period", "category", "density", "Condição"]].rename(columns={
            "position": "Posição", **cols}))
        return _result("Recortes e rankings" if operation == "ranking" else "Comparação territorial",
                       "Ordem relativa descritiva; não constitui julgamento normativo.", rows,
                       notes=["Resultados exibidos por período e categoria. A comparação exige equivalência metodológica das unidades."])
    # densidade e relatório de quantitativos (sem denominador, não fingir densidade)
    if operation == "report" and options["report_indicator"] == "quantity":
        rows = _records(data[keys + ["quantity"]].rename(columns=cols))
        return _result("Relatório de quantitativos", "Quantitativos da força de trabalho na base analisada.", rows,
                       notes=["Indicador escolhido: quantidade. Nenhuma densidade foi calculada."])
    rows = _records(data[keys + ["quantity", "population", "density"]].rename(columns=cols))
    valid = int(data["density"].notna().sum())
    notes = ["Densidade = quantitativo / população × 1.000.",
             "Valores ausentes e denominadores nulos não são transformados em zero.",
             "Para exportar um relatório, utilize o recurso de impressão/PDF do navegador."]
    return _result("Relatório analítico" if operation == "report" else "Densidade de profissionais",
                   count_unit_label(mapping, options) + " por 1.000 habitantes.",
                   rows, [{"label": "Unidades avaliáveis", "value": valid},
                          {"label": "Não avaliáveis", "value": int(len(data)-valid)}], notes)


async def _read_upload(file: UploadFile) -> bytes:
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima do limite experimental de 30 MB.")
    return contents


# Interpretação das fontes governadas Brasil, reaproveitada somente depois de load_brazil
# verificar o SHA-256 das duas fontes nesta requisição. A chave inclui a versão verificada:
# conteúdo novo nunca reutiliza o anterior. Uploads não passam por aqui (nada é guardado).
_BRAZIL_FRAMES: dict[tuple[str, str], pd.DataFrame] = {}
_BRAZIL_FRAMES_LOCK = threading.Lock()


def _brazil_cache_limit_bytes() -> int:
    """ADT_BRASIL_CACHE_MAX_MB limita o quadro guardado (padrão 512); 0 desliga o reaproveitamento."""
    try:
        return max(0, int(os.getenv("ADT_BRASIL_CACHE_MAX_MB", "512"))) * 1024 * 1024
    except ValueError:
        return 0


def _brazil_frame(raw: bytes, filename: str, source: dict) -> pd.DataFrame | None:
    key = (filename, source["version"])
    frame = None
    with _BRAZIL_FRAMES_LOCK:
        if key in _BRAZIL_FRAMES:
            # O quadro guardado nunca sai daqui: cada requisição recebe cópia própria.
            frame = _BRAZIL_FRAMES[key].copy()
    if frame is None:
        parsed, _ = read_dataset(raw, filename)
        if parsed is None:
            return None
        limit = _brazil_cache_limit_bytes()
        if limit and parsed.memory_usage(deep=True).sum() <= limit:
            with _BRAZIL_FRAMES_LOCK:
                for stale in [k for k in _BRAZIL_FRAMES if k[0] == filename]:
                    del _BRAZIL_FRAMES[stale]  # uma versão por fonte: nacional e municipal separadas
                _BRAZIL_FRAMES[key] = parsed
                frame = parsed.copy()
        else:
            frame = parsed
    frame.attrs["source"] = source
    return frame


SPATIAL_OPERATIONS = ("spatial", "nearest")


def _is_spatial(operation: str, options: dict) -> bool:
    """Análises cujo resultado depende de coordenadas; critérios só quando usam a distância."""
    return operation in SPATIAL_OPERATIONS or (operation == "criteria" and criteria_needs(options)["spatial"])


def _geo_identity(frame: pd.DataFrame, operation: str, options: dict) -> dict | None:
    """Camada complementar nas análises espaciais da base Brasil municipal; None nas demais (chaves inalteradas)."""
    source = frame.attrs.get("source") or {}
    if source.get("dataset") != "brazil" or source.get("scope") != "municipal" or not _is_spatial(operation, options):
        return None
    from geo_complement import frame_identity  # incompatível quando a camada se refere a outra versão da fonte
    return frame_identity(frame)


def _geo_token(identity: dict) -> str:
    return identity.get("sha256") or identity["estado"]


def _catalog_summary(frame: pd.DataFrame) -> dict | None:
    """Identidade da origem Brasil para a interface, sem caminhos físicos (ver /api/brazil/source)."""
    info = frame.attrs.get("catalog")
    if not info:
        return None
    summary = {key: info[key] for key in ("modo", "versao", "versao_governada", "versao_fixada", "integridade")}
    if (frame.attrs.get("source") or {}).get("scope") == "municipal":
        geo = _geo_identity(frame, "spatial", {})
        summary["complemento_geografico"] = {**geo, "token": _geo_token(geo)}
    return summary


async def _request_dataset(file, sheet, dataset, scope, operation="", dataset_version=""):
    if bool(file) == bool(dataset):
        raise ValueError("Escolha uma base do catálogo ou importe um arquivo.")
    if dataset:
        if dataset != "brazil":
            raise ValueError("Base de dados não reconhecida.")
        raw, filename, source, integrity = load_brazil(scope, operation, dataset_version, details=True)
        frame = _brazil_frame(raw, filename, source)
        if frame is not None:
            # Fora de "source": a identidade da origem não altera chaves de execução já existentes.
            frame.attrs["catalog"] = integrity
        return frame, []
    raw = await _read_upload(file)
    frame, sheets = read_dataset(raw, file.filename or "", sheet)
    if frame is not None:
        frame.attrs["input_file"] = {"name": file.filename, "sha256": hashlib.sha256(raw).hexdigest(), "sheet": sheet}
    return frame, sheets


@app.get("/api/modelo/estrutura-recomendada")
def download_recommended_structure() -> Response:
    """Modelo XLSX formatado; sem dados pessoais e sem acesso às bases brasileiras."""
    return Response(
        content=recommended_workbook(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="modelo_territorial_recomendado.xlsx"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm": False, "version": "0.1.0"}


@app.get("/api/brazil/source")
def brazil_source() -> dict:
    """Diagnóstico técnico: origem física, versão e integridade da base Brasil, sem conteúdo."""
    return brazil_diagnostics()


@app.get("/api/llm/status")
def llm_configuration_status() -> dict:
    """Indica disponibilidade local; não verifica crédito, franquia ou faturamento Google."""
    return llm_status()


@app.post("/api/llm/interpret")
async def llm_interpretation(request: ChatRequest, x_adt_session: str | None = Header(None)) -> dict:
    """Interpretação preliminar, sem acesso a arquivos ou execução analítica."""
    try:
        if x_adt_session:
            sessions.event(x_adt_session, "ENVIO_MENSAGEM")
            capture = sessions.capture(x_adt_session, request.context_revision, {})
        answer = await llm_interpret(request)
        if x_adt_session:
            sessions.remember(x_adt_session, capture["revision"], answer)
        return answer
    except LLMError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@app.post("/api/session")
def create_session():
    return sessions.create()


@app.get("/api/session")
def session_status(x_adt_session: str = Header(...)):
    return sessions.status(x_adt_session)


@app.post("/api/session/close")
def close_session(x_adt_session: str = Header(...)):
    sessions.close(x_adt_session)
    return {"closed": True}


@app.post("/api/session/interact")
def session_interaction(body: dict, x_adt_session: str = Header(...)):
    return sessions.event(x_adt_session, body.get("kind"))


@app.post("/api/session/revision")
def session_revision(body: dict, x_adt_session: str = Header(...)):
    sessions.revision(x_adt_session, body.get("revision"))
    return sessions.status(x_adt_session)


@app.get("/api/session/result/{result_id}")
def session_result(result_id: str, x_adt_session: str = Header(...)):
    return sessions.result(x_adt_session, result_id)


@app.post("/api/llm/interpret-context")
async def llm_interpretation_with_dataset(
    file: UploadFile | None = File(None),
    message: str = Form(...),
    history: str = Form("[]"),
    context_ready: bool = Form(True),
    mapping: str = Form("{}"),
    options: str = Form("{}"),
    sheet: str = Form(""),
    dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form(""),
    context_revision: int = Form(0), displayed_result_id: str = Form(""),
    x_adt_session: str | None = Header(None),
) -> dict:
    """Pré-exame local de uma base e interpretação LLM de um resumo técnico.

    O arquivo é lido pelo FastAPI apenas; nenhuma linha, coluna ou nome de
    arquivo é incorporado ao contexto entregue ao provedor.
    """
    try:
        request = ChatRequest(message=message, history=json.loads(history), context_revision=context_revision,
                              displayed_result_id=displayed_result_id)
        if x_adt_session:
            sessions.event(x_adt_session, "ENVIO_MENSAGEM")
        fields = json.loads(mapping)
        settings = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Contexto de análise inválido.")
        # Orientações genéricas não exigem ler nem reenviar um arquivo inteiro.
        # O canal local não solicita, valida ou executa análise da base.
        quick = llm_local_response(request)
        if quick is not None and (not x_adt_session or dialogue_action(message) != "simplify"):
            if x_adt_session:
                sessions.revision(x_adt_session, context_revision)
                sessions.remember(x_adt_session, context_revision, quick)
            return quick
        if not context_ready:
            raise HTTPException(status_code=409, detail="Aguarde ou repita a validação da base antes de solicitar uma proposta analítica.")
        frame, _ = await _request_dataset(file, sheet, dataset, scope, dataset_version=dataset_version)
        if frame is None or frame.empty:
            raise ValueError("Selecione uma planilha com dados antes de utilizar o contexto.")
        settings = apply_premises(frame, fields, settings)
        eligibility = preflight(frame, fields, settings)
        capture = None
        result_record = None
        if x_adt_session:
            capture = sessions.capture(x_adt_session, context_revision,
                                       investigation_context(frame, fields, settings, eligibility))
            if displayed_result_id:
                result_record = sessions.result(x_adt_session, displayed_result_id)
            action = dialogue_action(message)
            if action == "simplify" and capture["dialogue"].get("referent") == "document":
                topic = next((key for key, ids in TOPICS.items() if capture["dialogue"].get("document") in ids), None)
                if topic:
                    quick = _document_response(topic, simple=True)
            if action in ("explain_result", "simplify") and not (
                    action == "simplify" and quick and capture["dialogue"].get("referent") == "document"):
                answer = {**_system_response("", None, ""), **answer_result(message, action, result_record, capture)}
                sessions.remember(x_adt_session, context_revision, answer)
                return answer
            if action in ("next_steps", "change_selection", "change_period"):
                answer = {**_system_response("", None, ""), **screen_reply(action, capture)}
                sessions.remember(x_adt_session, context_revision, answer)
                return answer
            if quick is not None:
                sessions.remember(x_adt_session, context_revision, quick)
                return quick
        declared_category = settings.get("category_constant", "")  # objeto informado pelo usuário (sem confirmação)
        if not isinstance(declared_category, str):
            raise ValueError("Categoria declarada inválida.")
        def review_local(proposal):
            ambiguous = bind_local_parameters(proposal, request.message, eligibility)
            reviewed = review_interpretation(proposal, eligibility, category_constant=declared_category,
                                               frame=frame, mapping=fields, options=settings)
            if ambiguous:
                reviewed["capability_status"] = "needs_confirmation"
                reviewed["blockers"].append("Há mais de um período ou categoria no pedido; escolha o recorte na preparação.")
                reviewed["ambiguous_parameters"] = ambiguous
            return reviewed
        answer = await llm_interpret(
            request, eligibility=eligibility, category_constant=declared_category,
            proposal_reviewer=review_local,
            conversation_context=dialogue_projection(capture, result_record is not None) if capture else None,
            protected_values=([*frame.columns, frame.attrs.get("input_file", {}).get("name", ""), sheet,
                               *(value for column in frame.columns for value in frame[column].dropna().unique())]),
        )
        # O LLM propõe a capacidade; nomes e IDs são resolvidos exclusivamente no Python,
        # usando a manifestação original e o catálogo local, que nunca segue ao provedor.
        proposed_operation = answer.get("proposal", {}).get("operation")
        slots = answer.get("verification", {}).get("slots", {})
        if proposed_operation in ("comparisons", "density", "counts", "temporal", "aggregate") and not any(
                slots.get(key) == "not_confirmed_in_dataset" for key in ("period", "category")):
            local_frame, local_fields = frame, fields
            if dataset == "brazil" and frame.attrs.get("source", {}).get("scope") != "municipal":
                local_frame, _ = await _request_dataset(None, "", "brazil", "municipal", dataset_version=dataset_version)
                local_fields = suggested_mapping(local_frame)
            local_settings = apply_premises(local_frame, local_fields, settings)
            proposed_indicator = answer["proposal"].get("indicator")
            if proposed_indicator in ("density", "quantity"):
                local_settings = {**local_settings, "exploration_indicator": proposed_indicator}
            resolved = interpret_exploration(message, local_frame, local_fields,
                local_settings, operation_hint=proposed_operation)
            if resolved.get("handled"):
                answer["exploration"] = resolved
                answer["reply"] = resolved.get("clarification") or resolved.get("reply") or answer["reply"]
                answer.pop("clarification", None)
        if x_adt_session:
            if answer.get("dialogue_action") in ("next_steps", "change_selection", "change_period"):
                answer.update(screen_reply(answer["dialogue_action"], capture))
            elif answer.get("dialogue_action") in ("explain_result", "simplify"):
                answer.update(answer_result(message, answer["dialogue_action"], result_record, capture))
                # Uma intenção de explicação não muda a operação em preparação.
                answer["proposal"] = _system_response("", None, "")["proposal"]
                answer.pop("exploration", None)
            sessions.remember(x_adt_session, context_revision, answer)
        return answer
    except LLMError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Não foi possível validar o contexto da base.") from exc
    except Exception as exc:
        # Erros de Pydantic também não devem ecoar conteúdos potencialmente sensíveis.
        from pydantic import ValidationError
        if isinstance(exc, ValidationError):
            raise HTTPException(status_code=422, detail="Mensagem ou histórico inválido.") from exc
        raise


@app.get("/api/brazil/description")
def describe_brazil() -> dict:
    """Descrição factual das duas partes da base residente, sem seus registros."""
    try:
        profiles = []
        for scope in ("national", "municipal"):
            raw, name, source = load_brazil(scope=scope)
            frame = _brazil_frame(raw, name, source)
            if frame is None or frame.empty:
                raise ValueError("A base do Brasil não está disponível.")
            mapping = suggested_mapping(frame)
            profile = curated_profile(frame, mapping)
            period_col = mapping.get("period")
            category_col = mapping.get("category")
            periods = sorted(frame[period_col].dropna().astype(str).unique().tolist()) if period_col else []
            categories = sorted(frame[category_col].dropna().astype(str).unique().tolist()) if category_col else []
            profiles.append({"scope": scope, "periods": periods,
                             "categories": categories,
                             "curated": bool(profile),
                             "has_population": bool(mapping.get("population"))})
        national, municipal = profiles
        periods = sorted(set(national["periods"]) | set(municipal["periods"]))
        categories = sorted(set(national["categories"]) | set(municipal["categories"]))
        if not periods:
            raise ValueError("Períodos não reconhecidos.")
        def human_period(value):
            names = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                     "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
            if len(value) == 6 and value.isdigit() and 1 <= int(value[4:]) <= 12:
                return names[int(value[4:]) - 1] + " de " + value[:4]
            return value
        subject = ("médicos" if len(categories) == 1 and categories[0].strip().upper() == "MEDICINA"
                   else "as categorias profissionais registradas")
        narrative = (
            "Os dados do Brasil disponíveis nesta plataforma permitem analisar " + subject +
            " em recortes do país e dos municípios, com referências temporais de " +
            human_period(periods[0]) + " a " + human_period(periods[-1]) + ". "
            "A base inclui quantitativos por período e categoria profissional; "
            "a parte municipal também contém população estimada e coordenadas "
            "para análises de densidade e localização. "
            "Os resultados nacionais e municipais são fontes do mesmo catálogo, "
            "mas não são somados automaticamente entre si."
        )
        return {"description": narrative, "scopes": profiles}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Os dados do Brasil não estão disponíveis para consulta.") from exc


@app.post("/api/inspect")
async def inspect(file: UploadFile | None = File(None), sheet: str = Form(""),
                  dataset: str = Form(""), scope: str = Form("auto"), operation: str = Form("")):
    try:
        frame, sheets = await _request_dataset(file, sheet, dataset, scope, operation)
        if frame is None:
            return {"requires_sheet": True, "sheets": sheets, "columns": [], "row_count": 0, "suggested_mapping": {},
                    "column_profiles": [], "periods": [], "categories": [], "territories": [], "preflight": None,
                    "suggested_category_constant": "", "derived_fields": []}
        if frame.empty:
            raise ValueError("Planilha sem registros.")
        _, profiles = candidates(frame)
        # Só o reconhecido por regra conclusiva (e, na base oficial, o perfil) entra no mapeamento; as sugestões
        # ficam em suggested_columns, para o topo de cada seletor, e nunca são selecionadas em silêncio (D1).
        mapping = suggested_mapping(frame)
        suggestions = suggested_columns(profiles)
        def available(role):
            col = mapping.get(role)
            return frame[col].dropna().astype(str).unique().tolist()[:80] if col else []
        from semantic_bridge import category_from_count_header
        profile = curated_profile(frame, mapping)
        count_columns = [mapping["count"]] if mapping.get("count") else suggestions.get("count", [])
        return {"requires_sheet": False, "sheets": sheets, "columns": frame.columns.tolist(), "row_count": len(frame),
                "suggested_mapping": mapping, "suggested_columns": suggestions, "column_profiles": profiles,
                "curated_defaults": profile,
                "derived_fields": frame.attrs.get("derived_fields", []),
                "source": frame.attrs.get("source"),
                "catalog": _catalog_summary(frame),
                "suggested_category_constant": category_from_count_header(count_columns[0]) if len(count_columns) == 1 else "",
                "preflight": preflight(frame, mapping, apply_premises(frame, mapping, {})),
                "periods": available("period"), "categories": available("category"), "territories": available("territory")}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/preflight")
async def api_preflight(file: UploadFile | None = File(None), mapping: str = Form("{}"),
                        options: str = Form("{}"), sheet: str = Form(""),
                        dataset: str = Form(""), scope: str = Form("auto"),
                        operation: str = Form(""), dataset_version: str = Form("")):
    try:
        frame, _ = await _request_dataset(file, sheet, dataset, scope, operation, dataset_version)
        if frame is None:
            raise ValueError("Selecione uma planilha para concluir o exame.")
        fields = json.loads(mapping)
        settings = json.loads(options)
        return preflight(frame, fields, apply_premises(frame, fields, settings))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/exploration/interpret")
async def exploration_interpret(message: str = Form(...), file: UploadFile | None = File(None),
                               mapping: str = Form("{}"), options: str = Form("{}"), sheet: str = Form(""),
                               dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form(""),
                               context_revision: int = Form(0), x_adt_session: str | None = Header(None)):
    try:
        if len(message) > 800:
            raise ValueError("Mensagem acima do limite de 800 caracteres.")
        if x_adt_session:
            sessions.event(x_adt_session, "ENVIO_MENSAGEM")
            sessions.revision(x_adt_session, context_revision)
        requested = json.loads(options)
        if not isinstance(requested, dict):
            raise ValueError("Parâmetros inválidos.")
        if dialogue_action(message):
            if requested.get("conversation_operation_choice") == "comparisons":
                message = "Compare esses municípios"  # escolha explícita na alternativa; ainda sem cálculo
            else:
                return {"handled": False}  # o canal contextual distingue explicação de execução
        command = criteria_command(message, requested)  # critérios combinados: só estrutura, sem dados nem cálculo
        if command is not None:
            return command
        # Uma pergunta de orientação não responde à pendência territorial anterior.
        # Atendê-la aqui evita que o resolvedor de nomes a transforme em novo pedido de municípios.
        quick = llm_local_response(ChatRequest(message=message, history=[]))
        if quick is not None:
            if x_adt_session and quick.get("documentation"):
                return {"handled": False}  # registra o referente documental no contexto da sessão
            return {"handled": True, "reply": quick["reply"], "executed": False}
        choice = requested.get("conversation_operation_choice")
        if choice is not None:
            from analysis_catalog import OPERATION_LABELS
            if choice not in OPERATION_LABELS:
                raise ValueError("Tipo de análise escolhido não reconhecido.")
        correction = bool(re.fullmatch(r"(?:nao[, ]+)?(?:quero |prefiro |use )?(?:quantidade|quantitativos|densidade)[.!?]*", normalize_exploration(message)))
        adding = bool(re.search(r"\b(?:acrescente|adicione|inclua)\b", normalize_exploration(message)))
        if not choice and not operation_for(message) and not requested.get("conversation_pending_operation") and not (
                requested.get("exploration_operation") and (correction or adding)) and not (
                requested.get("exploration_operation") and re.search(r"\b(?:analise|analisar)\b", normalize_exploration(message))):
            return {"handled": False}
        frame, _ = await _request_dataset(file, sheet, dataset, "municipal" if dataset == "brazil" else scope,
                                          dataset_version=dataset_version)
        if frame is None:
            raise ValueError("Escolha a planilha antes de explorar os territórios.")
        fields, settings = json.loads(mapping), json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Parâmetros inválidos.")
        if dataset == "brazil":
            fields = suggested_mapping(frame)
        settings = apply_premises(frame, fields, settings)
        if x_adt_session:
            sessions.capture(x_adt_session, context_revision, investigation_context(frame, fields, settings,
                                                                                   preflight(frame, fields, settings)))
        return interpret_exploration(message, frame, fields, settings, operation_hint=choice)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyze")
async def analyze(file: UploadFile | None = File(None), operation: str = Form(...), mapping: str = Form("{}"),
                  options: str = Form("{}"), sheet: str = Form(""),
                  dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form(""),
                  geo_version: str = Form(""), context_revision: int = Form(0),
                  x_adt_session: str | None = Header(None)):
    try:
        if x_adt_session:
            sessions.event(x_adt_session, "CONFIRMACAO")  # evento de sessão: execução pedida pelo usuário
        frame, _ = await _request_dataset(file, sheet, dataset, scope, operation, dataset_version)
        if frame is None:
            raise ValueError("Selecione a planilha Excel antes de executar.")
        fields = json.loads(mapping)
        requested = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(requested, dict):
            raise ValueError("Parâmetros de análise inválidos.")
        settings = apply_premises(frame, fields, requested)
        eligibility = preflight(frame, fields, settings)
        gate = eligibility["capabilities"].get(operation)
        if gate is None:
            raise ValueError("Análise desconhecida.")
        if gate["status"] != "available":
            raise ValueError("Análise não habilitada para a configuração atual: " + " ".join(gate["reasons"]))
        geo = _geo_identity(frame, operation, settings)
        if geo is not None and geo_version and geo_version != _geo_token(geo):
            raise ValueError("A camada geográfica complementar mudou depois da preparação. Carregue novamente a base antes de analisar.")
        capture = sessions.capture(x_adt_session, context_revision,
                  investigation_context(frame, fields, settings, eligibility)) if x_adt_session else None
        if not _is_spatial(operation, settings):
            # Referencial e separador decimal internos valem só nas análises de distância. O contexto da
            # conversa mantém todas as premissas, como nas demais etapas, e a preparação continua a mesma.
            settings = apply_premises(frame, fields, requested, spatial=False)
        result = compute(frame, fields, operation, settings)
        result["metadata"]["data_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()
        result["result_id"] = str(uuid.uuid4())
        result["metadata"]["created_at"] = datetime.now(timezone.utc).isoformat()
        signature = {"data": result["metadata"]["data_sha256"], "source": frame.attrs.get("source"),
                     "mapping": fields, "options": settings, "operation": operation,
                     "method": result["metadata"]["method_version"]}
        if geo is not None and geo["estado"] == "valido":  # só quando a camada pode alterar o resultado espacial
            signature["geo_complement"] = geo
        result["metadata"]["execution_key"] = hashlib.sha256(json.dumps(signature, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        result["metadata"]["validity"] = "VALIDO"
        result["metadata"]["presentations"] = ["table", "csv", "metadata_json", "print"]
        if capture:
            result["conversation_reference"] = {"available": sessions.record_result(
                x_adt_session, context_revision, result, capture["context"])}
        return result
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
