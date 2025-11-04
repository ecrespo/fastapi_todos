# Logging Documentation

Este proyecto usa **structlog** para logging estructurado con salida Rich en consola y JSON en archivos.

## Características

- **Structured Logging**: Logs con contexto estructurado para mejor debugging
- **Rich Console Output**: Salida colorizada y formateada en consola
- **JSON File Output**: Logs en formato JSON para parsing automático
- **Context Binding**: Agregar contexto persistente a logs
- **Exception Formatting**: Tracebacks bonitos con Rich

## Uso Básico

### Importar el Logger

```python
from app.shared.LoggerSingleton import logger

# O importar la función para obtener una nueva instancia
from app.shared.LoggerSingleton import get_logger

# Obtener logger con nombre específico
import structlog
logger = structlog.get_logger("my_module")
```

### Logging Simple

```python
# Logs básicos
logger.info("User logged in", user_id=123, username="john")
logger.warning("High memory usage", memory_mb=950, threshold_mb=1000)
logger.error("Database connection failed", host="localhost", port=5432)
logger.debug("Cache hit", key="user:123", ttl=300)
```

### Logging con Contexto

```python
# Bind context que persiste en todos los logs subsecuentes
log = logger.bind(request_id="abc-123", user_id=456)

log.info("Processing request")  # Incluye request_id y user_id
log.info("Request completed", duration_ms=150)  # También incluye request_id y user_id
```

### Logging con Excepciones

```python
try:
    # Código que puede fallar
    result = divide(10, 0)
except Exception as e:
    logger.error(
        "Operation failed",
        operation="divide",
        exc_info=True  # Incluye traceback
    )
```

### Logging Estructurado

```python
# En lugar de strings formateados:
logger.info(f"User {user_id} created order {order_id}")

# Usar contexto estructurado:
logger.info(
    "order_created",
    user_id=user_id,
    order_id=order_id,
    items_count=5,
    total_amount=99.99,
    currency="USD"
)
```

## Ejemplos por Caso de Uso

### API Request Logging

```python
from app.shared.LoggerSingleton import logger

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    log = logger.bind(user_id=user_id, endpoint="/api/users")

    log.info("fetching_user_data")

    try:
        user = await db.get_user(user_id)
        log.info("user_data_fetched", username=user.username)
        return user
    except UserNotFound:
        log.warning("user_not_found")
        raise HTTPException(404)
```

### Database Operations

```python
async def create_todo(todo: TodoCreate, user_id: int):
    log = logger.bind(user_id=user_id, operation="create_todo")

    log.info("creating_todo", title=todo.title)

    async with get_session() as session:
        todo_obj = TodoORM(**todo.dict(), user_id=user_id)
        session.add(todo_obj)

        try:
            await session.commit()
            log.info("todo_created", todo_id=todo_obj.id)
            return todo_obj
        except IntegrityError as e:
            log.error("todo_creation_failed", error=str(e), exc_info=True)
            raise
```

### Background Tasks

```python
@celery_app.task
def process_email(email_id: str):
    log = logger.bind(email_id=email_id, task="process_email")

    log.info("task_started")

    try:
        email = fetch_email(email_id)
        log.info("email_fetched", recipient=email.to)

        send_email(email)
        log.info("email_sent")

    except Exception as e:
        log.error("task_failed", error=str(e), exc_info=True)
        raise
```

### Performance Monitoring

```python
import time

def expensive_operation(data_size: int):
    log = logger.bind(operation="expensive_operation", data_size=data_size)

    start = time.perf_counter()
    log.info("operation_started")

    # Operación costosa
    result = process_data(data_size)

    duration_ms = (time.perf_counter() - start) * 1000
    log.info(
        "operation_completed",
        duration_ms=round(duration_ms, 2),
        result_size=len(result)
    )

    return result
```

## Formato de Salida

### Console (Rich)

```
2025-11-04 16:30:15 [info     ] http_request_completed method=GET path=/api/todos/ status_code=200 duration_ms=12.45
```

### File (JSON)

```json
{
  "event": "http_request_completed",
  "level": "info",
  "logger": "FastAPI Todos",
  "timestamp": "2025-11-04T16:30:15.123456Z",
  "method": "GET",
  "path": "/api/todos/",
  "status_code": 200,
  "duration_ms": 12.45,
  "client_host": "127.0.0.1",
  "request_id": ""
}
```

## Configuración

La configuración del logger está en `app/shared/LoggerSingleton.py`:

- **Directorio de logs**: `logs/`
- **Formato de archivo**: `YYYY-MM-DD.log`
- **Nivel de log**: `INFO`
- **Procesadores activos**:
  - `TimeStamper`: Timestamps ISO 8601
  - `add_log_level`: Nivel de log
  - `add_logger_name`: Nombre del logger
  - `format_exc_info`: Formateo de excepciones
  - `JSONRenderer`: Salida JSON para archivos
  - `ConsoleRenderer`: Salida colorizada para consola

## Best Practices

### ✅ Hacer

```python
# Usar nombres descriptivos de eventos
logger.info("user_registration_completed", user_id=123)

# Agregar contexto relevante
logger.info("payment_processed", amount=99.99, currency="USD", method="credit_card")

# Usar bind para contexto persistente
log = logger.bind(request_id=req_id)

# Incluir exc_info para errores
logger.error("database_error", exc_info=True)

# Usar tipos primitivos (str, int, float, bool)
logger.info("metric_recorded", value=42, metric="latency_ms")
```

### ❌ Evitar

```python
# NO usar f-strings
logger.info(f"User {user_id} logged in")  # ❌

# NO incluir datos sensibles
logger.info("login", password=pwd)  # ❌

# NO usar objetos complejos
logger.info("user_data", user=user_object)  # ❌

# NO hacer logging excesivo en loops
for item in items:
    logger.info("processing", item=item)  # ❌
```

## Análisis de Logs

### Buscar logs por campo (jq)

```bash
# Filtrar por evento específico
cat logs/2025-11-04.log | jq 'select(.event == "http_request_completed")'

# Filtrar por status code
cat logs/2025-11-04.log | jq 'select(.status_code >= 400)'

# Calcular duración promedio
cat logs/2025-11-04.log | jq -s 'map(select(.duration_ms)) | add / length'

# Contar errores por tipo
cat logs/2025-11-04.log | jq -s 'group_by(.event) | map({event: .[0].event, count: length})'
```

### Buscar logs por texto (grep)

```bash
# Buscar por método HTTP
grep '"method":"POST"' logs/2025-11-04.log

# Buscar errores
grep '"level":"error"' logs/2025-11-04.log

# Buscar por user_id
grep '"user_id":123' logs/2025-11-04.log
```

## Troubleshooting

### Logs no aparecen

1. Verificar que el directorio `logs/` existe
2. Verificar permisos de escritura
3. Verificar nivel de log en configuración

### Formato incorrecto

1. Verificar que structlog está instalado: `uv list | grep structlog`
2. Re-importar logger: `from app.shared.LoggerSingleton import logger`

### Performance issues

Si el logging afecta el rendimiento:

1. Subir nivel de log a WARNING en producción
2. Reducir procesadores en `setup_structlog()`
3. Usar logging asíncrono (ver structlog docs)

## Referencias

- [structlog Documentation](https://www.structlog.org/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Twelve-Factor App: Logs](https://12factor.net/logs)
