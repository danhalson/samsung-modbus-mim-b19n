from dotenv import load_dotenv
from gpiozero import CPUTemperature
from os.path import join, dirname
import time
import paho.mqtt.client as mqtt
import json
import os
from datetime import datetime
import modbus_client

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Load .env variables
MQTT_USER = os.environ.get('MQTT_USER')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD')
MQTT_HOST = os.environ.get('MQTT_HOST')
MQTT_PORT = int(os.environ.get('MQTT_PORT'))

# Global variable definition
flag_connected = 0 # Loop flag for waiting to connect to MQTT broker

# Constant variable definition
MQTT_STATUS_TOPIC = "raspberry/ashp/status"
MQTT_SENSORS_TOPIC = "raspberry/ashp/sensors"

# Define variables
interval = 10 # Data collection interval in secs. 5 mins = 5 * 60 = 300

# MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected with flags [%s] rtn code [%d]"% (flags, rc) )
    global flag_connected
    flag_connected = 1

def on_disconnect(client, userdata, rc):
    print("disconnected with rtn code [%d]"% (rc) )
    global flag_connected
    flag_connected = 0

# TODO: Migrate to V2 (https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.connect(MQTT_HOST, MQTT_PORT)

# System Uptime
def uptime():
    t = os.popen('uptime -p').read()[:-1]
    uptime = t.replace('up ', '')
    return uptime

# Read CPU temp for future fan logic
cpu = CPUTemperature()

ashp = modbus_client.ModbusClient()

# Main loop
if __name__ == '__main__':
    client.loop_start()

    # Wait to receive the connected callback for MQTT
    while flag_connected == 0:
        print("Not connected. Waiting 1 second.")
        time.sleep(1)

    while True:
        start_time = time.time()

        cpu_temp = round(cpu.temperature, 1)

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
            # 'compressor_freq': ashp.get_compressor_freq(),
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
            'sys_uptime': sys_uptime,
            'last_message': last_message,
            'cpu_temp': cpu_temp
        }

        # Convert message to json
        payload_sensors = json.dumps(send_msg)

        # Debugging (used when testing and need to print variables)
        # print(payload_sensors)

        # Set status payload
        payload_status = "Online"

        # Publish status to mqtt
        client.publish(MQTT_STATUS_TOPIC, payload_status, qos=0)

        # Publish sensor data to mqtt
        client.publish(MQTT_SENSORS_TOPIC, payload_sensors, qos=0)
        
        # Wait for the interval
        time.sleep(interval)
        
client.loop_stop()
print("Loop Stopped.")
client.disconnect()
print("MQTT Disconnected.")
