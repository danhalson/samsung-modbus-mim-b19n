# samsung-modbus-mim-b19n

Example python script to for testing reading and writing data to a Samsung Heat Pump or HVAC unit using a [MIM-B19N Modbus module](https://www.samsung.com/uk/support/model/MIM-B19N/), [purchase from Midsummer](https://midsummerwholesale.co.uk/buy/samsung-heat-pumps/Samsung-modbus-MIM-B19) 

## Tested with:

- AE050RXYDEG-EU Gen6 ASHP
- Raspberry Pi with [USB Modbus reader](https://shop.openenergymonitor.com/modbus-rs485-to-usb-adaptor/)
- Python 3

## Setup a virtual environment

```
python3 -m venv venv
```

### Activate it on Linux / MacOS

```
source venv/bin/activate
```
### On Windows
```
.\venv\Scripts\activate
```

## Install python module
```
pip3 install minimalmodbus dotenv gpiozero paho-mqtt
```

## Test the modbus connection


```
python3 samsung-modbus.py
```

### Example output:

```
Central heating status: 0
Target indoor temp: 21.0
Indoor temp: 22.7
Target flow temp: 25.0
Flow temp: 32.7
Return temp: 33.6
DHW status: 1
DHW target temp: 55.0
DHW temp: 49.8
Away mode status: 0
```

## To run the mqtt client

### Create .env file

```
cp .env-example .env
```

Update the values to point at your MQTT server (this could be the homeassistant addon).

### Run the client manually

```
python3 mqtt_client.py
```

### Run the client as a service

## Running Script When Pi Starts

```
sudo cp samsung_modbus.service /etc/systemd/system/
```

Systemd needs to be made aware of the configuration change. Reload the systemd daemon with the following:

```
sudo systemctl daemon-reload
```

Enable the new service:

```
sudo systemctl enable samsung_modbus.service
```

Restart the pi and once the network services are loaded, the script should run and start broadcasting sensor data over MQTT. If it doesn't, type in this command to see the status of the service and diagnose from there.

```
sudo systemctl status samsung_modbus.service
```

## Control commands

It currently supports turning on/off the CH and DHW

## Next steps

- [**DONE:**](https://github.com/openenergymonitor/emonhub/tree/master/conf/interfacer_examples/samsung-ashp) Integrated this into a [EmonHub](https://github.com/openenergymonitor/emonhub) interfacer module to log the data to MQTT and [Emoncms](https://github.com/emoncms/emoncms) 
- Home Assistant integration? (can anyone help with this?)
- NodeRED module? (can anyone help with this?)

## More Resources 

More info on Samsung communication protocols including the NASA protocol which is used for communication between indoor and outdoor units can be found here: https://wiki.myehs.eu/wiki/Main_Page




