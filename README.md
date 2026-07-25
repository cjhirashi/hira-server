# Hira Server

Plataforma SCADA moderna para integradores de automatización de edificios (HVAC, BMS).

## Qué hace

Hira permite diseñar proyectos completos offline con simuladores de dispositivos y comisionarlos en campo conectando los mismos puntos a hardware real. El integrador diseña en su PC (modo Studio), valida con simuladores, exporta un paquete `.hira` y lo importa en el servidor del cliente (modo Server).

## Stack

| Servicio | Imagen |
|----------|--------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy async |
| Frontend | Node 20 · React · TypeScript · Vite |
| Base de datos | TimescaleDB (PostgreSQL 16) |
| Cache / broker de tareas | Redis 7.4 |
| MQTT | Mosquitto 2.0 |
| Reverse proxy | Nginx 1.27 |

## Levantar en desarrollo

```bash
# 1. Copiar variables de entorno y completar los valores
cp .env.example .env

# 2. Levantar con hot-reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Servicios disponibles:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Nginx (entrada principal): http://localhost:80

## Estructura de carpetas

```
hira-server/
├── backend/          → FastAPI, lógica de negocio, modelos, workers
├── frontend/         → React + TypeScript (Vite)
├── nginx/            → Configuración del reverse proxy
├── mosquitto/        → Configuración del broker MQTT
├── docs/             → Contrato de API (openapi.yaml)
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env.example
```

## Migraciones de base de datos

```bash
# Dentro del contenedor backend
docker compose exec backend alembic upgrade head
```
