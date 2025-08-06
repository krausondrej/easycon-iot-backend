# Struktura systému

- **Django REST API** – správa zařízení, čtení dat, odesílání příkazů
- **MQTT publisher / subscriber** – příjem a publikace dat ze zařízení
- **Modbus TCP server / klient** – simulace a čtení hodnot z registrů
- **MongoDB a PostgreSQL** – databáze pro senzorická data a aplikační data
- **Mosquitto (MQTT broker)** – přenos zpráv mezi zařízeními

## Spuštění projektu

1. Klon:

```bash
git clone https://github.com/krausondrej/easycon-iot-backend.git
```

2. Docker Compose:

```bash
docker-compose up --build
```

3. Testy:

```bash
docker-compose run --rm tests
```

## Poznámky

- `.env` soubory se načítají automaticky.
- MQTT broker je ve výchozím nastavení bez TLS a autentizace.
- Testy využívají mocking a běží odděleně od reálných zařízení.
- Do `.env` pridat vlastni SECRET_KEY.