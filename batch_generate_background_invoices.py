#!/usr/bin/env python3
"""
Пакетная генерация тестовых инвойсов: для каждого изображения из
папки `invoice backfon` создается PDF с этим изображением в качестве
фона (полный охват листа без полей, сохранение пропорций).

Выходные файлы сохраняются в `testinvoice3.0` с именами,
соответствующими исходным изображениям.
"""

import os
import re
import asyncio
from datetime import datetime
from typing import List

from models import TemplateStyle
from pdf_generator import PDFGenerator
from test_custom_invoice import generate_random_invoice_data


INPUT_DIR = os.path.join(os.getcwd(), "invoice backfon")
OUTPUT_DIR = os.path.join(os.getcwd(), "testinvoice3.0")


SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".jfif"}


def list_images(directory: str) -> List[str]:
    files = []
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext in SUPPORTED_EXTS:
            files.append(path)
    return sorted(files)


def sanitize_basename(name: str) -> str:
    base = os.path.splitext(os.path.basename(name))[0]
    # Заменяем все, кроме букв/цифр/дефиса/нижнего подчеркивания
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", base)
    return base.strip("_") or "image"


async def generate_for_image(image_path: str, pdf: PDFGenerator) -> str:
    # Генерируем базовые данные инвойса
    data = generate_random_invoice_data()
    # Указываем фон на текущее изображение
    meta = dict(data.meta or {})
    meta["background_image"] = image_path
    data.meta = meta

    # Генерируем PDF
    filepath = await pdf.generate_invoice_pdf(data, template_style=TemplateStyle.CUSTOM)

    # Формируем итоговое имя и копируем
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base = sanitize_basename(image_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"invoice_{base}_{ts}.pdf"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    # Перекладываем файл (rename/copy)
    try:
        # Пытаемся сначала переименовать (быстрее), если каталоги на одном диске
        os.replace(filepath, out_path)
    except Exception:
        import shutil
        shutil.copy2(filepath, out_path)
    return out_path


async def main():
    print("🧪 Пакетная генерация инвойсов по изображениям фона...")
    if not os.path.isdir(INPUT_DIR):
        raise RuntimeError(f"Папка не найдена: {INPUT_DIR}")

    images = list_images(INPUT_DIR)
    if not images:
        raise RuntimeError("В папке нет поддерживаемых изображений (.png/.jpg/.jpeg/.jfif)")

    print(f"📷 Найдено изображений: {len(images)}")
    pdf = PDFGenerator()

    generated = []
    for idx, img in enumerate(images, 1):
        print(f"[{idx}/{len(images)}] Фон: {os.path.basename(img)}")
        try:
            out = await generate_for_image(img, pdf)
            size = os.path.getsize(out)
            print(f"   ✅ Сохранено: {out} (Размер: {size} байт)")
            generated.append(out)
        except Exception as e:
            print(f"   ❌ Ошибка для {img}: {e}")

    print("\n🎉 Готово. Сгенерировано файлов:", len(generated))
    print("Папка результата:", OUTPUT_DIR)


if __name__ == "__main__":
    asyncio.run(main())

