# ==========================================
# Stage 1: Build Dependencies using uv
# ==========================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies needed for compiling python extensions if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv compiler/pip tool
RUN pip install --no-cache-dir uv

# Copy requirements and install packages in system site-packages
COPY requirements.txt .
RUN uv pip install --no-cache-dir --system -r requirements.txt

# ==========================================
# Stage 2: Final Slim Runtime Runner
# ==========================================
FROM python:3.12-slim

# Create a non-root user for security best practices
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy python dependencies site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project files and set ownership to appuser
COPY --chown=appuser:appuser . .

# Expose control plane default HTTP port
EXPOSE 8000

# Set Python path to ensure imports resolve
ENV PYTHONPATH=/app

# Use non-root user
USER appuser

# Start FastAPI API Control Plane by default
CMD ["uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
