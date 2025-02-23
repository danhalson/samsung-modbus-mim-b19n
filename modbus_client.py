#!/usr/bin/python3
import minimalmodbus
import serial
import struct
import time

# Define constants
SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 9600 # Baud
BYTESIZE = 8
PARITY = serial.PARITY_EVEN
STOPBITS = 1
TIMEOUT = 1 # seconds
SLAVE_ADDRESS = 1 # this is the slave address number
MODE = minimalmodbus.MODE_RTU # rtu or ascii mode
STD_INTERVAL = 0.5

class ModbusClient(object):
    def __init__(self):
        print("Connecting to device...")
        self.instrument = minimalmodbus.Instrument(SERIAL_PORT, SLAVE_ADDRESS)
        self.instrument.serial.port = SERIAL_PORT
        self.instrument.serial.baudrate = BAUDRATE
        self.instrument.serial.bytesize = BYTESIZE
        self.instrument.serial.parity = PARITY
        self.instrument.serial.stopbits = STOPBITS
        self.instrument.serial.timeout = TIMEOUT
        self.instrument.debug = False
        self.instrument.address = SLAVE_ADDRESS
        self.instrument.mode = MODE
        
        self.instrument.write_registers(7005,[0x42E9, 0x42F1, 0x4067, 0x8204])
        
        try:
            assert self.get_outdoor_temp(), "Failed to connect to device"
        except AssertionError as e:
            print(f"Error: {e}") 
            
    def get_outdoor_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(5, functioncode = 3, signed = True)
        return self.round(raw_value)
    
    def get_flow_rate(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(87, functioncode = 3)
        return self.round(raw_value)
    
    def get_three_way_valve_position(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(89, functioncode = 3)
        return round(raw_value)
    
    def get_compressor_freq(self):
        time.sleep(1)
        raw_value = self.instrument.read_register(88, functioncode = 3)
        return round(raw_value)
    
    def get_dhw_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(75, functioncode = 3, signed = True)
        return self.round(raw_value)
    
    def get_return_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(65, functioncode = 3, signed = True)
        return self.round(raw_value)
    
    def get_flow_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(66, functioncode = 3, signed = True)
        return self.round(raw_value)
    
    def get_target_flow_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(68, functioncode = 3)
        return self.round(raw_value)
    
    def get_dhw_status(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(72, functioncode = 3)
        return raw_value
    
    def get_target_dhw_temp(self):
        raw_value = self.instrument.read_register(74, functioncode = 3)
        time.sleep(STD_INTERVAL)
        return self.round(raw_value)
    
    def get_away_status(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(79, functioncode = 3)
        return raw_value
    
    def get_ch_status(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(52, functioncode = 3)
        return raw_value
    
    def get_indoor_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(59, functioncode = 3, signed = True)
        return self.round(raw_value)
    
    def get_target_indoor_temp(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(58, functioncode = 3, signed = True)
        return self.round(raw_value)
    
    def get_defrost_status(self):
        time.sleep(STD_INTERVAL)
        raw_value = self.instrument.read_register(2, functioncode = 3)
        return raw_value

    def round(self, value):
        return round(0.1 * value, 2)
    
    def millis(self):
        return int(round(time.time() * 1000))

    def C(self, val):
        return struct.pack('!H', val)

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
