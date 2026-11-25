from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_stop_client
from app.models.schemas import (
    FactorRiesgoCampo,
    GeoJSONFeatureCollection,
    TipoDelitoMapa,
)
from app.services.stop_client import StopCarabinerosClient

router = APIRouter(prefix="/api/v1/mapa", tags=["Capas Geográficas (GeoJSON)"])


def _validate_bbox(bbox: str) -> str:
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(
            status_code=422,
            detail="El parámetro bbox debe tener 4 coordenadas separadas por coma: min_lon,min_lat,max_lon,max_lat",
        )
    try:
        [float(p) for p in parts]
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Todas las coordenadas de bbox deben ser números válidos.",
        ) from exc
    return ",".join(parts)


@router.get(
    "/delitos",
    response_model=GeoJSONFeatureCollection,
    summary="Obtener capa hexagonal de delitos (GeoJSON)",
    description=(
        "Devuelve un FeatureCollection GeoJSON con hexágonos de concentración delictual "
        "para el bounding box (EPSG:4326) y rango de fechas indicados (por defecto últimos 91 días)."
    ),
)
async def obtener_mapa_delitos(
    bbox: str = Query(
        ...,
        description="Bounding box EPSG:4326: 'min_lon,min_lat,max_lon,max_lat'",
        examples=["-70.68,-33.47,-70.62,-33.43"],
    ),
    delito: TipoDelitoMapa = Query(
        TipoDelitoMapa.HURTOS,
        description="Tipo de delito para la capa hexagonal",
    ),
    zoom: int = Query(13, ge=1, le=20, description="Nivel de zoom del mapa (1-20)"),
    fecha_desde: str | None = Query(
        None,
        description="Fecha inicial 'YYYY-MM-DD HH:MM' (por defecto 91 días atrás)",
    ),
    fecha_hasta: str | None = Query(
        None,
        description="Fecha final 'YYYY-MM-DD HH:MM' (por defecto hoy 00:00)",
    ),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> GeoJSONFeatureCollection:
    bbox_clean = _validate_bbox(bbox)
    return await client.get_mapa_delitos(
        bbox=bbox_clean,
        filtro=delito.value,
        zoom=zoom,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@router.get(
    "/factores-riesgo",
    response_model=GeoJSONFeatureCollection,
    summary="Obtener capa de factores de riesgo (GeoJSON)",
    description=(
        "Devuelve un FeatureCollection GeoJSON con factores de riesgo situacionales, sociales, "
        "viales o de incendio forestal dentro del bounding box (EPSG:4326)."
    ),
)
async def obtener_factores_riesgo(
    bbox: str = Query(
        ...,
        description="Bounding box EPSG:4326: 'min_lon,min_lat,max_lon,max_lat'",
        examples=["-70.68,-33.47,-70.62,-33.43"],
    ),
    campo: FactorRiesgoCampo = Query(
        FactorRiesgoCampo.TIPO,
        description="Campo de filtro: 'ctpi_tipo' (categoría) o 'ctpi_descripcion' (detalle)",
    ),
    valor: str = Query(
        "SITUACIONAL",
        description="Valor del filtro (ej. 'SITUACIONAL', 'SOCIAL', 'VIAL', 'INCENDIO FORESTAL' o descripción específica)",
    ),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> GeoJSONFeatureCollection:
    bbox_clean = _validate_bbox(bbox)
    return await client.get_mapa_factores_riesgo(
        bbox=bbox_clean,
        campo=campo.value,
        valor=valor.strip(),
    )
