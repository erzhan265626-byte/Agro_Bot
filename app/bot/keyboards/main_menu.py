from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🗺 Мои поля"),
            KeyboardButton(text="🌦 Погода")
        ],
        [
            KeyboardButton(text="🛰 Спутниковый анализ"),
            KeyboardButton(text="📊 Сводка поля")
        ]
    ],
    resize_keyboard=True
)