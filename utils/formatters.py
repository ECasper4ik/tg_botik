import re
from datetime import datetime
from typing import Dict, List, Any

class ReportFormatter:
    """
    Форматирует отчёты для отправки в Telegram
    """
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Экранирует специальные символы для MarkdownV2
        """
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    
    @staticmethod
    def format_user_info(user_data: Dict) -> str:
        """Форматирует информацию о пользователе"""
        lines = []
        
        # Основная информация
        if user_data.get('first_name'):
            name = user_data['first_name']
            if user_data.get('last_name'):
                name += f" {user_data['last_name']}"
            lines.append(f"👤 *Имя:* {ReportFormatter.escape_markdown(name)}")
        
        if user_data.get('username'):
            lines.append(f"🆔 *Username:* @{ReportFormatter.escape_markdown(user_data['username'])}")
        
        if user_data.get('user_id'):
            lines.append(f"🔢 *User ID:* `{user_data['user_id']}`")
        
        if user_data.get('phone'):
            lines.append(f"📱 *Телефон:* `{ReportFormatter.escape_markdown(user_data['phone'])}`")
        
        if user_data.get('email'):
            lines.append(f"📧 *Email:* `{ReportFormatter.escape_markdown(user_data['email'])}`")
        
        if user_data.get('bio'):
            bio = ReportFormatter.escape_markdown(user_data['bio'][:500])
            lines.append(f"📝 *О себе:* {bio}")
        
        if user_data.get('premium'):
            lines.append("⭐ *Premium:* Да")
        
        if user_data.get('verified'):
            lines.append("✅ *Верифицирован:* Да")
        
        if user_data.get('common_chats_count') is not None:
            lines.append(f"💬 *Общих чатов:* {user_data['common_chats_count']}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_social_results(results: Dict[str, str]) -> str:
        """Форматирует результаты поиска по соцсетям"""
        if not results:
            return "🔍 *Соцсети:* Аккаунты не найдены"
        
        lines = ["🌐 *Найденные аккаунты:*"]
        for platform, url in results.items():
            lines.append(f"• [{platform}]({url})")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_breach_results(breaches: List[Dict]) -> str:
        """Форматирует результаты проверки утечек"""
        if not breaches:
            return "🔒 *Утечки:* Не найдено"
        
        lines = ["⚠️ *Найдено в утечках:*"]
        for breach in breaches[:10]:  # Ограничиваем 10
            name = breach.get('Name', 'Неизвестно')
            date = breach.get('BreachDate', 'Неизвестно')
            lines.append(f"• {name} ({date})")
        
        if len(breaches) > 10:
            lines.append(f"… и ещё {len(breaches) - 10}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_correlation_report(correlation_data: Dict) -> str:
        """Форматирует отчёт о корреляциях"""
        lines = ["🔗 *Корреляции:*"]
        
        if correlation_data.get('common_chats'):
            lines.append(f"• Общих чатов: {len(correlation_data['common_chats'])}")
        
        if correlation_data.get('related_users'):
            lines.append(f"• Связанных пользователей: {len(correlation_data['related_users'])}")
        
        if correlation_data.get('confidence_score') is not None:
            score = correlation_data['confidence_score'] * 100
            lines.append(f"• Уверенность: {score:.1f}%")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_footprint_report(username: str,
                                  social_results: Dict[str, str]) -> str:
        """
        Отчёт о цифровом следе субъекта, построенный ПОСЛЕ его явного согласия.
        Содержит только публичные аккаунты самого субъекта.
        """
        sections = []
        sections.append("🌐 *ОТЧЁТ О ЦИФРОВОМ СЛЕДЕ*")
        sections.append(
            f"Субъект: @{ReportFormatter.escape_markdown(username.lstrip('@'))} "
            "✅ проверка выполнена с его согласия"
        )
        sections.append("━" * 30)
        sections.append(ReportFormatter.format_social_results(social_results))
        sections.append("━" * 30)
        sections.append(
            f"🕐 *Сгенерировано:* {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        return "\n".join(sections)

    @staticmethod
    def generate_self_check_report(identifier_label: str,
                                   identifier_value: str,
                                   breaches: List[Dict]) -> str:
        """
        Отчёт самопроверки для подтверждённого контакта самого пользователя.
        Не содержит данных о третьих лицах.
        """
        sections = []
        sections.append("🛡 *ОТЧЁТ ПРОВЕРКИ ВАШИХ ДАННЫХ*\n")
        sections.append("━" * 30)
        sections.append(
            f"{identifier_label}: "
            f"`{ReportFormatter.escape_markdown(identifier_value)}` ✅ подтверждён\n"
        )
        sections.append(ReportFormatter.format_breach_results(breaches))

        if breaches:
            sections.append(
                "\n💡 *Рекомендации:*\n"
                "• смените пароли на затронутых сервисах;\n"
                "• включите двухфакторную аутентификацию;\n"
                "• не используйте один пароль на разных сайтах."
            )

        sections.append("\n━" * 1)
        sections.append(
            f"🕐 *Сгенерировано:* {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        return "\n".join(sections)


formatter = ReportFormatter()
