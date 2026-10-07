from telethon import TelegramClient
from telethon.errors import PhoneNumberInvalidError, UsernameInvalidError
from telethon.tl.types import User, UserFull
import asyncio
from config import config

class TelegramAPIClient:
    def __init__(self):
        self.client = TelegramClient(
            'session_name',           # Имя файла сессии
            config.API_ID,
            config.API_HASH
        )
        self._connected = False

    async def connect(self):
        """Подключение к Telegram API"""
        if not self._connected:
            await self.client.connect()
            # Проверка авторизации
            if not await self.client.is_user_authorized():
                # Запрос кода подтверждения (требуется для работы с номерами)
                raise Exception("Необходима авторизация в Telegram. Используйте функцию login()")
            self._connected = True
    
    async def login(self, phone: str, code_callback=None):
        """
        Авторизация пользователя бота в Telegram.
        Требуется для доступа к поиску по номерам телефонов.
        """
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(phone)
            if code_callback:
                code = await code_callback()
                await self.client.sign_in(phone, code)
    
    async def get_entity(self, input_str: str) -> User:
        """
        Получение пользователя по:
        - username (с @ или без)
        - user_id (число)
        - phone (в международном формате)
        """
        await self.connect()
        try:
            entity = await self.client.get_entity(input_str)
            if isinstance(entity, User):
                return entity
            return None
        except (PhoneNumberInvalidError, UsernameInvalidError, ValueError) as e:
            raise ValueError(f"Пользователь не найден: {e}")
    
    async def get_full_user_info(self, user_id: int) -> UserFull:
        """Получение расширенной информации о пользователе"""
        await self.connect()
        try:
            return await self.client.get_entity(user_id)
        except:
            return None
    
    async def get_common_chats(self, user_id: int):
        """Получение общих чатов с пользователем"""
        await self.connect()
        try:
            return await self.client.get_common_chats(user_id)
        except:
            return []
    
    async def get_profile_photos(self, user_id: int, limit: int = 5):
        """Получение фото профиля пользователя"""
        await self.connect()
        try:
            photos = await self.client.get_profile_photos(user_id, limit=limit)
            return photos
        except:
            return []
    
    async def get_contacts(self):
        """Получение списка контактов (требует авторизации)"""
        await self.connect()
        try:
            return await self.client.get_contacts()
        except:
            return []
    
    async def close(self):
        """Закрытие соединения"""
        if self._connected:
            await self.client.disconnect()
            self._connected = False

# Создаём глобальный экземпляр
telegram_client = TelegramAPIClient()
