"""Motor experimental sem LLM. Referência metodológica: IMPLEMENTATION_SPEC.md v1.2.4.
Não substitui a validação integral de todos os contratos e cenários da SPEC.
Nenhum arquivo enviado é armazenado no servidor.
"""
import csv
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

app = FastAPI(title="Agente Diagnóstico Territorial — Teste", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ADT_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
ROLES = ("territory", "period", "category", "count", "population", "latitude", "longitude", "identity")
ALIASES = {
    "territory": ("territorio", "municipio", "cod_municipio", "codigo_municipio", "localidade", "territory"),
    "period": ("periodo", "ano", "competencia", "year", "period"),
    "category": ("categoria", "ocupacao", "cbo", "profissao", "category"),
    "count": ("quantidade", "contagem", "qtd", "n_profissionais", "total_profissionais", "count"),
    "population": ("populacao", "populacao_estimada", "habitantes", "population"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng"),
    "identity": ("identificador_individual", "id_pessoa", "id_profissional", "id_trabalhador", "identity"),
}
ANALYSES = ("density", "counts", "distribution", "comparisons", "temporal", "aggregate", "spatial", "ranking", "rotation", "report")


def canonical_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(name).strip().lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return "_".join(normalized.replace("-", " ").split())


def suggest(columns: list[str]) -> dict[str, str]:
    result = {}
    for role, aliases in ALIASES.items():
        matching = [col for col in columns if canonical_name(col) in aliases]
        if len(matching) == 1:
            result[role] = matching[0]
    return result


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
            frame = pd.read_csv(io.StringIO(text), sep=separator, low_memory=False)
        except Exception as exc:
            raise ValueError("Não foi possível interpretar a estrutura do CSV.") from exc
        return frame, []
    if extension in ("xlsx", "xls"):
        try:
            engine = "openpyxl" if extension == "xlsx" else "xlrd"
            book = pd.ExcelFile(io.BytesIO(contents), engine=engine)
            sheets = book.sheet_names
            if not sheet and len(sheets) > 1:
                return None, sheets
            if sheet and sheet not in sheets:
                raise ValueError("A planilha selecionada não existe neste arquivo.")
            frame = pd.read_excel(book, sheet_name=sheet or sheets[0])
            return frame, sheets
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Não foi possível interpretar este arquivo Excel. Confira se é um .xls ou .xlsx válido, sem proteção por senha.") from exc
    raise ValueError("Formato não suportado. Utilize CSV, XLS ou XLSX.")


def _resolve(df: pd.DataFrame, mapping: dict[str, str], key: str, required: bool = False) -> str | None:
    selected = mapping.get(key)
    if selected and selected not in df.columns:
        raise ValueError("Campo selecionado inexistente: " + selected)
    if required and not selected:
        raise ValueError("Associe a coluna de " + key + " antes de executar esta análise.")
    return selected or None


def _parse_numbers(series: pd.Series, label: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    invalid = series.notna() & values.isna()
    if invalid.any():
        raise ValueError("Há valores não numéricos na coluna de " + label + ". Corrija ou escolha outra coluna.")
    if (values.dropna() < 0).any() and label in ("quantidade", "população"):
        raise ValueError("A coluna de " + label + " contém valores negativos.")
    return values


def _prepared(df: pd.DataFrame, mapping: dict[str, str], options: dict[str, Any], *, need_count: bool = True) -> pd.DataFrame:
    territory = _resolve(df, mapping, "territory", True)
    period = _resolve(df, mapping, "period")
    category = _resolve(df, mapping, "category")
    count = _resolve(df, mapping, "count")
    population = _resolve(df, mapping, "population")
    identity = _resolve(df, mapping, "identity")
    if need_count and not count and not identity:
        raise ValueError("Para calcular quantitativos, associe Quantidade ou um identificador individual autorizado.")
    if not category and not options.get("fts_scope_confirmed"):
        raise ValueError("Sem coluna Categoria, confirme que a base representa a FTS no recorte informado.")
    if not period and not options.get("single_period_confirmed"):
        raise ValueError("Sem coluna Período, confirme que a base representa um único período.")
    tmp = pd.DataFrame({
        "territory": df[territory].astype("string").str.strip(),
        "period": df[period].astype("string").str.strip() if period else "Período declarado",
        "category": df[category].astype("string").str.strip() if category else "FTS declarada",
    })
    if tmp[["territory", "period", "category"]].isna().any().any():
        raise ValueError("Existem valores ausentes nas dimensões necessárias.")
    keys = ["territory", "period", "category"]
    if count:
        tmp["quantity"] = _parse_numbers(df[count], "quantidade")
        if tmp.duplicated(keys).any():
            raise ValueError("Há várias linhas por território/período/categoria. Indique uma base já agregada ou utilize identidade individual para deduplicar. A soma não será presumida.")
        if tmp["quantity"].isna().any():
            raise ValueError("Há quantitativos ausentes; o preenchimento automático não é permitido.")
        data = tmp
    elif identity:
        if df[identity].isna().any():
            raise ValueError("Há identificadores ausentes; não é possível declarar contagem de pessoas únicas completa.")
        tmp["private_identity"] = df[identity].astype("string")
        data = tmp.groupby(keys, dropna=False, as_index=False)["private_identity"].nunique()
        data = data.rename(columns={"private_identity": "quantity"})
    else:
        data = tmp.drop_duplicates(keys)
        data["quantity"] = np.nan
    if population:
        pop = tmp[["territory", "period"]].copy()
        pop["population"] = _parse_numbers(df[population], "população")
        grouped = pop.groupby(["territory", "period"], dropna=False)["population"]
        if (grouped.nunique(dropna=True) > 1).any():
            raise ValueError("Populações conflitantes para o mesmo território e período.")
        pop = pop.drop_duplicates(["territory", "period"])
        data = data.merge(pop, on=["territory", "period"], how="left", validate="many_to_one")
    else:
        data["population"] = np.nan
    if options.get("period_filter"):
        data = data[data["period"] == str(options["period_filter"])]
    if options.get("category_filter"):
        data = data[data["category"] == str(options["category_filter"])]
    if data.empty:
        raise ValueError("Nenhum registro corresponde aos filtros selecionados.")
    data = data.copy()
    data["density"] = np.where(data["population"] > 0, data["quantity"] / data["population"] * 1000, np.nan)
    return data


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
    return clean({"title": title, "description": description, "rows": rows[:150], "total_rows": len(rows), "metrics": metrics or [], "notes": notes or []})


def _records(data: pd.DataFrame) -> list[dict]:
    return data.replace({np.nan: None}).to_dict(orient="records")


def compute(df: pd.DataFrame, mapping: dict[str, str], operation: str, options: dict[str, Any]) -> dict:
    if operation not in ANALYSES:
        raise ValueError("Análise não reconhecida.")
    if operation == "rotation":
        person = _resolve(df, mapping, "identity", True)
        territory = _resolve(df, mapping, "territory", True)
        period = _resolve(df, mapping, "period", True)
        category = _resolve(df, mapping, "category")
        if df[person].isna().any():
            raise ValueError("Identificador incompleto. Não é possível medir a permanência da coorte.")
        tmp = pd.DataFrame({"territory": df[territory].astype(str), "period": df[period].astype(str),
                            "category": df[category].astype(str) if category else "FTS declarada",
                            "person": df[person].astype(str)})
        all_periods = sorted(tmp["period"].unique().tolist())
        if len(all_periods) < 2:
            raise ValueError("Rotatividade exige pelo menos dois períodos.")
        first = str(options.get("initial_period") or all_periods[0])
        last = str(options.get("final_period") or all_periods[-1])
        if first >= last or first not in all_periods or last not in all_periods:
            raise ValueError("Informe períodos inicial e final válidos e em ordem.")
        rows = []
        for (ter, cat), group in tmp.groupby(["territory", "category"]):
            c0 = set(group[group.period == first].person)
            c1 = set(group[group.period == last].person)
            if not c0:
                continue
            ongoing = len(c0 & c1)
            rows.append({"Território": ter, "Categoria": cat, "Coorte inicial": len(c0),
                         "Permanecem": ongoing, "Saíram": len(c0) - ongoing,
                         "Permanência (%)": 100 * ongoing / len(c0),
                         "Rotatividade (%)": 100 * (len(c0) - ongoing) / len(c0)})
        return _result("Rotatividade e permanência", "Coorte inicial de pessoas distintas; identificadores não são retornados.", rows,
                       notes=["É necessária identidade longitudinal autorizada e suficiente nos dois períodos; confirme essa condição antes de interpretar os resultados."])
    if operation == "spatial":
        territory = _resolve(df, mapping, "territory", True)
        lat = _resolve(df, mapping, "latitude", True)
        lon = _resolve(df, mapping, "longitude", True)
        if options.get("crs") != "SIRGAS2000":
            raise ValueError("Indique explicitamente o referencial geodésico SIRGAS2000. Não há referencial presumido.")
        geo = pd.DataFrame({"territory": df[territory].astype(str), "lat": _parse_numbers(df[lat], "latitude"),
                            "lon": _parse_numbers(df[lon], "longitude")})
        if ((geo.lat < -90) | (geo.lat > 90) | (geo.lon < -180) | (geo.lon > 180)).any():
            raise ValueError("Coordenadas fora dos intervalos geográficos válidos.")
        if geo[["lat", "lon"]].isna().any().any():
            raise ValueError("Coordenadas ausentes; não haverá imputação.")
        if geo.groupby("territory")[["lat", "lon"]].nunique().gt(1).any().any():
            raise ValueError("Coordenadas conflitantes para um mesmo território.")
        geo = geo.drop_duplicates("territory")
        refname = options.get("reference_territory")
        match = geo[geo.territory == refname]
        if match.empty:
            raise ValueError("Selecione um território de referência existente na base.")
        reference = match.iloc[0]
        geod = Geod(ellps="GRS80")
        rows = []
        for _, item in geo.iterrows():
            _, _, meters = geod.inv(float(reference.lon), float(reference.lat), float(item.lon), float(item.lat))
            rows.append({"Território": item.territory, "Distância (km)": round(meters / 1000, 3)})
        return _result("Distâncias geodésicas", "Distância direta sobre o elipsoide GRS80 (SIRGAS2000). Não representa tempo nem distância por estrada.",
                       sorted(rows, key=lambda x: x["Distância (km)"]), notes=["Referência: " + str(refname)])
    data = _prepared(df, mapping, options)
    keys = ["territory", "period", "category"]
    cols = {"territory": "Território", "period": "Período", "category": "Categoria",
            "quantity": "Quantidade", "population": "População", "density": "Densidade por 1.000"}
    if operation == "counts":
        rows = _records(data[keys + ["quantity"]].rename(columns=cols))
        return _result("Quantitativos absolutos", "Contagem conforme a unidade de observação e o significado autorizados.", rows,
                       [{"label": "Registros territoriais", "value": len(rows)}])
    if operation in ("density", "report", "comparisons", "ranking", "distribution", "aggregate") and data["population"].isna().all() and operation in ("density", "report", "aggregate"):
        raise ValueError("Associe uma coluna População para calcular densidades.")
    if operation == "aggregate":
        if data["period"].nunique() > 1 or data["category"].nunique() > 1:
            raise ValueError("Selecione um único período e uma única categoria antes da agregação.")
        if data["population"].isna().any() or (data["population"] <= 0).any():
            raise ValueError("Agregação exige denominadores populacionais válidos em todas as unidades.")
        summed_quantity = float(data["quantity"].sum())
        summed_population = float(data.groupby("territory")["population"].first().sum())
        is_unique = bool(options.get("no_overlap_confirmed"))
        label = "Pessoas únicas (premissa expressa)" if is_unique else "Soma dos componentes (não equivale a pessoas únicas)"
        rows = [{"Tipo": label, "Quantidade": summed_quantity, "População": summed_population,
                 "Densidade por 1.000": summed_quantity / summed_population * 1000}]
        notes = ["Densidade agregada = soma dos quantitativos / soma das populações × 1.000.",
                 "A ausência de sobreposição não é inferida. Sem premissa/deduplicação, o resultado é apenas soma dos componentes."]
        return _result("Agregação territorial", "População territorial compartilhada contabilizada uma vez.", rows, notes=notes)
    if operation == "distribution":
        series = data["density"].dropna() if data["density"].notna().any() else data["quantity"].dropna()
        label = "Densidade por 1.000" if data["density"].notna().any() else "Quantidade"
        k = int(options.get("quantile_count", 5))
        if k < 2 or k > 10:
            raise ValueError("O número de classes deve estar entre 2 e 10.")
        if series.empty:
            raise ValueError("Não há valores avaliáveis para distribuição.")
        cuts = [float(np.quantile(series, j / k, method="linear")) for j in range(1, k)]
        classes = np.searchsorted(cuts, series.to_numpy(), side="left") + 1
        rows = [{"Classe": "Q" + str(i), "Unidades": int((classes == i).sum())} for i in range(1, k + 1)]
        return _result("Distribuição por quantis", "Percentis Hyndman–Fan tipo 7; valores iguais permanecem na classe inferior.",
                       rows, notes=["Indicador: " + label, "Pontos de corte: " + ", ".join(str(round(cut, 5)) for cut in cuts)])
    if operation == "temporal":
        pivot = data.pivot_table(index=["territory", "category"], columns="period", values="density", aggfunc="first")
        periods = sorted(data["period"].unique().tolist())
        if len(periods) < 2:
            raise ValueError("Mudança temporal exige ao menos dois períodos.")
        if not all(str(p).replace(".", "", 1).isdigit() for p in periods):
            raise ValueError("Períodos não possuem posição temporal numérica inequívoca.")
        periods = sorted(periods, key=lambda p: float(p))
        rows = []
        for (ter, cat), values in pivot.iterrows():
            a, b = values.get(periods[0]), values.get(periods[-1])
            if pd.isna(a) or pd.isna(b):
                continue
            row = {"Território": ter, "Categoria": cat, "Inicial": float(a), "Final": float(b),
                   "Variação absoluta": float(b - a),
                   "Variação (%)": float((b - a) / a * 100) if a != 0 else None}
            observations = [(float(p), float(values[p])) for p in periods if p in values and pd.notna(values[p])]
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
        return _result("Evolução temporal", "Mudança entre os períodos extremos observados; tendência apenas com pelo menos quatro observações.",
                       rows, notes=["Comparabilidade longitudinal entre períodos deve ser estabelecida pelos metadados da base."])
    if operation in ("comparisons", "ranking"):
        if not data["density"].notna().any():
            raise ValueError("Estas análises requerem densidades avaliáveis.")
        data = data.sort_values(["density", "territory"], ascending=[False, True]).copy()
        data["position"] = range(1, len(data)+1)
        rows = _records(data[["position", "territory", "period", "category", "density"]].rename(columns={
            "position": "Posição", **cols}))
        return _result("Recortes e rankings" if operation == "ranking" else "Comparação territorial",
                       "Ordem relativa descritiva; não constitui julgamento normativo.", rows,
                       notes=["Resultados exibidos por período e categoria. A comparação exige equivalência metodológica das unidades."])
    # density and report
    rows = _records(data[keys + ["quantity", "population", "density"]].rename(columns=cols))
    valid = int(data["density"].notna().sum())
    notes = ["Densidade = quantitativo / população × 1.000.",
             "Valores ausentes e denominadores nulos não são transformados em zero.",
             "Para exportar um relatório, utilize o recurso de impressão/PDF do navegador."]
    return _result("Relatório analítico" if operation == "report" else "Densidade de profissionais",
                   "Profissionais por 1.000 habitantes. Escala de apresentação definida explicitamente.",
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
                    "periods": [], "categories": [], "territories": []}
        if frame.empty:
            raise ValueError("Planilha sem registros.")
        columns = [str(column) for column in frame.columns]
        mapping = suggest(columns)
        def available(role):
            col = mapping.get(role)
            return frame[col].dropna().astype(str).unique().tolist()[:80] if col else []
        return {"requires_sheet": False, "sheets": sheets, "columns": columns, "row_count": len(frame),
                "suggested_mapping": mapping, "periods": available("period"),
                "categories": available("category"), "territories": available("territory")}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), operation: str = Form(...), mapping: str = Form("{}"),
                  options: str = Form("{}"), sheet: str = Form("")):
    try:
        frame, sheets = read_dataset(await _read_upload(file), file.filename or "", sheet)
        if frame is None:
            raise ValueError("Selecione a planilha Excel antes de executar.")
        fields = json.loads(mapping)
        settings = json.loads(options)
        if not isinstance(fields, dict) or not isinstance(settings, dict):
            raise ValueError("Parâmetros de análise inválidos.")
        return compute(frame, fields, operation, settings)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
