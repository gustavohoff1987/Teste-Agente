"""Formas PT imutáveis; autorização APT-20261016, sem equivalência semântica livre."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import re

import yaml  # já fornecido por uvicorn[standard]

ROOT = Path(__file__).resolve().parents[1]
CATALOG_SHA = "65766f37c27d1f2bc0a32cfeef928cdc59cb1bd968ddcaeedb607139c8827d89"
SPEC_SHA = "5769399e20b2f3492970951aea4d8b499e9b16e7c09a26e01a83522f2e20a11b"
DECISION = "APT-20261016"
ADDENDUM = "\n## Adendo APT-20261016 — autorização delimitada PT\n"


class DocumentationError(ValueError):
    pass


def _extract(locators, lines):
    parts = []
    for locator in locators.split("; "):
        match = re.fullmatch(r"L(\d+):(\d+)-(\d+)", locator)
        if not match:
            raise DocumentationError("Localizador documental inválido.")
        line, start, end = map(int, match.groups())
        if not 0 <= start <= end <= len(lines[line - 1]):
            raise DocumentationError("Intervalo documental inválido.")
        parts.append(lines[line - 1][start:end])
    return "\n".join(parts)


def load_catalog(catalog_bytes, spec_bytes):
    """Fail closed: literal aprovado + extração reproduzível, inclusive em testes."""
    catalog_bytes = catalog_bytes.replace(b"\r\n", b"\n")
    spec = spec_bytes.replace(b"\r\n", b"\n").decode("utf-8")
    original, separator, adendo = spec.partition(ADDENDUM)
    if (sha256(catalog_bytes).hexdigest() != CATALOG_SHA or not separator or
            DECISION not in adendo or sha256(original.encode()).hexdigest() != SPEC_SHA):
        raise DocumentationError("Snapshot documental incompatível com a autorização PT.")
    catalog = yaml.safe_load(catalog_bytes)
    if catalog["versao_spec_compativel"] != "1.2.4":
        raise DocumentationError("Versão documental incompatível.")
    lines = original.splitlines()
    entries = catalog["entradas"]
    registry = {}
    for line in lines[3213:]:
        columns = [part.strip() for part in line.strip("|").split("|")]
        if len(columns) != 6 or not columns[3].startswith("L"):
            continue
        source, path, kind, locators, conditions, dependencies = columns
        key = "DOC:" + source + ("." + path if path != "—" else "")
        if key in registry or key not in entries:
            raise DocumentationError("Inventário documental divergente.")
        entry = entries[key]
        if (entry["fonte_normativa"] != source or entry["caminho"] != (None if path == "—" else path) or
                entry["pt"]["base"]["texto_template"] != _extract(locators, lines)):
            raise DocumentationError("Forma PT não corresponde à fonte normativa.")
        registry[key] = {**entry, "tipo": kind, "dependencias": dependencies,
                         "condicoes": _extract(locators if conditions == "=texto" else conditions, lines)
                         if conditions != "—" else ""}
    if set(registry) != set(entries) or len(registry) != 703:
        raise DocumentationError("Catálogo incompleto.")
    return registry


@lru_cache(maxsize=1)
def registry():
    return load_catalog((ROOT / "Docs/CFG_DOC_CATALOG.yaml").read_bytes(),
                        (ROOT / "IMPLEMENTATION_SPEC.md").read_bytes())


def materialize(id_doc, *, language="PT", form="base", evidence=None):
    """Sem interpolação livre. Variantes só entram com predicado explicitamente implementado."""
    if language != "PT":
        raise DocumentationError("Apresentação EN não autorizada nesta integração.")
    entry = registry().get(id_doc)
    if entry is None or form not in entry["pt"]:
        raise DocumentationError("Forma documental ausente.")
    record = entry["pt"][form]
    if form != "base":
        allowed = ((id_doc, form) == ("DOC:CFG-DOC.comportamento", "insuficiencia") and
                   evidence == "DOCUMENTACAO_INSUFICIENTE") or (
                   (id_doc, form) == ("DOC:TPL-11", "mensagem") and evidence == "DISTANCIA_VERIFICADA")
        if not allowed or record.get("variaveis_tipadas"):
            raise DocumentationError("Condições da forma não demonstradas.")
    return {"text": record["texto_template"], "id_doc": id_doc, "language": language,
            "form": form, "version": record["versao"], "source_version": "SPEC-1.2.4",
            "authorization": DECISION, "usage": "DESCRICAO_GERAL" if form == "base" else evidence}


TOPICS = {
    "density": ("DOC:CAP-IND-02.metodo", "DOC:CAP-IND-02.representacao", "DOC:CAP-IND-02.precondicoes",
                "DOC:CAP-IND-02.avaliabilidade", "DOC:CAP-IND-02.proibicoes"),
    "spatial": ("DOC:CAP-ESP-01.metodo",),
    "aggregation": ("DOC:CAP-AGR-01.entradas", "DOC:CAP-AGR-01.metodo", "DOC:CAP-AGR-01.precondicoes",
                    "DOC:CAP-AGR-01.avaliabilidade"),
    # Só formas cujas frases coincidem com o que o motor faz (conferência de 20/10/2026): pontos de corte e classes
    # da distribuição e a referência mais próxima. Tendência, mudança, comparação, contagem, ranking, critérios e
    # rotatividade não entram: suas formas descrevem etapas que o protótipo não implementa.
    "distribution": ("DOC:CAP-DIS-02.metodo",),
    "nearest": ("DOC:CAP-ESP-02.metodo", "DOC:CAP-ESP-02.saida", "DOC:CAP-ESP-02.avaliabilidade"),
}


def explanation(topic, *, simple=False):
    keys = TOPICS.get(topic)
    if keys is None:
        return None
    # Apresentação progressiva reorganiza aspectos, sem editar o literal ou retirar condições.
    if simple and topic == "density":
        keys = (keys[1], keys[0], *keys[2:])
    forms = [materialize(key) for key in keys]
    return {"reply": "\n\n".join(form["text"] for form in forms), "documentation": forms}


def verify_documentation(text, forms):
    expected = [materialize(f["id_doc"], language=f["language"], form=f["form"],
                            evidence=f["usage"]) for f in forms]
    return forms == expected and text == "\n\n".join(f["text"] for f in expected)
