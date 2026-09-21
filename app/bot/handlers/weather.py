import aiohttp

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database.db import get_fields
from app.bot.keyboards.main_menu import main_menu


router = Router()


class WeatherState(StatesGroup):
    select_field = State()
    select_period = State()


# =========================================================
# КЛАВИАТУРА ВЫБОРА ПОЛЯ
# =========================================================

def fields_keyboard(user_id):

    fields = get_fields(user_id)

    keyboard = []

    for field in fields:

        field_id = field[0]
        name = field[2]

        keyboard.append([
            KeyboardButton(
                text=f"🌾 {name} [ID:{field_id}]"
            )
        ])

    keyboard.append([
        KeyboardButton(text="🔙 Назад")
    ])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


# =========================================================
# КЛАВИАТУРА ПЕРИОДА
# =========================================================

def period_keyboard():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="☀️ Сегодня"
                )
            ],
            [
                KeyboardButton(
                    text="📅 На 7 дней"
                )
            ],
            [
                KeyboardButton(
                    text="🔙 Назад"
                )
            ]
        ],
        resize_keyboard=True
    )


# =========================================================
# КНОПКА ПОГОДА
# =========================================================

@router.message(F.text == "🌦 Погода")
async def weather_start(
        message: Message,
        state: FSMContext
):

    user_id = message.from_user.id

    fields = get_fields(user_id)

    if not fields:

        await message.answer(
            "❌ У вас пока нет зарегистрированных полей.\n\n"
            "Сначала добавьте поле через:\n"
            "🗺 Мои поля → ➕ Добавить поле",
            reply_markup=main_menu
        )

        return

    await state.set_state(
        WeatherState.select_field
    )

    await message.answer(
        "🌦 Погода\n\n"
        "Выберите поле:",
        reply_markup=fields_keyboard(user_id)
    )


# =========================================================
# ВЫБОР ПОЛЯ
# =========================================================

@router.message(WeatherState.select_field)
async def select_field(
        message: Message,
        state: FSMContext
):

    if message.text == "🔙 Назад":

        await state.clear()

        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_menu
        )

        return

    text = message.text

    if "[ID:" not in text:

        await message.answer(
            "❌ Выберите поле из списка."
        )

        return

    try:

        field_id = int(
            text.split("[ID:")[1].replace("]", "")
        )

    except ValueError:

        await message.answer(
            "❌ Не удалось определить поле."
        )

        return

    user_id = message.from_user.id

    fields = get_fields(user_id)

    selected_field = None

    for field in fields:

        if field[0] == field_id:

            selected_field = field

            break

    if selected_field is None:

        await message.answer(
            "❌ Это поле вам недоступно."
        )

        return

    name = selected_field[2]
    latitude = selected_field[3]
    longitude = selected_field[4]

    await state.update_data(
        field_id=field_id,
        field_name=name,
        latitude=latitude,
        longitude=longitude
    )

    await state.set_state(
        WeatherState.select_period
    )

    await message.answer(
        f"🌾 Поле: {name}\n"
        f"📍 Координаты: {latitude}, {longitude}\n\n"
        "Выберите период прогноза:",
        reply_markup=period_keyboard()
    )


# =========================================================
# ПОЛУЧЕНИЕ ПОГОДЫ
# =========================================================

async def get_weather(
        latitude,
        longitude,
        forecast_days=7
):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation_probability,"
            "precipitation,"
            "wind_speed_10m,"
            "weather_code"
        ),

        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum,"
            "precipitation_probability_max"
        ),

        "forecast_days": forecast_days,

        "timezone": "auto"
    }

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                url,
                params=params
            ) as response:

                if response.status != 200:

                    print(
                        "Ошибка Open-Meteo:",
                        response.status
                    )

                    return None

                return await response.json()

    except Exception as error:

        print(
            "Ошибка получения погоды:",
            error
        )

        return None


# =========================================================
# ОПИСАНИЕ ПОГОДЫ
# =========================================================

def weather_description(code):

    descriptions = {

        0: "☀️ Ясно",

        1: "🌤 Преимущественно ясно",
        2: "⛅ Переменная облачность",
        3: "☁️ Пасмурно",

        45: "🌫 Туман",
        48: "🌫 Изморозь",

        51: "🌦 Лёгкая морось",
        53: "🌦 Морось",
        55: "🌧 Сильная морось",

        61: "🌧 Небольшой дождь",
        63: "🌧 Дождь",
        65: "🌧 Сильный дождь",

        71: "🌨 Небольшой снег",
        73: "❄️ Снег",
        75: "❄️ Сильный снег",

        80: "🌦 Ливень",
        81: "🌧 Ливень",
        82: "⛈ Сильный ливень",

        95: "⛈ Гроза",
        96: "⛈ Гроза с градом",
        99: "⛈ Сильная гроза"
    }

    return descriptions.get(
        code,
        "🌤 Неизвестно"
    )


# =========================================================
# ПРОГНОЗ НА СЕГОДНЯ
# =========================================================

async def show_today_weather(
        message: Message,
        data,
        field_name
):

    hourly = data["hourly"]

    times = hourly["time"]
    temperatures = hourly["temperature_2m"]
    humidity = hourly["relative_humidity_2m"]
    precipitation_probability = hourly[
        "precipitation_probability"
    ]
    precipitation = hourly["precipitation"]
    wind = hourly["wind_speed_10m"]
    weather_codes = hourly["weather_code"]

    text = (
        f"☀️ Погода на сегодня\n\n"
        f"🌾 Поле: {field_name}\n\n"
    )

    for i in range(min(24, len(times))):

        time = times[i][11:16]

        temperature = temperatures[i]
        hum = humidity[i]
        rain_probability = precipitation_probability[i]
        rain = precipitation[i]
        wind_speed = wind[i]

        description = weather_description(
            weather_codes[i]
        )

        text += (
            f"🕐 {time} — {description}\n"
            f"🌡 Температура: {temperature}°C\n"
            f"💧 Влажность: {hum}%\n"
            f"💨 Ветер: {wind_speed} км/ч\n"
            f"🌧 Осадки: {rain_probability}% "
            f"({rain} мм)\n\n"
        )

    await message.answer(
        text,
        reply_markup=period_keyboard()
    )


# =========================================================
# ПРОГНОЗ НА 7 ДНЕЙ
# =========================================================

async def show_week_weather(
        message: Message,
        data,
        field_name
):

    daily = data["daily"]

    dates = daily["time"]

    temperatures_max = daily[
        "temperature_2m_max"
    ]

    temperatures_min = daily[
        "temperature_2m_min"
    ]

    precipitation = daily[
        "precipitation_sum"
    ]

    precipitation_probability = daily[
        "precipitation_probability_max"
    ]

    weather_codes = daily[
        "weather_code"
    ]

    text = (
        f"📅 Погода на 7 дней\n\n"
        f"🌾 Поле: {field_name}\n\n"
    )

    for i in range(min(7, len(dates))):

        date = dates[i]

        description = weather_description(
            weather_codes[i]
        )

        temp_max = temperatures_max[i]
        temp_min = temperatures_min[i]

        rain = precipitation[i]

        rain_probability = (
            precipitation_probability[i]
        )

        text += (
            f"📅 {date}\n"
            f"{description}\n"
            f"🌡 {temp_min}°C ... {temp_max}°C\n"
            f"🌧 Осадки: {rain_probability}% "
            f"({rain} мм)\n\n"
        )

    await message.answer(
        text,
        reply_markup=period_keyboard()
    )


# =========================================================
# ВЫБОР ПЕРИОДА
# =========================================================

@router.message(WeatherState.select_period)
async def select_period(
        message: Message,
        state: FSMContext
):

    if message.text == "🔙 Назад":

        user_id = message.from_user.id

        await state.set_state(
            WeatherState.select_field
        )

        await message.answer(
            "🌦 Выберите поле:",
            reply_markup=fields_keyboard(user_id)
        )

        return

    data = await state.get_data()

    latitude = data["latitude"]
    longitude = data["longitude"]
    field_name = data["field_name"]


    # =====================================================
    # СЕГОДНЯ
    # =====================================================

    if message.text == "☀️ Сегодня":

        await message.answer(
            "⏳ Получаю прогноз на сегодня..."
        )

        weather = await get_weather(
            latitude,
            longitude,
            forecast_days=1
        )

        if weather is None:

            await message.answer(
                "❌ Не удалось получить данные о погоде."
            )

            return

        await show_today_weather(
            message,
            weather,
            field_name
        )

        return


    # =====================================================
    # 7 ДНЕЙ
    # =====================================================

    if message.text == "📅 На 7 дней":

        await message.answer(
            "⏳ Получаю прогноз на 7 дней..."
        )

        weather = await get_weather(
            latitude,
            longitude,
            forecast_days=7
        )

        if weather is None:

            await message.answer(
                "❌ Не удалось получить данные о погоде."
            )

            return

        await show_week_weather(
            message,
            weather,
            field_name
        )

        return


    await message.answer(
        "❌ Выберите период из меню.",
        reply_markup=period_keyboard()
    )