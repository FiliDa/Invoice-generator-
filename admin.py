from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
from datetime import datetime

from template_service import template_service
from models import TemplateStyle
from background_service import list_backgrounds, delete_background, get_background, scan_source_dir, add_from_path

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


def _count_files(dir_path: str) -> int:
    try:
        return len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
    except FileNotFoundError:
        return 0


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    all_templates = template_service.get_templates_for_user(app_id="admin", user_id="admin")
    free_count = len(template_service.get_free_templates())
    premium_count = len(template_service.get_premium_templates())
    invoices_count = _count_files("generated_invoices")
    logos_count = _count_files(os.path.join("uploads", "logos"))

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "templates_count": len(all_templates),
            "free_count": free_count,
            "premium_count": premium_count,
            "invoices_count": invoices_count,
            "logos_count": logos_count,
            "now": datetime.now(),
        },
    )


@router.get("/templates", response_class=HTMLResponse)
async def admin_templates(request: Request):
    all_templates = template_service.get_templates_for_user(app_id="admin", user_id="admin")
    return templates.TemplateResponse(
        "admin/templates_list.html",
        {"request": request, "templates": all_templates, "styles": [s.value for s in TemplateStyle]},
    )


@router.get("/templates/new", response_class=HTMLResponse)
async def admin_template_new(request: Request):
    return templates.TemplateResponse(
        "admin/template_form.html",
        {"request": request, "mode": "create", "styles": [s.value for s in TemplateStyle]},
    )


@router.post("/templates/new")
async def admin_template_create(
    request: Request,
    id: str = Form(...),
    name: str = Form(...),
    style: str = Form(...),
    description: Optional[str] = Form("") ,
    preview_url: Optional[str] = Form(""),
    is_premium: Optional[bool] = Form(False),
    table_header_fill: Optional[str] = Form(None),
    table_header_alpha: Optional[float] = Form(None),
    table_cell_fill: Optional[str] = Form(None),
    table_cell_alpha: Optional[float] = Form(None),
    table_border_color: Optional[str] = Form(None),
    table_border_alpha: Optional[float] = Form(None),
):
    if template_service.get_template_by_id(id):
        raise HTTPException(status_code=400, detail="Шаблон с таким ID уже существует")

    template_service.add_custom_template(
        {
            "id": id,
            "name": name,
            "style": style,
            "description": description,
            "preview_url": preview_url or "",
            "is_premium": bool(is_premium),
            "table_header_fill": table_header_fill,
            "table_header_alpha": table_header_alpha,
            "table_cell_fill": table_cell_fill,
            "table_cell_alpha": table_cell_alpha,
            "table_border_color": table_border_color,
            "table_border_alpha": table_border_alpha,
        }
    )
    return RedirectResponse(url="/admin/templates", status_code=303)


@router.get("/templates/{template_id}/edit", response_class=HTMLResponse)
async def admin_template_edit(request: Request, template_id: str):
    template = template_service.get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return templates.TemplateResponse(
        "admin/template_form.html",
        {"request": request, "mode": "edit", "template": template, "styles": [s.value for s in TemplateStyle]},
    )


@router.post("/templates/{template_id}/edit")
async def admin_template_update(
    request: Request,
    template_id: str,
    name: str = Form(...),
    style: str = Form(...),
    description: Optional[str] = Form("") ,
    preview_url: Optional[str] = Form(""),
    is_premium: Optional[bool] = Form(False),
    table_header_fill: Optional[str] = Form(None),
    table_header_alpha: Optional[float] = Form(None),
    table_cell_fill: Optional[str] = Form(None),
    table_cell_alpha: Optional[float] = Form(None),
    table_border_color: Optional[str] = Form(None),
    table_border_alpha: Optional[float] = Form(None),
):
    updated = template_service.update_template(
        template_id,
        {
            "name": name,
            "style": style,
            "description": description,
            "preview_url": preview_url or "",
            "is_premium": bool(is_premium),
            "table_header_fill": table_header_fill,
            "table_header_alpha": table_header_alpha,
            "table_cell_fill": table_cell_fill,
            "table_cell_alpha": table_cell_alpha,
            "table_border_color": table_border_color,
            "table_border_alpha": table_border_alpha,
        },
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return RedirectResponse(url="/admin/templates", status_code=303)


@router.post("/templates/{template_id}/delete")
async def admin_template_delete(template_id: str):
    deleted = template_service.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    return RedirectResponse(url="/admin/templates", status_code=303)


@router.get("/invoices", response_class=HTMLResponse)
async def admin_invoices(request: Request):
    files = []
    base_dir = "generated_invoices"
    try:
        for f in sorted(os.listdir(base_dir)):
            path = os.path.join(base_dir, f)
            if os.path.isfile(path):
                files.append({
                    "name": f,
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                    "url": f"/generated/{f}",
                    "mtime": datetime.fromtimestamp(os.path.getmtime(path)),
                })
    except FileNotFoundError:
        pass

    return templates.TemplateResponse("admin/invoices.html", {"request": request, "files": files})


@router.get("/uploads", response_class=HTMLResponse)
async def admin_uploads(request: Request):
    files = []
    base_dir = os.path.join("uploads", "logos")
    try:
        for f in sorted(os.listdir(base_dir)):
            path = os.path.join(base_dir, f)
            if os.path.isfile(path):
                files.append({
                    "name": f,
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                    "url": f"/uploads/logos/{f}",
                    "mtime": datetime.fromtimestamp(os.path.getmtime(path)),
                })
    except FileNotFoundError:
        pass

    return templates.TemplateResponse("admin/uploads.html", {"request": request, "files": files})


@router.get("/backgrounds", response_class=HTMLResponse)
async def admin_backgrounds(request: Request):
    """Страница управления фонами: список, превью, копирование ID"""
    items = list_backgrounds()
    # Добавляем вычисляемый веб-URL
    for it in items:
        try:
            import os
            basename = os.path.basename(it.get("stored_path", ""))
            it["url"] = f"/uploads/backgrounds/{basename}" if basename else None
        except Exception:
            it["url"] = None
    return templates.TemplateResponse("admin/backgrounds.html", {"request": request, "backgrounds": items})


@router.post("/backgrounds/upload")
async def admin_backgrounds_upload(file: UploadFile = File(...)):
    if file.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="Поддерживаются только PNG/JPG")
    import uuid, os, shutil
    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    tmp_path = os.path.join("uploads", "backgrounds", f"tmp_{uuid.uuid4()}{ext}")
    with open(tmp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        bg_id = add_from_path(tmp_path)
        if not bg_id:
            raise HTTPException(status_code=500, detail="Не удалось импортировать файл")
        return RedirectResponse(url="/admin/backgrounds", status_code=303)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@router.post("/backgrounds/{bg_id}/delete")
async def admin_backgrounds_delete(bg_id: str):
    ok = delete_background(bg_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Фон не найден")
    return RedirectResponse(url="/admin/backgrounds", status_code=303)


@router.post("/backgrounds/scan")
async def admin_backgrounds_scan():
    try:
        scan_source_dir()
    except Exception:
        pass
    return RedirectResponse(url="/admin/backgrounds", status_code=303)


@router.get("/configurator", response_class=HTMLResponse)
async def admin_configurator(request: Request):
    """Интерактивная страница-конструктор для заполнения шаблонов инвойсов"""
    all_templates = template_service.get_templates_for_user(app_id="admin", user_id="admin")

    # Параметры выбора шаблона: ?template_id=... или ?style=thermal
    q = request.query_params
    selected_template = None
    tpl_id = q.get("template_id")
    style = q.get("style")
    if tpl_id:
        selected_template = template_service.get_template_by_id(tpl_id)
    elif style:
        try:
            from models import TemplateStyle
            style_enum = TemplateStyle(style)
            by_style = template_service.get_templates_by_style(style_enum)
            selected_template = by_style[0] if by_style else None
        except Exception:
            selected_template = None

    if selected_template is None and all_templates:
        selected_template = all_templates[0]

    return templates.TemplateResponse(
        "admin/configurator.html",
        {
            "request": request,
            "templates": all_templates,
            "selected_template": selected_template,
        },
    )


@router.get("/generations", response_class=HTMLResponse)
async def admin_generations(request: Request):
    # Импортируем из main текущее хранилище статусов
    try:
        from main import generation_status
    except Exception:
        generation_status = {}

    items = []
    for gid, data in generation_status.items():
        items.append({
            "generation_id": gid,
            "status": data.get("status"),
            "progress": data.get("progress"),
            "pdf_url": data.get("pdf_url"),
            "created_at": data.get("created_at"),
            "completed_at": data.get("completed_at"),
        })

    return templates.TemplateResponse("admin/generations.html", {"request": request, "generations": items})
