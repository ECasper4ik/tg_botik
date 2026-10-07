# handlers/search.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging

from modules.telegram_api import telegram_client
from modules.social_search import social_scanner
from modules.breach_check import breach_checker
from modules.correlation import correlation_engine
from utils.validators import detect_input_type, normalize_phone
from utils.formatters import formatter

router = Router()
logger = logging.getLogger(__name__)

# FSM состояния
class SearchStates(StatesGroup):
    waiting_for_input = State()
    waiting_for_narrowing = State()
    waiting_for_birthdate = State()
    waiting_for_photo = State()

@router.message(Command("search"))
async def cmd_search(message: types.Message, state: FSMContext):
    """Обработчик команды /search"""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "🔍 *Использование:*\n"
            "`/search @username` — поиск по юзернейму\n"
            "`/search +79991234567` — поиск по телефону\n"
            "`/search 123456789` — поиск по user ID\n"
            "`/search email@example.com` — поиск по email\n\n"
            "_Также бот предложит уточнить данные для сужения поиска._",
            parse_mode="HTML"
        )
        return
    
    input_str = args[1].strip()
    input_type = detect_input_type(input_str)
    
    if input_type == 'unknown':
        await message.answer(
            "❌ Не удалось определить тип ввода.\n"
            "Пожалуйста, укажите:\n"
            "• @username — юзернейм\n"
            "• +79991234567 — номер телефона\n"
            "• 123456789 — числовой ID\n"
            "• email@example.com — email"
        )
        return
    
    status_msg = await message.answer("⏳ Выполняется поиск...")
    
    try:
        entity = await telegram_client.get_entity(input_str)
        
        if not entity:
            await status_msg.edit_text("❌ Пользователь не найден в Telegram")
            return
        
        user_data = {
            'user_id': entity.id,
            'username': entity.username,
            'first_name': entity.first_name,
            'last_name': entity.last_name,
            'phone': entity.phone if hasattr(entity, 'phone') else None,
            'bio': entity.about if hasattr(entity, 'about') else None,
            'premium': entity.premium if hasattr(entity, 'premium') else None,
            'verified': entity.verified if hasattr(entity, 'verified') else None,
        }
        
        try:
            common_chats = await telegram_client.get_common_chats(entity.id)
            user_data['common_chats_count'] = len(common_chats) if common_chats else 0
        except:
            user_data['common_chats_count'] = 0
        
        social_task = None
        breach_task = None
        
        if entity.username:
            social_task = asyncio.create_task(
                social_scanner.scan_username(entity.username)
            )
        
        if user_data.get('phone'):
            breach_task = asyncio.create_task(
                breach_checker.check_phone_breach(user_data['phone'])
            )
        
        social_results = {}
        breach_results = []
        
        if social_task:
            social_results = await social_task
        
        if breach_task:
            breach_results = await breach_task
        
        correlation_data = correlation_engine.merge_entities([user_data])
        
        report = formatter.generate_full_report(
            user_data,
            social_results,
            breach_results,
            correlation_data
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton("📅 По дате рождения", callback_data=f"narrow_birthdate_{entity.id}"),
                    InlineKeyboardButton("👥 Связанные пользователи", callback_data=f"narrow_users_{entity.id}")
                ],
                [
                    InlineKeyboardButton("📱 Поиск по другим номерам", callback_data=f"narrow_phone_{entity.id}"),
                    InlineKeyboardButton("🌐 Расширить по соцсетям", callback_data=f"narrow_social_{entity.id}")
                ],
                [
                    InlineKeyboardButton("📄 Скачать PDF", callback_data=f"pdf_{entity.id}")
                ]
            ]
        )
        
        await status_msg.delete()
        await message.answer(
            report,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        await state.update_data({
            'entity_id': entity.id,
            'user_data': user_data,
            'social_results': social_results,
            'breach_results': breach_results
        })
        
    except ValueError as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка в search: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка: {str(e)}")

@router.callback_query(F.data.startswith("narrow_"))
async def handle_narrowing(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик уточняющих запросов"""
    data = callback.data.split('_')
    action = data[1]
    entity_id = data[2]
    
    await callback.answer()
    
    if action == "birthdate":
        await callback.message.edit_text(
            "📅 Введите дату рождения в формате ДД.ММ.ГГГГ\n"
            "Например: 15.03.1990"
        )
        await state.set_state(SearchStates.waiting_for_birthdate)
        await state.update_data({'entity_id': entity_id})
    
    elif action == "users":
        await callback.message.edit_text(
            "👥 Поиск связанных пользователей...\n"
            "Это может занять некоторое время."
        )
        
        try:
            common_chats = await telegram_client.get_common_chats(int(entity_id))
            if common_chats:
                users = []
                for chat in common_chats[:5]:
                    try:
                        participants = await telegram_client.client.get_participants(chat, limit=20)
                        users.extend([p for p in participants if p.id != int(entity_id)])
                    except:
                        continue
                
                unique_users = {}
                for user in users:
                    if user.id not in unique_users:
                        unique_users[user.id] = user
                
                if unique_users:
                    msg = "👥 *Найдены связанные пользователи:*\n\n"
                    for user in list(unique_users.values())[:10]:
                        name = user.first_name or "Без имени"
                        username = f"@{user.username}" if user.username else "нет username"
                        msg += f"• {name} — {username} (ID: `{user.id}`)\n"
                    
                    await callback.message.edit_text(
                        msg,
                        parse_mode="HTML"
                    )
                else:
                    await callback.message.edit_text("❌ Связанные пользователи не найдены")
            else:
                await callback.message.edit_text("❌ Нет общих чатов для поиска связей")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
    
    elif action == "phone":
        await callback.message.edit_text(
            "📱 Введите номер телефона для поиска (в формате +7...):"
        )
        await state.set_state(SearchStates.waiting_for_input)
        await state.update_data({'entity_id': entity_id})
    
    elif action == "social":
        await callback.message.edit_text(
            "🌐 Расширенный поиск по соцсетям...\n"
            "Это может занять некоторое время."
        )
        try:
            data = await state.get_data()
            username = data.get('user_data', {}).get('username')
            if username:
                results = await social_scanner.scan_username(username)
                if results:
                    msg = "🌐 *Найдены аккаунты:*\n\n"
                    for platform, url in results.items():
                        msg += f"• [{platform}]({url})\n"
                    await callback.message.edit_text(msg, parse_mode="HTML")
                else:
                    await callback.message.edit_text("❌ Аккаунты не найдены")
            else:
                await callback.message.edit_text("❌ Нет username для поиска")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
    
    elif action == "pdf":
        await callback.message.edit_text("📄 Генерация PDF... (функция в разработке)")