from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import os
import json
from datetime import datetime
import asyncio
import shutil
import logging
from logging.handlers import RotatingFileHandler

# Импорты моделей и сервисов
from models import (
    InvoiceData, GenerationRequest, GenerationResponse, StatusResponse, 
    TemplatesResponse, InvoiceStatus, TemplateStyle
)
from pdf_generator import PDFGenerator
from template_service import template_service
from background_service import list_backgrounds, get_background, delete_background, add_from_path
from admin import router as admin_router
from background_service import ensure_monitor_loop, scan_source_dir

app = FastAPI(
    title="Invoice Maker for Contractors API",
    description="API для генерации инвойсов с готовыми шаблонами",
    version="1.0.0"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generated", StaticFiles(directory="generated_invoices"), name="generated")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Создание необходимых директорий
os.makedirs("templates", exist_ok=True)
os.makedirs("generated_invoices", exist_ok=True)
os.makedirs("uploads/logos", exist_ok=True)
os.makedirs("static/previews", exist_ok=True)
os.makedirs(os.path.join("uploads", "backgrounds"), exist_ok=True)

# Логи
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("invoice_app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    _console = logging.StreamHandler()
    _console.setFormatter(_formatter)
    _file = RotatingFileHandler(os.path.join("logs", "app.log"), maxBytes=1048576, backupCount=3, encoding="utf-8")
    _file.setFormatter(_formatter)
    logger.addHandler(_console)
    logger.addHandler(_file)

# Хранилище для статусов генерации (в продакшене использовать Redis)
generation_status = {}

# Инициализация PDF генератора
pdf_generator = PDFGenerator()

# Подключение админ-роутера
app.include_router(admin_router)

@app.get("/")
async def root():
    return {
        "message": "Invoice Maker for Contractors API",
        "version": "1.0.0",
        "endpoints": {
            "templates": "GET /templates?app_id={app_id}&user_id={user_id}",
            "generate": "POST /generate",
            "status": "GET /status/{generation_id}",
            "upload_logo": "POST /upload-logo"
        }
    }

@app.on_event("startup")
async def startup_monitor_backgrounds():
    """
    На старте приложения запускаем фоновый мониторинг каталога с фонами
    и выполняем первичное сканирование для импорта новых изображений.
    Требование: обнаружение новых фонов в течение 5 минут.
    """
    try:
        # Первичный скан источника, чтобы сразу подтянуть существующие файлы
        scan_source_dir()
        # Запускаем периодический мониторинг, интервал 300 секунд (5 минут)
        ensure_monitor_loop(loop_seconds=300)
    except Exception as e:
        # Не блокируем запуск приложения, просто логируем
        print(f"Startup background monitor init error: {e}")

@app.get(
    "/templates",
    response_model=TemplatesResponse,
    tags=["Templates"],
    summary="Получить доступные шаблоны",
    description="Возвращает список шаблонов, доступных пользователю на основании app_id и user_id",
    responses={
        200: {
            "description": "Список доступных шаблонов",
            "content": {
                "application/json": {
                    "example": {
                        "app_id": "contractor-app",
                        "user_id": "user-123",
                        "templates": [
                            {
                                "id": "modern-blue",
                                "name": "Modern Blue",
                                "style": "modern",
                                "description": "Современный синий шаблон",
                                "preview_url": "/static/previews/modern-blue.png",
                                "is_premium": False
                            }
                        ]
                    }
                }
            }
        },
        500: {"description": "Ошибка получения шаблонов"}
    }
)
async def get_templates(
    app_id: str = Query(..., description="ID приложения"),
    user_id: str = Query(..., description="ID пользователя")
):
    """
    Получение всех доступных шаблонов для пользователя
    
    Включает в себя app_id, user_id и возвращает список доступных оформлений для инвойсов
    """
    try:
        # Получаем шаблоны для пользователя
        templates = template_service.get_templates_for_user(app_id, user_id)
        
        return TemplatesResponse(
            app_id=app_id,
            user_id=user_id,
            templates=templates
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения шаблонов: {str(e)}")

@app.post(
    "/generate",
    response_model=GenerationResponse,
    tags=["Invoices"],
    summary="Сгенерировать инвойс (синхронно/асинхронно)",
    description="Принимает данные инвойса и генерирует PDF. В синхронном режиме сразу возвращает ссылку на PDF; в асинхронном режиме возвращает ID генерации.",
    responses={
        200: {
            "description": "Успешная генерация (синхронно) или запуск (асинхронно)",
            "content": {
                "application/json": {
                    "examples": {
                        "sync": {
                            "summary": "Синхронная генерация",
                            "value": {
                                "generation_id": "b2a5...",
                                "status": "completed",
                                "pdf_url": "/generated/invoice_INV-2024-001_20250101_120000.pdf",
                                "message": "Инвойс успешно сгенерирован"
                            }
                        },
                        "async": {
                            "summary": "Асинхронная генерация",
                            "value": {
                                "generation_id": "b2a5...",
                                "status": "processing",
                                "pdf_url": None,
                                "message": "Генерация запущена. Используйте /status/{generation_id} для проверки статуса"
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "Шаблон не найден"},
        500: {"description": "Ошибка генерации PDF"}
    }
)
async def generate_invoice(
    request: GenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Генерация инвойса
    
    Включает в себя всю информацию по товарам, ценах, компании, контакты + лого компании
    Возвращает ID генерации или сразу готовый PDF файл
    """
    try:
        logger.info("POST /generate started async=%s template_id=%s", request.async_generation, request.invoice_data.template_id)
        # Проверяем существование шаблона
        template = template_service.get_template_by_id(request.invoice_data.template_id)
        if not template:
            logger.warning("Template not found id=%s", request.invoice_data.template_id)
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        # Генерируем уникальный ID для генерации
        generation_id = str(uuid.uuid4())
        logger.info("Generation created id=%s", generation_id)
        
        # Получаем стиль шаблона
        template_style = template_service.get_template_style_by_id(request.invoice_data.template_id)
        # Инъекция настроек цветов таблицы из шаблона в данные инвойса
        if template:
            # Значения из шаблона, если присутствуют
            thf = getattr(template, 'table_header_fill', None)
            tha = getattr(template, 'table_header_alpha', None)
            tcf = getattr(template, 'table_cell_fill', None)
            tca = getattr(template, 'table_cell_alpha', None)
            tbc = getattr(template, 'table_border_color', None)
            tba = getattr(template, 'table_border_alpha', None)

            # Устанавливаем в request.invoice_data, не перезаписывая уже переданные клиентом значения
            if request.invoice_data.table_header_fill is None:
                request.invoice_data.table_header_fill = thf
            if request.invoice_data.table_header_alpha is None:
                request.invoice_data.table_header_alpha = tha if tha is not None else 0.85
            if request.invoice_data.table_cell_fill is None:
                request.invoice_data.table_cell_fill = tcf
            if request.invoice_data.table_cell_alpha is None:
                request.invoice_data.table_cell_alpha = tca if tca is not None else 0.75
            if request.invoice_data.table_border_color is None:
                request.invoice_data.table_border_color = tbc
            if request.invoice_data.table_border_alpha is None:
                request.invoice_data.table_border_alpha = tba if tba is not None else 0.50
        
        if request.async_generation:
            # Асинхронная генерация для больших файлов
            generation_status[generation_id] = {
                "status": InvoiceStatus.PROCESSING,
                "progress": 0,
                "created_at": datetime.now(),
                "pdf_url": None,
                "error_message": None
            }
            
            # Запускаем генерацию в фоне
            logger.info("Queue background PDF generation id=%s", generation_id)
            background_tasks.add_task(
                generate_pdf_async, 
                generation_id, 
                request.invoice_data, 
                template_style
            )
            
            return GenerationResponse(
                generation_id=generation_id,
                status=InvoiceStatus.PROCESSING,
                message="Генерация запущена. Используйте /status/{generation_id} для проверки статуса"
            )
        else:
            # Синхронная генерация
            generation_status[generation_id] = {
                "status": InvoiceStatus.PROCESSING,
                "progress": 50,
                "created_at": datetime.now(),
                "pdf_url": None,
                "error_message": None
            }
            
            try:
                # Генерируем PDF
                logger.info("Start sync PDF generation id=%s", generation_id)
                pdf_path = await pdf_generator.generate_invoice_pdf(
                    request.invoice_data, 
                    template_style
                )
                
                # Создаем URL для доступа к файлу
                pdf_filename = os.path.basename(pdf_path)
                pdf_url = f"/generated/{pdf_filename}"
                
                # Обновляем статус
                generation_status[generation_id].update({
                    "status": InvoiceStatus.COMPLETED,
                    "progress": 100,
                    "pdf_url": pdf_url,
                    "completed_at": datetime.now()
                })
                logger.info("Sync PDF completed id=%s url=%s", generation_id, pdf_url)
                
                return GenerationResponse(
                    generation_id=generation_id,
                    status=InvoiceStatus.COMPLETED,
                    pdf_url=pdf_url,
                    message="Инвойс успешно сгенерирован"
                )
                
            except Exception as e:
                logger.exception("Sync PDF generation failed id=%s error=%s", generation_id, str(e))
                generation_status[generation_id].update({
                    "status": InvoiceStatus.FAILED,
                    "error_message": str(e)
                })
                raise HTTPException(status_code=500, detail=f"Ошибка генерации PDF: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Invoice generation failed error=%s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка генерации инвойса: {str(e)}")

@app.get(
    "/status/{generation_id}",
    response_model=StatusResponse,
    tags=["Invoices"],
    summary="Проверить статус генерации",
    description="Возвращает текущий статус генерации по ID, включая прогресс и ссылку на PDF (если готов)",
    responses={
        200: {
            "description": "Текущий статус генерации",
            "content": {
                "application/json": {
                    "example": {
                        "generation_id": "b2a5...",
                        "status": "completed",
                        "progress": 100,
                        "pdf_url": "/generated/invoice_INV-2024-001_20250101_120000.pdf",
                        "error_message": None,
                        "created_at": "2025-01-01T11:59:55",
                        "completed_at": "2025-01-01T12:00:05"
                    }
                }
            }
        },
        404: {"description": "ID генерации не найден"}
    }
)
async def get_generation_status(generation_id: str):
    """
    Проверка статуса генерации
    
    Включает в себя ID генерации, получаемое с метода генерации
    Возвращает статус + ссылку/PDF (опционально)
    """
    if generation_id not in generation_status:
        logger.warning("Status requested for unknown id=%s", generation_id)
        raise HTTPException(status_code=404, detail="ID генерации не найден")
    
    status_data = generation_status[generation_id]
    logger.info("Status requested id=%s status=%s progress=%s", generation_id, status_data.get("status"), status_data.get("progress"))
    
    return StatusResponse(
        generation_id=generation_id,
        status=status_data["status"],
        progress=status_data.get("progress"),
        pdf_url=status_data.get("pdf_url"),
        error_message=status_data.get("error_message"),
        created_at=status_data["created_at"],
        completed_at=status_data.get("completed_at")
    )

@app.post(
    "/upload-logo",
    tags=["Uploads"],
    summary="Загрузить логотип компании",
    description="Принимает файл изображения логотипа и возвращает публичный URL для доступа",
    responses={
        200: {
            "description": "Логотип успешно загружен",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Логотип успешно загружен",
                        "logo_url": "/uploads/logos/123e4567-e89b-12d3-a456-426614174000.png",
                        "filename": "123e4567-e89b-12d3-a456-426614174000.png"
                    }
                }
            }
        },
        400: {"description": "Файл не является изображением"},
        500: {"description": "Ошибка загрузки файла"}
    }
)
async def upload_logo(file: UploadFile = File(...)):
    """
    Загрузка логотипа компании
    """
    try:
        logger.info("POST /upload-logo started content_type=%s filename=%s", getattr(file, "content_type", None), getattr(file, "filename", None))
        # Проверяем тип файла
        if not file.content_type.startswith('image/'):
            logger.warning("Upload rejected: non-image content_type=%s", file.content_type)
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        # Генерируем уникальное имя файла
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join("uploads/logos", unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Возвращаем URL файла (раздается через /uploads)
        logo_url = f"/uploads/logos/{unique_filename}"
        logger.info("Logo uploaded filename=%s path=%s url=%s", unique_filename, file_path, logo_url)
        
        return {
            "message": "Логотип успешно загружен",
            "logo_url": logo_url,
            "url": logo_url,
            "filename": unique_filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Logo upload failed error=%s", str(e))
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")
    except HTTPException:
        # Пробрасываем преднамеренные HTTP ошибки (например, 400)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")

# ------------------------- Backgrounds API -------------------------

@app.get(
    "/backgrounds",
    tags=["Backgrounds"],
    summary="Список фоновых изображений",
    description="Возвращает список импортированных фоновых изображений с метаданными",
    responses={
        200: {
            "description": "Успешное получение списка фонов",
            "content": {
                "application/json": {
                    "example": {
                        "backgrounds": [
                            {
                                "id": "021a38f006fcafbd37cb7c3f01e1d4b8",
                                "filename": "background-01.jpg",
                                "size_bytes": 345672,
                                "stored_path": "uploads/backgrounds/background-01.jpg",
                                "source_path": "invoice backfon/background-01.jpg",
                                "content_type": "image/jpeg",
                                "created_at": "2025-11-03T20:13:15",
                                "deleted": False,
                                "url": "/uploads/backgrounds/background-01.jpg"
                            }
                        ]
                    }
                }
            }
        },
        500: {"description": "Ошибка получения списка фонов"}
    }
)
async def backgrounds_list():
    items = list_backgrounds()
    # Добавляем удобный URL для превью
    for it in items:
        try:
            basename = os.path.basename(it.get("stored_path", ""))
            it["url"] = f"/uploads/backgrounds/{basename}" if basename else None
        except Exception:
            it["url"] = None
    return {"backgrounds": items}

@app.get(
    "/backgrounds/{bg_id}",
    tags=["Backgrounds"],
    summary="Детали фонового изображения",
    responses={
        200: {
            "description": "Успешное получение метаданных фона",
            "content": {
                "application/json": {
                    "example": {
                        "id": "021a38f006fcafbd37cb7c3f01e1d4b8",
                        "filename": "background-01.jpg",
                        "size_bytes": 345672,
                        "stored_path": "uploads/backgrounds/background-01.jpg",
                        "source_path": "invoice backfon/background-01.jpg",
                        "content_type": "image/jpeg",
                        "created_at": "2025-11-03T20:13:15",
                        "deleted": False,
                        "url": "/uploads/backgrounds/background-01.jpg"
                    }
                }
            }
        },
        404: {"description": "Фон не найден"},
        500: {"description": "Ошибка получения данных фона"}
    }
)
async def backgrounds_get(bg_id: str):
    data = get_background(bg_id)
    if not data:
        raise HTTPException(status_code=404, detail="Фон не найден")
    basename = os.path.basename(data.get("stored_path", ""))
    data["url"] = f"/uploads/backgrounds/{basename}" if basename else None
    return data

@app.delete(
    "/backgrounds/{bg_id}",
    tags=["Backgrounds"],
    summary="Пометить фон как удалённый",
    responses={
        200: {
            "description": "Фон помечен как удалённый",
            "content": {
                "application/json": {
                    "example": {"message": "Фон помечен как удалённый", "id": "021a38f006fcafbd37cb7c3f01e1d4b8"}
                }
            }
        },
        404: {"description": "Фон не найден"},
        500: {"description": "Ошибка удаления фона"}
    }
)
async def backgrounds_delete(bg_id: str):
    ok = delete_background(bg_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Фон не найден")
    return {"message": "Фон помечен как удалённый", "id": bg_id}

@app.post(
    "/backgrounds/upload",
    tags=["Backgrounds"],
    summary="Загрузить новое фоновое изображение",
    description="Принимает PNG/JPG, регистрирует его и возвращает уникальный id и URL",
    responses={
        200: {
            "description": "Фон успешно загружен",
            "content": {
                "application/json": {
                    "example": {"id": "021a38f006fcafbd37cb7c3f01e1d4b8", "url": "/uploads/backgrounds/background-01.jpg"}
                }
            }
        },
        400: {"description": "Поддерживаются только PNG/JPG"},
        500: {"description": "Не удалось импортировать файл"}
    }
)
async def backgrounds_upload(file: UploadFile = File(...)):
    if file.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="Поддерживаются только PNG/JPG")

    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    tmp_path = os.path.join("uploads", "backgrounds", f"tmp_{uuid.uuid4()}{ext}")
    with open(tmp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        bg_id = add_from_path(tmp_path)
        if not bg_id:
            raise HTTPException(status_code=500, detail="Не удалось импортировать файл")
        # Получаем данные и URL
        data = get_background(bg_id) or {}
        basename = os.path.basename(data.get("stored_path", ""))
        url = f"/uploads/backgrounds/{basename}" if basename else None
        return {"id": bg_id, "url": url}
    finally:
        # удаляем временный файл
        try:
            os.remove(tmp_path)
        except Exception:
            pass

@app.post(
    "/backgrounds/scan",
    tags=["Backgrounds"],
    summary="Запустить сканирование источника фонов",
    description="Сканирует исходную папку и импортирует новые изображения",
    responses={
        200: {
            "description": "Сканирование выполнено",
            "content": {
                "application/json": {"example": {"added_or_found": 42}}
            }
        },
        500: {"description": "Ошибка сканирования"}
    }
)
async def backgrounds_scan():
    try:
        added = scan_source_dir()
        return {"added_or_found": added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сканирования: {str(e)}")

@app.get(
    "/templates/styles",
    tags=["Templates"],
    summary="Получить доступные стили шаблонов",
    description="Возвращает список поддерживаемых стилей и краткие описания",
    responses={
        200: {
            "description": "Список стилей",
            "content": {
                "application/json": {
                    "example": {
                        "styles": [
                            "modern", "classic", "minimal", "corporate", "thermal",
                            "it_pro", "medical_pro", "construction_pro", "creative_pro", "legal_pro"
                        ],
                        "descriptions": {
                            "modern": "Современный дизайн с чистыми линиями",
                            "classic": "Классический элегантный стиль",
                            "minimal": "Минималистичный дизайн",
                            "corporate": "Корпоративный профессиональный стиль",
                            "thermal": "Чек для термопринтера (узкий формат 80мм)",
                            "it_pro": "IT/консалтинг: лаконичный техно-стиль, проектные блоки",
                            "medical_pro": "Медицина: чистые карточки, коды услуг, страховые поля",
                            "construction_pro": "Строительство: акцентные секции, объект/смета, этапы работ",
                            "creative_pro": "Креатив: выразительная типографика, акценты, портфолио",
                            "legal_pro": "Юридический: строгая верстка, номер дела, контекст договора"
                        }
                    }
                }
            }
        }
    }
)
async def get_template_styles():
    """Получение доступных стилей шаблонов"""
    return {
        "styles": [style.value for style in TemplateStyle],
        "descriptions": {
            "modern": "Современный дизайн с чистыми линиями",
            "classic": "Классический элегантный стиль",
            "minimal": "Минималистичный дизайн",
            "corporate": "Корпоративный профессиональный стиль",
            "thermal": "Чек для термопринтера (узкий формат 80мм)",
            "it_pro": "IT/консалтинг: лаконичный техно-стиль, проектные блоки",
            "medical_pro": "Медицина: чистые карточки, коды услуг, страховые поля",
            "construction_pro": "Строительство: акцентные секции, объект/смета, этапы работ",
            "creative_pro": "Креатив: выразительная типографика, акценты, портфолио",
            "legal_pro": "Юридический: строгая верстка, номер дела, контекст договора"
        }
    }

@app.get(
    "/templates/free",
    tags=["Templates"],
    summary="Получить бесплатные шаблоны",
    description="Возвращает список шаблонов, доступных бесплатно",
    responses={
        200: {
            "description": "Список бесплатных шаблонов",
            "content": {
                "application/json": {
                    "example": {
                        "templates": [
                            {
                                "id": "modern-blue",
                                "name": "Modern Blue",
                                "style": "modern",
                                "description": "Современный синий шаблон",
                                "preview_url": "/static/previews/modern-blue.png",
                                "is_premium": False
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_free_templates():
    """Получение бесплатных шаблонов"""
    templates = template_service.get_free_templates()
    return {"templates": templates}

@app.get(
    "/templates/premium",
    tags=["Templates"],
    summary="Получить премиум шаблоны",
    description="Возвращает список премиум шаблонов (требуется доступ)",
    responses={
        200: {
            "description": "Список премиум шаблонов",
            "content": {
                "application/json": {
                    "example": {
                        "templates": [
                            {
                                "id": "corporate-pro",
                                "name": "Corporate Pro",
                                "style": "corporate",
                                "description": "Профессиональный корпоративный шаблон",
                                "preview_url": "/static/previews/corporate-pro.png",
                                "is_premium": True
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_premium_templates():
    """Получение премиум шаблонов"""
    templates = template_service.get_premium_templates()
    return {"templates": templates}

async def generate_pdf_async(generation_id: str, invoice_data: InvoiceData, template_style: TemplateStyle):
    """Асинхронная генерация PDF"""
    try:
        # Обновляем прогресс
        generation_status[generation_id]["progress"] = 25
        
        # Генерируем PDF
        pdf_path = await pdf_generator.generate_invoice_pdf(invoice_data, template_style)
        
        # Обновляем прогресс
        generation_status[generation_id]["progress"] = 75
        
        # Создаем URL для доступа к файлу
        pdf_filename = os.path.basename(pdf_path)
        pdf_url = f"/generated/{pdf_filename}"
        
        # Завершаем генерацию
        generation_status[generation_id].update({
            "status": InvoiceStatus.COMPLETED,
            "progress": 100,
            "pdf_url": pdf_url,
            "completed_at": datetime.now()
        })
        
    except Exception as e:
        generation_status[generation_id].update({
            "status": InvoiceStatus.FAILED,
            "error_message": str(e),
            "completed_at": datetime.now()
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)
