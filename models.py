from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TemplateStyle(str, Enum):
    MODERN = "modern"
    CLASSIC = "classic"
    MINIMAL = "minimal"
    CORPORATE = "corporate"
    THERMAL = "thermal"
    CUSTOM = "custom"
    IT_PRO = "it_pro"
    MEDICAL_PRO = "medical_pro"
    CONSTRUCTION_PRO = "construction_pro"
    CREATIVE_PRO = "creative_pro"
    LEGAL_PRO = "legal_pro"

class CompanyInfo(BaseModel):
    name: str = Field(..., description="Название компании")
    address: str = Field(..., description="Адрес компании")
    phone: Optional[str] = Field(None, description="Телефон")
    email: Optional[str] = Field(None, description="Email")
    website: Optional[str] = Field(None, description="Веб-сайт")
    tax_id: Optional[str] = Field(None, description="Налоговый номер")
    logo_url: Optional[str] = Field(None, description="URL логотипа")
    logo_base64: Optional[str] = Field(None, description="Base64 (data URL) логотипа для встраивания без загрузки на сервер")

class ClientInfo(BaseModel):
    name: str = Field(..., description="Имя клиента/компании")
    address: str = Field(..., description="Адрес клиента")
    phone: Optional[str] = Field(None, description="Телефон клиента")
    email: Optional[str] = Field(None, description="Email клиента")

class InvoiceItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=120, description="Описание товара/услуги (1–120 символов)")
    quantity: float = Field(..., gt=0, le=100000, description="Количество (>0 и ≤ 100000)")
    unit_price: float = Field(..., gt=0, le=10000000, description="Цена за единицу (>0 и ≤ 10 000 000)")
    unit: Optional[str] = Field(None, description="Единица измерения (например: pcs, kg, lb, m, ft, l, gal)")
    total: Optional[float] = Field(None, description="Общая стоимость (автоматически рассчитывается)")

    def calculate_total(self):
        self.total = self.quantity * self.unit_price
        return self.total

class InvoiceTemplate(BaseModel):
    id: str = Field(..., description="ID шаблона")
    name: str = Field(..., description="Название шаблона")
    style: TemplateStyle = Field(..., description="Стиль шаблона")
    description: str = Field(..., description="Описание шаблона")
    preview_url: Optional[str] = Field(None, description="URL превью шаблона")
    is_premium: bool = Field(False, description="Премиум шаблон")
    # Настройки цветов таблиц (персистентные на уровне шаблона)
    table_header_fill: Optional[str] = Field(None, description="Цвет заливки заголовочных ячеек (HEX или rgba)")
    table_header_alpha: Optional[float] = Field(None, description="Прозрачность заголовочных ячеек (0.0–1.0)")
    table_cell_fill: Optional[str] = Field(None, description="Цвет заливки обычных ячеек (HEX или rgba)")
    table_cell_alpha: Optional[float] = Field(None, description="Прозрачность обычных ячеек (0.0–1.0)")
    table_border_color: Optional[str] = Field(None, description="Цвет границ таблицы (HEX или rgba)")
    table_border_alpha: Optional[float] = Field(None, description="Прозрачность границ таблицы (0.0–1.0)")

class InvoiceData(BaseModel):
    app_id: str = Field(..., description="ID приложения")
    user_id: str = Field(..., description="ID пользователя")
    template_id: str = Field(..., description="ID выбранного шаблона")
    
    # Информация об инвойсе
    invoice_number: str = Field(..., description="Номер инвойса")
    invoice_date: datetime = Field(default_factory=datetime.now, description="Дата инвойса")
    due_date: Optional[datetime] = Field(None, description="Дата оплаты")
    
    # Информация о компании и клиенте
    company: CompanyInfo = Field(..., description="Информация о компании")
    client: ClientInfo = Field(..., description="Информация о клиенте")
    
    # Товары/услуги
    items: List[InvoiceItem] = Field(..., min_items=1, description="Список товаров/услуг")
    
    # Финансовая информация
    subtotal: Optional[float] = Field(None, description="Подытог")
    tax_rate: Optional[float] = Field(0, ge=0, le=100, description="Налоговая ставка в процентах")
    tax_amount: Optional[float] = Field(None, description="Сумма налога")
    discount_rate: Optional[float] = Field(0, ge=0, le=100, description="Скидка в процентах")
    discount_amount: Optional[float] = Field(None, description="Сумма скидки")
    total_amount: Optional[float] = Field(None, description="Общая сумма")
    
    # Дополнительная информация
    notes: Optional[str] = Field(None, description="Примечания")
    terms: Optional[str] = Field(None, description="Условия оплаты")
    theme_color: Optional[str] = Field(None, description="Тематический цвет (HEX или rgb(r,g,b)) для акцентных элементов")
    # Настройки цветов таблицы (могут быть заданы шаблоном и/или пользователем)
    table_header_fill: Optional[str] = Field(None, description="Цвет заливки заголовочных ячеек (HEX или rgba)")
    table_header_alpha: Optional[float] = Field(None, description="Прозрачность заголовочных ячеек (0.0–1.0)")
    table_cell_fill: Optional[str] = Field(None, description="Цвет заливки обычных ячеек (HEX или rgba)")
    table_cell_alpha: Optional[float] = Field(None, description="Прозрачность обычных ячеек (0.0–1.0)")
    table_border_color: Optional[str] = Field(None, description="Цвет границ таблицы (HEX или rgba)")
    table_border_alpha: Optional[float] = Field(None, description="Прозрачность границ таблицы (0.0–1.0)")
    # Параметры для термочека
    currency: Optional[str] = Field(None, description="Валюта для цен (например: $, €, ₽, GBP, USD)")
    receipt_title: Optional[str] = Field(None, description="Заголовок чека (например: CHECK или RECEIPT)")
    paper_width_mm: Optional[int] = Field(None, description="Ширина бумаги для термопринтера в мм (57 или 80)")
    
    # Доп. поля для пользовательских шаблонов
    meta: Optional[Dict[str, Any]] = Field(None, description="Дополнительные произвольные поля для новых пользовательских шаблонов")
    
    def calculate_totals(self):
        """Автоматический расчет всех сумм"""
        # Рассчитываем общую стоимость каждого товара
        for item in self.items:
            item.calculate_total()
        
        # Подытог
        self.subtotal = sum(item.total for item in self.items)
        
        # Скидка
        if self.discount_rate and self.discount_rate > 0:
            self.discount_amount = self.subtotal * (self.discount_rate / 100)
        else:
            self.discount_amount = 0
        
        # Сумма после скидки
        amount_after_discount = self.subtotal - self.discount_amount
        
        # Налог
        if self.tax_rate and self.tax_rate > 0:
            self.tax_amount = amount_after_discount * (self.tax_rate / 100)
        else:
            self.tax_amount = 0
        
        # Итоговая сумма
        self.total_amount = amount_after_discount + self.tax_amount
        
        return self.total_amount

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "app_id": "contractor-app",
                "user_id": "user-123",
                "template_id": "modern-blue",
                "invoice_number": "INV-2024-001",
                "invoice_date": "2025-10-29T10:00:00",
                "due_date": "2025-11-05T10:00:00",
                "company": {
                    "name": "BuildCo LLC",
                    "address": "123 Main St, City",
                    "phone": "+1 555 0100",
                    "email": "info@buildco.example",
                    "website": "https://buildco.example",
                    "tax_id": "US-123456789",
                    "logo_url": "/uploads/logos/abcd-1234.png"
                },
                "client": {
                    "name": "ACME Corp",
                    "address": "456 Market Ave, City",
                    "phone": "+1 555 0200",
                    "email": "billing@acme.example"
                },
                "items": [
                    {"description": "Concrete work", "quantity": 10, "unit_price": 50, "unit": "m"},
                    {"description": "Rebar installation", "quantity": 5, "unit_price": 120, "unit": "pcs"}
                ],
                "tax_rate": 10,
                "discount_rate": 5,
                "notes": "Thank you for your business",
                "terms": "Payment due in 14 days"
            }
        })

class GenerationRequest(BaseModel):
    invoice_data: InvoiceData = Field(..., description="Данные для генерации инвойса")
    async_generation: bool = Field(False, description="Асинхронная генерация (для больших файлов)")

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "invoice_data": {
                    "app_id": "contractor-app",
                    "user_id": "user-123",
                    "template_id": "modern-blue",
                    "invoice_number": "INV-2024-001",
                    "invoice_date": "2025-10-29T10:00:00",
                    "due_date": "2025-11-05T10:00:00",
                    "company": {
                        "name": "BuildCo LLC",
                        "address": "123 Main St, City",
                        "phone": "+1 555 0100",
                        "email": "info@buildco.example",
                        "website": "https://buildco.example",
                        "tax_id": "US-123456789",
                        "logo_url": "/uploads/logos/abcd-1234.png"
                    },
                    "client": {
                        "name": "ACME Corp",
                        "address": "456 Market Ave, City",
                        "phone": "+1 555 0200",
                        "email": "billing@acme.example"
                    },
                    "items": [
                        {"description": "Concrete work", "quantity": 10, "unit_price": 50},
                        {"description": "Rebar installation", "quantity": 5, "unit_price": 120}
                    ],
                    "tax_rate": 10,
                    "discount_rate": 5,
                    "notes": "Thank you for your business",
                    "terms": "Payment due in 14 days"
                },
                "async_generation": False
            }
        })

class GenerationResponse(BaseModel):
    generation_id: str = Field(..., description="ID генерации")
    status: InvoiceStatus = Field(..., description="Статус генерации")
    pdf_url: Optional[str] = Field(None, description="URL готового PDF файла")
    message: str = Field(..., description="Сообщение о статусе")

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "generation_id": "b2a5f5c6-1234-5678-90ab-ef1234567890",
                "status": "completed",
                "pdf_url": "/generated/invoice_INV-2024-001_20251029_120000.pdf",
                "message": "Инвойс успешно сгенерирован"
            }
        })

class StatusResponse(BaseModel):
    generation_id: str = Field(..., description="ID генерации")
    status: InvoiceStatus = Field(..., description="Текущий статус")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Прогресс в процентах")
    pdf_url: Optional[str] = Field(None, description="URL готового PDF файла")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    created_at: datetime = Field(..., description="Время создания")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "generation_id": "b2a5f5c6-1234-5678-90ab-ef1234567890",
                "status": "processing",
                "progress": 75,
                "pdf_url": None,
                "error_message": None,
                "created_at": "2025-10-29T10:00:00",
                "completed_at": None
            }
        })

class TemplatesResponse(BaseModel):
    app_id: str = Field(..., description="ID приложения")
    user_id: str = Field(..., description="ID пользователя")
    templates: List[InvoiceTemplate] = Field(..., description="Список доступных шаблонов")
