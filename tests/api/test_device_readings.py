import pytest
from unittest import mock
from rest_framework.test import APIClient
from api.models import Device

# Test: když zařízení existuje, endpoint vrací čtení z MongoDB
@pytest.mark.django_db
@mock.patch("api.views.MongoClient")
def test_readings_success(mock_mongo):
    # Vytvoříme testovací zařízení v PostgreSQL
    device = Device.objects.create(name="SensorA", serial_number="XYZ987")
    
    # Fake data, která by jinak přišla z MongoDB
    fake_data = [
        {'_id': 'abc1', 'temperature': 21.5, 'humidity': 60, 'timestamp': 1690000000, 'source': 'modbus'},
        {'_id': 'abc2', 'temperature': 22.0, 'humidity': 58, 'timestamp': 1690000100, 'source': 'modbus'}
    ]

    # Mockujeme MongoClient tak, aby find() → sort() → limit() → vrátil fake data
    mock_client = mock_mongo.return_value
    mock_db = mock_client.get_database.return_value
    mock_coll = mock_db.modbus_data
    mock_coll.find.return_value.sort.return_value.limit.return_value = fake_data

    # Voláme API endpoint
    client = APIClient()
    response = client.get(f"/api/clients/{device.id}/readings/")

    # Ověříme, že odpověď je OK a obsahuje data z Mongo
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 2
    assert result[0]["temperature"] == 21.5
    assert result[1]["humidity"] == 58

# Test: pokud zařízení neexistuje, endpoint vrací 404
@pytest.mark.django_db
@mock.patch("api.views.MongoClient")
def test_readings_device_not_found(mock_mongo):
    # Pro jistotu nastavíme Mongo mock, i když by se neměl použít
    mock_client = mock_mongo.return_value
    mock_db = mock_client.get_database.return_value
    mock_db.modbus_data.find.return_value.sort.return_value.limit.return_value = []

    client = APIClient()
    response = client.get("/api/clients/9999/readings/")

    # Očekáváme 404, protože zařízení s tímto ID neexistuje
    assert response.status_code == 404
