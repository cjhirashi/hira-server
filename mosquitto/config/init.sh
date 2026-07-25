#!/bin/sh
# Genera el archivo passwd de Mosquitto desde variables de entorno
# y arranca el broker. Se ejecuta como entrypoint del contenedor.

set -e

PASSWD_FILE="/mosquitto/config/passwd"

if [ -z "${MQTT_USER}" ] || [ -z "${MQTT_PASSWORD}" ]; then
  echo "ERROR: MQTT_USER y MQTT_PASSWORD son obligatorios" >&2
  exit 1
fi

# Crear o regenerar el archivo de contraseñas
mosquitto_passwd -b -c "${PASSWD_FILE}" "${MQTT_USER}" "${MQTT_PASSWORD}"
chmod 600 "${PASSWD_FILE}"

echo "Mosquitto: archivo passwd generado para usuario '${MQTT_USER}'"

exec mosquitto -c /mosquitto/config/mosquitto.conf
