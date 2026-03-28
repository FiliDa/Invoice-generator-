# Invoice Generator API

Профессиональный REST API для генерации счетов-фактур с поддержкой множества шаблонов и автоматическими расчетами.

## 🚀 Возможности

- **8 готовых шаблонов** - различные стили для разных отраслей
- **PDF генерация** - высококачественные PDF документы
- **Автоматические расчеты** - налоги, скидки, итоговые суммы
- **Поддержка логотипов** - брендирование счетов
- **REST API** - легкая интеграция с любыми системами
- **Синхронная/асинхронная** обработка
- **Статус генерации** - отслеживание выполнения задач

## 📦 Установка

### Требования
- Python 3.8+
- pip

### Быстрый старт
```bash
# Клонирование репозитория
git clone <repository-url>
cd Invoice

# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
python main.py
```

## 🛠️ Использование

### Пример запроса
```python
import requests

url = "http://localhost:5000/generate-invoice"
data = {
    "template": "professional",
    "company_name": "ООО Рога и копыта",
    "items": [
        {"name": "Услуги разработки", "quantity": 10, "price": 5000}
    ]
}

response = requests.post(url, json=data)
with open('invoice.pdf', 'wb') as f:
    f.write(response.content)
```

### API Endpoints

- `POST /generate-invoice` - Генерация счета
- `GET /templates` - Список доступных шаблонов
- `GET /status/{task_id}` - Статус задачи

## 🏗️ Архитектура

```
Invoice/
├── main.py              # Основное приложение
├── models.py            # Модели данных
├── admin.py             # Админ-панель
├── static/              # Статические файлы
│   └── admin.css        # Стили админки
├── templates/           # Шаблоны счетов
└── requirements.txt     # Зависимости
```

## 🔧 Конфигурация

Создайте файл `.env` на основе `.env.example`:
```bash
PORT=5000
DEBUG=false
```

## 📊 Деплой

### Локальный запуск
```bash
python main.py
```

### Docker
```bash
docker build -t invoice-generator .
docker run -p 5000:5000 invoice-generator
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте feature ветку
3. Внесите изменения
4. Откройте Pull Request

## 📝 Лицензия

MIT License - смотрите файл LICENSE для подробностей.

## 🆘 Поддержка

- Создайте Issue в GitHub
- Email: ваш-email@example.com