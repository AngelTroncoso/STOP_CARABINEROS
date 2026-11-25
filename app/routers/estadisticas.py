from fastapi import APIRouter, Depends, Query

from app.dependencies import get_stop_client
from app.models.schemas import EstadisticaResponse, TipoConsultaEstadistica
from app.services.stop_client import StopCarabinerosClient

router = APIRouter(prefix="/api/v1/estadisticas", tags=["Estadísticas Delictuales"])


@router.get(
    "",
    response_model=EstadisticaResponse,
    summary="Consultar estadísticas STOP (unificado)",
    description=(
        "Consulta estadísticas delictuales de STOP para cualquier nivel territorial. "
        "Si no se especifica zona, prefectura ni unidad, consulta a nivel NACIONAL. "
        "Si se indica unidad, prevalece sobre prefectura y zona."
    ),
)
async def consultar_estadisticas(
    tipo: TipoConsultaEstadistica = Query(
        TipoConsultaEstadistica.EVENTOS,
        description="Tipo de estadística: eventos, detenidos, detenciones o umbrales",
    ),
    semana: str = Query(..., description="Identificador de semana, ej. 'SEMANA 47'"),
    ano: int = Query(..., ge=2015, le=2100, description="Año de la semana, ej. 2026"),
    zona: str | None = Query(None, description="Nombre de la zona (ej. 'NACIONAL', 'ZONA ARICA Y PARINACOTA')"),
    prefectura: str | None = Query(None, description="Nombre de la prefectura (ej. 'PREF. STGO. CENTRAL')"),
    unidad: str | None = Query(None, description="Nombre de la unidad/comisaría (ej. '2DA. COM. SANTIAGO')"),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> EstadisticaResponse:
    return await client.get_estadisticas(
        tipo=tipo,
        semana=semana,
        ano=ano,
        zona=zona,
        prefectura=prefectura,
        unidad=unidad,
    )


@router.get(
    "/eventos",
    response_model=EstadisticaResponse,
    summary="Consultar casos policiales / eventos delictuales",
)
async def consultar_eventos(
    semana: str = Query(..., description="Identificador de semana, ej. 'SEMANA 47'"),
    ano: int = Query(..., ge=2015, le=2100, description="Año de la semana, ej. 2026"),
    zona: str | None = Query(None),
    prefectura: str | None = Query(None),
    unidad: str | None = Query(None),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> EstadisticaResponse:
    return await client.get_estadisticas(
        tipo=TipoConsultaEstadistica.EVENTOS,
        semana=semana,
        ano=ano,
        zona=zona,
        prefectura=prefectura,
        unidad=unidad,
    )


@router.get(
    "/detenidos",
    response_model=EstadisticaResponse,
    summary="Consultar estadísticas de detenidos",
)
async def consultar_detenidos(
    semana: str = Query(..., description="Identificador de semana, ej. 'SEMANA 47'"),
    ano: int = Query(..., ge=2015, le=2100, description="Año de la semana, ej. 2026"),
    zona: str | None = Query(None),
    prefectura: str | None = Query(None),
    unidad: str | None = Query(None),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> EstadisticaResponse:
    return await client.get_estadisticas(
        tipo=TipoConsultaEstadistica.DETENIDOS,
        semana=semana,
        ano=ano,
        zona=zona,
        prefectura=prefectura,
        unidad=unidad,
    )


@router.get(
    "/detenciones",
    response_model=EstadisticaResponse,
    summary="Consultar estadísticas de detenciones",
)
async def consultar_detenciones(
    semana: str = Query(..., description="Identificador de semana, ej. 'SEMANA 47'"),
    ano: int = Query(..., ge=2015, le=2100, description="Año de la semana, ej. 2026"),
    zona: str | None = Query(None),
    prefectura: str | None = Query(None),
    unidad: str | None = Query(None),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> EstadisticaResponse:
    return await client.get_estadisticas(
        tipo=TipoConsultaEstadistica.DETENCIONES,
        semana=semana,
        ano=ano,
        zona=zona,
        prefectura=prefectura,
        unidad=unidad,
    )


@router.get(
    "/umbrales",
    response_model=EstadisticaResponse,
    summary="Consultar umbrales históricos (últimos 5+ años)",
)
async def consultar_umbrales(
    semana: str = Query(..., description="Identificador de semana, ej. 'SEMANA 47'"),
    ano: int = Query(..., ge=2015, le=2100, description="Año de la semana, ej. 2026"),
    zona: str | None = Query(None),
    prefectura: str | None = Query(None),
    unidad: str | None = Query(None),
    client: StopCarabinerosClient = Depends(get_stop_client),
) -> EstadisticaResponse:
    return await client.get_estadisticas(
        tipo=TipoConsultaEstadistica.UMBRALES,
        semana=semana,
        ano=ano,
        zona=zona,
        prefectura=prefectura,
        unidad=unidad,
    )
