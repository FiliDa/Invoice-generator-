import os
import hashlib
import shutil
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker


DB_PATH = os.path.join(os.getcwd(), "backgrounds.db")
MANAGED_DIR = os.path.join("uploads", "backgrounds")
SOURCE_DIR = os.path.join(os.getcwd(), "invoice backfon")

os.makedirs(MANAGED_DIR, exist_ok=True)

Base = declarative_base()


class Background(Base):
    __tablename__ = "backgrounds"

    id = Column(String(64), primary_key=True)  # неизменяемый id (uuid/hex)
    filename = Column(String(256), nullable=False)
    source_path = Column(Text, nullable=False)  # исходный путь (для мониторинга)
    stored_path = Column(Text, nullable=False)  # путь в управляемом каталоге uploads/backgrounds
    content_type = Column(String(64), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deleted = Column(Boolean, default=False)


engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def init_db():
    Base.metadata.create_all(engine)


def _ext_content_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in {".png"}:
        return "image/png"
    if ext in {".jpg", ".jpeg", ".jfif"}:
        return "image/jpeg"
    return "application/octet-stream"


def add_from_path(path: str, force_new_id: bool = False) -> Optional[str]:
    """
    Импорт файла в управляемый каталог и регистрацию в БД.
    Возвращает id. Если файл с тем же sha256 уже существует и force_new_id=False, возвращает существующий id.
    """
    if not os.path.isfile(path):
        return None
    init_db()
    session = SessionLocal()
    try:
        sha = _file_sha256(path)
        filename = os.path.basename(path)
        size = os.path.getsize(path)
        ctype = _ext_content_type(filename)

        if not force_new_id:
            existing = session.query(Background).filter(Background.sha256 == sha, Background.deleted == False).first()
            if existing:
                return existing.id

        # Генерация детерминированного id на основе sha256 (короткий префикс)
        bg_id = sha[:32]
        stored_name = f"{bg_id}_{filename}"
        stored_path = os.path.join(MANAGED_DIR, stored_name)

        # Копируем в управляемый каталог
        if os.path.abspath(path) != os.path.abspath(stored_path):
            shutil.copy2(path, stored_path)

        now = datetime.utcnow()
        record = Background(
            id=bg_id,
            filename=filename,
            source_path=os.path.abspath(path),
            stored_path=os.path.abspath(stored_path),
            content_type=ctype,
            size_bytes=size,
            sha256=sha,
            created_at=now,
            updated_at=now,
            deleted=False,
        )
        session.merge(record)  # upsert по pk
        session.commit()
        return bg_id
    finally:
        session.close()


def list_backgrounds(include_deleted: bool = False) -> List[Dict]:
    init_db()
    session = SessionLocal()
    try:
        q = session.query(Background)
        if not include_deleted:
            q = q.filter(Background.deleted == False)
        items = []
        for b in q.order_by(Background.created_at.desc()).all():
            items.append({
                "id": b.id,
                "filename": b.filename,
                "size_bytes": b.size_bytes,
                "stored_path": b.stored_path,
                "source_path": b.source_path,
                "content_type": b.content_type,
                "sha256": b.sha256,
                "created_at": b.created_at,
                "deleted": b.deleted,
            })
        return items
    finally:
        session.close()


def get_background(id_: str) -> Optional[Dict]:
    init_db()
    session = SessionLocal()
    try:
        b = session.query(Background).filter(Background.id == id_).first()
        if not b:
            return None
        return {
            "id": b.id,
            "filename": b.filename,
            "size_bytes": b.size_bytes,
            "stored_path": b.stored_path,
            "source_path": b.source_path,
            "content_type": b.content_type,
            "sha256": b.sha256,
            "created_at": b.created_at,
            "deleted": b.deleted,
        }
    finally:
        session.close()


def resolve_path(id_: str) -> Optional[str]:
    """Возвращает путь к управляемому файлу (stored_path) для id."""
    init_db()
    session = SessionLocal()
    try:
        b = session.query(Background).filter(Background.id == id_, Background.deleted == False).first()
        return b.stored_path if b else None
    finally:
        session.close()


def delete_background(id_: str) -> bool:
    init_db()
    session = SessionLocal()
    try:
        b = session.query(Background).filter(Background.id == id_).first()
        if not b:
            return False
        b.deleted = True
        b.updated_at = datetime.utcnow()
        session.commit()
        return True
    finally:
        session.close()


def scan_source_dir() -> int:
    """Сканирует SOURCE_DIR, импортирует новые файлы, возвращает число добавленных (или найденных) записей."""
    init_db()
    count = 0
    if not os.path.isdir(SOURCE_DIR):
        return 0
    for name in os.listdir(SOURCE_DIR):
        path = os.path.join(SOURCE_DIR, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".jfif"}:
            continue
        bg_id = add_from_path(path)
        if bg_id:
            count += 1
    return count


def ensure_monitor_loop(loop_seconds: int = 300):
    """Запускает фоновую асинхронную задачу периодического сканирования каталога."""
    import asyncio

    async def _worker():
        while True:
            try:
                scan_source_dir()
            except Exception as e:
                print(f"Background monitor error: {e}")
            await asyncio.sleep(loop_seconds)

    try:
        # если уже в event loop FastAPI — создаем задачу
        loop = asyncio.get_event_loop()
        loop.create_task(_worker())
    except RuntimeError:
        # если нет цикла — игнорируем (например, при пакетных скриптах)
        pass

