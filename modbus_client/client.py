import os
import time
from dotenv import load_dotenv
from pymodbus.client import ModbusTcpClient
from pymongo import MongoClient

# Načteme proměnné z .env
load_dotenv('.env')

# Konfigurace
MONGO_URI    = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MODBUS_HOST  = os.getenv('MODBUS_HOST', 'localhost')
MODBUS_PORT  = int(os.getenv('MODBUS_PORT', 502))
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 5))

# Připojení k MongoDB
mongo = MongoClient(MONGO_URI)
db = mongo.get_database()
coll = db.get_collection('modbus_data')

# Modbus klient
client = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)

def read_and_store():
    rr = client.read_holding_registers(1, 2, unit=1)
    if not rr.isError():
        temp = rr.registers[0] / 10.0
        hum  = rr.registers[1] / 10.0
        doc = {
            'temperature': temp,
            'humidity': hum,
            'source': 'modbus',
            'timestamp': time.time()
        }
        coll.insert_one(doc)
        print("Stored to MongoDB:", doc)
    else:
        print("Modbus read error:", rr)

def main():
    client.connect()
    print(f"Connected to Modbus server at {MODBUS_HOST}:{MODBUS_PORT}")
    while True:
        try:
            read_and_store()
        except Exception as e:
            print("Error during Modbus polling:", e)
        time.sleep(POLL_INTERVAL)

# Spustí se pouze pokud je soubor spuštěn napřímo
if __name__ == "__main__":
    main()
