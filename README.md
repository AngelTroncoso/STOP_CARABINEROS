# API Pública STOP Carabineros de Chile

API REST pública construida con **Python** y **FastAPI** que expone de forma estructurada, tipada y documentada (OpenAPI / Swagger) los datos públicos del **Sistema Táctico de Operación Policial (STOP)** de Carabineros de Chile ([stop.carabineros.cl](https://stop.carabineros.cl/)).

## Características

- **Catálogos territoriales y temporales**: semanas disponibles, zonas policiales, prefecturas y unidades/comisarías.
- **Estadísticas delictuales**: eventos (casos policiales), detenidos, detenciones y umbrales históricos (5+ años), con resolución automática de nivel territorial (`nacional`, `zona_metropolitana`, `zona`, `prefectura`, `unidad`).
- **Capas geográficas (GeoJSON)**: hexágonos de concentración delictual y factores de riesgo (situacionales, sociales, viales e incendios forestales) por *bounding box* (`EPSG:4326`).
- **Sesión XSRF automática y caché TTL en memoria**: maneja automáticamente las cookies de sesión de Laravel (`XSRF-TOKEN`) y cachea respuestas para ofrecer baja latencia sin sobrecargar el portal de origen.
- **CORS habilitado** para consumo desde cualquier frontend o cliente público.

## Instalación y ejecución

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Documentación interactiva disponible en:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Endpoints principales

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/health` | Estado del servicio |
| `GET` | `/api/v1/semanas` | Semanas estadísticas disponibles |
| `GET` | `/api/v1/zonas` | Zonas policiales |
| `GET` | `/api/v1/prefecturas?zona=...` | Prefecturas de una zona |
| `GET` | `/api/v1/unidades?prefectura=...` | Unidades/comisarías de una prefectura |
| `GET` | `/api/v1/estadisticas` | Consulta unificada (`tipo`: `eventos`, `detenidos`, `detenciones`, `umbrales`) |
| `GET` | `/api/v1/estadisticas/eventos` | Casos policiales / eventos delictuales |
| `GET` | `/api/v1/estadisticas/detenidos` | Detenidos |
| `GET` | `/api/v1/estadisticas/detenciones` | Detenciones |
| `GET` | `/api/v1/estadisticas/umbrales` | Umbrales históricos por año |
| `GET` | `/api/v1/mapa/delitos` | GeoJSON hexagonal de delitos (`EVE_LESIONES`, `EVE_ROB_FUVI`, `EVE_ROB_VI`, `EVE_ROB_FU`, `EVE_HURTO`) |
| `GET` | `/api/v1/mapa/factores-riesgo` | GeoJSON de factores de riesgo (`SITUACIONAL`, `SOCIAL`, `VIAL`, `INCENDIO FORESTAL`) |

## Ejemplos de uso

```bash
# Listar semanas
curl "http://localhost:8000/api/v1/semanas"

# Estadísticas nacionales de eventos para la semana 47 de 2026
curl "http://localhost:8000/api/v1/estadisticas/eventos?semana=SEMANA%2047&ano=2026"

# Estadísticas de una comisaría específica
curl "http://localhost:8000/api/v1/estadisticas/eventos?semana=SEMANA%2047&ano=2026&unidad=2DA.%20COM.%20SANTIAGO"

# Capa GeoJSON de hurtos en el centro de Santiago
curl "http://localhost:8000/api/v1/mapa/delitos?bbox=-70.68,-33.47,-70.62,-33.43&delito=EVE_HURTO&zoom=13"
```

## Pruebas

```bash
pytest -v
```

## Despliegue y pruebas en Vercel (Python Runtime)

El proyecto utiliza el entrypoint automático [app/main.py](app/main.py) (zero-config para FastAPI en Vercel) y la configuración de duración en [vercel.json](vercel.json):

```bash
# 1. Iniciar sesión en Vercel (si aún no estás autenticado)
vercel login

# 2. Probar localmente simulando Vercel Functions
vercel dev

# 3. Desplegar a producción
vercel --prod
```
