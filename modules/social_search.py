import aiohttp
import asyncio
from typing import Dict, List, Optional

class SocialMediaScanner:
    """
    Сканирует наличие аккаунта по никнейму на различных платформах
    """
    
    # Список платформ с URL-шаблонами
    PLATFORMS = {
        'Instagram': 'https://www.instagram.com/{username}',
        'Twitter': 'https://twitter.com/{username}',
        'GitHub': 'https://github.com/{username}',
        'VK': 'https://vk.com/{username}',
        'YouTube': 'https://www.youtube.com/@{username}',
        'TikTok': 'https://www.tiktok.com/@{username}',
        'Reddit': 'https://www.reddit.com/user/{username}',
        'Pinterest': 'https://www.pinterest.com/{username}',
        'Tumblr': 'https://{username}.tumblr.com',
        'Flickr': 'https://www.flickr.com/people/{username}',
        'SoundCloud': 'https://soundcloud.com/{username}',
        'Spotify': 'https://open.spotify.com/user/{username}',
        'Discord': 'https://discord.com/users/{username}',
        'Telegram': 'https://t.me/{username}',
        'WhatsApp': 'https://wa.me/{username}',
        'Snapchat': 'https://www.snapchat.com/add/{username}',
        'LinkedIn': 'https://www.linkedin.com/in/{username}',
        'Facebook': 'https://www.facebook.com/{username}',
        'Tinder': 'https://tinder.com/@{username}',
        'Badoo': 'https://badoo.com/{username}',
        'OK.ru': 'https://ok.ru/{username}',
        'MoiMir': 'https://my.mail.ru/{username}',
        'Habr': 'https://habr.com/ru/users/{username}',
        'Pikabu': 'https://pikabu.ru/{username}',
        '2ch': 'https://2ch.hk/{username}',
        'Twitch': 'https://www.twitch.tv/{username}',
    }
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=5)
    
    async def check_platform(self, session: aiohttp.ClientSession, 
                            platform: str, url_template: str, 
                            username: str) -> Optional[str]:
        """Проверяет существование аккаунта на одной платформе"""
        url = url_template.format(username=username)
        try:
            async with session.head(url, timeout=self.timeout, allow_redirects=True) as response:
                if response.status == 200:
                    return url
                elif response.status == 404:
                    return None
                else:
                    # Некоторые платформы возвращают 302/301 при существовании
                    if response.status in [301, 302]:
                        return url
                    return None
        except:
            return None
    
    async def scan_username(self, username: str) -> Dict[str, str]:
        """
        Сканирует все платформы и возвращает словарь {платформа: url}
        """
        results = {}
        async with aiohttp.ClientSession() as session:
            tasks = []
            for platform, url_template in self.PLATFORMS.items():
                task = self.check_platform(session, platform, url_template, username)
                tasks.append((platform, task))
            
            for platform, task in tasks:
                try:
                    url = await task
                    if url:
                        results[platform] = url
                except:
                    continue
        
        return results
    
    async def search_by_email(self, email: str) -> Dict[str, str]:
        """
        Поиск по email (ограниченная поддержка)
        Использует публичные API, где это возможно
        """
        results = {}
        
        # Gravatar
        gravatar_hash = self._get_gravatar_hash(email)
        if gravatar_hash:
            results['Gravatar'] = f'https://www.gravatar.com/{gravatar_hash}'
        
        # Другие сервисы можно добавить аналогично
        return results
    
    @staticmethod
    def _get_gravatar_hash(email: str) -> str:
        import hashlib
        return hashlib.md5(email.lower().encode()).hexdigest()

social_scanner = SocialMediaScanner()
