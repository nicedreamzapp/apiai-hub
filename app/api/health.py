from fastapi import Header, Request
from config.auth import guard
from utils.system import get_system_stats
import datetime

def create_health_routes(app):
    @app.get("/health")
    def health(request: Request, x_api_key: str | None = Header(None)):
        guard(x_api_key, request)
        return {"ok": True, "time": datetime.datetime.now().isoformat(), "service": "APIAI Hub Professional"}

    @app.get("/stats")
    def stats(request: Request, x_api_key: str | None = Header(None)):
        guard(x_api_key, request)
        return get_system_stats()
