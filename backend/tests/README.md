# tests/

## Propósito
Tests unitarios del backend Hira. Verifican la lógica de negocio aislada de infraestructura externa (BD, Redis, brokers).

## Archivos
- `test_security.py` — pruebas de bcrypt (hash/verify) y JWT (crear, decodificar, tokens inválidos)

## Cómo funciona
Los tests se ejecutan con `pytest` desde la carpeta `backend/`. No requieren Docker ni servicios externos — las funciones de `core/security.py` operan en memoria.

```bash
cd backend
pytest tests/ -v
```

## Dependencias
- `core/security.py` — funciones hash_password, verify_password, create_access_token, decode_token
- `core/config.py` — settings (SECRET_KEY leída del entorno o `.env`)
