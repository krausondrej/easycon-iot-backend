import json

from mqtt_subscriber import subscriber

# Dummy třída pro simulaci Mongo kolekce
class DummyMongoColl:
    def __init__(self):
        self.inserted = []

    # Uloží dokument do seznamu
    def insert_one(self, doc):
        self.inserted.append(doc)

# Dummy zpráva pro simulaci MQTT zprávy
class DummyMsg:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload

# Dummy klient pro ověření subscribe funkce
class DummyMqttClient:
    def __init__(self):
        self.subscribed = []

    # Zaznamená přihlášení k tématu
    def subscribe(self, topic):
        self.subscribed.append(topic)

# Testuje, že on_connect funkce přihlásí MQTT klienta k tématu
def test_on_connect_subscribes():
    mqttc = DummyMqttClient()
    subscriber.on_connect(mqttc, userdata=None, flags=None, rc=0)
    assert mqttc.subscribed == ["client/+/data"]

# Testuje, že on_message správně uloží validní JSON do Mongo kolekce
def test_on_message_inserts(monkeypatch):
    dummy_coll = DummyMongoColl()
    monkeypatch.setattr(subscriber, "db", type("X", (), {"modbus_data": dummy_coll}))
    
    payload = {"timestamp": 1234.5, "temperature": 22.1, "humidity": 55}
    msg = DummyMsg(topic="client/42/data", payload=json.dumps(payload).encode())

    subscriber.on_message(mqtt_client=None, userdata=None, msg=msg)

    assert len(dummy_coll.inserted) == 1
    doc = dummy_coll.inserted[0]
    assert doc["device_id"] == 42
    assert doc["timestamp"] == payload["timestamp"]
    assert doc["temperature"] == payload["temperature"]
    assert doc["humidity"] == payload["humidity"]

# Testuje, že on_message zachytí chybný JSON a nezpůsobí pád
def test_on_message_handles_bad_json(monkeypatch, capsys):
    class BadDummyColl:
        def insert_one(self, doc):
            pass

    monkeypatch.setattr(subscriber, "db", type("X", (), {"modbus_data": BadDummyColl()}))

    msg = DummyMsg(topic="client/5/data", payload=b"not-json")
    subscriber.on_message(mqtt_client=None, userdata=None, msg=msg)

    captured = capsys.readouterr()
    assert "Error saving message" in captured.out
