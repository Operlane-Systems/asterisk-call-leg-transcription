FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .
COPY docker/e2e/transcriber.py /app/transcriber.py
CMD ["python", "/app/transcriber.py"]
