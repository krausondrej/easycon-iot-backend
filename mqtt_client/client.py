import os
import time
import json
import requests
import socket
from dotenv import load_dotenv
from pathlib import Path
import paho.mqtt.client as mqtt

# Detekuje .env soubor podle prostředí – vývoj nebo Docker
env_path = Path("/app/.env")
if not env_path.exists():
    # fallback pro spuštění mimo Docker
    current_dir = Path(__file__).resolve().parent
    env_path = current_dir.parent / "backend" / ".env"

load_dotenv(dotenv_path=env_path)
print(f"Loaded .env from: {env_path}")

# Konfigurace z prostředí
MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PASS = os.getenv('MQTT_PASSWORD')
CLIENT_ID = os.getenv('CLIENT_ID', 'default')

# MQTT témata
CONTROL_TOPIC = f"client/{CLIENT_ID}/control"
PUBLISH_TOPIC = "api/data"

# API endpoint pro fetch dat
API_URL = os.getenv('API_URL', 'http://backend:8000/api/data/')
PUBLISH_INTERVAL = int(os.getenv('PUBLISH_INTERVAL', 30))  # interval publikace v sekundách

publishing_enabled = True  # řízení pomocí MQTT příkazů

# MQTT klient

client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

# Nastavíme autentizaci pro MQTT broker
if MQTT_USER and MQTT_PASS:
    client.username_pw_set(MQTT_USER, MQTT_PASS)
else:
    raise Exception("MQTT_USER or MQTT_PASSWORD not set!")

# MQTT callbacky
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
        client.subscribe(CONTROL_TOPIC)  # posloucháme kontrolní příkazy
        print(f"Subscribed to {CONTROL_TOPIC} for control commands.")
    else:
        print(f"Failed to connect to MQTT broker, return code: {rc}")

def on_message(client, userdata, msg):
    global publishing_enabled
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get('command', '').strip().lower()
        print(f"Received command: {command}")
        # Přepínání stavu publikace
        if command == 'stop':
            publishing_enabled = False
            print("Data publishing stopped.")
        elif command == 'start':
            publishing_enabled = True
            print("Data publishing started.")
        else:
            print(f"Unknown command: {command}")
    except Exception as e:
        print("Failed to process control message:", e)

# Přiřazení callbacků
client.on_connect = on_connect
client.on_message = on_message

# Kontrola dostupnosti MQTT brokeru
def wait_for_broker(host, port, max_retries=10, delay=3):
    for i in range(max_retries):
        try:
            print(f"Attempting to connect to MQTT broker at {host}:{port} (try {i+1})")
            with socket.create_connection((host, port), timeout=5):
                print("MQTT broker is reachable.")
                return True
        except Exception as e:
            print(f"MQTT broker not reachable: {e}")
            time.sleep(delay)
    print("Giving up after", max_retries, "attempts.")
    return False

# Hlavní smyčka pro fetch & publish
def fetch_data():
    try:
        resp = requests.get(API_URL)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print("Error fetching data:", e)
        return {}

def publish_loop(interval=PUBLISH_INTERVAL):
    while True:
        if publishing_enabled:
            data = fetch_data()
            if data:
                client.publish(PUBLISH_TOPIC, payload=json.dumps(data))
                print(f"Published to {PUBLISH_TOPIC}: {data}")
        else:
            print("Publishing paused.")
        time.sleep(interval)

# Spuštění celého klienta
def start():
    if not wait_for_broker(MQTT_HOST, MQTT_PORT):
        return
    try:
        client.connect(MQTT_HOST, MQTT_PORT)
        client.loop_start()  # běží na pozadí
    except Exception as e:
        print("Final connection to MQTT broker failed:", e)
        return
    publish_loop()

if __name__ == "__main__":
    start()
