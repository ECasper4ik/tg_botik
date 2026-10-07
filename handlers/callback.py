from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data.startswith('narrow_'))
async def narrow_search(callback: CallbackQuery):

    entity_id = callback.data.split('_')[1]
    
    # Показываем пользователю варианты уточнения
    options = [
        "🔍 Поиск по дате рождения",
        "👥 Показать связанных пользователей из общих чатов",
        "📱 Найти ассоциированные номера телефонов",
        "🌐 Расширить поиск по соцсетям"
    ]
    
    await callback.message.edit_text(
        "Выберите метод уточнения:",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(opt, callback_data=f'narrow_{i}_{entity_id}')]
             for i, opt in enumerate(options)]
        )
    )