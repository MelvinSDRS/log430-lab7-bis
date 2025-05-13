FROM python:3.12-slim AS builder

WORKDIR /app

COPY app.py test_app.py ./

RUN pip install --no-cache-dir pytest pylint

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/app.py ./

CMD ["python3", "app.py"] 