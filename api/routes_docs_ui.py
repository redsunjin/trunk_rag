from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from services import index_service

router = APIRouter()


def _web_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "web"


@router.get("/rag-docs")
def docs() -> dict[str, list[dict[str, int | str]]]:
    return {"docs": index_service.list_target_docs()}


@router.get("/rag-docs/{doc_name}")
def read_doc(doc_name: str) -> dict[str, str]:
    path = index_service.resolve_doc_path(doc_name)
    return {
        "name": path.name,
        "content": path.read_text(encoding="utf-8"),
    }


@router.get("/", response_class=HTMLResponse)
def index_page() -> HTMLResponse:
    return RedirectResponse(url="/intro")


@router.get("/intro", response_class=HTMLResponse)
def intro_page() -> HTMLResponse:
    page_path = _web_dir() / "intro.html"
    if not page_path.exists():
        return HTMLResponse("<h3>web/intro.html not found.</h3>", status_code=404)
    return HTMLResponse(page_path.read_text(encoding="utf-8"))


@router.get("/app", response_class=HTMLResponse)
def app_page() -> HTMLResponse:
    page_path = _web_dir() / "index.html"
    if not page_path.exists():
        return HTMLResponse("<h3>web/index.html not found.</h3>", status_code=404)
    return HTMLResponse(page_path.read_text(encoding="utf-8"))


@router.get("/admin", response_class=HTMLResponse)
def admin_page() -> HTMLResponse:
    page_path = _web_dir() / "admin.html"
    if not page_path.exists():
        return HTMLResponse("<h3>web/admin.html not found.</h3>", status_code=404)
    return HTMLResponse(page_path.read_text(encoding="utf-8"))


@router.get("/styles.css")
def styles_file() -> FileResponse:
    css_path = _web_dir() / "styles.css"
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="styles.css not found")
    return FileResponse(css_path, media_type="text/css")


@router.get("/js/{file_name}")
def script_file(file_name: str) -> FileResponse:
    safe_name = file_name.strip()
    if not safe_name.endswith(".js"):
        raise HTTPException(status_code=404, detail="js file not found")
    js_path = (_web_dir() / "js" / safe_name).resolve()
    js_root = (_web_dir() / "js").resolve()
    if js_root not in js_path.parents:
        raise HTTPException(status_code=404, detail="js file not found")
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="js file not found")
    return FileResponse(js_path, media_type="application/javascript")
