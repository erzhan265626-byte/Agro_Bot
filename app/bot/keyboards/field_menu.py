from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


field_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="➕ Добавить поле")
        ],
        [
            KeyboardButton(text="📋 Мои зарегистрированные поля")
        ],
        [
            KeyboardButton(text="🔙 Назад")
        ]
    ],
    resize_keyboard=True
)