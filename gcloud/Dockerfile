FROM oraclelinux:10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

RUN microdnf install -y python3 python3-pip ca-certificates \
    && microdnf clean all

WORKDIR /app

COPY pyproject.toml README.md LICENSE.txt ./
COPY src ./src

RUN python3 -m venv /opt/venv \
    && python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir '.[a2a]'

COPY gcloud/run-a2a-server.sh /app/gcloud/run-a2a-server.sh

RUN chmod 0555 /app/gcloud/run-a2a-server.sh

EXPOSE 8080

ENTRYPOINT ["/app/gcloud/run-a2a-server.sh"]
