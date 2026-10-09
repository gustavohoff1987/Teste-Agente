"""Motor experimental sem LLM. Referência metodológica: IMPLEMENTATION_SPEC.md v1.2.4.
Não substitui a validação integral de todos os contratos e cenários da SPEC.
Nenhum arquivo enviado é armazenado no servidor.
"""
import csv
import hashlib
import io
import json
import os
import unicodedata
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pyproj import Geod
from semantic_bridge import candidates, normalize_headers, preflight, ROLES, EXACT, OPERATIONS
from data_contract import validate_operation, rotation_data, period_positions, scoped, text_values

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
        header = next(csv.reader(io.StringIO(text), delimiter=separator))
        normalize_headers(pd.DataFrame(columns=header))
        try:
            # Preserva códigos e zeros iniciais; conversão numérica pertence ao contrato.
            frame = pd.read_csv(io.StringIO(text), sep=separator, dtype=str, keep_default_na=False)
            frame = frame.replace(r"^\s*$", pd.NA, regex=True)
        except Exception as exc:
            raise ValueError("Não foi possível interpretar a estrutura do CSV.") from exc
        return normalize_headers(frame), []
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
            frame = raw.iloc[1:].reset_index(drop=True)
            frame.columns = [str(x).strip() if pd.notna(x) else f"Unnamed: {i}" for i, x in enumerate(raw.iloc[0])]
            return normalize_headers(frame), sheets
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
    result = _compute(df, mapping, operation, options)
    result["metadata"] = {"method_version": "deterministic-0.2", "operation": operation,
                          "mapping": mapping, "options": options, "input_rows": len(df)}
    unit = "pessoas distintas" if not mapping.get("count") else options.get("custom_count_unit") if options.get("count_unit") == "outro" else options.get("count_unit", "unidade declarada")
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
        geod = Geod(ellps="GRS80" if options["crs"] == "SIRGAS2000" else "WGS84")
        rows = []
        for _, item in geo.iterrows():
            _, _, meters = geod.inv(float(reference.lon), float(reference.lat), float(item.lon), float(item.lat))
            rows.append({"Território": item.territory, "Distância (km)": round(meters / 1000, 3)})
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
        unit = "pessoas" if not mapping.get("count") else options.get("count_unit", "unidades declaradas")
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
        label = "Densidade por 1.000 habitantes" if indicator == "density" else "Quantidade de profissionais"
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
                             "Unidades": int((classes == i).sum()), "Indicador": label})
            for pos, (_, record) in enumerate(group.iterrows()):
                i = int(classes[pos])
                detail_rows.append({
                    "Território": record["territory"], "Período": period, "Categoria": category,
                    "Quintil": f"{i}º quintil" if k == 5 else f"{i}ª faixa de {k}",
                    label: float(record[metric]),
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
        # Sem denominador declarado a série continua válida como quantitativo;
        # nunca fabricar densidades nem presumir população.
        metric = "density" if data["density"].notna().any() and options.get("population_denominator_confirmed") else "quantity"
        pivot = data.pivot_table(index=["territory", "category"], columns="period", values=metric, aggfunc="first")
        positions = period_positions(data.period.unique(), options.get("period_convention", "auto"))
        periods = sorted(positions, key=positions.get)
        if len(periods) < 2:
            raise ValueError("Mudança temporal exige ao menos dois períodos.")
        rows = []
        for (ter, cat), values in pivot.iterrows():
            a, b = values.get(periods[0]), values.get(periods[-1])
            if pd.isna(a) or pd.isna(b):
                rows.append({"Território": ter, "Categoria": cat, "Período inicial": periods[0], "Período final": periods[-1],
                             "Inicial": None, "Final": None, "Variação absoluta": None, "Variação (%)": None,
                             "Tendência": "Não avaliável: observação ausente em um dos extremos"})
                continue
            row = {"Território": ter, "Categoria": cat, "Período inicial": periods[0], "Período final": periods[-1], "Inicial": float(a), "Final": float(b),
                   "Variação absoluta": float(b - a),
                   "Variação (%)": float((b - a) / a * 100) if a != 0 else None}
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
        return _result("Evolução temporal", "Variação de " + ("densidade por 1.000 habitantes" if metric == "density" else "quantitativos") + " entre períodos; tendência somente com quatro ou mais observações.",
                       rows, notes=["Comparabilidade temporal e identidade longitudinal foram declaradas pelo usuário para esta execução."])
    if operation in ("comparisons", "ranking"):
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
    if operation == "report" and (not options.get("population_denominator_confirmed") or not mapping.get("territory")):
        rows = _records(data[keys + ["quantity"]].rename(columns=cols))
        return _result("Relatório de quantitativos", "Quantitativos da força de trabalho na base analisada.", rows,
                       notes=["Sem denominador populacional confirmado: nenhuma densidade foi calculada."])
    rows = _records(data[keys + ["quantity", "population", "density"]].rename(columns=cols))
    valid = int(data["density"].notna().sum())
    notes = ["Densidade = quantitativo / população × 1.000.",
             "Valores ausentes e denominadores nulos não são transformados em zero.",
             "Para exportar um relatório, utilize o recurso de impressão/PDF do navegador."]
    return _result("Relatório analítico" if operation == "report" else "Densidade de profissionais",
                   (options.get("custom_count_unit") if options.get("count_unit") == "outro" else options.get("count_unit") or "Pessoas") + " por 1.000 habitantes.",
                   rows, [{"label": "Unidades avaliáveis", "value": valid},
                          {"label": "Não avaliáveis", "value": int(len(data)-valid)}], notes)


async def _read_upload(file: UploadFile) -> bytes:
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima do limite experimental de 30 MB.")
    return contents


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm": False, "version": "0.1.0"}


@app.post("/api/inspect")
async def inspect(file: UploadFile = File(...), sheet: str = Form("")):
    try:
        frame, sheets = read_dataset(await _read_upload(file), file.filename or "", sheet)
        if frame is None:
            return {"requires_sheet": True, "sheets": sheets, "columns": [], "row_count": 0, "suggested_mapping": {},
                    "column_profiles": [], "periods": [], "categories": [], "territories": [], "preflight": None,
                    "suggested_category_constant": ""}
        if frame.empty:
            raise ValueError("Planilha sem registros.")
        mapping, profiles = candidates(frame)
        def available(role):
            col = mapping.get(role)
            return frame[col].dropna().astype(str).unique().tolist()[:80] if col else []
        from semantic_bridge import category_from_count_header
        return {"requires_sheet": False, "sheets": sheets, "columns": frame.columns.tolist(), "row_count": len(frame),
                "suggested_mapping": mapping, "column_profiles": profiles,
                "suggested_category_constant": category_from_count_header(mapping.get("count", "")),
                "preflight": preflight(frame, mapping),
                "periods": available("period"), "categories": available("category"), "territories": available("territory")}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/preflight")
async def api_preflight(file: UploadFile = File(...), mapping: str = Form("{}"),
                        options: str = Form("{}"), sheet: str = Form("")):
    try:
        frame, _ = read_dataset(await _read_upload(file), file.filename or "", sheet)
        if frame is None:
            raise ValueError("Selecione uma planilha para concluir o exame.")
        fields = json.loads(mapping)
        settings = json.loads(options)
        return preflight(frame, fields, settings)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), operation: str = Form(...), mapping: str = Form("{}"),
                  options: str = Form("{}"), sheet: str = Form("")):
    try:
        frame, _ = read_dataset(await _read_upload(file), file.filename or "", sheet)
        if frame is None:
            raise ValueError("Selecione a planilha Excel antes de executar.")
        fields = json.loads(mapping)
        settings = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Parâmetros de análise inválidos.")
        eligibility = preflight(frame, fields, settings)
        gate = eligibility["capabilities"].get(operation)
        if gate is None:
            raise ValueError("Análise desconhecida.")
        if gate["status"] != "available":
            raise ValueError("Análise não habilitada para a configuração atual: " + " ".join(gate["reasons"]))
        result = compute(frame, fields, operation, settings)
        result["metadata"]["data_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()
        return result
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
