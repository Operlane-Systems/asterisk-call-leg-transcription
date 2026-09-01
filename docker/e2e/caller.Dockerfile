FROM python:3.12-slim

WORKDIR /app
RUN python -m pip install --no-cache-dir pyVoIP==1.6.8 "requests>=2.31,<3"
COPY docker/e2e/caller.py /app/caller.py
CMD ["python", "/app/caller.py"]
