import asyncio
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote, unquote

import httpx
from cachetools import TTLCache

from app.config import settings
from app.models.schemas import (
    EstadisticaDelito,
    EstadisticaResponse,
    GeoJSONFeatureCollection,
    Prefectura,
    Semana,
    TipoConsultaEstadistica,
    UmbralDelito,
    Unidad,
    Zona,
    _parse_numeric,
)


class StopAPIError(Exception):
    """Error al comunicarse con el portal STOP Carabineros."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


_DELTA_MAP: dict[TipoConsultaEstadistica, str] = {
    TipoConsultaEstadistica.EVENTOS: "1",
    TipoConsultaEstadistica.DETENIDOS: "2",
    TipoConsultaEstadistica.DETENCIONES: "3",
    TipoConsultaEstadistica.UMBRALES: "4",
}


class StopCarabinerosClient:
    """Cliente asíncrono con manejo de sesión XSRF y caché TTL para stop.carabineros.cl."""

    def __init__(
        self,
        base_url: str = settings.stop_base_url,
        timeout: float = settings.http_timeout_seconds,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/",
            },
        )
        self._xsrf_token: str | None = None
        self._session_lock = asyncio.Lock()

        self._catalog_cache: TTLCache[str, Any] = TTLCache(
            maxsize=128, ttl=settings.cache_ttl_catalogs_seconds
        )
        self._stats_cache: TTLCache[str, Any] = TTLCache(
            maxsize=512, ttl=settings.cache_ttl_stats_seconds
        )
        self._geo_cache: TTLCache[str, Any] = TTLCache(
            maxsize=256, ttl=settings.cache_ttl_geo_seconds
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _ensure_session(self, force: bool = False) -> None:
        """Obtiene o renueva cookies de sesión Laravel y el token XSRF."""
        if self._xsrf_token and not force:
            return
        async with self._session_lock:
            if self._xsrf_token and not force:
                return
            try:
                resp = await self._client.get("/")
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise StopAPIError(f"Error al iniciar sesión con STOP: {exc}", status_code=502) from exc

            raw_token = self._client.cookies.get("XSRF-TOKEN")
            if not raw_token:
                raise StopAPIError(
                    "STOP no devolvió cookie XSRF-TOKEN al iniciar sesión.", status_code=502
                )
            self._xsrf_token = unquote(raw_token)

    async def _post_json(self, path: str) -> Any:
        """Ejecuta una petición POST autenticada con XSRF-TOKEN y reintenta si expira."""
        await self._ensure_session()
        headers = {"X-XSRF-TOKEN": self._xsrf_token} if self._xsrf_token else {}

        try:
            resp = await self._client.post(path, headers=headers)
            if resp.status_code in (401, 403, 419):
                await self._ensure_session(force=True)
                headers = {"X-XSRF-TOKEN": self._xsrf_token} if self._xsrf_token else {}
                resp = await self._client.post(path, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException as exc:
            raise StopAPIError(f"Timeout consultando STOP ({path}): {exc}", status_code=504) from exc
        except httpx.HTTPStatusError as exc:
            raise StopAPIError(
                f"STOP respondió HTTP {exc.response.status_code} en {path}",
                status_code=502,
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise StopAPIError(f"Error procesando respuesta de STOP ({path}): {exc}", status_code=502) from exc

    async def get_semanas(self) -> list[Semana]:
        cache_key = "semanas"
        if cache_key in self._catalog_cache:
            return self._catalog_cache[cache_key]

        raw = await self._post_json("/cargasemana")
        semanas: list[Semana] = []
        for item in raw:
            valor = str(item.get("VALUE1", ""))
            partes = valor.split("@")
            semana_txt = partes[0] if partes else valor
            ano_val = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 0
            semanas.append(
                Semana(
                    valor=valor,
                    semana=semana_txt,
                    ano=ano_val,
                    descripcion=str(item.get("cadena", "")).strip(),
                )
            )
        self._catalog_cache[cache_key] = semanas
        return semanas

    async def get_zonas(self) -> list[Zona]:
        cache_key = "zonas"
        if cache_key in self._catalog_cache:
            return self._catalog_cache[cache_key]

        raw = await self._post_json("/cargazonas")
        zonas = [
            Zona(
                id=int(item["id"]),
                nombre=str(item["deszona"]).strip(),
                orden=item.get("orden"),
            )
            for item in raw
        ]
        self._catalog_cache[cache_key] = zonas
        return zonas

    async def get_prefecturas(self, zona: str) -> list[Prefectura]:
        zona_clean = zona.strip()
        cache_key = f"prefecturas:{zona_clean}"
        if cache_key in self._catalog_cache:
            return self._catalog_cache[cache_key]

        raw = await self._post_json(f"/cargaprefecturas/{quote(zona_clean, safe='')}")
        prefecturas = [
            Prefectura(
                id=int(item["id"]),
                nombre=str(item["desprefectura"]).strip(),
                zona=str(item.get("deszona", zona_clean)).strip(),
            )
            for item in raw
        ]
        self._catalog_cache[cache_key] = prefecturas
        return prefecturas

    async def get_unidades(self, prefectura: str) -> list[Unidad]:
        pref_clean = prefectura.strip()
        cache_key = f"unidades:{pref_clean}"
        if cache_key in self._catalog_cache:
            return self._catalog_cache[cache_key]

        raw = await self._post_json(f"/cargaunidades/{quote(pref_clean, safe='')}")
        unidades = [
            Unidad(
                id=int(item["id"]),
                nombre=str(item["desunidad"]).strip(),
                prefectura=str(item.get("desprefectura", pref_clean)).strip(),
            )
            for item in raw
        ]
        self._catalog_cache[cache_key] = unidades
        return unidades

    @staticmethod
    def resolver_nivel_y_entidad(
        zona: str | None = None,
        prefectura: str | None = None,
        unidad: str | None = None,
    ) -> tuple[str, str, str]:
        """Determina el código de nivel STOP (1..5), nombre de nivel y entidad objetivo."""
        if unidad and unidad.strip():
            return "5", "unidad", unidad.strip()
        if prefectura and prefectura.strip():
            return "4", "prefectura", prefectura.strip()
        if zona and zona.strip():
            z = zona.strip()
            if z.upper() == "NACIONAL":
                return "1", "nacional", "NACIONAL"
            if z.upper() == "JEF. ZONA METROPOLITANA":
                return "2", "zona_metropolitana", "JEF. ZONA METROPOLITANA"
            return "3", "zona", z
        return "1", "nacional", "NACIONAL"

    async def get_estadisticas(
        self,
        tipo: TipoConsultaEstadistica,
        semana: str,
        ano: int,
        zona: str | None = None,
        prefectura: str | None = None,
        unidad: str | None = None,
    ) -> EstadisticaResponse:
        semana_clean = semana.strip()
        nivel_code, nivel_nombre, entidad = self.resolver_nivel_y_entidad(zona, prefectura, unidad)
        caso = f"{nivel_code}{_DELTA_MAP[tipo]}"

        cache_key = f"stats:{caso}:{semana_clean}:{ano}:{entidad}"
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        path = (
            f"/tablaeventos/{quote(caso, safe='')}/"
            f"{quote(semana_clean, safe='')}/"
            f"{ano}/"
            f"{quote(entidad, safe='')}"
        )
        raw = await self._post_json(path)

        if tipo == TipoConsultaEstadistica.UMBRALES:
            datos: list[EstadisticaDelito] | list[UmbralDelito] = [
                UmbralDelito(
                    delito=str(row.get("delito", "")).strip(),
                    tipo=row.get("type"),
                    crime_id=row.get("crimeId"),
                    series_anuales={
                        k: _parse_numeric(v)
                        for k, v in row.items()
                        if k not in {"delito", "type", "crimeId"}
                    },
                )
                for row in raw
            ]
        else:
            datos = [
                EstadisticaDelito(
                    delito=str(row.get("delito", "")).strip(),
                    tipo=row.get("type"),
                    crime_id=row.get("crimeId"),
                    ultima_semana_ano_anterior=row.get("lastWeekPastYear"),
                    ultima_semana_ano_actual=row.get("lastWeekThisYear"),
                    ultima_semana_variacion_pct=row.get("lastWeekChangeRate"),
                    ultimo_mes_ano_anterior=row.get("lastMonthPastYear"),
                    ultimo_mes_ano_actual=row.get("lastMonthThisYear"),
                    ultimo_mes_variacion_pct=row.get("lastMonthChangeRate"),
                    ano_en_curso_anterior=row.get("currentYearPastYear"),
                    ano_en_curso_actual=row.get("currentYearThisYear"),
                    ano_en_curso_variacion_pct=row.get("currentYearChangeRate"),
                )
                for row in raw
            ]

        result = EstadisticaResponse(
            tipo=tipo,
            semana=semana_clean,
            ano=ano,
            nivel=nivel_nombre,
            entidad=entidad,
            caso_stop=caso,
            total_registros=len(datos),
            datos=datos,
        )
        self._stats_cache[cache_key] = result
        return result

    async def get_mapa_delitos(
        self,
        bbox: str,
        filtro: str,
        zoom: int = 13,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> GeoJSONFeatureCollection:
        now = datetime.now()
        if not fecha_hasta:
            fecha_hasta = now.strftime("%Y-%m-%d 00:00")
        if not fecha_desde:
            fecha_desde = (now - timedelta(days=91)).strftime("%Y-%m-%d 23:59")

        cache_key = f"geo4:{bbox}:{filtro}:{zoom}:{fecha_desde}:{fecha_hasta}"
        if cache_key in self._geo_cache:
            return self._geo_cache[cache_key]

        path = (
            f"/serviceCall4/{quote(bbox, safe=',.-')}/"
            f"{quote(filtro, safe='')}/"
            f"{zoom}/"
            f"{quote(fecha_desde, safe=':- ')}/"
            f"{quote(fecha_hasta, safe=':- ')}"
        )
        raw = await self._post_json(path)
        result = GeoJSONFeatureCollection.model_validate(raw)
        self._geo_cache[cache_key] = result
        return result

    async def get_mapa_factores_riesgo(
        self,
        bbox: str,
        campo: str,
        valor: str,
    ) -> GeoJSONFeatureCollection:
        cache_key = f"geo3:{bbox}:{campo}:{valor}"
        if cache_key in self._geo_cache:
            return self._geo_cache[cache_key]

        path = (
            f"/serviceCall3/{quote(bbox, safe=',.-')}/"
            f"{quote(campo, safe='')}/"
            f"{quote(valor, safe='')}"
        )
        raw = await self._post_json(path)
        result = GeoJSONFeatureCollection.model_validate(raw)
        self._geo_cache[cache_key] = result
        return result
