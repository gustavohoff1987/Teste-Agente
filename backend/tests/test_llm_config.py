"""Credencial local persistente: testes offline sem qualquer chave verdadeira."""
from pathlib import Path

import llm_bridge
from llm_config import LOCAL_ENV_PATH, load_local_environment


def test_local_env_file_loads_key_and_only_reports_boolean(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    fake = "test-only-in-memory-not-a-real-secret"
    path = tmp_path / ".env"
    path.write_text(f"GEMINI_API_KEY={fake}\n", encoding="utf-8")
    assert load_local_environment(path) is True
    status = llm_bridge.status()
    assert status["configured"] is True
    assert "GEMINI_API_KEY" not in status
    assert fake not in str(status)


def test_host_environment_precedence_over_local_file(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "injected-by-host")
    path = tmp_path / ".env"
    path.write_text("GEMINI_API_KEY=local-not-to-use\n", encoding="utf-8")
    load_local_environment(path)
    assert llm_bridge.os.environ["GEMINI_API_KEY"] == "injected-by-host"


def test_absent_or_empty_local_secret_never_enables_gemini(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert load_local_environment(tmp_path / "missing.env") is False
    assert llm_bridge.status()["configured"] is False
    empty = tmp_path / ".env"
    empty.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    load_local_environment(empty)
    assert llm_bridge.status()["configured"] is False


def test_secret_path_is_anchored_to_backend_not_working_directory():
    assert isinstance(LOCAL_ENV_PATH, Path)
    assert LOCAL_ENV_PATH.name == ".env"
    assert LOCAL_ENV_PATH.parent.name == "backend"
