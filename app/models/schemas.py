from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _parse_numeric(value: Any) -> int | float | str | None:
    """Convierte strings numéricos a int/float cuando es posible."""
    if value is None or isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return int(stripped)
        except ValueError:
            try:
                return float(stripped)
            except ValueError:
                return stripped
    return value


class Semana(BaseModel):
    """Semana epidemiológica/estadística disponible en STOP."""

    valor: str = Field(..., description="Identificador interno, ej. 'SEMANA 47@2026'")
    semana: str = Field(..., description="Nombre de la semana, ej. 'SEMANA 47'")
    ano: int = Field(..., description="Año de la semana, ej. 2026")
    descripcion: str = Field(..., description="Texto legible con rango de fechas")


class Zona(BaseModel):
    """Zona policial o nivel de agregación superior."""

    id: int
    nombre: str = Field(..., description="Nombre oficial de la zona (deszona)")
    orden: int | None = None


class Prefectura(BaseModel):
    """Prefectura perteneciente a una zona policial."""

    id: int
    nombre: str = Field(..., description="Nombre oficial de la prefectura (desprefectura)")
    zona: str = Field(..., description="Nombre de la zona a la que pertenece")


class Unidad(BaseModel):
    """Comisaría o unidad policial perteneciente a una prefectura."""

    id: int
    nombre: str = Field(..., description="Nombre oficial de la unidad (desunidad)")
    prefectura: str = Field(..., description="Nombre de la prefectura a la que pertenece")


class TipoConsultaEstadistica(str, Enum):
    """Tipo de estadística a consultar en STOP."""

    EVENTOS = "eventos"
    DETENIDOS = "detenidos"
    DETENCIONES = "detenciones"
    UMBRALES = "umbrales"


class EstadisticaDelito(BaseModel):
    """Registro estadístico de un delito (eventos, detenidos o detenciones)."""

    delito: str
    tipo: int | None = Field(default=None, description="Tipo de agrupación (type)")
    crime_id: int | None = Field(default=None, description="ID del delito (crimeId)")
    ultima_semana_ano_anterior: int | float | str | None = None
    ultima_semana_ano_actual: int | float | str | None = None
    ultima_semana_variacion_pct: int | float | str | None = None
    ultimo_mes_ano_anterior: int | float | str | None = None
    ultimo_mes_ano_actual: int | float | str | None = None
    ultimo_mes_variacion_pct: int | float | str | None = None
    ano_en_curso_anterior: int | float | str | None = None
    ano_en_curso_actual: int | float | str | None = None
    ano_en_curso_variacion_pct: int | float | str | None = None

    @field_validator(
        "ultima_semana_ano_anterior",
        "ultima_semana_ano_actual",
        "ultima_semana_variacion_pct",
        "ultimo_mes_ano_anterior",
        "ultimo_mes_ano_actual",
        "ultimo_mes_variacion_pct",
        "ano_en_curso_anterior",
        "ano_en_curso_actual",
        "ano_en_curso_variacion_pct",
        mode="before",
    )
    @classmethod
    def _coerce_numbers(cls, v: Any) -> int | float | str | None:
        return _parse_numeric(v)


class UmbralDelito(BaseModel):
    """Registro histórico de comportamiento de 5 años (umbrales) por delito."""

    model_config = ConfigDict(extra="allow")

    delito: str
    tipo: int | None = None
    crime_id: int | None = None
    series_anuales: dict[str, int | float | str | None] = Field(
        default_factory=dict,
        description="Valores históricos por año (ej. {'ano2015': 501, ...})",
    )


class EstadisticaResponse(BaseModel):
    """Respuesta unificada de estadísticas STOP."""

    tipo: TipoConsultaEstadistica
    semana: str
    ano: int
    nivel: str = Field(..., description="Nivel territorial consultado (nacional, zona_metropolitana, zona, prefectura, unidad)")
    entidad: str = Field(..., description="Nombre de la entidad territorial consultada")
    caso_stop: str = Field(..., description="Código interno 'caso' utilizado en STOP")
    total_registros: int
    datos: list[EstadisticaDelito] | list[UmbralDelito]


class TipoDelitoMapa(str, Enum):
    """Filtros de delitos disponibles para la capa hexagonal del mapa."""

    LESIONES = "EVE_LESIONES"
    ROBOS = "EVE_ROB_FUVI"
    ROBOS_CON_VIOLENCIA = "EVE_ROB_VI"
    ROBOS_CON_FUERZA = "EVE_ROB_FU"
    HURTOS = "EVE_HURTO"


class FactorRiesgoCampo(str, Enum):
    """Campo de consulta para factores de riesgo."""

    TIPO = "ctpi_tipo"
    DESCRIPCION = "ctpi_descripcion"


class FactorRiesgoTipo(str, Enum):
    """Categorías principales de factores de riesgo."""

    SITUACIONAL = "SITUACIONAL"
    SOCIAL = "SOCIAL"
    VIAL = "VIAL"
    INCENDIO_FORESTAL = "INCENDIO FORESTAL"


class GeoJSONFeatureCollection(BaseModel):
    """Colección GeoJSON devuelta por los servicios geográficos de STOP."""

    model_config = ConfigDict(extra="allow")

    type: str = "FeatureCollection"
    bbox: list[float] | None = None
    features: list[dict[str, Any]] = Field(default_factory=list)
