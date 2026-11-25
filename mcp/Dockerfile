FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend.py server.py ./

# Non-root: this container only ever reads HTTP, so it needs nothing else.
RUN useradd --create-home --uid 10001 mcp && chown -R mcp:mcp /srv
USER mcp

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)"

# `--proxy-headers` with explicit private ranges (AGENTS.md rule 27): nginx is
# the only hop, and trusting `*` would let a client forge the forwarded IP.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", \
     "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]
