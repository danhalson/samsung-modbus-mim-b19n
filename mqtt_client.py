#!/usr/bin/python3 -u

import os
from dotenv import load_dotenv
from os.path import join, dirname
import time
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import modbus_client
import http_status_server
import threading
import logging
import random

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)

# Load .env variables
MQTT_HOST = os.environ.get('MQTT_HOST')
MQTT_PORT = int(os.environ.get('MQTT_PORT'))

if not all([MQTT_HOST, MQTT_PORT]):
    raise EnvironmentError("Missing one or more required MQTT environment variables.")

# Global variable definition
flag_connected = threading.Event()  # Use threading.Event for thread-safe signaling

# Constant variable definition
CLIENT_ID = f'python-mqtt-tcp-pub-sub-{random.randint(0, 1000)}'
DEBUG_MODE = False
MSG_INTERVAL = 5  # Data collection interval in secs. 5 mins = 5 * 60 = 300

MQTT_ONLINE = "Online"
MQTT_STATUS_TOPIC = "raspberry/ashp/status"
MQTT_SENSORS_TOPIC = "raspberry/ashp/sensors"
MQTT_COMMAND_TOPIC = "raspberry/ashp/command"

DISCOVER_DIR = "homeassistant" # where the Home Assistant discovery files are located
DISCOVERY_PREFIX = "homeassistant" # prefix used for Home Assistant MQTT discovery

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

exit_event = threading.Event()

ashp = modbus_client.ModbusClient()

first_publish_done = False

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0 and client.is_connected():
        logging.info(f"Connected with flags [{flags}] reason code [{reason_code}]")
        client.subscribe(MQTT_COMMAND_TOPIC)
    else:
        logging.error(f'Failed to connect, return code {reason_code}')

def on_disconnect(client, userdata, flags, reason_code):
  logging.info(f"Disconnected with flags [{flags}] reason code [{reason_code}]")
  reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
  while reconnect_count < MAX_RECONNECT_COUNT:
    logging.info("Reconnecting in %d seconds...", reconnect_delay)
    time.sleep(reconnect_delay)

    try:
      client.reconnect()
      logging.info("Reconnected successfully!")
      return
    except Exception as err:
      logging.error("%s. Reconnect failed. Retrying...", err)

    reconnect_delay *= RECONNECT_RATE
    reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
    reconnect_count += 1
  logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)
  exit_event.set()  # Signal to exit the main loop

# Define the callback function for message handling
def on_message(client, userdata, msg):
  logging.info(f"Receiving topic {msg.topic}: {msg.payload.decode()}")
  # Assuming the payload is a JSON string with a method name and arguments
  try:
    message = json.loads(msg.payload.decode())
    method_name = message.get('method')
    value = message.get('value')

    # Call the method on the ashp object
    if hasattr(ashp, method_name):
      method = getattr(ashp, method_name)
      method(value)
    else:
      logging.error(f"Method {method_name} not found on ashp object")
  except json.JSONDecodeError:
    logging.error("Failed to decode JSON message")

def connect_mqtt():
  client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, CLIENT_ID)
  client.on_connect = on_connect
  client.on_message = on_message
  client.connect(MQTT_HOST, MQTT_PORT, keepalive=120)
  client.on_disconnect = on_disconnect
  return client

def publish_ha_discovery_config(client):
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

def publish(client):
  global first_publish_done

  # Record current date and time for message timestamp
  now = datetime.now()

  # Format message timestamp to mm/dd/YY H:M:S
  last_message = now.strftime("%m/%d/%Y %H:%M:%S")

  # Get current system uptime
  sys_uptime = uptime()

  # Create JSON dict for MQTT transmission
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

  # Publish status and sensor data to mqtt
  client.publish(MQTT_STATUS_TOPIC, MQTT_ONLINE, qos=0)
  client.publish(MQTT_SENSORS_TOPIC, payload_sensors, qos=0)

  if not first_publish_done:
    logging.info("Publishing first dump of sensor data...")
    first_publish_done = True

  # Debugging...
  if DEBUG_MODE:
    logging.info(payload_sensors)

def run():
  # Start the HTTP server in a separate thread
  http_status_server.run_http_server_in_thread(flag_connected)

  # Start the MQTT loop
  client = connect_mqtt()
  client.loop_start()

  try:
    while not exit_event.is_set():
      if client.is_connected():
        publish(client)
      time.sleep(MSG_INTERVAL)
  finally:
    client.loop_stop()

if __name__ == '__main__':
  run()
