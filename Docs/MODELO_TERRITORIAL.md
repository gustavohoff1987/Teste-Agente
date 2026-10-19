# Estrutura recomendada dos dados territoriais

A opção **Importar seus dados** oferece o download de um XLSX com uma única aba
`Dados`. A tabela editável ocupa **A:K**; a legenda explicativa permanece à
direita, em **M:O**, e é excluída da leitura pelo backend quando o arquivo
contém a identificação exata da legenda gerada pelo sistema.

## Cabeçalhos da tabela

`territorio_analise`, `territorio_superior_1`,
`territorio_superior_2`, `codigo_identificador`, `latitude`,
`longitude`, `categoria_profissional`, `periodo_ano`,
`periodo_mes`, `quantidade`, `populacao_estimada`.

O modelo segue a organização da fonte municipal brasileira, mas sua
nomenclatura é neutra quanto ao país. Não incorpora registros brasileiros.

## Hierarquia declarada

- **Território de análise:** unidade representada em cada linha.
- **Território superior 1:** unidade que contém o território de análise.
- **Território superior 2:** unidade que contém o território superior 1.

O carregamento identifica também equivalências determinísticas, por exemplo:
`municipio` / `UF` / `regiao_geografica` e
`codigo_identificador` / `cod_ibge`. O código territorial fica como sugestão no topo do seletor, que
permanece vazio até a escolha do usuário (o nome do campo não basta para estabelecê-lo).

Outros nomes de colunas são permitidos. O território analisado pode ser
associado na preparação; as colunas superiores desconhecidas podem ser
selecionadas em **Hierarquia territorial**, na mesma etapa.

O backend verifica relações observadas nos registros e devolve sua descrição
em `territorial_hierarchy` no pré-exame, bem como nos metadados dos cálculos.
Isso **não prova limites administrativos** externos, **não autoriza agregação**,
não substitui as premissas metodológicas (aplicadas pelo backend, com nota) e não resolve sobreposições de
contagens de profissionais. Municípios homônimos podem ser diferenciados por
códigos, que são tratados como identificadores opacos.

Na base Brasil oficial (desde 19/10/2026), o estado de cada município vem do prefixo do código IBGE, pela
regra governada `brasil-cod-uf-prefix-1`, e não da coluna `uf`. O estado como objeto de análise é sempre a
soma dos seus municípios (SOMA_DOS_COMPONENTES, com possível dupla contagem), nunca o total de pessoas
distintas do estado nem algo comparável com o total do Brasil. A divergência da coluna `uf` em uma
competência (o 251365, declarado PA em 2016/6) vira uma nota, e o município continua selecionável como PB.
Em bases importadas, a hierarquia de colunas continua só descritiva: não autoriza agregação, e a unidade
com hierarquia divergente continua bloqueada para seleção. Detalhes:
[abrangência territorial](ABRANGENCIA_TERRITORIAL.md).

## Compatibilidade

O carregador normaliza apenas em memória. Nenhuma coluna é renomeada nos
arquivos brasileiros originais; `cod_ibge` continua aceito e vinculado ao
papel interno `territory_id`. Os algoritmos determinísticos continuam usando
os papéis internos já existentes.

Os níveis superiores são opcionais para bases sem hierarquia informada.
Campos de população, coordenadas e período são exigidos apenas conforme o
tipo de análise e suas respectivas regras de habilitação.

## Uso

1. Clique **Importar seus dados → Estrutura recomendada (.xlsx)**.
2. Abra o arquivo Excel e consulte a legenda à direita.
3. Preencha as colunas A:K. Pode alterar cabeçalhos para equivalentes conhecidos.
4. Salve em XLSX e escolha **Importar arquivo**.
5. Confira as associações detectadas e escolha nos seletores as colunas que ficaram como
   sugestão (por exemplo, `codigo_identificador`) antes de executar cálculos; não há confirmação
   de significados.
