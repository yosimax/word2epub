# Minimal Dockerfile to run yaml2epub in a reproducible container
# Note: lxml and some packages require system build deps; we install them here.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required to build some Python packages (lxml etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libxml2-dev \
       libxslt1-dev \
       zlib1g-dev \
       gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy lockfile / requirements if available for deterministic installs
COPY requirements.txt requirements-dev.txt pyproject.toml ./

RUN python -m pip install --upgrade pip setuptools wheel

# Install runtime requirements (if present)
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Optionally install dev requirements at build time by passing --build-arg INSTALL_DEV=true
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ] && [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Copy project files
COPY . .

# Default command: run the script (users can override the CMD at runtime)
ENTRYPOINT ["python", "yaml2epub.py"]
