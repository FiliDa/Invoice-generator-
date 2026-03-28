import json
import os
from typing import List, Dict, Optional
from models import InvoiceTemplate, TemplateStyle

class TemplateService:
    def __init__(self):
        self.templates_file = "templates/templates.json"
        self.templates_cache = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Инициализация шаблонов по умолчанию (оставляем только 2)"""
        default_templates = [
            {
                "id": "modern-blue",
                "name": "Modern Blue",
                "style": "modern",
                "description": "Современный синий шаблон с чистым дизайном",
                "preview_url": "/static/previews/modern-blue.png",
                "is_premium": False
            },
            {
                "id": "thermal-receipt",
                "name": "Thermal Receipt",
                "style": "thermal",
                "description": "Чек для термопринтера 80мм с простым оформлением",
                "preview_url": "/static/previews/thermal-receipt.png",
                "is_premium": False
            }
        ]
        
        # Создаем файл шаблонов если его нет
        if not os.path.exists(self.templates_file):
            os.makedirs(os.path.dirname(self.templates_file), exist_ok=True)
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(default_templates, f, indent=2, ensure_ascii=False)
        
        # Загружаем шаблоны в кэш
        self._load_templates()
    
    def _load_templates(self):
        """Загрузка шаблонов из файла"""
        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
                self.templates_cache = {t['id']: t for t in templates_data}
        except Exception as e:
            print(f"Ошибка загрузки шаблонов: {e}")
            self.templates_cache = {}
    
    def get_templates_for_user(self, app_id: str, user_id: str) -> List[InvoiceTemplate]:
        """Получение доступных шаблонов для пользователя"""
        # В реальном приложении здесь была бы логика проверки подписки пользователя
        # Пока что возвращаем все шаблоны
        
        templates = []
        for template_data in self.templates_cache.values():
            template = InvoiceTemplate(**template_data)
            templates.append(template)
        
        return templates
    
    def get_free_templates(self) -> List[InvoiceTemplate]:
        """Получение бесплатных шаблонов"""
        templates = []
        for template_data in self.templates_cache.values():
            if not template_data.get('is_premium', False):
                template = InvoiceTemplate(**template_data)
                templates.append(template)
        
        return templates
    
    def get_premium_templates(self) -> List[InvoiceTemplate]:
        """Получение премиум шаблонов"""
        templates = []
        for template_data in self.templates_cache.values():
            if template_data.get('is_premium', False):
                template = InvoiceTemplate(**template_data)
                templates.append(template)
        
        return templates
    
    def get_template_by_id(self, template_id: str) -> Optional[InvoiceTemplate]:
        """Получение шаблона по ID"""
        template_data = self.templates_cache.get(template_id)
        if template_data:
            return InvoiceTemplate(**template_data)
        return None
    
    def get_templates_by_style(self, style: TemplateStyle) -> List[InvoiceTemplate]:
        """Получение шаблонов по стилю"""
        templates = []
        for template_data in self.templates_cache.values():
            if template_data['style'] == style.value:
                template = InvoiceTemplate(**template_data)
                templates.append(template)
        
        return templates
    
    def add_custom_template(self, template_data: dict) -> InvoiceTemplate:
        """Добавление пользовательского шаблона"""
        template = InvoiceTemplate(**template_data)
        
        # Добавляем в кэш
        self.templates_cache[template.id] = template_data
        
        # Сохраняем в файл
        self._save_templates()
        
        return template
    
    def update_template(self, template_id: str, template_data: dict) -> Optional[InvoiceTemplate]:
        """Обновление шаблона"""
        if template_id not in self.templates_cache:
            return None
        
        # Обновляем данные
        self.templates_cache[template_id].update(template_data)
        template = InvoiceTemplate(**self.templates_cache[template_id])
        
        # Сохраняем в файл
        self._save_templates()
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Удаление шаблона"""
        if template_id in self.templates_cache:
            del self.templates_cache[template_id]
            self._save_templates()
            return True
        return False
    
    def _save_templates(self):
        """Сохранение шаблонов в файл"""
        try:
            templates_list = list(self.templates_cache.values())
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates_list, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения шаблонов: {e}")
    
    def is_user_has_premium_access(self, app_id: str, user_id: str) -> bool:
        """Проверка доступа к премиум шаблонам"""
        # В реальном приложении здесь была бы проверка подписки
        # Пока что возвращаем True для демонстрации
        return True
    
    def get_template_style_by_id(self, template_id: str) -> Optional[TemplateStyle]:
        """Получение стиля шаблона по ID"""
        template_data = self.templates_cache.get(template_id)
        if template_data:
            return TemplateStyle(template_data['style'])
        return None

# Глобальный экземпляр сервиса шаблонов
template_service = TemplateService()