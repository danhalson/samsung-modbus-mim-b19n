#!/usr/bin/python3
import minimalmodbus
import serial
import time
import threading

# Define constants
DEBUG_MODE = False
SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 9600 # Baud
BYTESIZE = 8
PARITY = serial.PARITY_EVEN
STOPBITS = 1
TIMEOUT = 1 # seconds
SLAVE_ADDRESS = 1 # this is the slave address number
MODE = minimalmodbus.MODE_RTU # rtu or ascii mode
STD_INTERVAL = 0.5
RETRIES = 3
RETRY_DELAY = 5

# TODO: Get CH mode
# TODO: Get target flow temp (taking weather compensation into account, if possible)
# TODO: Set indoor temp? if this makes sense

class ModbusClient(object):
    def __init__(self):
        print("Connecting to device...")
        
        self.lock = threading.Lock()
        
        self.instrument = minimalmodbus.Instrument(SERIAL_PORT, SLAVE_ADDRESS)
        self.instrument.serial.port = SERIAL_PORT
        self.instrument.serial.baudrate = BAUDRATE
        self.instrument.serial.bytesize = BYTESIZE
        self.instrument.serial.parity = PARITY
        self.instrument.serial.stopbits = STOPBITS
        self.instrument.serial.timeout = TIMEOUT
        self.instrument.debug = DEBUG_MODE
        self.instrument.address = SLAVE_ADDRESS
        self.instrument.mode = MODE
        
        self.instrument.write_registers(7005, [0x42E9, 0x42F1, 0x4067, 0x8204])
        
        try:
            assert self.get_outdoor_temp(), "Failed to connect to device"
        except AssertionError as e:
            print(f"Error: {e}") 
            
    def get_outdoor_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(5, 3, True)
        return self.round(raw_value)
    
    def get_flow_rate(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(87, 3)
        return self.round(raw_value)
    
    def get_three_way_valve_position(self):
        time.sleep(STD_INTERVAL)
        return self.safe_read_register(89, 3)
    
    def get_compressor_freq(self):
        time.sleep(1)
        raw_value = self.safe_read_register(88, 3)
        return self.round(raw_value)
    
    def get_dhw_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(75, 3, True)
        return self.round(raw_value)
    
    def get_return_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(65, 3, True)
        return self.round(raw_value)
    
    def get_flow_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(66, 3, True)
        return self.round(raw_value)
    
    def get_target_flow_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(68, 3)
        return self.round(raw_value)
    
    def get_dhw_status(self):
        time.sleep(STD_INTERVAL)
        return self.safe_read_register(72, 3)
    
    def get_target_dhw_temp(self):
        raw_value = self.safe_read_register(74, 3)
        time.sleep(STD_INTERVAL)
        return self.round(raw_value)
    
    def get_away_status(self):
        time.sleep(STD_INTERVAL)
        return self.safe_read_register(79, 3)
    
    def get_ch_status(self):
        time.sleep(STD_INTERVAL)
        return self.safe_read_register(52, 3)
    
    def get_indoor_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(59, 3, True)
        return self.round(raw_value)
    
    def get_target_indoor_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.safe_read_register(58, 3, True)
        return self.round(raw_value)
    
    def get_defrost_status(self):
        time.sleep(STD_INTERVAL)
        return self.safe_read_register(2, 3)
    
    def get_dhw_mode(self):
        time.sleep(STD_INTERVAL)
        return self.safe_read_register(73, 3)

    def get_error_code(self):
        time.sleep(STD_INTERVAL)
        error_1 = self.safe_read_register(63, 3)
        error_2 = self.safe_read_register(64, 3)
        return error_1, error_2
    
    def set_ch_status(self, value):
        if value not in [0, 1]:
            raise ValueError("Invalid value for CH status. Only 0 or 1 is allowed.")
        
        return self.safe_write_register(52, value)
    
    def set_dhw_status(self, value):
        if value not in [0, 1]:
            raise ValueError("Invalid value for DHW status. Only 0 or 1 is allowed.")
        
        return self.safe_write_register(72, value)
    
    def safe_read_register(self, reg, fcode, signed=False):
        with self.lock:
            for attempt in range(RETRIES + 1):
                try:
                    result = self.instrument.read_register(
                        reg, functioncode = fcode, signed = signed
                    ) 
                    if result is None:
                        return None
                    return result
                except minimalmodbus.NoResponseError as e:
                    if attempt < RETRIES:
                        time.sleep(RETRY_DELAY)
                except serial.SerialException as e:
                    print(f"SerialException: {e}")
                    self.reconnect_serial()
                    if attempt < RETRIES:
                        time.sleep(RETRY_DELAY)
            print(f"Failed to read register {reg} after {RETRIES + 1} attempts.")
            return None

    def safe_write_register(self, reg, value):
        with self.lock:
            for attempt in range(RETRIES + 1):
                try:
                    result = self.instrument.write_register(reg, value)
                    if result is None:
                        return None
                    return result
                except minimalmodbus.NoResponseError as e:
                    if attempt < RETRIES:
                        time.sleep(RETRY_DELAY)
                except serial.SerialException as e:
                    print(f"SerialException: {e}")
                    self.reconnect_serial()
                    if attempt < RETRIES:
                        time.sleep(RETRY_DELAY)
            print(f"Failed to write register {reg} after {RETRIES + 1} attempts.")
            return None

    def reconnect_serial(self):
        try:
            self.instrument.serial.close()
            self.instrument.serial.open()
            print("Reconnected to serial device")
        except Exception as e:
            print(f"Failed to reconnect: {e}")

    def round(self, value):
        if value is None:
            return None
        return round(0.1 * value, 2)
        
    def millis(self):
        return int(round(time.time() * 1000))

if __name__ == "__main__":
    obj = ModbusClient()
    print("Outdoor temp: %s" % obj.get_outdoor_temp())
    print("Flow rate: %s" % obj.get_flow_rate())
    print("3 way valve position: %s" % obj.get_three_way_valve_position())
    print("Compressor freq: %s" % obj.get_compressor_freq())
    print("DHW temp: %s" % obj.get_dhw_temp())
    print("Return temp: %s" % obj.get_return_temp())
    print("Flow temp: %s" % obj.get_flow_temp())
    print("Target flow temp: %s" % obj.get_target_flow_temp())
    print("DHW status: %s" % obj.get_dhw_status())
    print("Target DHW temp: %s" % obj.get_target_dhw_temp())
    print("Away mode status: %s" % obj.get_away_status())
    print("Central heating status: %s" % obj.get_ch_status())
    print("Indoor temp: %s" % obj.get_indoor_temp())
    print("Target indoor temp: %s" % obj.get_target_indoor_temp())
    print("Defrost operation status: %s" % obj.get_defrost_status())
    print("Error code: %s" % obj.get_error_code())
    print("DHW mode: %s" % obj.get_dhw_mode())
