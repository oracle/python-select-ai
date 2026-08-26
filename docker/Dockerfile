FROM oraclelinux:10-slim

ENV PATH=/opt/venv/bin:$PATH

RUN microdnf update -y \
    && microdnf install -y python3 python3-pip ca-certificates unzip \
    && microdnf clean all

WORKDIR /app

COPY pyproject.toml README.md LICENSE.txt ./
COPY src ./src

RUN python3 -m venv /opt/venv \
    && python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir '.[a2a]'

COPY docker/a2a-entrypoint.sh /app/docker/a2a-entrypoint.sh

RUN chmod 0555 /app/docker/a2a-entrypoint.sh

ENTRYPOINT ["select-ai"]
