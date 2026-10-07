"""
Управление согласиями на проверку цифрового следа.

Модель (вариант «запрос с подтверждением цели»):
  1. Оператор инициирует запрос на проверку конкретного пользователя.
  2. Бот отправляет САМОМУ проверяемому запрос с кнопками «Разрешаю» / «Нет».
  3. Проверка выполняется только после явного согласия субъекта.

Технические гарантии честности согласия:
  - запрос можно доставить только пользователю, который сам запускал бота
    (ограничение Telegram + собственный реестр UserRegistry);
  - подтвердить согласие может только сам субъект (сверяется user_id);
  - согласие одноразовое и имеет срок жизни;
  - на одного и того же субъекта оператор не может слать запросы слишком часто.

Проверяется только собственный цифровой след субъекта. Сбор данных о третьих
лицах (участники общих чатов и т. п.) в этой модели не предусмотрен.
"""
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple


REQUEST_TTL_SECONDS = 15 * 60       # запрос согласия живёт 15 минут
REQUEST_COOLDOWN_SECONDS = 5 * 60   # не чаще одного запроса на субъекта в 5 минут


class ConsentStatus(str, Enum):
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"


class ConsentError(Exception):
    pass


class RequestNotFoundError(ConsentError):
    pass


class RequestExpiredError(ConsentError):
    pass


class NotTargetError(ConsentError):
    """Подтверждение/отказ пришёл не от самого проверяемого."""


class AlreadyAnsweredError(ConsentError):
    pass


class RequestTooSoonError(ConsentError):
    pass


@dataclass
class ConsentRequest:
    token: str
    operator_id: int
    target_id: int
    target_username: Optional[str]
    created_at: float
    expires_at: float
    status: ConsentStatus = ConsentStatus.PENDING


class UserRegistry:
    """
    Запоминает пользователей, которые взаимодействовали с ботом,
    чтобы оператор мог адресовать запрос по @username, а бот — доставить его.
    """

    def __init__(self):
        self._by_id: Dict[int, Optional[str]] = {}
        self._by_username: Dict[str, int] = {}

    def register(self, user_id: int, username: Optional[str]) -> None:
        old = self._by_id.get(user_id)
        if old and old.lower() in self._by_username:
            # чистим устаревший username, если пользователь его сменил
            if self._by_username.get(old.lower()) == user_id:
                del self._by_username[old.lower()]
        self._by_id[user_id] = username
        if username:
            self._by_username[username.lower()] = user_id

    def resolve(self, identifier: str) -> Optional[int]:
        """Возвращает user_id по @username или по числовому id, если известен."""
        identifier = identifier.strip()
        if identifier.startswith("@"):
            return self._by_username.get(identifier[1:].lower())
        if identifier.isdigit():
            uid = int(identifier)
            return uid if uid in self._by_id else None
        return self._by_username.get(identifier.lower())

    def username_of(self, user_id: int) -> Optional[str]:
        return self._by_id.get(user_id)


class ConsentManager:
    def __init__(self, ttl: int = REQUEST_TTL_SECONDS,
                 cooldown: int = REQUEST_COOLDOWN_SECONDS):
        self._store: Dict[str, ConsentRequest] = {}
        self._last_request: Dict[Tuple[int, int], float] = {}
        self._ttl = ttl
        self._cooldown = cooldown

    def _now(self) -> float:
        return time.monotonic()

    def create_request(self, operator_id: int, target_id: int,
                       target_username: Optional[str]) -> ConsentRequest:
        now = self._now()
        key = (operator_id, target_id)
        last = self._last_request.get(key)
        if last is not None and (now - last) < self._cooldown:
            raise RequestTooSoonError(int(self._cooldown - (now - last)))

        token = secrets.token_urlsafe(8)
        req = ConsentRequest(
            token=token,
            operator_id=operator_id,
            target_id=target_id,
            target_username=target_username,
            created_at=now,
            expires_at=now + self._ttl,
        )
        self._store[token] = req
        self._last_request[key] = now
        return req

    def _get_live(self, token: str) -> ConsentRequest:
        req = self._store.get(token)
        if req is None:
            raise RequestNotFoundError()
        if self._now() > req.expires_at:
            self._store.pop(token, None)
            raise RequestExpiredError()
        return req

    def _answer(self, token: str, by_user_id: int,
                status: ConsentStatus) -> ConsentRequest:
        req = self._get_live(token)
        if by_user_id != req.target_id:
            raise NotTargetError()
        if req.status is not ConsentStatus.PENDING:
            raise AlreadyAnsweredError()
        req.status = status
        return req

    def grant(self, token: str, by_user_id: int) -> ConsentRequest:
        return self._answer(token, by_user_id, ConsentStatus.GRANTED)

    def deny(self, token: str, by_user_id: int) -> ConsentRequest:
        return self._answer(token, by_user_id, ConsentStatus.DENIED)

    def consume(self, token: str) -> None:
        """Удаляет запрос после использования результата."""
        self._store.pop(token, None)

    def purge_expired(self) -> int:
        now = self._now()
        expired = [t for t, r in self._store.items() if now > r.expires_at]
        for t in expired:
            del self._store[t]
        return len(expired)


# Глобальные экземпляры
user_registry = UserRegistry()
consent_manager = ConsentManager()
