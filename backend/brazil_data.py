"""Base lógica Brasil. Fontes de granularidades distintas nunca são somadas ou unidas.

O armazenamento é privado ao servidor e configurável na hospedagem. Somente
identificadores de catálogo são aceitos da API, nunca caminhos de arquivos.
"""
import hashlib
import json
import os
from pathlib import Path


FILES = {"national": "Dados_Brasil.xlsx", "municipal": "Dados_Municipios_Brasil.csv"}
DEFAULT_SCOPES = {op: ("national" if op in ("counts", "temporal", "report") else "municipal")
                  for op in ("density", "counts", "distribution", "comparisons", "temporal",
                             "aggregate", "spatial", "ranking", "rotation", "report")}
# A referência mais próxima só existe no recorte municipal, o único com coordenadas. Fica fora de
# default_scopes porque a origem compõe a chave de execução das análises já existentes.
ENGINE_SCOPES = {**DEFAULT_SCOPES, "nearest": "municipal"}
DEFAULT_DIR = Path(__file__).resolve().parents[1] / ".local" / "datasets" / "brasil"


def data_directory():
    return Path(os.environ.get("ADT_BRASIL_DATA_DIR") or DEFAULT_DIR)


def load_brazil(scope="auto", operation="", version=""):
    if scope not in ("auto", "national", "municipal") or (operation and operation not in ENGINE_SCOPES):
        raise ValueError("Recorte ou análise da base Brasil inválido.")
    selected = ENGINE_SCOPES.get(operation, "municipal") if scope == "auto" else scope
    folder = data_directory()
    try:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema_version"] != 1:
            raise ValueError()
        contents = {}
        hashes = {}
        for key, filename in FILES.items():
            path = folder / filename
            if path.stat().st_size > 30 * 1024 * 1024:
                raise ValueError()
            contents[key] = path.read_bytes()
            hashes[key] = hashlib.sha256(contents[key]).hexdigest()
            if hashes[key] != manifest["sha256"][key]:
                raise ValueError()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("A base Brasil está indisponível ou sua integridade não foi validada. Solicite ao administrador a instalação da base.") from exc
    current_version = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    if version and version != current_version:
        raise ValueError("A base Brasil foi atualizada. Carregue-a novamente e revise as confirmações antes de analisar.")
    return contents[selected], FILES[selected], {
        "dataset": "brazil", "label": "Dados do Brasil", "scope": selected,
        "version": current_version, "default_scopes": DEFAULT_SCOPES,
        "available_scopes": list(FILES),
    }
