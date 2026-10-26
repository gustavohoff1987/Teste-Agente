"""Triagem determinística antes do provedor de IA (triagem.py; RQ-DAD-20, RQ-DAD-37 a RQ-DAD-39), 26/10/2026.

Frente I da missão de 26/10/2026: a preparação preserva negação, verbos, operadores, referências temporais, comparações,
referências geográficas permitidas, a sintaxe e o que a continuidade precisa; protege identificadores, valores protegidos e
metadados; e não mascara por maiúscula, coincidência lexical ou palavra que também é nome de coluna.
"""
import pytest

import triagem
from triagem import Protecao, preparar, preparar_varios, protecao_da_base

BASE = protecao_da_base({"municipio": ["MANAUS", "TEFE", "RIO DE JANEIRO", "PORTO ALEGRE", "BELEM"],
                         "uf": ["AM", "RJ", "RS", "PA"], "categoria_profissional": ["MEDICINA"],
                         "cod_ibge": ["130260"], "nome_profissional": ["Joaquina Prates"]},
                        {"territory": "municipio", "category": "categoria_profissional", "identity": "nome_profissional"},
                        nomes_extras=["Amazonas", "Rio Grande do Sul", "Pará"], metadados_extras=["Dados_saude.xlsx", "Plan1"])


@pytest.mark.parametrize("frase", [
    # Exemplos do diagnóstico.
    "Não era isso que eu queria.", "Município.", "Caiu em 2023?",
    # Formulações adversariais novas: negação, verbos, operadores, períodos, comparações, dêixis e continuidade.
    "Não, o estado.", "Nem um nem outro, quero os dois.", "Quero só 2024.", "Compare 2019-2023 com 2024.",
    "Qual deles apresenta densidade maior?", "E em relação à população?", "Troca o primeiro pelo segundo.",
    "Volta para a comparação anterior.", "Agora explique de maneira mais técnica.", "Explica-me a tendência.",
    "Esse crescimento significa que o município melhorou?", "Qual foi a causa dessa queda?",
    "Quero saber como esses dois municípios se diferenciam.", "Coloca um do lado do outro para eu entender.",
    "Mostre só os que estão abaixo de 2 por mil.", "Não entendi a aceleração, explica de novo?",
    "Compare o norte e o sul.", "E se considerarmos todos?", "Claramente isso caiu entre junho e dezembro.",
])
def test_linguagem_funcional_fica_intacta(frase):
    assert preparar(frase, BASE) == frase


@pytest.mark.parametrize("frase", [
    "Compare Rio de Janeiro com Porto Alegre.", "Quero ver Manaus e Tefé em junho de 2024.",
    "Como está o Amazonas?", "E Belém, no Pará?", "Mostre o Rio Grande do Sul", "Densidade de MEDICINA em Tefé",
    "Quero o município de Fonte Boa", "E a cidade de São Gabriel da Cachoeira?",
])
def test_referencias_geograficas_da_base_e_marcadas_ficam(frase):
    assert preparar(frase, BASE) == frase


@pytest.mark.parametrize("frase,esperado", [
    ("Meu CPF é 123.456.789-00 e o telefone (92) 99999-1234", "Meu CPF é [CPF_1] e o telefone [TELEFONE_1]"),
    ("cpf: 12345678900", "cpf: [CPF_1]"),
    ("escreva para joao@example.com.br", "escreva para [EMAIL_1]"),
    ("ligue +55 92 99999-1234", "ligue [TELEFONE_1]"),
    ("telefone 92 99999 1234", "telefone [TELEFONE_1]"),
    ("CNS: 898001234567890", "CNS: [IDENTIFICADOR_1]"),
    ("o número 89800123456789 é de quem?", "o número [IDENTIFICADOR_1] é de quem?"),
    ("nome: joão da silva", "nome: [IDENTIFICADOR_1]"),
    ("veja https://exemplo.org/x", "veja [IDENTIFICADOR_1]"),
    ("Abra o arquivo Dados_saude.xlsx", "Abra o arquivo [ARQUIVO_1]"),
    ("o campo cod_ibge está certo?", "o campo [CAMPO_1] está certo?"),
    ("e a Joaquina Prates, trabalha onde?", "e a [IDENTIFICADOR_1], trabalha onde?"),
    ("O Dr. Severino Quaresma atende em Manaus?", "O Dr. [ENTIDADE_PROTEGIDA_1] atende em Manaus?"),
    ("A professora Ana Lúcia Prates trabalha em Tefé?", "A professora [ENTIDADE_PROTEGIDA_1] trabalha em Tefé?"),
    ("Dra Maria J. Silva, né?", "Dra [ENTIDADE_PROTEGIDA_1]. [ENTIDADE_PROTEGIDA_2], né?"),
])
def test_identificadores_valores_protegidos_e_metadados_saem(frase, esperado):
    assert preparar(frase, BASE) == esperado


def test_formula_titulo_e_interjeicao_ficam():
    # Letra isolada é símbolo de fórmula ou inicial, não nome; título e "né" são linguagem funcional (26/10/2026).
    for frase in ("O que é D(u, p, c)?", "Explique o P da fórmula", "Tá bom, né?", "Apresentação dos dados, por favor.",
                  "Decisão final: quero a densidade.", "Senhor, explique o formato."):
        assert preparar(frase, BASE) == frase


def test_o_que_ja_virou_marcador_continua_protegido_no_texto_do_sistema():
    # A resposta verificada (texto do sistema, sem a etapa nominal) que repete o nome escrito pela pessoa não o revela:
    # mesmo marcador, inclusive em outra caixa; a fórmula e os códigos do método ficam como estão.
    numeracao = triagem.Numeracao()
    assert preparar("Por que o Joaquim Silveira não aparece?", BASE, numeracao) == \
        "Por que o [ENTIDADE_PROTEGIDA_1] não aparece?"
    resposta = ("Não encontrei “Joaquim Silveira” (JOAQUIM SILVEIRA) entre os territórios. Fórmula: D(u, p, c) = "
                "Q(u, p, c) / P(u, p′); limitação DENOMINADOR_ALTERNATIVO (DA-09).")
    assert preparar(resposta, BASE, numeracao, nominal=False) == (
        "Não encontrei “[ENTIDADE_PROTEGIDA_1]” ([ENTIDADE_PROTEGIDA_1]) entre os territórios. Fórmula: D(u, p, c) = "
        "Q(u, p, c) / P(u, p′); limitação DENOMINADOR_ALTERNATIVO (DA-09).")


def test_numero_isolado_nao_vira_telefone_e_quantidade_fica():
    for frase in ("A população de 212583750 habitantes", "Tefé tem 600 habitantes e 6 médicos", "Mais de 1.000 médicos",
                  "Período 2015-2024", "Código 130260"):
        assert preparar(frase, BASE) == frase


def test_mesmo_valor_mesmo_marcador_no_envio_e_outro_valor_outro_numero():
    textos = ["A Maria Quitéria disse que viu Joaquina Prates", "E a Maria Quitéria? E o Bento Gonçalvez?",
              "Escreva para a@b.com e c@d.com e a@b.com"]
    preparados = preparar_varios(textos, BASE)
    assert preparados == ["A [ENTIDADE_PROTEGIDA_1] disse que viu [IDENTIFICADOR_1]",
                          "E a [ENTIDADE_PROTEGIDA_1]? E o [ENTIDADE_PROTEGIDA_2]?",
                          "Escreva para [EMAIL_1] e [EMAIL_2] e [EMAIL_1]"]


def test_maiuscula_nao_mascara_palavra_conhecida_nem_coincidencia_com_coluna():
    # "Municipio" e "uf" são nomes de coluna e também linguagem comum: ficam. Valores de outra coluna que coincidem com
    # palavras comuns ("se", "sul") também ficam.
    protecao = protecao_da_base({"Municipio": ["Vila"], "uf": ["X"], "observacao": ["se", "sul", "norte"]},
                                {"territory": "Municipio"})
    assert preparar("O Municipio do sul se destacou? E a uf?", protecao) == "O Municipio do sul se destacou? E a uf?"
    assert preparar("NÃO ERA ISSO. EXPLIQUE DE NOVO.", Protecao()) == "NÃO ERA ISSO. EXPLIQUE DE NOVO."


def test_original_nunca_muda_e_marcadores_voltam_ao_original_so_no_backend():
    numeracao = triagem.Numeracao()
    original = "A Maria Quitéria pediu o CPF 123.456.789-00"
    preparado = preparar(original, BASE, numeracao)
    assert original == "A Maria Quitéria pediu o CPF 123.456.789-00"
    assert preparado == "A [ENTIDADE_PROTEGIDA_1] pediu o CPF [CPF_1]"
    assert numeracao.originais() == {"[ENTIDADE_PROTEGIDA_1]": "Maria Quitéria", "[CPF_1]": "123.456.789-00"}


def test_texto_do_backend_so_troca_classes_a_e_c():
    protecao = protecao_da_base({"pessoa": ["Joaquina Prates"]}, {}, metadados_extras=["privado.csv"])
    texto = "Resultado de MANAUS (AM), CAP-TEN-01 e TPL-11; nota de privado.csv sobre Joaquina Prates"
    assert preparar(texto, protecao, nominal=False) == \
        "Resultado de MANAUS (AM), CAP-TEN-01 e TPL-11; nota de [ARQUIVO_1] sobre [IDENTIFICADOR_1]"


def test_protecao_da_base_separa_as_classes():
    protecao = protecao_da_base({"distrito": ["Angoche"], "provincia": ["Nampula"], "codigo": ["D1"],
                                 "trabalhador": ["Ana Lúcia"], "quantidade": [3]},
                                {"territory": "distrito", "identity": "trabalhador"}, metadados_extras=["d.csv", "Aba"])
    assert {"angoche", "nampula"} <= protecao.liberados
    assert "ana lucia" in protecao.protegidos and "angoche" not in protecao.protegidos
    assert {"distrito", "provincia", "codigo", "trabalhador", "d.csv", "aba"} <= protecao.metadados


def test_nome_desconhecido_junto_de_territorio_liberado_continua_protegido():
    # Regressão: a sequência nominal com um território liberado não pode deixar passar o nome ao lado dele.
    assert preparar("Compare Joaquim Silveira e Manaus", BASE) == "Compare [ENTIDADE_PROTEGIDA_1] e Manaus"
    assert preparar("Manaus Joaquim", BASE) == "Manaus [ENTIDADE_PROTEGIDA_1]"
    assert preparar("Compare Rio de Janeiro com Porto Alegre e Joaquim", BASE) == \
        "Compare Rio de Janeiro com Porto Alegre e [ENTIDADE_PROTEGIDA_1]"
