"""Proteção de carga da hospedagem (Cloud Run: uma instância de 1 vCPU e 2 GiB, decisão de implantação de 01/11/2026).

- **Tamanho do pedido:** o arquivo enviado tem até 15 MB (15.000.000 bytes); o pedido inteiro, até o arquivo e mais os
  campos do formulário (mapeamento, opções, conversa). Acima disso, 413, antes de qualquer leitura.
- **Operações pesadas** (ler uma planilha, conferir e copiar a base do Brasil, calcular no motor) correm em vagas, fora do
  laço de eventos: `/api/health`, a consulta da sessão e a conversa continuam respondendo enquanto o motor calcula. Sem vaga,
  o pedido espera na fila, em ordem de chegada; com a fila cheia ou depois da espera máxima, recebe 503 com `ocupado` e a
  mensagem cordial. Um pedido que o navegador abandonou enquanto esperava (o gráfico mudou de novo) sai da fila sem calcular.
- **Pedidos por sessão:** cada sessão (`X-ADT-Session`) tem um número máximo de pedidos pesados ou da conversa em andamento;
  acima dele, só o pedido novo é recusado.

Nenhum limite encerra uma sessão nem apaga o que ela guarda: no limite, só o pedido novo é recusado. Os contadores ficam na
memória do processo e recomeçam com o contêiner. Nada aqui lê o conteúdo dos pedidos, nem o registra.
"""
import asyncio
import collections
import io
import json
import os
import threading
import time
import zipfile

MAX_UPLOAD_BYTES = 15_000_000  # 15 MB por arquivo (antes de 01/11/2026, 30 MiB)
# Campos do formulário além do arquivo: o mapeamento, as opções do gráfico, a janela e a memória da conversa.
MARGEM_DO_FORMULARIO = 2 * 1024 * 1024
LIMITE_DO_PEDIDO = MAX_UPLOAD_BYTES + MARGEM_DO_FORMULARIO

TEXTO_ARQUIVO_GRANDE = "Arquivo acima do limite de 15 MB; nenhum dado foi analisado."
TEXTO_OCUPADO = ("O Agente Diagnóstico Territorial da Força de Trabalho na Saúde está atendendo muitas solicitações neste "
                 "momento. Aguarde alguns segundos e tente novamente; a sua sessão e as suas análises continuam.")
TEXTO_SESSAO_OCUPADA = ("Ainda há pedidos seus em andamento. Aguarde a conclusão deles e tente novamente; a sua sessão e as "
                        "suas análises continuam.")
TENTE_EM_SEGUNDOS = 5

# Planilhas XLSX são pacotes compactados: o que conta para a memória é o conteúdo depois de descompactado. Recusada, antes
# da leitura, a planilha que passa do teto absoluto ou que cresce mais que a proporção máxima (com um piso, para que
# arquivos pequenos não sejam recusados pela proporção). A planilha legítima de 15 MB cresce de 5 a 20 vezes.
XLSX_EXPANDIDO_MAXIMO = 150_000_000
XLSX_PROPORCAO_MAXIMA = 100
XLSX_PISO_DA_PROPORCAO = 10_000_000
# CSV: o texto não se expande, mas cada célula vira um objeto na memória. O CSV legítimo de 15 MB com as colunas do modelo
# tem cerca de 2 milhões de células; o teto recusa os arquivos de células minúsculas e muitíssimas linhas.
CSV_CELULAS_MAXIMAS = 6_000_000
# TPL-13 (RQ-DAD-43): impossibilidade técnica de materialização integral; o texto é fixo (CFG-TPL).
TPL_13 = ("Não foi possível materializar integralmente esta entrada. Ela não foi analisada. Forneça um arquivo estruturado "
          "em formato admitido (CSV ou XLSX) e associe-o ao pedido preservado. O arquivo será uma nova entrada; a retomada "
          "depende da associação e habilitação válidas.")


class Ocupado(Exception):
    """Sem vaga para a operação pesada: o pedido é recusado com 503 e `ocupado`, sem afetar a sessão."""

    def __init__(self, texto: str = TEXTO_OCUPADO):
        super().__init__(texto)
        self.texto = texto


def corpo_ocupado(texto: str = TEXTO_OCUPADO) -> dict:
    return {"detail": texto, "ocupado": True, "tente_em": TENTE_EM_SEGUNDOS}


def _megabytes(valor: int) -> str:
    return f"{valor / 1_000_000:.1f}".replace(".", ",")


def conferir_xlsx(contents: bytes) -> None:
    """Recusa, antes da leitura, o XLSX com expansão desproporcional ao tamanho do arquivo. O pacote que não é ZIP segue
    para a leitura, que o recusa com a mensagem de arquivo Excel inválido. Os tamanhos declarados no pacote limitam o que
    a descompactação entrega (o zipfile não lê além deles)."""
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as pacote:
            expandido = sum(max(0, item.file_size) for item in pacote.infolist())
    except (zipfile.BadZipFile, OSError, ValueError, EOFError):
        return
    limite = min(XLSX_EXPANDIDO_MAXIMO, max(XLSX_PISO_DA_PROPORCAO, XLSX_PROPORCAO_MAXIMA * len(contents)))
    if expandido > limite:
        raise ValueError("A planilha cresce demais quando é aberta: o conteúdo do arquivo XLSX, descompactado, teria "
                         + _megabytes(expandido) + " MB, para um arquivo de " + _megabytes(len(contents)) +
                         " MB, acima do que esta versão processa com segurança. " + TPL_13)


def conferir_csv(linhas: int, colunas: int) -> None:
    """Recusa o CSV com células demais para a memória do serviço; a leitura chama a cada bloco de linhas, de modo que a
    recusa vem antes de a memória crescer além do teto."""
    if linhas * colunas > CSV_CELULAS_MAXIMAS:
        raise ValueError("A planilha tem células demais para esta versão: mais de " +
                         f"{CSV_CELULAS_MAXIMAS:,}".replace(",", ".") + " células. " + TPL_13)


def _inteiro(nome: str, padrao: int, minimo: int) -> int:
    try:
        return max(minimo, int(os.getenv(nome, str(padrao))))
    except ValueError:
        return padrao


class Vagas:
    """Vagas para operações pesadas: no máximo `total` ao mesmo tempo; até `fila` pedidos esperam, em ordem de chegada, no
    máximo `espera` segundos. Funciona em qualquer laço de eventos (o servidor, o TestClient, o aquecimento), porque a
    espera consulta o estado a cada 50 ms em vez de guardar um futuro preso a um laço."""

    def __init__(self, total: int, fila: int, espera: float, relogio=time.monotonic):
        self.total, self.fila_maxima, self.espera = total, fila, espera
        self._relogio = relogio
        self._lock = threading.Lock()
        self._em_uso = 0
        self._fila: collections.deque = collections.deque()
        self.recusas = 0
        self.abandonos = 0

    def _tentar(self, senha) -> bool:
        with self._lock:
            if self._em_uso < self.total and self._fila and self._fila[0] is senha:
                self._fila.popleft()
                self._em_uso += 1
                return True
            return False

    async def entrar(self, desistiu=None) -> bool:
        """True com a vaga ocupada (quem entra chama `sair` depois). False sem vaga: fila cheia, espera esgotada ou, com
        `desistiu`, o pedido abandonado enquanto esperava."""
        senha = object()
        with self._lock:
            if self._em_uso < self.total and not self._fila:
                self._em_uso += 1
                return True
            if len(self._fila) >= self.fila_maxima:
                self.recusas += 1
                return False
            self._fila.append(senha)
        prazo = self._relogio() + self.espera
        try:
            while not self._tentar(senha):
                if desistiu is not None and desistiu():
                    with self._lock:
                        self.abandonos += 1
                    return False
                if self._relogio() >= prazo:
                    with self._lock:
                        self.recusas += 1
                    return False
                await asyncio.sleep(0.05)
            return True
        finally:
            with self._lock:
                try:
                    self._fila.remove(senha)
                except ValueError:
                    pass

    def sair(self) -> None:
        with self._lock:
            self._em_uso = max(0, self._em_uso - 1)

    def estado(self) -> dict:
        with self._lock:
            return {"total": self.total, "em_uso": self._em_uso, "na_fila": len(self._fila), "fila_maxima": self.fila_maxima,
                    "espera_s": self.espera, "recusas": self.recusas, "abandonos": self.abandonos}


VAGAS = Vagas(total=_inteiro("ADT_PESADAS_SIMULTANEAS", 2, 1), fila=_inteiro("ADT_PESADAS_FILA", 8, 0),
              espera=float(_inteiro("ADT_PESADAS_ESPERA_S", 20, 1)))
POR_SESSAO = _inteiro("ADT_PEDIDOS_POR_SESSAO", 6, 1)

# Rotas que leem a base ou a planilha e calculam no motor: ocupam uma vaga durante todo o pedido.
PESADAS = frozenset(("/api/inspect", "/api/preflight", "/api/analyze", "/api/painel", "/api/painel/referencias",
                     "/api/painel/territorios", "/api/painel/mapa", "/api/brazil/description"))
# Rotas da conversa: contam nos pedidos da sessão; a leitura da base ocupa uma vaga só enquanto dura (main._request_dataset),
# e a espera pelo provedor de IA não ocupa vaga.
CONVERSA = frozenset(("/api/llm/interpret", "/api/llm/interpret-context", "/api/exploration/interpret"))


def _cabecalho(scope, nome: bytes) -> str:
    for chave, valor in scope.get("headers") or []:
        if chave.lower() == nome:
            return valor.decode("latin-1").strip()
    return ""


async def _responder(send, status: int, corpo: dict, extras=()) -> None:
    dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
    cabecalhos = [(b"content-type", b"application/json"), (b"content-length", str(len(dados)).encode()),
                  (b"cache-control", b"no-store"), *extras]
    await send({"type": "http.response.start", "status": status, "headers": cabecalhos})
    await send({"type": "http.response.body", "body": dados})


class _Grande(Exception):
    pass


async def _ler_corpo(receive, limite: int):
    """O corpo inteiro do pedido (até `limite` bytes) ou None se o navegador desistiu antes de terminar o envio."""
    partes, total = [], 0
    while True:
        mensagem = await receive()
        if mensagem["type"] == "http.disconnect":
            return None
        corpo = mensagem.get("body", b"")
        total += len(corpo)
        if total > limite:
            raise _Grande()
        partes.append(corpo)
        if not mensagem.get("more_body", False):
            return b"".join(partes)


def _repetir(corpo: bytes, receive):
    """receive para o app: o corpo já lido, uma vez; depois, o receive original (o fim da conexão)."""
    entregue = False

    async def receber():
        nonlocal entregue
        if not entregue:
            entregue = True
            return {"type": "http.request", "body": corpo, "more_body": False}
        return await receive()
    return receber


class ProtecaoDeCarga:
    """Middleware ASGI. Fica por dentro do CORS, para que as recusas (413, 503) cheguem legíveis ao navegador."""

    def __init__(self, app, vagas: Vagas | None = None, por_sessao: int | None = None, ignorar=lambda: False):
        self.app = app
        self._vagas = vagas
        self._por_sessao = por_sessao
        self.ignorar = ignorar
        self._lock = threading.Lock()
        self._sessoes: dict[str, int] = {}

    @property
    def vagas(self) -> Vagas:
        return self._vagas or VAGAS  # sem vagas próprias, as do processo (as mesmas das rotas da conversa)

    def _entrar_na_sessao(self, token: str) -> bool:
        with self._lock:
            atual = self._sessoes.get(token, 0)
            if atual >= (self._por_sessao or POR_SESSAO):
                return False
            self._sessoes[token] = atual + 1
            return True

    def _sair_da_sessao(self, token: str) -> None:
        with self._lock:
            restante = self._sessoes.get(token, 0) - 1
            if restante > 0:
                self._sessoes[token] = restante
            else:
                self._sessoes.pop(token, None)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.ignorar():
            await self.app(scope, receive, send)
            return
        declarado = _cabecalho(scope, b"content-length")
        tamanho = int(declarado) if declarado.isdigit() else None
        if tamanho is not None and tamanho > LIMITE_DO_PEDIDO:
            await _responder(send, 413, {"detail": TEXTO_ARQUIVO_GRANDE})
            return
        caminho, metodo = scope.get("path", ""), scope.get("method", "GET")
        pesada = caminho in PESADAS
        conversa = metodo == "POST" and caminho in CONVERSA
        if not (pesada or conversa):
            if metodo == "POST" and tamanho is None:
                await self._com_corpo(scope, receive, send, pesada=False)
            else:
                await self.app(scope, receive, send)
            return
        token = _cabecalho(scope, b"x-adt-session")
        if token and not self._entrar_na_sessao(token):
            await _responder(send, 503, corpo_ocupado(TEXTO_SESSAO_OCUPADA),
                             [(b"retry-after", str(TENTE_EM_SEGUNDOS).encode())])
            return
        try:
            if pesada or tamanho is None:
                await self._com_corpo(scope, receive, send, pesada=pesada)
            else:
                await self.app(scope, receive, send)
        finally:
            if token:
                self._sair_da_sessao(token)

    async def _com_corpo(self, scope, receive, send, *, pesada: bool):
        try:
            corpo = await _ler_corpo(receive, LIMITE_DO_PEDIDO)
        except _Grande:
            await _responder(send, 413, {"detail": TEXTO_ARQUIVO_GRANDE})
            return
        if corpo is None:
            return  # o navegador desistiu durante o envio: nada a responder
        if not pesada:
            await self.app(scope, _repetir(corpo, receive), send)
            return
        # Na fila, o fim da conexão (o navegador abandonou o pedido) tira o pedido da fila sem calcular.
        desistiu = asyncio.Event()

        async def vigiar():
            mensagem = await receive()
            if mensagem.get("type") == "http.disconnect":
                desistiu.set()
        vigia = asyncio.ensure_future(vigiar())
        try:
            entrou = await self.vagas.entrar(desistiu=desistiu.is_set)
        finally:
            vigia.cancel()
            try:
                await vigia
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 — só a vigília do fim da conexão
                pass
        if not entrou:
            if not desistiu.is_set():
                await _responder(send, 503, corpo_ocupado(), [(b"retry-after", str(TENTE_EM_SEGUNDOS).encode())])
            return
        try:
            await self.app(scope, _repetir(corpo, receive), send)
        finally:
            self.vagas.sair()
