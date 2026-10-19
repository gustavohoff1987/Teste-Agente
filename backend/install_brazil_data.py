"""Instala cópias validadas em armazenamento privado; nunca altera os originais.

Uso: python backend/install_brazil_data.py [--source <pasta>] [--destination <pasta nova>]
Sem --source, copia os arquivos versionados na raiz do repositório. O uso local não exige
instalação: o backend lê diretamente a raiz (ver brazil_data.py). A cópia serve a ambientes
que configuram ADT_BRASIL_DATA_DIR explicitamente; por padrão só é aceita a versão governada
(dados/brasil/manifesto.json). --permitir-versao-nao-governada instala outra versão (por exemplo,
catálogos sintéticos de teste), que o backend só usa com ADT_BRASIL_DATA_VERSION fixada.
"""
import argparse
import hashlib
import json
from pathlib import Path

from brazil_data import DEFAULT_DIR, FILES, REPO_ROOT, governed_manifest, version_of
from main import read_dataset


def install(source, destination, governed=True):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise ValueError("Escolha uma pasta de destino nova. A instalação não sobrescreve bases existentes.")
    payloads, hashes = {}, {}
    for scope, filename in FILES.items():
        raw = (source / filename).read_bytes()
        frame, _ = read_dataset(raw, filename)
        required = {"periodo_ano", "periodo_mes", "categoria_profissional"} | (
            {"pais", "contagem"} if scope == "national" else {"uf", "contagem"} if scope == "state" else
            {"municipio", "cod_ibge", "quantidade", "população_estimada", "latitude", "longitude"})
        if frame is None or frame.empty or not required.issubset(frame.columns):
            raise ValueError("As fontes não correspondem à estrutura esperada da base Brasil.")
        payloads[filename] = raw
        hashes[scope] = hashlib.sha256(raw).hexdigest()
    version = version_of(hashes)
    if governed and version != governed_manifest()["versao"]:
        raise ValueError("As fontes não correspondem à versão governada do repositório; nenhuma cópia foi feita.")
    destination.mkdir(parents=True, exist_ok=False)
    for filename, raw in payloads.items():
        (destination / filename).write_bytes(raw)
        if (destination / filename).read_bytes() != raw or (source / filename).read_bytes() != raw:
            raise ValueError("Falha ao verificar a preservação da fonte ou a cópia instalada.")
    # Publicar o manifesto por último: instalações incompletas não são carregadas.
    (destination / "manifest.json").write_text(json.dumps({"schema_version": 1, "sha256": hashes, "versao": version,
                                                           "versao_governada": bool(governed)}, indent=2),
                                               encoding="utf-8")
    return hashes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO_ROOT)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--permitir-versao-nao-governada", action="store_true")
    args = parser.parse_args()
    install(args.source, args.destination, governed=not args.permitir_versao_nao_governada)
    print("Base Brasil instalada e verificada. Originais preservados.")
