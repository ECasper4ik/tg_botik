import aiohttp
import hashlib
from typing import List, Dict, Optional
from config import config

class BreachChecker:
    """
    Проверка email и телефона в базах утечек
    """
    
    def __init__(self):
        self.hibp_api_key = config.HIBP_API_KEY
    
    async def check_email_hibp(self, email: str) -> List[Dict]:
        """
        Проверка email через Have I Been Pwned API
        """
        if not self.hibp_api_key:
            return []
        
        # truncateResponse=false — чтобы получить категории утёкших данных (DataClasses)
        url = (
            "https://haveibeenpwned.com/api/v3/breachedaccount/"
            f"{email}?truncateResponse=false"
        )
        headers = {
            "hibp-api-key": self.hibp_api_key,
            "User-Agent": "OSINT-Bot"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return []
                    else:
                        return []
        except:
            return []
    
    async def check_phone_breach(self, phone: str) -> List[Dict]:
        """
        Проверка телефона в открытых базах утечек
        Использует публичные источники (например, leak-check.net API)
        """
        # Реализация через сторонние API
        # Это пример заглушки
        return []
    
    async def check_password_hash(self, password_hash: str) -> int:
        """
        Проверка хэша пароля через Pwned Passwords API (k-Anonymity)
        Возвращает количество раз, когда пароль встречался в утечках
        """
        if len(password_hash) < 5:
            return 0
        
        prefix = password_hash[:5]
        suffix = password_hash[5:].upper()
        
        url = f"https://api.pwnedpasswords.com/range/{prefix}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.text()
                        for line in data.splitlines():
                            # формат строки: SUFFIX:count
                            parts = line.split(':')
                            if parts[0].strip().upper() == suffix:
                                return int(parts[1])
                    return 0
        except aiohttp.ClientError:
            return 0

    async def check_password(self, password: str) -> int:
        """
        Проверяет пароль через Pwned Passwords API по k-анонимности.
        SHA-1 хэш считается локально; на сервер уходят только первые 5 символов.
        """
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        return await self.check_password_hash(sha1)


breach_checker = BreachChecker()
