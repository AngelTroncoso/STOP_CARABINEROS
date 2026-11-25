from fastapi import APIRouter, Depends, Query

from app.dependencies import get_stop_client
from app.models.schemas import Prefectura, Semana, Unidad, Zona
from app.services.stop_client import StopCarabinerosClient

router = APIRouter(prefix="/api/v1", tags=["Catálogos"])


@router.get(
    "/semanas",
    response_model=list[Semana],
    summary="Listar semanas disponibles",
    description="Devuelve todas las semanas estadísticas disponibles en STOP Carabineros.",
)
async def listar_semanas(
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> list[Semana]:
    return await client.get_semanas()


@router.get(
    "/zonas",
    response_model=list[Zona],
    summary="Listar zonas policiales",
    description="Devuelve las zonas policiales disponibles (incluyendo NACIONAL y JEF. ZONA METROPOLITANA).",
)
async def listar_zonas(
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> list[Zona]:
    return await client.get_zonas()


@router.get(
    "/prefecturas",
    response_model=list[Prefectura],
    summary="Listar prefecturas de una zona",
    description="Devuelve las prefecturas pertenecientes a una zona policial específica.",
)
async def listar_prefecturas(
    zona: str = Query(..., description="Nombre exacto de la zona (ej. 'ZONA DE CARABINEROS SANTIAGO OESTE')"),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> list[Prefectura]:
    return await client.get_prefecturas(zona)


@router.get(
    "/unidades",
    response_model=list[Unidad],
    summary="Listar unidades policiales de una prefectura",
    description="Devuelve las comisarías/unidades pertenecientes a una prefectura específica.",
)
async def listar_unidades(
    prefectura: str = Query(..., description="Nombre exacto de la prefectura (ej. 'PREF. STGO. CENTRAL')"),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> list[Unidad]:
    return await client.get_unidades(prefectura)
