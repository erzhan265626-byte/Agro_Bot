import json

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.field_menu import field_menu
from app.bot.keyboards.main_menu import main_menu
from database.db import add_field, get_fields


router = Router()


# ============================================================
# СОСТОЯНИЯ ДОБАВЛЕНИЯ ПОЛЯ
# ============================================================

class AddField(StatesGroup):
    name = State()
    latitude = State()
    longitude = State()
    area = State()
    crop = State()
    custom_crop = State()
    boundary = State()


# ============================================================
# КУЛЬТУРЫ
# ============================================================

CROPS = [
    "🌾 Пшеница",
    "🌽 Кукуруза",
    "🌻 Подсолнечник",
    "🌱 Ячмень",
    "🥔 Картофель",
    "🫘 Соя",
    "🌾 Овёс",
    "🌿 Рапс",
    "🍅 Томаты",
    "🥕 Морковь",
    "🧅 Лук",
    "✏️ Другая культура"
]


def crop_keyboard():

    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    keyboard = []

    for i in range(0, len(CROPS), 2):

        row = [
            KeyboardButton(text=CROPS[i])
        ]

        if i + 1 < len(CROPS):
            row.append(
                KeyboardButton(text=CROPS[i + 1])
            )

        keyboard.append(row)

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


# ============================================================
# МОИ ПОЛЯ
# ============================================================

@router.message(F.text == "🗺 Мои поля")
async def my_fields(message: Message):

    await message.answer(
        "🗺 Мои поля\n\n"
        "Выберите действие:",
        reply_markup=field_menu
    )


# ============================================================
# НАЗАД
# ВАЖНО: ЭТОТ ОБРАБОТЧИК ДОЛЖЕН БЫТЬ ДО ОБРАБОТЧИКОВ FSM
# ============================================================

@router.message(F.text == "🔙 Назад")
async def back_to_main(
        message: Message,
        state: FSMContext
):

    # Полностью сбрасываем текущее состояние
    await state.clear()

    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu
    )


# ============================================================
# ДОБАВИТЬ ПОЛЕ
# ============================================================

@router.message(F.text == "➕ Добавить поле")
async def add_field_start(
        message: Message,
        state: FSMContext
):

    await state.set_state(
        AddField.name
    )

    await message.answer(
        "Введите название поля:"
    )


# ============================================================
# НАЗВАНИЕ
# ============================================================

@router.message(AddField.name)
async def add_field_name(
        message: Message,
        state: FSMContext
):

    name = message.text.strip()

    if not name:

        await message.answer(
            "❌ Название поля не может быть пустым."
        )

        return

    await state.update_data(
        name=name
    )

    await state.set_state(
        AddField.latitude
    )

    await message.answer(
        "📍 Введите широту центра поля:\n\n"
        "Например:\n"
        "53.3325"
    )


# ============================================================
# ШИРОТА
# ============================================================

@router.message(AddField.latitude)
async def add_field_latitude(
        message: Message,
        state: FSMContext
):

    try:

        latitude = float(
            message.text.replace(",", ".")
        )

    except ValueError:

        await message.answer(
            "❌ Введите широту числом.\n\n"
            "Например:\n"
            "53.3325"
        )

        return

    if latitude < -90 or latitude > 90:

        await message.answer(
            "❌ Широта должна быть от -90 до 90."
        )

        return

    await state.update_data(
        latitude=latitude
    )

    await state.set_state(
        AddField.longitude
    )

    await message.answer(
        "📍 Введите долготу центра поля:\n\n"
        "Например:\n"
        "69.2720"
    )


# ============================================================
# ДОЛГОТА
# ============================================================

@router.message(AddField.longitude)
async def add_field_longitude(
        message: Message,
        state: FSMContext
):

    try:

        longitude = float(
            message.text.replace(",", ".")
        )

    except ValueError:

        await message.answer(
            "❌ Введите долготу числом.\n\n"
            "Например:\n"
            "69.2720"
        )

        return

    if longitude < -180 or longitude > 180:

        await message.answer(
            "❌ Долгота должна быть от -180 до 180."
        )

        return

    await state.update_data(
        longitude=longitude
    )

    await state.set_state(
        AddField.area
    )

    await message.answer(
        "📐 Введите площадь поля в гектарах:\n\n"
        "Например:\n"
        "120"
    )


# ============================================================
# ПЛОЩАДЬ
# ============================================================

@router.message(AddField.area)
async def add_field_area(
        message: Message,
        state: FSMContext
):

    try:

        area = float(
            message.text.replace(",", ".")
        )

    except ValueError:

        await message.answer(
            "❌ Введите площадь числом.\n\n"
            "Например:\n"
            "120"
        )

        return

    if area <= 0:

        await message.answer(
            "❌ Площадь должна быть больше 0."
        )

        return

    await state.update_data(
        area=area
    )

    await state.set_state(
        AddField.crop
    )

    await message.answer(
        "🌱 Выберите культуру:",
        reply_markup=crop_keyboard()
    )


# ============================================================
# КУЛЬТУРА
# ============================================================

@router.message(AddField.crop)
async def add_field_crop(
        message: Message,
        state: FSMContext
):

    crop = message.text.strip()

    if crop == "✏️ Другая культура":

        await state.set_state(
            AddField.custom_crop
        )

        await message.answer(
            "Введите название культуры:"
        )

        return

    if crop not in CROPS:

        await message.answer(
            "❌ Выберите культуру из списка.",
            reply_markup=crop_keyboard()
        )

        return

    crop = crop.split(" ", 1)[1]

    await state.update_data(
        crop=crop
    )

    await request_boundary(
        message,
        state
    )


# ============================================================
# ДРУГАЯ КУЛЬТУРА
# ============================================================

@router.message(AddField.custom_crop)
async def add_custom_crop(
        message: Message,
        state: FSMContext
):

    crop = message.text.strip()

    if not crop:

        await message.answer(
            "❌ Название культуры не может быть пустым."
        )

        return

    await state.update_data(
        crop=crop
    )

    await request_boundary(
        message,
        state
    )


# ============================================================
# ГРАНИЦЫ
# ============================================================

async def request_boundary(
        message: Message,
        state: FSMContext
):

    await state.set_state(
        AddField.boundary
    )

    await message.answer(
        "🗺 Теперь укажите границы поля.\n\n"
        "Введите минимум 3 точки.\n"
        "Каждая точка — новая строка.\n\n"
        "Формат:\n"
        "широта, долгота\n\n"
        "Пример:\n"
        "53.3325, 69.2720\n"
        "53.3310, 69.2975\n"
        "53.3185, 69.2950\n"
        "53.3200, 69.2695\n\n"
        "После последней точки отправьте сообщение."
    )


# ============================================================
# СОХРАНЕНИЕ ГРАНИЦ
# ============================================================

@router.message(AddField.boundary)
async def add_field_boundary(
        message: Message,
        state: FSMContext
):

    lines = message.text.strip().splitlines()

    if len(lines) < 3:

        await message.answer(
            "❌ Нужно минимум 3 точки.\n\n"
            "Пример:\n"
            "53.3325, 69.2720\n"
            "53.3310, 69.2975\n"
            "53.3185, 69.2950"
        )

        return

    boundary = []

    for line in lines:

        try:

            parts = line.split(",")

            if len(parts) != 2:
                raise ValueError

            latitude = float(
                parts[0].strip()
            )

            longitude = float(
                parts[1].strip()
            )

            if latitude < -90 or latitude > 90:
                raise ValueError

            if longitude < -180 or longitude > 180:
                raise ValueError

            boundary.append([
                latitude,
                longitude
            ])

        except ValueError:

            await message.answer(
                "❌ Ошибка в координатах.\n\n"
                "Используйте формат:\n"
                "53.3325, 69.2720"
            )

            return

    boundary_json = json.dumps(
        boundary
    )

    await state.update_data(
        boundary=boundary_json
    )

    await save_field(
        message,
        state
    )


# ============================================================
# СОХРАНЕНИЕ ПОЛЯ В БД
# ============================================================

async def save_field(
        message: Message,
        state: FSMContext
):

    data = await state.get_data()

    user_id = message.from_user.id

    name = data["name"]
    latitude = data["latitude"]
    longitude = data["longitude"]
    area = data["area"]
    crop = data["crop"]
    boundary = data["boundary"]

    try:

        add_field(
            user_id=user_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            area=area,
            crop=crop,
            boundary=boundary
        )

    except Exception as error:

        print(
            "Ошибка сохранения поля:",
            error
        )

        await message.answer(
            "❌ Не удалось сохранить поле.\n"
            "Проверьте консоль PyCharm."
        )

        return

    await state.clear()

    await message.answer(
        "✅ Поле успешно зарегистрировано!\n\n"
        f"🌾 Название: {name}\n"
        f"📍 Широта: {latitude}\n"
        f"📍 Долгота: {longitude}\n"
        f"📐 Площадь: {area} га\n"
        f"🌱 Культура: {crop}\n"
        f"🗺 Границ: {len(json.loads(boundary))} точек",
        reply_markup=main_menu
    )


# ============================================================
# СПИСОК ПОЛЕЙ
# ============================================================

@router.message(F.text == "📋 Мои зарегистрированные поля")
async def show_fields(message: Message):

    user_id = message.from_user.id

    fields = get_fields(user_id)

    if not fields:

        await message.answer(
            "📋 У вас пока нет зарегистрированных полей.",
            reply_markup=field_menu
        )

        return

    text = "📋 Ваши зарегистрированные поля:\n\n"

    for field in fields:

        (
            field_id,
            field_user_id,
            name,
            latitude,
            longitude,
            area,
            crop,
            boundary
        ) = field

        boundary_count = 0

        if boundary:

            try:

                boundary_count = len(
                    json.loads(boundary)
                )

            except Exception:

                boundary_count = 0

        text += (
            f"🌾 Поле №{field_id}\n"
            f"Название: {name}\n"
            f"📍 Широта: {latitude}\n"
            f"📍 Долгота: {longitude}\n"
            f"📐 Площадь: {area} га\n"
            f"🌱 Культура: {crop}\n"
            f"🗺 Точек границы: {boundary_count}\n\n"
        )

    await message.answer(
        text,
        reply_markup=field_menu
    )