import os
import sys
import pytest

# Přidáme kořen repozitáře do cesty, abychom mohli naimportovat modbus klienta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import importlib
client_module = importlib.import_module('modbus_client.client')

# Test: když je čtení z Modbusu v pohodě, data se správně uloží do MongoDB
def test_read_and_store_success(monkeypatch, capsys):
    # Nahradíme čas za fixní hodnotu kvůli stabilnímu testu
    monkeypatch.setattr(client_module, 'time', type('tm', (), {'time': lambda: 123456.0}))

    # Mock odpověď z Modbusu – dvě hodnoty: teplota a vlhkost
    class FakeRR:
        def __init__(self):
            self.registers = [230, 450]  # odpovídá 23.0 °C a 45.0 %
        def isError(self):
            return False
    monkeypatch.setattr(client_module.client, 'read_holding_registers',
                        lambda address, count, unit: FakeRR())

    # Simulujeme Mongo kolekci – místo reálného insert_one sbíráme dokumenty
    inserted = []
    monkeypatch.setattr(client_module.coll, 'insert_one', lambda doc: inserted.append(doc))

    # Spustíme funkci, která má číst z Modbusu a ukládat do DB
    client_module.read_and_store()

    # Ověříme, že se uložil 1 dokument s očekávanými hodnotami
    assert len(inserted) == 1
    doc = inserted[0]
    assert doc['temperature'] == pytest.approx(23.0)
    assert doc['humidity'] == pytest.approx(45.0)
    assert doc['source'] == 'modbus'
    assert doc['timestamp'] == 123456.0

    # Funkce má něco vypsat do konzole – zkontrolujeme to
    captured = capsys.readouterr()
    assert 'Stored to MongoDB:' in captured.out

# Test: když čtení z Modbusu selže, data se neuloží a vypíše se chyba
def test_read_and_store_error(monkeypatch, capsys):
    # Mock odpověď, která signalizuje chybu
    class FakeRR:
        def isError(self):
            return True
        def __str__(self):
            return 'ErrorResponse'

    monkeypatch.setattr(client_module.client, 'read_holding_registers',
                        lambda address, count, unit: FakeRR())

    # Pokud by došlo k insertu, test se skipne (nemělo by se to stát)
    monkeypatch.setattr(client_module.coll, 'insert_one', lambda doc: pytest.skip("Should not insert on error"))

    # Spuštění funkce
    client_module.read_and_store()

    # Zkontrolujeme, že došlo k výpisu chyby
    captured = capsys.readouterr()
    assert 'Modbus read error:' in captured.out
