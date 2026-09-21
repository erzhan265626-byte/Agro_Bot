from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.bot.keyboards.main_menu import main_menu

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "🌾 Добро пожаловать в AgroAI Assistant!\n\n"
        "Я помогу анализировать сельскохозяйственные поля.",
        reply_markup=main_menu
    )