WeatherBot is a Telegram bot that provides current weather and a 5-day forecast. It can send rain alerts, supports temperature unit selection, allows changing the default city, and offers interactive buttons for user-friendly experience.

Features

    - Get current weather by city name

    - 5-day forecast with day and night temperature

    - Choose temperature units: °C or °F

    - Set and change default city

    - Rain alerts for upcoming precipitation

    - Inline buttons to choose forecast type (now / 5 days)

    - Stores user's last searched city

Technologies

    - Python 3.11+

    - Aiogram 3 — Telegram bot framework

    - aiohttp — asynchronous HTTP requests

    - FastAPI — backend server for OpenWeather API

    - SQLite — storing user data (optional: can switch to PostgreSQL)

    - dotenv — store tokens and API keys

Installation

    Clone the repository:

    git clone https://github.com/yourusername/weatherbot.git
    
    cd weatherbot


    Run the backend server:

    python server.py


    Run the bot:

    python bot.py

Usage

    /start — start the bot and select temperature units

    /help — show help and instructions

    /settings — change default city or temperature unit

    Send a city name — bot asks which forecast you want (now / 5 days)