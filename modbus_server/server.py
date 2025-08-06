import os
import time
import threading
import requests
from dotenv import load_dotenv
from pymodbus.server import StartTcpServer
from pymodbus import ModbusDeviceIdentification
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusDeviceContext,
    ModbusServerContext,
)

# Načteme proměnné z .env
load_dotenv('.env')

# Konfigurace
MODBUS_HOST = os.getenv('MODBUS_HOST', 'localhost')
MODBUS_PORT = int(os.getenv('MODBUS_PORT', 502))
API_URL = os.getenv('API_URL', 'http://localhost:8000/api/data/')

# Vytvoření device contextu s 100 registrů pro každý typ
store = ModbusDeviceContext(
    di=ModbusSequentialDataBlock(0, [0] * 100),
    co=ModbusSequentialDataBlock(0, [0] * 100),
    hr=ModbusSequentialDataBlock(0, [0] * 100),
    ir=ModbusSequentialDataBlock(0, [0] * 100),
)
context = ModbusServerContext(store, single=True)

def fetch_data():
    try:
        resp = requests.get(API_URL)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("Error fetching data from API:", e)
        raise

def updating_writer():
    while True:
        try:
            data = fetch_data()
            temp = int(data.get('temperature', 0) * 10)
            hum = int(data.get('humidity', 0) * 10)
            context[0].setValues(3, 1, [temp, hum])
            print(f"Updated registers: temp={temp}, hum={hum}")
        except Exception as e:
            print("Modbus update error:", e)
        time.sleep(5)

def main():
    # Identifikace serveru
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'EasyCon'
    identity.ProductCode = 'EC'
    identity.VendorUrl = 'http://example.com'
    identity.ProductName = 'EasyCon Modbus Server'
    identity.ModelName = 'EC-Modbus'
    identity.MajorMinorRevision = '1.0'

    # Spuštění vlákna pro zápis do registrů
    thread = threading.Thread(target=updating_writer, daemon=True)
    thread.start()

    # Start TCP serveru
    print(f"Starting Modbus server on {MODBUS_HOST}:{MODBUS_PORT}")
    StartTcpServer(context, identity=identity, address=(MODBUS_HOST, MODBUS_PORT))

if __name__ == "__main__":
    main()
