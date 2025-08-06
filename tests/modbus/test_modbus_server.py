import os
import sys
import pytest
import importlib

# Přidáme repozitář do cesty, abychom mohli naimportovat modbus_server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Fixture: nahradíme time.sleep za okamžité přerušení (kvůli rychlosti testů)
@pytest.fixture(autouse=True)
def stop_sleep(monkeypatch):
    import time
    # Po jednom volání sleep rovnou vyhodí výjimku → smyčka se ukončí
    monkeypatch.setattr(time, 'sleep', lambda s: (_ for _ in ()).throw(StopIteration))
    yield

# Test: fetch_data vrací očekávaná data když je API odpověď OK
def test_fetch_data_success(monkeypatch):
    server = importlib.import_module('modbus_server.server')

    class FakeResp:
        def __init__(self, status_code, data):
            self.status_code = status_code
            self._data = data
        def raise_for_status(self):
            if self.status_code != 200:
                raise pytest.fail("Unexpected status code")
        def json(self):
            return self._data

    fake = {'temperature': 21.5, 'humidity': 48}
    monkeypatch.setattr(server.requests, 'get', lambda url: FakeResp(200, fake))

    result = server.fetch_data()
    assert result == fake

# Test: fetch_data vyhodí výjimku když API vrátí chybu
def test_fetch_data_error(monkeypatch):
    server = importlib.import_module('modbus_server.server')

    class FakeResp:
        def raise_for_status(self):
            raise server.requests.HTTPError("Bad API")

    monkeypatch.setattr(server.requests, 'get', lambda url: FakeResp())

    with pytest.raises(server.requests.HTTPError):
        server.fetch_data()

# Test: updating_writer zapisuje správné hodnoty do registrů, pokud API vrátí data
def test_updating_writer_success(monkeypatch, capsys):
    server = importlib.import_module('modbus_server.server')

    # Vytvoříme fake data (temp a vlhkost)
    monkeypatch.setattr(server, 'fetch_data', lambda: {'temperature': 20.0, 'humidity': 50.0})

    # Místo skutečného zápisu do registrů si uložíme hodnoty do seznamu
    calls = []
    def fake_setValues(mode, address, values):
        calls.append((mode, address, values))
    monkeypatch.setattr(server.context[0], 'setValues', fake_setValues)

    # Očekáváme StopIteration, protože sleep je fake
    with pytest.raises(StopIteration):
        server.updating_writer()

    # Ověříme, že došlo ke správnému zápisu (temp a hum * 10)
    assert calls == [(3, 1, [200, 500])]
    out = capsys.readouterr().out
    assert "Updated registers: temp=200, hum=500" in out

# Test: když fetch_data selže, do registrů se nic nezapisuje
def test_updating_writer_error(monkeypatch, capsys):
    server = importlib.import_module('modbus_server.server')

    # fetch_data simuluje výjimku
    monkeypatch.setattr(server, 'fetch_data', lambda: (_ for _ in ()).throw(ValueError("fail")))

    # Zápis do registrů by se neměl vůbec zavolat
    monkeypatch.setattr(server.context[0], 'setValues', lambda *args, **kwargs: pytest.skip("Should not set on error"))

    with pytest.raises(StopIteration):
        server.updating_writer()

    # Ověříme, že se do konzole zalogovala chyba
    out = capsys.readouterr().out
    assert "Modbus update error:" in out
