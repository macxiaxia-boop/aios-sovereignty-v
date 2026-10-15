FROM python:3.11-slim
WORKDIR /app
# Install runtime deps for PostgreSQL + AIOS kernel gateway
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy project files (use .dockerignore for cache friendliness)
COPY pyproject.toml .
COPY src/aios_kernel ./aios_kernel
COPY README.md .

# Install kernel + runtime deps
RUN pip install --no-cache-dir -e .

# Production hardening
ENV AIOS_KERNEL_OFFLINE=1 \
    AIOS_KERNEL_NO_EXTERNAL_APIS=1 \
    AIOS_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose HTTP/MCP gateway (default) + scheduler is in-process
EXPOSE 9000

# Health check via the gateway /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9000/health').read()" || exit 1

# Default: run scheduler foreground (PID 1). For HTTP gateway, override with
#   docker run -p 9000:9000 ... aios-kernel gateway:run
CMD ["python", "-m", "aios_kernel.cli", "scheduler", "run"]
