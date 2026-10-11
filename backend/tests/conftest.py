"""A regressão é offline, inclusive quando há credenciais no ambiente local."""
import socket
import pytest


@pytest.fixture(autouse=True)
def forbid_external_network(monkeypatch):
    original_connect = socket.socket.connect
    original_lookup = socket.getaddrinfo

    def allowed(host):
        return host in ("localhost", "127.0.0.1", "::1", None)

    def connect(sock, address):
        if isinstance(address, tuple) and not allowed(address[0]):
            raise AssertionError("Rede externa proibida durante os testes")
        return original_connect(sock, address)

    def lookup(host, *args, **kwargs):
        if not allowed(host):
            raise AssertionError("DNS externo proibido durante os testes")
        return original_lookup(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
