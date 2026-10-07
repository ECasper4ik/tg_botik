# handlers/consent.py
"""
Проверка цифрового следа с подтверждением со стороны проверяемого.

Сценарий:
  /request @username  — оператор инициирует запрос;
  бот присылает САМОМУ пользователю запрос с кнопками «Разрешаю» / «Нет»;
  скан его публичного следа запускается только после согласия,
  результат отправляется оператору.

Запрос доставляется только тем, кто сам запускал бота (ограничение Telegram
плюс собственный реестр). Данные третьих лиц не собираются.
"""
import logging

from aiogram import Router, types, F
from aiogram.filters import Command

from modules.social_search import social_scanner
from utils.formatters import formatter
from utils.consent import (
    consent_manager,
    user_registry,
    RequestNotFoundError,
    RequestExpiredError,
    NotTargetError,
    AlreadyAnsweredError,
    RequestTooSoonError,
)

router = Router()
logger = logging.getLogger(__name__)


def _register(user: types.User) -> None:
    if user:
        user_registry.register(user.id, user.username)


def _consent_keyboard(token: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Разрешаю", callback_data=f"cns:allow:{token}"),
            types.InlineKeyboardButton(text="🚫 Нет", callback_data=f"cns:deny:{token}"),
        ]]
    )


@router.message(Command("request"))
async def cmd_request(message: types.Message):
    _register(message.from_user)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Использование: <code>/request @username</code>\n\n"
            "Бот спросит согласие у этого пользователя и, если он разрешит, "
            "проверит его публичный цифровой след. Запросить можно только того, "
            "кто сам запускал этого бота.",
            parse_mode="HTML",
        )
        return

    target_ref = parts[1].strip()
    target_id = user_registry.resolve(target_ref)

    if target_id is None:
        await message.answer(
            "❌ Не могу найти этого пользователя. Бот умеет писать только тем, "
            "кто сам его запускал. Попросите человека открыть бота и нажать "
            "/start, затем повторите запрос."
        )
        return

    if target_id == message.from_user.id:
        await message.answer("Свои данные можно проверить напрямую: /check")
        return

    target_username = user_registry.username_of(target_id)
    if not target_username:
        await message.answer(
            "❌ У этого пользователя нет публичного @username, по которому можно "
            "проверить цифровой след."
        )
        return

    try:
        req = consent_manager.create_request(
            operator_id=message.from_user.id,
            target_id=target_id,
            target_username=target_username,
        )
    except RequestTooSoonError as e:
        await message.answer(
            f"⏳ Вы уже отправляли запрос этому пользователю. "
            f"Повторить можно через {int(str(e))} сек."
        )
        return

    operator_name = message.from_user.username and f"@{message.from_user.username}"
    operator_name = operator_name or message.from_user.full_name

    try:
        await message.bot.send_message(
            target_id,
            f"🔔 Пользователь <b>{operator_name}</b> просит разрешение проверить "
            "ваш <b>публичный цифровой след</b> — какие ваши аккаунты в соцсетях "
            "можно найти по вашему @username. Результат увидит только он.\n\n"
            "Проверка затронет <b>только ваши собственные</b> публичные данные. "
            "Разрешаете?",
            parse_mode="HTML",
            reply_markup=_consent_keyboard(req.token),
        )
    except Exception:
        consent_manager.consume(req.token)
        logger.info("Не удалось доставить запрос согласия target_id=%s", target_id)
        await message.answer(
            "❌ Не удалось доставить запрос: пользователь не начинал диалог с ботом "
            "или заблокировал его."
        )
        return

    await message.answer(
        "✅ Запрос на согласие отправлен. Проверка начнётся, только если человек "
        "её разрешит. Запрос действует 15 минут."
    )


@router.callback_query(F.data.startswith("cns:allow:"))
async def on_allow(callback: types.CallbackQuery):
    _register(callback.from_user)
    token = callback.data.split(":", 2)[2]

    try:
        req = consent_manager.grant(token, callback.from_user.id)
    except (RequestNotFoundError, RequestExpiredError):
        await callback.answer("Запрос не найден или истёк", show_alert=True)
        return
    except NotTargetError:
        await callback.answer("Подтвердить может только сам проверяемый", show_alert=True)
        return
    except AlreadyAnsweredError:
        await callback.answer("На этот запрос уже дан ответ", show_alert=True)
        return

    await callback.answer("Спасибо, согласие зафиксировано")
    try:
        await callback.message.edit_text(
            "✅ Вы разрешили проверку своего публичного следа. Выполняется..."
        )
    except Exception:
        pass

    try:
        social_results = await social_scanner.scan_username(req.target_username)
    except Exception:
        logger.exception("Ошибка скана цифрового следа")
        await callback.bot.send_message(
            req.operator_id, "❌ Проверка не удалась из-за ошибки сервиса."
        )
        consent_manager.consume(token)
        return

    report = formatter.generate_footprint_report(req.target_username, social_results)
    await callback.bot.send_message(
        req.operator_id, report, parse_mode="Markdown", disable_web_page_preview=True
    )
    try:
        await callback.message.edit_text(
            "✅ Готово. Результат отправлен запросившему. Отозвать доступ к будущим "
            "проверкам можно, просто отказав в следующем запросе."
        )
    except Exception:
        pass
    consent_manager.consume(token)


@router.callback_query(F.data.startswith("cns:deny:"))
async def on_deny(callback: types.CallbackQuery):
    _register(callback.from_user)
    token = callback.data.split(":", 2)[2]

    try:
        req = consent_manager.deny(token, callback.from_user.id)
    except (RequestNotFoundError, RequestExpiredError):
        await callback.answer("Запрос не найден или истёк", show_alert=True)
        return
    except NotTargetError:
        await callback.answer("Ответить может только сам проверяемый", show_alert=True)
        return
    except AlreadyAnsweredError:
        await callback.answer("На этот запрос уже дан ответ", show_alert=True)
        return

    await callback.answer("Вы отказали в проверке")
    try:
        await callback.message.edit_text("🚫 Вы отклонили запрос. Проверка не выполнялась.")
    except Exception:
        pass
    await callback.bot.send_message(
        req.operator_id, "🚫 Пользователь отказал в проверке."
    )
    consent_manager.consume(token)
