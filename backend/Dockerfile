FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies only — pytest/mypy/ruff/aiosqlite are test
# tooling and have no business in the image that serves production traffic.
# (Run the test suite from the host: `cd backend && pip install -e ".[dev]"`.)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Informational only (nothing depends_on it). TrustedHostMiddleware rejects an
# unknown Host header in production, so send the first configured trusted host.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request as u; h = (os.environ.get('TRUSTED_HOSTS') or 'localhost').split(',')[0].strip(); u.urlopen(u.Request('http://127.0.0.1:8000/health', headers={'Host': h}), timeout=4)"

# Run with uvicorn. --proxy-headers trusts X-Forwarded-Proto/X-Forwarded-For
# from the proxies in front of this container so redirect_uri generation
# (OIDC callbacks) resolves to https:// and per-IP rate limits see the real
# client. The trusted set is the *private* ranges, not "*": with "*" uvicorn
# takes the LEFT-most X-Forwarded-For entry, which the client controls, so a
# forged header both spoofed the client IP and bypassed the auth rate limits.
# With explicit ranges it walks the header from the right and stops at the
# first untrusted address — the real client as appended by the outermost
# proxy — and ignores anything the client prepended. Every proxy hop here
# (reverse proxy, the frontend's nginx) sits on a private Docker address, and
# docker-compose.prod.yml exposes no host port, so nothing else reaches this.
# tests/test_forwarded_ips.py pins this value. No --reload here;
# docker-compose.dev.yml adds it back for local development via a command
# override.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]
