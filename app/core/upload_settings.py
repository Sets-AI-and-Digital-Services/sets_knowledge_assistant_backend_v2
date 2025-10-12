# app/core/upload_settings.py
from pydantic_settings import BaseSettings

class UploadSettings(BaseSettings):
    # Limits (tweak as you like)
    MAX_FILES: int = 30
    MAX_FILE_MB: int = 15
    MAX_TOTAL_MB: int = 200

    # Chunked upload
    UPLOAD_CHUNK_BYTES: int = 1024 * 1024  # 1 MB
    STORAGE_ROOT: str = "./Storage"

    # File types
    ALLOWED_EXTS: tuple[str, ...] = (
        "pdf","doc","docx","ppt","pptx","xls","xlsx","csv","txt","json","xml"
    )
    ALLOWED_MIMES: tuple[str, ...] = (
        "application/pdf",
        "application/msword","application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-powerpoint","application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv","text/plain","application/json","application/xml","text/xml",
    )

    model_config = {"env_prefix": "", "case_sensitive": False}
