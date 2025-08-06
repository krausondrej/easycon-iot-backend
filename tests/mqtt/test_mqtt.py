import os
import sys
import pytest
import requests
import importlib
import json
import time

# Přidá kořenový adresář do cesty pro importy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Fixture: nastaví environment proměnné pro testované moduly
@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv('API_URL', 'http://example.com/data')
    monkeypatch.setenv('MQTT_HOST', 'mqtt.local')
    monkeypatch.setenv('MQTT_PORT', '1883')
    monkeypatch.setenv('MQTT_USER', 'user')
    monkeypatch.setenv('MQTT_PASSWORD', 'pass')
    monkeypatch.setenv('CLIENT_ID', 'test-client')
    monkeypatch.setenv('PUBLISH_INTERVAL', '1')
    yield

# Fixture: nahradí skutečný MQTT klient dummy třídou
@pytest.fixture(autouse=True)
def disable_mqtt(monkeypatch):
    class DummyClient:
        def __init__(self, *args, **kwargs): pass
        def username_pw_set(self, user, pwd): pass
        def on_connect(self, *args, **kwargs): pass
        def on_message(self, *args, **kwargs): pass
        def connect(self, host, port): pass
        def loop_start(self): pass
        def publish(self, topic, payload=None): pass
    monkeypatch.setattr('paho.mqtt.client.Client', DummyClient)
    yield

# Načte testovaný modul až po aplikaci patchů
client_module = importlib.import_module('mqtt_client.client')

# Test: správné zpracování platné odpovědi z API
def test_fetch_data_success(monkeypatch):
    fake_data = {'temperature': 25.0, 'humidity': 60}
    
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return fake_data

    monkeypatch.setattr(requests, 'get', lambda url: FakeResp())

    result = client_module.fetch_data()
    assert result == fake_data

# Test: API odpověď vyhodí chybu - funkce vrací prázdný slovník
def test_fetch_data_error(monkeypatch):
    class FakeResp:
        def raise_for_status(self): raise requests.HTTPError("API error")
        def json(self): return {}

    monkeypatch.setattr(requests, 'get', lambda url: FakeResp())

    result = client_module.fetch_data()
    assert result == {}

# Test: funkce publish_loop publikuje získaná data
def test_publish_loop_success(monkeypatch):
    published = []

    monkeypatch.setattr(client_module, 'fetch_data', lambda: {'test': True})

    # Dummy MQTT klient pro zachycení publikací
    class FakeClient:
        def publish(self, topic, payload=None):
            published.append((topic, payload))

    monkeypatch.setattr(client_module, 'client', FakeClient())

    # Fake sleep k okamžitému přerušení smyčky
    monkeypatch.setattr(time, 'sleep', lambda s: (_ for _ in ()).throw(StopIteration))

    with pytest.raises(StopIteration):
        client_module.publish_loop(interval=0)

    # Ověří, že došlo k jedné publikaci s očekávanými daty
    assert published == [(client_module.PUBLISH_TOPIC, json.dumps({'test': True}))]

# Test: fetch_data vyhodí chybu - žádná publikace se neprovede
def test_publish_loop_fetch_error(monkeypatch):
    def failing_fetch():
        raise ValueError("fetch failed")

    monkeypatch.setattr(client_module, 'fetch_data', failing_fetch)

    class FakeClient:
        def publish(self, topic, payload=None): pytest.fail("Should not be called")

    monkeypatch.setattr(client_module, 'client', FakeClient())

    with pytest.raises(ValueError, match="fetch failed"):
        client_module.publish_loop(interval=0)
