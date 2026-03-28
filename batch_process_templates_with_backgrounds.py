#!/usr/bin/env python3
"""
Пакетная обработка: для каждого шаблона применить каждый доступный фон
и сохранить результат как отдельный PDF в папку `testInvoce4v`.

Требования:
- Поддержка исходного разрешения страниц шаблона
- Наложение фона без искажений (моделируется COVER-масштабированием)
- Понятное именование файлов: invoice_<templateId>_<backgroundId|basename>_<timestamp>.pdf
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional

from models import TemplateStyle
from pdf_generator import PDFGenerator
from template_service import template_service
from background_service import list_backgrounds
from test_custom_invoice import generate_random_invoice_data


OUTPUT_DIR = os.path.join(os.getcwd(), "testInvoce4v")
SOURCE_IMAGES_DIR = os.path.join(os.getcwd(), "invoice backfon")
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".jfif"}


def _sanitize(s: str) -> str:
    return ''.join(c for c in s if c.isalnum() or c in ('-', '_')).strip()


def _list_source_images(directory: str) -> List[str]:
    paths = []
    if not os.path.isdir(directory):
        return paths
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext in SUPPORTED_EXTS:
            paths.append(path)
    return sorted(paths)


def _load_templates() -> List[Dict]:
    # Используем template_service для актуального списка шаблонов
    templates: List[Dict] = []
    for t in template_service.templates_cache.values():
        templates.append(t)
    return templates


async def _generate_for_combo(pdf: PDFGenerator, template: Dict, bg: Dict) -> Optional[str]:
    # Подготовка данных инвойса
    data = generate_random_invoice_data()
    # Устанавливаем текущий шаблон
    data.template_id = template.get('id')

    # Переносим настройки цветов таблицы из шаблона (если есть)
    for key in (
        'table_header_fill', 'table_header_alpha',
        'table_cell_fill', 'table_cell_alpha',
        'table_border_color', 'table_border_alpha',
    ):
        if template.get(key) is not None:
            setattr(data, key, template.get(key))

    # Устанавливаем фон по id (если из БД), иначе по пути
    meta = dict(data.meta or {})
    if 'id' in bg and bg.get('stored_path'):
        meta['background_id'] = str(bg['id'])
    elif 'path' in bg:
        meta['background_image'] = bg['path']
    data.meta = meta

    # Стиль шаблона
    style_value = template.get('style')
    try:
        style = TemplateStyle(style_value)
    except Exception:
        # Фолбэк — modern
        style = TemplateStyle.MODERN

    # Генерация PDF
    out_path_tmp = await pdf.generate_invoice_pdf(data, template_style=style)

    # Формируем итоговое имя
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bg_part = str(bg.get('id') or os.path.splitext(os.path.basename(bg.get('path', 'bg')))[0])
    out_name = f"invoice_{_sanitize(template.get('id', 'template'))}_{_sanitize(bg_part)}_{ts}.pdf"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    # Переносим файл
    try:
        os.replace(out_path_tmp, out_path)
    except Exception:
        import shutil
        shutil.copy2(out_path_tmp, out_path)
    return out_path


async def main():
    print("🚀 Пакетная обработка шаблонов с фонами...")
    pdf = PDFGenerator()

    # Шаблоны
    templates = _load_templates()
    if not templates:
        raise RuntimeError("Не найдены шаблоны (templates.json пуст) — проверьте админку.")
    print(f"📄 Шаблонов: {len(templates)}")

    # Фоны из БД (uploads/backgrounds)
    db_backgrounds = list_backgrounds()
    source_images = _list_source_images(SOURCE_IMAGES_DIR)

    # Собираем унифицированный список фонов
    backgrounds: List[Dict] = []
    if db_backgrounds:
        for b in db_backgrounds:
            if b.get('stored_path') and os.path.exists(b['stored_path']):
                backgrounds.append({
                    'id': b['id'],
                    'stored_path': b['stored_path'],
                })
    elif source_images:
        for p in source_images:
            backgrounds.append({'path': p})

    if not backgrounds:
        raise RuntimeError("Не найдены доступные фоны: ни в БД, ни в папке 'invoice backfon'.")
    print(f"🖼️ Фонов: {len(backgrounds)}")

    total = 0
    ok = 0
    for ti, t in enumerate(templates, 1):
        print(f"\n[{ti}/{len(templates)}] Шаблон: {t.get('id')} ({t.get('style')})")
        for bi, b in enumerate(backgrounds, 1):
            total += 1
            label = str(b.get('id') or os.path.basename(b.get('path', 'bg')))
            print(f"  [{bi}/{len(backgrounds)}] Фон: {label}")
            try:
                out = await _generate_for_combo(pdf, t, b)
                size = os.path.getsize(out)
                print(f"     ✅ {out} (Размер: {size} байт)")
                ok += 1
            except Exception as e:
                print(f"     ❌ Ошибка: {e}")

    print(f"\n🎉 Готово. Успешных файлов: {ok} из {total}")
    print(f"Папка результата: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())

