# handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 <b>Бот запущен!</b>\n\n"
        "Команды:\n"
        "/search @username — поиск по юзернейму\n"
        "/search +79991234567 — поиск по телефону\n"
        "/search 123456789 — поиск по ID\n"
        "/help — помощь",
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        " <b>Помощь</b>\n\n"
        "Бот ищет информацию о пользователях Telegram\n\n"
        "Примеры \n"
        "/search @durov`\n"
        "/search +79001234567`\n"
        "/search 123456789`",
        parse_mode="HTML"
    )