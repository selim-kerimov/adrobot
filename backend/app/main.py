from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import offers
from app.campaigns.router import router as campaigns_router
from app.editor.router import router as editor_router
from app.editor.service import EditorError, NotFoundError
from app.editor.weights import WeightError
from app.keitaro import KeitaroError

app = FastAPI(title="Adrobot")
app.include_router(campaigns_router)
app.include_router(editor_router)
app.include_router(offers.router)


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})


@app.exception_handler(NotFoundError)
def not_found(request: Request, error: NotFoundError) -> JSONResponse:
    return _error(404, str(error))


@app.exception_handler(EditorError)
def editor_error(request: Request, error: EditorError) -> JSONResponse:
    return _error(409, str(error))


@app.exception_handler(WeightError)
def weight_error(request: Request, error: WeightError) -> JSONResponse:
    return _error(422, str(error))


@app.exception_handler(KeitaroError)
def keitaro_error(request: Request, error: KeitaroError) -> JSONResponse:
    # A missing object in Keitaro is a 404 for our client too; anything else is Keitaro's fault.
    return _error(404 if error.status_code == 404 else 502, str(error))


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
