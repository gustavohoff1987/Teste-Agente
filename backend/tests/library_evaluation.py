"""Avaliação da Biblioteca de Inteligência Conversacional em trajetórias inéditas (fora da biblioteca).

Mede a pertinência dos exemplos que o integrador entregaria ao modelo, sem chamar o provedor: para cada turno
inédito, a biblioteca escolhe os exemplos como em produção, e compara-se o rótulo esperado do turno (a decisão
principal do intérprete) com o dos exemplos. Linhas de base: nenhum exemplo (como antes da biblioteca), exemplos
fixos (os mesmos para toda mensagem) e exemplos aleatórios. A votação dos exemplos é um classificador por
vizinhança, usado só como indicador de pertinência; não mede a qualidade do Gemini.
"""
from collections import Counter, defaultdict
import random
import time

import conversation_library as library


def label(interpretation: dict) -> str:
    """Decisão principal do intérprete para o turno."""
    if len(interpretation["candidates"]) >= 2:
        return "ambiguidade"
    if interpretation["operation"] != "none":
        return "operacao:" + interpretation["operation"]
    if interpretation["dialogue"] not in ("none", "acknowledge"):
        return "dialogo:" + interpretation["dialogue"]
    if interpretation["topic"] != "none":
        return "topico:" + interpretation["topic"]
    return "intencao:" + interpretation["intent"]


def _vote(items: list[dict]) -> str | None:
    weights = Counter()
    for rank, item in enumerate(items):
        weights[label(item["turn"]["interpretacao"])] += 1 / (rank + 1)
    return weights.most_common(1)[0][0] if weights else None


def evaluate(collection: library.Library, records: list[dict], k: int = 5, seed: int = 20261020) -> dict:
    known = {library.fold(item["turn"]["usuario"]) for item in collection.turns}
    every = [item for record in records for item in library.turns(record)]
    # Mensagem longa idêntica a uma da biblioteca (comandos canônicos) não mede generalização: fica fora da conta.
    turns = [item for item in every
             if len(item["turn"]["usuario"]) <= 25 or library.fold(item["turn"]["usuario"]) not in known]
    rng = random.Random(seed)
    pool = {"base": [item for item in collection.turns if library.mode(item["state"]) == "base"],
            "sem_base": [item for item in collection.turns if library.mode(item["state"]) == "sem_base"]}
    # Exemplos fixos: um turno de cada um dos rótulos mais frequentes da biblioteca, iguais para toda mensagem.
    fixed = {}
    for key, items in pool.items():
        frequent = [name for name, _ in Counter(label(i["turn"]["interpretacao"]) for i in items).most_common(k)]
        fixed[key] = [next(i for i in items if label(i["turn"]["interpretacao"]) == name) for name in frequent]
    totals = defaultdict(Counter)
    by_group = defaultdict(Counter)
    times = []
    for item in turns:
        expected = label(item["turn"]["interpretacao"])
        start = time.perf_counter()
        chosen = collection.select(item["turn"]["usuario"], item["history"], item["state"], k)
        times.append(time.perf_counter() - start)
        key = library.mode(item["state"])
        strategies = {"biblioteca": chosen, "fixos": fixed[key],
                      "aleatorios": rng.sample(pool[key], min(k, len(pool[key])))}
        for name, items in strategies.items():
            labels = [label(i["turn"]["interpretacao"]) for i in items]
            totals[name]["turnos"] += 1
            totals[name]["com_exemplos"] += bool(items)
            totals[name]["acerto_em_k"] += expected in labels
            totals[name]["acerto_no_primeiro"] += bool(labels) and labels[0] == expected
            totals[name]["precisao"] += (labels.count(expected) / len(labels)) if labels else 0
            totals[name]["voto"] += _vote(items) == expected
        for group in ("dimensao:" + item["trajectory"]["dimensao"], "idioma:" + item["trajectory"]["idioma"]):
            labels = [label(i["turn"]["interpretacao"]) for i in chosen]
            by_group[group]["turnos"] += 1
            by_group[group]["acerto_em_k"] += expected in labels
            by_group[group]["voto"] += _vote(chosen) == expected
    times.sort()
    rates = {name: {metric: counts[metric] / counts["turnos"] for metric in counts if metric != "turnos"}
             for name, counts in totals.items()}
    return {"turnos": len(turns), "repetidos": len(every) - len(turns), "trajetorias": len(records), "k": k,
            "estrategias": rates,
            "grupos": {group: {"turnos": c["turnos"], "acerto_em_k": c["acerto_em_k"] / c["turnos"],
                               "voto": c["voto"] / c["turnos"]} for group, c in sorted(by_group.items())},
            "latencia_ms": {"media": 1000 * sum(times) / max(1, len(times)),
                            "p95": 1000 * times[int(0.95 * (len(times) - 1))] if times else 0.0}}


def table(report: dict) -> str:
    lines = [f"Turnos inéditos: {report['turnos']} ({report['trajetorias']} trajetórias; {report['repetidos']} com "
             f"mensagem idêntica à da biblioteca ficaram fora), k = {report['k']}", "",
             "| Exemplos entregues ao modelo | Com exemplos | Rótulo esperado entre os k | No primeiro | Precisão | Voto |",
             "|---|---|---|---|---|---|",
             "| Nenhum (antes da biblioteca) | 0% | 0% | 0% | 0% | 0% |"]
    names = {"biblioteca": "Biblioteca (recuperação por mensagem e contexto)", "fixos": "Fixos (os mesmos sempre)",
             "aleatorios": "Aleatórios"}
    for key, name in names.items():
        rate = report["estrategias"][key]
        lines.append(f"| {name} | {rate['com_exemplos']:.0%} | {rate['acerto_em_k']:.0%} | "
                     f"{rate['acerto_no_primeiro']:.0%} | {rate['precisao']:.0%} | {rate['voto']:.0%} |")
    lines += ["", "| Grupo | Turnos | Rótulo entre os k | Voto |", "|---|---|---|---|"]
    lines += [f"| {group} | {values['turnos']} | {values['acerto_em_k']:.0%} | {values['voto']:.0%} |"
              for group, values in report["grupos"].items()]
    latency = report["latencia_ms"]
    lines += ["", f"Seleção dos exemplos: média {latency['media']:.1f} ms, p95 {latency['p95']:.1f} ms por mensagem."]
    return "\n".join(lines)
