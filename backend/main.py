"""Motor determinístico experimental com interpretação LLM opcional e isolada.

Referência metodológica: IMPLEMENTATION_SPEC.md v1.2.4.
A integração conversacional não implementa a governança integral da SPEC.
Uploads não são persistidos. A base Brasil usa armazenamento privado configurável.
Nenhum arquivo ou registro é enviado ao LLM.
"""
import asyncio
from contextlib import asynccontextmanager
import contextvars
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
from fastapi.responses import JSONResponse
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from semantic_bridge import candidates, normalize_headers, preflight, suggested_columns, ROLES, EXACT, OPERATIONS
from data_contract import (ChoiceRequired, validate_operation, rotation_data, period_positions, resolve_convention, scoped,
                           text_values, count_unit_label, canonical_crs, comparison_window as comparison_window_periods)
import comparison_window
from temporal_change import evolution, evolution_notes
from trend import METHOD_VERSION as TREND_METHOD
from dataset_normalization import compose_period
from recommended_template import HEADERS as RECOMMENDED_HEADERS, LEGEND_HEADER, recommended_workbook
from territorial_hierarchy import describe_hierarchy
from brazil_data import diagnostics as brazil_diagnostics, load_brazil_sources, selected_scope
from brazil_catalog_profile import curated_profile, source_identity, suggested_mapping
import territorial_levels
from analysis_premises import apply_premises, limitations, premise_notes
from llm_bridge import ChatRequest, LLMError, interpret as llm_interpret, status as llm_status, local_response as llm_local_response
from llm_context import review_interpretation, investigation_context, dialogue_projection, screen_reply, bind_local_parameters
from llm_bridge import dialogue_action, _system_response, _document_response
from document_catalog import TOPICS
from conversation_session import sessions, lifespan
from result_conversation import answer_result
from territorial_selection import universe_metadata
from exploration import interpret_exploration, operation_for, normalize as normalize_exploration, RELATIVE_YEARS
from request_memo import RequestMemoMiddleware, mark_source, per_source
from combined_criteria import needs as criteria_needs
from criteria_conversation import criteria_command
import conversation_library
import conversa_grafico
import dialogo
import painel
import conversa_gemini
import contexto_conversa
import definicoes
import llm_bridge
import triagem
from territorial_selection import STATES


# Aquecimento em curso: a primeira requisição à base Brasil espera por ele em vez de repetir o mesmo cálculo em paralelo.
_WARM_DONE = threading.Event()
_WARM_DONE.set()  # sem a partida do servidor (testes, scripts), nada espera
_WARMING = contextvars.ContextVar("adt_aquecimento", default=False)


def _warm_up():
    """Aquecimento na partida, em segundo plano: a biblioteca conversacional e a mesma inspeção da base Brasil que a
    interface pede primeiro, pelo próprio app (mesmas regras e memória da versão). Nada é exibido nem registrado na
    sessão; uma falha equivale a não aquecer, e a primeira requisição calcula como antes."""
    token = _WARMING.set(True)
    try:
        async def inspect_brazil():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://aquecimento") as client:
                await client.post("/api/inspect", data={"dataset": "brazil", "scope": "auto", "operation": "", "sheet": ""})
        asyncio.run(inspect_brazil())
    except Exception:  # noqa: BLE001 - aquecimento opcional; o pedido real relata qualquer erro
        pass
    finally:
        _WARMING.reset(token)
        _WARM_DONE.set()
    try:
        if conversation_library.enabled():
            conversation_library.library()  # só as mensagens ao provedor usam a biblioteca: depois da base
    except (OSError, ValueError, KeyError, TypeError):
        pass  # o pedido ao provedor segue sem exemplos, como em _library_examples


@asynccontextmanager
async def _lifespan(application):
    # ADT_AQUECIMENTO=0 desliga (partida sem cálculo antecipado).
    if os.getenv("ADT_AQUECIMENTO", "1").strip() != "0":
        _WARM_DONE.clear()
        threading.Thread(target=_warm_up, name="aquecimento", daemon=True).start()
    async with lifespan(application):
        yield


app = FastAPI(title="Agente Diagnóstico Territorial — Teste", version="0.1.0", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ADT_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
# Catálogo, recorte territorial e hierarquia repetidos numa requisição são calculados uma vez.
app.add_middleware(RequestMemoMiddleware)
# Respostas grandes vão comprimidas (gzip) quando o cliente aceita, como o navegador: o gráfico com todos os municípios
# passa de 10 MB. Nível 1, o mais rápido (cerca de 0,08 s para 10 MB, com um quinto do tamanho); abaixo de 64 KB, sem
# compressão. O corpo descomprimido é o mesmo, byte a byte.
app.add_middleware(GZipMiddleware, minimum_size=64 * 1024, compresslevel=1)
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


def temporal_metrics(rows: list[dict], mudanca: dict) -> list[dict]:
    """Contagens do motor na evolução temporal (séries e direção da mudança entre os extremos, CAP-TMP-01)."""
    directions = mudanca["direcoes"]
    return [{"label": "Séries territoriais", "value": len(rows)},
            {"label": "Aumento entre os extremos", "value": directions["AUMENTO"]},
            {"label": "Redução entre os extremos", "value": directions["REDUCAO"]},
            {"label": "Sem mudança entre os extremos", "value": directions["SEM_MUDANCA"]},
            {"label": "Mudança não avaliável", "value": sum(mudanca["nao_avaliaveis"].values())}]


def ranking_metrics(rows: list[dict]) -> list[dict]:
    """Territórios com posição calculada (CAP-SUB-02) e não avaliáveis, contados pelo motor."""
    ordered = sum(row.get("Posição") is not None for row in rows)
    return [{"label": "Territórios ordenados", "value": ordered}, {"label": "Não avaliáveis", "value": len(rows) - ordered}]


def compute(df: pd.DataFrame, mapping: dict[str, str], operation: str, options: dict[str, Any]) -> dict:
    if operation in ("spatial", "nearest", "criteria") and canonical_crs(options.get("crs")):
        options = {**options, "crs": canonical_crs(options["crs"])}
    result = _compute(df, mapping, operation, options)
    return _finish(result, df, mapping, operation, options)


def _finish(result: dict, df: pd.DataFrame, mapping: dict[str, str], operation: str, options: dict[str, Any],
            universe: dict | None = None, periods: list | None = None, categories: list | None = None,
            levels: dict | None = None) -> dict:
    """Metadados, notas e representação de um resultado calculado por _compute.

    Sem `universe`, `periods` e `categories`, eles vêm do recorte de `df` (caminho de uma fonte). O orquestrador dos
    níveis territoriais (territorial_levels.py) os informa, porque o resultado reúne partes de fontes diferentes;
    `levels` leva a ele as limitações e o contrato de apresentação dos níveis."""
    nearest = result.pop("_nearest", None)
    criteria = result.pop("_criteria", None)
    trend = result.pop("_tendencia", None)
    comparison = result.pop("_comparacao", None)
    result["metadata"] = {"method_version": "deterministic-0.4", "operation": operation,
                          "mapping": mapping, "options": options, "input_rows": len(df),
                          "derived_fields": df.attrs.get("derived_fields", [])}
    if comparison:
        # Comparação com competência dos valores (D6): janela, grupos de relação e objetos sem relação.
        result["metadata"]["comparacao"] = comparison
    if trend:
        # Tendência (CAP-TEN-01) e mudança (CAP-TMP-01) estruturadas; a versão do método entra na chave de execução.
        result["metadata"]["tendencia"] = trend["tendencia"]
        result["metadata"]["mudanca"] = trend["mudanca"]
        result["metadata"]["metodos"] = {"tendencia": TREND_METHOD}
    result["metadata"]["territorial_hierarchy"] = describe_hierarchy(df, mapping, options.get("hierarchy_columns"))
    if universe is None:
        universe = universe_metadata(scoped(df, mapping, options), mapping, options)
    result["metadata"]["universe"] = universe
    result["metadata"]["input_file"] = df.attrs.get("input_file")
    if periods is None or categories is None:
        actual_scope = scoped(df, mapping, options)
        if periods is None:
            periods = sorted(text_values(actual_scope[mapping["period"]]).dropna().unique().tolist()) if mapping.get("period") else ["Período declarado"]
        if categories is None:
            categories = sorted(text_values(actual_scope[mapping["category"]]).dropna().unique().tolist()) if mapping.get("category") else [options.get("category_constant", "FTS declarada")]
    result["metadata"]["periods"] = periods
    result["metadata"]["categories"] = categories
    result["metadata"]["indicator"] = (options.get("comparison_indicator", "density") if operation=="comparisons" else
        options.get(operation + "_indicator") if operation in ("temporal", "report", "distribution") else
        "quantity" if operation=="counts" else "density" if operation in ("density", "aggregate", "ranking") else operation)
    limits = list(dict.fromkeys([*limitations(options, operation), *((levels or {}).get("limitacoes") or [])]))
    # Na comparação com janela, a mudança e a tendência de cada território estão em detail_rows.
    inspected = result["rows"] + (result.get("detail_rows") or [] if comparison else [])
    result["metadata"]["evaluability"] = {"status": "AVALIAVEL_COM_LIMITACOES" if limits or any(
        "Não avaliável" in str(value) or "possível dupla contagem" in str(value) for row in inspected for value in row.values()) else "AVALIAVEL",
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
    if (levels or {}).get("source"):
        result["metadata"]["source"] = levels["source"]
    elif df.attrs.get("source"):
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
    premises = premise_notes(options, operation, mapping)
    if comparison and comparison.get("mudanca_e_tendencia"):
        # A janela usa as mesmas premissas temporais da evolução (comparabilidade e identidade territorial).
        premises += [note for note in premise_notes(options, "temporal", mapping) if note not in premises and
                     note.startswith(("Comparabilidade temporal", "Identidade territorial"))]
    result["notes"][:0] = premises
    result["metadata"]["representacao"] = _representation(df, mapping, operation, options, result, nearest, criteria,
                                                          (trend or {}).get("quebras"), levels)
    return result


def _representation(df, mapping, operation, options, result, nearest, criteria, breaks=None, levels=None):
    """Contrato de apresentação (Bloco 3): uma falha nele nunca invalida o resultado analítico."""
    from representation import VERSION, payload
    try:
        return payload(df, mapping, operation, options, result, nearest, criteria, breaks=breaks, levels=levels)
    except Exception:  # noqa: BLE001 — registrada no log; tabela e exportações seguem disponíveis
        logging.getLogger(__name__).exception("Falha ao preparar a representação do resultado")
        return {"versao": VERSION, "geometria": {"estado": "INDISPONIVEL", "motivo": "Falha interna ao preparar a "
                                                 "representação; a tabela e as exportações continuam disponíveis."}}


def distribution_cuts(series, k: int) -> list[float]:
    """Pontos de corte da distribuição (CAP-DIS-02): Hyndman–Fan tipo 7 (interpolação linear), os mesmos usados por
    _compute na classificação e devolvidos pelo gráfico (painel.py), sem fórmula paralela."""
    return [float(np.quantile(series, j / k, method="linear")) for j in range(1, k)]


def _compute(df: pd.DataFrame, mapping: dict[str, str], operation: str, options: dict[str, Any],
             prepared: pd.DataFrame | None = None) -> dict:
    """Linhas da análise. `prepared` (quadro já preparado por data_contract.prepare, mesmas colunas) é usado no lugar
    da preparação de `df` nas análises numéricas: o orquestrador dos níveis chama esta função uma vez por universo."""
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
        observed = sum(row["Condição"] == "Avaliável" for row in rows)
        return _result("Rotatividade e permanência", "Coorte inicial de pessoas distintas; identificadores não são retornados.", rows,
                       [{"label": "Coortes avaliáveis", "value": observed},
                        {"label": "Coortes não avaliáveis (sem registro em um dos períodos)", "value": len(rows) - observed}],
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
        from nearest_reference import GEODS
        geod = GEODS[options["crs"]]  # elipsoide do referencial confirmado (canônico em compute)
        rows = []
        complemented = set(geo.territory[geo.complementada & geo.valida]) if "complementada" in geo else set()
        invalid = geo[~geo.valida] if "valida" in geo else geo.iloc[0:0]
        for _, item in geo.iterrows():
            valid = bool(item.get("valida", True))
            # RQ-DAD-25: coordenada ausente ou inválida deixa só este território não avaliável (lacuna, nunca zero).
            distance = geod.inv(float(reference.lon), float(reference.lat), float(item.lon), float(item.lat))[2] / 1000 if valid else None
            row = {"Território": item.territory, "Distância (km)": distance}
            if complemented:  # coluna só existe quando a camada complementar foi efetivamente usada
                sides = [side for side, used in (("território", item.territory in complemented),
                                                 ("referência", reference.territory in complemented)) if used]
                row["Coordenada complementada (camada oficial)"] = " e ".join(sides).capitalize() if sides else "Não"
            if len(invalid):  # coluna só existe quando algum território ficou sem coordenada válida
                row["Condição"] = "Avaliável" if valid else "Não avaliável: coordenada " + (
                    "ausente" if item.get("condicao") == "AUSENTE" else "inválida")
            rows.append(row)
        notes = ["Referência: " + str(refname)]
        if complemented:
            notes.append(str(len(complemented)) + " território(s) com ponto inválido na fonte original usam coordenadas da camada "
                         "geográfica complementar versionada, sob a premissa do usuário de coordenada fixa de 2014 a 2024.")
        if len(invalid):
            notes.append(str(len(invalid)) + " território(s) sem coordenada válida no recorte ficam não avaliáveis "
                         "(COORDENADA_INVALIDA), sem distância e fora do mapa; os demais foram calculados.")
        return _result("Distâncias geodésicas", "Distância direta no referencial " + options["crs"] + ". Não representa tempo nem distância por estrada.",
                       sorted(rows, key=lambda x: (x["Distância (km)"] is None, x["Distância (km)"] or 0.0)), notes=notes)
    data = validate_operation(df, mapping, options, operation, prepared=prepared)
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
        return _result("Agregação territorial", "População territorial compartilhada contabilizada uma vez.", rows,
                       [{"label": "Territórios agregados", "value": int(data.territory.nunique())}], notes=notes)
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
            cuts = distribution_cuts(series, k)
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
            # Em bloco, pelas colunas (sem montar uma Series por território): os mesmos valores, na mesma ordem.
            names = [f"{i}º {group_label}" if group_label else f"{i}ª faixa de {k}" for i in range(k + 1)]
            for territory, i, inside, overall, value, quantity, population in zip(
                    group["territory"].tolist(), classes.tolist(), inside_positions.tolist(), overall_positions.tolist(),
                    series.tolist(), group["quantity"].tolist(), group["population"].tolist()):
                detail_rows.append({
                    "Território": territory, "Período": period, "Categoria": category,
                    "Quintil": names[i],
                    position_column: int(inside),
                    "Posição geral": int(overall),
                    label: float(value),
                    "Unidade de contagem": unit,
                    "Quantidade": float(quantity),
                    "População": float(population) if pd.notna(population) else None,
                })
        # Total do motor (o frontend não soma as classes): unidades classificadas e número de classes.
        result = _result(
            "Distribuição territorial",
            "Unidades territoriais classificadas do menor para o maior valor do indicador escolhido. Cada período e categoria compõem um universo próprio.",
            rows, [{"label": "Unidades classificadas", "value": len(detail_rows)}, {"label": "Classes", "value": k}], notes=["Indicador escolhido: " + label,
                         "Distribuição com pontos de corte Hyndman–Fan tipo 7. Valores iguais permanecem na classe inferior, portanto as contagens podem ser diferentes.",
                         "Posições crescentes por período e categoria; empates preservados (1, 1, 3).",
                         "Os pontos de corte são usados internamente; os resultados individuais estão no detalhamento territorial."]
        )
        result["detail_rows"] = detail_rows
        return result
    if operation == "temporal":
        # CAP-TMP-01 (mudança entre a primeira e a última competência) e CAP-TEN-01 (tendência, DA-15) em
        # aritmética exata; Inicial, Final e as variações continuam em float, como antes.
        metric = options["temporal_indicator"]
        convention = resolve_convention(data.period.unique(), options.get("period_convention", "auto"))
        positions = period_positions(data.period.unique(), convention)
        rows, detail_rows, tendencia, mudanca, breaks = evolution(
            data, metric, positions, convention=convention,
            value_unit="por 1.000 habitantes" if metric == "density" else count_unit_label(mapping, options))
        # As premissas de comparação (perfil oficial ou da análise) entram nas notas por compute; nenhuma é declarada aqui.
        result = _result("Evolução temporal", "Variação de " + ("densidade por 1.000 habitantes" if metric == "density" else "quantitativos") +
                         " entre períodos; tendência (CAP-TEN-01) somente com quatro ou mais observações válidas.",
                         rows, temporal_metrics(rows, mudanca), notes=["Cada competência é independente; não se somam pessoas de períodos diferentes.",
                                      *evolution_notes(tendencia, mudanca, convention)])
        result["detail_rows"] = detail_rows
        result["_tendencia"] = {"tendencia": tendencia, "mudanca": mudanca, "quebras": breaks}
        return result
    if operation == "comparisons":
        metric = options.get("comparison_indicator", "density")
        unit = count_unit_label(mapping, options)
        objects = int(data.territory.nunique())
        if comparison_window.requested_period(options) is not None:
            return _comparison_with_window(data, mapping, options, metric, unit)
        # AT-84: a cardinalidade é a do conjunto solicitado, não a dos objetos que restarem por recorte.
        rows = comparison_window.relation_rows(data, metric, unit)
        return _result("Comparação territorial", "Valores e relações comparativas por período e categoria, sem posições de ranking.", rows,
            [{"label": "Territórios comparados", "value": objects}],
            notes=[comparison_window.NOTE_PAIRS, comparison_window.NOTE_SET])
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
                       "Ordem relativa descritiva; não constitui julgamento normativo.", rows, ranking_metrics(rows),
                       notes=["Resultados exibidos por período e categoria. A comparação exige equivalência metodológica das unidades."])
    # densidade e relatório de quantitativos (sem denominador, não fingir densidade)
    if operation == "report" and options["report_indicator"] == "quantity":
        rows = _records(data[keys + ["quantity"]].rename(columns=cols))
        return _result("Relatório de quantitativos", "Quantitativos da força de trabalho na base analisada.", rows,
                       [{"label": "Registros territoriais", "value": len(rows)}],
                       notes=["Indicador escolhido: quantidade. Nenhuma densidade foi calculada."])
    rows = _records(data[keys + ["quantity", "population", "density"]].rename(columns=cols))
    valid = int(data["density"].notna().sum())
    notes = ["Densidade = quantitativo / população × 1.000.",
             "Valores ausentes e denominadores nulos não são transformados em zero.",
             "Para exportar um relatório, utilize o recurso de impressão/PDF do navegador."]
    return _result("Relatório analítico" if operation == "report" else "Densidade de profissionais",
                   "Densidade de " + count_unit_label(mapping, options) + " por 1.000 habitantes.",
                   rows, [{"label": "Unidades avaliáveis", "value": valid},
                          {"label": "Não avaliáveis", "value": int(len(data)-valid)}], notes)


def _comparison_with_window(data: pd.DataFrame, mapping: dict, options: dict, metric: str, unit: str) -> dict:
    """Comparação com competência dos valores (D6): relações só nessa competência, no formato de sempre, e um registro
    por território com valores, mudança e tendência na janela (comparison_window.py)."""
    period = comparison_window.requested_period(options)
    ordered, positions = comparison_window_periods(data.period.unique(), mapping, options)
    current = data[data.period == period]
    objects = int(data.territory.nunique())
    rows = comparison_window.relation_rows(current, metric, unit, requested=objects)
    density = metric == "density"
    evolved, tendencia, mudanca, breaks = {}, None, None, []
    convention = resolve_convention(list(positions), options.get("period_convention", "auto"))
    if len(ordered) >= 2:
        evolved, tendencia, mudanca, breaks = comparison_window.evolve(
            data, metric, positions, convention, "por 1.000 habitantes" if density else unit)
    records = {(item["territory"], item["category"]): item for item in current.to_dict("records")}
    keys = sorted({(ter, cat) for ter, cat in zip(data.territory, data.category)}, key=lambda key: (str(key[0]), str(key[1])))
    detail = []
    for territory, category in keys:
        record = records.get((territory, category))
        row = {"Território": territory, "Categoria": category, "Período": period,
               **comparison_window.value_columns(record, metric, density), "Unidade de contagem": unit,
               "Condição": "Avaliável" if record is not None else comparison_window.MISSING_VALUES}
        if len(ordered) >= 2:
            row.update(comparison_window.window_columns(evolved.get((territory, category))))
        detail.append(row)
    comparacao = comparison_window.window_meta(period, ordered, metric)
    present = sorted(set(current.territory))
    comparacao["grupos"] = [{"nivel": None, "unidade_contagem": unit, "objetos": present, "relacoes": len(present) >= 2}]
    comparacao["sem_relacao"] = [{"objeto": key[0], "motivo": comparison_window.MISSING_VALUES}
                                 for key in keys if key not in records] + (
        [{"objeto": name, "motivo": "Não avaliável: menos de dois territórios neste recorte"} for name in present]
        if len(present) < 2 else [])
    metrics = [{"label": "Territórios comparados", "value": objects},
               {"label": "Competências na janela", "value": len(ordered)}]
    result = _result("Comparação territorial", "Valores e relações comparativas na competência " + str(period) +
                     (", com mudança e tendência de cada território na janela" if len(ordered) >= 2 else "") +
                     "; sem posições de ranking.", rows, metrics,
                     notes=comparison_window.notes(period, ordered, tendencia, mudanca, convention, [
                         comparison_window.NOTE_PAIRS if objects == 2 else comparison_window.NOTE_SET]))
    result["detail_rows"] = detail
    result["_comparacao"] = comparacao
    if tendencia is not None:
        result["_tendencia"] = {"tendencia": tendencia, "mudanca": mudanca, "quebras": breaks}
    return result


async def _read_upload(file: UploadFile) -> bytes:
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima do limite experimental de 30 MB.")
    return contents


# Interpretação das fontes governadas Brasil, reaproveitada somente depois de load_brazil_sources
# verificar o SHA-256 das fontes nesta requisição. A chave inclui a versão verificada:
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
    reused = frame is not None
    if frame is None:
        parsed, _ = read_dataset(raw, filename)
        if parsed is None:
            return None
        limit = _brazil_cache_limit_bytes()
        if limit and parsed.memory_usage(deep=True).sum() <= limit:
            # Guardado já consolidado (a cópia do pandas junta os blocos de mesmo tipo): a cópia de cada requisição não
            # refaz a consolidação. Mesmos valores, colunas, tipos e índice.
            stored = parsed.copy()
            with _BRAZIL_FRAMES_LOCK:
                for stale in [k for k in _BRAZIL_FRAMES if k[0] == filename]:
                    del _BRAZIL_FRAMES[stale]  # uma versão por fonte: nacional e municipal separadas
                _BRAZIL_FRAMES[key] = stored
                frame = parsed
                reused = True
        else:
            frame = parsed
    frame.attrs["source"] = source
    if reused:
        # Cópia íntegra da versão guardada: as derivações puras dela valem entre requisições (request_memo).
        mark_source(frame, key)
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


class BrazilSources:
    """As fontes da base Brasil de uma requisição (nacional, estadual e municipal), de uma única leitura verificada (mesma
    versão).

    Cada quadro é montado só quando pedido (cópia do quadro guardado por versão) e mantém o próprio escopo em
    attrs["source"]; a integridade fica em attrs["catalog"], fora da chave de execução."""

    def __init__(self, version: str = ""):
        self._contents, self.integrity = load_brazil_sources(version)
        self.version = self.integrity["versao"]
        self._frames: dict[str, pd.DataFrame | None] = {}

    def frame(self, scope: str) -> pd.DataFrame | None:
        if scope not in self._frames:
            raw, filename, source = self._contents[scope]
            frame = _brazil_frame(raw, filename, source)
            if frame is not None:
                # Fora de "source": a identidade da origem não altera chaves de execução já existentes.
                frame.attrs["catalog"] = self.integrity
            self._frames[scope] = frame
        return self._frames[scope]


def _brazil_sources(version: str = "") -> BrazilSources:
    return BrazilSources(version)


async def _request_dataset(file, sheet, dataset, scope, operation="", dataset_version="", with_sources=False):
    """Quadro do pedido (base Brasil ou arquivo importado). Com with_sources, devolve também as fontes Brasil
    da mesma leitura verificada (None nos uploads)."""
    if bool(file) == bool(dataset):
        raise ValueError("Escolha uma base do catálogo ou importe um arquivo.")
    if dataset:
        if dataset != "brazil":
            raise ValueError("Base de dados não reconhecida.")
        if not _WARM_DONE.is_set() and not _WARMING.get():
            await asyncio.to_thread(_WARM_DONE.wait, 60)  # o aquecimento já calcula o mesmo; no limite, segue sem ele
        selected = selected_scope(scope, operation)
        sources = _brazil_sources(dataset_version)
        frame = sources.frame(selected)
        return (frame, [], sources) if with_sources else (frame, [])
    raw = await _read_upload(file)
    frame, sheets = read_dataset(raw, file.filename or "", sheet)
    if frame is not None:
        frame.attrs["input_file"] = {"name": file.filename, "sha256": hashlib.sha256(raw).hexdigest(), "sheet": sheet}
    return (frame, sheets, None) if with_sources else (frame, sheets)


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


ESCOLHA_DOS_DADOS = ("Para fazer essa análise, primeiro escolha os dados: use os dados do Brasil ou envie os seus, em CSV "
                     "ou Excel. Assim que a base estiver pronta, sigo com o seu pedido.")


@app.post("/api/llm/interpret")
async def llm_interpretation(request: ChatRequest, x_adt_session: str | None = Header(None)) -> dict:
    """Interpretação preliminar, sem acesso a arquivos ou execução analítica."""
    try:
        llm_bridge.iniciar_relogio()
        if x_adt_session:
            sessions.event(x_adt_session, "ENVIO_MENSAGEM")
            capture = sessions.capture(x_adt_session, request.context_revision, {})
        quick = llm_local_response(request)
        if quick is None and request.lembrar_base and conversa_grafico.pedido_de_analise(request.message):
            # Pedido de análise antes da escolha dos dados, na página única (26/10/2026): a orientação para escolher a base,
            # na hora, sem o provedor; a tela guarda o pedido e segue com ele quando a base fica pronta.
            answer = _system_response(ESCOLHA_DOS_DADOS, None, "")
            answer.update(aguarda_base=True, note="Pedido de análise antes da escolha dos dados; nada foi interpretado "
                                                  "pelo provedor nem calculado.")
            if x_adt_session:
                sessions.remember(x_adt_session, capture["revision"], answer)
            return answer
        if quick is not None and _conversa_pelo_modelo(quick):
            # Orientação sobre o agente com o provedor disponível: o Gemini redige a partir do texto do catálogo.
            answer = await _redigida(quick, request.message, request.turnos, {}, None, None, None, {"tipo": "nenhuma"},
                                     None, triagem.Protecao(), fatos=quick["reply"], pedidas=_fichas_da_documentacao(quick))
        else:
            contexto = contexto_conversa.montar(mensagem=request.message, turnos=request.turnos,
                                                fonte={"tipo": "nenhuma"}) if request.turnos else None
            try:
                answer = await llm_interpret(request, contexto=contexto)
            except LLMError as exc:
                if exc.causa == "entrada":
                    raise
                return _sem_o_modelo(exc)
            answer = await _redacao_da_interpretacao(answer, request.message, request.turnos, {}, None, None, None,
                                                     {"tipo": "nenhuma"}, None, triagem.Protecao())
        # Sem base, o comando do gráfico vem só da operação proposta (família, indicador e função); a tela o aplica
        # quando a base fica pronta. Nomes e competências são resolvidos depois, pela conversa local.
        proposal = answer.get("proposal") or {}
        painel_proposto = conversa_grafico.painel_da_operacao(proposal.get("operation"), proposal.get("indicator"),
                                                              request.message)
        if painel_proposto:
            answer["painel"] = painel_proposto
        answer = llm_bridge.publico(answer)
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


def _colunas_de_texto(frame: pd.DataFrame) -> dict:
    return {str(coluna): list(frame[coluna].dropna().unique()) for coluna in frame.columns if frame[coluna].dtype == object}


@per_source()  # base Brasil: a mesma proteção em toda requisição da versão
def protecao_da_fonte(frame: pd.DataFrame, papeis: dict, sheet: str) -> triagem.Protecao:
    """A proteção da triagem (triagem.py, RQ-DAD-20) para a base carregada: territórios, grupos territoriais, regiões e
    categorias liberados (classe B), os valores das demais colunas de texto protegidos (classe A) e os nomes das colunas,
    do arquivo e da planilha tratados como metadados (classe C). As unidades federativas do Brasil são sempre liberadas."""
    estados = [nome for _sigla, nome in STATES.values()] + [sigla for sigla, _nome in STATES.values()]
    return triagem.protecao_da_base(_colunas_de_texto(frame), {k: v for k, v in (papeis or {}).items() if isinstance(v, str)},
                                    nomes_extras=estados,
                                    metadados_extras=[frame.attrs.get("input_file", {}).get("name", ""), sheet])


def _resposta_do_dialogo(turno: dict, origem: str = "CANAL_SISTEMICO") -> dict:
    """A resposta do gestor de diálogo no contrato do intérprete contextual: a tela lê o pedido do gráfico, as
    alternativas e a memória em `exploration`, como as respostas da gramática local."""
    resposta = _system_response(turno.get("clarification") or turno.get("reply") or "", None, "")
    resposta.update(origin=origem, exploration=turno, note="Gestor de diálogo: nenhuma análise executada pela conversa.")
    if turno.get("painel"):
        resposta["painel"] = turno["painel"]
    for chave in ("memoria", "dialogo", "acoes", "desfazer", "modelo_de_resposta", "redacao", "continuar"):
        if chave in turno:
            resposta[chave] = turno[chave]
    return resposta


def _indisponivel(causa: str) -> dict:
    """Sem o componente de linguagem (seção 11.4 da missão de 26/10/2026): a comunicação cordial, como resposta da
    conversa, sem código nem mensagem técnica; os controles e as análises continuam. Nada é executado."""
    aviso = llm_bridge.indisponibilidade(causa)
    resposta = _system_response(aviso["texto"], None, "")
    resposta.update(indisponibilidade=aviso, degradado=True,
                    note="Componente de linguagem indisponível; os controles e as análises da tela continuam.")
    return resposta


RESERVA_DA_INTERPRETACAO = ("Não consegui interpretar este pedido com segurança. Pode dizer de outro jeito? Os pedidos sobre o "
                            "gráfico, como “compare dois territórios” ou “mostre a tendência”, e os botões da tela "
                            "continuam disponíveis.")


def _sem_o_modelo(exc: LLMError) -> dict:
    """A resposta quando o provedor não serviu: saída fora do contrato depois das tentativas (reserva de interpretação) ou
    indisponibilidade (cota, rede, configuração), cada uma com o seu tratamento (seção 11.4, item F)."""
    if exc.causa == "contrato":
        resposta = _system_response(RESERVA_DA_INTERPRETACAO, None, "")
        resposta.update(reserva=True, note="Saída do provedor fora do contrato depois das tentativas previstas.")
        return resposta
    return _indisponivel(exc.causa)


def _conversa_pelo_modelo(rapida: dict | None) -> bool:
    """Uma orientação do catálogo local que o Gemini pode redigir (o funcionamento do agente, um conceito): com o provedor
    disponível, sim; saudação e agradecimento continuam com o texto fixo."""
    if rapida is None or not conversa_gemini.ativa():
        return False
    texto = str(rapida.get("reply") or "")
    return not texto.startswith(("Olá", "De nada"))


def _turnos_da_tela(texto) -> list[dict]:
    """A janela da conversa que a tela envia (campo `turnos`): as mensagens mais recentes da pessoa e do agente."""
    try:
        valor = json.loads(texto) if isinstance(texto, str) and texto.strip() else []
    except json.JSONDecodeError:
        return []
    return [t for t in valor if isinstance(t, dict)][-12:] if isinstance(valor, list) else []


def _classes_do_resultado(resultado: dict | None) -> list[str]:
    return list(dict.fromkeys((item.get("tendencia") or {}).get("classe") for item in (resultado or {}).get("itens") or []
                              if (item.get("tendencia") or {}).get("avaliavel")))


VISTAS_DO_INTERPRETE = ("show_map", "show_chart", "show_table", "previous_result")
TOPICOS_DAS_FICHAS = {"density": "densidade", "spatial": "distancia", "aggregation": "agregacao", "distribution": "grupos",
                      "nearest": "referencia"}


def _fonte_do_cartao(dataset: str) -> dict:
    return {"tipo": "brasil"} if dataset == "brazil" else {"tipo": "arquivo"}


def _fichas_da_documentacao(resposta: dict) -> list[str]:
    """As fichas de método do tema que a resposta do catálogo explica (densidade, distância, agregação…)."""
    return [TOPICOS_DAS_FICHAS[t] for t, ids in TOPICS.items()
            if any(doc.get("id_doc") in ids for doc in resposta.get("documentation") or [])][:1]


# Proteção da triagem da base do Brasil por versão e escopo: os valores da versão não mudam, e montá-la a cada mensagem
# relia e conferia os arquivos da base (SHA-256) e copiava o quadro inteiro.
_PROTECOES_DO_BRASIL: dict[tuple[str, str], triagem.Protecao] = {}


async def _protecao_do_pedido(file, sheet, dataset, scope, dataset_version, fields) -> triagem.Protecao:
    """A proteção da base do pedido, quando há base; sem base, a triagem só com as unidades federativas."""
    chave = (dataset_version, scope or "") if dataset == "brazil" and dataset_version and not file else None
    if chave in _PROTECOES_DO_BRASIL:
        return _PROTECOES_DO_BRASIL[chave]
    try:
        frame, _ = await _request_dataset(file, sheet, dataset, scope, dataset_version=dataset_version)
    except (ValueError, TypeError, HTTPException):
        frame = None
    if frame is None or frame.empty:
        return triagem.Protecao(liberados=frozenset(triagem.dobrar(n) for par in STATES.values() for n in par))
    papeis = suggested_mapping(frame) if dataset == "brazil" else (fields if isinstance(fields, dict) else {})
    protecao = protecao_da_fonte(frame, papeis, sheet)
    if chave is not None:
        if len(_PROTECOES_DO_BRASIL) >= 4:
            _PROTECOES_DO_BRASIL.clear()
        _PROTECOES_DO_BRASIL[chave] = protecao
    return protecao


async def _redigida(base: dict, mensagem: str, turnos, conversa_tela, grafico, resultado, anterior, fonte, rotulos,
                    protecao, *, fatos: str, termos=(), pedidas=(), acao: bool = False, registro: str = "objetivo",
                    rascunho: str | None = None, marcadores: dict | None = None) -> dict:
    """A resposta com o texto redigido pelo Gemini e conferido (conversa_gemini.redigir), ou com a reserva verificada.
    O cartão leva o resultado em exibição, a tela, a conversa, os fatos verificados e as fichas de método."""
    fichas_pedidas = [definicoes.FICHAS[i] for i in pedidas if i in definicoes.FICHAS]
    fichas = list(dict.fromkeys([*fichas_pedidas, *definicoes.pertinentes(
        mensagem, termos=termos, classes=_classes_do_resultado(resultado), familia=(grafico or {}).get("familia"))]))
    contexto = contexto_conversa.montar(mensagem=mensagem, turnos=turnos, memoria=conversa_tela, grafico=grafico,
                                        resultado=resultado, anterior=anterior, fonte=fonte, rotulos=rotulos, fatos=fatos,
                                        fichas=fichas, protecao=protecao)
    refs = contexto_conversa.referencias_de_fidelidade(
        mensagem=mensagem, turnos=turnos, resultado=resultado, anterior=anterior, fatos=fatos, fichas=fichas,
        pedidas=fichas_pedidas, acao=acao, marcadores={**contexto["numeracao"].originais(), **(marcadores or {})})
    redigida = await conversa_gemini.redigir(contexto=contexto, refs=refs, reserva=str(base.get("reply") or fatos),
                                             registro=registro, rascunho=rascunho)
    resposta = {**base, "reply": redigida["texto"], "redacao": {"origem": redigida["origem"],
                                                                 "tentativas": redigida["tentativas"]}}
    if base.get("clarification") and isinstance(base["clarification"], str):
        resposta["clarification"] = redigida["texto"]
    return resposta


async def _redacao_da_interpretacao(answer: dict, mensagem, turnos, conversa_tela, grafico, resultado, anterior, fonte,
                                    rotulos, protecao) -> dict:
    """Interpretação sem comando nem ato executado pelo gestor (conversa, funcionamento do agente, conceito do catálogo, ou
    ato que o gestor não pôde executar): o texto que o Gemini já redigiu junto com a interpretação é conferido; aprovado,
    aparece no lugar do texto do catálogo."""
    rascunho = answer.get("_resposta_modelo") or ""
    if (not rascunho.strip() or (answer.get("proposal") or {}).get("operation") or answer.get("exploration") or
            answer.get("painel") or answer.get("clarification") or
            answer.get("dialogue_action") in ("explain_result", "simplify", "next_steps", "change_selection",
                                              "change_period", *VISTAS_DO_INTERPRETE)):
        return answer
    topico = next((TOPICOS_DAS_FICHAS[t] for t, ids in TOPICS.items()
                   if any(doc.get("id_doc") in ids for doc in answer.get("documentation") or [])), None)
    return await _redigida(answer, mensagem, turnos, conversa_tela, grafico, resultado, anterior, fonte, rotulos, protecao,
                           fatos=str(answer.get("reply") or ""), pedidas=[topico] if topico else [], rascunho=rascunho,
                           marcadores=answer.get("_marcadores"))


@app.post("/api/llm/interpret-context")
async def llm_interpretation_with_dataset(
    file: UploadFile | None = File(None),
    message: str = Form(...),
    history: str = Form("[]"),
    context_ready: str = Form("true"),
    mapping: str = Form("{}"),
    options: str = Form("{}"),
    sheet: str = Form(""),
    dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form(""),
    context_revision: int = Form(0), displayed_result_id: str = Form(""), conversa: str = Form(""),
    turnos: str = Form("[]"), x_adt_session: str | None = Header(None),
) -> dict:
    """Pré-exame local de uma base e interpretação com o provedor, com o cartão do contexto (contexto_conversa.py).

    O arquivo é lido pelo FastAPI apenas; nenhuma linha, nome de coluna ou nome de arquivo vai ao provedor. Vão a mensagem
    triada, a janela da conversa triada e, na página única, o estado da tela e o resultado agregado em exibição.
    """
    try:
        llm_bridge.iniciar_relogio()
        janela = _turnos_da_tela(turnos)
        request = ChatRequest(message=message, history=json.loads(history), context_revision=context_revision,
                              displayed_result_id=displayed_result_id, turnos=janela)
        if x_adt_session:
            sessions.event(x_adt_session, "ENVIO_MENSAGEM")
        fields = json.loads(mapping)
        settings = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Contexto de análise inválido.")
        # Página única: o estado do gráfico chega em options; o pré-exame recebe só as opções do intérprete, e o papel
        # grupo_territorial (coluna-mãe das planilhas) fica com a conversa no gráfico.
        grafico = conversa_grafico.contexto(settings)
        grupo_territorial = None
        if grafico is not None:
            settings = conversa_grafico.opcoes_do_interprete(settings, grafico)
            fields, grupo_territorial = conversa_grafico.campos_do_mapeamento(fields)
            turno = await _turno_do_dialogo(message, conversa, settings, grafico, file, mapping, sheet, dataset, scope,
                                            dataset_version, x_adt_session, displayed_result_id, redacao_permitida=True,
                                            turnos=janela)
            if turno is not None:
                return _resposta_do_dialogo(turno)
        # Orientações genéricas não exigem ler nem reenviar um arquivo inteiro.
        # O canal local não solicita, valida ou executa análise da base.
        quick = llm_local_response(request)
        if quick is not None and (not x_adt_session or dialogue_action(message) != "simplify"):
            if _conversa_pelo_modelo(quick):
                # Com o provedor disponível, o Gemini redige a orientação a partir do texto do catálogo, com a tela.
                resultado, anterior = _resultados_da_conversa(x_adt_session, displayed_result_id)
                protecao = await _protecao_do_pedido(file, sheet, dataset, scope, dataset_version, fields)
                quick = await _redigida(quick, message, janela, _conversa_da_tela(conversa), grafico, resultado, anterior,
                                        _fonte_do_cartao(dataset), (grafico or {}).get("rotulos"), protecao,
                                        fatos=quick["reply"], pedidas=_fichas_da_documentacao(quick))
            if x_adt_session:
                sessions.revision(x_adt_session, context_revision)
                sessions.remember(x_adt_session, context_revision, quick)
            return quick
        # O campo chega como texto; ausente vale "true". A leitura explícita não depende de como cada
        # versão do FastAPI converte um booleano ausente (a 0.147 passou a tratá-lo como falso).
        if context_ready.strip().lower() in ("false", "0", "no", "off"):
            raise HTTPException(status_code=409, detail="Aguarde ou repita a validação da base antes de solicitar uma proposta analítica.")
        frame, _ = await _request_dataset(file, sheet, dataset, scope, dataset_version=dataset_version)
        if frame is None or frame.empty:
            raise ValueError("Selecione uma planilha com dados antes de utilizar o contexto.")
        if grafico is not None and dataset != "brazil":
            settings = conversa_grafico.papeis_escolhidos(settings, fields)
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
                reviewed["blockers"].append("Há mais de um período ou categoria no pedido; escolha o recorte.")
                reviewed["ambiguous_parameters"] = ambiguous
            return reviewed
        # O grupo territorial das planilhas (província, distrito…) é entidade não pessoal, como o território.
        protecao = protecao_da_fonte(frame, {**fields, **({"grupo_territorial": grupo_territorial} if grupo_territorial
                                                         else {})}, sheet)
        resultado_tela, anterior_tela = _resultados_da_conversa(x_adt_session, displayed_result_id)
        memoria_tela = _conversa_da_tela(conversa)
        contexto = contexto_conversa.montar(
            mensagem=message, turnos=janela, memoria=memoria_tela, grafico=grafico, resultado=resultado_tela,
            anterior=anterior_tela, fonte=_fonte_do_cartao(dataset), rotulos=(grafico or {}).get("rotulos"),
            protecao=protecao) if grafico is not None or janela else None
        try:
            answer = await llm_interpret(
                request, eligibility=eligibility, category_constant=declared_category,
                proposal_reviewer=review_local,
                conversation_context=dialogue_projection(capture, result_record is not None) if capture else None,
                protecao=protecao, contexto=contexto,
            )
        except LLMError as exc:
            if exc.causa == "entrada":
                raise
            return _sem_o_modelo(exc)
        if grafico is not None and isinstance(answer.get("dialogo_ato"), dict):
            # O intérprete com o provedor reconheceu um ato do diálogo que a leitura local não cobriu: o gestor o executa,
            # e o texto que o Gemini já redigiu é conferido contra a resposta verificada do gestor.
            ato = dialogo.do_interprete(answer["dialogo_ato"], message, memoria_tela)
            turno = await _turno_do_dialogo(message, conversa, settings, grafico, file, mapping, sheet, dataset, scope,
                                            dataset_version, x_adt_session, displayed_result_id, ato=ato,
                                            redacao_permitida=True, turnos=janela,
                                            rascunho=answer.get("_resposta_modelo"),
                                            marcadores=answer.get("_marcadores")) if ato else None
            if turno is not None:
                answer.update(_resposta_do_dialogo(turno, origem="INTERPRETACAO_LLM"))
                answer = llm_bridge.publico(answer)
                if x_adt_session:
                    sessions.remember(x_adt_session, context_revision, answer)
                return answer
        answer = await _redacao_da_interpretacao(answer, message, janela, memoria_tela, grafico, resultado_tela,
                                                 anterior_tela, _fonte_do_cartao(dataset),
                                                 (grafico or {}).get("rotulos"), protecao)
        # O LLM propõe a capacidade; nomes e IDs são resolvidos exclusivamente no Python,
        # usando a manifestação original e o catálogo local, que nunca segue ao provedor.
        proposed_operation = answer.get("proposal", {}).get("operation")
        slots = answer.get("verification", {}).get("slots", {})
        if grafico is not None:
            # Página única: a operação proposta vira o comando do gráfico, com nomes e competências do pedido original.
            if proposed_operation:
                local_frame, local_fields = frame, fields
                if dataset == "brazil" and frame.attrs.get("source", {}).get("scope") != "municipal":
                    local_frame, _ = await _request_dataset(None, "", "brazil", "municipal", dataset_version=dataset_version)
                    local_fields = suggested_mapping(local_frame)
                conversa_grafico.aplicar(answer, conversa_grafico.interpretar(
                    message, local_frame, local_fields, apply_premises(local_frame, local_fields, settings), grafico,
                    brasil=dataset == "brazil", opcoes=settings, grupo=grupo_territorial, dica=proposed_operation,
                    dica_indicador=answer["proposal"].get("indicator")))
        elif proposed_operation in ("comparisons", "density", "counts", "temporal", "aggregate") and not any(
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
        if grafico is None:
            # Fora da página única, o mesmo pedido também vem como comando do gráfico (mapeamento das operações atuais).
            painel_proposto = conversa_grafico.painel_do_legado(answer["exploration"]) if "exploration" in answer else \
                conversa_grafico.painel_da_operacao(proposed_operation, answer["proposal"].get("indicator"), message)
            if painel_proposto:
                answer["painel"] = painel_proposto
        if x_adt_session:
            if answer.get("dialogue_action") in ("next_steps", "change_selection", "change_period"):
                answer.update(screen_reply(answer["dialogue_action"], capture))
            elif answer.get("dialogue_action") in ("explain_result", "simplify"):
                answer.update(answer_result(message, answer["dialogue_action"], result_record, capture))
                # Uma intenção de explicação não muda a operação em preparação nem o gráfico.
                answer["proposal"] = _system_response("", None, "")["proposal"]
                answer.pop("exploration", None)
                answer.pop("painel", None)
            answer = llm_bridge.publico(answer)
            sessions.remember(x_adt_session, context_revision, answer)
        return llm_bridge.publico(answer)
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
    """Descrição factual das três partes da base residente, sem seus registros."""
    try:
        profiles = []
        sources = _brazil_sources()
        for scope in ("national", "state", "municipal"):
            frame = sources.frame(scope)
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
        periods = sorted({period for profile in profiles for period in profile["periods"]})
        categories = sorted({category for profile in profiles for category in profile["categories"]})
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
            " em recortes do país, dos estados e dos municípios, com referências temporais de " +
            human_period(periods[0]) + " a " + human_period(periods[-1]) + ". "
            "A base inclui quantitativos por período e categoria profissional; "
            "a parte municipal também contém população estimada e coordenadas "
            "para análises de densidade e localização. "
            "O total do Brasil vem da fonte nacional, e o de cada estado, da fonte estadual de médicos únicos (quem atua "
            "em mais de um município do estado conta uma vez). As densidades usam a população municipal: a de junho do "
            "ano no Brasil e a soma dos municípios do estado na própria competência (regras governadas). As fontes não "
            "são somadas entre si."
        )
        return {"description": narrative, "scopes": profiles}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Os dados do Brasil não estão disponíveis para consulta.") from exc


@app.post("/api/inspect")
async def inspect(file: UploadFile | None = File(None), sheet: str = Form(""),
                  dataset: str = Form(""), scope: str = Form("auto"), operation: str = Form("")):
    try:
        frame, sheets, sources = await _request_dataset(file, sheet, dataset, scope, operation, with_sources=True)
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
        levels = None
        if sources is not None and source_identity(frame) == "municipal":
            # Base oficial: Brasil, estados e municípios para a abrangência territorial (sem dados da base ao provedor).
            levels = territorial_levels.inspect_block(sources, mapping)
        return {"requires_sheet": False, "sheets": sheets, "columns": frame.columns.tolist(), "row_count": len(frame),
                **({"niveis": levels} if levels else {}),
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
        frame, _, sources = await _request_dataset(file, sheet, dataset, scope, operation, dataset_version, with_sources=True)
        if frame is None:
            raise ValueError("Selecione uma planilha para concluir o exame.")
        fields = json.loads(mapping)
        settings = json.loads(options)
        if isinstance(settings, dict) and "abrangencia" in settings:
            # Mesmo roteamento do /api/analyze; a rota de níveis devolve o esquema atual da fonte municipal (com a lista
            # de municípios da tela) e capabilities[op].niveis.
            try:
                route = territorial_levels.resolve(sources, fields, operation or "density", settings, scope)
            except ChoiceRequired as exc:
                # Escolha pendente na abrangência (estados e municípios juntos, ou territórios de menos): a tela mostra o
                # motivo e mantém o cálculo bloqueado; o pré-exame não é recusado.
                return territorial_levels.pending_preflight(sources, fields, operation or "density", settings, str(exc))
            if route.kind != "niveis":
                return preflight(route.frame, route.mapping, apply_premises(route.frame, route.mapping, route.options))
            municipal = sources.frame("municipal")
            base = preflight(municipal, fields, apply_premises(municipal, fields, route.options))
            return territorial_levels.level_preflight(base, sources, fields, route.options, route.abrangencia,
                                                      territorial_levels.municipal_index(municipal))
        return preflight(frame, fields, apply_premises(frame, fields, settings))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/exploration/interpret")
async def exploration_interpret(message: str = Form(...), file: UploadFile | None = File(None),
                               mapping: str = Form("{}"), options: str = Form("{}"), sheet: str = Form(""),
                               dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form(""),
                               context_revision: int = Form(0), conversa: str = Form(""),
                               displayed_result_id: str = Form(""), x_adt_session: str | None = Header(None)):
    try:
        if len(message) > 800:
            raise ValueError("Mensagem acima do limite de 800 caracteres.")
        if x_adt_session:
            sessions.event(x_adt_session, "ENVIO_MENSAGEM")
            sessions.revision(x_adt_session, context_revision)
        requested = json.loads(options)
        if not isinstance(requested, dict):
            raise ValueError("Parâmetros inválidos.")
        # Página única (Docs/CONVERSACAO_INCREMENTO_FN.md, "Conversa no gráfico"): o estado do gráfico chega em options,
        # e o pedido volta como o comando `painel`. Nas demais telas, o caminho anterior continua.
        grafico = conversa_grafico.contexto(requested)
        if grafico is not None:
            requested = conversa_grafico.opcoes_do_interprete(requested, grafico)
            # Gestor de diálogo (26/10/2026): memória, continuidade, explicação, verificação e governança, sem o provedor.
            turno = await _turno_do_dialogo(message, conversa, requested, grafico, file, mapping, sheet, dataset, scope,
                                            dataset_version, x_adt_session, displayed_result_id)
            if turno is not None:
                return turno  # a resposta do gestor ou ADIAR (pergunta de conversa para o canal com o Gemini)
        if dialogue_action(message) and not (grafico is not None and conversa_grafico.comando_do_grafico(message)):
            if requested.get("conversation_operation_choice") == "comparisons":
                message = "Compare esses municípios"  # escolha explícita na alternativa; ainda sem cálculo
            else:
                return {"handled": False}  # o canal contextual distingue explicação de execução
        if grafico is None:
            command = criteria_command(message, requested)  # critérios combinados: só estrutura, sem dados nem cálculo
            if command is not None:
                return conversa_grafico.com_painel(command)
        # Uma pergunta de orientação não responde à pendência territorial anterior.
        # Atendê-la aqui evita que o resolvedor de nomes a transforme em novo pedido de municípios.
        quick = llm_local_response(ChatRequest(message=message, history=[]))
        if quick is not None:
            if (x_adt_session and quick.get("documentation")) or _conversa_pelo_modelo(quick):
                # Registra o referente documental no contexto da sessão, ou o Gemini redige a orientação no canal contextual.
                return {"handled": False}
            return {"handled": True, "reply": quick["reply"], "executed": False}
        choice = requested.get("conversation_operation_choice")
        if choice is not None:
            from analysis_catalog import OPERATION_LABELS
            if choice not in OPERATION_LABELS:
                raise ValueError("Tipo de análise escolhido não reconhecido.")
        if grafico is not None:
            return await _conversa_no_grafico(message, file, mapping, sheet, dataset, scope, dataset_version, requested,
                                              grafico, choice, x_adt_session, context_revision)
        correction = bool(re.fullmatch(r"(?:nao[, ]+)?(?:quero |prefiro |use )?(?:quantidade|quantitativos|densidade)[.!?]*", normalize_exploration(message)))
        adding = bool(re.search(r"\b(?:acrescente|adicione|inclua)\b", normalize_exploration(message)))
        if not choice and not operation_for(message) and not requested.get("conversation_pending_operation") and not (
                requested.get("exploration_operation") and (correction or adding)) and not (
                requested.get("exploration_operation") and re.search(r"\b(?:analise|analisar)\b", normalize_exploration(message))) and not (
                requested.get("exploration_operation") and RELATIVE_YEARS.search(normalize_exploration(message))):
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
        return conversa_grafico.com_painel(interpret_exploration(message, frame, fields, settings, operation_hint=choice))
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _base_da_conversa(file, mapping, sheet, dataset, scope, dataset_version, requested):
    """A base da conversa no gráfico, lida como na interpretação local: (quadro, campos, opções com as premissas, opções
    do pedido, coluna do grupo territorial). Nada dela vai ao provedor de IA."""
    frame, _ = await _request_dataset(file, sheet, dataset, "municipal" if dataset == "brazil" else scope,
                                      dataset_version=dataset_version)
    if frame is None:
        raise ValueError("Escolha a planilha antes de explorar os territórios.")
    fields = json.loads(mapping)
    if not isinstance(fields, dict):
        raise ValueError("Parâmetros inválidos.")
    fields, grupo_territorial = conversa_grafico.campos_do_mapeamento(fields)
    if dataset == "brazil":
        fields, grupo_territorial = suggested_mapping(frame), None
    else:
        requested = conversa_grafico.papeis_escolhidos(requested, fields)
    return frame, fields, apply_premises(frame, fields, requested), requested, grupo_territorial


def _conversa_da_tela(texto) -> dict:
    """A memória da conversa que a tela envia (campo `conversa`): pendência, memória da resposta anterior e estados
    anteriores do gráfico. Fica no backend local; inválida, vale vazia."""
    try:
        valor = json.loads(texto) if isinstance(texto, str) and texto.strip() else {}
    except json.JSONDecodeError:
        return {}
    return valor if isinstance(valor, dict) else {}


def _resultados_da_conversa(x_adt_session, displayed_result_id):
    """O resultado do gráfico em exibição e o anterior, lidos da sessão com a integridade conferida (nunca valores do
    navegador); (None, None) sem sessão ou sem resultado do gráfico."""
    if not x_adt_session or not displayed_result_id:
        return None, None
    try:
        record = sessions.result(x_adt_session, displayed_result_id)
    except HTTPException:
        return None, None
    if record["result"].get("metadata", {}).get("operation") != painel.OPERATION:
        return None, None
    try:
        anterior = sessions.panel_before(x_adt_session, displayed_result_id)
    except HTTPException:
        anterior = None
    return record["result"], (anterior or {}).get("result")


def _descricao_do_brasil() -> str:
    try:
        return describe_brazil()["description"]
    except HTTPException:
        return ""


# Atos do gestor que são perguntas de conversa (o resultado, um conceito, a tela, uma verificação): com o provedor disponível,
# o Gemini redige a resposta a partir da resposta verificada do gestor. Comandos do gráfico, respostas a esclarecimentos,
# desfazer, voltar e as recusas de governança continuam com o texto determinístico.
CONVERSACIONAIS = frozenset(("compara", "diferenca", "contagem", "explica", "limite", "refere_anterior", "estado"))
ADIAR = {"handled": False}  # intérprete local: a pergunta de conversa segue para o canal com o Gemini


def _pedidas_do_ato(ato: dict, resposta: dict) -> list[str]:
    """As fichas que a resposta precisa explicar: as classes que a explicação destacou e os temas do catálogo pedidos."""
    pedidas = []
    for acao in resposta.get("acoes") or []:
        if isinstance(acao, dict) and acao.get("tipo") == "explicar":
            pedidas += ["classe:" + codigo for codigo in acao.get("termos") or [] if "classe:" + str(codigo) in definicoes.FICHAS]
    if ato.get("ato") == "explica" and ato.get("topico") == "conceito":
        for termo in ato.get("termos") or []:
            if termo in ("densidade", "distancia", "referencia", "quintil", "agregacao", "velocidade"):
                pedidas += list(definicoes.DO_TERMO.get(termo, ()))
    return list(dict.fromkeys(pedidas))


async def _turno_do_dialogo(message, conversa, requested, grafico, file, mapping, sheet, dataset, scope, dataset_version,
                            x_adt_session, displayed_result_id, ato=None, redacao_permitida=False, turnos=None,
                            rascunho=None, marcadores=None):
    """Gestor de diálogo (dialogo.py) da página única, antes da gramática local e do intérprete com o provedor: resposta
    digitada a esclarecimentos, continuidade, perguntas sobre o resultado em exibição, explicação, verificação, estado da
    tela e governança. `ato` vem do intérprete com o provedor quando o reconhecimento local não cobre a formulação. None:
    o pedido segue o caminho de antes. ADIAR: pergunta de conversa no intérprete local, com o provedor disponível; ela
    segue para o canal contextual, onde o Gemini redige a resposta. Nunca calcula."""
    if not dialogo.ativo() or grafico is None:
        return None
    memoria = _conversa_da_tela(conversa)
    resultado, anterior = _resultados_da_conversa(x_adt_session, displayed_result_id)
    if ato is None:
        ato = dialogo.reconhecer(message, memoria, resultado is not None,
                                 resultado_tendencia=(resultado.get("tendencia") is not None) if resultado else None,
                                 nomes_no_resultado=[item.get("rotulo", "") for item in (resultado or {}).get("itens") or []
                                                     if item.get("tipo") in ("municipio", "estado")])
    if ato is None:
        return None
    conversacional = ato.get("ato") in CONVERSACIONAIS
    if conversacional and not redacao_permitida and conversa_gemini.ativa():
        return dict(ADIAR)
    interpretar = nomes = None
    frame = fields = grupo = None
    if ato["ato"] in dialogo.PRECISA_DA_BASE or (ato["ato"] == "estado" and ato.get("assunto") == "ausente"):
        frame, fields, settings, opcoes, grupo = await _base_da_conversa(file, mapping, sheet, dataset, scope,
                                                                        dataset_version, requested)
        brasil = dataset == "brazil"

        def interpretar(texto, dica=None, dica_indicador=None):
            return conversa_grafico.interpretar(texto, frame, fields, settings, grafico, brasil=brasil, opcoes=opcoes,
                                                grupo=grupo, dica=dica, dica_indicador=dica_indicador)

        def nomes(texto):
            return conversa_grafico.nomes_citados(texto, frame, fields, settings, grafico, brasil=brasil, opcoes=opcoes,
                                                  grupo=grupo)
    fonte = {"tipo": "brasil", "descricao": _descricao_do_brasil() if ato.get("assunto") == "dados" else ""} \
        if dataset == "brazil" else {"tipo": "arquivo", "nome": getattr(file, "filename", "") or ""}
    rotulos = grafico.get("rotulos") or ({"unidade": {"singular": "município", "plural": "municípios"},
                                          "grupo": {"singular": "estado", "plural": "estados"}} if dataset == "brazil"
                                         else {})
    ambiente = dialogo.Ambiente(message, memoria, grafico, resultado, anterior, fonte, interpretar, nomes, rotulos)
    try:
        resposta = dialogo.executar(ato, ambiente)
    except Exception:  # noqa: BLE001 — defeito do gestor (inclusive composição recusada na conferência): registrado no log;
        # o pedido segue o caminho de antes, que não depende do gestor, em vez de falhar.
        logging.getLogger(__name__).exception("Falha no gestor de diálogo; o pedido segue o caminho anterior")
        return None
    if resposta is None:
        return None
    resposta.pop("_composicao", None)
    if conversacional and redacao_permitida and (conversa_gemini.ativa() or rascunho):
        if frame is not None:
            protecao = protecao_da_fonte(frame, {**fields, **({"grupo_territorial": grupo} if grupo else {})}, sheet)
        else:
            protecao = await _protecao_do_pedido(file, sheet, dataset, scope, dataset_version, json.loads(mapping or "{}"))
        registro = ato.get("registro") or (resposta.get("memoria") or {}).get("registro") or "objetivo"
        resposta = await _redigida(resposta, message, turnos, memoria, grafico, resultado, anterior, fonte, rotulos,
                                   protecao, fatos=resposta.get("reply") or "", termos=ato.get("termos") or [],
                                   pedidas=_pedidas_do_ato(ato, resposta),
                                   acao=bool(resposta.get("painel") or resposta.get("acoes")), registro=registro,
                                   rascunho=rascunho, marcadores=marcadores)
    return resposta


async def _conversa_no_grafico(message, file, mapping, sheet, dataset, scope, dataset_version, requested, grafico, choice,
                               x_adt_session, context_revision):
    """Pedido da página única: a base é lida como na interpretação local e o pedido volta como o comando `painel`
    (conversa_grafico.py), sem cálculo e sem o provedor de IA. Sem comando reconhecido, {"handled": False} leva o pedido
    ao intérprete com o provedor, como antes."""
    frame, fields, settings, requested, grupo_territorial = await _base_da_conversa(file, mapping, sheet, dataset, scope,
                                                                                   dataset_version, requested)
    if x_adt_session:
        sessions.capture(x_adt_session, context_revision, investigation_context(frame, fields, settings,
                                                                               preflight(frame, fields, settings)))
    return conversa_grafico.interpretar(message, frame, fields, settings, grafico, brasil=dataset == "brazil",
                                        opcoes=requested, grupo=grupo_territorial, dica=choice,
                                        dica_indicador=requested.get("exploration_indicator") if choice else None)


@app.post("/api/analyze")
async def analyze(file: UploadFile | None = File(None), operation: str = Form(...), mapping: str = Form("{}"),
                  options: str = Form("{}"), sheet: str = Form(""),
                  dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form(""),
                  geo_version: str = Form(""), context_revision: int = Form(0),
                  x_adt_session: str | None = Header(None)):
    try:
        if x_adt_session:
            sessions.event(x_adt_session, "CONFIRMACAO")  # evento de sessão: execução pedida pelo usuário
        frame, _, sources = await _request_dataset(file, sheet, dataset, scope, operation, dataset_version,
                                                   with_sources=True)
        if frame is None:
            raise ValueError("Selecione a planilha Excel antes de executar.")
        fields = json.loads(mapping)
        requested = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(requested, dict):
            raise ValueError("Parâmetros de análise inválidos.")
        route = None
        if "abrangencia" in requested:
            # Brasil, estados e municípios (D3): só municípios seguem o caminho municipal; só o Brasil sem densidade, o
            # nacional; o resto, a rota de níveis (territorial_levels.py), que nunca soma um nível a outro.
            route = territorial_levels.resolve(sources, fields, operation, requested, scope)
            if route.kind == "niveis":
                return _analyze_levels(route, sources, operation, x_adt_session, context_revision)
            frame, fields, requested = route.frame, route.mapping, route.options
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
        if route is not None:
            result["notes"] += territorial_levels.coverage_notes(route.selecao, operation)
            result["metadata"]["selecao_territorial"] = route.selecao
        if sources is not None and territorial_levels.wants_reference(operation, settings, frame):
            # D5: taxa nacional como referência de contexto na densidade da base oficial, também sem abrangência.
            territorial_levels.attach_reference(result, sources, result["metadata"]["periods"],
                                                result["metadata"]["categories"])
        return _seal(result, frame, fields, settings, operation, x_adt_session, context_revision, capture, geo)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _analyze_levels(route, sources, operation, x_adt_session, context_revision):
    """Rota de níveis: portão das partes, cálculo por universo e a mesma selagem (chave, sessão) da rota atual."""
    municipal = sources.frame("municipal")
    fields = route.mapping
    index = territorial_levels.municipal_index(municipal)
    settings = apply_premises(municipal, fields, route.options, spatial=False)
    eligibility = territorial_levels.gate(sources, route, operation, settings, index)
    capture = sessions.capture(x_adt_session, context_revision,
              investigation_context(municipal, fields, settings, eligibility)) if x_adt_session else None
    result = territorial_levels.compute_levels(sources, route, operation, settings)
    settings = {**settings, "abrangencia": territorial_levels.serialize(route.abrangencia)}
    return _seal(result, municipal, fields, settings, operation, x_adt_session, context_revision, capture, None)


def _attach_summary(result: dict) -> None:
    """Frase-resumo, indicadores e procedência (result_summary.py) em metadata.representacao.resumo, depois do
    result_id. Como a representação, uma falha nunca invalida o resultado: o resumo apenas não é anexado. Só para a
    interface; não entra em llm_context nem em provider_snapshot."""
    representation = result["metadata"].get("representacao")
    if not isinstance(representation, dict):
        return
    try:
        from result_summary import summary
        resumo = summary(result)
    except Exception:  # noqa: BLE001 — registrada no log; tabela, gráficos e exportações seguem disponíveis
        logging.getLogger(__name__).exception("Falha ao compor a frase-resumo do resultado")
        resumo = None
    if resumo:
        representation["resumo"] = resumo


def _seal(result, frame, fields, settings, operation, x_adt_session, context_revision, capture, geo):
    """Identidade do resultado: hash dos dados, chave de execução reproduzível e registro na sessão."""
    result["metadata"]["data_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()
    result["result_id"] = str(uuid.uuid4())
    result["metadata"]["created_at"] = datetime.now(timezone.utc).isoformat()
    signature = {"data": result["metadata"]["data_sha256"], "source": result["metadata"].get("source", frame.attrs.get("source")),
                 "mapping": fields, "options": settings, "operation": operation,
                 "method": result["metadata"]["method_version"]}
    if result["metadata"].get("metodos"):  # só quando um método versionado é usado (tendência, níveis, população)
        signature["metodos"] = result["metadata"]["metodos"]
    if geo is not None and geo["estado"] == "valido":  # só quando a camada pode alterar o resultado espacial
        signature["geo_complement"] = geo
    result["metadata"]["execution_key"] = hashlib.sha256(json.dumps(signature, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    result["metadata"]["validity"] = "VALIDO"
    result["metadata"]["presentations"] = ["table", "csv", "metadata_json", "print"]
    _attach_summary(result)
    if capture:
        result["conversation_reference"] = {"available": sessions.record_result(
            x_adt_session, context_revision, result, capture["context"])}
    return result


async def _panel_request(file, sheet, dataset, scope, dataset_version, mapping, options, uploads_allowed):
    """Pedido do painel integrado. A base Brasil oficial (fonte municipal) é lida e verificada como em /api/analyze
    (integridade pelo manifesto; versão divergente recusada). A planilha enviada é lida como em /api/analyze (limite de
    30 MB, planilha escolhida, nada persistido); só vale quando `uploads_allowed` aceita o pedido (página única)."""
    if file is not None:
        fields, requested = json.loads(mapping), json.loads(options)
        if not isinstance(fields, dict) or not isinstance(requested, dict) or not uploads_allowed(requested):
            raise ValueError(painel.OFFICIAL_ONLY)
        if dataset:
            raise ValueError("Escolha uma base do catálogo ou importe um arquivo.")
        frame, _ = await _request_dataset(file, sheet, "", "auto")
        if frame is None:
            raise ValueError("Escolha a planilha (aba) do arquivo antes de pedir o gráfico.")
        return frame, None, fields, requested
    if dataset != "brazil":
        raise ValueError(painel.OFFICIAL_ONLY)
    if scope not in ("municipal", "auto"):
        raise ValueError("O painel usa a fonte municipal da base Brasil: envie scope=municipal.")
    fields, requested = json.loads(mapping), json.loads(options)
    if not isinstance(fields, dict) or not isinstance(requested, dict):
        raise ValueError("Parâmetros do painel inválidos.")
    frame, _, sources = await _request_dataset(None, "", "brazil", "municipal", "", dataset_version, with_sources=True)
    return frame, sources, fields, requested


class _PanelJSON(JSONResponse):
    """Resposta do gráfico: os mesmos bytes de JSONResponse, sem a conferência de referências circulares do json (a
    resposta é montada pelo motor só com dicionários, listas e valores nativos), que pesa com milhares de itens."""

    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":"),
                          check_circular=False).encode("utf-8")


def _panel_pending(exc: ChoiceRequired) -> JSONResponse:
    """Escolha pendente (422): o texto em `detail` e a pendência estruturada, para a tela oferecer a escolha."""
    return JSONResponse(status_code=422, content={"detail": str(exc), "pendencia": painel.pendencia(exc)})


def _attach_panel_summary(body: dict) -> None:
    """Frase-resumo da página única (resumo_painel.py) em `resumo`, antes do registro na sessão. Como a frase-resumo de
    /api/analyze, uma falha nunca derruba a resposta: registrada no log, o campo é omitido. Só para a interface; nada
    dela vai ao provedor de IA."""
    try:
        from resumo_painel import summary
        resumo = summary(body, painel.summary_facts(body))
    except Exception:  # noqa: BLE001 — registrada no log; o gráfico, a tabela e as exportações seguem disponíveis
        logging.getLogger(__name__).exception("Falha ao compor a frase-resumo do gráfico")
        resumo = None
    if resumo:
        body["resumo"] = resumo


def _panel_session(x_adt_session, context_revision, body, frame, fields, requested) -> None:
    """Página única: grava o resultado do gráfico na sessão (Histórico e conversa), com um contexto próprio que não
    substitui o da conversa. Uma falha só deixa `sessao.registrado` falso; o cálculo é devolvido do mesmo jeito."""
    if not x_adt_session:
        body["sessao"] = {"registrado": False, "result_id": None,
                          "motivo": "Sem sessão: o pedido não trouxe o cabeçalho X-ADT-Session."}
        return
    result_id = str(uuid.uuid4())
    body["sessao"] = {"registrado": True, "result_id": result_id, "motivo": None}
    try:
        recorded = sessions.record_panel(x_adt_session, context_revision, painel.session_record(body, result_id),
                                         painel.session_context(frame, fields, requested, body))
        reason = None if recorded else "Limite de resultados da sessão atingido; o gráfico foi calculado e não foi gravado."
    except HTTPException as exc:
        recorded, reason = False, str(exc.detail)
    if not recorded:
        body["sessao"] = {"registrado": False, "result_id": None, "motivo": reason}


@app.post("/api/painel")
async def integrated_panel(file: UploadFile | None = File(None), mapping: str = Form("{}"), options: str = Form("{}"),
                           sheet: str = Form(""), dataset: str = Form(""), scope: str = Form("municipal"),
                           dataset_version: str = Form(""), geo_version: str = Form(""), context_revision: int = Form(0),
                           x_adt_session: str | None = Header(None)):
    """Painel integrado de bolhas (Docs/PAINEL_INTEGRADO.md): população, quantidade, densidade, distância até a
    referência e variação de cada município e conjunto, calculadas pelo motor; a tela só posiciona, filtra e desenha.
    Com `nivel` (página única): estados, planilhas enviadas, tendência, grupos, faixas, condições, ordenação, comparação,
    rotatividade, disponibilidade, contexto do Brasil e o registro do resultado na sessão. Nada vai ao provedor de IA."""
    try:
        if x_adt_session:
            sessions.event(x_adt_session, "CONFIRMACAO")  # evento de sessão: execução pedida pelo usuário
        frame, sources, fields, requested = await _panel_request(file, sheet, dataset, scope, dataset_version, mapping,
                                                                 options, painel.is_page)
        if sources is not None and geo_version and requested.get("referencia"):
            geo = _geo_identity(frame, "nearest", {})
            if geo is not None and geo_version != _geo_token(geo):
                raise ValueError("A camada geográfica complementar mudou depois da preparação. Carregue novamente a base "
                                 "antes de analisar.")
        body = painel.compute(sources, fields, requested, frame=None if sources is not None else frame)
        if painel.is_page(requested):
            _attach_panel_summary(body)
            _panel_session(x_adt_session, context_revision, body, frame, fields, requested)
        # Resposta já em tipos JSON nativos (sem NaN): serializada direto, sem a conversão genérica do FastAPI, que
        # pesaria com milhares de municípios.
        return _PanelJSON(body)
    except ChoiceRequired as exc:
        return _panel_pending(exc)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/painel/referencias")
async def integrated_panel_references(file: UploadFile | None = File(None), mapping: str = Form("{}"),
                                      options: str = Form("{}"), sheet: str = Form(""), dataset: str = Form(""),
                                      scope: str = Form("municipal"), dataset_version: str = Form(""),
                                      context_revision: int = Form(0)):
    """Candidatos à referência do painel, na ordem do critério (CAP-SUB-02), com empates na mesma posição e não
    avaliáveis à parte, na base Brasil ou numa planilha enviada. Só lista: não inicia análise nem escolhe a referência."""
    try:
        frame, sources, fields, requested = await _panel_request(file, sheet, dataset, scope, dataset_version, mapping,
                                                                 options, lambda requested: True)
        return JSONResponse(painel.references(sources, fields, requested, frame=None if sources is not None else frame))
    except ChoiceRequired as exc:
        return _panel_pending(exc)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/painel/mapa")
async def integrated_panel_map(file: UploadFile | None = File(None), mapping: str = Form("{}"), options: str = Form("{}"),
                               sheet: str = Form(""), dataset: str = Form(""), scope: str = Form("municipal"),
                               dataset_version: str = Form(""), geo_version: str = Form(""),
                               context_revision: int = Form(0)):
    """Coordenadas autorizadas do mapa da página única (Docs/PAINEL_INTEGRADO.md, "Rota 3"): o ponto de cada unidade
    da fonte na competência, o mesmo que a análise espacial usa para medir as distâncias, ou o motivo de não ter ponto.
    Base Brasil ou planilha enviada. Só lê: nada é registrado na sessão e nada vai ao provedor de IA."""
    try:
        frame, sources, fields, requested = await _panel_request(file, sheet, dataset, scope, dataset_version, mapping,
                                                                 options, lambda requested: True)
        if sources is not None and geo_version:
            geo = _geo_identity(frame, "nearest", {})
            if geo is not None and geo_version != _geo_token(geo):
                raise ValueError("A camada geográfica complementar mudou depois da preparação. Carregue novamente a base "
                                 "antes de analisar.")
        return _PanelJSON(painel.mapa(sources, fields, requested, frame=None if sources is not None else frame))
    except ChoiceRequired as exc:
        return _panel_pending(exc)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
