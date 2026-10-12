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
import os
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from pyproj import Geod
from semantic_bridge import candidates, normalize_headers, preflight, ROLES, EXACT, OPERATIONS
from data_contract import validate_operation, rotation_data, period_positions, scoped, text_values, count_unit_label, canonical_crs
from dataset_normalization import compose_period
from recommended_template import HEADERS as RECOMMENDED_HEADERS, LEGEND_HEADER, recommended_workbook
from territorial_hierarchy import describe_hierarchy
from brazil_data import load_brazil
from brazil_catalog_profile import curated_profile, apply_curated_options
from llm_bridge import ChatRequest, LLMError, interpret as llm_interpret, status as llm_status, local_response as llm_local_response
from llm_context import review_interpretation
from territorial_selection import universe_metadata
from exploration import interpret_exploration, operation_for

app = FastAPI(title="Agente Diagnóstico Territorial — Teste", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ADT_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
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
    if operation == "spatial" and canonical_crs(options.get("crs")):
        options = {**options, "crs": canonical_crs(options["crs"])}
    result = _compute(df, mapping, operation, options)
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
    result["metadata"]["evaluability"] = {"status": "AVALIAVEL_COM_LIMITACOES" if any(
        "Não avaliável" in str(value) or "possível dupla contagem" in str(value) for row in result["rows"] for value in row.values()) else "AVALIAVEL",
        "policy": "Ausências não são convertidas em zero; condições por elemento preservadas nas linhas."}
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
    if operation != "spatial":
        result["notes"].append("Unidade de contagem: " + str(unit) + ". Não há conversão entre pessoas, vínculos e postos.")
    if mapping.get("territory_id"):
        result["notes"].append("Identificação territorial: nome e código associado pelo usuário; códigos não foram confrontados com cadastro externo.")
    if options.get("duplicate_policy") == "remove_exact":
        removed = int(scoped(df, mapping, options).duplicated().sum())
        result["notes"].append(f"Remoção autorizada de {removed} cópias idênticas em todas as colunas.")
    if options.get("rows_additive_confirmed"):
        result["notes"].append("Componentes somados sob declaração de ausência de sobreposição do usuário; população territorial utilizada uma vez.")
    return result


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
            ongoing = len(c0 & c1)
            rows.append({"Território": ter, "Categoria": cat, "Período inicial": first, "Período final": last, "Coorte inicial": len(c0),
                         "Permanecem": ongoing, "Saíram": len(c0) - ongoing,
                         "Permanência (%)": 100 * ongoing / len(c0) if c0 else None,
                         "Rotatividade (%)": 100 * (len(c0) - ongoing) / len(c0) if c0 else None,
                         "Condição": "Avaliável" if c0 else "Coorte inicial vazia"})
        return _result("Rotatividade e permanência", "Coorte inicial de pessoas distintas; identificadores não são retornados.", rows,
                       notes=["É necessária identidade longitudinal autorizada e suficiente nos dois períodos; confirme essa condição antes de interpretar os resultados."])
    if operation == "spatial":
        geo = validate_operation(df, mapping, options, operation).rename(columns={"latitude": "lat", "longitude": "lon"})
        refname = options.get("reference_territory")
        match = geo[geo.territory == refname]
        if match.empty:
            raise ValueError("Selecione um território de referência existente na base.")
        reference = match.iloc[0]
        geod = Geod(ellps="GRS80")
        rows = []
        for _, item in geo.iterrows():
            _, _, meters = geod.inv(float(reference.lon), float(reference.lat), float(item.lon), float(item.lat))
            rows.append({"Território": item.territory, "Distância (km)": meters / 1000})
        return _result("Distâncias geodésicas", "Distância direta no referencial " + options["crs"] + ". Não representa tempo nem distância por estrada.",
                       sorted(rows, key=lambda x: x["Distância (km)"]), notes=["Referência: " + str(refname)])
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
            for i in range(1, k + 1):
                title = f"{i}º quintil — {names[i]}" if k == 5 else f"{i}ª faixa de {k}"
                rows.append({"Período": period, "Categoria": category,
                             "Classe": "Q" + str(i), "Quintil": title,
                             "Unidades": int((classes == i).sum()), "Indicador": label,
                             "Unidade de contagem": unit})
            for pos, (_, record) in enumerate(group.iterrows()):
                i = int(classes[pos])
                detail_rows.append({
                    "Território": record["territory"], "Período": period, "Categoria": category,
                    "Quintil": f"{i}º quintil" if k == 5 else f"{i}ª faixa de {k}",
                    label: float(record[metric]),
                    "Unidade de contagem": unit,
                    "Quantidade": float(record["quantity"]),
                    "População": float(record["population"]) if pd.notna(record["population"]) else None,
                })
        result = _result(
            "Distribuição territorial",
            "Unidades territoriais classificadas do menor para o maior valor do indicador escolhido. Cada período e categoria compõem um universo próprio.",
            rows, notes=["Indicador escolhido: " + label,
                         "Quintis com pontos de corte Hyndman–Fan tipo 7. Valores iguais permanecem na classe inferior, portanto as contagens podem ser diferentes.",
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
        result = _result("Evolução temporal", "Variação de " + ("densidade por 1.000 habitantes" if metric == "density" else "quantitativos") + " entre períodos; tendência somente com quatro ou mais observações.",
                       rows, notes=["Comparabilidade temporal e identidade longitudinal foram declaradas pelo usuário para esta execução.",
                                    "Cada competência é independente; não se somam pessoas de períodos diferentes."])
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


async def _request_dataset(file, sheet, dataset, scope, operation="", dataset_version=""):
    if bool(file) == bool(dataset):
        raise ValueError("Escolha uma base do catálogo ou importe um arquivo.")
    if dataset:
        if dataset != "brazil":
            raise ValueError("Base de dados não reconhecida.")
        raw, filename, source = load_brazil(scope, operation, dataset_version)
        frame, sheets = read_dataset(raw, filename)
        if frame is not None:
            frame.attrs["source"] = source
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


@app.get("/api/llm/status")
def llm_configuration_status() -> dict:
    """Indica disponibilidade local; não verifica crédito, franquia ou faturamento Google."""
    return llm_status()


@app.post("/api/llm/interpret")
async def llm_interpretation(request: ChatRequest) -> dict:
    """Interpretação preliminar, sem acesso a arquivos ou execução analítica."""
    try:
        return await llm_interpret(request)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


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
) -> dict:
    """Pré-exame local de uma base e interpretação LLM de um resumo técnico.

    O arquivo é lido pelo FastAPI apenas; nenhuma linha, coluna ou nome de
    arquivo é incorporado ao contexto entregue ao provedor.
    """
    try:
        request = ChatRequest(message=message, history=json.loads(history))
        fields = json.loads(mapping)
        settings = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Contexto de análise inválido.")
        # Orientações genéricas não exigem ler nem reenviar um arquivo inteiro.
        # O canal local não solicita, valida ou executa análise da base.
        quick = llm_local_response(request)
        if quick is not None:
            return quick
        if not context_ready:
            raise HTTPException(status_code=409, detail="Aguarde ou repita a validação da base antes de solicitar uma proposta analítica.")
        frame, _ = await _request_dataset(file, sheet, dataset, scope, dataset_version=dataset_version)
        if frame is None or frame.empty:
            raise ValueError("Selecione uma planilha com dados antes de utilizar o contexto.")
        settings = apply_curated_options(frame, fields, settings)
        eligibility = preflight(frame, fields, settings)
        declared_category = settings.get("category_constant", "") if settings.get("object_confirmed") is True else ""
        if not isinstance(declared_category, str):
            raise ValueError("Categoria declarada inválida.")
        return await llm_interpret(
            request, eligibility=eligibility, category_constant=declared_category,
            proposal_reviewer=lambda proposal: review_interpretation(proposal, eligibility,
                category_constant=declared_category, frame=frame, mapping=fields, options=settings)
        )
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
            frame, _ = read_dataset(raw, name)
            if frame is None or frame.empty:
                raise ValueError("A base do Brasil não está disponível.")
            mapping, _ = candidates(frame)
            frame.attrs["source"] = source
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
        mapping, profiles = candidates(frame)
        def available(role):
            col = mapping.get(role)
            return frame[col].dropna().astype(str).unique().tolist()[:80] if col else []
        from semantic_bridge import category_from_count_header
        profile = curated_profile(frame, mapping)
        return {"requires_sheet": False, "sheets": sheets, "columns": frame.columns.tolist(), "row_count": len(frame),
                "suggested_mapping": mapping, "column_profiles": profiles,
                "curated_defaults": profile,
                "derived_fields": frame.attrs.get("derived_fields", []),
                "source": frame.attrs.get("source"),
                "suggested_category_constant": category_from_count_header(mapping.get("count", "")),
                "preflight": preflight(frame, mapping, apply_curated_options(frame, mapping, {})),
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
        return preflight(frame, fields, apply_curated_options(frame, fields, settings))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/exploration/interpret")
async def exploration_interpret(message: str = Form(...), file: UploadFile | None = File(None),
                               mapping: str = Form("{}"), options: str = Form("{}"), sheet: str = Form(""),
                               dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form("")):
    try:
        if len(message) > 800:
            raise ValueError("Mensagem acima do limite de 800 caracteres.")
        if not operation_for(message):
            return {"handled": False}
        frame, _ = await _request_dataset(file, sheet, dataset, "municipal" if dataset == "brazil" else scope,
                                          dataset_version=dataset_version)
        if frame is None:
            raise ValueError("Escolha a planilha antes de explorar os territórios.")
        fields, settings = json.loads(mapping), json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Parâmetros inválidos.")
        if dataset == "brazil":
            fields, _ = candidates(frame)
        settings = apply_curated_options(frame, fields, settings)
        return interpret_exploration(message, frame, fields, settings)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyze")
async def analyze(file: UploadFile | None = File(None), operation: str = Form(...), mapping: str = Form("{}"),
                  options: str = Form("{}"), sheet: str = Form(""),
                  dataset: str = Form(""), scope: str = Form("auto"), dataset_version: str = Form("")):
    try:
        frame, _ = await _request_dataset(file, sheet, dataset, scope, operation, dataset_version)
        if frame is None:
            raise ValueError("Selecione a planilha Excel antes de executar.")
        fields = json.loads(mapping)
        settings = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Parâmetros de análise inválidos.")
        settings = apply_curated_options(frame, fields, settings)
        eligibility = preflight(frame, fields, settings)
        gate = eligibility["capabilities"].get(operation)
        if gate is None:
            raise ValueError("Análise desconhecida.")
        if gate["status"] != "available":
            raise ValueError("Análise não habilitada para a configuração atual: " + " ".join(gate["reasons"]))
        result = compute(frame, fields, operation, settings)
        result["metadata"]["data_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()
        result["result_id"] = str(uuid.uuid4())
        result["metadata"]["created_at"] = datetime.now(timezone.utc).isoformat()
        signature = {"data": result["metadata"]["data_sha256"], "source": frame.attrs.get("source"),
                     "mapping": fields, "options": settings, "operation": operation,
                     "method": result["metadata"]["method_version"]}
        result["metadata"]["execution_key"] = hashlib.sha256(json.dumps(signature, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        result["metadata"]["validity"] = "VALIDO"
        result["metadata"]["presentations"] = ["table", "csv", "metadata_json", "print"]
        return result
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
