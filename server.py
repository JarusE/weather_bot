from fastapi import FastAPI
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")

@app.get("/ping")
async def ping():
    """
    Handles HTTP GET requests to the "/ping" endpoint.

    This function is an asynchronous endpoint in a FastAPI application. It
    is primarily used to check the health and availability of the application
    by returning a simple JSON response. It does not accept any parameters
    and responds with a key-value pair indicating the server's readiness.

    :return: A dictionary with the key "ping" and the value "pong!".
    :rtype: dict
    """
    return {"ping": "pong!"}

@app.get("/weather")
async def get_wether(city:str, units:str="metric"):
    """
    Fetches current weather data for a given city. The weather information
    is retrieved from the OpenWeatherMap API using the provided city name
    and units of measurement.

    :param city: The name of the city for which weather data is to be fetched.
    :type city: str
    :param units: The measurement system for the weather data (metric, imperial, or standard).
                  Defaults to "metric". If an unsupported value is provided, the unit
                  defaults to "metric".
    :type units: str, optional
    :return: A dictionary containing the current weather data if the response is
             successful, or an error message indicating the failure.
    :rtype: dict
    """
    if units not in ["metric", "imperial", "standart"]:
        units = "metric"

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units={units}&lang=uk"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "city": data["name"],
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "weather": data["weather"][0]["description"],
                }
            else:
                return {"error": f"не удалось получить погоду для {city}"}

@app.get("/forecast")
async def get_forecast(city:str, units:str="metric"):
    """
    Fetches the 5-day weather forecast for a specific city based on the given location
    and units. The forecast data is retrieved from the OpenWeather API.

    :param city: The name of the city for which the forecast is to be fetched
    :param units: The unit system for temperature. Default is "metric". Accepts valid
                  units supported by OpenWeather API.
    :return: A dictionary containing the city name and a list of daily weather forecasts
             for up to 5 days. Each forecast includes date, daily maximum temperature,
             nightly minimum temperature, daily feels-like temperature, nightly feels-like
             temperature, and a brief weather description.
    """
    url_forecast = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_KEY}&units={units}&lang=uk"

    async with aiohttp.ClientSession() as session:
        async with session.get(url_forecast) as resp:
            if resp.status !=200:
                return {"error:" f"Не удалось получить прогноз для {city}"}
            data = await resp.json()

    daily_forecast = {}
    for item in data["list"]:
        date = item["dt_txt"].split(" ")[0]
        temp = item ["main"]["temp"]
        feels_like = item["main"]["feels_like"]
        weather = item["weather"][0]["description"]

        if  date not in daily_forecast:
            daily_forecast[date] = {
                "temp_day": temp,
                "temp_night": temp,
                "feels_like_day": feels_like,
                "feels_like_night": feels_like,
                "weather": weather,
            }
        else:
            daily_forecast[date]["temp_day"] = max(daily_forecast[date]["temp_day"], temp)
            daily_forecast[date]["temp_night"] = min(daily_forecast[date]["temp_night"], temp)
            daily_forecast[date]["feels_like_day"] = max(daily_forecast[date]["feels_like_day"], feels_like)
            daily_forecast[date]["feels_like_night"] = min(daily_forecast[date]["feels_like_night"], feels_like)

    forecast_list = []
    for i, (date, info) in enumerate(daily_forecast.items()):
        if i >= 5:
            break
        forecast_list.append({
            "date": date,
            "temp_day": round(info["temp_day"],1),
            "temp_night": round(info["temp_night"],1),
            "feels_like_day": round(info["feels_like_day"],1),
            "feels_like_night": round(info["feels_like_night"],1),
            "weather": info["weather"]
        })

    return {"city": data["city"]["name"], "forecast": forecast_list}

@app.get("/rain_alert")
async def rain_alert(city:str, units:str="metric", hours_ahed: int = 6):
    """
    Checks the weather forecast for a specific city and provides
    a rain alert for the upcoming hours.

    This function fetches weather data from the OpenWeatherMap API and
    analyzes precipitation probabilities and weather conditions within
    a defined number of hours ahead. If rain is predicted with a
    precipitation probability above zero, an alert will be triggered
    and the relevant times will be listed.

    :param city: Name of the city for which to fetch the weather forecast
    :type city: str
    :param units: Unit system for temperature and weather data.
                  Defaults to "metric"
    :type units: str
    :param hours_ahed: Number of hours ahead to check for rainfall
    :type hours_ahed: int
    :return: Dictionary containing the rain alert status, city name,
             and possible alert times if rain is detected
    :rtype: dict
    """
    url_forecast = (
        f"http://api.openweathermap.org/data/2.5/forecast"
        f"?q={city}&appid={OPENWEATHER_KEY}&units={units}&lang=uk"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url_forecast) as resp:
            if resp.status != 200:
                return {"eror": f"Unable to get forecast for {city}"}
            data = await resp.json()

    from datetime import datetime, timedelta

    now = datetime.utcnow()
    alert=False
    alert_times = []

    for item in data["list"]:
        forecast_time = datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if forecast_time > now + timedelta(hours=hours_ahed):
            break

        pop = item.get("pop", 0)
        weather_desc = item["weather"][0]["main"].lower()
        if "rain" in weather_desc and pop > 0:
            alert = True
            alert_times.append(item["dt_txt"])

    if alert:
        return {"alert": True, "alert_times": alert_times, "city": data["city"]["name"]}
    else:
        return {"alert": False, "city": data["city"]["name"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)