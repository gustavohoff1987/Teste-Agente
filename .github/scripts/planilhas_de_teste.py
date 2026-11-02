"""Planilhas sintéticas para as medições do contêiner (medir_conteiner.py): CSV e XLSX com as colunas do modelo recomendado,
de tamanho exato, e os casos de recusa (malformada, truncada e com expansão desproporcional).

Os territórios, códigos e valores são inventados (nenhum dado real). O XLSX segue o formato do Excel (cadeias compartilhadas)
e chega ao tamanho exato com uma parte armazenada sem compressão, que o leitor ignora. Tudo é determinístico (semente fixa).
"""
import io
import random
import zipfile
from pathlib import Path

CABECALHO = ["territorio_analise", "territorio_superior_1", "territorio_superior_2", "codigo_identificador", "latitude",
             "longitude", "categoria_profissional", "periodo_ano", "periodo_mes", "quantidade", "populacao_estimada"]
TERRITORIOS = 5570
PREENCHIMENTO = "docProps/preenchimento.bin"


def linhas(semente: int = 7):
    """Linhas sem fim: todos os territórios numa competência, depois a seguinte (mês a mês desde janeiro de 2016)."""
    sorteio = random.Random(semente)
    territorios = [(f"Território {i:04d}", f"Grupo {i % 27:02d}", f"Região {i % 5}", str(1100000 + i),
                    f"{sorteio.uniform(-33, 5):.6f}", f"{sorteio.uniform(-73, -35):.6f}", sorteio.randint(1000, 900000))
                   for i in range(TERRITORIOS)]
    ano, mes = 2016, 1
    while True:
        for nome, grupo, regiao, codigo, lat, lon, populacao in territorios:
            yield [nome, grupo, regiao, codigo, lat, lon, "MEDICINA", str(ano), str(mes), str(sorteio.randint(0, 3000)),
                   str(populacao + sorteio.randint(-500, 500))]
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1


def csv_exato(caminho: Path, tamanho: int) -> Path:
    """CSV de exatamente `tamanho` bytes; o que sobra fica em linhas em branco no fim (a leitura as ignora)."""
    total = 0
    with caminho.open("wb") as saida:
        cabecalho = (";".join(CABECALHO) + "\n").encode("utf-8")
        saida.write(cabecalho)
        total += len(cabecalho)
        for linha in linhas():
            dados = (";".join(linha) + "\n").encode("utf-8")
            if total + len(dados) > tamanho:
                break
            saida.write(dados)
            total += len(dados)
        saida.write(b"\n" * (tamanho - total))
    assert caminho.stat().st_size == tamanho
    return caminho


def _coluna(indice: int) -> str:
    letras = ""
    indice += 1
    while indice:
        indice, resto = divmod(indice - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _escapar(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


PARTES_FIXAS = {
    "[Content_Types].xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'),
    "_rels/.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'),
    "xl/workbook.xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Dados" sheetId="1" r:id="rId1"/></sheets></workbook>'),
    "xl/_rels/workbook.xml.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'),
    "xl/styles.xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="1"><xf xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'),
}
NUMERICAS = {"codigo_identificador", "periodo_ano", "periodo_mes", "quantidade", "populacao_estimada"}


def _pacote(alvo_comprimido: int, preenchimento: int | None) -> tuple[bytes, int]:
    """O XLSX com linhas até o conteúdo comprimido chegar perto do alvo; com `preenchimento`, a parte armazenada desse
    tamanho. Devolve (bytes, tamanho que a parte de preenchimento precisa ter para fechar o alvo)."""
    saida = io.BytesIO()
    compartilhadas: dict[str, int] = {}
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as pacote:
        for nome, texto in PARTES_FIXAS.items():
            pacote.writestr(nome, texto)
        with pacote.open("xl/worksheets/sheet1.xml", "w") as folha:
            folha.write(b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')

            def linha_xml(numero: int, valores: list[str]) -> bytes:
                celulas = []
                for indice, (coluna, valor) in enumerate(zip(CABECALHO, valores)):
                    referencia = _coluna(indice) + str(numero)
                    if coluna in NUMERICAS and numero > 1:
                        celulas.append(f'<c r="{referencia}"><v>{valor}</v></c>')
                    else:
                        posicao = compartilhadas.setdefault(valor, len(compartilhadas))
                        celulas.append(f'<c r="{referencia}" t="s"><v>{posicao}</v></c>')
                return (f'<row r="{numero}">' + "".join(celulas) + "</row>").encode("utf-8")
            folha.write(linha_xml(1, CABECALHO))
            numero = 2
            # Folga para as cadeias compartilhadas, as partes finais e o diretório do pacote; a conferência é por blocos de
            # linhas, menores nos arquivos pequenos.
            margem = min(900_000, max(60_000, alvo_comprimido // 4))
            passo = 200 if alvo_comprimido < 2_000_000 else 2000
            for valores in linhas():
                folha.write(linha_xml(numero, valores))
                numero += 1
                if numero % passo == 0 and saida.tell() >= alvo_comprimido - margem:
                    break
            folha.write(b"</sheetData></worksheet>")
        textos = "".join(f"<si><t>{_escapar(texto)}</t></si>" for texto in compartilhadas)
        pacote.writestr("xl/sharedStrings.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="%d" uniqueCount="%d">'
                        % (len(compartilhadas), len(compartilhadas)) + textos + "</sst>")
        posicao = saida.tell()
        diretorio = sum(46 + len(item.filename.encode()) + len(item.extra) + len(item.comment) for item in pacote.infolist())
        nome = PREENCHIMENTO.encode()
        necessario = alvo_comprimido - (posicao + 30 + len(nome) + diretorio + 46 + len(nome) + 22)
        if preenchimento is not None:
            pacote.writestr(zipfile.ZipInfo(PREENCHIMENTO), random.Random(11).randbytes(max(0, preenchimento)))
    return saida.getvalue(), necessario


def xlsx_exato(caminho: Path, tamanho: int) -> Path:
    """XLSX de exatamente `tamanho` bytes."""
    _, necessario = _pacote(tamanho, None)
    if necessario < 0:
        raise RuntimeError("o conteúdo passou do alvo; aumente a margem")
    dados, _ = _pacote(tamanho, necessario)
    if len(dados) != tamanho:  # o deflate é determinístico: a diferença fecha na segunda volta
        dados, _ = _pacote(tamanho, necessario + tamanho - len(dados))
    assert len(dados) == tamanho, (len(dados), tamanho)
    caminho.write_bytes(dados)
    return caminho


def xlsx_expandido(caminho: Path, megabytes: int) -> Path:
    """Pacote pequeno cujo conteúdo, descompactado, tem `megabytes` MB (expansão desproporcional)."""
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as pacote:
        for nome, texto in PARTES_FIXAS.items():
            pacote.writestr(nome, texto)
        with pacote.open("xl/worksheets/sheet1.xml", "w") as folha:
            bloco = b"0" * (1024 * 1024)
            for _ in range(megabytes):
                folha.write(bloco)
    return caminho


def xlsx_malformado(caminho: Path) -> Path:
    caminho.write_bytes(random.Random(3).randbytes(1_000_000))
    return caminho


def xlsx_truncado(caminho: Path, origem: Path) -> Path:
    dados = origem.read_bytes()
    caminho.write_bytes(dados[: len(dados) // 2])
    return caminho
