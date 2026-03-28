import os
import io
import urllib.request
from datetime import datetime
from typing import Optional, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from models import InvoiceData, TemplateStyle
from background_service import resolve_path as resolve_background_path

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Настройка пользовательских стилей"""
        # Стиль для заголовка
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # Стиль для подзаголовков
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#34495e')
        )
        
        # Стиль для обычного текста
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Стиль для итогов
        self.total_style = ParagraphStyle(
            'CustomTotal',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )

    async def generate_invoice_pdf(self, invoice_data: InvoiceData, template_style: TemplateStyle = TemplateStyle.MODERN) -> str:
        """Генерация PDF инвойса"""
        # Рассчитываем все суммы
        invoice_data.calculate_totals()
        
        # Создаем уникальное имя файла
        filename = f"invoice_{invoice_data.invoice_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join("generated_invoices", filename)
        
        # Создаем PDF документ
        # Выбор формата страницы под стиль
        if template_style == TemplateStyle.THERMAL:
            # Ширина 57/80 мм, высота динамическая
            requested_w = getattr(invoice_data, 'paper_width_mm', None)
            w_mm = 80 if requested_w is None else (57 if requested_w <= 57 else 80)
            base_h_mm = 140
            per_item_mm = 10
            height_mm = base_h_mm + max(0, len(invoice_data.items)) * per_item_mm
            pagesize = (w_mm*mm, height_mm*mm)
            margins = {
                'rightMargin': 5*mm,
                'leftMargin': 5*mm,
                'topMargin': 8*mm,
                'bottomMargin': 8*mm
            }
        else:
            pagesize = A4
            margins = {
                'rightMargin': 2*cm,
                'leftMargin': 2*cm,
                'topMargin': 2*cm,
                'bottomMargin': 2*cm
            }

        doc = SimpleDocTemplate(
            filepath,
            pagesize=pagesize,
            **margins
        )
        
        # Создаем содержимое в зависимости от стиля
        if template_style == TemplateStyle.MODERN:
            story = self._create_modern_template(invoice_data)
        elif template_style == TemplateStyle.CLASSIC:
            story = self._create_classic_template(invoice_data)
        elif template_style == TemplateStyle.MINIMAL:
            story = self._create_minimal_template(invoice_data)
        elif template_style == TemplateStyle.THERMAL:
            story = self._create_thermal_template(invoice_data)
        elif template_style == TemplateStyle.CUSTOM:
            story = self._create_custom_template(invoice_data)
        elif template_style == TemplateStyle.IT_PRO:
            story = self._create_it_pro_template(invoice_data)
        elif template_style == TemplateStyle.MEDICAL_PRO:
            story = self._create_medical_pro_template(invoice_data)
        elif template_style == TemplateStyle.CONSTRUCTION_PRO:
            story = self._create_construction_pro_template(invoice_data)
        elif template_style == TemplateStyle.CREATIVE_PRO:
            story = self._create_creative_pro_template(invoice_data)
        elif template_style == TemplateStyle.LEGAL_PRO:
            story = self._create_legal_pro_template(invoice_data)
        else:  # CORPORATE
            story = self._create_corporate_template(invoice_data)
        
        # Генерация PDF с возможным фоном для ЛЮБОГО стиля
        bg_path = None
        try:
            # Путь можно передать через meta.background_image
            meta = getattr(invoice_data, 'meta', None) or {}
            bg_path = meta.get('background_image')
            # Либо meta.background_id (приоритетнее)
            bg_id = meta.get('background_id')
            if bg_id:
                resolved = resolve_background_path(str(bg_id))
                if resolved and os.path.exists(resolved):
                    bg_path = resolved
            # Если путь не задан, пробуем дефолтные варианты только для custom
            if not bg_path and template_style == TemplateStyle.CUSTOM:
                candidates = [
                    os.path.join(os.getcwd(), 'Gemini_Generated_Image_kdnypbkdnypbkdny.png'),
                    os.path.join(os.getcwd(), 'static', 'previews', 'custom-background.png'),
                ]
                for p in candidates:
                    if os.path.exists(p):
                        bg_path = p
                        break
        except Exception:
            bg_path = None

        def _draw_background(canv, doc_obj):
            if not bg_path or not os.path.exists(bg_path):
                return
            try:
                canv.saveState()
                page_w, page_h = doc_obj.pagesize
                # Автоопределение размеров изображения
                img = ImageReader(bg_path)
                img_w, img_h = img.getSize()  # в пикселях, пропорции корректны
                # Масштаб по принципу COVER: без искажений, полный охват страницы
                scale = max(page_w / img_w, page_h / img_h)
                draw_w = img_w * scale
                draw_h = img_h * scale
                # Центрируем изображение; лишнее обрежется рамками страницы
                x = (page_w - draw_w) / 2
                y = (page_h - draw_h) / 2
                canv.drawImage(bg_path, x, y, width=draw_w, height=draw_h, preserveAspectRatio=False, mask='auto')
                canv.restoreState()
            except Exception:
                # Если фон не удалось нарисовать — продолжаем без него
                pass

        if bg_path:
            doc.build(story, onFirstPage=_draw_background, onLaterPages=_draw_background)
        else:
            doc.build(story)
        
        return filepath

    def _create_thermal_template(self, invoice_data: InvoiceData) -> list:
        """Узкий шаблон чека для термопринтера (80мм)"""
        story = []
        # Параметры
        title_text = (getattr(invoice_data, 'receipt_title', None) or 'CHECK').upper()
        currency_raw = getattr(invoice_data, 'currency', None)
        currency = self._resolve_currency_symbol(currency_raw)
        # Логотип (если есть) — компактный, по центру
        try:
            content_w_mm = (getattr(invoice_data, 'paper_width_mm', None) or 80) - 10
            # делаем логотип примерно в 2 раза меньше ширины контента
            logo_max_w_mm = content_w_mm / 2
            logo_flow = self._load_logo_image(
                invoice_data.company,
                max_width_pt=logo_max_w_mm * mm,
                max_height_pt=logo_max_w_mm * mm,
            )
            if logo_flow:
                logo_flow.hAlign = 'CENTER'
                story.append(logo_flow)
                story.append(Spacer(1, 4*mm))
        except Exception:
            pass
        # Заголовок
        title_style = ParagraphStyle(
            'ThermalTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            spaceAfter=6
        )
        story.append(Paragraph(title_text, title_style))

        # Верхняя строка: CASH RECEIPT | Date/Time
        header_style = ParagraphStyle(
            'ThermalHeader', parent=self.styles['Normal'], fontSize=9, textColor=colors.black
        )
        left = Paragraph(title_text if title_text else 'CASH RECEIPT', header_style)
        right = Paragraph(f"Date: {invoice_data.invoice_date.strftime('%d/%m/%Y')}<br/>Time: {invoice_data.invoice_date.strftime('%H:%M')}", header_style)
        # Колонки адаптивно под ширину
        content_w_mm = (getattr(invoice_data, 'paper_width_mm', None) or 80) - 10  # минус поля
        header_cols = [content_w_mm * 0.6 * mm, content_w_mm * 0.4 * mm]
        t = Table([[left, right]], colWidths=header_cols)
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t)

        # Разделитель
        story.append(Paragraph('.'.ljust(40, '.'), header_style))

        # Таблица позиций: 2 колонки: описание (с количеством и единицей) | цена
        data = []
        data.append(['', ''])  # заголовок пустой для ровных отступов
        for item in invoice_data.items:
            unit = getattr(item, 'unit', None) or ''
            qty = getattr(item, 'quantity', None)
            qty_part = f" × {qty:g} {unit}".strip() if qty is not None else ''
            desc = f"{item.description}{qty_part}".strip()
            data.append([desc, f"{item.total:.2f}{currency}"])
        items_cols = [content_w_mm * 0.65 * mm, content_w_mm * 0.35 * mm]
        items_table = Table(data, colWidths=items_cols)
        items_table.setStyle(TableStyle([
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,1), (0,-1), 'LEFT'),
            ('ALIGN', (1,1), (1,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(items_table)

        # Разделитель
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph('.'.ljust(40, '.'), header_style))

        # Итого
        total_style = ParagraphStyle('ThermalTotal', parent=self.styles['Normal'], fontSize=11, fontName='Helvetica-Bold')
        totals = Table([
            [Paragraph('TOTAL', total_style), Paragraph(f"{invoice_data.total_amount:.2f}{currency}", total_style)]
        ], colWidths=items_cols)
        totals.setStyle(TableStyle([
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(totals)

        return story

    def _create_it_pro_template(self, invoice_data: InvoiceData) -> list:
        """IT/Consulting: техно-стиль, акцент на проектах и часах"""
        story = []

        title_style = ParagraphStyle(
            'ITTitle', parent=self.styles['Heading1'], fontSize=22, alignment=TA_LEFT,
            textColor=self._parse_theme_color(getattr(invoice_data, 'theme_color', {'r':40,'g':120,'b':200})),
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("INVOICE — IT & Consulting", title_style))
        story.append(Spacer(1, 12))

        # Компания / Клиент
        cc_table = Table([[
            self._format_company_info(invoice_data.company),
            self._format_client_info(invoice_data.client)
        ]], colWidths=[8*cm, 8*cm])
        cc_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
        story.append(cc_table)
        story.append(Spacer(1, 10))

        # Информация по счету
        info = [
            ['Invoice #', invoice_data.invoice_number],
            ['Date', invoice_data.invoice_date.strftime('%Y-%m-%d')],
        ]
        if invoice_data.due_date:
            info.append(['Due', invoice_data.due_date.strftime('%Y-%m-%d')])
        info_table = Table(info, colWidths=[3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),10),('LEFTPADDING',(0,0),(-1,-1),0)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 10))

        # Таблица услуг
        items_table = self._create_items_table_with_settings(
            invoice_data.items,
            invoice_data,
            fallback_header_color=self._parse_theme_color(getattr(invoice_data, 'theme_color', {'r':40,'g':120,'b':200}))
        )
        story.append(items_table)
        story.append(Spacer(1, 12))

        totals_table = self._create_totals_table(invoice_data)
        story.append(totals_table)

        if invoice_data.notes:
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Project Summary: {invoice_data.notes}", self.normal_style))
        return story

    def _create_medical_pro_template(self, invoice_data: InvoiceData) -> list:
        """Медицинский: мягкие тона, коды услуг/страховка"""
        story = []
        accent = colors.HexColor('#1CA7A1')
        title_style = ParagraphStyle('MedTitle', parent=self.styles['Heading1'], fontSize=22, alignment=TA_LEFT, textColor=accent)
        story.append(Paragraph("Medical Invoice", title_style))
        story.append(Spacer(1, 10))

        cc = Table([[self._format_company_info(invoice_data.company), self._format_client_info(invoice_data.client)]], colWidths=[8*cm,8*cm])
        cc.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
        story.append(cc)
        story.append(Spacer(1, 8))

        items_table = self._create_items_table_with_settings(invoice_data.items, invoice_data, fallback_header_color=accent)
        story.append(items_table)
        story.append(Spacer(1, 10))
        story.append(self._create_totals_table(invoice_data))

        meta = getattr(invoice_data, 'meta', {}) or {}
        med_codes = meta.get('medical_codes')
        if med_codes:
            story.append(Spacer(1, 8))
            codes_text = med_codes if isinstance(med_codes, str) else ", ".join(map(str, med_codes))
            story.append(Paragraph(f"Service Codes: {codes_text}", self.normal_style))
        return story

    def _create_construction_pro_template(self, invoice_data: InvoiceData) -> list:
        """Строительство: акцентные секции, объект/смета/этапы"""
        story = []
        accent = colors.HexColor('#E67E22')
        title_style = ParagraphStyle('ConstrTitle', parent=self.styles['Heading1'], fontSize=22, alignment=TA_LEFT, textColor=accent, fontName='Helvetica-Bold')
        story.append(Paragraph("Construction Invoice", title_style))
        story.append(Spacer(1, 8))

        meta = getattr(invoice_data, 'meta', {}) or {}
        site = meta.get('site_address')
        phase = meta.get('work_phase')
        if site or phase:
            story.append(Paragraph(f"Site: {site or '—'} | Phase: {phase or '—'}", self.normal_style))
            story.append(Spacer(1, 6))

        cc = Table([[self._format_company_info(invoice_data.company), self._format_client_info(invoice_data.client)]], colWidths=[8*cm,8*cm])
        cc.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
        story.append(cc)
        story.append(Spacer(1, 8))

        items_table = self._create_items_table_with_settings(invoice_data.items, invoice_data, fallback_header_color=accent)
        story.append(items_table)
        story.append(Spacer(1, 8))
        story.append(self._create_totals_table(invoice_data))
        return story

    def _create_creative_pro_template(self, invoice_data: InvoiceData) -> list:
        """Креатив: выразительная типографика, акценты, портфолио"""
        story = []
        accent = self._parse_theme_color(getattr(invoice_data, 'theme_color', {'r':255,'g':120,'b':180}))
        title_style = ParagraphStyle('CreatTitle', parent=self.styles['Heading1'], fontSize=26, alignment=TA_CENTER, textColor=accent, fontName='Helvetica-Bold')
        story.append(Paragraph("Creative Invoice", title_style))
        story.append(Spacer(1, 12))

        cc = Table([[self._format_company_info(invoice_data.company), self._format_client_info(invoice_data.client)]], colWidths=[8*cm,8*cm])
        cc.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
        story.append(cc)
        story.append(Spacer(1, 10))

        items_table = self._create_items_table_with_settings(invoice_data.items, invoice_data, fallback_header_color=accent)
        story.append(items_table)
        story.append(Spacer(1, 10))
        story.append(self._create_totals_table(invoice_data))

        meta = getattr(invoice_data, 'meta', {}) or {}
        portfolio = meta.get('portfolio_url')
        if portfolio:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Portfolio: {portfolio}", self.normal_style))
        return story

    def _create_legal_pro_template(self, invoice_data: InvoiceData) -> list:
        """Юридический: строгая верстка, номер дела"""
        story = []
        title_style = ParagraphStyle('LegalTitle', parent=self.styles['Heading1'], fontSize=22, alignment=TA_CENTER, textColor=colors.black, fontName='Times-Bold')
        story.append(Paragraph("Legal Invoice", title_style))
        story.append(Spacer(1, 10))

        cc = Table([[self._format_company_info(invoice_data.company), self._format_client_info(invoice_data.client)]], colWidths=[8*cm,8*cm])
        cc.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
        story.append(cc)
        story.append(Spacer(1, 8))

        items_table = self._create_items_table_with_settings(invoice_data.items, invoice_data, fallback_header_color=colors.HexColor('#3C4C64'))
        story.append(items_table)
        story.append(Spacer(1, 8))
        story.append(self._create_totals_table(invoice_data))

        meta = getattr(invoice_data, 'meta', {}) or {}
        case_ref = meta.get('case_reference')
        if case_ref:
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Case Reference: {case_ref}", self.normal_style))
        return story

    def _resolve_currency_symbol(self, c: Optional[str]) -> str:
        """Определение символа валюты по входному значению."""
        if not c:
            return '$'
        c = c.strip().upper()
        # Если прислан уже символ — вернём как есть
        symbols = {'$': '$', '€': '€', '£': '£', '₽': '₽', '¥': '¥'}
        if c in symbols:
            return symbols[c]
        # Коды валют
        codes = {
            'USD': '$', 'EUR': '€', 'GBP': '£', 'RUB': '₽', 'RUR': '₽', 'JPY': '¥', 'CNY': '¥'
        }
        return codes.get(c, c)

    def _create_modern_template(self, invoice_data: InvoiceData) -> list:
        """Создание современного шаблона"""
        story = []

        # Заголовок
        title = Paragraph("INVOICE", self.title_style)
        story.append(title)
        story.append(Spacer(1, 20))

        # Логотип компании, если задан — компактнее и справа
        try:
            logo_flow = self._load_logo_image(
                invoice_data.company,
                max_width_pt=2.5*cm,
                max_height_pt=2.5*cm,
            )
            if logo_flow:
                logo_flow.hAlign = 'RIGHT'
                story.append(logo_flow)
                story.append(Spacer(1, 8))
        except Exception:
            pass
        
        # Информация о компании и клиенте
        company_client_data = [
            [self._format_company_info(invoice_data.company), self._format_client_info(invoice_data.client)]
        ]
        
        company_client_table = Table(company_client_data, colWidths=[8*cm, 8*cm])
        company_client_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(company_client_table)
        story.append(Spacer(1, 30))
        
        # Информация об инвойсе
        invoice_info_data = [
            ['Invoice Number:', invoice_data.invoice_number],
            ['Invoice Date:', invoice_data.invoice_date.strftime('%d.%m.%Y')],
        ]
        
        if invoice_data.due_date:
            invoice_info_data.append(['Due Date:', invoice_data.due_date.strftime('%d.%m.%Y')])
        
        invoice_info_table = Table(invoice_info_data, colWidths=[4*cm, 4*cm])
        invoice_info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(invoice_info_table)
        story.append(Spacer(1, 30))
        
        # Таблица товаров/услуг
        items_table = self._create_items_table_with_settings(invoice_data.items, invoice_data, fallback_header_color=self._parse_theme_color(getattr(invoice_data, 'theme_color', None)))
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Итоги
        totals_table = self._create_totals_table(invoice_data)
        story.append(totals_table)
        
        # Примечания и условия
        if invoice_data.notes:
            story.append(Spacer(1, 30))
            notes_title = Paragraph("Notes:", self.subtitle_style)
            story.append(notes_title)
            notes_text = Paragraph(invoice_data.notes, self.normal_style)
            story.append(notes_text)
        
        if invoice_data.terms:
            story.append(Spacer(1, 20))
            terms_title = Paragraph("Terms & Conditions:", self.subtitle_style)
            story.append(terms_title)
            terms_text = Paragraph(invoice_data.terms, self.normal_style)
            story.append(terms_text)
        
        return story

    def _create_classic_template(self, invoice_data: InvoiceData) -> list:
        """Создание классического шаблона"""
        story = []
        
        # Заголовок с рамкой
        title = Paragraph("INVOICE", self.title_style)
        story.append(title)
        story.append(Spacer(1, 30))
        
        # Остальная логика аналогична современному шаблону, но с другими стилями
        # Для краткости используем ту же структуру
        return self._create_modern_template(invoice_data)

    def _create_minimal_template(self, invoice_data: InvoiceData) -> list:
        """Создание минималистичного шаблона"""
        story = []
        
        # Простой заголовок
        minimal_title_style = ParagraphStyle(
            'MinimalTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.black
        )
        
        title = Paragraph("Invoice", minimal_title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Остальная логика
        return self._create_modern_template(invoice_data)

    def _create_corporate_template(self, invoice_data: InvoiceData) -> list:
        """Создание корпоративного шаблона"""
        story = []
        
        # Корпоративный заголовок
        corporate_title_style = ParagraphStyle(
            'CorporateTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            spaceAfter=25,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d'),
            fontName='Helvetica-Bold'
        )
        
        title = Paragraph("INVOICE", corporate_title_style)
        story.append(title)
        story.append(Spacer(1, 25))
        
        # Остальная логика
        return self._create_modern_template(invoice_data)

    def _format_company_info(self, company) -> Paragraph:
        """Форматирование информации о компании как Paragraph для корректных переносов строк и стилизации"""
        info = f"<b>{company.name}</b><br/>{company.address}"
        details = []
        if getattr(company, 'phone', None):
            details.append(f"Phone: {company.phone}")
        if getattr(company, 'email', None):
            details.append(f"Email: {company.email}")
        if getattr(company, 'website', None):
            details.append(f"Website: {company.website}")
        if getattr(company, 'tax_id', None):
            details.append(f"Tax ID: {company.tax_id}")
        if details:
            info += "<br/>" + "<br/>".join(details)
        return Paragraph(info, self.normal_style)

    def _format_client_info(self, client) -> Paragraph:
        """Форматирование информации о клиенте как Paragraph для аккуратного блока Bill To"""
        info = f"<b>Bill To:</b><br/><b>{client.name}</b><br/>{client.address}"
        details = []
        if getattr(client, 'phone', None):
            details.append(f"Phone: {client.phone}")
        if getattr(client, 'email', None):
            details.append(f"Email: {client.email}")
        if details:
            info += "<br/>" + "<br/>".join(details)
        return Paragraph(info, self.normal_style)

    def _create_items_table(self, items, header_color: Optional[colors.Color] = None) -> Table:
        """Создание таблицы товаров/услуг"""
        # Заголовки таблицы
        data = [['Description', 'Qty', 'Unit Price', 'Total']]
        
        # Добавляем товары
        for item in items:
            unit = getattr(item, 'unit', None) or ''
            qty_display = f"{item.quantity:g} {unit}".strip()
            data.append([
                item.description,
                qty_display,
                f"${item.unit_price:.2f}",
                f"${item.total:.2f}"
            ])
        
        table = Table(data, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])
        header_bg = header_color or colors.HexColor('#34495e')
        table.setStyle(TableStyle([
            # Заголовок
            ('BACKGROUND', (0, 0), (-1, 0), header_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Данные
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            
            # Границы
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Чередующиеся цвета строк
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        
        return table

    def _create_totals_table(self, invoice_data) -> Table:
        """Создание таблицы итогов с аккуратным форматированием и выравниванием"""
        data = []

        # Подытог
        data.append([
            Paragraph('Subtotal:', self.normal_style),
            Paragraph(f"${invoice_data.subtotal:.2f}", self.normal_style)
        ])

        # Скидка
        if invoice_data.discount_amount and invoice_data.discount_amount > 0:
            data.append([
                Paragraph(f'Discount ({invoice_data.discount_rate}%):', self.normal_style),
                Paragraph(f"-${invoice_data.discount_amount:.2f}", self.normal_style)
            ])

        # Налог
        if invoice_data.tax_amount and invoice_data.tax_amount > 0:
            data.append([
                Paragraph(f'Tax ({invoice_data.tax_rate}%):', self.normal_style),
                Paragraph(f"${invoice_data.tax_amount:.2f}", self.normal_style)
            ])

        # Итого
        data.append([
            Paragraph('<b>TOTAL:</b>', self.total_style),
            Paragraph(f"<b>${invoice_data.total_amount:.2f}</b>", self.total_style)
        ])

        table = Table(data, colWidths=[10*cm, 4*cm])
        table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        return table
    def _parse_theme_color(self, theme_color: Optional[str]):
        """Парсинг пользовательского цвета: поддержка HEX и 'rgb(r,g,b)'. Возвращает объект colors.Color."""
        default = colors.HexColor('#34495e')
        if not theme_color:
            return default
        s = str(theme_color).strip()
        try:
            if s.startswith('#') or all(c in '0123456789abcdefABCDEF' for c in s.replace('#','')):
                return colors.HexColor(s if s.startswith('#') else f'#{s}')
            if s.lower().startswith('rgb'):
                m = s[s.find('(')+1:s.find(')')].split(',')
                r, g, b = [max(0, min(255, int(float(x)))) for x in m]
                return colors.Color(r/255.0, g/255.0, b/255.0)
            # Формат "r,g,b"
            parts = s.split(',')
            if len(parts) == 3:
                r, g, b = [max(0, min(255, int(float(x)))) for x in parts]
                return colors.Color(r/255.0, g/255.0, b/255.0)
        except Exception:
            return default
        return default

    def _parse_color_with_alpha(self, value: Any):
        """Возвращает (Color, alpha|None). Поддерживает HEX, rgb(), rgba(), 'r,g,b', 'r,g,b,a', dict{'r','g','b','a'}."""
        def clamp01(a: float) -> float:
            try:
                return max(0.0, min(1.0, float(a)))
            except Exception:
                return 1.0
        if value is None:
            return colors.HexColor('#34495e'), None
        if isinstance(value, colors.Color):
            return value, None
        # dict с r,g,b[,a]
        if isinstance(value, dict):
            r = max(0, min(255, int(float(value.get('r', 52)))))
            g = max(0, min(255, int(float(value.get('g', 73)))))
            b = max(0, min(255, int(float(value.get('b', 94)))))
            a = value.get('a')
            if a is not None and float(a) > 1:
                a = float(a) / 255.0
            alpha = clamp01(a) if a is not None else None
            return colors.Color(r/255.0, g/255.0, b/255.0), alpha
        # строковые форматы
        s = str(value).strip()
        try:
            if s.startswith('#') or all(c in '0123456789abcdefABCDEF' for c in s.replace('#','')):
                return colors.HexColor(s if s.startswith('#') else f'#{s}'), None
            if s.lower().startswith('rgba'):
                m = s[s.find('(')+1:s.find(')')].split(',')
                r, g, b = [max(0, min(255, int(float(x)))) for x in m[:3]]
                a_raw = float(m[3]) if len(m) > 3 else 1.0
                if a_raw > 1:
                    a_raw = a_raw / 255.0
                return colors.Color(r/255.0, g/255.0, b/255.0), clamp01(a_raw)
            if s.lower().startswith('rgb'):
                m = s[s.find('(')+1:s.find(')')].split(',')
                r, g, b = [max(0, min(255, int(float(x)))) for x in m[:3]]
                return colors.Color(r/255.0, g/255.0, b/255.0), None
            parts = s.split(',')
            if len(parts) == 4:
                r, g, b = [max(0, min(255, int(float(x)))) for x in parts[:3]]
                a_raw = float(parts[3])
                if a_raw > 1:
                    a_raw = a_raw / 255.0
                return colors.Color(r/255.0, g/255.0, b/255.0), clamp01(a_raw)
            if len(parts) == 3:
                r, g, b = [max(0, min(255, int(float(x)))) for x in parts]
                return colors.Color(r/255.0, g/255.0, b/255.0), None
        except Exception:
            pass
        return colors.HexColor('#34495e'), None

    def _blend_with_white(self, color: colors.Color, alpha: float) -> colors.Color:
        """Имитация прозрачности: смешивание цвета с белым фоном по коэффициенту alpha."""
        a = max(0.0, min(1.0, float(alpha)))
        r = a * color.red + (1 - a) * 1.0
        g = a * color.green + (1 - a) * 1.0
        b = a * color.blue + (1 - a) * 1.0
        return colors.Color(r, g, b)

    def _create_items_table_with_settings(self, items, invoice_data: InvoiceData, fallback_header_color: Optional[colors.Color] = None) -> Table:
        """Создание таблицы товаров/услуг с учетом настроек цвета/прозрачности из invoice_data."""
        data = [['Description', 'Qty', 'Unit Price', 'Total']]
        for item in items:
            unit = getattr(item, 'unit', None) or ''
            qty_display = f"{item.quantity:g} {unit}".strip()
            data.append([
                item.description,
                qty_display,
                f"${item.unit_price:.2f}",
                f"${item.total:.2f}"
            ])

        table = Table(data, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])

        # Header fill and alpha
        header_fill_val = getattr(invoice_data, 'table_header_fill', None)
        header_color_parsed, header_alpha_parsed = self._parse_color_with_alpha(header_fill_val)
        if fallback_header_color and header_fill_val is None:
            header_color_parsed = fallback_header_color
        # resolve alpha precedence: explicit field > from rgba > default
        header_alpha = getattr(invoice_data, 'table_header_alpha', None)
        if header_alpha is None:
            header_alpha = header_alpha_parsed if header_alpha_parsed is not None else 0.85
        header_bg = self._blend_with_white(header_color_parsed, header_alpha)

        # Cell fill and alpha
        cell_fill_val = getattr(invoice_data, 'table_cell_fill', None)
        cell_color_parsed, cell_alpha_parsed = self._parse_color_with_alpha(cell_fill_val)
        cell_alpha = getattr(invoice_data, 'table_cell_alpha', None)
        if cell_alpha is None:
            cell_alpha = cell_alpha_parsed if cell_alpha_parsed is not None else 0.75
        cell_bg = self._blend_with_white(cell_color_parsed, cell_alpha)

        # Border color and alpha
        border_fill_val = getattr(invoice_data, 'table_border_color', None)
        border_color_parsed, border_alpha_parsed = self._parse_color_with_alpha(border_fill_val)
        border_alpha = getattr(invoice_data, 'table_border_alpha', None)
        if border_alpha is None:
            border_alpha = border_alpha_parsed if border_alpha_parsed is not None else 0.50
        border_color = self._blend_with_white(border_color_parsed, border_alpha)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), header_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),

            ('GRID', (0, 0), (-1, -1), 1, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [cell_bg, colors.white]),
        ]))

        return table

    def _load_logo_image(self, company, max_width_pt: float = None, max_height_pt: float = None):
        """Загрузка логотипа из base64 data URL или по URL. Возвращает flowable Image или None.
        max_width_pt — максимальная ширина в пунктах (points). max_height_pt — максимальная высота.
        Если указана только ширина, высота подгоняется пропорционально.
        """
        # Сначала пробуем base64 data URL
        data_url = getattr(company, 'logo_base64', None)
        if isinstance(data_url, str) and data_url.strip():
            try:
                # Формат: data:image/png;base64,<...>
                s = data_url.strip()
                if s.startswith('data:') and ';base64,' in s:
                    header, b64 = s.split(';base64,', 1)
                    import base64
                    buf = base64.b64decode(b64)
                    bio = io.BytesIO(buf)
                    img = Image(bio)
                    if max_width_pt:
                        try:
                            img._restrictSize(max_width_pt, max_height_pt or max_width_pt)
                        except Exception:
                            pass
                    return img
            except Exception:
                pass
        # Далее — по logo_url
        url = getattr(company, 'logo_url', None)
        if isinstance(url, str) and url.strip():
            s = url.strip()
            try:
                # http(s)
                if s.startswith('http://') or s.startswith('https://'):
                    with urllib.request.urlopen(s, timeout=5) as resp:
                        data = resp.read()
                    bio = io.BytesIO(data)
                    img = Image(bio)
                else:
                    # локальный путь типа /uploads/logos/...
                    local = s.lstrip('/\\')
                    fpath = os.path.join(local) if os.path.exists(local) else os.path.join(os.getcwd(), local)
                    if not os.path.exists(fpath):
                        # пробуем абсолютный путь из проекта
                        cand = os.path.join(os.getcwd(), s)
                        fpath = cand if os.path.exists(cand) else s
                    img = Image(fpath)
                if max_width_pt:
                    try:
                        img._restrictSize(max_width_pt, max_height_pt or max_width_pt)
                    except Exception:
                        pass
                return img
            except Exception:
                pass
        return None

    def _create_custom_template(self, invoice_data: InvoiceData) -> list:
        """Пользовательский шаблон с фоном на основе invoice_9683.pdf"""
        story = []
        
        # Создаем фоновый элемент с градиентом
        from reportlab.platypus import PageBreak
        from reportlab.lib.colors import HexColor
        
        # Определяем цветовую схему на основе анализа PDF
        primary_color = HexColor('#2E4057')  # Темно-синий
        secondary_color = HexColor('#4A90A4')  # Бирюзовый
        accent_color = HexColor('#F4D03F')  # Желтый акцент
        
        # Заголовок с фоном
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.white,
            backColor=primary_color,
            borderPadding=15,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 10))
        
        # Создаем таблицу с информацией о компании и клиенте
        company_client_data = []
        
        # Логотип и информация о компании
        company_info = []
        logo_img = self._load_logo_image(invoice_data.company, max_width_pt=80, max_height_pt=80)
        if logo_img:
            company_info.append(logo_img)
        
        company_text = f"""
        <b>{invoice_data.company.name}</b><br/>
        {invoice_data.company.address}<br/>
        {invoice_data.company.phone or ''}<br/>
        {invoice_data.company.email or ''}
        """
        company_para = Paragraph(company_text, self.normal_style)
        company_info.append(company_para)
        
        # Информация о клиенте
        client_text = f"""
        <b>Bill To:</b><br/>
        <b>{invoice_data.client.name}</b><br/>
        {invoice_data.client.address}<br/>
        {invoice_data.client.phone or ''}<br/>
        {invoice_data.client.email or ''}
        """
        client_para = Paragraph(client_text, self.normal_style)
        
        # Информация об инвойсе
        invoice_info_text = f"""
        <b>Invoice #:</b> {invoice_data.invoice_number}<br/>
        <b>Date:</b> {invoice_data.invoice_date.strftime('%Y-%m-%d')}<br/>
        <b>Due Date:</b> {invoice_data.due_date.strftime('%Y-%m-%d') if invoice_data.due_date else 'N/A'}
        """
        invoice_info_para = Paragraph(invoice_info_text, self.normal_style)
        
        # Создаем таблицу заголовка
        header_table = Table([
            [company_info, client_para, invoice_info_para]
        ], colWidths=[6*cm, 6*cm, 6*cm])
        
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8F9FA')),
            ('GRID', (0, 0), (-1, -1), 1, secondary_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        # Таблица товаров с цветным заголовком
        items_data = [['Description', 'Qty', 'Unit Price', 'Total']]
        
        for item in invoice_data.items:
            items_data.append([
                item.description,
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${item.total:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm])
        items_table.setStyle(TableStyle([
            # Заголовок
            ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Данные
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, secondary_color),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Таблица итогов с акцентным цветом
        totals_data = []
        if invoice_data.subtotal:
            totals_data.append(['Subtotal:', f"${invoice_data.subtotal:.2f}"])
        if invoice_data.discount_amount and invoice_data.discount_amount > 0:
            totals_data.append(['Discount:', f"-${invoice_data.discount_amount:.2f}"])
        if invoice_data.tax_amount and invoice_data.tax_amount > 0:
            totals_data.append(['Tax:', f"${invoice_data.tax_amount:.2f}"])
        totals_data.append(['TOTAL:', f"${invoice_data.total_amount:.2f}"])
        
        totals_table = Table(totals_data, colWidths=[10*cm, 6*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('BACKGROUND', (0, -1), (-1, -1), accent_color),
            ('TEXTCOLOR', (0, -1), (-1, -1), primary_color),
            ('GRID', (0, 0), (-1, -1), 1, secondary_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(totals_table)
        
        # Примечания и условия
        if invoice_data.notes or invoice_data.terms:
            story.append(Spacer(1, 20))
            
            if invoice_data.notes:
                notes_style = ParagraphStyle(
                    'Notes',
                    parent=self.normal_style,
                    fontSize=10,
                    textColor=HexColor('#666666'),
                    spaceAfter=10
                )
                story.append(Paragraph(f"<b>Notes:</b> {invoice_data.notes}", notes_style))
            
            if invoice_data.terms:
                terms_style = ParagraphStyle(
                    'Terms',
                    parent=self.normal_style,
                    fontSize=10,
                    textColor=HexColor('#666666')
                )
                story.append(Paragraph(f"<b>Terms:</b> {invoice_data.terms}", terms_style))
        
        return story
