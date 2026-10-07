"""
Профиль пользователя для детального разбора утечек.

Хранится ТОЛЬКО в памяти процесса и только для самого пользователя — это его
собственные данные, которые он вводит добровольно, чтобы бот мог показать,
какие утечки относятся именно к нему. На диск ничего не пишется.
"""
from typing import Dict, Optional, Any


class ProfileStore:
    def __init__(self):
        self._store: Dict[int, Dict[str, Any]] = {}

    def set_field(self, user_id: int, field: str, value: Any) -> None:
        self._store.setdefault(user_id, {})[field] = value

    def set(self, user_id: int, profile: Dict[str, Any]) -> None:
        self._store[user_id] = dict(profile)

    def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self._store.get(user_id)

    def clear(self, user_id: int) -> None:
        self._store.pop(user_id, None)

    def has(self, user_id: int) -> bool:
        return bool(self._store.get(user_id))


profile_store = ProfileStore()
