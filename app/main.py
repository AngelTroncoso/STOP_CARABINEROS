from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import catalogos, estadisticas, mapa
from app.services.stop_client import StopAPIError, StopCarabinerosClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = getattr(app.state, "stop_client", None)
    if client is None:
        client = StopCarabinerosClient()
        app.state.stop_client = client
    try:
        yield
    finally:
        await client.close()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(StopAPIError)
async def stop_api_error_handler(_request: Request, exc: StopAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "stop_upstream_error", "detail": exc.message},
    )


@app.get("/", tags=["Sistema"], summary="Información general de la API")
async def root() -> dict[str, str]:
    return {
        "nombre": settings.app_name,
        "version": settings.app_version,
        "fuente": settings.stop_base_url,
        "documentacion_swagger": "/docs",
        "documentacion_redoc": "/redoc",
        "openapi": "/openapi.json",
        "health": "/health",
    }


@app.get("/health", tags=["Sistema"], summary="Estado del servicio")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(catalogos.router)
app.include_router(estadisticas.router)
app.include_router(mapa.router)
