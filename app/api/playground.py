from pathlib import Path

from fastapi import APIRouter
from starlette.responses import FileResponse, RedirectResponse

router = APIRouter(include_in_schema=False)
WEB_DIRECTORY = Path(__file__).resolve().parent.parent / "web"
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
}


@router.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse("/playground")


@router.get("/playground")
async def playground() -> FileResponse:
    return FileResponse(WEB_DIRECTORY / "index.html", headers=HEADERS)


@router.get("/playground/assets/style.css")
async def stylesheet() -> FileResponse:
    return FileResponse(WEB_DIRECTORY / "style.css", headers=HEADERS, media_type="text/css")


@router.get("/playground/assets/playground.js")
async def javascript() -> FileResponse:
    return FileResponse(
        WEB_DIRECTORY / "playground.js", headers=HEADERS, media_type="application/javascript"
    )
