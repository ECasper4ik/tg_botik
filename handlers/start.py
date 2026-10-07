# handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🛡 <b>Бот проверки ваших данных на утечки</b>\n\n"
        "Я помогаю проверить, не попали ли <b>ваши</b> данные в известные "
        "утечки. Проверяются только те контакты, владение которыми вы "
        "подтвердите.\n\n"
        "Команды:\n"
        "/check — начать проверку (email / телефон / пароль)\n"
        "/help — помощь",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>Помощь</b>\n\n"
        "Бот проверяет <b>только ваши собственные данные</b>:\n"
        "• <b>email</b> — вводите адрес, получаете код, подтверждаете владение;\n"
        "• <b>телефон</b> — отправляете кнопкой «Поделиться контактом»;\n"
        "• <b>пароль</b> — проверяется по k-анонимности, целиком не передаётся.\n\n"
        "Начать: /check\n\n"
        "Поиск по чужим данным в боте не поддерживается.",
        parse_mode="HTML",
    )
