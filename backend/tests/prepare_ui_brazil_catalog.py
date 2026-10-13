"""Instala somente bases sintéticas locais para o teste de navegação da CI."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openpyxl import Workbook
from install_brazil_data import install


def prepare(destination: Path) -> None:
    with TemporaryDirectory(prefix="adt-ui-synthetic-source-") as folder:
        source = Path(folder)
        book = Workbook()
        book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
        book.active.append(["Brasil", 2024, 6, "MEDICINA", 30])
        book.active.append(["Brasil", 2023, 6, "MEDICINA", 20])
        book.save(source / "Dados_Brasil.xlsx")
        (source / "Dados_Municipios_Brasil.csv").write_text(
            "municipio;cod_ibge;periodo_ano;periodo_mes;categoria_profissional;quantidade;população_estimada;latitude;longitude\n"
            "A;001;2024;6;MEDICINA;10;1000;-10;-40\n"
            "B;002;2024;6;MEDICINA;20;2000;-11;-41\n",
            encoding="utf-8",
        )
        install(source, destination, governed=False)  # fixture sintética, nunca a versão governada


if __name__ == "__main__":
    prepare(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/adt-brazil-synthetic"))
    print("Dual-source synthetic catalog installed outside the repository.")
