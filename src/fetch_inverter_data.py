import sys
import os
import signal
import logging
import time
import threading
import serial
import minimalmodbus
import json
import paho.mqtt.client as mqtt

from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from typing import Optional, Dict, Any, Union, List, Callable, Tuple
from serial.serialutil import SerialException
from paho.mqtt import MQTTException
from ha_auto_discovery import AutoDiscoveryConfig


# Type aliases for clarity
ConfigValue = Union[int, float, bool, str, None]
InverterData = Dict[str, Any]

# State container for shared application state
class AppState:
    def __init__(self):
        self.mqtt_client: Optional[mqtt.Client] = None
        self.instrument: Optional[minimalmodbus.Instrument] = None
        self.inverter: Dict[str, Any] = {}

app_state = AppState()

logger: Optional[logging.Logger] = None

# --- Health/Watchdog state ---
# Timestamp of last successful BMS poll (seconds since epoch).
last_update_ts: float = 0.0
# MQTT connection state as seen by callbacks.
mqtt_connected: bool = False


def _serial_is_open() -> bool:
    """Compatibility wrapper across pyserial versions."""
    s = app_state.instrument.serial if app_state.instrument else None
    if not s:
        return False
    # Newer pyserial: property
    if hasattr(s, "is_open"):
        return bool(getattr(s, "is_open"))
    # Older pyserial: method
    if hasattr(s, "isOpen"):
        try:
            return bool(s.isOpen())
        except Exception:
            return False
    return False


def _mqtt_loop_running() -> bool:
    """Best-effort check whether Paho's network loop thread is alive."""
    c = app_state.mqtt_client
    if not c:
        return False
    t = getattr(c, "_thread", None)
    return bool(t and getattr(t, "is_alive", lambda: False)())


def _compute_max_age_seconds() -> int:
    cycle_pause = int(getattr(Config, "MQTT_UPDATE_INTERVAL", 30) or 0)
    expected_cycle = max(cycle_pause, 0)
    # Add a little slack for serial hiccups and startup.
    return max(15, int(expected_cycle * 3 + 5))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        now = time.time()
        max_age = _compute_max_age_seconds()

        healthy = (
            mqtt_connected
            and _mqtt_loop_running()
            and _serial_is_open()
            and (now - last_update_ts) < max_age
        )

        if healthy:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(503)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"unhealthy")

    def log_message(self, format, *args):
        # Keep addon logs clean
        return


def _start_health_server() -> None:
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()


def graceful_exit(signum: Optional[int] = None, _frame: Optional[Any] = None) -> None:
    """Handle script exit to disconnect MQTT gracefully and cleanup."""

    try:
        # Close MQTT client if connected
        if app_state.mqtt_client and app_state.mqtt_client.is_connected():
            if logger:
                logger.info("Sending offline status to MQTT")
            app_state.mqtt_client.publish(f"{os.getenv('MQTT_TOPIC', 'inverter')}/availability", "offline", retain=True)
            inverter =  app_state.inverter
            app_state.mqtt_client.publish(_availability_topic(inverter["address"]), "offline", retain=False)
            if logger:
                logger.info("Disconnecting MQTT client")
            app_state.mqtt_client.disconnect()
            app_state.mqtt_client.loop_stop()

        # Close serial connection if open
        if _serial_is_open():
            if logger:
                logger.info("Closing serial connection")
            app_state.instrument.serial.close()
    except Exception as e:
        if logger:
            logger.error("Error during graceful exit: %s", e)

    if signum is not None:
        sys.exit(0)


# Register signal handler for SIGTERM
signal.signal(signal.SIGTERM, graceful_exit)
signal.signal(signal.SIGINT, graceful_exit)


def get_env_value(var_name: str, default: Any = None, return_type: type = str) -> ConfigValue:

    value = os.getenv(var_name, default)

    if value is None or value == "":
        return default

    try:
        if return_type == int:
            return int(value)
        elif return_type == float:
            return float(value)
        elif return_type == bool:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ['true', '1', 'yes', 'on']
        else:
            return str(value)
    except (ValueError, TypeError):
        return default


# Configuration from environment variables with defaults
class Config:

    # Modbus Configuration
    MODBUS_ID = get_env_value("MODBUS_ID", 1, int)

    # Serial Configuration
    SERIAL_INTERFACE = get_env_value("SERIAL_INTERFACE", "/dev/ttyUSB0", str)

    # MQTT Configuration
    MQTT_HOST = get_env_value("MQTT_HOST", "192.168.1.100", str)
    MQTT_PORT = get_env_value("MQTT_PORT", 1883, int)
    MQTT_USERNAME = get_env_value("MQTT_USERNAME", "mqtt", str)
    MQTT_PASSWORD = get_env_value("MQTT_PASSWORD", "", str)
    MQTT_TOPIC = get_env_value("MQTT_TOPIC", "inverter", str)
    MQTT_UPDATE_INTERVAL = get_env_value("MQTT_UPDATE_INTERVAL", 30, int)

    # Home Assistant Discovery
    ENABLE_HA_DISCOVERY_CONFIG = get_env_value("ENABLE_HA_DISCOVERY_CONFIG", True, bool)
    HA_DISCOVERY_PREFIX = get_env_value("HA_DISCOVERY_PREFIX", "homeassistant", str)
    INVERT_HA_DIS_CHARGE_MEASUREMENTS = get_env_value("INVERT_HA_DIS_CHARGE_MEASUREMENTS", True, bool)

    # Logging
    LOGGING_LEVEL = get_env_value("LOGGING_LEVEL", "info", str).upper()


# Logging setup
logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Inverter")

# Set log level based on configuration
log_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}
logger.setLevel(log_levels.get(Config.LOGGING_LEVEL, logging.INFO))

# Log configuration on startup
logger.info("Starting Inverter Data Logger")
logger.debug("Configuration loaded: %s", vars(Config))


def _availability_topic(modbus_id: int) -> str:
    return f"{Config.MQTT_TOPIC}/inverter-{modbus_id}/availability"


def _heartbeat_topic(modbus_id: int) -> str:
    return f"{Config.MQTT_TOPIC}/inverter-{modbus_id}/heartbeat"


def _publish_inverter_availability(inverter: Dict[str, Any], now: float) -> None:
    if not app_state.mqtt_client:
        return

    max_age = _compute_max_age_seconds()
    last_success = inverter.get("last_success_ts", 0.0)
    is_online = last_success > 0 and (now - last_success) <= max_age
    desired = "online" if is_online else "offline"

    if inverter.get("availability") != desired:
        topic = _availability_topic(inverter["address"])
        app_state.mqtt_client.publish(topic, desired, retain=False)
        inverter["availability"] = desired


class Telemetry:
    def __init__(self):
        # Battery
        self.battery_voltage: Optional[float] = None
        self.battery_current: Optional[float] = None
        self.battery_power: Optional[int] = None
        self.battery_soc: Optional[float] = None
        # Grid
        self.grid_input_voltage: Optional[float] = None
        self.grid_line_voltage: Optional[float] = None
        self.grid_power: Optional[int] = None
        # Output Line 1
        self.l1_voltage: Optional[float] = None
        self.l1_current: Optional[float] = None
        self.l1_power: Optional[int] = None
        self.l1_apparent_power: Optional[int] = None
        self.l1_load: Optional[int] = None
        # Output Line 2
        self.l2_voltage: Optional[float] = None
        self.l2_current: Optional[float] = None
        self.l2_power: Optional[int] = None
        self.l2_apparent_power: Optional[int] = None
        self.l2_load: Optional[int] = None
        # Total Output Line
        self.total_output_power: Optional[int] = None 
        self.total_output_load: Optional[int] = None 
        # PV 1
        self.pv1_voltage: Optional[float] = None
        self.pv1_current: Optional[float] = None
        self.pv1_power: Optional[int] = None
        # PV 2
        self.pv2_voltage: Optional[float] = None
        self.pv2_current: Optional[float] = None
        self.pv2_power: Optional[int] = None
        # Total PV
        self.total_pv_power: Optional[int] = None 
        # DateTime
        self.year: Optional[int] = None 
        self.month: Optional[int] = None
        self.day: Optional[int] = None 
        self.hour: Optional[int] = None
        self.minute: Optional[int] = None
        self.second: Optional[int] = None
        # Energy
        self.energy_today: Optional[float] = None
        self.energy_year: Optional[float] = None
        # Configured limits
        self.conf_line_voltage: Optional[int] = None
        self.conf_line_frequency: Optional[int] = None
        self.conf_l2_power: Optional[int] = None
        self.conf_chrg_float_voltage: Optional[float] = None
        self.conf_chrg_max_current: Optional[int] = None
        self.conf_chrg_grid_current: Optional[int] = None
        self.conf_pointback: Optional[float] = None
        self.conf_l1_cutoff: Optional[float] = None
        self.conf_l2_cutoff: Optional[float] = None


class SolarInverter:

    FRAME_READ_RETRIES = 5
    REGISTER_PAGE = 124

    def __init__(self, modbus_id: int):
        self.modbus_id = modbus_id
        self.last_status: Optional[InverterData] = None
        self.telemetry = Telemetry()

    def process_register(self, register_map, address, decimals=0, signed=False, note=""):

        value = register_map[address]

        # 1. Handle Signedness (Two's Complement)
        if signed and value > 32767:
            value -= 65536
            
        # 2. Handle Decimals
        if decimals > 0:
            value =  round(value / (10 ** decimals), decimals)
        
        logger.debug("Register %s : %s	%s", address, value, note)

        return value


    def get_telemetry(self, register_map) -> Dict[str, Any]:

        telemetry_feedback = {"normal": {}}
        feedback = telemetry_feedback["normal"]

        # Battery Status
        self.telemetry.battery_voltage = self.process_register(277, register_map, decimals = 1, signed = False, note="Battery Voltage")
        self.telemetry.battery_current = self.process_register(278, register_map, decimals = 1, signed = True,  note="Battery Current")
        self.telemetry.battery_power = self.process_register(279, register_map, decimals = 0, signed = True,  note="Battery Charge/Discharge Power")
        self.telemetry.battery_soc = self.process_register(280, register_map, decimals = 0, signed = False, note="Battery SoC")
        
        feedback.update({
            "battery_voltage": self.telemetry.battery_voltage,
            "battery_current": self.telemetry.battery_current,
            "battery_power": self.telemetry.battery_power,
            "battery_soc": self.telemetry.battery_soc
        })

        # Grid Status
        self.telemetry.grid_input_voltage = self.process_register(338, register_map, decimals = 1, signed = False, note="Grid AC Ref. Voltage")
        self.telemetry.grid_line_voltage = self.process_register(342, register_map, decimals = 1, signed = False, note="Grif AC Line Voltage")
        self.telemetry.grid_power = self.process_register(340, register_map, decimals = 0, signed = False, note="Grid Power in W")

        feedback.update({
            "grid_input_voltage": self.telemetry.grid_input_voltage,
            "grid_line_voltage": self.telemetry.grid_line_voltage,
            "grid_power": self.telemetry.grid_power
        })

        # L1 Output Status
        self.telemetry.l1_voltage = self.process_register(346, register_map, decimals = 1, signed = False, note="L1 AC Voltage")
        self.telemetry.l1_current = self.process_register(347, register_map, decimals = 1, signed = False, note="L1 Current in A")
        self.telemetry.l1_power = self.process_register(348, register_map, decimals = 0, signed = True,  note="L1 Power in W")
        self.telemetry.l1_apparent_power = self.process_register(349, register_map, decimals = 0, signed = True,  note="L1 Power in VA")
        self.telemetry.l1_load = self.process_register(350, register_map, decimals = 0, signed = False, note="L1 Load in %")

        feedback.update({
            "l1_voltage": self.telemetry.l1_voltage,
            "l1_current": self.telemetry.l1_current,
            "l1_power": self.telemetry.l1_power,
            "l1_apparent_power": self.telemetry.l1_apparent_power,
            "l1_load": self.telemetry.l1_load
        })

        # L2 Output Status
        self.telemetry.l2_voltage = self.process_register(384, register_map, decimals = 1, signed = False, note="L2 AC Voltage")
        self.telemetry.l2_current = self.process_register(385, register_map, decimals = 1, signed = False, note="L2 Current in A")
        self.telemetry.l2_apparent_power = self.process_register(386, register_map, decimals = 0, signed = True,  note="L2 Power in VA")
        self.telemetry.l2_power = self.process_register(387, register_map, decimals = 0, signed = True,  note="L2 Power in W")
        self.telemetry.l2_load = self.process_register(388, register_map, decimals = 0, signed = False, note="L2 Load in W")

        feedback.update({
            "l2_voltage": self.telemetry.l2_voltage,
            "l2_current": self.telemetry.l2_current,
            "l2_apparent_power": self.telemetry.l2_apparent_power,
            "l2_power": self.telemetry.l2_power,
            "l2_load": self.telemetry.l2_load
        })
        # Total Output Line
        self.telemetry.total_output_power = self.process_register(344, register_map, decimals = 0, signed = False, note="L1+L2 Power in VA")
        self.telemetry.total_output_load = self.process_register(256, register_map, decimals = 0, signed = False, note="L1+L2 Load in %")

        feedback.update({
            "total_output_power": self.telemetry.total_output_power,
            "total_output_load": self.telemetry.total_output_load
        })

        # PV 1 Status
        self.telemetry.pv1_voltage = self.process_register(351, register_map, decimals = 1, signed = False, note="PV1 Voltage")
        self.telemetry.pv1_current = self.process_register(352, register_map, decimals = 1, signed = False, note="PV1 Current in A")
        self.telemetry.pv1_power = self.process_register(353, register_map, decimals = 0, signed = False, note="PV1 Power in W")

        feedback.update({
            "pv1_voltage": self.telemetry.pv1_voltage,
            "pv1_current": self.telemetry.pv1_current,
            "pv1_power": self.telemetry.pv1_power
        })
        
        # PV 2 Status
        self.telemetry.pv2_voltage = self.process_register(389, register_map, decimals = 1, signed = False, note="PV2 Voltage")
        self.telemetry.pv2_current = self.process_register(390, register_map, decimals = 1, signed = False, note="PV2 Current in A")
        self.telemetry.pv2_power = self.process_register(391, register_map, decimals = 0, signed = False, note="PV2 Power in W")

        feedback.update({
            "pv2_voltage": self.telemetry.pv2_voltage,
            "pv2_current": self.telemetry.pv2_current,
            "pv2_power": self.telemetry.pv2_power
        })
        # Total PV
        self.telemetry.total_pv_power = self.process_register(302, register_map, decimals = 0, signed = False, note="PV1 + PV2 Power in W")

        feedback.update({
            "total_pv_power": self.telemetry.total_pv_power
        })

        # DateTime
        self.telemetry.year = self.process_register(696, register_map, decimals = 0, signed = False, note="Year")
        self.telemetry.month = self.process_register(697, register_map, decimals = 0, signed = False, note="Month")
        self.telemetry.day = self.process_register(698, register_map, decimals = 0, signed = False, note="Day")
        self.telemetry.hour = self.process_register(699, register_map, decimals = 0, signed = False, note="Hour")
        self.telemetry.minute = self.process_register(700, register_map, decimals = 0, signed = False, note="Minutes")
        self.telemetry.second = self.process_register(701, register_map, decimals = 0, signed = False, note="Seconds")      

        feedback.update({
            "year": self.telemetry.year,
            "month": self.telemetry.month,
            "day": self.telemetry.day,
            "hour": self.telemetry.hour,
            "minute": self.telemetry.minute,
            "second": self.telemetry.second
        })

        # Energy
        self.telemetry.energy_today = self.process_register(702, register_map, decimals = 2, signed = False, note="Energy per Day in kW/h")
        self.telemetry.energy_year = self.process_register(704, register_map, decimals = 2, signed = False, note="Energy per Year in kW/h")

        feedback.update({
            "energy_today": self.telemetry.energy_today,
            "energy_year": self.telemetry.energy_year
        })

        # Configured Limits
        self.telemetry.conf_line_voltage = self.process_register(606, register_map, decimals = 1, signed = False, note="Voltage Set")
        self.telemetry.conf_l2_power = self.process_register(607, register_map, decimals = 0, signed = False, note="Capacity for L2 in W")
        self.telemetry.conf_line_frequency = self.process_register(608, register_map, decimals = 0, signed = False, note="Frequency Set in Hz")
        self.telemetry.conf_chrg_float_voltage = self.process_register(638, register_map, decimals = 1, signed = False, note="Floating Charging Voltage")
        self.telemetry.conf_chrg_max_current = self.process_register(640, register_map, decimals = 1, signed = False, note="Max Total Charging Current")
        self.telemetry.conf_chrg_grid_current = self.process_register(641, register_map, decimals = 1, signed = False, note="Max Grid Charging Current")
        self.telemetry.conf_pointback = self.process_register(644, register_map, decimals = 1, signed = False, note="SoC Point Back to Utility")
        self.telemetry.conf_l1_cutoff = self.process_register(645, register_map, decimals = 1, signed = False, note="Cutoff Voltage for L1")
        self.telemetry.conf_l2_cutoff = self.process_register(646, register_map, decimals = 1, signed = False, note="Cutoff Voltage for L2")

        feedback.update({
            "voltage_conf": self.telemetry.conf_line_voltage,
            "l2_power_conf": self.telemetry.conf_l2_power,
            "frequency_conf": self.telemetry.conf_line_frequency,
            "floating_charging_voltage": self.telemetry.conf_chrg_float_voltage,
            "max_total_charging_current": self.telemetry.conf_chrg_max_current,
            "max_grid_charging_current": self.telemetry.conf_chrg_grid_current,
            "soc_point_back_to_utility": self.telemetry.conf_pointback,
            "l1_cutoff_voltage": self.telemetry.conf_l1_cutoff,
            "l2_cutoff_voltage": self.telemetry.conf_l2_cutoff
        })

        return telemetry_feedback


    def read_registers(self, page_address)-> List[int]:
        values = []
        try:
            values = app_state.instrument.read_registers(page_address, self.REGISTER_PAGE, functioncode=3)
        except Exception as e:
            logger.error("Error reading registers: %s", e)
        return values

    def read_modbus(self, register_map, start_address = 0, pages = 5):
        for p in range(pages):
            time.sleep(1)
            page_address = start_address + self.REGISTER_PAGE * p
            logger.info("Reading page: %s", p)
        
            values = []

            for ret in range(self.FRAME_READ_RETRIES):
                values = self.read_registers(page_address)

            if len(values) > 0:
                break;
            
            logger.info("Retrying page %s", p )
            time.sleep(0.5)

            register_map |= {page_address + i: val for i, val in enumerate(values)}


    def read_serial_data(self) -> Tuple[Optional[InverterData], bool]:

        logger.info("Inverter %s: Requesting data...", self.modbus_id)

        if not app_state.instrument:
            logger.error("Instrument is not initialized")
            return None

        log_data = {
            "telemetry": {},
        }

        register_map = {}

        try:
            # Flush serial buffers
            app_state.instrument.serial.flushOutput()
            app_state.instrument.serial.flushInput()

            self.read_modbus(register_map, start_address=100, pages=3)
            self.read_modbus(register_map, start_address=600, pages=1)

            # Request telemetry data
            telemetry_feedback = self.get_telemetry(register_map)

            if telemetry_feedback is None:
                return None, False
            log_data["telemetry"] = telemetry_feedback

            # Mandatory delay between each request or there will be corrupt data
            time.sleep(1)

            # Check if data has changed
            if self.last_status is None or self.last_status != log_data:
                self.last_status = log_data
                return log_data, True

            return None, True
        except Exception as e:
            logger.error("Inverter %s: Error reading data: %s", self.modbus_id, e)
            return None, False


def on_mqtt_connect(
    _client: mqtt.Client,
    _userdata: Any,
    _flags: Any,
    reason_code: int
) -> None:
    """Handle MQTT connection."""
    global mqtt_connected
    if reason_code == 0:
        mqtt_connected = True
        logger.info(
            "Connected to MQTT broker (%s:%s)",
            Config.MQTT_HOST,
            Config.MQTT_PORT
        )
    else:
        mqtt_connected = False
        logger.error("Failed to connect to MQTT broker: %s", reason_code)


def on_mqtt_disconnect(
    _client: mqtt.Client,
    _userdata: Any,
    _reason_code: int,
    _properties: Any = None,
) -> None:
    """Handle MQTT disconnect."""
    global mqtt_connected
    mqtt_connected = False


def initialize_mqtt() -> mqtt.Client:
    """Initialize and connect MQTT client."""
    client = mqtt.Client()
    client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
    client.on_connect = on_mqtt_connect
    client.on_disconnect = on_mqtt_disconnect
    client.will_set(f"{Config.MQTT_TOPIC}/availability", payload="offline", qos=2, retain=False)

    try:
        client.connect(Config.MQTT_HOST, Config.MQTT_PORT, keepalive=60)
        client.loop_start()
        return client
    except MQTTException as e:
        logger.error("MQTT connection failed: %s", e)
        sys.exit(1)


def initialize_serial() -> minimalmodbus.Instrument:
    """Initialize serial connection."""
    try:
        inverter = minimalmodbus.Instrument(Config.SERIAL_INTERFACE, slaveaddress=Config.MODBUS_ID)
        inverter.serial.baudrate = 9600
        inverter.serial.bytesize = 8
        inverter.serial.parity   = serial.PARITY_NONE
        inverter.serial.stopbits = 1
        inverter.serial.timeout  = 1           # Seconds
        inverter.mode = minimalmodbus.MODE_RTU # Explicitly set RTU mode
        #inverter.close_port_after_each_call = True


        logger.info(
            "Initializing serial interface %s for modbus_id %s",
            Config.SERIAL_INTERFACE,
            Config.MODBUS_ID
        )
        return inverter
    
    except SerialException as e:
        logger.error("Serial initialization failed: %s", e)
        sys.exit(1)


def main():
    """Main application loop."""
    global last_update_ts
    try:
        app_state.mqtt_client = initialize_mqtt()
        app_state.instrument = initialize_serial()
        app_state.mqtt_client.publish(_availability_topic(Config.MODBUS_ID), "offline", retain=False)

        solar_inverter = SolarInverter(modbus_id=Config.MODBUS_ID)
        app_state.inverter = {
            "address": Config.MODBUS_ID,
            "last_success_ts": 0.0,
            "publish_counter": 0,
            "availability": "offline",
        }
        logger.info("Initialized inverter with modbus_id %s", Config.MODBUS_ID)

        last_update_ts = time.time()

        # Start minimal HTTP health endpoint for HA Supervisor watchdog
        health_thread = threading.Thread(target=_start_health_server, daemon=True)
        health_thread.start()
        logger.info("Health endpoint started on http://0.0.0.0:8081/health")

        # Send Home Assistant Auto-Discovery configurations on startup
        if Config.ENABLE_HA_DISCOVERY_CONFIG:
            logger.info("Sending Home Assistant Auto-Discovery configurations")
            auto_discovery = AutoDiscoveryConfig(
                mqtt_topic=Config.MQTT_TOPIC,
                discovery_prefix=Config.HA_DISCOVERY_PREFIX,
                invert_ha_dis_charge_measurements=Config.INVERT_HA_DIS_CHARGE_MEASUREMENTS,
                mqtt_client=app_state.mqtt_client
            )
            auto_discovery.create_autodiscovery_sensors(modbus_id=Config.MODBUS_ID)
            logger.info("Auto-Discovery configurations sent")

        # Main loop
        while True:
            try:
                inverter = app_state.inverter

                # Fetch data
                log_data, poll_success = solar_inverter.read_serial_data()
                now = time.time()

                if poll_success:
                    last_update_ts = now
                    inverter["last_success_ts"] = now
                    inverter["publish_counter"] += 1

                    heartbeat_payload = {
                        "last_publish": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "publish_counter": inverter["publish_counter"],
                    }
                    
                    app_state.mqtt_client.publish(
                        _heartbeat_topic(Config.MODBUS_ID),
                        json.dumps(heartbeat_payload),
                        retain=False,
                    )
                    
                    app_state.mqtt_client.publish(
                        _availability_topic(Config.MODBUS_ID),
                        "online",
                        retain=False,
                    )

                    inverter["availability"] = "online"

                if log_data:
                    logger.info("Inverter %s: Publishing updated data to MQTT", Config.MODBUS_ID)
                    topic = f"{Config.MQTT_TOPIC}/inverter-{Config.MODBUS_ID}/sensors"
                    payload = {**log_data}
                    app_state.mqtt_client.publish(topic, json.dumps(payload, indent=2))
                elif poll_success:
                    logger.info("Inverter %s: No changes detected", Config.MODBUS_ID)

                _publish_inverter_availability(inverter, now)

                app_state.mqtt_client.publish(f"{Config.MQTT_TOPIC}/availability", "online", retain=False)

                time.sleep(1)

                if Config.MQTT_UPDATE_INTERVAL > 0:
                    logger.info(
                        "Waiting %s seconds before next cycle",
                        Config.MQTT_UPDATE_INTERVAL
                    )
                time.sleep(Config.MQTT_UPDATE_INTERVAL)

            except Exception as e:
                logger.error("Error in main loop: %s", e)
                time.sleep(10)

    except KeyboardInterrupt:
        logger.info("Shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error("Fatal error: %s", e)
    finally:
        graceful_exit()


if __name__ == "__main__":
    main()
