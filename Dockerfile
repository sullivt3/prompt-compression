FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/gateway
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY app ./app
ENV TIKTOKEN_CACHE_DIR=/srv/tokenizer-cache
RUN pip install --no-cache-dir --no-deps . && python -c "import tiktoken; tiktoken.get_encoding('o200k_base'); tiktoken.get_encoding('cl100k_base')" && useradd --system --uid 10001 gateway
COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
USER gateway
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
