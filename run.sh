#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting Inverter Data Logger Add-on..."

export SERIAL_INTERFACE=$(bashio::config 'serial_interface')
export MODBUS_ID=$(bashio::config 'modbus_id')
export MQTT_UPDATE_INTERVAL=$(bashio::config 'mqtt_update_interval')
export ENABLE_HA_DISCOVERY_CONFIG=$(bashio::config 'enable_ha_discovery')
export INVERT_HA_DIS_CHARGE_MEASUREMENTS=$(bashio::config 'invert_ha_dis_charge_measurements')
export HA_DISCOVERY_PREFIX=$(bashio::config 'ha_discovery_prefix')
export LOGGING_LEVEL=$(bashio::config 'logging_level')
export MQTT_TOPIC=$(bashio::config 'mqtt_topic')

if bashio::services.available "mqtt"; then
    export MQTT_HOST=$(bashio::services mqtt "host")
    export MQTT_PORT=$(bashio::services mqtt "port")
    export MQTT_USERNAME=$(bashio::services mqtt "username")
    export MQTT_PASSWORD=$(bashio::services mqtt "password")
    bashio::log.info "MQTT service configured: ${MQTT_HOST}:${MQTT_PORT}"
else
    bashio::log.error "MQTT service not available!"
    exit 1
fi

bashio::log.info "Using local serial interface: ${SERIAL_INTERFACE}"

# Debug-Ausgabe wenn gewünscht
if [[ "${LOGGING_LEVEL}" == "debug" ]]; then
    bashio::log.debug "Configuration loaded:"
    bashio::log.debug "SERIAL_INTERFACE: ${SERIAL_INTERFACE}"
    bashio::log.debug "MODBUS_ID: ${MODBUS_ID}"
    bashio::log.debug "MQTT_UPDATE_INTERVAL: ${MQTT_UPDATE_INTERVAL}"
    bashio::log.debug "ENABLE_HA_DISCOVERY_CONFIG: ${ENABLE_HA_DISCOVERY_CONFIG}"
    bashio::log.debug "INVERT_HA_DIS_CHARGE_MEASUREMENTS: ${INVERT_HA_DIS_CHARGE_MEASUREMENTS}"
    bashio::log.debug "HA_DISCOVERY_PREFIX: ${HA_DISCOVERY_PREFIX}"
    bashio::log.debug "LOGGING_LEVEL: ${LOGGING_LEVEL}"
    bashio::log.debug "MQTT_TOPIC: ${MQTT_TOPIC}"
fi

bashio::log.info "Starting Inverter Data Logger..."

# Python-Script mit ENV-Variablen starten
exec python3 -u /usr/src/app/fetch_inverter_data.py