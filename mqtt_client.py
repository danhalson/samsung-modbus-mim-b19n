#!/usr/bin/python3 -u

from dotenv import load_dotenv
from os.path import join, dirname
import time
import paho.mqtt.client as mqtt
import json
import os
from datetime import datetime
import modbus_client
import http_status_server
import threading

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Load .env variables
MQTT_USER = os.environ.get('MQTT_USER')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD')
MQTT_HOST = os.environ.get('MQTT_HOST')
MQTT_PORT = int(os.environ.get('MQTT_PORT'))

# Global variable definition
flag_connected = threading.Event()  # Use threading.Event for thread-safe signaling

# Constant variable definition
DEBUG_MODE = False
MSG_INTERVAL = 5  # Data collection interval in secs. 5 mins = 5 * 60 = 300
MQTT_ONLINE = "Online"
DISCOVER_DIR = "homeassistant" # where the Home Assistant discovery files are located
DISCOVERY_PREFIX = "homeassistant" # prefix used for Home Assistant MQTT discovery
#MQTT_STATUS_TOPIC = f"{discovery_prefix}/status"
#MQTT_SENSORS_TOPIC = f"{discovery_prefix}/sensor/device/ashp/sensors/config"
#MQTT_COMMAND_TOPIC = f"{discovery_prefix}/sensor/device/ashp/command/config"
MQTT_STATUS_TOPIC = "raspberry/ashp/status"
MQTT_SENSORS_TOPIC = "raspberry/ashp/sensors"
MQTT_COMMAND_TOPIC = "raspberry/ashp/command"

# MQTT
def on_connect(client, userdata, flags, reason_code, properties):
  print(f"Connected with flags [{flags}] reason code [{reason_code}]")
  flag_connected.set()  # Set the event to indicate connection

def on_disconnect(client, userdata, flags, reason_code, properties):
  print(f"Disconnected with flags [{flags}] reason code [{reason_code}]")
  flag_connected.clear()  # Clear the event to indicate disconnection
  # Attempt to reconnect
  try:
    client.reconnect()
    print("Reconnected to MQTT broker")
  except Exception as e:
    print(f"Reconnection failed: {e}")
    time.sleep(5)

ashp = modbus_client.ModbusClient()
modbus_lock = threading.Lock()

# Define the callback function for message handling
def on_message(client, userdata, msg):
  print(f"Receiving topic {msg.topic}: {msg.payload.decode()}")
  # Assuming the payload is a JSON string with a method name and arguments
  try:
    message = json.loads(msg.payload.decode())
    method_name = message.get('method')
    value = message.get('value')

    # Call the method on the ashp object
    if hasattr(ashp, method_name):
      method = getattr(ashp, method_name)
      with modbus_lock:
        method(value)
    else:
      print(f"Method {method_name} not found on ashp object")
  except json.JSONDecodeError:
    print("Failed to decode JSON message")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.connect(MQTT_HOST, MQTT_PORT)
client.subscribe(MQTT_COMMAND_TOPIC)

def publish_ha_discovery_config():
  this_dir = os.path.dirname(__file__)
  sconfig_path = os.path.join(this_dir, DISCOVER_DIR, "sensor_config.json")
  with open(sconfig_path, "r") as f:
    sensor_configs = json.load(f)
  dconfig_path = os.path.join(this_dir, DISCOVER_DIR, "device.json")
  with open(dconfig_path, "r") as f:
    device_config = json.load(f)
  for sensor in sensor_configs:
    # Extract unique_id for topic, fallback to name if not present
    unique_id = sensor.get("unique_id")
    sensor["device"] = device_config
    config_topic = f"{DISCOVERY_PREFIX}/sensor/{unique_id}/config"
    if DEBUG_MODE:
      print(json.dumps(sensor))

    client.publish(config_topic, json.dumps(sensor), retain=True)

def on_off_state(value):
  if value == 1 or value is True:
      return "on"
  elif value == 0 or value is False:
      return "off"
  return "unknown"

# System Uptime
def uptime():
  t = os.popen('uptime -p').read()[:-1]
  uptime = t.replace('up ', '')
  return uptime

# Main loop
if __name__ == '__main__':
  # Start the HTTP server in a separate thread
  http_status_server.run_http_server_in_thread(flag_connected)

  # Start the MQTT loop
  client.loop_start()

  # Wait to receive the connected callback for MQTT
  while not flag_connected.is_set():
    print("Not connected. Waiting 1 second.")
    time.sleep(1)

  # Publish Home Assistant discovery configs
  publish_ha_discovery_config()

  def publish_sensor_data():
    while True:
      # Record current date and time for message timestamp
      now = datetime.now()

      # Format message timestamp to mm/dd/YY H:M:S
      last_message = now.strftime("%m/%d/%Y %H:%M:%S")

      # Get current system uptime
      sys_uptime = uptime()

      # Create JSON dict for MQTT transmission
      with modbus_lock:
        send_msg = {
          'outdoor_temp': ashp.get_outdoor_temp(),
          'flow_rate': ashp.get_flow_rate(),
          'three_way_valve_position': ashp.get_three_way_valve_position(),
          'compressor_freq': ashp.get_compressor_freq(),
          'dhw_temp': ashp.get_dhw_temp(),
          'return_temp': ashp.get_return_temp(),
          'flow_temp': ashp.get_flow_temp(),
          'target_flow_temp': ashp.get_target_flow_temp(),
          'dhw_status': ashp.get_dhw_status(),
          'target_dhw_temp': ashp.get_target_dhw_temp(),
          'away_status': ashp.get_away_status(),
          'ch_status': ashp.get_ch_status(),
          'indoor_temp': ashp.get_indoor_temp(),
          'target_indoor_temp': ashp.get_target_indoor_temp(),
          'defrost_status': ashp.get_defrost_status(),
          'error_code': ashp.get_error_code(),
          'dhw_mode': ashp.get_dhw_mode(),
          'last_message': last_message,
          'sys_uptime': sys_uptime
        }

      send_msg['dhw_status'] = on_off_state(ashp.get_dhw_status())
      send_msg['ch_status'] = on_off_state(ashp.get_ch_status())
      send_msg['away_status'] = on_off_state(ashp.get_away_status())
      send_msg['defrost_status'] = on_off_state(ashp.get_defrost_status())

      current_position = ashp.get_three_way_valve_position()
      send_msg['three_way_valve_position'] = current_position == 0 and "heating" or current_position == 1 and "water" or "unknown"

      dhw_mode = ashp.get_dhw_mode()
      send_msg['dhw_mode'] = dhw_mode == 0 and "eco" or dhw_mode == 1 and "standard" or dhw_mode == 2 and "power" or dhw_mode == 3 and "forced" or "unknown"

      # Convert message to json
      payload_sensors = json.dumps(send_msg)

      # Debugging (used when testing and need to print variables)
      if DEBUG_MODE:
        print(payload_sensors)

      print("Publishing sensor data...")

      # Set status payload
      payload_status = MQTT_ONLINE

      # Publish status to mqtt
      client.publish(MQTT_STATUS_TOPIC, payload_status, qos=0)

      # Publish sensor data to mqtt
      client.publish(MQTT_SENSORS_TOPIC, payload_sensors, qos=0)

      # Wait for the interval
      time.sleep(MSG_INTERVAL)

  # Start the sensor data publishing in a separate thread
  threading.Thread(target=publish_sensor_data).start()

  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    print("Interrupted by user")

  client.loop_stop()
  client.disconnect()
  print("MQTT Disconnected.")
