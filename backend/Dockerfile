FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir \
    bcrypt \
    celery \
    fastapi \
    pydantic-settings \
    "psycopg[binary]" \
    redis \
    sqlalchemy \
    uvicorn[standard]

COPY app /app/app
COPY tests /app/tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
