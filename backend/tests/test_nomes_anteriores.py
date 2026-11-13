"""A busca pelo nome anterior de um município continua achando o município (decisão do responsável de 13/11/2026, na pausa 1
do comando V23: 19 municípios da base Brasil passaram ao nome oficial do IBGE).

- a tabela dos nomes anteriores (`nomes_anteriores.py`): 19 códigos IBGE de 6 dígitos, no formato dos nomes da base;
- o nome anterior igual ao atual não vira apelido (uma base que ainda traz o nome anterior);
- os dois caminhos da conversa (`conversa_grafico._Catalogo` e `exploration.search_names`) acham o município pelo nome
  anterior e mostram o nome atual; um nome anterior igual ao nome atual de outro município continua homônimo, como antes.

Os casos com a base versionada (o catálogo com `former_names`) ficam em `test_levels_real_data.py`.
"""
import re

import conversa_grafico
import exploration
import nomes_anteriores


def test_tabela_dos_19_nomes_anteriores_no_formato_da_base():
    tabela = nomes_anteriores.ANTERIORES
    assert len(tabela) == 19
    assert all(re.fullmatch(r"\d{6}", codigo) for codigo in tabela)
    nomes = [nome for anteriores in tabela.values() for nome in anteriores]
    assert len(nomes) == 19 and all(re.fullmatch(r"[A-Z][A-Z '\-]*[A-Z]", nome) for nome in nomes), nomes
    assert tabela["330380"] == ("PARATI",) and tabela["353080"] == ("MOJI MIRIM",) and tabela["240130"] == ("AUGUSTO SEVERO",)
    assert tabela["251365"] == ("SANTAREM",)   # JOCA CLAUDINO (PB)


def test_nomes_anteriores_do_codigo_e_do_rotulo():
    assert nomes_anteriores.do_codigo("330380", "PARATY") == ["PARATI"]
    assert nomes_anteriores.do_codigo("3303807", "PARATY") == ["PARATI"]      # o código de 7 dígitos também serve
    assert nomes_anteriores.do_codigo(" 330380 ") == ["PARATI"]
    # Uma base que ainda traz o nome anterior não ganha um apelido igual ao nome.
    assert nomes_anteriores.do_codigo("330380", "PARATI") == [] and nomes_anteriores.do_codigo("330380", " parati ") == []
    assert nomes_anteriores.do_codigo("130260", "MANAUS") == [] and nomes_anteriores.do_codigo("", "") == []
    assert nomes_anteriores.do_rotulo("code:330380", "PARATY (RJ)") == ["PARATI"]
    assert nomes_anteriores.do_rotulo("code:251365", "SANTAREM (PB)") == []
    assert nomes_anteriores.do_rotulo("uf:33", "Rio de Janeiro (RJ)") == [] and nomes_anteriores.do_rotulo("c1", "Conjunto A") == []


def _item(codigo, nome, uf, estado, anteriores=()):
    item = {"id": "code:" + codigo, "name": nome, "code": codigo, "label": nome + " [" + codigo + "]", "parents": [],
            "selection_reason": "", "state": uf, "state_name": estado, "state_code": codigo[:2]}
    if anteriores:
        item["former_names"] = list(anteriores)
    return item


CATALOGO = [_item("330380", "PARATY", "RJ", "Rio de Janeiro", ["PARATI"]), _item("150680", "SANTAREM", "PA", "Pará"),
            _item("251365", "JOCA CLAUDINO", "PB", "Paraíba", ["SANTAREM"]), _item("130260", "MANAUS", "AM", "Amazonas")]


def test_os_nomes_de_busca_de_uma_unidade_trazem_os_anteriores():
    assert exploration.search_names(CATALOGO[0]) == ["paraty", "parati"]
    assert exploration.search_names(CATALOGO[3]) == ["manaus"]
    assert exploration.search_names({"name": "São Luiz do Anauá", "former_names": ["SÃO LUIZ"]}) == ["sao luiz do anaua", "sao luiz"]


def test_a_conversa_acha_o_municipio_pelo_nome_anterior_e_mostra_o_atual():
    catalogo = conversa_grafico._Catalogo(CATALOGO, True)
    assert catalogo.nomes["parati"] == catalogo.nomes["paraty"] == ["code:330380"]
    assert "parati" in catalogo.expressoes and "paraty" in catalogo.expressoes
    assert catalogo.rotulo("code:330380") == "PARATY (RJ)"
    # O nome anterior igual ao nome atual de outro município continua homônimo, como era antes da troca dos nomes: "Santarém"
    # traz o do Pará e o da Paraíba (hoje JOCA CLAUDINO), e a conversa pergunta qual.
    assert catalogo.nomes["santarem"] == ["code:150680", "code:251365"] and catalogo.nomes["joca claudino"] == ["code:251365"]
    assert catalogo.rotulo("code:251365") == "JOCA CLAUDINO (PB)"
    # Sem nomes anteriores, nada muda.
    simples = conversa_grafico._Catalogo([CATALOGO[1], CATALOGO[3]], True)
    assert simples.nomes == {"santarem": ["code:150680"], "manaus": ["code:130260"]}
