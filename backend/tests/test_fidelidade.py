"""Conferência de fidelidade do texto do Gemini (fidelidade.py) e fichas de método (definicoes.py), 26/10/2026.

Frente V (Adendo PAR-20261026 da SPEC): o Gemini explica com as palavras dele, e a conferência — independente do modelo,
nunca a concordância dele — olha a função de cada frase: números e nomes do contexto, ordens e classes do motor, ressalvas
obrigatórias, afirmações proibidas fora de negação e os elementos essenciais de cada conceito explicado.
"""
import re
from pathlib import Path

import pytest

import contexto_conversa
import definicoes
import fidelidade

# Resultado sintético no formato da resposta do motor (painel): dois municípios, densidade, tendência e distância.
BODY = {
    "nivel": "municipios", "indicador": "densidade", "competencia": "202406", "competencia_inicial": None,
    "categoria": "MEDICINA", "resumo": {"texto": "Em junho de 2024, o gráfico tem 2 municípios. A densidade vai de 10 a "
                                                 "23,50 por 1.000 habitantes."},
    "notas": ["Densidade = quantitativo / população × 1.000 (por 1.000 habitantes)."], "limitacoes": [],
    "referencia": {"rotulo": "BELEM (PA)"}, "disponibilidade": {},
    "tendencia": {"janela": {"inicio": "202106", "fim": "202406"},
                  "classes": [{"codigo": "CRESCIMENTO", "rotulo": "Crescimento"},
                              {"codigo": "CRESCIMENTO_ACELERADO", "rotulo": "Aceleração do crescimento"}],
                  "contagens": {"CRESCIMENTO": 1, "CRESCIMENTO_ACELERADO": 1}},
    "itens": [
        {"id": "code:130260", "tipo": "municipio", "rotulo": "MANAUS (AM)", "populacao": 2000, "quantidade": 47,
         "densidade": 23.5, "distancia_km": 1293.4, "variacao_percentual": {}, "referencia": False,
         "tendencia": {"avaliavel": True, "classe": "CRESCIMENTO_ACELERADO", "rotulo": "Aceleração do crescimento",
                       "observacoes": [{"competencia": "202106", "valor": 15}, {"competencia": "202206", "valor": 17},
                                       {"competencia": "202306", "valor": 20}, {"competencia": "202406", "valor": 23.5}]}},
        {"id": "code:130420", "tipo": "municipio", "rotulo": "TEFE (AM)", "populacao": 600, "quantidade": 6,
         "densidade": 10, "distancia_km": 1950.2, "variacao_percentual": {}, "referencia": False,
         "tendencia": {"avaliavel": True, "classe": "CRESCIMENTO", "rotulo": "Crescimento",
                       "observacoes": [{"competencia": "202106", "valor": 8.33}, {"competencia": "202206", "valor": 8.33},
                                       {"competencia": "202306", "valor": 10}, {"competencia": "202406", "valor": 10}]}},
    ],
}


def refs(mensagem="Explique o resultado", fichas=(), pedidas=(), acao=False, marcadores=None, body=BODY, fatos=None):
    return contexto_conversa.referencias_de_fidelidade(
        mensagem=mensagem, resultado=body, fichas=[definicoes.FICHAS[f] for f in fichas],
        pedidas=[definicoes.FICHAS[f] for f in pedidas], acao=acao, marcadores=marcadores, fatos=fatos)


def violacoes(texto, **kwargs):
    return fidelidade.conferir(texto, refs(**kwargs))


# ------------------------------------------------------------------------------------------------- fatos dos dados
def test_texto_fiel_aos_valores_e_a_ordem_do_motor_passa():
    assert violacoes("Em junho de 2024, MANAUS (AM) tem a maior densidade, 23,50 por 1.000 habitantes, e TEFE (AM) a "
                     "menor, 10 por 1.000 habitantes. São 2 municípios no gráfico.") == []
    assert violacoes("Tefé tem 600 habitantes e 6 profissionais; Manaus, 2.000 habitantes e 47 profissionais.") == []


@pytest.mark.parametrize("texto,regra", [
    ("MANAUS (AM) tem cerca de 24 por 1.000 habitantes.", "V-01"),
    ("A média dos dois é 16,75 por 1.000 habitantes.", "V-01"),
    ("Recife tem densidade parecida com a de Manaus.", "V-02"),
    ("TEFE (AM) tem a maior densidade.", "V-07"),
    ("A densidade de TEFE (AM) é maior que a de MANAUS (AM).", "V-07"),
    ("TEFE (AM) está em aceleração do crescimento.", "V-05"),
])
def test_numero_nome_ordem_e_classe_fora_do_motor_sao_recusados(texto, regra):
    assert any(regra in v for v in violacoes(texto)), violacoes(texto)


@pytest.mark.parametrize("texto,regra", [
    ("MANAUS (AM) tem médicos suficientes.", "V-03"),
    ("A densidade de TEFE (AM) é inadequada para a população.", "V-03"),
    ("A alta em MANAUS (AM) foi causada pela abertura de hospitais.", "V-04"),
    ("O crescimento se deve a novos concursos.", "V-04"),
    ("A queda pode estar relacionada à migração de profissionais.", "V-04"),
    ("TEFE (AM) fica a horas de barco de Belém, o que dificulta o acesso.", "V-06"),
    ("Manaus vai continuar crescendo nos próximos anos.", "projeção"),
    ("Os municípios são muito heterogêneos.", "V-13"),
    ("Há uma correlação entre densidade e população.", "método que o sistema não tem"),
])
def test_juizo_causa_acesso_previsao_e_metodo_inexistente_afirmados_sao_recusados(texto, regra):
    assert any(regra in v for v in violacoes(texto)), violacoes(texto)


@pytest.mark.parametrize("texto", [
    "O resultado não diz se há médicos suficientes em MANAUS (AM).",
    "Os dados não mostram a causa da diferença entre os dois.",
    "A distância é em linha reta: não é tempo de deslocamento nem acesso real.",
    "Para entender melhor, veja os valores na tabela dos Detalhes.",
    "A análise não faz previsão: descreve só a janela de junho de 2021 a junho de 2024.",
    "Passo 1: veja a densidade de cada município. Passo 2: compare com a referência de contexto.",
    "A análise inclui MANAUS (AM) e TEFE (AM); vou mostrar como ler o gráfico.",
    "Para responder melhor, preciso saber qual indicador você quer comparar.",
])
def test_a_ressalva_negativa_e_a_construcao_benigna_passam(texto):
    assert violacoes(texto) == []


@pytest.mark.parametrize("texto", [
    "Nesse ritmo, MANAUS (AM) passa logo de 25 por 1.000 habitantes.",
    "A densidade de MANAUS (AM) deve continuar subindo.",
    "No próximo ano, TEFE (AM) tende a se manter estável.",
    "MANAUS (AM) chegará a 23,50 de novo.",
])
def test_previsao_em_outras_palavras_e_recusada(texto):
    # Medição de 26/10/2026 com a base versionada: "Nesse ritmo, ... vai passar de ... no próximo ano" passava.
    assert any("previsão" in v for v in violacoes(texto)), texto


@pytest.mark.parametrize("texto,regra", [
    # Sondagem de 26/10/2026 com a base versionada: estas formulações passavam pela conferência.
    ("MANAUS (AM) está numa situação boa.", "juízo"),
    ("É um resultado positivo para MANAUS (AM).", "juízo"),
    ("MANAUS (AM) se saiu bem no período.", "juízo"),
    ("MANAUS (AM) tem médicos de sobra.", "juízo"),
    ("MANAUS (AM) está bem servida de médicos.", "juízo"),
    ("Faltam médicos em TEFE (AM).", "juízo"),
    ("A alta reflete investimentos na saúde de MANAUS (AM).", "causa"),
    ("A tendência é continuar subindo em MANAUS (AM).", "previsão"),
    ("Espera-se que a densidade de MANAUS (AM) suba mais.", "previsão"),
    ("Os moradores de MANAUS (AM) encontram médico com facilidade.", "acesso"),
    ("MANAUS (AM) se destaca no estado.", "destaque"),
    ("MANAUS (AM) tem mais que o dobro da densidade de TEFE (AM).", "relação calculada"),
    ("A densidade de MANAUS (AM) é 2 vezes maior que a de TEFE (AM).", "relação calculada"),
])
def test_juizo_causa_previsao_acesso_destaque_e_relacao_em_outras_palavras_sao_recusados(texto, regra):
    assert any(regra in v for v in violacoes(texto)), (texto, violacoes(texto))


def test_formulas_cordiais_e_a_mencao_ao_tema_da_causa_passam():
    assert violacoes("Excelente pergunta! MANAUS (AM) tem a maior densidade: 23,50 por 1.000 habitantes.") == []
    assert violacoes("Quanto à causa, a análise não identifica por que os valores mudaram.") == []


@pytest.mark.parametrize("texto", [
    # Instruções de uso e sinais de valores não são previsão nem juízo.
    "Para comparar, você deve voltar à Seleção de Territórios.",
    "Os botões vão continuar funcionando enquanto a conversa estiver indisponível.",
    "O gráfico vai voltar ao estado anterior se você pedir para desfazer.",
    "A variação foi positiva para MANAUS (AM).",
    "O sinal negativo indicaria queda.",
])
def test_instrucoes_de_uso_e_sinal_de_valor_passam(texto):
    assert violacoes(texto) == [], violacoes(texto)


def test_lidera_e_ordem_conferida_com_o_motor_nao_destaque():
    assert violacoes("MANAUS (AM) lidera em densidade, com 23,50 por 1.000 habitantes.") == []
    assert any("V-07" in v for v in violacoes("TEFE (AM) lidera em densidade."))


def test_avaliacao_sem_valor_e_juizo():
    assert any("juízo" in v for v in violacoes("Isso é positivo para MANAUS (AM)."))


def test_frase_copiada_da_resposta_verificada_nao_e_afirmacao_nova_mas_a_da_pessoa_e():
    fatos = ("A distância apresentada é geográfica direta. Não representa distância viária, tempo de deslocamento ou "
             "acessibilidade real.")
    assert violacoes("Em outras palavras: " + fatos, fatos=fatos, fichas=("distancia",)) == []
    # O que a pessoa escreveu não é material verificado: repetido pelo modelo, é conferido como qualquer frase.
    assert any("causa" in v for v in violacoes("A queda se deve à pandemia.", mensagem="A queda se deve à pandemia?"))


def test_ficha_pedida_exige_os_essenciais_so_quando_a_resposta_verificada_explica():
    pedida = ("classe:CRESCIMENTO_ACELERADO",)
    so_aponta = "O significado de cada classe está em “Entenda esta análise”, na aba Tendência."
    rascunho = "MANAUS (AM) está na classe Aceleração do crescimento; o significado está em “Entenda esta análise”."
    assert violacoes(rascunho, fatos=so_aponta, pedidas=pedida, fichas=pedida) == []
    explica = definicoes.FICHAS["classe:CRESCIMENTO_ACELERADO"].texto
    assert any("essencial" in v for v in violacoes(rascunho, fatos=explica, pedidas=pedida, fichas=pedida))


def test_previsao_negada_passa():
    assert violacoes("Não dá para dizer se MANAUS (AM) vai continuar subindo: a análise não faz previsão.") == []


def test_numero_do_exemplo_documentado_nao_vira_valor_de_territorio():
    # O "16" de "10, 11, 13 e 16" (exemplo da ficha da classe) ilustra a regra; com unidade, ao lado de um território,
    # seria um valor que o motor não deu.
    fichas = ("classe:CRESCIMENTO_ACELERADO",)
    assert any("exemplo documentado" in v for v in violacoes("MANAUS (AM) tem 16 por 1.000 habitantes.", fichas=fichas))
    assert violacoes("Um exemplo da regra: 10, 11, 13 e 16, com altas de 1, 2 e 3.", fichas=fichas) == []
    assert violacoes("TEFE (AM) tem 10 por 1.000 habitantes.", fichas=fichas) == []
    # A escala não é valor, e a ficha copiada inteira continua valendo.
    densidade = definicoes.FICHAS["densidade"].texto
    assert violacoes(densidade, body=None, fichas=("densidade",), pedidas=("densidade",)) == []


def test_distancia_sem_a_ressalva_de_linha_reta_e_recusada():
    assert any("TPL-11" in v for v in violacoes("MANAUS (AM) fica a 1.293,40 km da referência."))
    assert violacoes("MANAUS (AM) fica a 1.293,40 km da referência, em linha reta.") == []


def test_acao_que_a_resposta_nao_fez_e_recusada():
    assert any("ação" in v for v in violacoes("Abri a comparação de MANAUS (AM) e TEFE (AM)."))
    assert violacoes("Abri a comparação de MANAUS (AM) e TEFE (AM).", acao=True) == []


def test_marcadores_da_triagem_voltam_ao_original_e_marcador_inventado_e_recusado():
    r = refs(mensagem="E a Maria Quitéria?", marcadores={"[ENTIDADE_PROTEGIDA_1]": "Maria Quitéria"})
    texto = "Não tenho dados sobre [ENTIDADE_PROTEGIDA_1]; o resultado traz só territórios."
    assert fidelidade.conferir(texto, r) == []
    assert fidelidade.texto_para_exibir(texto, r).startswith("Não tenho dados sobre Maria Quitéria;")
    assert any("marcadores" in v for v in fidelidade.conferir("E [ENTIDADE_PROTEGIDA_7]?", r))


def test_texto_vazio_longo_ou_com_marcacao_e_recusado():
    assert violacoes("") == ["texto vazio"]
    assert any("longo" in v for v in violacoes("a " * 1500))
    assert any("links" in v for v in violacoes("Veja [aqui](https://exemplo.org)."))
    assert any("links" in v for v in violacoes("Veja [aqui](exemplo)."))
    # Marcador de proteção seguido de parênteses não é link.
    r = refs(mensagem="E a Maria Quitéria(AM)?", marcadores={"[ENTIDADE_PROTEGIDA_1]": "Maria Quitéria"})
    assert fidelidade.conferir("Não tenho dados sobre [ENTIDADE_PROTEGIDA_1](AM) no resultado.", r) == []


# ------------------------------------------------------------------------------------------------- paráfrase de método
@pytest.mark.parametrize("ficha,texto", [
    ("densidade", "É quantos profissionais existem para cada 1.000 moradores: divide-se o número de médicos pela "
                  "população do lugar e multiplica-se por 1.000. Ela não diz, sozinha, se o número é suficiente."),
    ("distancia", "É a distância em linha reta entre os dois pontos, medida em km sobre o elipsoide; não é o caminho por "
                  "estrada nem o tempo de viagem."),
    ("grupos", "Os quintis ordenam os valores e usam pontos de corte (percentis) para formar cinco grupos; como valores "
               "iguais ficam juntos, os grupos podem ter tamanhos diferentes."),
    ("agregacao", "O conjunto soma as contagens das partes, e a mesma pessoa pode entrar mais de uma vez (dupla contagem)."),
    ("variacao", "A variação compara o valor final com o inicial, em percentual; ela não explica o porquê da mudança."),
    ("classe:CRESCIMENTO_ACELERADO", "Quer dizer que o indicador subiu em todos os períodos e cada alta foi igual ou maior "
                                     "que a anterior: o crescimento ganhou ritmo."),
    ("classe:SEM_CLASSIFICACAO", "Sem classificação é quando o indicador mudou de direção (subiu e caiu) ou ficou igual: "
                                 "é um resultado do método, não falta de informação."),
])
def test_parafrase_fiel_do_conceito_passa(ficha, texto):
    assert violacoes(texto, mensagem="o que é isso?", fichas=[ficha], pedidas=[ficha]) == []


@pytest.mark.parametrize("ficha,texto", [
    # Distância geodésica não é distância rodoviária.
    ("distancia", "A distância é o caminho mais curto pela estrada entre as duas cidades."),
    # Densidade não é evidência de suficiência assistencial.
    ("densidade", "A densidade divide os médicos pela população e mostra se o atendimento é suficiente."),
    ("densidade", "A densidade é o total de médicos do município."),  # sem população nem a escala
    # Variação temporal não vira explicação causal.
    ("variacao", "A variação compara o final com o inicial, em percentual, e mostra o efeito do programa de contratação."),
    # Classe de tendência não ganha critério diferente do motor.
    ("classe:CRESCIMENTO_ACELERADO", "Aceleração do crescimento quer dizer que o indicador cresceu mais de 10% ao ano."),
    ("classe:CRESCIMENTO_ACELERADO", "Quer dizer que o indicador subiu bastante no último período."),
    ("classe:SEM_CLASSIFICACAO", "Sem classificação quer dizer que faltam dados para classificar."),
    # Grupos por posição não têm tamanho igual por definição.
    ("grupos", "Os quintis usam pontos de corte e dividem os municípios em cinco grupos com o mesmo número de municípios."),
    # Conjunto agregado não é contagem de pessoas únicas.
    ("agregacao", "O conjunto soma as contagens e mostra o total de pessoas únicas."),
])
def test_parafrase_que_muda_o_metodo_e_recusada(ficha, texto):
    assert violacoes(texto, mensagem="o que é isso?", fichas=[ficha], pedidas=[ficha]), texto


def test_definicao_espontanea_de_conceito_tambem_e_conferida():
    # A pessoa não pediu o conceito, mas o texto o define: os elementos essenciais e as proibições valem do mesmo jeito.
    texto = "A densidade é o número de médicos da cidade, e MANAUS (AM) tem 47 médicos."
    assert any("Densidade" in v for v in violacoes(texto, fichas=["densidade"]))
    fato = "A maior densidade é a de MANAUS (AM), 23,50 por 1.000 habitantes."
    assert violacoes(fato, fichas=["densidade"]) == []  # frase de dado, não definição


def test_as_fichas_nao_criam_criterio_e_as_classes_sao_as_da_tela():
    # As descrições das classes são as de "Entenda esta análise" (painelModel.DESCRICAO_DAS_CLASSES), sem divergência.
    ts = (Path(__file__).resolve().parents[2] / "frontend/src/painelModel.ts").read_text(encoding="utf-8")
    bloco = ts.split("export const DESCRICAO_DAS_CLASSES")[1].split("};")[0]
    tela = {codigo: "".join(re.findall(r'"([^"]*)"', corpo)) for codigo, corpo in
            re.findall(r"(\w+): ((?:\"[^\"]*\"\s*\+?\s*)+)", bloco)}
    assert tela == definicoes.DESCRICAO_DAS_CLASSES
    for codigo, descricao in definicoes.DESCRICAO_DAS_CLASSES.items():
        ficha = definicoes.FICHAS["classe:" + codigo]
        assert ficha.texto.endswith(descricao)
        # A própria formulação autorizada passa na conferência da ficha (as regras não se contradizem).
        assert violacoes(ficha.texto, mensagem="o que é?", fichas=["classe:" + codigo], pedidas=["classe:" + codigo]) == []
    for chave in ("densidade", "distancia", "referencia", "grupos", "agregacao", "variacao", "tendencia", "velocidade",
                  "comparacao", "regua", "rotatividade", "quantidade"):
        ficha = definicoes.FICHAS[chave]
        assert violacoes(ficha.texto, mensagem="o que é?", fichas=[chave], pedidas=[chave]) == [], chave


def test_a_concordancia_do_modelo_nao_basta():
    # Um texto que se declara fiel continua sendo conferido pelas regras, não pela própria declaração.
    texto = "Conferi e esta explicação é fiel ao método: a densidade mostra onde faltam médicos."
    assert violacoes(texto, mensagem="o que é densidade?", fichas=["densidade"], pedidas=["densidade"])
