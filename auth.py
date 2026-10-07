# auth.py
import asyncio
import re
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from config import config

async def main():
    client = TelegramClient('session_name', config.API_ID, config.API_HASH)
    
    await client.connect()
    
    if not await client.is_user_authorized():
        print("🔐 Требуется авторизация")
        phone = input("📱 Введите номер телефона (в формате +7XXXXXXXXXX): ")
        
        # Очищаем номер от лишних символов
        phone = re.sub(r'[^\d+]', '', phone)
        
        # Отправляем запрос кода
        await client.send_code_request(phone)
        code = input("📨 Введите код из Telegram: ")
        
        try:
            # Пытаемся войти с кодом
            await client.sign_in(phone, code)
            print("✅ Авторизация успешна!")
        except SessionPasswordNeededError:
            # Если включена 2FA — запрашиваем пароль
            password = input("🔑 Введите пароль двухфакторной аутентификации: ")
            await client.sign_in(password=password)
            print("✅ Авторизация с 2FA успешна!")
    else:
        print("✅ Уже авторизованы")
    
    me = await client.get_me()
    print(f"👤 Аккаунт: {me.first_name} (@{me.username})")
    print(f"🆔 User ID: {me.id}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())