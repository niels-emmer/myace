FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with uvicorn. --proxy-headers trusts X-Forwarded-Proto/X-Forwarded-For
# from whatever's in front of this container (a reverse proxy in prod) so
# redirect_uri generation (OIDC callbacks) resolves to https:// correctly —
# safe here specifically because docker-compose.prod.yml exposes no host
# port, so only the proxy container on the same Docker network can reach
# this at all. No --reload here; docker-compose.dev.yml adds it back for
# local development via a command override.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
