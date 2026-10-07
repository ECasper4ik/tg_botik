from typing import List, Dict, Set, Any
from datetime import datetime
import re

class CorrelationEngine:
    """
    Анализирует связи между пользователями и находит корреляции
    """
    
    def __init__(self):
        self.common_chats_cache = {}
    
    def extract_usernames_from_text(self, text: str) -> List[str]:
        """Извлекает возможные usernames из текста"""
        pattern = r'@([a-zA-Z0-9_]{4,32})'
        return re.findall(pattern, text)
    
    def extract_phones_from_text(self, text: str) -> List[str]:
        """Извлекает номера телефонов из текста"""
        pattern = r'(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        return re.findall(pattern, text)
    
    def extract_emails_from_text(self, text: str) -> List[str]:
        """Извлекает email из текста"""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)
    
    def find_connections(self, chat_members: List[int], target_id: int) -> List[int]:
        """
        Находит пользователей, которые состоят в нескольких общих чатах с целью
        """
        # Это упрощённая версия — в реальности требует анализа графов
        return []
    
    def calculate_trust_score(self, entity_data: Dict) -> float:
        """
        Вычисляет "степень доверия" к найденной информации
        """
        score = 0.0
        factors = {
            'has_verified_phone': 0.2,
            'has_verified_email': 0.15,
            'has_common_chats': 0.25,
            'has_bio': 0.1,
            'has_profile_photo': 0.1,
            'premium_account': 0.1,
            'account_age_days': 0.1
        }
        
        # Проверка каждого фактора
        if entity_data.get('phone_confirmed'):
            score += factors['has_verified_phone']
        if entity_data.get('email_confirmed'):
            score += factors['has_verified_email']
        if entity_data.get('common_chats_count', 0) > 0:
            score += factors['has_common_chats']
        if entity_data.get('bio'):
            score += factors['has_bio']
        if entity_data.get('photo'):
            score += factors['has_profile_photo']
        if entity_data.get('premium'):
            score += factors['premium_account']
        
        # Возраст аккаунта (если есть дата регистрации)
        if entity_data.get('registration_date'):
            days = (datetime.now() - entity_data['registration_date']).days
            if days > 365:
                score += factors['account_age_days']
        
        return min(score, 1.0)
    
    def merge_entities(self, entities: list):
        merged = {
            'user_ids': set(),
            'usernames': set(),
            'phones': set(),
            'emails': set(),
            'names': set(),
            'platforms': {},
            'common_chats': set(),
            'confidence_score': 0.0
        }

        for entity in entities:
            # Объединение данных
            if entity.get('user_id'):
                merged['user_ids'].add(entity['user_id'])
            if entity.get('username'):
                merged['usernames'].add(entity['username'])
            if entity.get('phone'):
                merged['phones'].add(entity['phone'])
            if entity.get('email'):
                merged['emails'].add(entity['email'])
            if entity.get('name'):
                merged['names'].add(entity['name'])
            
            # Платформы
            if entity.get('platforms'):
                merged['platforms'].update(entity['platforms'])
            
            # Общие чаты
            if entity.get('common_chats'):
                merged['common_chats'].update(entity['common_chats'])
        
        # Конвертация множеств в списки для сериализации
        merged['user_ids'] = list(merged['user_ids'])
        merged['usernames'] = list(merged['usernames'])
        merged['phones'] = list(merged['phones'])
        merged['emails'] = list(merged['emails'])
        merged['names'] = list(merged['names'])
        merged['common_chats'] = list(merged['common_chats'])
        
        return merged

correlation_engine = CorrelationEngine()
