"""
Handle creation and publishing of auto discovery configs for Home Assistant.
"""
import json
import logging
import copy
from typing import Optional, Dict, Any, List

logger = logging.getLogger("Inverter.Discovery")

# Base sensor template
BASE_SENSOR = {
    "name": "Solar Inverter Data Logger",
    "uniq_id": "",  # unique_id
    "obj_id": "",  # object_id
    "stat_t": "",  # state_topic
    "val_tpl": "",  # value_template
    "avty": [],  # availability
    "dev": {}  # device
}

DEVICE_BASE_CONFIG = {
    "hw": "11k",  # hw_version
    "sw": "0.0",  # sw_version
    "mdl": "Solar Inverter 11kW",  # model
    "mf": "No Name"  # manufacturer
}

# Telemetry sensor templates
TELEMETRY_SENSOR_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "Battery Voltage",
        "value_template_key": "battery_voltage",
        "device_class": "voltage",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "flash-triangle-outline"
    },
    {
        "name": "Battery Current",
        "value_template_key": "battery_current",
        "device_class": "current",
        "unit_of_measurement": "A",
        "suggested_display_precision": 1,
        "icon": "mdi:current-ac"
    },
    {
        "name": "Battery Power",
        "value_template_key": "battery_power",
        "device_class": "power",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "Battery State of Charge",
        "value_template_key": "battery_soc",
        "device_class": "battery",
        "unit_of_measurement": "%",
        "suggested_display_precision": 0,
        "icon": "mdi:battery-charging-50"
    },
    {
        "name": "Grid Input Voltage",
        "value_template_key": "grid_input_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "Grid Line Voltage",
        "value_template_key": "grid_line_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "Grid Power",
        "value_template_key": "grid_power",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "L1 Voltage",
        "value_template_key": "l1_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "L1 Current",
        "value_template_key": "l1_current",
        "device_class": "current",
        "state_class": "measurement",
        "unit_of_measurement": "A",
        "suggested_display_precision": 1,
        "icon": "mdi:current-ac"
    },
    {
        "name": "L1 Power",
        "value_template_key": "l1_power",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "L1 Apparent Power",
        "value_template_key": "l1_apparent_power",
        "device_class": "apparent_power",
        "state_class": "measurement",
        "unit_of_measurement": "VA",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "L1 Load",
        "value_template_key": "l1_load",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "suggested_display_precision": 0,
        "icon": "mdi:reload"
    },
    {
        "name": "L2 Voltage",
        "value_template_key": "l2_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "L2 Current",
        "value_template_key": "l2_current",
        "device_class": "current",
        "state_class": "measurement",
        "unit_of_measurement": "A",
        "suggested_display_precision": 1,
        "icon": "mdi:current-ac"
    },
    {
        "name": "L2 Power",
        "value_template_key": "l2_power",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "L2 Apparent Power",
        "value_template_key": "l2_apparent_power",
        "device_class": "apparent_power",
        "state_class": "measurement",
        "unit_of_measurement": "VA",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "L2 Load",
        "value_template_key": "l2_load",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "suggested_display_precision": 0,
        "icon": "mdi:reload"
    },
    {
        "name": "Total Output Power",
        "value_template_key": "total_output_power",
        "device_class": "apparent_power",
        "state_class": "measurement",
        "unit_of_measurement": "VA",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "Total Output Load",
        "value_template_key": "total_output_load",
        "device_class": "battery",
        "state_class": "measurement",
        "unit_of_measurement": "%",
        "suggested_display_precision": 0,
        "icon": "mdi:reload"
    },
    {
        "name": "PV1 Voltage",
        "value_template_key": "pv1_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "PV1 Current",
        "value_template_key": "pv1_current",
        "device_class": "current",
        "state_class": "measurement",
        "unit_of_measurement": "A",
        "suggested_display_precision": 1,
        "icon": "mdi:current-ac"
    },
    {
        "name": "PV1 Power",
        "value_template_key": "pv1_power",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "PV2 Voltage",
        "value_template_key": "pv2_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "PV2 Current",
        "value_template_key": "pv2_current",
        "device_class": "current",
        "state_class": "measurement",
        "unit_of_measurement": "A",
        "suggested_display_precision": 1,
        "icon": "mdi:current-ac"
    },
    {
        "name": "PV2 Power",
        "value_template_key": "pv2_power",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "Total PV Power",
        "value_template_key": "total_pv_power",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "Year",
        "value_template_key": "year",
        "icon": "mdi:calendar-month"
    },
    {
        "name": "Month",
        "value_template_key": "month",
        "icon": "mdi:calendar-month"
    },
    {
        "name": "Day",
        "value_template_key": "day",
        "icon": "mdi:calendar-today"
    },
    {
        "name": "Hour",
        "value_template_key": "hour",
        "icon": "mdi:clock-outline"
    },
    {
        "name": "Minute",
        "value_template_key": "minute",
        "icon": "mdi:clock-outline"
    },
    {
        "name": "Second",
        "value_template_key": "second",
        "icon": "mdi:clock-outline"
    },
    {
        "name": "Energy Today",
        "value_template_key": "energy_today",
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit_of_measurement": "kWh",
        "suggested_display_precision": 2,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "Energy Year",
        "value_template_key": "energy_year",
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit_of_measurement": "kWh",
        "suggested_display_precision": 2,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "Voltage Configuration",
        "value_template_key": "voltage_conf",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "L2 Power Configuration",
        "value_template_key": "l2_power_conf",
        "device_class": "power",
        "state_class": "measurement",
        "unit_of_measurement": "W",
        "suggested_display_precision": 0,
        "icon": "mdi:flash-outline"
    },
    {
        "name": "Frequency Configuration",
        "value_template_key": "frequency_conf",
        "device_class": "frequency",
        "state_class": "measurement",
        "unit_of_measurement": "Hz",
        "suggested_display_precision": 0,
        "icon": "mdi:waveform"
    },
    {
        "name": "Floating Charging Voltage",
        "value_template_key": "floating_charging_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "Max Total Charging Current",
        "value_template_key": "max_total_charging_current",
        "device_class": "current",
        "state_class": "measurement",
        "unit_of_measurement": "A",
        "suggested_display_precision": 1,
        "icon": "mdi:current-ac"
    },
    {
        "name": "Max Grid Charging Current",
        "value_template_key": "max_grid_charging_current",
        "device_class": "current",
        "state_class": "measurement",
        "unit_of_measurement": "A",
        "suggested_display_precision": 1,
        "icon": "mdi:current-ac"
    },
    {
        "name": "SOC Point Back to Utility",
        "value_template_key": "soc_point_back_to_utility",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "L1 Cutoff Voltage",
        "value_template_key": "l1_cutoff_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    },
    {
        "name": "L2 Cutoff Voltage",
        "value_template_key": "l2_cutoff_voltage",
        "device_class": "voltage",
        "state_class": "measurement",
        "unit_of_measurement": "V",
        "suggested_display_precision": 1,
        "icon": "mdi:flash-triangle-outline"
    }
]



class AutoDiscoveryConfig:

    """Handle Home Assistant auto-discovery configuration creation and publishing."""

    def __init__(self, mqtt_topic: str, discovery_prefix: str, invert_ha_dis_charge_measurements: bool, mqtt_client) -> None:
        self.mqtt_topic = mqtt_topic
        self.discovery_prefix = discovery_prefix
        self.invert_ha_dis_charge_measurements = invert_ha_dis_charge_measurements
        self.mqtt_client = mqtt_client
        self._device_info_published = set()


    # -------------------------------------------------------------------------

    def _add_device_info(self, entity: Dict[str, Any], modbus_id: int) -> None:
        if modbus_id not in self._device_info_published:
            entity["dev"] = {**DEVICE_BASE_CONFIG}
            entity["dev"]["name"] = f"Inverter-{modbus_id}"
            entity["dev"]["ids"] = f"Inverter_{modbus_id}"
            if modbus_id > 0:
                entity["dev"]["via_device"] = "inverter_0"
            self._device_info_published.add(modbus_id)
        else:
            entity["dev"] = {"ids": f"inverter_{modbus_id}"}
            if modbus_id > 0:
                entity["dev"]["via_device"] = "inverter_0"

    def _build_availability(self, modbus_id: int) -> List[Dict[str, str]]:
        return [
            {"t": f"{self.mqtt_topic}/availability"},
            {"t": f"{self.mqtt_topic}/inverter-{modbus_id}/availability"},
        ]

    def _build_base_entity(
        self,
        modbus_id: int,
        name: str,
        value_template: str,
        uniq_obj_id: str,
        state_topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        entity = copy.deepcopy(BASE_SENSOR)

        self._add_device_info(entity, modbus_id)

        entity["name"] = name
        entity["avty"] = self._build_availability(modbus_id)
        entity["avty_mode"] = "all"
        entity["stat_t"] = state_topic or f"{self.mqtt_topic}/inverter-{modbus_id}/sensors"
        entity["val_tpl"] = value_template
        entity["uniq_id"] = uniq_obj_id
        entity["obj_id"] = uniq_obj_id

        return entity

    def _apply_optional_fields(self, entity: Dict[str, Any], optional_fields: Dict[str, Any]) -> None:
        for key, value in optional_fields.items():
            if value is not None:
                entity[key] = value

    def _publish_config(
        self,
        entity_type: str,
        modbus_id: int,
        name: str,
        value_template_key: str,
        config: Dict[str, Any],
    ) -> None:

        discovery_topic = f"{self.discovery_prefix}/{entity_type}/inverter-{modbus_id}/{value_template_key}/config"

        try:
            self.mqtt_client.publish(
                discovery_topic,
                json.dumps(config),
                retain=True,
                qos=1
            )
            logger.debug(
                "Published discovery config for inverter %s, %s: %s",
                modbus_id,
                entity_type,
                name,
            )
        except Exception as e:
            logger.error("Failed to publish discovery config: %s", e)



    # -------------------------------------------------------------------------

    def _build_binary_sensor_config(
        self,
        modbus_id: int,
        name: str,
        value_template_group: str,
        value_template_key: str,
        icon: Optional[str] = None,
        entity_category: Optional[str] = None,
        device_class: Optional[str] = None,
        payload_on: Optional[str] = None,
        payload_off: Optional[str] = None,
        options: Optional[List[str]] = None
    ) -> Dict[str, Any]:

        value_template = f"{{{{ value_json.{value_template_group}.binary.{value_template_key} }}}}"
        binary_sensor = self._build_base_entity(
            modbus_id=modbus_id,
            name=name,
            value_template=value_template,
            uniq_obj_id = f"inverter_{modbus_id}_{value_template_key}",
        )

        optional_fields = {
            "ic": icon,
            "ent_cat": entity_category,
            "dev_cla": device_class,
            "pl_on": payload_on,
            "pl_off": payload_off,
            "ops": options
        }
        self._apply_optional_fields(binary_sensor, optional_fields)

        return binary_sensor

    def _build_sensor_config(
        self,
        modbus_id: int,
        name: str,
        value_template_group: str,
        value_template_key: str,
        invert_value: Optional[bool] = False,
        unit_of_measurement: Optional[str] = None,
        suggested_display_precision: Optional[int] = None,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        entity_category: Optional[str] = None
    ) -> Dict[str, Any]:

        value_template_expr = f"value_json.{value_template_group}.normal.{value_template_key}"

        sensor = self._build_base_entity(
            modbus_id=modbus_id,
            name=name,
            value_template=f"{{{{ ({value_template_expr} | float) * -1 }}}}" if invert_value and self.invert_ha_dis_charge_measurements else f"{{{{ {value_template_expr} }}}}",
            uniq_obj_id=f"inverter_{modbus_id}_{value_template_key}",
        )

        optional_fields = {
            "stat_cla": state_class,
            "unit_of_meas": unit_of_measurement,
            "sug_dsp_prc": suggested_display_precision,
            "ic": icon,
            "ent_cat": entity_category,
            "dev_cla": device_class
        }
        self._apply_optional_fields(sensor, optional_fields)

        return sensor



    # -------------------------------------------------------------------------
    
    def _publish_binary_sensor_config(
        self,
        modbus_id: int,
        binary_sensor_name: str,
        value_template_key: str,
        binary_sensor_config: Dict[str, Any]
    ) -> None:
        """
        Publish binary sensor configuration to MQTT.
        """
        self._publish_config(
            entity_type="binary_sensor",
            modbus_id=modbus_id,
            name=binary_sensor_name,
            value_template_key=value_template_key,
            config=binary_sensor_config,
        )

    def _publish_sensor_config(
        self,
        modbus_id: int,
        sensor_name: str,
        value_template_key: str,
        sensor_config: Dict[str, Any]
    ) -> None:
        """
        Publish sensor configuration to MQTT.
        """
        self._publish_config(
            entity_type="sensor",
            modbus_id=modbus_id,
            name=sensor_name,
            value_template_key=value_template_key,
            config=sensor_config,
        )

    def create_binary_sensor_config(
        self,
        modbus_id: int,
        name: str,
        value_template_group: str,
        value_template_key: str,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        entity_category: Optional[str] = None,
        payload_on: Optional[str] = None,
        payload_off: Optional[str] = None,
        options: Optional[List[str]] = None
    ) -> None:

        logger.debug(
            "Creating auto-discovery binary sensors for inverter %s",
            modbus_id,
        )

        binary_sensor_config = self._build_binary_sensor_config(
            modbus_id=modbus_id,
            value_template_group=value_template_group,
            name=name,
            value_template_key=value_template_key,
            icon=icon,
            device_class=device_class,
            entity_category=entity_category,
            payload_on=payload_on,
            payload_off=payload_off,
            options=options
        )

        self._publish_binary_sensor_config(modbus_id, name, value_template_key, binary_sensor_config)

        logger.debug(
            "Auto-discovery binary sensors published for inverter %s",
            modbus_id,
        )


    def create_sensor_config(
        self,
        modbus_id: int,
        value_template_group: str,
        name: str,
        value_template_key: str,
        invert_value: Optional[bool] = False,
        unit_of_measurement: Optional[str] = None,
        suggested_display_precision: Optional[int] = None,
        icon: Optional[str] = None,
        device_class: Optional[str] = None,
        state_class: Optional[str] = None,
        entity_category: Optional[str] = None
    ) -> None:

        logger.debug(
            "Creating auto-discovery sensors for inverter %s",
            modbus_id,
        )

        sensor_config = self._build_sensor_config(
            modbus_id=modbus_id,
            value_template_group=value_template_group,
            name=name,
            value_template_key=value_template_key,
            invert_value=invert_value,
            unit_of_measurement=unit_of_measurement,
            suggested_display_precision=suggested_display_precision,
            icon=icon,
            device_class=device_class,
            state_class=state_class,
            entity_category=entity_category
        )

        self._publish_sensor_config(modbus_id, name, value_template_key, sensor_config)

        logger.debug(
            "Auto-discovery sensors published for inverter %s",
            modbus_id,
        )

    def create_heartbeat_sensor_config(self, modbus_id: int) -> None:

        name = "Last Publish"
        value_template_key = "last_publish"
        state_topic = f"{self.mqtt_topic}/inverter-{modbus_id}/heartbeat"
        value_template = "{{ value_json.last_publish }}"

        sensor = self._build_base_entity(
            modbus_id=modbus_id,
            name=name,
            value_template=value_template,
            uniq_obj_id=f"inverter_{modbus_id}_{value_template_key}",
            state_topic=state_topic,
        )

        self._apply_optional_fields(
            sensor,
            {
                "ic": "mdi:update",
                "ent_cat": "diagnostic",
            },
        )

        self._publish_sensor_config(modbus_id, name, value_template_key, sensor)


    def create_autodiscovery_sensors(self, modbus_id: int) -> None:

        self._device_info_published.discard(modbus_id)

        # Create telemetry sensors
        for config in TELEMETRY_SENSOR_TEMPLATES:
            self.create_sensor_config(
                modbus_id=modbus_id,
                value_template_group="telemetry",
                **config
            )

        # Create heartbeat sensor
        self.create_heartbeat_sensor_config(modbus_id=modbus_id)
