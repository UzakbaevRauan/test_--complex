# test_app.py

from fastapi.testclient import TestClient
from main import app  # импортируем приложение из main.py

client = TestClient(app)

def test_homepage_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Прогноз погоды" in response.text  # Проверяем, что заголовок страницы есть в ответе


def test_city_search_and_weather():
    city_name = "Almaty"
    # Отправляем POST запрос с формой
    response = client.post("/", data={"city": city_name})
    assert response.status_code in (200, 303)  # в зависимости от редиректа или страницы

    # Проверяем, что после запроса город есть в тексте ответа
    response = client.get(f"/?city={city_name}")
    assert city_name.lower() in response.text.lower()

def test_autocomplete():
    response = client.get("/autocomplete?q=Ast")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
