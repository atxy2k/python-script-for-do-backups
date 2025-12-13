FROM python:3.11-slim

ARG MYSQL_VERSION=8.0.40
ARG TARGETARCH
ENV DEBIAN_FRONTEND=noninteractive \
    MYSQL_PLUGIN_DIR=/usr/lib/mysql/plugin \
    MYSQL_LIB_DIR=/usr/local/mysql/lib \
    LD_LIBRARY_PATH=/usr/local/mysql/lib:$LD_LIBRARY_PATH

WORKDIR /app

# Install utilities and download the official MySQL client tarball that includes
# mysqldump with caching_sha2_password support for both amd64 and arm64 builds.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates wget xz-utils; \
    case "${TARGETARCH}" in \
        amd64) MYSQL_TARBALL="mysql-${MYSQL_VERSION}-linux-glibc2.28-x86_64.tar.xz" ;; \
        arm64) MYSQL_TARBALL="mysql-${MYSQL_VERSION}-linux-glibc2.28-aarch64.tar.xz" ;; \
        *) echo "Unsupported TARGETARCH=${TARGETARCH}" && exit 1 ;; \
    esac; \
    wget -q "https://dev.mysql.com/get/Downloads/MySQL-8.0/${MYSQL_TARBALL}"; \
    tar -xJf "${MYSQL_TARBALL}"; \
    MYSQL_DIR=""; \
    for item in mysql-${MYSQL_VERSION}-linux-glibc2.28-*; do \
        if [ -d "${item}" ]; then MYSQL_DIR="${item}"; break; fi; \
    done; \
    if [ -z "${MYSQL_DIR}" ]; then echo "MySQL directory not found" && exit 1; fi; \
    cp "${MYSQL_DIR}/bin/mysqldump" /usr/local/bin/; \
    cp "${MYSQL_DIR}/bin/mysql" /usr/local/bin/; \
    mkdir -p "${MYSQL_LIB_DIR}"; \
    cp -r "${MYSQL_DIR}/lib/." "${MYSQL_LIB_DIR}/"; \
    mkdir -p "${MYSQL_PLUGIN_DIR}"; \
    cp -r "${MYSQL_DIR}/lib/plugin/." "${MYSQL_PLUGIN_DIR}/"; \
    rm -rf "${MYSQL_DIR}" "${MYSQL_TARBALL}"; \
    apt-get purge -y --auto-remove wget xz-utils; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "app.py"]

