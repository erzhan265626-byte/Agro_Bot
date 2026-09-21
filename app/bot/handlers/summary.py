from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database.field_service import get_all_fields
from database.db import get_latest_satellite_result
from app.bot.keyboards.main_menu import main_menu

import aiohttp


router = Router()


# =========================================================
# КЛАВИАТУРА ВЫБОРА ПОЛЯ
# =========================================================

def create_summary_keyboard(fields):
    keyboard = []

    for field in fields:
        keyboard.append([
            KeyboardButton(
                text=f"📊 {field.name} — {field.crop}"
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
# ПОГОДА
# =========================================================

async def get_current_weather(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "wind_speed_10m"
        ),
        "timezone": "auto"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=30
            ) as response:

                if response.status != 200:
                    return None

                return await response.json()

    except Exception as error:
        print(
            "Ошибка получения погоды:",
            error
        )
        return None


# =========================================================
# ОЦЕНКА ОБЩЕГО СОСТОЯНИЯ
# =========================================================

def get_overall_condition(ndvi, ndmi):

    if ndvi is None or ndmi is None:
        return (
            "ℹ️ Недостаточно данных "
            "для общей оценки."
        )

    if ndvi < 0.2 and ndmi < 0:
        return (
            "🔴 Требуется дополнительное "
            "наблюдение за полем."
        )

    if ndvi < 0.3:
        return (
            "🟡 Растительность находится "
            "на низком уровне."
        )

    if ndmi < -0.3:
        return (
            "🔴 Возможен недостаток влаги. "
            "Рекомендуется дополнительный контроль."
        )

    if ndmi < 0:
        return (
            "🟠 Влажность растительности "
            "ниже нулевого уровня. "
            "Рекомендуется наблюдение."
        )

    if ndvi >= 0.5 and ndmi >= 0.2:
        return (
            "🟢 Показатели растительности "
            "и влажности находятся "
            "на хорошем уровне."
        )

    return (
        "🟡 Состояние поля требует "
        "периодического наблюдения."
    )


# =========================================================
# ТЕКСТОВАЯ ОЦЕНКА NDVI
# =========================================================

def ndvi_text(ndvi):

    if ndvi < 0:
        return "🔵 Нерастительная поверхность"

    if ndvi < 0.2:
        return "🔴 Очень слабая растительность"

    if ndvi < 0.3:
        return "🟡 Слабая растительность"

    if ndvi < 0.5:
        return "🟢 Умеренная растительность"

    if ndvi < 0.7:
        return "🟢 Хорошая растительность"

    return "🟢 Очень высокая растительность"


# =========================================================
# ТЕКСТОВАЯ ОЦЕНКА NDMI
# =========================================================

def ndmi_text(ndmi):

    if ndmi < -0.3:
        return "🔴 Очень низкая влажность"

    if ndmi < 0:
        return "🟠 Низкая влажность"

    if ndmi < 0.2:
        return "🟡 Умеренная влажность"

    if ndmi < 0.4:
        return "🟢 Хорошая влажность"

    return "🟢 Высокая влажность"


# =========================================================
# КНОПКА СВОДКИ
# =========================================================

@router.message(
    F.text == "📊 Сводка поля"
)
async def summary_start(
    message: Message
):

    user_id = message.from_user.id

    fields = get_all_fields(user_id)

    if not fields:

        await message.answer(
            "📊 Для создания сводки "
            "сначала зарегистрируйте поле.",
            reply_markup=main_menu
        )

        return

    keyboard = create_summary_keyboard(
        fields
    )

    await message.answer(
        "📊 Выберите поле для сводки:",
        reply_markup=keyboard
    )


# =========================================================
# ВЫБОР ПОЛЯ
# =========================================================

@router.message(
    F.text.startswith("📊 ")
)
async def summary_field_selected(
    message: Message
):

    user_id = message.from_user.id

    fields = get_all_fields(user_id)

    text = message.text.replace(
        "📊 ",
        "",
        1
    ).strip()

    selected_field = None

    for field in fields:

        button_text = (
            f"{field.name} — "
            f"{field.crop}"
        )

        if text == button_text:
            selected_field = field
            break

    if selected_field is None:

        await message.answer(
            "❌ Поле не найдено.",
            reply_markup=main_menu
        )

        return

    field = selected_field

    await message.answer(
        "📊 Формирую сводку поля...\n\n"
        f"🌾 {field.name}\n"
        f"🌱 {field.crop}\n"
        f"📐 {field.area} га"
    )

    # =====================================================
    # СПУТНИК
    # =====================================================

    satellite_result = get_latest_satellite_result(
        field.id,
        user_id
    )

    # =====================================================
    # ПОГОДА
    # =====================================================

    weather = await get_current_weather(
        field.latitude,
        field.longitude
    )

    # =====================================================
    # ФОРМИРУЕМ ТЕКСТ
    # =====================================================

    text = (
        "📊 <b>СВОДКА ПОЛЯ</b>\n\n"
        f"🌾 <b>Поле:</b> {field.name}\n"
        f"🌱 <b>Культура:</b> {field.crop}\n"
        f"📐 <b>Площадь:</b> {field.area} га\n\n"
    )

    # =====================================================
    # СПУТНИКОВЫЕ ДАННЫЕ
    # =====================================================

    text += "🛰 <b>СПУТНИКОВЫЙ АНАЛИЗ</b>\n\n"

    if satellite_result:

        (
            result_id,
            field_id,
            result_user_id,
            date,
            mean_ndvi,
            min_ndvi,
            max_ndvi,
            mean_ndmi,
            min_ndmi,
            max_ndmi
        ) = satellite_result

        text += (
            f"📅 Снимок: {date}\n\n"
            f"🌿 Средний NDVI: "
            f"{mean_ndvi:.3f}\n"
            f"📉 Минимальный NDVI: "
            f"{min_ndvi:.3f}\n"
            f"📈 Максимальный NDVI: "
            f"{max_ndvi:.3f}\n"
            f"➡️ {ndvi_text(mean_ndvi)}\n\n"
            f"💧 Средний NDMI: "
            f"{mean_ndmi:.3f}\n"
            f"📉 Минимальный NDMI: "
            f"{min_ndmi:.3f}\n"
            f"📈 Максимальный NDMI: "
            f"{max_ndmi:.3f}\n"
            f"➡️ {ndmi_text(mean_ndmi)}\n\n"
        )

    else:

        text += (
            "ℹ️ Спутниковый анализ "
            "ещё не выполнялся.\n\n"
        )

    # =====================================================
    # ПОГОДА
    # =====================================================

    text += "🌦 <b>ТЕКУЩАЯ ПОГОДА</b>\n\n"

    if weather:

        current = weather.get(
            "current",
            {}
        )

        temperature = current.get(
            "temperature_2m"
        )

        humidity = current.get(
            "relative_humidity_2m"
        )

        precipitation = current.get(
            "precipitation"
        )

        wind = current.get(
            "wind_speed_10m"
        )

        if temperature is not None:
            text += (
                f"🌡 Температура: "
                f"{temperature:.1f} °C\n"
            )

        if humidity is not None:
            text += (
                f"💧 Влажность воздуха: "
                f"{humidity:.0f}%\n"
            )

        if precipitation is not None:
            text += (
                f"🌧 Осадки: "
                f"{precipitation:.1f} мм\n"
            )

        if wind is not None:
            text += (
                f"💨 Ветер: "
                f"{wind:.1f} км/ч\n"
            )

        text += "\n"

    else:

        text += (
            "❌ Не удалось получить "
            "текущую погоду.\n\n"
        )

    # =====================================================
    # ОБЩАЯ ОЦЕНКА
    # =====================================================

    text += "📋 <b>ОБЩАЯ ОЦЕНКА</b>\n\n"

    if satellite_result:

        overall = get_overall_condition(
            mean_ndvi,
            mean_ndmi
        )

        text += overall

    else:

        text += (
            "ℹ️ Выполните спутниковый анализ, "
            "чтобы получить общую оценку."
        )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu
    )