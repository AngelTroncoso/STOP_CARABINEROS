from fastapi.testclient import TestClient

from app.main import app
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
)
from app.services.stop_client import StopAPIError, StopCarabinerosClient


class FakeStopClient:
    """Cliente simulado para pruebas deterministas de la API."""

    async def get_semanas(self) -> list[Semana]:
        return [
            Semana(
                valor="SEMANA 47@2026",
                semana="SEMANA 47",
                ano=2026,
                descripcion="SEMANA 47/2026  (del 16-11-2026 al 22-11-2026)",
            )
        ]

    async def get_zonas(self) -> list[Zona]:
        return [
            Zona(id=1, nombre="NACIONAL", orden=1),
            Zona(id=2, nombre="JEF. ZONA METROPOLITANA", orden=2),
            Zona(id=18, nombre="ZONA DE CARABINEROS SANTIAGO OESTE", orden=3),
        ]

    async def get_prefecturas(self, zona: str) -> list[Prefectura]:
        return [
            Prefectura(id=32, nombre="PREF. STGO. CENTRAL", zona=zona),
        ]

    async def get_unidades(self, prefectura: str) -> list[Unidad]:
        return [
            Unidad(id=136, nombre="2DA. COM. SANTIAGO", prefectura=prefectura),
        ]

    async def get_estadisticas(
        self,
        tipo: TipoConsultaEstadistica,
        semana: str,
        ano: int,
        zona: str | None = None,
        prefectura: str | None = None,
        unidad: str | None = None,
    ) -> EstadisticaResponse:
        nivel_code, nivel, entidad = StopCarabinerosClient.resolver_nivel_y_entidad(
            zona, prefectura, unidad
        )
        delta = {"eventos": "1", "detenidos": "2", "detenciones": "3", "umbrales": "4"}[
            tipo.value
        ]
        if tipo == TipoConsultaEstadistica.UMBRALES:
            datos = [
                UmbralDelito(
                    delito="Homicidios",
                    tipo=1,
                    crime_id=1,
                    series_anuales={"ano2015": 501, "ano2020": 689},
                )
            ]
        else:
            datos = [
                EstadisticaDelito(
                    delito="Homicidios",
                    tipo=1,
                    crime_id=1,
                    ultima_semana_ano_anterior="17",
                    ultima_semana_ano_actual="11",
                    ultima_semana_variacion_pct="-35",
                    ultimo_mes_ano_anterior="72",
                    ultimo_mes_ano_actual="60",
                    ultimo_mes_variacion_pct="-17",
                    ano_en_curso_anterior="689",
                    ano_en_curso_actual="760",
                    ano_en_curso_variacion_pct="10",
                )
            ]
        return EstadisticaResponse(
            tipo=tipo,
            semana=semana,
            ano=ano,
            nivel=nivel,
            entidad=entidad,
            caso_stop=f"{nivel_code}{delta}",
            total_registros=len(datos),
            datos=datos,
        )

    async def get_mapa_delitos(
        self,
        bbox: str,
        filtro: str,
        zoom: int = 13,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> GeoJSONFeatureCollection:
        return GeoJSONFeatureCollection(
            type="FeatureCollection",
            bbox=[float(x) for x in bbox.split(",")],
            features=[{"type": "Feature", "properties": {"filtro": filtro, "zoom": zoom}}],
        )

    async def get_mapa_factores_riesgo(
        self,
        bbox: str,
        campo: str,
        valor: str,
    ) -> GeoJSONFeatureCollection:
        return GeoJSONFeatureCollection(
            type="FeatureCollection",
            bbox=[float(x) for x in bbox.split(",")],
            features=[{"type": "Feature", "properties": {"campo": campo, "valor": valor}}],
        )

    async def close(self) -> None:
        return None


def _get_client() -> TestClient:
    client = TestClient(app)
    app.state.stop_client = FakeStopClient()
    return client


def test_root_docs_and_health() -> None:
    with TestClient(app) as client:
        r_root = client.get("/")
        assert r_root.status_code == 200
        root_json = r_root.json()
        assert root_json["documentacion_swagger"] == "/docs"
        assert root_json["documentacion_redoc"] == "/redoc"
        assert root_json["openapi"] == "/openapi.json"
        assert root_json["health"] == "/health"

        r_health = client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json() == {"status": "ok"}

        r_docs = client.get("/docs")
        assert r_docs.status_code == 200
        assert "Swagger UI" in r_docs.text

        r_redoc = client.get("/redoc")
        assert r_redoc.status_code == 200
        assert "ReDoc" in r_redoc.text

        r_openapi = client.get("/openapi.json")
        assert r_openapi.status_code == 200
        openapi_data = r_openapi.json()
        assert "/api/v1/semanas" in openapi_data["paths"]
        assert "/api/v1/estadisticas" in openapi_data["paths"]


def test_catalogos() -> None:
    client = _get_client()

    r_sem = client.get("/api/v1/semanas")
    assert r_sem.status_code == 200
    assert r_sem.json()[0]["ano"] == 2026

    r_zon = client.get("/api/v1/zonas")
    assert r_zon.status_code == 200
    assert len(r_zon.json()) == 3

    r_pref = client.get("/api/v1/prefecturas", params={"zona": "ZONA DE CARABINEROS SANTIAGO OESTE"})
    assert r_pref.status_code == 200
    assert r_pref.json()[0]["nombre"] == "PREF. STGO. CENTRAL"

    r_uni = client.get("/api/v1/unidades", params={"prefectura": "PREF. STGO. CENTRAL"})
    assert r_uni.status_code == 200
    assert r_uni.json()[0]["nombre"] == "2DA. COM. SANTIAGO"


def test_resolver_nivel_y_entidad() -> None:
    assert StopCarabinerosClient.resolver_nivel_y_entidad() == ("1", "nacional", "NACIONAL")
    assert StopCarabinerosClient.resolver_nivel_y_entidad(zona="NACIONAL") == (
        "1",
        "nacional",
        "NACIONAL",
    )
    assert StopCarabinerosClient.resolver_nivel_y_entidad(
        zona="JEF. ZONA METROPOLITANA"
    ) == ("2", "zona_metropolitana", "JEF. ZONA METROPOLITANA")
    assert StopCarabinerosClient.resolver_nivel_y_entidad(
        zona="ZONA ARICA Y PARINACOTA"
    ) == ("3", "zona", "ZONA ARICA Y PARINACOTA")
    assert StopCarabinerosClient.resolver_nivel_y_entidad(
        zona="ZONA ARICA Y PARINACOTA", prefectura="PREF. ARICA"
    ) == ("4", "prefectura", "PREF. ARICA")
    assert StopCarabinerosClient.resolver_nivel_y_entidad(
        prefectura="PREF. STGO. CENTRAL", unidad="2DA. COM. SANTIAGO"
    ) == ("5", "unidad", "2DA. COM. SANTIAGO")


def test_estadisticas_endpoints() -> None:
    client = _get_client()

    r_ev = client.get("/api/v1/estadisticas/eventos", params={"semana": "SEMANA 47", "ano": 2026})
    assert r_ev.status_code == 200
    body = r_ev.json()
    assert body["caso_stop"] == "11"
    assert body["datos"][0]["ultima_semana_ano_actual"] == 11
    assert body["datos"][0]["ultima_semana_variacion_pct"] == -35

    r_umb = client.get(
        "/api/v1/estadisticas/umbrales",
        params={"semana": "SEMANA 47", "ano": 2026, "unidad": "2DA. COM. SANTIAGO"},
    )
    assert r_umb.status_code == 200
    assert r_umb.json()["caso_stop"] == "54"
    assert r_umb.json()["datos"][0]["series_anuales"]["ano2015"] == 501


def test_mapa_endpoints_y_validacion_bbox() -> None:
    client = _get_client()

    r_del = client.get(
        "/api/v1/mapa/delitos",
        params={"bbox": "-70.68,-33.47,-70.62,-33.43", "delito": "EVE_HURTO", "zoom": 13},
    )
    assert r_del.status_code == 200
    assert r_del.json()["features"][0]["properties"]["filtro"] == "EVE_HURTO"

    r_fac = client.get(
        "/api/v1/mapa/factores-riesgo",
        params={"bbox": "-70.68,-33.47,-70.62,-33.43", "valor": "SITUACIONAL"},
    )
    assert r_fac.status_code == 200
    assert r_fac.json()["features"][0]["properties"]["valor"] == "SITUACIONAL"

    r_bad = client.get("/api/v1/mapa/delitos", params={"bbox": "invalido"})
    assert r_bad.status_code == 422


def test_upstream_error_handler() -> None:
    class ErrorClient(FakeStopClient):
        async def get_zonas(self) -> list[Zona]:
            raise StopAPIError("Fallo de prueba", status_code=502)

    client = TestClient(app)
    app.state.stop_client = ErrorClient()
    r = client.get("/api/v1/zonas")
    assert r.status_code == 502
    assert r.json()["error"] == "stop_upstream_error"


def test_vercel_entrypoint_lazy_client() -> None:
    import json
    from pathlib import Path
    from starlette.requests import Request
    from app.dependencies import get_stop_client
    from app.main import app as vercel_app

    vercel_cfg = json.loads(Path("vercel.json").read_text(encoding="utf-8"))
    assert "rewrites" not in vercel_cfg
    assert "app/main.py" in vercel_cfg.get("functions", {})

    if hasattr(vercel_app.state, "stop_client"):
        delattr(vercel_app.state, "stop_client")

    client = TestClient(vercel_app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    # Verifica que get_stop_client inicialice el cliente de forma lazy sin lifespan
    scope = {"type": "http", "app": vercel_app, "headers": []}
    req = Request(scope)
    lazy_client = get_stop_client(req)
    assert isinstance(lazy_client, StopCarabinerosClient)

