"""Nomes anteriores de municípios da base Brasil.

Em 13/11/2026, a pedido do responsável pelo produto (pausa 1 do comando V23), 19 municípios passaram, na fonte municipal, ao
nome oficial atual do IBGE (a lista, com o código, o nome anterior e o atual, está em `Docs/DADOS_BRASIL_VALIDACAO.md`). A busca
pelo nome anterior continua achando o município: as buscas das telas e a conversa procuram também nestes nomes, e o que aparece
é sempre o nome atual.

Vale só para a base Brasil: a chave é o código IBGE de 6 dígitos. Os nomes ficam aqui, numa tabela à parte, e nunca como linhas
da base (um código com dois nomes é recusado pelo catálogo). Nada daqui vai ao provedor de IA.
"""
from __future__ import annotations

ANTERIORES: dict[str, tuple[str, ...]] = {
    "140060": ("SAO LUIZ",),                   # SAO LUIZ DO ANAUA (RR)
    "170825": ("FORTALEZA DO TABOCAO",),       # TABOCAO (TO)
    "172049": ("SAO VALERIO DA NATIVIDADE",),  # SAO VALERIO (TO)
    "230630": ("ITAPAGE",),                    # ITAPAJE (CE)
    "240020": ("ACU",),                        # ASSU (RN)
    "240120": ("ARES",),                       # AREZ (RN)
    "240130": ("AUGUSTO SEVERO",),             # CAMPO GRANDE (RN)
    "241030": ("PRESIDENTE JUSCELINO",),       # SERRA CAIADA (RN)
    "251365": ("SANTAREM",),                   # JOCA CLAUDINO (PB)
    "251540": ("SERIDO",),                     # SAO VICENTE DO SERIDO (PB)
    "260160": ("BELEM DE SAO FRANCISCO",),     # BELEM DO SAO FRANCISCO (PE)
    "260690": ("IGUARACI",),                   # IGUARACY (PE)
    "260850": ("LAGOA DO ITAENGA",),           # LAGOA DE ITAENGA (PE)
    "292850": ("SANTA TERESINHA",),            # SANTA TEREZINHA (BA)
    "310890": ("BRASOPOLIS",),                 # BRAZOPOLIS (MG)
    "330380": ("PARATI",),                     # PARATY (RJ)
    "330590": ("TRAJANO DE MORAIS",),          # TRAJANO DE MORAES (RJ)
    "351610": ("FLORINIA",),                   # FLORINEA (SP)
    "353080": ("MOJI MIRIM",),                 # MOGI MIRIM (SP)
}


def do_codigo(codigo, atual: str = "") -> list[str]:
    """Os nomes anteriores do município de código IBGE `codigo` (6 ou 7 dígitos), sem o que for igual ao nome atual: uma base
    que ainda traz o nome anterior não ganha um apelido repetido."""
    mesmo = str(atual).strip().upper()
    return [nome for nome in ANTERIORES.get(str(codigo).strip()[:6], ()) if nome != mesmo]


def do_rotulo(identificador, rotulo: str = "") -> list[str]:
    """O mesmo, para uma linha das ferramentas: o id "code:330380" e o rótulo "PARATY (RJ)"."""
    identificador = str(identificador)
    if not identificador.startswith("code:"):
        return []
    return do_codigo(identificador[5:], str(rotulo).rsplit(" (", 1)[0])
