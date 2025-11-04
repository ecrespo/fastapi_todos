# Contributing Guide

## Pre-commit Hooks

Este proyecto usa pre-commit hooks para mantener la calidad del código. Los hooks se ejecutan automáticamente antes de cada commit.

### Instalación

Los hooks ya están instalados si ejecutaste `uv sync --dev`. Si no, ejecuta:

```bash
uv run pre-commit install
```

### Herramientas Configuradas

#### Activas por defecto:

1. **Black** - Formateador de código Python
   - Formato consistente y automático
   - Línea máxima: 120 caracteres
   - Target: Python 3.12

2. **Ruff** - Linter rápido para Python
   - Reemplaza flake8, isort, pyupgrade y más
   - Arregla automáticamente muchos problemas
   - Verifica imports, simplificación de código, etc.

3. **Pre-commit hooks** - Validaciones generales
   - Trailing whitespace
   - End of file fixer
   - YAML/TOML/JSON validation
   - Detección de claves privadas
   - Prevención de archivos grandes

#### Opcionales (comentadas):

- **MyPy** - Verificación de tipos estáticos
- **Bandit** - Análisis de seguridad
- **Safety** - Verificación de vulnerabilidades en dependencias

Para habilitarlas, descomenta las secciones correspondientes en `.pre-commit-config.yaml`.

### Ejecutar Manualmente

```bash
# Ejecutar todos los hooks en todos los archivos
uv run pre-commit run --all-files

# Ejecutar un hook específico
uv run pre-commit run black --all-files
uv run pre-commit run ruff --all-files

# Actualizar versiones de los hooks
uv run pre-commit autoupdate
```

### Bypass Pre-commit (usar con precaución)

```bash
# Saltar pre-commit en un commit específico
git commit --no-verify -m "mensaje"
```

### Comandos de Desarrollo

#### Formateo y Linting

```bash
# Formatear código con Black
uv run black app/ tests/

# Ejecutar Ruff
uv run ruff check app/ tests/
uv run ruff check --fix app/ tests/  # Auto-fix

# Type checking con MyPy
uv run mypy app/
```

#### Tests

```bash
# Ejecutar todos los tests
uv run pytest

# Tests sin coverage
uv run pytest --no-cov

# Tests específicos
uv run pytest tests/test_auth_login.py

# Tests con modo verbose
uv run pytest -v

# Tests excluyendo trio
uv run pytest -k "not trio"
```

#### Otros Comandos

```bash
# Instalar dependencias de desarrollo
uv sync --dev

# Ejecutar servidor de desarrollo
uv run uvicorn app.main:app --reload

# Crear nueva migración de Alembic
uv run alembic revision -m "descripción"

# Aplicar migraciones
uv run alembic upgrade head
```

## Workflow de Desarrollo

1. **Crear rama** para tu feature/fix:
   ```bash
   git checkout -b feature/mi-feature
   ```

2. **Desarrollar** tu código siguiendo las convenciones

3. **Ejecutar tests**:
   ```bash
   uv run pytest
   ```

4. **Commit** (pre-commit se ejecuta automáticamente):
   ```bash
   git add .
   git commit -m "feat: descripción del cambio"
   ```

5. **Push** y crear Pull Request:
   ```bash
   git push origin feature/mi-feature
   ```

## Convenciones de Código

- **Línea máxima**: 120 caracteres
- **Formato**: Black (automático via pre-commit)
- **Imports**: Ordenados por Ruff (automático)
- **Type hints**: Usar cuando sea posible
- **Docstrings**: Estilo Google para funciones públicas
- **Tests**: Requeridos para nuevas funcionalidades

## Estructura de Commits

Usamos conventional commits:

- `feat:` - Nueva funcionalidad
- `fix:` - Corrección de bugs
- `docs:` - Cambios en documentación
- `style:` - Formateo de código
- `refactor:` - Refactorización de código
- `test:` - Adición o corrección de tests
- `chore:` - Mantenimiento (dependencias, config, etc.)

Ejemplo:
```bash
git commit -m "feat: add JWT refresh token endpoint"
git commit -m "fix: resolve token expiration validation"
git commit -m "docs: update API documentation"
```

## Solución de Problemas

### Pre-commit falla en install

```bash
# Reinstalar pre-commit
uv sync --dev
uv run pre-commit install --install-hooks
```

### Black/Ruff fallan

```bash
# Ejecutar manualmente para ver detalles
uv run black --check app/
uv run ruff check app/
```

### Tests fallan después de formateo

```bash
# Los formateadores no deberían romper tests
# Ejecutar tests para ver el error específico
uv run pytest -v
```

## Recursos

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
