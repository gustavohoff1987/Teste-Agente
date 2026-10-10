"""Carregamento local de credenciais para desenvolvimento.

Arquivo fixo backend/.env: nunca é versionado ou incluído no frontend.
Variáveis já definidas pelo sistema/hospedagem sempre prevalecem.
"""
from pathlib import Path

from dotenv import load_dotenv

LOCAL_ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_local_environment(path: Path | None = None) -> bool:
    """Carrega .env uma vez, sem ecoar variáveis ou alterar segredo do host."""
    return load_dotenv(dotenv_path=path if path is not None else LOCAL_ENV_PATH,
                       override=False)
