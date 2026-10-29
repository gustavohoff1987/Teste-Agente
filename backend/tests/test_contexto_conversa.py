"""Cartão do contexto enviado ao Gemini (contexto_conversa.py; Frentes II e IV), 26/10/2026.

O cartão leva o que a tela mostra — a análise aberta, o resultado em exibição com os valores formatados como na tela, as
ordens do motor, a frase-resumo, as notas, a disponibilidade — e a conversa (a janela recente e a pendência). Nunca leva
identificadores internos, nomes de colunas ou de arquivos, nem o texto da pessoa sem triagem.
"""
import json

import contexto_conversa
import triagem
from test_fidelidade import BODY

GRAFICO = {"familia": "tendencia", "indicador": "densidade", "nivel": "municipios", "competencia": "202406",
           "janela": ["202106", "202206", "202306", "202406"], "vista": "grafico", "mapa_disponivel": True}
PROTECAO = triagem.protecao_da_base({"municipio": ["MANAUS", "TEFE"], "uf": ["AM"], "cod_ibge": ["130260"]},
                                    {"territory": "municipio"}, metadados_extras=["Dados_Municipios_Brasil.csv"])


def montar(**extra):
    argumentos = dict(mensagem="Qual deles tem a maior densidade?", grafico=GRAFICO, resultado=BODY,
                      fonte={"tipo": "brasil"}, protecao=PROTECAO)
    argumentos.update(extra)
    return contexto_conversa.montar(**argumentos)


def test_cartao_leva_a_tela_e_o_resultado_em_exibicao_como_na_tela():
    cartao = montar()["cartao"]
    assert cartao["tela"]["analise_aberta"] == "Análise de Tendência"
    assert cartao["tela"]["janela_da_tendencia"] == ["junho de 2021", "junho de 2022", "junho de 2023", "junho de 2024"]
    resultado = cartao["resultado_em_exibicao"]
    assert resultado["frase_resumo_do_motor"] == BODY["resumo"]["texto"]
    manaus = next(item for item in resultado["itens"] if item["nome"] == "MANAUS (AM)")
    assert manaus["densidade"] == "23,50 por 1.000 habitantes" and manaus["populacao"] == "2.000 habitantes"
    assert manaus["classe_de_tendencia"] == "Aceleração do crescimento"
    assert manaus["valores_observados"][-1] == {"competencia": "junho de 2024", "valor": "23,50"}
    assert manaus["distancia_geografica_direta"] == "1.293,40 km"
    assert resultado["ordens_do_motor"]["densidade"] == {"maior": ["MANAUS (AM)"], "menor": ["TEFE (AM)"]}
    assert "linha reta" in resultado["ressalva_da_distancia"]
    assert any("Juntar" in f for f in cartao["funcionalidades_da_pagina"])


def test_cartao_leva_a_referencia_mais_proxima_da_escolha_dos_territorios_com_os_empates():
    """Com a Escolha dos territórios (27/10/2026), a referência mais próxima de cada item vem em referencia_do_item, com os
    empates; desde 28/10/2026, o cartão e a conferência de fidelidade a trazem (antes, só a referência da análise antiga)."""
    manaus, tefe = (dict(item) for item in BODY["itens"])
    manaus["referencia_do_item"] = {"id": "code:130340", "rotulo": "PARINTINS (AM)", "empate": []}
    tefe["referencia_do_item"] = {"id": "code:130250", "rotulo": "MANACAPURU (AM)", "empate": [
        {"id": "code:130250", "rotulo": "MANACAPURU (AM)"}, {"id": "code:130185", "rotulo": "IRANDUBA (AM)"}]}
    body = {**BODY, "itens": [manaus, tefe]}
    itens = {item["nome"]: item for item in montar(resultado=body)["cartao"]["resultado_em_exibicao"]["itens"]}
    assert itens["MANAUS (AM)"]["referencia_mais_proxima"] == "PARINTINS (AM)"
    assert itens["TEFE (AM)"]["referencias_mais_proximas_empatadas"] == ["MANACAPURU (AM)", "IRANDUBA (AM)"]
    nomes = contexto_conversa.referencias_de_fidelidade(mensagem="Qual o mais próximo?", resultado=body).nomes
    assert {"PARINTINS (AM)", "MANACAPURU (AM)", "IRANDUBA (AM)"} <= set(nomes)


def test_cartao_nao_leva_identificadores_colunas_nem_arquivos():
    texto = json.dumps(montar(fatos="Veja Dados_Municipios_Brasil.csv e a coluna cod_ibge.")["cartao"], ensure_ascii=False)
    for proibido in ("code:130260", "code:130420", "130260", "Dados_Municipios_Brasil.csv", "cod_ibge"):
        assert proibido not in texto, proibido


def test_texto_da_pessoa_no_cartao_passa_pela_triagem_completa():
    contexto = montar(mensagem="E o Severino Quaresma, por que não aparece?",
                      fatos="Não encontrei “Severino Quaresma” no resultado.",
                      memoria={"pendente": {"pergunta": "Qual?", "pedido": "Compare Joaquim Silveira e Manaus",
                                            "alternativas": [{"rotulo": "MANAUS (AM)"}]}},
                      turnos=[{"papel": "usuario", "texto": "Meu CPF é 123.456.789-09"},
                              {"papel": "agente", "texto": "Não guardo documentos."}])
    texto = json.dumps(contexto, default=str, ensure_ascii=False)
    for proibido in ("Severino", "Quaresma", "Joaquim", "Silveira", "123.456.789-09"):
        assert proibido not in texto, proibido
    assert contexto["mensagem"] == "E o [ENTIDADE_PROTEGIDA_1], por que não aparece?"
    assert contexto["cartao"]["resposta_verificada_do_sistema"] == "Não encontrei “[ENTIDADE_PROTEGIDA_1]” no resultado."
    assert contexto["cartao"]["conversa"]["pergunta_pendente_do_agente"]["pedido_original"] == \
        "Compare [ENTIDADE_PROTEGIDA_2] e Manaus"
    assert contexto["conversa_recente"][0] == {"papel": "pessoa", "texto": "Meu CPF é [CPF_1]"}


def test_resposta_verificada_fica_como_esta_e_o_eco_do_nome_continua_protegido():
    # Texto do sistema (catálogo): a fórmula e os códigos não viram marcadores; o nome que a pessoa escreveu, sim, com o
    # mesmo número da mensagem (regressão de 26/10/2026: as letras da fórmula viravam marcadores).
    contexto = montar(mensagem="Como se calcula a densidade? E o Joaquim Silveira?",
                      fatos="Fórmula: D(u, p, c) = Q(u, p, c) / P(u, p′), com DENOMINADOR_ALTERNATIVO (DA-09). Não "
                            "encontrei “Joaquim Silveira” no resultado.")
    assert contexto["mensagem"] == "Como se calcula a densidade? E o [ENTIDADE_PROTEGIDA_1]?"
    assert contexto["cartao"]["resposta_verificada_do_sistema"] == (
        "Fórmula: D(u, p, c) = Q(u, p, c) / P(u, p′), com DENOMINADOR_ALTERNATIVO (DA-09). Não encontrei "
        "“[ENTIDADE_PROTEGIDA_1]” no resultado.")


def test_janela_da_conversa_e_limitada_e_o_resultado_grande_vai_pelos_extremos():
    turnos = [{"papel": "usuario" if i % 2 == 0 else "agente", "texto": "mensagem " + str(i)} for i in range(20)]
    contexto = montar(turnos=turnos)
    assert [t["texto"] for t in contexto["conversa_recente"]] == ["mensagem " + str(i) for i in range(12, 20)]
    grande = {**BODY, "tendencia": None, "referencia": None,
              "itens": [{"id": "code:" + str(i), "tipo": "municipio", "rotulo": "M" + str(i) + " (AM)", "populacao": 1000 + i,
                         "quantidade": i, "densidade": float(i)} for i in range(1, 40)]}
    resultado = montar(resultado=grande)["cartao"]["resultado_em_exibicao"]
    assert "itens" not in resultado and resultado["quantidade_de_itens"] == 39
    assert resultado["extremos_por_atributo"]["densidade"]["maior"][0]["nome"] == "M39 (AM)"


def test_exemplos_do_mapa_de_funcionalidades_nao_viram_numeros_verificados():
    """Correção de 29/10/2026: os exemplos da proximidade no mapa de funcionalidades ("no mínimo 1,5", "mais de 50 mil") iam
    aos textos da conferência de fidelidade, e um 1,5 ou um 50 numa redação passava como valor verificado."""
    assert not {1.5, 50.0, 50000.0} & contexto_conversa.referencias_de_fidelidade(mensagem="qual o mais próximo?").numeros()
    proximidade = next(frase for frase in contexto_conversa.FUNCIONALIDADES if frase.startswith("Pela conversa, a referência"))
    assert "no mínimo um valor" in proximidade and not any(caractere.isdigit() for caractere in proximidade)
