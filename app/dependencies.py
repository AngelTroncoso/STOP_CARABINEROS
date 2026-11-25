from fastapi import Request

from app.services.stop_client import StopCarabinerosClient


def get_stop_client(request: Request) -> StopCarabinerosClient:
    """Devuelve el cliente STOP compartido, inicializándolo de forma lazy en entornos serverless."""
    client = getattr(request.app.state, "stop_client", None)
    if client is None:
        client = StopCarabinerosClient()
        request.app.state.stop_client = client
    return client
