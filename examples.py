"""
Примеры использования Invoice Maker API
"""

import requests
import json
from datetime import datetime, timedelta

# Базовый URL API
BASE_URL = "http://localhost:8080"

def example_get_templates():
    """Пример получения шаблонов"""
    print("=== Получение шаблонов ===")
    
    params = {
        "app_id": "my-app-123",
        "user_id": "user-456"
    }
    
    response = requests.get(f"{BASE_URL}/templates", params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Найдено {len(data['templates'])} шаблонов:")
        for template in data['templates']:
            print(f"- {template['name']} ({template['style']}) - {'Премиум' if template['is_premium'] else 'Бесплатный'}")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

def example_generate_invoice():
    """Пример генерации инвойса"""
    print("\n=== Генерация инвойса ===")
    
    # Данные для инвойса
    invoice_data = {
        "invoice_data": {
            "app_id": "my-app-123",
            "user_id": "user-456",
            "template_id": "modern-blue",
            "invoice_number": "INV-2024-001",
            "invoice_date": datetime.now().isoformat(),
            "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
            
            "company": {
                "name": "ООО 'Строительная Компания'",
                "address": "г. Москва, ул. Строителей, д. 15",
                "phone": "+7 (495) 123-45-67",
                "email": "info@stroyka.ru",
                "website": "www.stroyka.ru",
                "tax_id": "7701234567"
            },
            
            "client": {
                "name": "ИП Иванов Иван Иванович",
                "address": "г. Москва, ул. Клиентская, д. 10",
                "phone": "+7 (495) 987-65-43",
                "email": "ivanov@example.com"
            },
            
            "items": [
                {
                    "description": "Строительные работы по возведению фундамента",
                    "quantity": 1,
                    "unit_price": 150000.00
                },
                {
                    "description": "Материалы: цемент, арматура, песок",
                    "quantity": 1,
                    "unit_price": 75000.00
                },
                {
                    "description": "Доставка материалов",
                    "quantity": 3,
                    "unit_price": 5000.00
                }
            ],
            
            "tax_rate": 20.0,
            "discount_rate": 5.0,
            "notes": "Оплата в течение 30 дней с момента выставления счета.",
            "terms": "При просрочке платежа начисляется пеня 0.1% за каждый день просрочки."
        },
        "async_generation": False
    }
    
    response = requests.post(f"{BASE_URL}/generate", json=invoice_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Инвойс сгенерирован!")
        print(f"ID генерации: {data['generation_id']}")
        print(f"Статус: {data['status']}")
        if data.get('pdf_url'):
            print(f"PDF доступен по адресу: {BASE_URL}{data['pdf_url']}")
        return data['generation_id']
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None

def example_check_status(generation_id):
    """Пример проверки статуса генерации"""
    print(f"\n=== Проверка статуса генерации {generation_id} ===")
    
    response = requests.get(f"{BASE_URL}/status/{generation_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Статус: {data['status']}")
        if data.get('progress'):
            print(f"Прогресс: {data['progress']}%")
        if data.get('pdf_url'):
            print(f"PDF доступен: {BASE_URL}{data['pdf_url']}")
        if data.get('error_message'):
            print(f"Ошибка: {data['error_message']}")
        print(f"Создано: {data['created_at']}")
        if data.get('completed_at'):
            print(f"Завершено: {data['completed_at']}")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

def example_async_generation():
    """Пример асинхронной генерации"""
    print("\n=== Асинхронная генерация ===")
    
    invoice_data = {
        "invoice_data": {
            "app_id": "my-app-123",
            "user_id": "user-456",
            "template_id": "corporate-professional",
            "invoice_number": "INV-2024-002",
            "invoice_date": datetime.now().isoformat(),
            
            "company": {
                "name": "ООО 'Большая Стройка'",
                "address": "г. Санкт-Петербург, пр. Невский, д. 100",
                "phone": "+7 (812) 123-45-67",
                "email": "info@bigbuild.ru"
            },
            
            "client": {
                "name": "ООО 'Заказчик'",
                "address": "г. Санкт-Петербург, ул. Заказная, д. 5"
            },
            
            "items": [
                {
                    "description": "Комплексные строительные работы",
                    "quantity": 1,
                    "unit_price": 500000.00
                }
            ],
            
            "tax_rate": 20.0
        },
        "async_generation": True
    }
    
    response = requests.post(f"{BASE_URL}/generate", json=invoice_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Асинхронная генерация запущена!")
        print(f"ID генерации: {data['generation_id']}")
        print(f"Статус: {data['status']}")
        print(f"Сообщение: {data['message']}")
        
        # Проверяем статус через некоторое время
        import time
        time.sleep(2)
        example_check_status(data['generation_id'])
        
        return data['generation_id']
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None

def example_get_template_styles():
    """Пример получения стилей шаблонов"""
    print("\n=== Доступные стили шаблонов ===")
    
    response = requests.get(f"{BASE_URL}/templates/styles")
    
    if response.status_code == 200:
        data = response.json()
        print("Доступные стили:")
        for style in data['styles']:
            description = data['descriptions'].get(style, "Описание недоступно")
            print(f"- {style}: {description}")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

def example_get_free_templates():
    """Пример получения бесплатных шаблонов"""
    print("\n=== Бесплатные шаблоны ===")
    
    response = requests.get(f"{BASE_URL}/templates/free")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Найдено {len(data['templates'])} бесплатных шаблонов:")
        for template in data['templates']:
            print(f"- {template['name']} ({template['style']})")
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("Примеры использования Invoice Maker API")
    print("=====================================")
    
    # Проверяем доступность API
    try:
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            print("API недоступен. Убедитесь, что сервер запущен на http://localhost:8000")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("Не удается подключиться к API. Запустите сервер командой: python main.py")
        exit(1)
    
    # Запускаем примеры
    example_get_template_styles()
    example_get_free_templates()
    example_get_templates()
    
    # Генерируем инвойс
    generation_id = example_generate_invoice()
    if generation_id:
        example_check_status(generation_id)
    
    # Асинхронная генерация
    async_generation_id = example_async_generation()
    
    print("\n=== Завершено ===")
    print("Все примеры выполнены. Проверьте папку 'generated_invoices' для созданных PDF файлов.")