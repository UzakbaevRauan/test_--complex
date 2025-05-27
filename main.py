from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import requests
from sqlalchemy import select
from database import database, search_history  
from sqlalchemy import func
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Query
import httpx
from sqlalchemy import delete

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, city: str = None):
    if city:
        city = city.strip()
        query = select(search_history).where(search_history.c.city == city)
        existing = await database.fetch_one(query)

        if existing:
            update_query = (
                search_history.update()
                .where(search_history.c.city == city)
                .values(count=existing["count"] + 1)
            )
            await database.execute(update_query)
        else:
            insert_query = search_history.insert().values(city=city, count=1)
            await database.execute(insert_query)

    # Получаем топ 5 городов из истории
    historyquery = select(search_history.c.city, search_history.c.count).order_by(search_history.c.count.desc()).limit(5)
    history_rows = await database.fetch_all(historyquery)
    top_cities = [{"city": row["city"], "count": row["count"]} for row in history_rows]
    print("top_cities", top_cities)

    # Получаем полную историю запросов
    query = select(search_history.c.city, search_history.c.count).order_by(search_history.c.count.desc())
    rows = await database.fetch_all(query)
    history = [{"city": row["city"], "count": row["count"]} for row in rows]

    weather_data = None
    error = None
    current = None
    hourly = []

    if city:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if "results" in data and data["results"]:
                result = data["results"][0]
                latitude = result["latitude"]
                longitude = result["longitude"]
                city_name = result["name"]
                country = result["country"]

                weather_url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={latitude}&longitude={longitude}"
                    f"&current_weather=true"
                    f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
                )
                weather_response = requests.get(weather_url)

                if weather_response.status_code == 200:
                    weather_data = weather_response.json()
                    current = weather_data.get("current_weather", None)
                    if "hourly" in weather_data:
                        times = weather_data["hourly"].get("time", [])
                        temps = weather_data["hourly"].get("temperature_2m", [])
                        humids = weather_data["hourly"].get("relative_humidity_2m", [])
                        winds = weather_data["hourly"].get("wind_speed_10m", [])
                        hourly = list(zip(times[:5], temps[:5], humids[:5], winds[:5]))
                    else:
                        hourly = []
                else:
                    error = "Не удалось получить данные о погоде."
            else:
                error = f"Город с названием '{city}' не найден. Попробуйте другой запрос."
        else:
            error = "Ошибка при запросе к API геокодирования."
    else:
        country = None
        city_name = None

    error_param = request.query_params.get("error")
    if error_param == "notfound":
        error = "Город не найден. Попробуйте снова."

    print("error",error)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "history": history,
        "current": current,
        "error": error,
        "city": city,
        "top_cities": top_cities,
        "hourly": hourly
    })


@app.post("/", response_class=HTMLResponse)
async def post_city(request: Request, city: str = Form(...)):
    city = city.strip()

    # Проверяем через API, существует ли такой город
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            # Можно вернуть ошибку или просто редирект без добавления
            return RedirectResponse(url="/?error=notfound", status_code=303)
        data = resp.json()

    if "results" not in data or not data["results"]:
        # Если город не найден, не добавляем в базу, редирект на главную без параметра
        return RedirectResponse(url="/?error=notfound", status_code=303)


    # Если город найден, работаем с базой
    query = select(search_history).where(search_history.c.city == city)
    existing = await database.fetch_one(query)

    if existing:
        update_query = (
            search_history.update()
            .where(search_history.c.city == city)
            .values(count=existing["count"] + 1)
        )
        await database.execute(update_query)
    else:
        insert_query = search_history.insert().values(city=city, count=1)
        await database.execute(insert_query)

    return RedirectResponse(url=f"/?city={city}", status_code=303)



@app.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1)):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()

    suggestions = []
    if "results" in data:
        suggestions = [item["name"] for item in data["results"]]
    return JSONResponse(content=suggestions)


@app.delete("/clear_history")
async def clear_history():
    query = delete(search_history)
    await database.execute(query)
    return {"message": "История поиска очищена"}