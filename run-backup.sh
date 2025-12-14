#!/bin/bash
#
# Script wrapper para ejecutar backup desde cron
# Guarda logs y maneja errores

set -e

# Directorio del proyecto
PROJECT_DIR="/opt/python-script-for-do-backups"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/backup_$(date +%Y-%m-%d).log"

# Crear directorio de logs si no existe
mkdir -p "${LOG_DIR}"

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Inicio
log "===== Iniciando backup ====="

# Cambiar al directorio del proyecto
cd "${PROJECT_DIR}" || {
    log "ERROR: No se puede acceder al directorio ${PROJECT_DIR}"
    exit 1
}

# Ejecutar backup
if docker compose run --rm backup >> "${LOG_FILE}" 2>&1; then
    log "✓ Backup completado exitosamente"
    exit 0
else
    log "✗ ERROR: Backup falló con código $?"
    exit 1
fi

