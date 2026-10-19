"""Base lógica Brasil: fonte nacional (contagem do país) e fonte municipal, lidas e verificadas juntas.

As duas fontes nunca são somadas nem unidas. O total do Brasil vem sempre da fonte nacional; a densidade
do Brasil combina, por regra governada (BR-POP-JUNHO-1, territorial_levels.py), essa contagem com a
população municipal de junho do mesmo ano. Estados são somas dos municípios pelo prefixo do código IBGE.

Origem padrão: os dois arquivos versionados na raiz do repositório, conferidos a cada
requisição contra o manifesto governado `dados/brasil/manifesto.json` (tamanho e SHA-256).
Não há cópia intermediária nem fallback para outra pasta: `.local/` não é lida.

`ADT_BRASIL_DATA_DIR` aponta, de forma explícita, para uma instalação externa (cópia com o
manifesto do instalador). Ela só é aceita com a versão governada ou quando
`ADT_BRASIL_DATA_VERSION` fixa exatamente a versão instalada; versão divergente é recusada.
Somente identificadores de catálogo são aceitos da API, nunca caminhos de arquivos.

Uso administrativo (raiz do repositório):
    python backend/brazil_data.py diagnostico          # origem, versão e integridade
    python backend/brazil_data.py versao <pasta>       # versão declarada por uma instalação externa
    python backend/brazil_data.py manifesto [--gravar] # identidade dos arquivos versionados
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path


FILES = {"national": "Dados_Brasil.xlsx", "municipal": "Dados_Municipios_Brasil.csv"}
DEFAULT_SCOPES = {op: ("national" if op in ("counts", "temporal", "report") else "municipal")
                  for op in ("density", "counts", "distribution", "comparisons", "temporal",
                             "aggregate", "spatial", "ranking", "rotation", "report")}
# A referência mais próxima e os critérios combinados só existem no recorte municipal, o único com
# coordenadas. Ficam fora de default_scopes porque a origem compõe a chave de execução das análises
# já existentes.
ENGINE_SCOPES = {**DEFAULT_SCOPES, "nearest": "municipal", "criteria": "municipal"}
REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNED_MANIFEST = Path("dados") / "brasil" / "manifesto.json"  # relativo à raiz do repositório
DEFAULT_DIR = REPO_ROOT / ".local" / "datasets" / "brasil"  # destino padrão do instalador (cópia opcional)
MAX_BYTES = 30 * 1024 * 1024
UNAVAILABLE = "A base Brasil está indisponível ou sua integridade não foi validada"
SHA256 = re.compile(r"[0-9a-f]{64}")


def version_of(hashes):
    """Identidade da versão: resumo canônico dos SHA-256 das duas fontes (inalterada desde o Bloco 1)."""
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def _hashes(entries, label):
    if not isinstance(entries, dict) or any(not isinstance(entries.get(k), str) or not SHA256.fullmatch(entries[k])
                                             for k in FILES):
        raise ValueError(label + " sem SHA-256 válido para as duas fontes")
    return {k: entries[k] for k in FILES}


def governed_manifest(root=None):
    """Manifesto versionado: caminho, tamanho e SHA-256 de cada fonte e a versão correspondente."""
    path = Path(root or REPO_ROOT) / GOVERNED_MANIFEST
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("manifesto governado ausente ou ilegível (" + GOVERNED_MANIFEST.as_posix() + ")") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("arquivos"), dict):
        raise ValueError("manifesto governado inválido (esquema)")
    files = data["arquivos"]
    sizes = {}
    for key, filename in FILES.items():
        entry = files.get(key)
        if not isinstance(entry, dict) or entry.get("caminho") != filename or not isinstance(entry.get("bytes"), int):
            raise ValueError("manifesto governado inválido (" + key + ")")
        sizes[key] = entry["bytes"]
    hashes = _hashes({k: files[k].get("sha256") for k in FILES}, "manifesto governado")
    if data.get("versao") != version_of(hashes):
        raise ValueError("manifesto governado inconsistente (versão não corresponde aos SHA-256)")
    return {"versao": data["versao"], "sha256": hashes, "bytes": sizes, "caminho": path}


def catalog_version(folder):
    """Versão declarada pelo manifesto de uma instalação externa (não confere os arquivos)."""
    try:
        data = json.loads((Path(folder) / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("instalação externa sem manifesto legível") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("manifesto da instalação externa inválido")
    return version_of(_hashes(data.get("sha256"), "manifesto da instalação externa"))


def _resolve(root=None):
    """Origem efetiva e identidade esperada; ValueError com o motivo quando a origem é recusada."""
    root = Path(root or REPO_ROOT)
    external = os.environ.get("ADT_BRASIL_DATA_DIR", "").strip()
    if not external:
        manifest = governed_manifest(root)
        return {"modo": "repositorio", "pasta": root, "manifesto": str(manifest["caminho"]),
                "sha256": manifest["sha256"], "bytes": manifest["bytes"], "versao": manifest["versao"],
                "versao_governada": manifest["versao"], "versao_fixada": None}
    folder = Path(external)
    data = json.loads((folder / "manifest.json").read_text(encoding="utf-8")) if (folder / "manifest.json").is_file() else None
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("a pasta externa (ADT_BRASIL_DATA_DIR) não contém manifesto válido")
    hashes = _hashes(data.get("sha256"), "manifesto da pasta externa")
    version = version_of(hashes)
    try:
        governed = governed_manifest(root)["versao"]
    except ValueError:
        governed = None
    pinned = os.environ.get("ADT_BRASIL_DATA_VERSION", "").strip() or None
    if pinned and pinned != version:
        raise ValueError("ADT_BRASIL_DATA_VERSION fixa " + pinned[:12] + ", mas a pasta externa contém " + version[:12])
    if version != governed and not pinned:
        raise ValueError("a pasta externa (ADT_BRASIL_DATA_DIR) contém a versão " + version[:12] + ", diferente da versão "
                         "governada " + (governed[:12] if governed else "(manifesto governado indisponível)") +
                         "; atualize a instalação ou fixe explicitamente ADT_BRASIL_DATA_VERSION com a versão instalada")
    return {"modo": "externo", "pasta": folder, "manifesto": str(folder / "manifest.json"), "sha256": hashes,
            "bytes": None, "versao": version, "versao_governada": governed, "versao_fixada": pinned}


def _read_verified(state):
    contents = {}
    for key, filename in FILES.items():
        path = state["pasta"] / filename
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise ValueError("o arquivo " + filename + " não foi encontrado na origem") from exc
        if size > MAX_BYTES or (state["bytes"] and size != state["bytes"][key]):
            raise ValueError("o arquivo " + filename + " difere do manifesto (tamanho)")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != state["sha256"][key]:
            raise ValueError("o arquivo " + filename + " difere do manifesto (SHA-256)")
        contents[key] = raw
    return contents


def data_directory():
    """Pasta efetiva das fontes: a raiz do repositório ou a pasta externa explicitamente configurada."""
    external = os.environ.get("ADT_BRASIL_DATA_DIR", "").strip()
    return Path(external) if external else REPO_ROOT


def _integrity(state):
    return {"modo": state["modo"], "origem": {k: str(state["pasta"] / f) for k, f in FILES.items()},
            "manifesto": state["manifesto"], "sha256": state["sha256"], "versao": state["versao"],
            "versao_governada": state["versao_governada"], "versao_fixada": state["versao_fixada"],
            "integridade": "verificada"}


def selected_scope(scope="auto", operation=""):
    """Recorte efetivo de um pedido: o informado ou, em "auto", o padrão da análise."""
    if scope not in ("auto", "national", "municipal") or (operation and operation not in ENGINE_SCOPES):
        raise ValueError("Recorte ou análise da base Brasil inválido.")
    return ENGINE_SCOPES.get(operation, "municipal") if scope == "auto" else scope


def load_brazil_sources(version=""):
    """As duas fontes numa única leitura verificada (mesmo estado, mesma versão).

    Devolve ({escopo: (conteúdo, nome do arquivo, source)}, integridade); cada source mantém o próprio
    escopo, como em load_brazil."""
    try:
        state = _resolve()
        contents = _read_verified(state)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) else "falha de leitura"
        raise ValueError(UNAVAILABLE + ": " + reason + ".") from exc
    current_version = state["versao"]
    if version and version != current_version:
        raise ValueError("A base Brasil foi atualizada. Carregue-a novamente e revise as escolhas antes de analisar.")
    sources = {key: (contents[key], FILES[key], {
        "dataset": "brazil", "label": "Dados do Brasil", "scope": key,
        "version": current_version, "default_scopes": DEFAULT_SCOPES,
        "available_scopes": list(FILES),
    }) for key in FILES}
    return sources, _integrity(state)


def load_brazil(scope="auto", operation="", version="", details=False):
    selected = selected_scope(scope, operation)
    sources, integrity = load_brazil_sources(version)
    raw, filename, source = sources[selected]
    if details:
        return raw, filename, source, integrity
    return raw, filename, source


def diagnostics():
    """Origem física, versão e integridade, sem conteúdo dos arquivos; nunca levanta exceção."""
    external = os.environ.get("ADT_BRASIL_DATA_DIR", "").strip()
    try:
        state = _resolve()
        _read_verified(state)
        return _integrity(state)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"modo": "externo" if external else "repositorio",
                "origem": {k: str(data_directory() / f) for k, f in FILES.items()},
                "integridade": "recusada", "motivo": str(exc) or "falha de leitura"}


def manifest_from_repository(root=None):
    """Identidade atual dos arquivos versionados (para revisar e, explicitamente, gravar)."""
    root = Path(root or REPO_ROOT)
    entries = {}
    for key, filename in FILES.items():
        raw = (root / filename).read_bytes()
        entries[key] = {"caminho": filename, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return {"schema_version": 1,
            "finalidade": "Identidade governada da base Brasil versionada na raiz do repositório; o backend só usa "
                          "fontes cujos tamanhos e SHA-256 correspondem a este manifesto.",
            "arquivos": entries, "versao": version_of({k: v["sha256"] for k, v in entries.items()})}


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "diagnostico"
    if command == "diagnostico":
        print(json.dumps(diagnostics(), ensure_ascii=False, indent=2))
    elif command == "versao" and len(sys.argv) == 3:
        print(catalog_version(sys.argv[2]))
    elif command == "manifesto":
        manifest = manifest_from_repository()
        if "--gravar" in sys.argv:
            target = REPO_ROOT / GOVERNED_MANIFEST
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("Manifesto governado gravado em " + GOVERNED_MANIFEST.as_posix() + "; revise e registre no Git.")
        else:
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        raise SystemExit(__doc__)
