import pytest
from rest_framework.test import APIClient
from api.models import Device
from unittest import mock

# Fixture pro REST API klienta
@pytest.fixture
def api_client():
    return APIClient()

# Test zařízení dostane příkaz a vše projde OK (200)
@pytest.mark.django_db
def test_control_device_command_success(api_client):
    device = Device.objects.create(name='ControlledDevice', serial_number='CTRL001')

    # Mockujeme MQTT publish, abychom nezáviseli na brokeru
    with mock.patch('api.views.publish.single') as mock_publish:
        response = api_client.post(
            f'/api/clients/{device.id}/control/',
            {'command': 'stop'},
            format='json'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'sent'
        assert data['topic'] == f'client/{device.id}/control'
        assert 'stop' in data['payload']

        # Ověříme, že publish byl opravdu zavolán
        mock_publish.assert_called_once_with(
            f'client/{device.id}/control',
            data['payload'],
            hostname=mock.ANY,
            port=mock.ANY,
            auth=mock.ANY
        )

# Test když chybí command, API vrátí 400
@pytest.mark.django_db
def test_control_device_command_missing_command(api_client):
    device = Device.objects.create(name='MissingCommandDevice', serial_number='CTRL002')

    response = api_client.post(
        f'/api/clients/{device.id}/control/',
        {},
        format='json'
    )

    assert response.status_code == 400
    data = response.json()
    assert 'command' in data['error']

# Test pokud zařízení neexistuje, dostaneme 404
@pytest.mark.django_db
def test_control_device_not_found(api_client):
    response = api_client.post(
        '/api/clients/9999/control/',
        {'command': 'restart'},
        format='json'
    )
    assert response.status_code == 404

# Test pokud publish vyhodí chybu, API vrátí 500
@pytest.mark.django_db
def test_control_mqtt_publish_failure(api_client):
    device = Device.objects.create(name='MQTTFailureDevice', serial_number='CTRL003')

    with mock.patch('api.views.publish.single', side_effect=Exception("MQTT error")):
        response = api_client.post(
            f'/api/clients/{device.id}/control/',
            {'command': 'shutdown'},
            format='json'
        )

        assert response.status_code == 500
        data = response.json()
        assert 'error' in data

# Test command 'restart' funguje stejně jako ostatní – vrací 200 a publikuje
@pytest.mark.django_db
def test_control_device_command_restart(api_client):
    device = Device.objects.create(name='RestartDevice', serial_number='CTRL004')

    with mock.patch('api.views.publish.single') as mock_publish:
        response = api_client.post(
            f'/api/clients/{device.id}/control/',
            {'command': 'restart'},
            format='json'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'sent'
        assert 'restart' in data['payload']
        mock_publish.assert_called_once()

# Test pokud command není string (např. číslo), API vrací 400
@pytest.mark.django_db
def test_control_device_command_not_string(api_client):
    device = Device.objects.create(name='IntCommand', serial_number='CTRL006')
    
    response = api_client.post(
        f'/api/clients/{device.id}/control/',
        {'command': 12345},  # int místo string
        format='json'
    )

    assert response.status_code == 400
    data = response.json()
    assert 'command' in data['error']

# Test vícenásobné příkazy – každý se správně odešle zvlášť
@pytest.mark.django_db
def test_control_device_multiple_commands(api_client):
    device = Device.objects.create(name='MultiCommandDevice', serial_number='CTRL007')

    with mock.patch('api.views.publish.single') as mock_publish:
        for cmd in ['start', 'pause', 'resume']:
            response = api_client.post(
                f'/api/clients/{device.id}/control/',
                {'command': cmd},
                format='json'
            )
            assert response.status_code == 200
            assert cmd in response.json()['payload']

        # Ověření, že publish byl zavolán 3×
        assert mock_publish.call_count == 3
