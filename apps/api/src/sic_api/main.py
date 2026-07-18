from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .settings import get_settings
from .modules.users.api import router as users_router
from .modules.identity.api import router as identity_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.api_version)
app.include_router(identity_router)
app.include_router(users_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    return {"status": "ok", "service": "sic-api"}


@app.get("/health/ready", tags=["health"])
async def ready() -> JSONResponse:
    return JSONResponse({"status": "ready", "service": "sic-api", "environment": settings.app_env})
