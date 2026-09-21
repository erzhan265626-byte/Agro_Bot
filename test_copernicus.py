import os
import requests
from dotenv import load_dotenv


load_dotenv()

client_id = os.getenv("COPERNICUS_CLIENT_ID")
client_secret = os.getenv("COPERNICUS_CLIENT_SECRET")


if not client_id or not client_secret:
    print("❌ Данные Copernicus не найдены в .env")
    exit()


url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

data = {
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret
}


response = requests.post(url, data=data)


if response.status_code == 200:

    token = response.json()["access_token"]

    print("✅ Подключение к Copernicus успешно!")
    print("✅ OAuth-токен получен.")
    print("Длина токена:", len(token))

else:

    print("❌ Ошибка подключения")
    print("Код:", response.status_code)
    print(response.text)