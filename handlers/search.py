# handlers/search.py
"""
Самопроверка данных пользователя на утечки.

Бот проверяет ТОЛЬКО те контакты, владение которыми пользователь подтвердил:
  - email  — кодом, отправленным на этот адрес;
  - телефон — кнопкой Telegram «Поделиться контактом»;
  - пароль — проверяется по k-анонимности, на сервер уходит лишь префикс хэша.

Поиск по чужим идентификаторам в этом боте не предусмотрен.
"""
import logging

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from modules.breach_check import breach_checker
from utils.validators import validate_email, normalize_phone
from utils.formatters import formatter
from utils.verification import (
    verification_manager,
    CodeExpiredError,
    TooManyAttemptsError,
    ResendTooSoonError,
)
from utils import mailer

router = Router()
logger = logging.getLogger(__name__)


class CheckStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_email_code = State()
    waiting_for_contact = State()
    waiting_for_password = State()


def _menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📧 Проверить мой email",
                                  callback_data="sc_email")],
            [InlineKeyboardButton(text="📱 Проверить мой телефон",
                                  callback_data="sc_phone")],
            [InlineKeyboardButton(text="🔑 Проверить пароль",
                                  callback_data="sc_password")],
        ]
    )


@router.message(Command("check"))
async def cmd_check(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🛡 <b>Проверка ваших данных на утечки</b>\n\n"
        "Бот проверяет только ваши собственные данные и только после "
        "подтверждения владения ими. Выберите, что проверить:",
        parse_mode="HTML",
        reply_markup=_menu(),
    )


# ---------------------------- EMAIL ----------------------------

@router.callback_query(F.data == "sc_email")
async def sc_email(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CheckStates.waiting_for_email)
    await callback.message.answer(
        "📧 Введите ваш email. На него придёт код подтверждения."
    )


@router.message(CheckStates.waiting_for_email)
async def on_email(message: types.Message, state: FSMContext):
    email = (message.text or "").strip()
    if not validate_email(email):
        await message.answer("❌ Это не похоже на корректный email. Попробуйте ещё раз.")
        return

    try:
        code = verification_manager.create("email", email)
    except ResendTooSoonError as e:
        await message.answer(f"⏳ Код уже отправлен. Повторить можно через {int(str(e))} сек.")
        return

    try:
        await mailer.send_code(email, code)
    except mailer.MailerNotConfiguredError:
        verification_manager.discard("email", email)
        await message.answer(
            "⚠️ Отправка писем не настроена на сервере (SMTP). "
            "Проверка email временно недоступна."
        )
        await state.clear()
        return
    except mailer.MailerError:
        verification_manager.discard("email", email)
        logger.exception("Не удалось отправить код на email")
        await message.answer("❌ Не удалось отправить письмо. Проверьте адрес и попробуйте позже.")
        return

    await state.update_data(email=email)
    await state.set_state(CheckStates.waiting_for_email_code)
    await message.answer("✅ Код отправлен. Введите его сюда (действует 10 минут).")


@router.message(CheckStates.waiting_for_email_code)
async def on_email_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    email = data.get("email")
    if not email:
        await state.clear()
        await message.answer("Сессия истекла. Начните заново: /check")
        return

    code = (message.text or "").strip()
    try:
        ok = verification_manager.verify("email", email, code)
    except CodeExpiredError:
        await state.clear()
        await message.answer("⌛ Код истёк. Начните заново: /check")
        return
    except TooManyAttemptsError:
        await state.clear()
        await message.answer("🚫 Слишком много попыток. Начните заново: /check")
        return

    if not ok:
        await message.answer("❌ Неверный код. Попробуйте ещё раз.")
        return

    await state.clear()
    status = await message.answer("⏳ Проверяю email по базам утечек...")
    try:
        breaches = await breach_checker.check_email_hibp(email)
    except Exception:
        logger.exception("Ошибка проверки email в HIBP")
        await status.edit_text("❌ Сервис проверки недоступен, попробуйте позже.")
        return

    report = formatter.generate_self_check_report("📧 Email", email, breaches)
    await status.edit_text(report, parse_mode="Markdown", disable_web_page_preview=True)


# ---------------------------- ТЕЛЕФОН ----------------------------

@router.callback_query(F.data == "sc_phone")
async def sc_phone(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CheckStates.waiting_for_contact)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться моим контактом",
                                  request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await callback.message.answer(
        "Нажмите кнопку ниже, чтобы отправить свой номер. "
        "Так Telegram подтверждает, что номер принадлежит вам.",
        reply_markup=keyboard,
    )


@router.message(CheckStates.waiting_for_contact, F.contact)
async def on_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    # Принимаем только собственный контакт пользователя
    if contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Это чужой контакт. Можно проверить только свой номер — "
            "используйте кнопку «Поделиться моим контактом».",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.clear()
    phone = normalize_phone(contact.phone_number)
    status = await message.answer("⏳ Проверяю номер...", reply_markup=ReplyKeyboardRemove())
    try:
        breaches = await breach_checker.check_phone_breach(phone)
    except Exception:
        logger.exception("Ошибка проверки телефона")
        await status.edit_text("❌ Сервис проверки недоступен, попробуйте позже.")
        return

    report = formatter.generate_self_check_report("📱 Телефон", phone, breaches)
    await status.edit_text(report, parse_mode="Markdown", disable_web_page_preview=True)


@router.message(CheckStates.waiting_for_contact)
async def on_contact_wrong(message: types.Message):
    await message.answer("Пожалуйста, воспользуйтесь кнопкой «Поделиться моим контактом».")


# ---------------------------- ПАРОЛЬ ----------------------------

@router.callback_query(F.data == "sc_password")
async def sc_password(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CheckStates.waiting_for_password)
    await callback.message.answer(
        "🔑 Отправьте пароль, который хотите проверить.\n\n"
        "Пароль НЕ передаётся целиком: бот считает хэш локально и отправляет "
        "сервису лишь первые 5 символов (k-анонимность). Ваше сообщение "
        "будет сразу удалено."
    )


@router.message(CheckStates.waiting_for_password)
async def on_password(message: types.Message, state: FSMContext):
    password = message.text or ""
    await state.clear()

    # Немедленно убираем пароль из чата
    try:
        await message.delete()
    except Exception:
        pass

    if not password:
        await message.answer("❌ Пустой пароль. Начните заново: /check")
        return

    status = await message.answer("⏳ Проверяю пароль...")
    try:
        count = await breach_checker.check_password(password)
    except Exception:
        logger.exception("Ошибка проверки пароля")
        await status.edit_text("❌ Сервис проверки недоступен, попробуйте позже.")
        return

    if count > 0:
        await status.edit_text(
            f"⚠️ Этот пароль встречался в утечках *{count}* раз(а).\n"
            "Срочно смените его и не используйте повторно.",
            parse_mode="Markdown",
        )
    else:
        await status.edit_text("✅ Пароль не найден в известных утечках.")
