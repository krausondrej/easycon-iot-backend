import json
import os
import time
from pymongo import MongoClient
import paho.mqtt.client as mqtt

# Načtení konfigurace z prostředí (Docker, .env...)
MONGO_URI = os.getenv('MONGO_URI')
MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))

# Připojení k MongoDB
client = MongoClient(MONGO_URI)
db = client.get_database()

# Callback: po připojení k MQTT brokeru se přihlásíme k tématu
def on_connect(mqtt_client, userdata, flags, rc):
    mqtt_client.subscribe("client/+/data")

# Callback: když dorazí zpráva, pokusíme se ji uložit do Mongo
def on_message(mqtt_client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())

        # Vytáhneme device_id z topicu – např. z "client/3/data" → 3
        device_id = int(msg.topic.split('/')[1])

        # Připravíme dokument k uložení
        doc = {
            'device_id': device_id,
            'timestamp': payload.get('timestamp', time.time()),  # fallback na aktuální čas
            **payload  # přidá všechny ostatní hodnoty (teplota, vlhkost...)
        }

        db.modbus_data.insert_one(doc)
    except Exception as e:
        print("Error saving message:", e)

# Hlavní smyčka – spustí MQTT klienta a poslouchá navždy
if __name__ == "__main__":
    mqttc = mqtt.Client()
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(MQTT_HOST, MQTT_PORT)
    mqttc.loop_forever()
