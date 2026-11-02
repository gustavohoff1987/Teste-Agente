# Agente Diagnóstico Territorial da Força de Trabalho na Saúde — serviço de análise (backend FastAPI) para o Google Cloud Run.
#
# Construída e verificada no GitHub Actions (job "conteiner" do ci.yml); o envio ao Artifact Registry é só do workflow
# imagem.yml, na Fase 2 (Docs/implantacao/ROTEIRO_FASE2.md). Python 3.11 slim fixado por digest e dependências com versões
# exatas (backend/requirements-conteiner.txt): a imagem é reprodutível. Leva o backend, a base do Brasil versionada com o
# manifesto (integridade conferida no aquecimento e a cada requisição), a camada de coordenadas, a biblioteca conversacional e
# o catálogo documental com a SPEC, que o backend lê em execução. Nenhum segredo: em produção, a chave do Gemini chega pelo
# Secret Manager como variável de ambiente; backend/.env e qualquer .env ficam fora (.dockerignore).
FROM python:3.11.18-slim-trixie@sha256:ffe4b0c76963e64f05484d74dbb3f67fad1effcf3c5c22c2235f0fafc8a9c98f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    HOME=/tmp \
    PORT=8080 \
    ADT_DOCUMENTACAO_DA_API=0

COPY backend/requirements-conteiner.txt /tmp/requirements-conteiner.txt
RUN pip install --no-deps -r /tmp/requirements-conteiner.txt && pip check && rm /tmp/requirements-conteiner.txt

WORKDIR /app
COPY Dados_Brasil.xlsx Dados_Estados_Brasil.csv Dados_Municipios_Brasil.csv IMPLEMENTATION_SPEC.md ./
COPY dados/brasil/ dados/brasil/
COPY Docs/CFG_DOC_CATALOG.yaml Docs/CFG_DOC_CATALOG.yaml
COPY backend/ backend/
# Os .pyc vêm prontos (o usuário do serviço não grava na pasta do app) e o serviço roda sem privilégios.
RUN python -m compileall -q backend \
    && useradd --system --uid 10001 --gid nogroup --no-create-home --home-dir /tmp --shell /usr/sbin/nologin adt

USER 10001
WORKDIR /app/backend
EXPOSE 8080
# A verificação de saúde do Docker (o Cloud Run usa a própria verificação de partida, pela porta).
HEALTHCHECK --interval=30s --timeout=5s --start-period=240s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/api/health', timeout=4)"]
# Um processo Uvicorn em 0.0.0.0:$PORT; o exec deixa o Uvicorn como PID 1, que recebe o SIGTERM do Cloud Run e encerra limpo
# (até 8 s para os pedidos em curso, dentro dos 10 s da plataforma). O aquecimento termina antes de a porta abrir.
CMD exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}" --workers 1 --timeout-graceful-shutdown 8 \
    --no-access-log --no-server-header
