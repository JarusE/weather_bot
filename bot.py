import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,InlineKeyboardButton,InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram import F
import asyncio
from dotenv import load_dotenv
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
from db import init_db, get_user, set_user, get_all_users, User

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


button_weather = KeyboardButton(text="Weather")
button_forecast = KeyboardButton(text = "5 day forecast")
builder = ReplyKeyboardBuilder()
builder.add(button_weather, button_forecast)
keyboard = builder.as_markup(resize_keyboard=True)

button_celsius = KeyboardButton(text="°C")
button_farenheit = KeyboardButton(text = "°F")
unit_keyboard = ReplyKeyboardMarkup(
    keyboard=[[button_celsius, button_farenheit]],
    resize_keyboard=True
)

class WeatherStates(StatesGroup):
    """
    Manages the states for a weather-related process.

    This class is a StateGroup used in defining a process where users can interact
    with different weather-related functionalities. Each state represents a step
    in the workflow, such as waiting for a city input, choosing a default city,
    or selecting a unit of measurement for weather data.

    :ivar waiting_for_city: State where the process waits for the user to specify
                            the name of a city.
    :type waiting_for_city: State
    :ivar choosing_default_city: State where the user chooses a city to set as the
                                 default for weather-related queries.
    :type choosing_default_city: State
    :ivar choosing_unit: State where the user selects the type of unit (e.g.,
                         metric or imperial) for weather information.
    :type choosing_unit: State
    """
    waiting_for_city = State()
    choosing_default_city = State()
    choosing_unit = State()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """
    Handles the "/start" command initiated by a user. Logs the user's information
    and responds based on their existence in the system. Clears the user's state
    and either welcomes back an existing user or initializes the unit selection
    process for a new user.

    :param message: The incoming message object containing details such as the
        user's ID, full name, and the message content.
    :type message: types.Message
    :param state: The finite state machine context representing the user's
        current state in the interaction flow.
    :type state: FSMContext
    :return: None
    """
    logging.info(f"User {message.from_user.id} ({message.from_user.full_name}) sent: {message.text}")
    await state.clear()
    user_id = message.from_user.id

    user = await get_user(user_id)

    if user:
        await message.answer(
            f"Welcome back, {message.from_user.full_name}!",
            reply_markup = keyboard
        )
    else:
        await message.answer(
            "Select a temperature measurement system:",
            reply_markup = unit_keyboard
        )
        await state.set_state(WeatherStates.choosing_unit)

@dp.message(Command("help"))
async def help_command(mesage: types.Message):
    """
    Handles the /help command from users, providing instructions on how to use
    the bot. Logs the user information when the command is received and
    responds to the user with a message describing the bot's functionality.

    :param message: Represents the message instance received from the user,
        containing all associated data such as the user ID, full name, and
        command text.
    :type message: types.Message
    :return: None
    """
    logging.info(f"User {mesage.from_user.id} ({mesage.from_user.full_name}) sent: {mesage.text}")
    await mesage.answer("Write the name of the city and I will write its weather")

async def check_rain(user_id: int, city: str, unit: str):
    """
    Check if rain is expected in a given city within a certain time frame and
    send an alert to the specified user if rain is anticipated.

    This function interacts with a weather service API to check for rain
    alerts for the specified city and unit of measurement. If rain is
    forecasted, the user is notified with a message containing information
    about the city and the times when rain is expected.

    :param user_id: An integer representing the unique identifier of the user
        to whom the alert should be sent.
    :type user_id: int
    :param city: The name of the city for which to check the rain alert.
    :type city: str
    :param unit: A string representing the unit of temperature measurement.
        Accepted values include "°C" for metric or other values for imperial.
    :type unit: str
    :return: None. This function does not explicitly return any value.
    :rtype: None
    """
    units_api = "metric" if unit == "°C" else "imperial"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://127.0.0.1:8002/rain_alert",
                params={"city": city, "units": units_api, "hours_ahed": 6}
            ) as resp:
                if resp.status != 200:
                    return
                data = await resp.json()
    except aiohttp.ClientError:
        return

    if data.get("alert"):
        times = ", ".join([t.split(" ")[1] for t in data.get("alert_times", [])])
        await bot.send_message(
            user_id,
            f"Rain is expected in the near future in {data['city']} ({times})"
        )

async def rein_scheduler():
    """
    Schedules periodic rain checks for users.

    This function periodically retrieves all users and checks if their city and unit
    information is available. If so, it performs a rain check for the user based on their
    location configuration. The function operates in an infinite loop, running the process
    in one-hour intervals. It is designed to work asynchronously to efficiently handle
    multiple users and their respective configurations.

    :raises Exception: if any issue arises during user retrieval or rain-check process
    """
    while True:
        users =  await get_all_users()
        for user in users:
            if user.city and user.unit:
                await check_rain(user.id, user.city, user.unit)
        await asyncio.sleep(3600)

@dp.message(Command("settings"))
async def settings(message: types.Message, state: FSMContext):
    """
    Handles the settings command which allows the user to change configurable options
    related to their account, such as default city and measurement system. The function
    verifies if the user has already set up a city and measurement system before allowing
    further interaction. If the city and measurement system are not configured, the user
    will be prompted to set them up initially.

    :param message: Represents the incoming message object from the user.
    :type message: types.Message
    :param state: Stores the current state of the finite state machine for the user.
    :type state: FSMContext
    :return: Asynchronous function, does not return any value.
    """
    user  = await get_user(message.from_user.id)

    if not user or not user.city or not user.unit:
        await message.answer("First, set the city and measurement system. (/start)")
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Default city"),
                KeyboardButton(text="Measurement system"),
            ]
        ],
        resize_keyboard=True
    )
    await message.answer("What do you want to change?", reply_markup=keyboard)

@dp.message(F.text.in_({"Default city", "Measurement system"}))
async def change_setting(message: types.Message, state: FSMContext):
    """
    Handles user intent to change a specific application setting, such as the default city
    or the temperature measurement system, and guides the user through the necessary steps.

    :param message: The incoming message from the user providing their choice (either
        "Город по умолчанию" or "Систему измерения").
    :param state: The finite-state machine context to manage and persist user session
        data across asynchronous operations.
    :return: None
    """
    if message.text == "Default city":
        await message.answer("Enter a new default city")
        await state.set_state(WeatherStates.choosing_default_city)
    else:
        await message.answer("Select a temperature measurement system", reply_markup=unit_keyboard)
        await state.set_state(WeatherStates.choosing_unit)

@dp.message(WeatherStates.choosing_unit)
async def choose_unit(message: types.Message, state: FSMContext):
    """
    Handles user input to choose a temperature unit (°C or °F).

    :param message: The Telegram message object.
    :type message: types.Message
    :param state: The finite state machine context for the user session.
    :type state: FSMContext
    :return: None
    :rtype: None
    """
    logging.info(f"User {message.from_user.id} ({message.from_user.full_name}) sent: {message.text}")
    user_id = message.from_user.id
    unit = message.text.strip()
    if unit not in ["°C", "°F"]:
        await message.answer("Select °C or °F", reply_markup = unit_keyboard)
        return
    await set_user(user_id, unit=unit)
    await message.answer("Enter default city")
    await state.set_state(WeatherStates.choosing_default_city)

@dp.message(WeatherStates.choosing_default_city)
async def choose_default_city(message: types.Message, state: FSMContext):
    """
    Handles the 'choose_default_city' functionality, allowing users to set their default city
    for weather forecasts. Validates the city input to ensure it's correctly formatted and
    updates the user preference on success. Additionally, provides user feedback after completion.

    :param message: The incoming message containing the user's input for the city
    :type message: types.Message
    :param state: The current state of the finite state machine
    :type state: FSMContext
    :return: None
    """
    logging.info(f"User {message.from_user.id} ({message.from_user.full_name}) sent: {message.text}")
    user_id = message.from_user.id
    city = message.text.strip()
    if not all(part.isalpha() for part in city.split()):
        await message.answer("Please enter the correct city name")
        return
    await set_user(user_id, city=city)
    await message.answer(
        f"Default city: {city}\n"
        "Click the Weather button to see the forecast",
        reply_markup = keyboard
    )
    await state.clear()

@dp.message(F.text == "Weather")
async def show_default_weather(message: types.Message):
    """
    Handles the weather request when the user sends the message "Weather". The function
    retrieves the user's default city and unit settings to fetch and display the current
    weather using an external weather service API.

    :param message: Telegram message object containing the user's request
    :type message: types.Message
    :return: None
    """
    logging.info(f"User {message.from_user.id} ({message.from_user.full_name}) sent: {message.text}")
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user or not user.city:
        await message.answer("First, set the city and measurement system. (/start)")
        return

    city = user.city
    unit = user.unit

    units_api = "metric" if unit =="°C" else "imperial"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://127.0.0.1:8002/weather",
                params={"city": city, "units": units_api}
            ) as resp:
                if resp.status != 200:
                    await message.answer("Weather service is unavailable")
                    return
                data = await resp.json()
    except aiohttp.ClientError:
        await message.answer("Error connecting to server")
        return

    if "error" in data:
        await message.answer(data["error"])
    else:
        text = (
            f"City: {data['city']}\n"
            f"Temperature: {data['temperature']}°{unit[1]}\n"
            f"Feels like: {data['feels_like']}°{unit[1]}\n"
            f"Weather: {data['weather']}"
        )
        await message.answer(text)

@dp.message(F.text == "5 day forecast")
async def show_forecast(message: types.Message):
    """
    Handles the message event to display a 5-day weather forecast for the user.

    This function checks if the user is registered and has configured a default city
    and measurement units. If the information is missing, it prompts the user to
    perform the initial setup. Otherwise, it retrieves and displays the forecast data
    from a weather service API. The forecast information includes daily temperatures,
    feel-like temperatures, and weather conditions for the default city.

    :param message: The incoming Telegram message to process
    :type message: aiogram.types.Message
    :return: None
    """
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.answer("First, set the city and measurement system. (/start)")
        return

    city = user.city
    unit = user.unit
    units_api = "metric" if unit == "°C" else "imperial"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://127.0.0.1:8002/forecast",
                params={"city": city, "units": units_api}
            ) as resp:
                if resp.status !=200:
                    await message.answer("Weather service is unavailable")
                    return
                data = await resp.json()
    except aiohttp.ClientError:
        await message.answer("Error connecting to server")
        return

    if "error" in data:
        await message.answer(data["error"])
        return

    text = f"5 day forecast for {data['city']}:\n\n"
    for day in data["forecast"]:
        text +=(
            f"{day['date']}:\n"
            f"Daytime: {day['temp_day']}°{unit[1]} feels like {day['feels_like_day']}°{unit[1]}\n"
            f"Nighttime: {day['temp_night']}°{unit[1]} feels like {day['feels_like_night']}°{unit[1]}\n"
            f"{day['weather']}\n\n"
        )
    await message.answer(text)

@dp.message(F.text)
async def ask_forecast_type(message: types.Message):
    """
    Handles the incoming message to ask the user about their desired type of weather forecast.

    The function processes a user's text message, retrieves user data, and updates the last
    entered city. If the user is not registered or has not configured their preferences, they
    are prompted to do so. An inline keyboard is presented to the user to select the type of
    forecast: "Current" or "5-day".

    :param message: The incoming message object containing user input,
                    specifically the city name.
    :type message: aiogram.types.Message
    :return: None
    :rtype: None
    """
    user_id  =message.from_user.id
    city  = message.text.strip()

    user = await get_user(user_id)
    if not user:
        await message.answer("First, set the city and measurement system. (/start)")
        return

    await set_user(user_id, last_city=city)

    kb = InlineKeyboardMarkup(
        inline_keyboard= [[ InlineKeyboardButton(text = "Now", callback_data="forecast_now"), InlineKeyboardButton(text = "5 day forecast", callback_data="forecast_5")]]
    )
    await  message.answer(f"What forecast do you need? ", reply_markup=kb)

@dp.callback_query(F.data == "forecast_now")
async def show_now_forecast(callback: types.CallbackQuery):
    """
    Handles a callback query to display the current weather forecast for the user.
    Retrieves the user's last city or current city, their preferred unit of temperature,
    and fetches the weather data from an external weather API. The fetched data is then
    formatted and sent to the user as a response message. If an error occurs, the error
    message is sent instead.

    :param callback: An instance of `types.CallbackQuery`, representing the callback query
        initiated by the user.
    :return: None
    """
    user_id = callback.from_user.id
    user = await get_user(user_id)

    city = user.last_city or user.city
    unit = user.unit
    units_api = "metric" if unit =="°C" else "imperial"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "http://127.0.0.1:8002/weather",
            params={"city": city, "units": units_api}
        ) as resp:
            data = await resp.json()

    if "error" in data:
        await callback.message.answer(data["error"])
    else:
        text = (
            f"City: {data['city']}\n"
            f"Temperature: {data['temperature']}°{unit[1]}\n"
            f"Feels like: {data['feels_like']}°{unit[1]}\n"
            f"Weather: {data['weather']}"
        )
        await callback.message.answer(text)

    await callback.answer()

@dp.callback_query(F.data == "forecast_5")
async def show_5_forecast(callback: types.CallbackQuery):
    """
    Handles displaying a 5-day weather forecast for a user based on their preferred city and temperature unit. Fetches data
    from an external weather service API and formats it into a user-friendly message for display.

    :param callback: An instance of the CallbackQuery triggered by user interaction through the bot.
    :type callback: types.CallbackQuery

    :return: None
    """
    user_id = callback.from_user.id
    user = await get_user(user_id)
    city = user.last_city or user.city
    unit = user.unit
    units_api = "metric" if unit == "°C" else "imperial"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "http://127.0.0.1:8002/forecast",
            params={"city": city, "units": units_api}
        ) as resp:
            data = await resp.json()
    if "error" in data:
        await callback.message.answer(data["error"])
        return

    text = f"5 day forecast for {data['city']}:\n\n"
    for day in data["forecast"]:
        text += (
            f"{day['date']}:\n"
            f"Daytime: {day['temp_day']}°{unit[1]} feels like {day['feels_like_day']}°{unit[1]}\n"
            f"Nighttime: {day['temp_night']}°{unit[1]} feels like {day['feels_like_night']}°{unit[1]}\n"
            f"{day['weather']}\n\n"
        )
    await callback.message.answer(text)
    await callback.answer()

async def main():
    """
    Main entry function that initializes the database, starts background tasks,
    and begins polling the bot for updates.

    This function ensures that the database is initialized properly before
    executing further processes. A coroutine is also created to run the scheduler
    in the background that operates independently of the main polling process.
    Finally, it starts polling the bot for incoming updates or commands.

    :raises Exception: If any unforeseen error occurs during execution

    :return: None
    """
    await init_db()
    asyncio.create_task(rein_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())