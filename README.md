# Backup Automático con Docker + S3 + Telegram

Sistema automatizado de respaldo de bases de datos MySQL y directorios adicionales, con subida a AWS S3 y notificaciones por Telegram.

## Características

- ✅ Backup de múltiples bases de datos MySQL
- ✅ Compresión de directorios adicionales (uploads, etc.)
- ✅ Subida automática a AWS S3
- ✅ Notificaciones por Telegram
- ✅ Contenedorizado con Docker (Python 3.11)
- ✅ Soporte para MySQL 8.0 con `caching_sha2_password`
- ✅ Limpieza automática de archivos temporales

## Requisitos

- Docker y Docker Compose
- Cuenta AWS con acceso a S3
- Bot de Telegram (opcional, para notificaciones)

## Instalación

### 1. Clonar o copiar el proyecto

```bash
cd /opt  # o tu directorio preferido
git clone <tu-repo> python-script-for-do-backups
cd python-script-for-do-backups
```

### 2. Configurar credenciales

```bash
cp config.cfg.example config.cfg
nano config.cfg
```

Ejemplo de configuración:

```
databases :
[
    {
        host     : 'localhost',
        user     : 'root',
        password : 'tu-password',
        port     : 3306,
        database : 'produccion'
    },
    {
        host     : '192.168.1.100',
        user     : 'backup_user',
        password : 'otro-password',
        port     : 3306,
        database : 'clientes'
    }
],
amazon : {
    bucket : 'mi-bucket-backups',
    access_key : 'AKIAXXXXXXXXXXXXXXXX',
    secret_access : 'tu-secret-key-aqui'
},
telegram : {
    bot_token : '123456789:ABCdefGHIjklMNOpqrsTUVwxyz',
    chat_id   : '987654321',
    message   : '✅ Backup completado exitosamente\n📅 Fecha: {timestamp}\n📦 Archivo: {filename}\n💾 Bases de datos: {databases}'
},
extra_directories :
[
    {
        path : '/var/www/html/uploads',
        name : 'uploads'
    }
]
```

#### Variables disponibles para el mensaje de Telegram:

- `{timestamp}` - Fecha y hora del backup
- `{filename}` - Nombre del archivo generado
- `{databases}` - Lista de bases de datos respaldadas

### 3. Obtener credenciales de Telegram

#### Crear un bot:
1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Envía `/newbot` y sigue las instrucciones
3. Copia el **token** que te proporciona (ej: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Obtener tu Chat ID:
1. Habla con [@userinfobot](https://t.me/userinfobot) en Telegram
2. Te responderá con tu **Chat ID** (ej: `987654321`)

O para un grupo:
1. Agrega tu bot al grupo
2. Envía un mensaje en el grupo
3. Visita: `https://api.telegram.org/bot<TU_BOT_TOKEN>/getUpdates`
4. Busca el `"chat":{"id":-XXXXXXXXX}` en la respuesta

### 4. Configurar permisos

```bash
chmod 600 config.cfg  # Solo el dueño puede leer
chmod +x run-backup.sh
```

### 5. Probar manualmente

```bash
# Construir imagen Docker
docker compose build backup

# Ejecutar backup
docker compose run --rm backup
```

## Automatización con Cron

### 1. Editar crontab

```bash
crontab -e
```

### 2. Agregar entrada

```bash
# Backup diario a las 3:00 AM
0 3 * * * /opt/python-script-for-do-backups/run-backup.sh

# Backup cada 6 horas
0 */6 * * * /opt/python-script-for-do-backups/run-backup.sh

# Backup semanal (domingos a las 2 AM)
0 2 * * 0 /opt/python-script-for-do-backups/run-backup.sh
```

### 3. Ver logs

```bash
# Ver log de hoy
tail -f /opt/python-script-for-do-backups/logs/backup_$(date +%Y-%m-%d).log

# Ver todos los logs
ls -lh /opt/python-script-for-do-backups/logs/

# Buscar errores
grep ERROR /opt/python-script-for-do-backups/logs/*.log
```

## Estructura del proyecto

```
python-script-for-do-backups/
├── app.py                 # Script principal de backup
├── Dockerfile             # Imagen Docker con Python 3.11 + MySQL client 8.0
├── docker-compose.yml     # Configuración de Docker Compose
├── requirements.txt       # Dependencias Python (boto3)
├── run-backup.sh          # Script wrapper para cron con logging
├── config.cfg             # Configuración (credenciales, NO incluir en git)
├── config.cfg.example     # Plantilla de configuración
├── backup/                # Directorio temporal (se limpia automáticamente)
│   └── .gitkeep
└── logs/                  # Logs de ejecución (creado automáticamente)
```

## Ejemplo de notificación en Telegram

Cuando el backup se complete, recibirás un mensaje como:

```
✅ Backup completado exitosamente
📅 Fecha: 2025-12-14 03:00:15
📦 Archivo: backup_2025-12-14-03.00.zip
💾 Bases de datos: produccion, clientes
```

Puedes personalizar este mensaje editando el campo `message` en `config.cfg`.

## Troubleshooting

### Error: "Cannot connect to MySQL"
- Verifica que el host MySQL sea accesible desde el contenedor
- Si MySQL está en `localhost`, usa `host.docker.internal` (Mac/Windows) o la IP del host

### Error: "Access Denied for S3"
- Verifica tus credenciales AWS
- Asegúrate de que el bucket existe y tienes permisos de escritura

### No recibo notificaciones de Telegram
- Verifica el `bot_token` y `chat_id`
- Asegúrate de haber iniciado una conversación con el bot primero
- Revisa los logs para ver mensajes de error

### El backup crece indefinidamente
- Ya está solucionado en la versión actual
- Los archivos temporales se limpian después de cada ejecución

## Seguridad

- **NUNCA** subas `config.cfg` a un repositorio público
- Usa variables de entorno para producción si lo prefieres
- Limita los permisos del archivo de configuración: `chmod 600 config.cfg`
- Rota tus credenciales AWS periódicamente

## Licencia

MIT

