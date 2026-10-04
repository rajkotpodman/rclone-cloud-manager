# ==============================================================================
# Rclone Cloud Manager - Dockerfile
# Base: Python 3.10 Slim with official Rclone binary
# ==============================================================================

FROM python:3.10-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install curl, ca-certificates, and Rclone
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    unzip \
    && curl -fsSL https://rclone.org/install.sh | bash \
    && apt-get purge -y --auto-remove curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python package dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source and assets
COPY src/ src/
COPY templates/ templates/
COPY config/ config/
COPY scripts/ scripts/
COPY docs/ docs/
COPY LICENSE README.md ./

# Create default logs directory
RUN mkdir -p logs

# Expose Web Dashboard Port
EXPOSE 5000

# Set entrypoint to main CLI tool
ENTRYPOINT ["python", "src/main.py"]
CMD ["--help"]
