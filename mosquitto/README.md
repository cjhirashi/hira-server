# mosquitto/

Broker MQTT Mosquitto 2.0 con autenticación obligatoria (V-01).

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `config/mosquitto.conf` | Configuración del broker: autenticación, persistencia, logs |
| `config/init.sh` | Script de entrypoint: genera `passwd` desde env vars y arranca Mosquitto |

## Configuración de seguridad

`allow_anonymous false` — ninguna conexión sin credenciales es aceptada.

Las credenciales vienen de variables de entorno:

```env
MQTT_USER=hira
MQTT_PASSWORD=<contraseña segura>
```

## Cómo rotar las credenciales

1. Actualizar `MQTT_USER` y `MQTT_PASSWORD` en `.env`
2. Reiniciar el contenedor — `init.sh` regenera el archivo `passwd` automáticamente:

```bash
docker compose restart mosquitto
```

## Verificar que el broker rechaza conexiones anónimas

```bash
# Debe fallar con "Connection Refused: not authorised"
mosquitto_pub -h localhost -p 1883 -t test -m hello

# Debe funcionar con credenciales correctas
mosquitto_pub -h localhost -p 1883 -u $MQTT_USER -P $MQTT_PASSWORD -t test -m hello
```

## Estructura de volúmenes

| Volumen local | Dentro del contenedor | Propósito |
|---------------|----------------------|-----------|
| `mosquitto/config/` | `/mosquitto/config/` | Configuración y archivo passwd |
| `mosquitto/data/` | `/mosquitto/data/` | Persistencia de mensajes |
| `mosquitto/log/` | `/mosquitto/log/` | Logs del broker |
