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
    
    # Браузерный User-Agent снижает число ложных блокировок/404 от площадок
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, timeout: int = 7, concurrency: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._semaphore = asyncio.Semaphore(concurrency)

    async def check_platform(self, session: aiohttp.ClientSession,
                             platform: str, url_template: str,
                             username: str) -> Optional[str]:
        """Проверяет существование аккаунта на одной платформе."""
        url = url_template.format(username=username)
        async with self._semaphore:
            try:
                # GET надёжнее HEAD: часть площадок не отвечает на HEAD корректно
                async with session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers=self.HEADERS,
                ) as response:
                    # 200 на конечном URL — аккаунт, скорее всего, существует.
                    # Редирект на страницу логина/главную обычно означает «нет».
                    if response.status == 200 and self._looks_like_profile(response, url):
                        return url
                    return None
            except (aiohttp.ClientError, asyncio.TimeoutError):
                return None

    @staticmethod
    def _looks_like_profile(response: aiohttp.ClientResponse, requested_url: str) -> bool:
        """Грубая эвристика: финальный URL не ушёл на /login, /404 и т. п."""
        final = str(response.url).rstrip("/").lower()
        bad_markers = ("/login", "/signup", "/404", "/error", "not-found")
        return not any(m in final for m in bad_markers)

    async def scan_username(self, username: str) -> Dict[str, str]:
        """
        Сканирует все платформы и возвращает словарь {платформа: url}.

        ВНИМАНИЕ: запускать только для собственного ника субъекта и только
        после его явного согласия (см. handlers/consent.py). Результат —
        best-effort: часть площадок защищена от автоматических проверок,
        поэтому возможны ложные пропуски.
        """
        username = username.lstrip("@").strip()
        results: Dict[str, str] = {}
        async with aiohttp.ClientSession() as session:
            tasks = {
                platform: asyncio.create_task(
                    self.check_platform(session, platform, tpl, username)
                )
                for platform, tpl in self.PLATFORMS.items()
            }
            for platform, task in tasks.items():
                try:
                    url = await task
                    if url:
                        results[platform] = url
                except Exception:
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
