"""Fixture sintética explícita para CI; não representa quantitativos reais."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openpyxl import Workbook
from brazil_data import FILES
from install_brazil_data import install


def prepare(destination):
    with TemporaryDirectory(prefix="adt-block1-") as folder:
        source = Path(folder)
        book = Workbook()
        book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
        rows = ["municipio;cod_ibge;periodo_ano;periodo_mes;categoria_profissional;quantidade;população_estimada;latitude;longitude"]
        for year, month, offset in [(2023, 1, 0), (2023, 6, 2), (2024, 1, 3), (2024, 6, 5)]:
            book.active.append(["Brasil", year, month, "MEDICINA", 100 + offset])
            for name, code, count, population in [("MANAUS", "130260", 10, 1000), ("TEFE", "130420", 5, 2000),
                                                    ("PARINTINS", "130340", 7, 4000), ("FORA", "350010", 100, 9000)]:
                rows.append(f"{name};{code};{year};{month};MEDICINA;{count + offset};{population};-3;-60")
        book.save(source / FILES["national"])
        (source / FILES["municipal"]).write_text("\n".join(rows) + "\n", encoding="utf-8")
        install(source, destination)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]))
    print("Catálogo sintético do Bloco 1 preparado.")
