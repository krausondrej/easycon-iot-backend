import pytest
from rest_framework.test import APIClient
from api.models import Device

# Fixture: vytvoří DRF API klienta pro testy
@pytest.fixture
def api_client():
    return APIClient()

# Test: zařízení se úspěšně vytvoří (201)
@pytest.mark.django_db
def test_create_device_success(api_client):
    url = '/api/clients/'
    payload = {'name': 'Device1', 'serial_number': 'SN123'}

    response = api_client.post(url, data=payload, format='json')
    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'Device1'
    assert data['serial_number'] == 'SN123'

    # Ověříme, že zařízení bylo opravdu vytvořeno v databázi
    assert Device.objects.filter(serial_number='SN123').exists()

# Test: pokud chybí oba required fieldy, API vrací 400 + chybové hlášky
@pytest.mark.django_db
def test_create_device_missing_fields(api_client):
    url = '/api/clients/'
    response = api_client.post(url, data={}, format='json')

    assert response.status_code == 400
    errors = response.json()
    assert 'name' in errors
    assert 'serial_number' in errors

# Test: pokus o vytvoření zařízení se stejným serial_numberem selže (unikátnost)
@pytest.mark.django_db
def test_duplicate_serial_number(api_client):
    # Předpřipravíme zařízení se stejným serial_numberem
    Device.objects.create(name='Existing', serial_number='SN_DUP')

    url = '/api/clients/'
    payload = {'name': 'NewDevice', 'serial_number': 'SN_DUP'}
    response = api_client.post(url, data=payload, format='json')

    assert response.status_code == 400
    errors = response.json()
    assert 'serial_number' in errors

# Test: update existujícího zařízení funguje a vrací změněná data
@pytest.mark.django_db
def test_update_device(api_client):
    device = Device.objects.create(name='Old', serial_number='SN_UPD')
    url = f'/api/clients/{device.id}/'
    payload = {'name': 'Updated', 'serial_number': 'SN_UPD2'}

    response = api_client.put(url, data=payload, format='json')
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'Updated'
    assert data['serial_number'] == 'SN_UPD2'

    # Ověříme, že změny proběhly i v databázi
    device.refresh_from_db()
    assert device.name == 'Updated'
    assert device.serial_number == 'SN_UPD2'

# Test: zařízení se úspěšně smaže (204), pak už není v databázi
@pytest.mark.django_db
def test_delete_device(api_client):
    device = Device.objects.create(name='ToDelete', serial_number='SN_DEL')
    url = f'/api/clients/{device.id}/'

    response = api_client.delete(url)
    assert response.status_code == 204

    # Kontrola, že záznam byl smazán
    assert not Device.objects.filter(id=device.id).exists()
