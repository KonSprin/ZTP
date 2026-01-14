FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry==1.7.1

COPY pyproject.toml poetry.lock* ./

# RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
