FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies from pyproject.toml so adding a new dep
# (httpx, etc.) doesn't require editing this Dockerfile. We copy just the
# metadata + minimal package skeleton first to maximise layer caching.
COPY pyproject.toml README.md /app/
COPY app /app/app
RUN pip install --no-cache-dir /app

COPY tests /app/tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
