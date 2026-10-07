# handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command

from utils.consent import user_registry

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Запоминаем пользователя, чтобы ему можно было адресовать запрос согласия
    user_registry.register(message.from_user.id, message.from_user.username)
    await message.answer(
        "🛡 <b>Бот проверки данных</b>\n\n"
        "Я помогаю проверить, не попали ли <b>ваши</b> данные в известные "
        "утечки, и — по согласию — показать чей-то публичный цифровой след.\n\n"
        "Команды:\n"
        "/check — проверить свои данные (email / телефон / пароль)\n"
        "/request @username — запросить у человека согласие на проверку его следа\n"
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
        "<b>Проверка чужого цифрового следа</b> возможна только с согласия "
        "самого человека: <code>/request @username</code> — бот спросит у него "
        "разрешение, и проверка запустится, лишь если он нажмёт «Разрешаю». "
        "Данные третьих лиц при этом не собираются.",
        parse_mode="HTML",
    )
