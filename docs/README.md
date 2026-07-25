# docs/

Documentación técnica del proyecto Hira.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `openapi.yaml` | Contrato de la API REST — se define antes de implementar cualquier router |

## Principio contract-first

**El contrato se escribe antes del código.**

Flujo obligatorio por sprint:
1. Añadir los endpoints del sprint a `openapi.yaml`
2. Validar coherencia del contrato
3. Implementar el router siguiendo el contrato — nunca al revés

Si un endpoint no está en `openapi.yaml`, no existe todavía.

## Validar el YAML

```bash
# Con swagger-cli (Node)
npx swagger-cli validate docs/openapi.yaml

# Con openapi-spec-validator (Python)
pip install openapi-spec-validator
python -m openapi_spec_validator docs/openapi.yaml
```

## Ver la documentación interactiva

Con el backend corriendo, abrir http://localhost:8000/docs (Swagger UI) o http://localhost:8000/redoc.
