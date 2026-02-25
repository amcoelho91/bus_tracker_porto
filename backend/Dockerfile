FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy project metadata AND source before installing the package
COPY pyproject.toml /app/pyproject.toml
COPY src /app/src

# Install dependencies (and your package)
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "app.main"]